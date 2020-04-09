import soundfile as sf
from os import system, path, remove
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import numpy.ma as ma
import argparse


def extract_audio(video_file, audio_file="audio.wav"):
    system(f"ffmpeg -hide_banner -loglevel panic -i {video_file} -vn -acodec pcm_s16le -ar 44100 -ac 1 {audio_file}")


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
    parser = argparse.ArgumentParser()
    parser.add_argument('-video', '-i', default="video.mp4", help='The location of the input video (default: %(default)s)')
    parser.add_argument('-output', '-o', default="out.mp4", help='The location of the output video (default: %(default)s)')
    parser.add_argument('-fps', default=15, help="Frame rate of the output video (default: %(default)s)")
    parser.add_argument('-halfres', action='store_true', help="If present the output video will be half resolution")
    parser.add_argument('-audio_limit', default=0.01, help='The threshold at which point the audio is removed (default: %(default)s)')
    parser.add_argument('-section_padding', default=0.25, help='A multiple of one second to add to the beginning and end of each cut (default: %(default)s)')
    parser.add_argument('-min_spacing', default=1.5, help='The minimum length between each cut (default: %(default)s)')
    parser.add_argument('-audio', default='audio.wav', help='The program needs an audiofile to process where to cut. \
        This specifies what audio file to process. \
        Leave blank for automatic creation of said file. \
        If the file does not exist, it will be created.')
    parser.add_argument('-dry', action='store_true', help='Do not run the final ffmpeg command')
    parser.add_argument('-print', action='store_true', help='Print the final ffmpeg command')
    parser.add_argument('-save', help='Save the final ffmpeg command to the specified file')
    parser.add_argument('-overwrite', action='store_true', help='Tell ffmpeg to overwrite output file if it already exists.')
    args = parser.parse_args()

    audio_file = args.audio
    video_file = args.video
    output_file = args.output
    audio_limit = args.audio_limit
    padding = args.section_padding
    max_section_spacing = args.min_spacing
    dry = args.dry
    fps = args.fps
    halfres = args.halfres
    print_cmd = args.print
    save_cmd = args.save
    overwrite = args.overwrite

    remove_audio_file = False
    if not path.isfile(audio_file) and path.isfile(video_file):
        remove_audio_file = True
        extract_audio(video_file, audio_file)

    data, samplerate = sf.read(audio_file)
    if remove_audio_file:
        remove(audio_file)
    peaks, _ = find_peaks(data, height=0)
    masked_peaks = ma.masked_where(data[peaks] < audio_limit, peaks)
    clumped_masked_peaks = ma.flatnotmasked_contiguous(masked_peaks)

    sections = [[
            (peaks[clumped_masked_peaks[0].start] - samplerate * padding) / samplerate,
            (peaks[clumped_masked_peaks[0].stop - 1] + samplerate * padding) / samplerate
        ]]
    
    if (sections[0][0] < 0):
        sections[0][0] = 0

    for i in range(1, len(clumped_masked_peaks)):
        if peaks[clumped_masked_peaks[i-1].stop - 1] + samplerate * max_section_spacing >= peaks[clumped_masked_peaks[i].start]:
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

    final_audio_name_i = name_i - 1

    out.append(f"[v{hex(name_i - 1)}]fps=fps={fps}[v{hex(name_i)}]")
    name_i += 1

    if halfres:
        out.append(f"[v{hex(name_i - 1)}]scale=w=-2:h=ih/2[v{hex(name_i)}]")
        name_i += 1
    
    cmd = f"ffmpeg -i {video_file} {'-y ' if overwrite else ''}-preset veryfast -filter_complex \"{';'.join(out)}\" -map \"[v{hex(name_i - 1)}]\" -map \"[a{hex(final_audio_name_i)}]\" {output_file}"

    if save_cmd:
        with open(save_cmd, 'w') as f:
            f.write(cmd)

    if print_cmd:
        print(cmd)
    if not dry:
        system(cmd)
