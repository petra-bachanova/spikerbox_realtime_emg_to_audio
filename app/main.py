import numpy as np
import musicpy
from musicpy import degree_to_note, play
import socketio
from scipy import signal

from app.utils.config import Config
import app.play_notes as play_notes
import app.data_reading.nsp_data as nsp_reader
import app.data_reading.wav_data as wav_data_reader
import app.process_data as process_data
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
                i=i,
                frame_length=stft_frame_length
                )
        except IndexError:
            print("Reached end of signal")
            # TODO - this is ok when running outsite of Dash but not appropriate for Dash
            exit()

    return frame


def emit_data(
        config: Config,
        sio: socketio.Client,
        frame_data: np.array,
        sample_rate: int,
        rms_amplitude: int,
        signal_frequency_content: zip,
        start_time
        ):

    time_elapsed = time.perf_counter() - start_time

    frame_length = len(frame_data)
    # get second half of frame_data, as between two main loops, half of the data is duplicated
    plot_data = frame_data[frame_length//2:]
    plot_data_length = len(plot_data)
    time_list = time_elapsed + np.array(range(plot_data_length))/(sample_rate)

    plot_sample_rate = plot_data_length / config.update_interval

    if plot_sample_rate > config.plot_points_per_second:
        slice_every_n = int(plot_sample_rate / config.plot_points_per_second)
        plot_data = plot_data[1::slice_every_n]
        time_list = time_list[1::slice_every_n]

    data_dict = {
        "frame": plot_data.tolist(),
        "frame_time": time_list.tolist(),
        "rms_amplitude": rms_amplitude,
        "rms_sample_time": time_elapsed,
        "frequency_magnitude": list(signal_frequency_content),
    }

    print(list(signal_frequency_content))

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

    if not config.use_live_data:
        sample_rate, wav_signal = wav_data_reader.read_wav_file(config)
    else:
        sample_rate = config.sample_rate
        wav_signal = None
        com_port = config.com_port
        baud_rate = config.baud_rate
        nsp_reader.initialize_serial(com_port=com_port, baud_rate=baud_rate)

    # stft = Short-Time Fourier Transform. See https://brianmcfee.net/dstbook-site/content/ch09-stft/STFT.html for docs
    # frame length is the samples we are executing the FFT on
    # hop length is the number of samples between each FFT
    stft_hop_length = int(sample_rate * config.update_interval)  # sample
    stft_frame_length = 2 * stft_hop_length  # samples

    i = 0  # initialise loop iteration

    start_time = time.perf_counter()
    start_loop_time = time.perf_counter()

    # filters
    notch_frequencies = [config.grid_frequency * i for i in range(1, 8)]

    while True:
        # print(f"Time since last loop = {time.perf_counter() - start_loop_time:.4f} seconds")
        start_loop_time = time.perf_counter()

        if i < stft_frame_length:
            # wait until we have enough samples for stft
            i += stft_hop_length
            continue

        frame = get_signal_frame(
            config=config,
            i=i,
            stft_frame_length=stft_frame_length,
            wav_signal=wav_signal,
            )

        # Notch and bandpass filtering
        filtered_frame = process_data.apply_grid_noise_notch_filters(
            signal_in=frame,
            notch_frequencies=notch_frequencies
            )

        filtered_frame = process_data.apply_bandpass_filters(
            signal_in=filtered_frame,
            sample_rate=sample_rate
            )

        signal_frequency_content = process_data.apply_stft(
            signal=filtered_frame,
            sample_rate=sample_rate,
            )
        
        print(signal_frequency_content)

        # Get power within the band pass filter
        rms_amplitude = np.sqrt(np.mean(filtered_frame**2))
        # print(rms_amplitude)

        if not calibrate_mode:
            play_notes.play_notes(
                config=config,
                rms_amplitude=rms_amplitude,
                resting_amplitude=resting_amplitude,
                max_amplitude=max_amplitude,
            )

        # emit data if running via backend server
        if from_backend:
            emit_data(
                config=config,
                sio=sio,
                frame_data=frame,
                sample_rate=sample_rate,
                rms_amplitude=rms_amplitude,
                signal_frequency_content=signal_frequency_content,
                start_time=start_time
                )
        
        # emit_data(
        #     config=config,
        #     sio=sio,
        #     frame_data=frame,
        #     sample_rate=sample_rate,
        #     rms_amplitude=rms_amplitude,
        #     signal_frequency_content=signal_frequency_content,
        #     start_time=start_time
        #     )

        end_loop_time = time.perf_counter()
        loop_time = end_loop_time - start_loop_time
        # print(f"Loop time: {loop_time:.4f} seconds")

        # sleep for additional data, take into account loop processing time
        if loop_time < config.update_interval:
            # print(f"Sleeping for {config.update_interval - loop_time:.4f} seconds")
            time.sleep(config.update_interval - loop_time)

        i += stft_hop_length


def print_intro_text():
    with open("app/utils/terminal_intro.txt", "r") as f:
        intro_text = f.read()

    print(intro_text)
    time.sleep(1)


def start_main_from_backend(sio: socketio.Client):

    config = Config()
    print_intro_text()
    main(config=config, from_backend=True, sio=sio)


if __name__ == "__main__":

    config = Config()
    print_intro_text()
    main(config=config)
