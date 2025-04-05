import serial
import numpy as np

def read_raw_nsp_data(com_port, baud_rate):
    ser = serial.Serial(com_port, int(baud_rate))
    inputBufferSize = 4000  # 20000 = 1 second
    ser.timeout = inputBufferSize/20000.0  # set read timeout

    data_ = ser.read(inputBufferSize)
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