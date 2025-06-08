## Neuro SpikerBox real-time EMG to audio converter

### Overview
This repository contains Python scripts for reading and processing data from a SpikerBox, a device used for recording Electromyography (EMG) data. Processing includes converting signals to audible sounds.

A frontend is available to view the processed and real-time data streamed from the SpikerBox.

Demo SpikerBox data is included, enabling testing of the app without a SpikerBox.

### Contents

- `app/main.py`: Read and analyse data from the SpikerBox via serial communication; convert to audio
- `app/dash_app/`: Socket.IO server and Dash app enabling data from `app/main.py` to be displayed in a frontend.

### Usage

1. **Configure config.ini**: The key setting to configure to start quickly is `use_live_data`. If `true`, the code will expect data from a conencted SpikerBox. If `false`, demo data from the repository will be used to simulate a SpikerBox connection.

2. (Optional) **Connect the SpikerBox**: Connect via USB. Update `config.ini` with the COM port used. For Mac, use: `ls /dev/tty.usb*` to help identify the COM port. If no SpikerBox is connected, the COM port setting is ignored by the code.

3. **Activete python environment and run**:
- `python app/main.py` for the bare data reading, processing and audio production.
- `python app/dash_app/start_app.py` will start a Socket.IO server and dash app frontend, in addition to the above script. Access the frontend via `http://localhost:8501/`.

### Installation
Using venv and pip:
1. Create a virtual environment e.g. `python -m venv .venv`
2. Activate the environment e.g. `.venv\Scripts\activate`
3. Install the project and it's dependencies. From the project root: `pip install -e .`

---
This project is built upon the core code from [SpikerStream Python repository](https://github.com/PHYS3888/SpikerStream/tree/master/SpikerStream_Python)