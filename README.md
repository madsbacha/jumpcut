# jumpcut
Remove all silence from a video

## Usage
The file is meant to be used as a cli tool. You have to install the following packages:
```
python -m pip install soundfile argparse webrtcvad
```

### Example
Following will produce `out.mp4`
```
python jumpcut.py -i video.mp4
```

Here is the output of the help command:
```
> python jumpcut.py --help

usage: jumpcut.py [-h] [-video VIDEO] [-output OUTPUT] [-fps FPS] [-halfres] [-audio_limit AUDIO_LIMIT]
                  [-section_padding SECTION_PADDING] [-min_spacing MIN_SPACING] [-audio AUDIO] [-dry] [-print]
                  [-save SAVE] [-overwrite] [-vad_aggr VAD_AGGR]

optional arguments:
  -h, --help            show this help message and exit
  -video VIDEO, -i VIDEO
                        The location of the input video (default: video.mp4)
  -output OUTPUT, -o OUTPUT
                        The location of the output video (default: out.mp4)
  -fps FPS              Frame rate of the output video (default: 15)
  -halfres              If present the output video will be half resolution
  -audio_limit AUDIO_LIMIT
                        The threshold at which point the audio is removed (default: 0.01)
  -section_padding SECTION_PADDING
                        A multiple of one second to add to the beginning and end of each cut (default: 0.25)
  -min_spacing MIN_SPACING
                        The minimum length between each cut (default: 1.5)
  -audio AUDIO          The program needs an audiofile to process where to cut. This specifies what audio file to
                        process. Leave blank for automatic creation of said file. If the file does not exist, it will
                        be created.
  -dry                  Do not run the final ffmpeg command
  -print                Print the final ffmpeg command
  -save SAVE            Save the final ffmpeg command to the specified file
  -overwrite            Tell ffmpeg to overwrite output file if it already exists.
  -vad_aggr VAD_AGGR    The aggressiveness mode for filtering out speech, using py-webrtcvad.
```

