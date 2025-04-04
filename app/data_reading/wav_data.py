from scipy.io import wavfile
import numpy as np
import os

from utils.config import Config


def read_wav_file(config: Config) -> tuple:
    """
    TODO - finish docstring
    """

    wav_file = os.path.join(config.wav_file_dir, config.wav_file)
    sample_rate, data = wavfile.read(wav_file)

    return sample_rate, data


def extract_window(signal, sample_rate, i, frame_length):
    """
    TODO - docstring
    """

    # slice the frame
    frame = signal[i: i + frame_length]

    # check if length of frame is as expected
    # if not, we have reached the end of the signal
    if len(frame) < frame_length:
        raise IndexError

    return frame


# def extract_dominant_frequency(wav_file, window_size=1):
#     sample_rate, data = wavfile.read(wav_file)
#     samples_per_window = int(window_size * sample_rate)  # number of samples in each time window
#     num_windows = len(data) // samples_per_window

#     dominant_freqs = []
#     for i in range(num_windows):
#         # get data segment for current window
#         window_data = data[i * samples_per_window: (i + 1) * samples_per_window]
#         # calculate spectrogram
#         f, t, Sxx = spectrogram(window_data, fs=sample_rate, nperseg=samples_per_window)
#         # find the index of the maximum amplitude frequency & get the dominant frequency
#         dominant_freq_index = np.argmax(Sxx, axis=0)
#         dominant_freq = f[dominant_freq_index][0]
#         dominant_freqs.append(dominant_freq)

#     return dominant_freqs


# def freq_to_note(f):
#     notes_ = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']

#     note_number = 12 * math.log2(f / 440) + 49
#     note_number = round(note_number)

#     note_ = (note_number - 1) % len(notes_)
#     note_ = notes_[note_]

#     octave = (note_number + 8) // len(notes_)

#     return f"{note_}{octave}"


# # Example usage:
# file = 'wav files/Elis 2.wav'
# dominant_frequencies = extract_dominant_frequency(file)

# # plot_df = pd.DataFrame({"freq": dominant_frequencies, "time": range(len(dominant_frequencies))})
# # sns.lineplot(data=plot_df, x="time", y="freq")

# notes = []
# for freq in dominant_frequencies:
#     if freq < 40:
#         notes.append(mp.rest(1/2))
#     else:
#         notes.append(freq_to_note(freq))

# # note_melody = ', '.join(notes)
# melody = mp.chord(notes, interval=[1/4]*(len(notes)-notes.count(mp.rest(1/2))))
# drum_ex = mp.drum('K, H, S, H, K;H, K;H, S, H, r:5')
# mp.play(mp.P([melody, drum_ex.notes], [1, 1], channels=[0, 9]))
# # mp.play does not wait for song to play, so add sleep time to allow for this before the script ends.
# time.sleep(60)  # tweak as desired
