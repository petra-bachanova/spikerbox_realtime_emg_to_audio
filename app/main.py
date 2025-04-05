import numpy as np
import scipy
import os
import sys
import socketio


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



def get_signal_frame(
        config: Config,
        i: int,
        stft_frame_length: int,
        signal: list,
        sample_rate: int,
        ):
    """
    TODO - docstring
    """

    if config.use_live_data:
        # read spikerbox data
        com_port = config.com_port
        baud_rate = config.baud_rate
        serial_bytes = nsp_reader.read_raw_nsp_data(com_port=com_port, baud_rate=baud_rate)
        frame = nsp_reader.process_data(serial_bytes)

    else:
        try:
            frame = wav_data_reader.extract_window(
                signal=signal,
                sample_rate=sample_rate,
                i=i,
                frame_length=stft_frame_length
                )
        except IndexError:
            print("Reached end of signal")
            # TODO - this is ok when running outsite of Dash but not appropriate for Dash
            exit()

    return frame


def emit_data(
        sio: socketio.Client,
        frame_data: np.array,
        sample_rate: int,
        rms_amplitude: int
        ):

    global start_time
    current_time = time.time() - start_time

    time_list = current_time + np.array(range(len(frame_data)))/(sample_rate)

    frame_data = frame_data[1::3]
    time_list = time_list[1::3]

    data_dict = {
        "frame": frame_data.tolist(),
        "frame_time": time_list.tolist(),
        "rms_amplitude": rms_amplitude,
        "rms_sample_time": current_time,
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

    global start_time
    start_time = time.time()

    if not config.use_live_data:
        # sample_rate: samples per second
        # data: numpy array
        sample_rate, signal = wav_data_reader.read_wav_file(config)
        signal_min = signal.min()
        signal_max = signal.max()
    else:
        sample_rate = 10000

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
            signal = None

        frame = get_signal_frame(
            config=config,
            i=i,
            stft_frame_length=stft_frame_length,
            stft_hop_length=stft_hop_length,
            signal=signal,
            sample_rate=sample_rate
            )

        # process data - apply filters and Fourier Transforms
        notch_frequencies = [60, 120, 180, 240, 300, 360, 420]
        filtered_frame = process_data.apply_notch_filters(
            signal_in=frame,
            notch_frequencies=notch_frequencies
            )
        # TODO

        # plot data (if stated in config)


        # emit data if running via backend server
        if from_backend and (i % stft_frame_length == 0):
            # i % stft_frame_length == 0 ensures we are not duplicating data in graph
            emit_data(
                sio=sio,
                frame_data=frame,
                sample_rate=sample_rate,
                rms_amplitude=rms_amplitude
                )

        time.sleep(hop_time)  # maybe 0.2 s
        i += stft_hop_length


def start_main_from_backend(sio: socketio.Client):

    print("Starting main() from backend")
    config = Config()
    main(config=config, from_backend=True, sio=sio)


if __name__ == "__main__":

    print("here")
    config = Config()
    main(config=config)
