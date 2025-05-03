import musicpy
import numpy as np

from app.utils.config import Config


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

    # Create and play the musicpy note
    return musicpy.note(note_name, octave, duration)


def play_notes(
        config: Config,
        rms_amplitude: float,
        rms_to_audio_range: list[int],
        ):
    """
    From a given RMS amplitude, play a note.

    Calculation of the note to play is handled here as well as the play audio instruction to the system. 
    """

    # Extract min and max RMS values, between which we will play notes
    rms_to_audio_range_min = rms_to_audio_range[0]
    rms_to_audio_range_max = rms_to_audio_range[1]

    # For the given RMS value range, calculate (proportionally) where the given RMS value falls
    normalized_amplitude = (rms_amplitude - rms_to_audio_range_min) / (rms_to_audio_range_max - rms_to_audio_range_min)
    normalized_amplitude = np.clip(normalized_amplitude, 0, 1)

    # calculate MIDI number and play MIDI
    if normalized_amplitude > 0.05:
        # Map to MIDI note range (e.g., C3 to C6)
        min_note = 48  # C3
        max_note = 84  # C6
        midi_number = min_note + int(normalized_amplitude * (max_note - min_note))

        if config.play_sounds:
            note_obj = midi_to_musicpy_note(midi_number, config.update_interval)
            musicpy.play(note_obj)
