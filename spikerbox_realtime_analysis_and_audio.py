import math
import serial
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram
from scipy import signal
import musicpy as mp
import time


COM_PORT = '/dev/tty.usbserial-DM89ON8K'  # on mac, type ls /dev/tty.usb* to find serial ports
BAUD_RATE = 230400  # Adjust to match the baud rate of your SpikerBox

# Create a serial object
ser = serial.Serial(COM_PORT, BAUD_RATE)
inputBufferSize = 20000  # 20000 = 1 second
ser.timeout = inputBufferSize/20000.0  # set read timeout


def read_spikerbox_data(ser_, inputBufferSize_):
    """
    Read data from the SpikerBox connected to the specified serial port.

    :param ser_: (serial.Serial) The serial port object representing the connection to the SpikerBox.
    :param inputBufferSize_: (int) The size of the buffer used to read data from the serial port.
    :return: out: (list) Data from SpikerBox with each element representing a byte of the data.
    """

    data_ = ser_.read(inputBufferSize_)
    out = [(int(data_[i])) for i in range(0, len(data_))]

    return out


def process_data(data_):
    """
    Processes the raw data stream from SpikerBox by extracting 16-bit samples.
    Each sample is formed by combining two consecutive bytes, where the most significant bit of the first byte is
    cleared, and the second byte occupies the lower 7 bits of the resulting 16-bit sample.

    :param data_: (list) Raw data received from the SpikerBox.
    :return: result: (numpy.ndarray) Array containing the processed 16-bit samples extracted from the raw data.

    """

    data_in = np.array(data_)
    result = []
    i = 1

    while i < len(data_in)-1:
        if data_in[i] > 127:  # Check if the current byte indicates the beginning of a frame of data
            # Extracts one sample from 2 bytes by combining them with bitwise operations
            intout = (np.bitwise_and(data_in[i], 127))*128
            i = i + 1  # Move to the next byte of data
            # add the next byte to the lower 7 bits of 'intout', combining the two bytes to form a 16-bit sample
            intout = intout + data_in[i]  # Combine the two bytes to form a 16-bit sample
            result = np.append(result,  intout)
        i = i + 1  # Move to the next byte of data

    return result


def notch_filters(notch_frequencies, input_signal_):
    """
    Apply notch filters to remove specific frequencies from the input signal (e.g., 60 Hz power line interference)

    :param notch_frequencies: (list) A list of frequencies (in Hz) to be removed from the input signal.
    :param input_signal_: (numpy.ndarray) The input signal to which the notch filters will be applied.
    :return: (numpy.ndarray) The input signal with notch filters applied to remove specified frequencies.
    """
    filtered_signal_ = input_signal_

    # Iterate over each notch frequency
    for f0 in notch_frequencies:
        fs_filter = 10000  # Sampling frequency of the signal
        Q = 30.0  # Quality factor of the notch filter
        b, a = signal.iirnotch(f0, Q, fs_filter)  # coefficients that define the filter transfer function
        filtered_signal_ = signal.filtfilt(b, a, filtered_signal_)

    return filtered_signal_


def rescale_frequency(frequency, min_recorded, max_recorded):
    """
    Rescale a frequency from a specified range (participant's baseline) to a new range (c1 to c5 musical range)

    :param frequency: (float) The frequency to be rescaled
    :param min_recorded: (float) Participant's min
    :param max_recorded: (float) Participant's max
    :return new_frequency: (float) The rescaled frequency
    """
    c1_frequency = 32.7
    c5_frequency = 523.2
    # Calculate the number of full tones between the starting and ending frequencies in both scales
    recorded_frequency_range = max_recorded - min_recorded  # 69 steps
    c1_c5_frequency_range = c5_frequency - c1_frequency  # 490.5 steps
    stretch_factor = c1_c5_frequency_range / recorded_frequency_range

    new_frequency = (frequency - min_recorded) * stretch_factor + c1_frequency

    return new_frequency


def frequency_to_note(freq):
    """
    Convert a frequency (rescaled to musical range) to its corresponding musical note.

    :param freq: (float) The frequency to be converted to a note
    :return note (str) The musical note corresponding to the input frequency
    """
    # Convert frequency to note
    notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    try:
        note_number = 7 * math.log2(freq / 32.7)
    except Exception as e:
        print(freq)
        raise Exception(e)

    note_number = round(note_number)

    note_ = notes[(note_number - 1) % len(notes)]
    octave = (note_number + 1) // len(notes) + 1

    return f"{note_}{octave}"


