from scipy import signal
import scipy.fft
import numpy as np
import plotly.express as px


def apply_grid_noise_notch_filters(signal_in, notch_frequencies: list[int]):
    """
    Apply notch filters to remove specific frequencies from the input signal (e.g., 60 Hz power line interference)

    :param input_signal_: (numpy.ndarray) The input signal to which the notch filters will be applied.
    :return: (numpy.ndarray) The input signal with notch filters applied to remove specified frequencies.
    """

    signal_out = signal_in

    # Iterate over each notch frequency
    for f0 in notch_frequencies:
        fs_filter = 10000  # Sampling frequency of the signal
        Q = 35  # Quality factor of the notch filter
        b, a = signal.iirnotch(f0, Q, fs_filter)  # coefficients that define the filter transfer function
        signal_out = signal.filtfilt(b, a, signal_out)

    return signal_out


def apply_bandpass_filters(signal_in, sample_rate: int):
    """
    Band pass filtering
    TODO: docstring
    """

    b, a = signal.butter(4, [20, 450], 'bandpass', fs=sample_rate)
    signal_out = signal.filtfilt(b, a, signal_in)

    return signal_out


def apply_stft(signal, sample_rate) -> zip:
    """
    TODO docstring
    Returns zipped frequency and magnitude of the signal
    """
    f = scipy.fft.fft(signal)
    freqs = scipy.fft.fftfreq(len(signal), 1/sample_rate)

    # Magnitude - note, this will not reflect actual magnitudes of each frequency component
    # look into scaling if we want to introduce this.
    magnitude = np.abs(f)

    # Take positive frequencies only
    half_N = len(signal) // 2
    freqs = freqs[:half_N]
    magnitude = magnitude[:half_N]

    # fig = px.line(x=freqs, y=magnitude)
    # fig.write_html("freq-magnitude.html")

    return zip(freqs, magnitude)
