import configparser


class Config():
    """
    Configuration class to read and store settings from a config file.
    """

    def __init__(self):

        config = configparser.ConfigParser()
        config.read("config.ini")

        self.update_interval = config.getfloat("DEFAULT", "update_interval_seconds")
        self.use_live_data = config.getboolean("DEFAULT", "use_live_data")
        self.wav_file_dir = config.get("DEFAULT", "wav_file_dir")
        self.wav_file = config.get("DEFAULT", "wav_file")
        self.play_sounds = config.getboolean("DEFAULT", "play_sounds")

        self.com_port = config.get("NSP", "com_port")
        self.baud_rate = config.getint("NSP", "baud_rate")
        self.sample_rate = config.getint("NSP", "sample_rate")

        self.plot_points_per_second = config.getint("UI", "plot_samples_per_second")
        self.plot_time_span = config.getfloat("UI", "plot_last_n_seconds")

        self.grid_frequency = config.getint("FILTERS", "grid_frequency")
