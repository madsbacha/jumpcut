import soundfile as sf
from math import floor
from os import system


data, samplerate = sf.read('audio.wav')

slice_length = int(samplerate)
audio_limit = 0.1

removed_sections = []

def samplerate_to_seconds(samplerate, sample):
  return sample / samplerate

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

def get_section_name(nr, max_nr):
  name = []
  max_characters = ord('z') - ord('a')
  for i in range(floor(max_nr / max_characters) + 1):
    name.append('a')
  for i in range(floor(nr / max_characters) + 1):
    name[i] = 'z'
  name[floor(nr / max_characters)] = str(chr(nr % max_characters + ord('a')))
  return ''.join(name)

def sample_to_filter_params(start, end, name):
  start = round(start, 2)
  end = round(end, 2)
  out = ""
  if start == 0.0:
    out += f"[0:v]trim=duration={end}[{name}v];[0:a]atrim=duration={end}[{name}a]"
  else:
    out += f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[{name}v];"
    out += f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[{name}a]"
  return out

def concat(a, b, out):
  return f"[{a}v][{b}v]concat[{out}v];[{a}a][{b}a]concat=v=0:a=1[{out}a]"

new_section = {
  "start": None,
  "end": None,
  "count": 0
}

i = slice_length
max_length = len(data)
# max_length = samplerate * 30
while i < max_length:
  avg = average(data, i - slice_length, i)
  # print(f"for {i - slice_length} to {i}, ({max_length - i} remaining) average was: {avg:0.5f} below: {avg < audio_limit} found {len(removed_sections)}")
  if avg < audio_limit:
    if new_section["count"] == 0:
      new_section["start"] = i - slice_length
    new_section["end"] = i
    new_section["count"] += 1
  elif new_section["count"] > 0:
    if new_section["count"] > 3:
      removed_sections.append([new_section["start"] / samplerate, new_section["end"] / samplerate])
    new_section["start"] = None
    new_section["end"] = None
    new_section["count"] = 0
  i += slice_length

max_names = len(removed_sections) + 1 + len(removed_sections) + 1
out = []
name_i = 0
if removed_sections[0][0] > 0.0: 
  out.append(sample_to_filter_params(0, removed_sections[0][0], get_section_name(name_i, max_names)))
  name_i += 1

for i in range(1, len(removed_sections)):
  name = get_section_name(name_i, max_names)
  name_i += 1
  out.append(sample_to_filter_params(removed_sections[i-1][1], removed_sections[i][0], name))

out.append(sample_to_filter_params(
  removed_sections[len(removed_sections) - 1][1],
  max_length / samplerate,
  get_section_name(name_i, max_names)))
name_i += 1


out.append(concat(
    get_section_name(0, max_names),
    get_section_name(1, max_names),
    get_section_name(name_i, max_names)
    ))
name_i += 1
for i in range(2, len(removed_sections) + 1):
  out.append(concat(
    get_section_name(name_i - 1, max_names),
    get_section_name(i, max_names),
    get_section_name(name_i, max_names)
    ))
  name_i += 1
name_i -= 1

cmd = f"ffmpeg -i video.mp4 -filter_complex '{';'.join(out)}' -map '[{get_section_name(name_i, max_names)}v]' -map '[{get_section_name(name_i, max_names)}a]' out.mp4"

print(cmd)

system(cmd)
