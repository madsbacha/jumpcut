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

    data, samplerate = sf.read('audio.wav')
    peaks, _ = find_peaks(data, height=0)
    audio_limit = 0.01
    padding = 0.25

    masked_peaks = ma.masked_where(data[peaks] < audio_limit, peaks)

    clumped_masked_peaks = ma.flatnotmasked_contiguous(masked_peaks)

    sections = [[
            (peaks[clumped_masked_peaks[0].start] - samplerate * padding) / samplerate,
            (peaks[clumped_masked_peaks[0].stop - 1] + samplerate * padding) / samplerate
        ]]
    
    if (sections[0][0] < 0):
        sections[0][0] = 0

    for i in range(1, len(clumped_masked_peaks)):
        if peaks[clumped_masked_peaks[i-1].stop - 1] + samplerate * (padding * 2) >= peaks[clumped_masked_peaks[i].start]:
            sections[len(sections) - 1][1] = (peaks[clumped_masked_peaks[i].stop - 1] + samplerate * padding) / samplerate
        else:
            sections.append([
                (peaks[clumped_masked_peaks[i].start] - samplerate * padding) / samplerate,
                (peaks[clumped_masked_peaks[i].stop] + samplerate * padding) / samplerate
            ])

    out = []
    for i, section in enumerate(sections):
        out.append(trim(sections[i][0], sections[i][1], hex(i)))

    name_i = len(sections)
    out.append(concat(
        hex(0),
        hex(1),
        hex(name_i)
    ))
    name_i += 1

    for i in range(2, len(sections)):
        out.append(concat(
            hex(name_i - 1),
            hex(i),
            hex(name_i)
        ))
        name_i += 1
    name_i -= 1

    cmd = f"ffmpeg -i video.mp4 -y -filter_complex \"{';'.join(out)}\" -map \"[v{hex(name_i)}]\" -map \"[a{hex(name_i)}]\" out.mp4"

    # with open('cmd.txt', 'w') as f:
    #     f.write(cmd)

    # print(cmd)

    system(cmd)
