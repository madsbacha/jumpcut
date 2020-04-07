import soundfile as sf
from math import floor
from os import system, path
import numpy as np
import matplotlib.pyplot as plt

def extract_audio(video_file, audio_file="audio.wav"):
  system(f"ffmpeg -i {video_file} -vn -acodec pcm_s16le -ar 44100 -ac 2 {audio_file}")

def average(data, f, t):
  if f >= t:
    raise Exception('Argument error: f must be smaller than t')
  val = 0
  prev = 0
  for i in range(f, t + 1):
    if prev < abs(data[i]):
      prev = abs(data[i])
    else:
      val += prev
  return val / (t - f + 1)

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

if not path.isfile("audio.wav") and path.isfile("video.mp4"):
  extract_audio("video.mp4", "audio.wav")

info = sf.info('audio.wav')
second_sections = int(info.samplerate / 1024)
blocksize = int(info.samplerate/second_sections)

rms = [np.sqrt(np.mean(block**2)) for block in
       sf.blocks('audio.wav', blocksize=blocksize, overlap=512)]

audio_limit = 0.01

plt.plot(rms)
x=np.linspace(0,len(rms), len(rms))
plt.plot(x, x*0+audio_limit, '-r', label='audio limit')
plt.show()

removed_sections = []

new_section_start = None
new_section_end = None
new_section_count = 0

for i, block in enumerate(rms):
  if block < audio_limit:
    print(block)
    if new_section_count == 0:
      new_section_start = blocksize * i - 1
    new_section_end = blocksize * i
    new_section_count += 1
  elif new_section_count > 0:
    if new_section_count >= (int(second_sections) * 0.75):
      removed_sections.append([new_section_start / info.samplerate, new_section_end / info.samplerate])
    new_section_start = None
    new_section_end = None
    new_section_count = 0

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
  blocksize * len(rms) / info.samplerate,
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
name_i -= 1

cmd = f"ffmpeg -i video.mp4 -filter_complex \"{';'.join(out)}\" -map \"[v{hex(name_i)}]\" -map \"[a{hex(name_i)}]\" out.mp4"

with open('cmd.txt', 'w') as f:
  f.write(cmd)

# print(cmd)

system(cmd)
