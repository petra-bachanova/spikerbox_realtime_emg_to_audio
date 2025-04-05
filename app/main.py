import numpy as np
import scipy
import os
import musicpy
from musicpy import degree_to_note, play
import sys
import socketio
from scipy import signal


# Add the project root to sys.path
app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

from app.utils.config import Config
import app.data_reading.nsp_data as nsp_reader
import app.data_reading.wav_data as wav_data_reader
import app.plot_data
import app.process_data as process_data
import app.save_data
import time

global calibrate_mode
calibrate_mode = False
resting_amplitude = 6
max_amplitude = 70

def get_signal_frame(
        config: Config,
        i: int,
        stft_frame_length: int,
        wav_signal: list,
        sample_rate: int,
        ):
    """
    TODO - docstring
    """

    if config.use_live_data:
        # read spikerbox data
        serial_bytes = nsp_reader.read_raw_nsp_data()
        frame = nsp_reader.process_data(serial_bytes)
    else:
        try:
            frame = wav_data_reader.extract_window(
                wav_signal=wav_signal,
                sample_rate=sample_rate,
                i=i,
                frame_length=stft_frame_length
                )
        except IndexError:
            print("Reached end of signal")
            # TODO - this is ok when running outsite of Dash but not appropriate for Dash
            exit()

    return frame


def emit_data(sio: socketio.Client, data: np.array, sample_rate: int):

    global start_time
    current_time = time.time() - start_time

    time_list = current_time + np.array(range(len(data)))/(sample_rate)

    data = data[1::3]
    time_list = time_list[1::3]

    data_dict = {
        "frame": data.tolist(),
        "time": time_list.tolist()
    }

    try:
        sio.emit('signal_frame_update', {"data": data_dict})
    except Exception as e:
        print(f"Error sending data: {e}")


def main(
        config: Config,
        from_backend: bool = False,
        sio: socketio.Client | None = None
        ):
    """
    TODO - docstring
    """

    global calibrate_mode
    global start_time
    start_time = time.time()

    if not config.use_live_data:
        # sample_rate: samples per second
        # data: numpy array
        sample_rate, wav_signal = wav_data_reader.read_wav_file(config)
        signal_min = signal.min()
        signal_max = signal.max()
    else:
        sample_rate = 10000
        com_port = config.com_port
        baud_rate = config.baud_rate
        nsp_reader.initialize_serial(com_port=com_port, baud_rate=baud_rate)

    # stft = Short-Time Fourier Transform. See https://brianmcfee.net/dstbook-site/content/ch09-stft/STFT.html for docs
    # TODO - define appropriate frame length
    # TODO - place frame length in config.ini or calculate appropriate length
    stft_frame_length = 2000  # samples
    stft_hop_length = 1000  # samples
    hops_per_frame = stft_frame_length / stft_hop_length
    hop_time = stft_hop_length / sample_rate  # time between hops in seconds

    i = 0  # initialise loop iteration

    while True:
        # print(f"i = {i}")

        if i < stft_frame_length:
            # wait until we have enough samples for stft
            i += stft_hop_length
            continue

        if config.use_live_data:
            wav_signal = None

        frame = get_signal_frame(
            config=config,
            i=i,
            stft_frame_length=stft_frame_length,
            wav_signal=wav_signal,
            sample_rate=sample_rate
            )

        # Notch filtering
        notch_frequencies = [60, 120, 180, 240, 300, 360, 420]
        filtered_frame = process_data.apply_notch_filters(
            signal_in=frame,
            notch_frequencies=notch_frequencies
            )

        # Band pass filtering
        b, a = signal.butter(4, [20, 450], 'bandpass', fs=sample_rate)
        filtered_emg = signal.filtfilt(b, a, filtered_frame)
        # Get power within the band pass filter
        rms_amplitude = np.sqrt(np.mean(filtered_emg**2))
        print(rms_amplitude)

        if not calibrate_mode:
            normalized_amplitude = (rms_amplitude - resting_amplitude) / (max_amplitude - resting_amplitude)
            normalized_amplitude = np.clip(normalized_amplitude, 0, 1)
            
            if normalized_amplitude > 0.05:
                # Map to MIDI note range (e.g., C3 to C6)
                min_note = 48  # C3
                max_note = 84  # C6
                midi_number = min_note + int(normalized_amplitude * (max_note - min_note))
            
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


                note_obj = midi_to_musicpy_note(midi_number, 0.5)
                musicpy.play(note_obj)


        # emit data if running via backend server
        if from_backend and (i % stft_frame_length == 0):
            # i % stft_frame_length == 0 ensures we are not duplicating data in graph
            emit_data(sio=sio, data=frame, sample_rate=sample_rate)

        time.sleep(0.2)
        # print(f"hop: {hop_time}")
        i += stft_hop_length


def start_main_from_backend(sio: socketio.Client):

    print("Starting main() from backend")
    config = Config()
    main(config=config, from_backend=True, sio=sio)


if __name__ == "__main__":

    print("here")
    config = Config()
    main(config=config)
