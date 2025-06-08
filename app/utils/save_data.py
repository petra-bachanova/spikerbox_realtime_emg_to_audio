""""""
import numpy as np
import os
import pandas as pd
from scipy.io import wavfile


def save_data_to_file(signal_recording: list, sample_rate: int, metadata: dict):

    if not os.path.exists("recordings"):
        os.mkdir("recordings")

    wav_fname = f"recordings/{metadata["file_name"]}.wav"
    metadata_fname = "recordings/metadata.csv"

    # Write to a wav file
    np_data = np.array(signal_recording, dtype=np.int16)
    wavfile.write(wav_fname, sample_rate, np_data)

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

    print(f"Recording and metadata saved to {wav_fname}, {metadata_fname}")