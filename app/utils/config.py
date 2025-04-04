import configparser


class Config():
    """
    TODO - docstring
    """

    def __init__(self):

        config = configparser.ConfigParser()
        config.read("config.ini")

        print(config.sections())

        self.use_live_data = config.getboolean("DEFAULT", "use_live_data")
        self.wav_file_dir = config.get("DEFAULT", "wav_file_dir")
        self.wav_file = config.get("DEFAULT", "wav_file")
