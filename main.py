import soundfile as sf
from os import system, path
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import numpy.ma as ma


def extract_audio(video_file, audio_file="audio.wav"):
    system(f"ffmpeg -i {video_file} -vn -acodec pcm_s16le -ar 44100 -ac 2 {audio_file}")


def trim(start, end, name):
    start = round(start, 2)
    end = round(end, 2)
    out = ""
    if start == 0.0:
        out += f"[0:v]trim=duration={end}[v{name}];[0:a]atrim=duration={end}[a{name}]"
    else:
        out += f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{name}];"
        out += f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{name}]"
    return out


def concat(a, b, out):
    return f"[v{a}][v{b}]concat[v{out}];[a{a}][a{b}]concat=v=0:a=1[a{out}]"


if __name__ == '__main__':
    if not path.isfile("audio.wav") and path.isfile("video.mp4"):
        extract_audio("video.mp4", "audio.wav")

    tempdata, samplerate = sf.read('audio.wav')
    data = tempdata[0:int(samplerate*20)]
    peaks, _ = find_peaks(data, height=0)
    audio_limit = 0.01

    masked_peaks = ma.masked_where(data[peaks] > audio_limit, peaks)
    unmasked_peaks = ma.masked_where(data[peaks] < audio_limit, peaks)

    clumped_masked_peaks = ma.flatnotmasked_contiguous(masked_peaks)

    plt.plot(masked_peaks, data[masked_peaks], 'rx')
    plt.plot(unmasked_peaks, data[unmasked_peaks], 'bx')

    filtered_clumps = []
    removed_sections = []

    for clump in clumped_masked_peaks:
        if samplerate / 4 / 1000 < (clump.stop - clump.start):
            filtered_clumps.extend(peaks[clump])
            removed_sections.append([
                peaks[clump.start] / samplerate,
                peaks[clump.stop] / samplerate
            ])

    plt.plot(peaks[clumped_masked_peaks[0]], data[peaks[clumped_masked_peaks[0]]], 'gx')
    # plt.plot(np.zeros_like(peaks), "--", color="gray")
    plt.show()

    max_names = len(removed_sections) + 1 + len(removed_sections) + 1
    out = []
    name_i = 0
    if removed_sections[0][0] > 0.0:
        out.append(trim(0, removed_sections[0][0], hex(name_i)))
        name_i += 1

    for i in range(1, len(removed_sections)):
        out.append(trim(removed_sections[i-1][1], removed_sections[i][0], hex(name_i)))
        name_i += 1

    out.append(trim(
        removed_sections[len(removed_sections) - 1][1],
        len(data) / samplerate,
        hex(name_i)))
    name_i += 1

    out.append(concat(
        hex(0),
        hex(1),
        hex(name_i)
    ))
    name_i += 1
    for i in range(2, len(removed_sections)):
        out.append(concat(
            hex(name_i - 1),
            hex(i),
            hex(name_i)
        ))
        name_i += 1
    out.append(concat(
        hex(name_i - 1),
        hex(len(removed_sections)),
        hex(name_i)
    ))

    seperator = ';'
    cmd = f"ffmpeg -i video.mp4 -y -filter_complex \"{seperator.join(out)}\" -map \"[v{hex(name_i)}]\" -map \"[a{hex(name_i)}]\" out.mp4"

    with open('cmd.txt', 'w') as f:
        f.write(cmd)

    # print(cmd)

    system(cmd)
