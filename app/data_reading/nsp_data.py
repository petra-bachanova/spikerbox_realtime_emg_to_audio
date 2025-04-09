import serial
import numpy as np
from app.utils.config import Config

ser = None


def initialize_serial(config: Config, com_port: str, baud_rate: int):
    """
    Initializes the serial connection to the SpikerBox device.
    """
    global ser
    if ser is None or not ser.is_open:
        ser = serial.Serial(com_port, int(baud_rate))
        # timeout == 0 for Non-blocking mode
        # ser.read() will return immediately with whatever data is available
        ser.timeout = 0


def read_raw_nsp_data(flush_buffer=False):
    """
    Reads raw data from the SpikerBox device over the serial connection
    """
    global ser

    if flush_buffer:
        ser.reset_input_buffer()  # Clear any backlog

    inputBufferSize = 4000
    data_ = ser.read(inputBufferSize)
    out = [(int(data_[i])) for i in range(0, len(data_))]

    return out


def process_data(data):
    """
    Processes the raw data stream from SpikerBox by extracting 16-bit samples.
    Each sample is formed by combining two consecutive bytes, where the most significant bit of the first byte is
    cleared, and the second byte occupies the lower 7 bits of the resulting 16-bit sample.

    :param data: (list) Raw data received from the SpikerBox.
    :return: result: (numpy.ndarray) Array containing the processed 16-bit samples extracted from the raw data.
    """

    data_in = np.array(data)
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
