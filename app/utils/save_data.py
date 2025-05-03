""""""
import numpy as np


def save_data(
    id: str,
    data_record: list
    ):

    if data_record:
        data_record = np.array(data_record)
        file = f"recordings/{id}.npy"
        print(f"Saving data to {file}")
        # Save to .npy file
        np.save(file, data_record)
    else:
        print("Save failed; data record is empty")
