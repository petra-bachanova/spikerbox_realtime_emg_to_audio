from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="spikerbox_realtime_emg_to_audio",
    version="2.0",
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
    description="Real-time SpikerBox EMG to Music Creator",
    author="Petra Bachanova and Elis Jackson",
)
