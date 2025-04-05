import numpy as np
from scipy import signal


def apply_notch_filters(signal_in, notch_frequencies: list):
    """
    Apply notch filters to remove specific frequencies from the input signal (e.g., 60 Hz power line interference)

    :param notch_frequencies: (list) A list of frequencies (in Hz) to be removed from the input signal.
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


def apply_low_pass_filter(frame):
    """
    TODO - docstring
    """
    pass


def apply_high_pass_filter(frame):
    """
    TODO - docstring
    """
    pass


def apply_windowing(frame):
    """
    TODO - docstring
    """
    pass


def apply_stft():
    """
    TODO docstring
    """
    pass
