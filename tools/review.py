"""Review a finished video the way a viewer would: frame contact sheets, a transcript of the audio, loudness, caption check."""
import json, os, re, subprocess, sys, requests

OUT = "out"; R = f"{OUT}/review"; os.makedirs(R, exist_ok=True)
def sh(*a): return subprocess.run(a, capture_output=True, text=True)

dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{OUT}/video.mp4").stdout.strip())
short = json.load(open(f"{OUT}/meta.json")).get("mode") == "short"
step = max(1.0, dur / 24)
sh("ffmpeg", "-y", "-i", f"{OUT}/video.mp4", "-vf", f"fps=1/{step:.2f},scale={'270:480' if short else '480:270'},tile=6x4", "-frames:v", "1", f"{R}/sheet.png")
sh("ffmpeg", "-y", "-ss", "0.6", "-i", f"{OUT}/video.mp4", "-frames:v", "1", f"{R}/first_frame.png")
vol = sh("ffmpeg", "-i", f"{OUT}/video.mp4", "-af", "volumedetect", "-f", "null", "-").stderr
loud = re.findall(r"(mean_volume|max_volume): (-?[\d.]+)", vol)
sh("ffmpeg", "-y", "-i", f"{OUT}/video.mp4", "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", f"{R}/a.mp3")
txt = ""
try:
    r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        files={"file": open(f"{R}/a.mp3", "rb")}, data={"model": "whisper-large-v3-turbo", "response_format": "text"}, timeout=120)
    txt = r.text.strip()
except Exception as e:
    txt = f"(transcription failed: {e})"
script = json.load(open(f"{OUT}/script.json")) if os.path.exists(f"{OUT}/script.json") else {}
with open(f"{R}/report.md", "w", encoding="utf-8") as f:
    f.write(f"duration {dur:.1f}s  short={short}\nloudness {loud}\n\n## Title\n{script.get('title')}\n\n## Script narration\n")
    for i, s in enumerate(script.get("scenes", [])): f.write(f"{i + 1}. [{s.get('keyword')}] {s.get('heading')} :: {s.get('narration')}\n")
    f.write(f"\n## What the audio actually says (speech-to-text)\n{txt}\n")
os.remove(f"{R}/a.mp3")
print(open(f"{R}/report.md", encoding="utf-8").read())
