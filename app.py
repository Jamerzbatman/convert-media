import os
import subprocess
import json
import re
from pathlib import Path
import requests
import time
import platform

# Determine platform-safe paths
if platform.system() == "Windows":
    Movie = "M:"
    TvShows = "T:"
else:
    Movie = "/Movies"
    TvShows = "/Shows"

# Allowed formats for Roku
ALLOWED_VIDEO_CODEC = "h264"
ALLOWED_AUDIO_CODECS = {"aac", "ac3"}
ALLOWED_CONTAINERS = {"mp4", "mkv"}

# Conversion settings
FFMPEG_VIDEO_CODEC = "libx264"
FFMPEG_AUDIO_CODEC = "aac"
CRF = "23"

# Plex settings
PLEX_URL_BASE = "http://192.168.1.173:32400"
PLEX_TOKEN = "u8njFiC5nc75yzDNsvP_"

def trigger_plex_scan(library_section_id):
    url = f"{PLEX_URL_BASE}/library/sections/{library_section_id}/refresh"
    headers = {"X-Plex-Token": PLEX_TOKEN}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("🔄 Plex scan triggered.")
        else:
            print(f"⚠️ Failed to trigger Plex scan. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error triggering Plex scan: {e}")

def get_media_info(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=format_name:stream=index,codec_type,codec_name",
        "-of", "json", file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ ffprobe failed with return code {result.returncode}")
            print(f"stderr: {result.stderr.strip()}")
            return None

        if not result.stdout.strip():
            print("⚠️ ffprobe returned empty stdout")
            return None

        return json.loads(result.stdout)
    except Exception as e:
        print(f"❌ Failed to analyze {file_path}: {e}")
        return None

def is_compatible(info):
    try:
        containers = {c.strip().lower() for c in info["format"]["format_name"].split(',')}
        if not containers & ALLOWED_CONTAINERS:
            return False
        video_ok = False
        audio_ok = False

        for stream in info["streams"]:
            if stream["codec_type"] == "video" and stream["codec_name"] == ALLOWED_VIDEO_CODEC:
                video_ok = True
            elif stream["codec_type"] == "audio" and stream["codec_name"] in ALLOWED_AUDIO_CODECS:
                audio_ok = True

        return video_ok and audio_ok
    except Exception as e:
        print(f"⚠️ Compatibility check failed: {e}")
        return False

def clean_filename(original_name):
    """
    Strips typical scene release junk while keeping important info.
    Example: "The.Show.S01E01.WEBDL-1080p.x264.mkv" -> "The Show S01E01.mp4"
    """
    base = Path(original_name).stem

    # Remove common tags (case-insensitive)
    patterns_to_remove = [
        r'\bWEB[-_. ]?DL\b', r'\bWEBRip\b', r'\bBluRay\b', r'\bHDRip\b',
        r'\bHDTV\b', r'\bDVDRip\b', r'\bProper\b', r'\bRemux\b',
        r'\b1080p\b', r'\b720p\b', r'\b480p\b', r'\b4K\b', r'\bHEVC\b',
        r'\bH\.?264\b', r'\bX264\b', r'\bX265\b', r'\bAAC\b', r'\bAC3\b',
        r'\bDD5\.1\b', r'\bMP3\b', r'\bDTS\b'
    ]
    for pattern in patterns_to_remove:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)

    # Replace dots/underscores/hyphens with spaces
    base = re.sub(r'[\._\-]+', ' ', base)

    # Collapse multiple spaces
    base = re.sub(r'\s{2,}', ' ', base).strip()

    return base + ".mp4"


def convert_file(src_path, info=None):
    if info is None:
        info = get_media_info(src_path)

    parent_dir = os.path.dirname(src_path)
    new_name = clean_filename(os.path.basename(src_path))
    temp_output = os.path.join(parent_dir, "__converted_temp__.mp4")
    final_output = os.path.join(parent_dir, new_name)

    # Determine audio channel count for bitrate selection
    audio_channels = 2
    try:
        if info:
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_channels = int(stream.get("channels", audio_channels))
                    break
    except Exception as e:
        print(f"⚠️ Could not determine channel count: {e}")

    # Adjust bitrate based on number of channels
    audio_bitrate = "160k" if audio_channels <= 2 else "384k"

    # 🔥 Delete temp file if it already exists
    if os.path.exists(temp_output):
        try:
            os.remove(temp_output)
            print(f"🧹 Removed existing temp file: {temp_output}")
        except Exception as e:
            print(f"❌ Could not remove existing temp file: {e}")
            return False

    cmd = [
        "ffmpeg", "-i", src_path,
        "-c:v", FFMPEG_VIDEO_CODEC, "-preset", "medium", "-crf", CRF,
        "-c:a", FFMPEG_AUDIO_CODEC, "-b:a", audio_bitrate,
        "-ac", str(audio_channels),
        "-movflags", "+faststart",
        temp_output
    ]

    try:
        print(f"\n🔁 Converting: {src_path}")
        subprocess.run(cmd, check=True)
        print(f"✅ Converted successfully: {new_name}")
        os.remove(src_path)
        os.replace(temp_output, final_output)
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Conversion failed: {src_path}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return False

def scan_and_convert(directory, library_section_id):
    now = time.time()
    one_hour = 60 * 60

    for root, _, files in os.walk(directory):
        for name in files:
            if not name.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                continue

            full_path = os.path.join(root, name)

            try:
                mtime = os.path.getmtime(full_path)
                if (now - mtime) < one_hour:
                    continue
            except Exception as e:
                print(f"⚠️ Skipping {full_path} due to error checking time: {e}")
                continue

            info = get_media_info(full_path)
            print(full_path, is_compatible(info))
            if info and not is_compatible(info):
                if convert_file(full_path, info):
                    trigger_plex_scan(library_section_id)
                    time.sleep(10)

if __name__ == "__main__":
    while True:
        scan_and_convert(TvShows, 2)
        scan_and_convert(Movie, 1)
        time.sleep(1500)
        print("\n✅ All incompatible files processed.")
 