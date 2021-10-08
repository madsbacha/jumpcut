import collections
import contextlib
import wave

from os import system, path, remove
import argparse
import webrtcvad


def extract_audio(video_file, audio_file="audio.wav"):
    system(f"ffmpeg -hide_banner -loglevel panic -i {video_file} -vn -acodec pcm_s16le -ar 32000 -ac 1 {audio_file}")


def read_wave(path):
    """Reads a .wav file.
    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


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


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.
    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.
    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def get_voice_segments(frames, frame_duration_ms, padding_duration_ms, sample_rate, vad):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_segments = []
    voiced_frames = []
    for frame in frames:
        webrtcvad.valid_rate_and_frame_length(sample_rate, len(frame.bytes))
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        ring_buffer.append((frame, is_speech))

        if not triggered:
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)

            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                ring_buffer.clear()
                voiced_segments.append([voiced_frames[0].timestamp, voiced_frames[-1].timestamp])
                voiced_frames = []
    return voiced_segments


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-video', '-i', default="video.mp4", help='The location of the input video (default: %(default)s)')
    parser.add_argument('-output', '-o', default="out.mp4", help='The location of the output video (default: %(default)s)')
    parser.add_argument('-fps', default=15, help="Frame rate of the output video (default: %(default)s)")
    parser.add_argument('-halfres', action='store_true', help="If present the output video will be half resolution")
    parser.add_argument('-audio', default='audio.wav', help='The program needs an audiofile to process where to cut. \
        This specifies what audio file to process. \
        Leave blank for automatic creation of said file. \
        If the file does not exist, it will be created.')
    parser.add_argument('-dry', action='store_true', help='Do not run the final ffmpeg command')
    parser.add_argument('-print', action='store_true', help='Print the final ffmpeg command')
    parser.add_argument('-save', help='Save the final ffmpeg command to the specified file')
    parser.add_argument('-overwrite', action='store_true', help='Tell ffmpeg to overwrite output file if it already exists.')
    parser.add_argument('-vad_aggr', default=1, help='The aggressiveness mode for filtering out speech, using py-webrtcvad.')
    args = parser.parse_args()

    audio_file = args.audio
    video_file = args.video
    output_file = args.output
    dry = args.dry
    fps = args.fps
    halfres = args.halfres
    print_cmd = args.print
    save_cmd = args.save
    overwrite = args.overwrite
    vad_aggr = int(args.vad_aggr)

    remove_audio_file = False
    if not path.isfile(audio_file) and path.isfile(video_file):
        remove_audio_file = True
        extract_audio(video_file, audio_file)

    data, samplerate = read_wave(audio_file)
    if remove_audio_file:
        remove(audio_file)

    vad = webrtcvad.Vad(vad_aggr)
    frames = list(frame_generator(30, data, samplerate))
    sections = get_voice_segments(frames, 30, 300, samplerate, vad)

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
