import numpy as np
import scipy
import os

from utils.config import Config
import data_reading.spikerbox_data
import data_reading.wav_data
import plot_data
import process_data
import save_data
import time


def get_signal_frame(
        config: Config,
        i: int,
        stft_frame_length: int,
        stft_hop_length: int,
        signal: list,
        sample_rate: int,
        ):
    """
    TODO - docstring
    """

    if config.use_live_data:
        # read spikerbox data
        # TODO - get frame
        # frame = []
        pass
    else:
        try:
            frame = data_reading.wav_data.extract_window(
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


def main(config: Config, from_backend: bool = False):
    """
    TODO - docstring
    """

    if not config.use_live_data:
        # sample_rate: samples per second
        # data: numpy array
        sample_rate, signal = data_reading.wav_data.read_wav_file(config)
        signal_min = signal.min()
        signal_max = signal.max()

    # stft = Short-Time Fourier Transform. See https://brianmcfee.net/dstbook-site/content/ch09-stft/STFT.html for docs
    # TODO - define appropriate frame length
    # TODO - place frame length in config.ini or calculate appropriate length
    stft_frame_length = 500  # samples
    stft_hop_length = 250  # samples

    hop_time = stft_hop_length / sample_rate  # time between hops in seconds

    i = 0  # initialise loop iteration

    while True:

        print(f"i = {i}")

        if i < stft_frame_length:
            # wait until we have enough samples for stft
            i += stft_hop_length
            continue

        frame = get_signal_frame(
            config=config,
            i=i,
            stft_frame_length=stft_frame_length,
            stft_hop_length=stft_hop_length,
            signal=signal,
            sample_rate=sample_rate
            )

        # process data - apply filters and Fourier Transforms
        # TODO

        # plot data (if stated in config)


        time.sleep(hop_time)
        i += stft_hop_length


def start_main_from_backend():

    print("Starting main() from backend")
    config = Config()
    main(config=config, from_backend=True)


if __name__ == "__main__":

    print("here")
    config = Config()
    main(config=config)
