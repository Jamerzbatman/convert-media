# convert-media

A simple script that scans movie directories and converts incompatible files using ffmpeg.

## Usage

```bash
python app.py [--copy-audio] [--audio-bitrate 320k]
```

- `--copy-audio`: Preserve existing audio streams when already in a supported format (`aac` or `ac3`).
- `--audio-bitrate`: Bitrate to use when re-encoding audio (defaults to `160k`).

The script continuously monitors the configured directories and converts files as needed.
