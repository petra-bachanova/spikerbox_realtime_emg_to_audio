import numpy as np
import socketio
import pandas as pd
import time
from scipy.io import wavfile
from serial.serialutil import SerialException
import os

from app.utils.config import Config
import app.play_notes as play_notes
import app.data_reading.nsp_data as nsp_reader
import app.data_reading.wav_data as wav_data_reader
import app.process_data as process_data
import app.utils.save_data as save_data
import app.utils.com_port_validation as com_port_validation


def handle_hop_data_received_messaging(
        hop_data_received: bool,
        backend_client_running: bool,
        sio: socketio.Client | None,
        last_data_available_bool: bool,
        ) -> bool:
    """
    TODO - docstring
    """

    if not hop_data_received:
        # No hop data has been received
        if not backend_client_running:
            print("No data from Spikerbox")
        else:
            # Check if data availability has changed from last loop. If yes - send message to front end
            if last_data_available_bool:
                sio.emit('data_available_message', {"data": "False"})
                last_data_available_bool = False
    else:
        # Hop data has been received
        if backend_client_running and not last_data_available_bool:
            # Update front end data availibility flag, and update last_data_available_bool
            sio.emit('data_available_message', {"data": "True"})
            last_data_available_bool = True


def sleep_for_loop_interval(config: Config, start_loop_time: float):
    """
    Sleep to achieve the desired total loop duration, taking into account the loop's processing time

    Args:
        config (Config): Configuration object containing desired loop duration
        start_loop_time (float): start time for the loop, used to calculate sleep duration
    """

    end_loop_time = time.perf_counter()
    loop_time = end_loop_time - start_loop_time

    # sleep for additional data, take into account loop processing time
    if loop_time < config.update_interval:
        # print(f"Sleeping for {config.update_interval - loop_time:.4f} seconds")
        time.sleep(config.update_interval - loop_time)


def end_of_file_handler(
    save_data_flag: bool,
    data_record: list
):
    if save_data_flag:
        save_data.save_data(
            id="test",
            data_record=data_record
            )
        save_data_to_file(
            metadata={
                "file_name": "test",
                }
            )


def get_hop_data(
        config: Config,
        i: int,
        stft_hop_length: int,
        wav_signal: list,
        ) -> tuple[np.array, bool]:
    """
    TODO - docstring
    """

    # TODO - see if we can remove this, and
    # instead propagate the indexerror to main to use there.
    # initialise as False
    end_of_data = False

    if config.use_live_data:
        # read spikerbox data
        serial_bytes = nsp_reader.read_raw_nsp_data()
        hop_data = nsp_reader.process_data(serial_bytes)
    else:
        # extract data from local wav file
        try:
            hop_data = wav_data_reader.extract_window(
                wav_signal=wav_signal,
                i=i,
                hop_length=stft_hop_length
                )
        except IndexError:
            hop_data = None
            end_of_data = True

    return hop_data, end_of_data


