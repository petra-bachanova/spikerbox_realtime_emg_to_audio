import configparser


class Config():
    """
    Configuration class to read and store settings from a config file.
    """

    def __init__(self):
        """Load runtime settings from config.ini into typed attributes."""

        config = configparser.ConfigParser()
        config.read("config.ini")

        self.update_interval = config.getfloat("DEFAULT", "update_interval_seconds")
        self.use_live_data = config.getboolean("DEFAULT", "use_live_data")
        self.wav_file_dir = config.get("DEFAULT", "wav_file_dir")
        self.wav_file = config.get("DEFAULT", "wav_file")
        self.play_sounds = config.getboolean("DEFAULT", "play_sounds")
        # initial range (lower->upper) of RMS values, between which notes will be played
        self.init_lower_rms_audio_val = config.getint("DEFAULT", "init_lower_rms_audio_val")
        self.init_upper_rms_audio_val = config.getint("DEFAULT", "init_upper_rms_audio_val")
        self.audio_min_emit_period_seconds = config.getfloat(
            "DEFAULT",
            "audio_min_emit_period_seconds",
            fallback=0.4,
        )
        self.audio_note_duration_seconds = config.getfloat(
            "DEFAULT",
            "audio_note_duration_seconds",
            fallback=0.45,
        )
        self.audio_pitch_change_threshold_semitones = config.getint(
            "DEFAULT",
            "audio_pitch_change_threshold_semitones",
            fallback=0,
        )

        self.com_port = config.get("NSP", "com_port")
        self.baud_rate = config.getint("NSP", "baud_rate")
        self.sample_rate = config.getint("NSP", "sample_rate")

        self.plot_points_per_second = config.getint("UI", "plot_samples_per_second")
        self.plot_time_span = config.getfloat("UI", "plot_last_n_seconds")
        self.freq_plot_bins = config.getint("UI", "frequency_plot_bins")

        self.grid_frequency = config.getint("FILTERS", "grid_frequency")
        self.bandpass_min = config.getint("FILTERS", "bandpass_min")
        self.bandpass_max = config.getint("FILTERS", "bandpass_max")

        self.save_recording = config.getboolean("SAVE", "save_recording")
        self.max_recording_time = config.getint("SAVE", "max_recording_time")