# choose sound type
instrument = 1

# record_participant_baseline: if False, sound plays & real-time graph is shown
# if True, real-time graph is shown w/out sound. When code is stopped, min and max frequencies are printed
# use these in the next line to "tune" the sound range to the participant
record_participant_baseline = False
participant_min_freq, participant_max_freq = (10, 170)  # input min and max frequencies

# Check if the port was opened successfully
if ser.is_open:
    print(f"Serial port {COM_PORT} opened successfully.")
else:
    print(f"Failed to open serial port {COM_PORT}.")
    exit()  # Exit the script if the port was not opened successfully

all_frequencies = []
try:
    # Read data from the serial port
    while True:

        total_time = 40.0  # time in seconds [[1 s = 20000 buffer size]]
        max_time = 10.0  # time plotted in window [s]
        N_loops = 20000.0/inputBufferSize*total_time

        T_acquire = inputBufferSize/20000.0    # length of time that data is acquired for
        N_max_loops = math.floor(max_time/T_acquire)    # total number of loops to cover desire time window

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)
        plt.ion()
        fig.show()
        fig.canvas.draw()

        k = 0
        while k < N_loops:  # Will end early so can't run forever.
            data = read_spikerbox_data(ser, inputBufferSize)
            data_temp = process_data(data)

            if k <= N_max_loops:
                if k == 0:
                    data_plot = data_temp
                else:
                    data_plot = np.append(data_temp, data_plot)

                t = (min(k+1, N_max_loops))*inputBufferSize/20000.0*np.linspace(0, 1, len(data_plot))

            else:
                data_plot = np.roll(data_plot, len(data_temp))
                data_plot[0:len(data_temp)] = data_temp

            t = (min(k+1, N_max_loops))*inputBufferSize/20000.0*np.linspace(0, 1, len(data_plot))

            ax1.clear()
            ax1.set_xlim(0, 10)
            plt.xlabel('time [s]')
            ax1.plot(t, data_plot)
            fig.canvas.draw()
            plt.draw()
            plt.pause(0.001)
            k += 1

            # get the length of the data_plot array
            length_tot = len(data_plot)
            # average over 5% of the array. np.roll above shifts the read frame of the array
            input_signal = data_plot[0: round(0.05 * length_tot)]

            # filter out specific frequencies (~60 Hz is likely noise from the US grid)
            notch_filter_frequencies = [60.06, 299, 59.8]
            filtered_signal = notch_filters(notch_filter_frequencies, input_signal_=input_signal)

            # Fast Fourier Transform
            sample_rate = 10000
            f, t, Sxx = spectrogram(filtered_signal, fs=sample_rate, nperseg=len(filtered_signal))
            # find the index of the maximum amplitude frequency & get the dominant frequency
            dominant_freq_index = np.argmax(Sxx, axis=0)
            dominant_freq = f[dominant_freq_index][0]

            # Choice between record baseline mode or game mode (play sounds)
            if record_participant_baseline:
                # Frequencies higher than 500 are likely to be noise from touching electrodes.
                # No muscle flexing outputs f=~4579 Hz. Most likely averaging & fft artefact
                if dominant_freq < 500:
                    all_frequencies.append(dominant_freq)
                rescaled_freq = ""
                note = ""

            else:
                # only continue if the dominant frequency from fft is between participant's min and max
                if participant_min_freq < dominant_freq < participant_max_freq:

                    # rescale to nicer sound frequency scale (c1 - c5)
                    rescaled_freq = rescale_frequency(
                        dominant_freq,
                        min_recorded=participant_min_freq,
                        max_recorded=participant_max_freq
                    )

                    # convert to note e.g., C1 = 32.7 Hz
                    note = frequency_to_note(rescaled_freq)
                    # play the note
                    mp.play(mp.N(note), instrument=instrument)

                else:
                    time.sleep(0.5)
                    rescaled_freq = ""
                    note = ""

            print(f"Dominant, rescaled, note: {dominant_freq, rescaled_freq, note}")


except KeyboardInterrupt:
    # Close the serial port when the program is interrupted
    ser.close()
    print("Serial port closed.")
    if all_frequencies:
        # in record baseline mode this will output participant's min and max
        print(min(all_frequencies), max(all_frequencies))
    else:
        print("all_frequencies list is empty! Game mode on?")