def emit_data(
        config: Config,
        sio: socketio.Client,
        frame_data: np.array,
        sample_rate: int,
        rms_amplitude: int,
        signal_frequency_content: dict[str, list[float]],
        start_time
        ):

    time_elapsed = time.perf_counter() - start_time

    frame_length = len(frame_data)
    # get second half of frame_data, as between two main loops, half of the data is duplicated
    plot_data = frame_data[frame_length//2:]
    plot_data_length = len(plot_data)
    # conver to int for data transfer efficiency
    plot_data = [int(x) for x in plot_data]
    time_list = time_elapsed + np.array(range(plot_data_length))/(sample_rate)

    plot_sample_rate = plot_data_length / config.update_interval

    if plot_sample_rate > config.plot_points_per_second:
        slice_every_n = int(plot_sample_rate / config.plot_points_per_second)
        plot_data = plot_data[1::slice_every_n]
        time_list = time_list[1::slice_every_n]

    # process frequency and magnitude content
    frequencies = signal_frequency_content["frequencies"]
    magnitudes = signal_frequency_content["magnitudes"]

    # calculate the bins for the frequency plot
    # add 10% to the low bandpass filter cut-off frequency
    max_frequency = int(config.bandpass_max * 1.1)
    freq_bins = np.linspace(0, max_frequency, config.freq_plot_bins + 1)

    # Digitize x-values to find which bin they fall into
    bin_indices = np.digitize(frequencies, freq_bins) - 1   # subtract 1 to make 0-based index
    bin_indices = np.clip(bin_indices, 0, len(freq_bins) - 2)  # ensure stays within valid range

    # Build dataframe and group
    df = pd.DataFrame({
        'x': frequencies,
        'y': magnitudes,
        'bin': bin_indices
    })

    # Group by bin and compute mean y and bin center as x
    grouped = df.groupby('bin').agg({
        'y': 'mean'
    }).reset_index()
    bin_labels = (freq_bins[:-1] + freq_bins[1:]) / 2  # bin centers
    grouped['x'] = bin_labels[grouped['bin']]
    min_max_freq = [grouped["x"].min(), grouped["x"].max()]
    # grouped = grouped[["x", "y"]].astype(int)
    grouped = grouped[["y"]].astype(int)
    freq_magnitude_data_dict = grouped.to_dict(orient='list')  # Convert DataFrame to dict

    data_dict = {
        "frame": plot_data,
        "frame_time": time_list.tolist(),
        "rms_amplitude": rms_amplitude,
        "rms_sample_time": time_elapsed,
        "frequency_magnitude": freq_magnitude_data_dict,
        "frequency_magnitude_freq_min_max": min_max_freq,
    }

    try:
        sio.emit('signal_frame_update', {"data": data_dict})
    except Exception as e:
        print(f"Error sending data: {e}")


# Define the event handler function
def update_save_data_flag(flag: bool):
    global save_data_flag

    if flag["active"]:
        save_data_flag = True
    else:
        save_data_flag = False


def update_global_min_max_rms_for_audio(min_max_rms: list[int]):
    global rms_to_audio_range
    rms_to_audio_range = min_max_rms


def save_data_to_file(metadata: dict):
    global data_record
    global sample_rate

    f_name = f"recordings/{metadata["file_name"]}.wav"
    metadata_fname = "recordings/metadata.csv"

    # Write to a wav file
    np_data = np.array(data_record, dtype=np.int16)
    wavfile.write(f_name, sample_rate, np_data)

    # Save the metadata to recordings/metadata.csv
    # New row as a dictionary
    new_row = metadata

    # Convert new_row to a DataFrame
    new_df = pd.DataFrame([new_row])

    # If file exists, read it and append new row
    if os.path.isfile(metadata_fname):
        existing_df = pd.read_csv(metadata_fname)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Save to CSV (overwrites if file exists)
    combined_df.to_csv(metadata_fname, index=False)

    # Empty the data_record ready for next recording
    data_record = []


def register_sio_events(sio: socketio.Client):
    """
    Register socketio listeners if sio is not None (the front end is in use).
    """
    if sio is not None:  # Skip if socketio client backend / front end is not in use
        @sio.on('save_data')
        def handle_save_data_event(flag: bool):
            update_save_data_flag(flag)

        @sio.on("complete_save_data")
        def handle_complete_save_data_event(metadata: dict):
            save_data_to_file(metadata=metadata)

        @sio.on("min-max-rms-audio-update")
        def handle_update_min_max_rms_audio_event(min_max_rms: list[int]):
            update_global_min_max_rms_for_audio(min_max_rms=min_max_rms)


def print_terminal_intro_text():
    with open("app/utils/terminal_intro.txt", "r") as f:
        intro_text = f.read()
    print(intro_text)
    time.sleep(1)


def main(
        config: Config,
        backend_client_running: bool = False,
        sio: socketio.Client | None = None
        ):
    """
    Runs the main data processing loop, including data reading, signal processing, and audio output.

    Args:
        config (Config): Configuration object containing initial settings.
        backend_client_running (bool): If True, indicates the backend client is already running 
            (e.g. in full app mode with frontend). If False, runs standalone for testing or debugging.
        sio (socketio.Client | None): Socket.IO client for communicating with the frontend. 
            Should be None if backend_client_running is False.

    Returns:
        None
    """

    print_terminal_intro_text()

    # Set up global variables - these are typically global as they are used by socketio funcitons
    # for inputs in the front end to update variables on a 'live' basis in the main() while True loop.

    global save_data_flag
    save_data_flag = config.save_recording

    # initialise list for data recording
    global data_record
    data_record = []

    global sample_rate

    global rms_to_audio_range
    rms_to_audio_range = [config.init_lower_rms_audio_val, config.init_upper_rms_audio_val]

    register_sio_events(sio=sio)

    if not config.use_live_data:
        # Read local wav file upfront
        sample_rate, wav_data = wav_data_reader.read_wav_file(config)
    else:
        # Validate and set up Spikerbox serial port connection
        sample_rate = config.sample_rate
        wav_data = None
        try:
            nsp_reader.initialize_serial(config=config)
        except SerialException as e:
            # Validate - send front end message or raise Exception
            com_ports = com_port_validation.find_com_ports()
            if sio:
                sio.emit('invalid_com_port', {"valid_com_ports": com_ports})
                # TODO - force backend to hang?
                raise Exception(f"{e}\nAvailable COM ports: {com_ports}")
            else:
                raise Exception(f"{e}\nAvailable COM ports: {com_ports}")

    # stft = Short-Time Fourier Transform. See https://brianmcfee.net/dstbook-site/content/ch09-stft/STFT.html for docs
    # frame length is the samples we are executing the FFT on
    # hop length is the number of samples between each FFT
    stft_hop_length = int(sample_rate * config.update_interval)  # samples
    stft_frame_length = 2 * stft_hop_length  # samples

    start_time = time.perf_counter()
    start_loop_time = time.perf_counter()

    # create list of notch frequencies we will apply within loop
    notch_frequencies = [config.grid_frequency * i for i in range(1, 8)]

    # determine the max recording samples we will hold before beginning to overwrite recorded data
    max_recording_len = sample_rate * config.max_recording_time

    # boolean flag, used to determine when to send "end of file" message to front end
    last_data_available_bool = False

    stft_frame = []  # initialise empty frame
    i = 0  # initialise frame counter. Represents how many frames have been processed since the beginning of the loop

    # loop - read and process data, while handling updates from front end, and playing notes
    while True:
        # print(f"Time since last loop = {time.perf_counter() - start_loop_time:.4f} seconds")
        start_loop_time = time.perf_counter()

        # get latest data from NSP, or the next batch of wav file data
        hop_data, end_of_data = get_hop_data(
            config=config,
            i=i,
            stft_hop_length=stft_hop_length,
            wav_signal=wav_data,
            )

        if end_of_data:
            # save data and exit
            end_of_file_handler(
                save_data_flag=save_data_flag,
                data_record=data_record,
            )
            save_data_flag = False

        # Handle no data received
        if hop_data is None or hop_data.size == 0:
            handle_hop_data_received_messaging(
                hop_data_received=False,
                backend_client_running=backend_client_running,
                sio=sio,
                last_data_available_bool=last_data_available_bool
            )
            # sleep until loop duration is reached, and iterate loop
            sleep_for_loop_interval(config=config, start_loop_time=start_loop_time)
            i += stft_hop_length
            continue
        else:
            handle_hop_data_received_messaging(
                hop_data_received=True,
                backend_client_running=backend_client_running,
                sio=sio,
                last_data_available_bool=last_data_available_bool
            )

        # from the latest data (hop_data), create the frame of stft_frame_length used for FFT processing
        if len(stft_frame) >= stft_frame_length:
            # discrard first half of frame, promote second half to what will become the first half (after .extend())
            stft_frame = stft_frame[stft_hop_length:]
        stft_frame.extend(hop_data)  # latest hop data appended to end of the frame

        if len(stft_frame) < stft_frame_length:
            # wait until we have enough samples for stft
            sleep_for_loop_interval(config=config, start_loop_time=start_loop_time)
            i += stft_hop_length
            continue

        # update data_record if we are in save data mode
        if save_data_flag:
            if len(data_record) > max_recording_len:
                # Overwrite the first frame with the current frame
                data_record = data_record[len(hop_data):]
            data_record.extend(hop_data)

        # Notch and bandpass filtering
        filtered_frame = process_data.apply_grid_noise_notch_filters(
            signal_in=stft_frame,
            notch_frequencies=notch_frequencies
            )

        filtered_frame = process_data.apply_bandpass_filters(
            signal_in=filtered_frame,
            sample_rate=sample_rate,
            lower_bandpass_freq=config.bandpass_min,
            upper_bandpass_freq=config.bandpass_max
            )

        # Apply STFT
        signal_frequency_content = process_data.apply_stft(
            signal=filtered_frame,
            sample_rate=sample_rate,
            )

        # Get RMS amplitude
        rms_amplitude = np.sqrt(np.mean(filtered_frame**2))
        # print(rms_amplitude)

        play_notes.play_notes(
            config=config,
            rms_amplitude=rms_amplitude,
            rms_to_audio_range=rms_to_audio_range
        )

        # emit latest data to front end
        if backend_client_running:
            emit_data(
                config=config,
                sio=sio,
                frame_data=stft_frame,
                sample_rate=sample_rate,
                rms_amplitude=rms_amplitude,
                signal_frequency_content=signal_frequency_content,
                start_time=start_time
                )

        sleep_for_loop_interval(config=config, start_loop_time=start_loop_time)
        i += stft_hop_length


def start_main_from_backend(sio: socketio.Client):
    config = Config()
    main(config=config, backend_client_running=True, sio=sio)


if __name__ == "__main__":
    config = Config()
    main(config=config)
