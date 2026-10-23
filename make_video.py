"""Make one money-explainer video: topic -> script (Gemini) -> voice (edge-tts) -> slides (Pillow) -> mp4 (ffmpeg)."""
import asyncio, json, os, subprocess, sys, textwrap
import edge_tts, requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
VOICE = os.environ.get("VOICE", "en-US-AriaNeural")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
CF_MODEL = os.environ.get("CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
OUT = "out"
BG, INK, ACCENT = (13, 27, 42), (240, 244, 248), (46, 204, 113)

PROMPT = """Write a 4-5 minute YouTube explainer for adults about: "{topic}".
Audience: beginners, English speakers worldwide. Tone: calm, clear, friendly, no hype, no get-rich promises.
Use plain words, one concrete example with numbers, and end with one action the viewer can take today.
General education only, not personal financial advice.
Return ONLY JSON: {{"title": str (under 70 chars), "description": str, "tags": [str],
"scenes": [{{"heading": str (max 6 words), "bullets": [str, max 3, each max 9 words], "narration": str (40-70 words)}}]}}
Use 9 to 12 scenes."""

def _groq(p):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": p}],
              "response_format": {"type": "json_object"}}, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _cloudflare(p):
    acct = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{CF_MODEL}",
        headers={"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"]},
        json={"messages": [{"role": "user", "content": p}], "max_tokens": 4096,
              "response_format": {"type": "json_object"}}, timeout=180)
    r.raise_for_status()
    res = r.json()["result"]["response"]
    return res if isinstance(res, str) else json.dumps(res)

def script(topic):
    p = PROMPT.format(topic=topic)
    for name, fn in (("groq", _groq), ("cloudflare", _cloudflare)):
        try:
            s = json.loads(fn(p))
            if len(s.get("scenes", [])) >= 6:
                print("script by", name); return s
            print(name, "returned too few scenes")
        except Exception as e:
            print(name, "failed:", e)
    sys.exit("No AI provider produced a usable script")

def font(size, bold=False):
    for p in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
              f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def slide(path, heading, bullets, n, total):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 24, H], fill=ACCENT)
    y = 170
    for line in textwrap.wrap(heading, 28):
        d.text((140, y), line, font=font(96, True), fill=INK); y += 120
    y += 50
    for b in bullets:
        for i, line in enumerate(textwrap.wrap(b, 44)):
            d.text((140, y), ("•  " if i == 0 else "    ") + line, font=font(58), fill=INK); y += 78
        y += 26
    d.rectangle([140, H - 90, 140 + int((W - 280) * n / total), H - 80], fill=ACCENT)
    im.save(path)

def run(*a): subprocess.run(a, check=True, capture_output=True)

async def voice(text, path):
    await edge_tts.Communicate(text, VOICE, rate="-4%").save(path)

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else open("topics.txt").readline().strip()
    os.makedirs(OUT, exist_ok=True)
    s = script(topic); sc = s["scenes"]
    sc.append({"heading": "Thanks for watching", "bullets": ["General education only.", "Not personal financial advice."],
               "narration": "This video is general education and not personal financial advice. Thanks for watching."})
    clips = []
    for i, c in enumerate(sc):
        img, aud, clip = f"{OUT}/s{i}.png", f"{OUT}/s{i}.mp3", f"{OUT}/s{i}.mp4"
        slide(img, c["heading"], c["bullets"], i + 1, len(sc))
        asyncio.run(voice(c["narration"], aud))
        run("ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud, "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "160k", "-shortest", clip)
        clips.append(clip)
    open(f"{OUT}/list.txt", "w").write("".join(f"file '{os.path.basename(c)}'\n" for c in clips))
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}/video.mp4")
    json.dump({"title": s["title"], "description": s["description"] + "\n\nGeneral education only, not personal financial advice.",
               "tags": s["tags"]}, open(f"{OUT}/meta.json", "w"), indent=2)
    print("Done:", s["title"])

main()
