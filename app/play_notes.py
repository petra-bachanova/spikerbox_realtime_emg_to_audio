import queue
import statistics
import threading
import time
from collections import deque

import musicpy
import numpy as np

from app.utils.config import Config


class NotePlaybackWorker:
    """
    Background worker that serializes note playback on a dedicated thread.
    """

    def __init__(
            self,
            queue_size: int = 3,
            queue_timeout_seconds: float = 0.05,
            expected_interval_seconds: float | None = None,
            stats_window_size: int = 25,
            ):
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._queue_timeout_seconds = queue_timeout_seconds
        self._expected_interval_seconds = expected_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._play_durations_seconds = deque(maxlen=stats_window_size)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, note_obj):
        """
        Add a note to the queue.

        If the queue is full, discard the oldest queued note to prioritize recency.
        """
        if note_obj is None or self._stop_event.is_set():
            return
        try:
            self._queue.put_nowait(note_obj)
        except queue.Full:
            try:
                _ = self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                return
            try:
                self._queue.put_nowait(note_obj)
            except queue.Full:
                # Rare race if worker refills queue before put; drop note.
                return

    def stop(self, join_timeout_seconds: float = 2.0):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=join_timeout_seconds)

    def _run(self):
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                note_obj = self._queue.get(timeout=self._queue_timeout_seconds)
            except queue.Empty:
                continue
            try:
                t0 = time.perf_counter()
                musicpy.play(note_obj)
                elapsed_seconds = time.perf_counter() - t0
                self._play_durations_seconds.append(elapsed_seconds)
                median_seconds = statistics.median(self._play_durations_seconds)

                if self._expected_interval_seconds is not None:
                    print(
                        "Playback timing | "
                        f"elapsed={elapsed_seconds:.4f}s | "
                        f"rolling_median={median_seconds:.4f}s | "
                        f"update_interval={self._expected_interval_seconds:.4f}s"
                    )
                else:
                    print(
                        "Playback timing | "
                        f"elapsed={elapsed_seconds:.4f}s | "
                        f"rolling_median={median_seconds:.4f}s"
                    )
            except Exception as e:
                print(f"Note playback error: {e}")
            finally:
                self._queue.task_done()


def midi_to_musicpy_note(midi_number, duration=0.5):
    """
    Convert MIDI note number to musicpy note() format and play it
    Parameters:
    midi_number: int - MIDI note number (e.g., 60 for middle C)
    duration: float - note duration in seconds
    """
    note_with_octave = str(musicpy.degree_to_note(midi_number))
    note_name = note_with_octave[0]
    # Handle sharps/flats (which would make the note name 2 characters)
    if len(note_with_octave) > 2 and note_with_octave[1] in ['#', 'b']:
        note_name = note_with_octave[:2]
        octave = int(note_with_octave[2:])
    else:
        octave = int(note_with_octave[1:])

    # Create the musicpy note
    return musicpy.note(note_name, octave, duration)


def get_midi_for_amplitude(
        config: Config,
        rms_amplitude: float,
        rms_to_audio_range: list[int],
        ):
    """
    From a given RMS amplitude, compute MIDI note value if amplitude is in playback range.
    """
    rms_to_audio_range_min = rms_to_audio_range[0]
    rms_to_audio_range_max = rms_to_audio_range[1]
    if rms_to_audio_range_max <= rms_to_audio_range_min:
        return None

    normalized_amplitude = (rms_amplitude - rms_to_audio_range_min) / (rms_to_audio_range_max - rms_to_audio_range_min)
    normalized_amplitude = np.clip(normalized_amplitude, 0, 1)

    if normalized_amplitude <= 0.03:
        return None

    min_note = 48  # C3
    max_note = 84  # C6
    return min_note + int(normalized_amplitude * (max_note - min_note))


def play_midi_note(
        config: Config,
        midi_number: int,
        playback_worker: NotePlaybackWorker | None = None,
        ):
    """
    Create and play/submit a note from a MIDI value.
    """
    note_obj = midi_to_musicpy_note(
        midi_number=midi_number,
        duration=config.audio_note_duration_seconds,
    )

    if playback_worker is not None:
        playback_worker.submit(note_obj)
        return

    # Fallback keeps backward compatibility for direct call sites.
    musicpy.play(note_obj)


def get_note_for_amplitude(
        config: Config,
        rms_amplitude: float,
        rms_to_audio_range: list[int],
        ):
    """
    From a given RMS amplitude, create a note object if amplitude is in the playback range.
    """
    midi_number = get_midi_for_amplitude(
        config=config,
        rms_amplitude=rms_amplitude,
        rms_to_audio_range=rms_to_audio_range,
    )
    if midi_number is None:
        return None

    return midi_to_musicpy_note(midi_number, config.audio_note_duration_seconds)


def play_notes(
        config: Config,
        rms_amplitude: float,
        rms_to_audio_range: list[int],
        playback_worker: NotePlaybackWorker | None = None,
        ):
    """
    From a given RMS amplitude, play a note.

    Calculation of the note to play is handled here as well as the play audio instruction to the system.
    """

    if not config.play_sounds:
        return

    midi_number = get_midi_for_amplitude(
        config=config,
        rms_amplitude=rms_amplitude,
        rms_to_audio_range=rms_to_audio_range,
    )
    if midi_number is None:
        return

    play_midi_note(
        config=config,
        midi_number=midi_number,
        playback_worker=playback_worker,
    )
