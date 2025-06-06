# Convert Media

This small utility checks your Movies or TV Shows directories for files that won't play on devices that expect H.264/AAC in an MP4 container. Any incompatible files are transcoded with `ffmpeg` and replaced in place. After conversion the script can ping Plex so your library picks up the new versions automatically.

## Requirements

- **Python 3.11+**
- **ffmpeg/ffprobe** available in your `PATH`
- Python package requirements listed in [`requirements.txt`](requirements.txt)

You can install the Python requirements with:

```bash
pip install -r requirements.txt
```

## Running directly

Edit `app.py` if you need to adjust the paths (`/Movies`, `/Shows` on Linux or `M:`/`T:` on Windows) or change your Plex URL/token. Then simply execute:

```bash
python app.py
```

The script will loop forever, scanning the configured directories every 25 minutes. Converted files are renamed to a cleaned up title and left in the same folder.

## Docker usage

A `Dockerfile` is provided. Build it with:

```bash
docker build -t convert-media .
```

Run the container and mount your media directories:

```bash
docker run --rm \
  -v /path/to/movies:/Movies \
  -v /path/to/shows:/Shows \
  convert-media
```

Inside the container the script runs exactly as above.

## Configuration options

All configuration is done by editing constants at the top of `app.py`:

- `Movie` and `TvShows` – directories to scan
- `ALLOWED_*` constants – codecs and containers considered compatible
- `FFMPEG_*` and `CRF` – conversion parameters
- `PLEX_URL_BASE` and `PLEX_TOKEN` – Plex server details

Save your changes and re-run the script or rebuild the Docker image.
