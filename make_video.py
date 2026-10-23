"""Make one money-explainer video: topic -> script (Gemini) -> voice (edge-tts) -> slides (Pillow) -> mp4 (ffmpeg)."""
import asyncio, json, os, subprocess, sys, textwrap
import edge_tts, requests
from PIL import Image, ImageDraw, ImageFont

MODE = (sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].strip() else os.environ.get("MODE", "long")).lower()
SHORT = MODE == "short"
W, H = (1080, 1920) if SHORT else (1920, 1080)
BRAND = "Fricomind"
VOICE = os.environ.get("VOICE", "en-US-AriaNeural")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
CF_MODEL = os.environ.get("CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
OUT = "out"
BG, INK, ACCENT = (13, 27, 42), (240, 244, 248), (46, 204, 113)

PROMPT_SHORT = """Write a 40-50 second YouTube Short for adults about: "{topic}".
Open with a one-line hook that makes people stay. Tone: calm, clear, friendly, no hype, no get-rich promises. One concrete example with numbers, end with one action to take today. General education only.
Return ONLY JSON: {{"title": str (under 60 chars, add #shorts), "description": str, "tags": [str],
"scenes": [{{"keyword": str (1-2 plain words for stock footage), "heading": str (max 5 words), "bullets": [str, max 2, each max 6 words], "narration": str (14-24 words)}}]}}
Use 5 to 6 scenes."""

PROMPT = """Write a 4-5 minute YouTube explainer for adults about: "{topic}".
Audience: beginners, English speakers worldwide. Tone: calm, clear, friendly, no hype, no get-rich promises.
Use plain words, one concrete example with numbers, and end with one action the viewer can take today.
General education only, not personal financial advice.
Return ONLY JSON: {{"title": str (under 70 chars), "description": str, "tags": [str],
"scenes": [{{"keyword": str (1-2 plain English words for stock footage, concrete and visual, e.g. "coins", "calculator", "city"), "heading": str (max 6 words), "bullets": [str, max 3, each max 9 words], "narration": str (40-70 words)}}]}}
Use 9 to 12 scenes."""

def _groq(p):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": p}]}, timeout=120)
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
    p = (PROMPT_SHORT if SHORT else PROMPT).format(topic=topic)
    for name, fn in (("groq", _groq), ("cloudflare", _cloudflare)):
        try:
            raw = fn(p); s = json.loads(raw[raw.index('{'):raw.rindex('}') + 1])
            if len(s.get("scenes", [])) >= (4 if SHORT else 6):
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

def slide(path, heading, bullets, n, total, overlay=False):
    im = Image.new("RGBA", (W, H), BG + (165,) if overlay else BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 24, H], fill=ACCENT)
    y = 420 if SHORT else 170
    for line in textwrap.wrap(heading, 14 if SHORT else 28):
        d.text((100 if SHORT else 140, y), line, font=font(120 if SHORT else 96, True), fill=INK); y += 140 if SHORT else 120
    y += 50
    for b in bullets:
        for i, line in enumerate(textwrap.wrap(b, 22 if SHORT else 44)):
            d.text((100 if SHORT else 140, y), ("•  " if i == 0 else "    ") + line, font=font(64 if SHORT else 58), fill=INK); y += 86 if SHORT else 78
        y += 26
    d.text((100 if SHORT else 140, 90 if SHORT else 60), BRAND, font=font(44, True), fill=ACCENT)
    d.rectangle([140, H - 90, 140 + int((W - 280) * n / total), H - 80], fill=ACCENT)
    im.convert("RGBA" if overlay else "RGB").save(path)

def stock(keyword, path):
    """Download one Pixabay stock clip for the keyword. Returns the path, or None if nothing usable."""
    try:
        r = requests.get("https://pixabay.com/api/videos/", params={"key": os.environ["PIXABAY_API_KEY"], "q": keyword,
            "safesearch": "true", "per_page": 5}, timeout=30)
        r.raise_for_status()
        for h in r.json().get("hits", []):
            v = h["videos"].get("medium") or h["videos"].get("small")
            if v and v.get("url"):
                open(path, "wb").write(requests.get(v["url"], timeout=120).content)
                return path
    except Exception as e:
        print("stock failed for", keyword, ":", e)
    return None

def run(*a): subprocess.run(a, check=True, capture_output=True)

async def voice(text, path):
    """Save the narration and return [(start_s, end_s, word)] from the speech engine's word timings."""
    words = []
    with open(path, "wb") as f:
        async for ch in edge_tts.Communicate(text, VOICE, rate="-4%", boundary="WordBoundary").stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7; words.append((st, st + ch["duration"] / 1e7, ch["text"]))
    return words

def _t(x): return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"

def captions(words, path, per=3):
    """ASS file: three words at a time, big and centred in the lower third, each group shown while it is spoken."""
    head = ("[Script Info]
ScriptType: v4.00+
PlayResX: %d
PlayResY: %d

[V4+ Styles]
"
            "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Outline,Shadow,Alignment,MarginL,MarginR,MarginV
"
            "Style: C,DejaVu Sans,84,&H00FFFFFF,&H00000000,&H80000000,1,6,2,2,80,80,420

"
            "[Events]
Format: Layer,Start,End,Style,Text
") % (W, H)
    ev = []
    for k in range(0, len(words), per):
        g = words[k:k + per]
        end = words[k + per][0] if k + per < len(words) else g[-1][1] + 0.3
        ev.append(f"Dialogue: 0,{_t(g[0][0])},{_t(end)},C," + " ".join(w[2] for w in g).upper() + "
")
    open(path, "w", encoding="utf-8").write(head + "".join(ev))

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else open("topics.txt").readline().strip()
    os.makedirs(OUT, exist_ok=True)
    s = script(topic); sc = s["scenes"]
    sc.append({"heading": "Follow " + BRAND, "bullets": ["General education only.", "Not personal financial advice."],
               "narration": "General education only, not financial advice. Follow Fricomind for more."})
    clips = []
    for i, c in enumerate(sc):
        img, aud, clip = f"{OUT}/s{i}.png", f"{OUT}/s{i}.mp3", f"{OUT}/s{i}.mp4"
        words = asyncio.run(voice(c["narration"], aud)); ass = f"{OUT}/s{i}.ass"
        if SHORT: captions(words, ass)
        vf = f",ass={ass}" if SHORT else ""
        bg = stock(c["keyword"], f"{OUT}/s{i}_bg.mp4") if c.get("keyword") and os.environ.get("PIXABAY_API_KEY") else None
        slide(img, c["heading"], c["bullets"], i + 1, len(sc), overlay=bool(bg))
        if bg:
            run("ffmpeg", "-y", "-stream_loop", "-1", "-i", bg, "-loop", "1", "-i", img, "-i", aud, "-filter_complex",
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=24[v];[v][1:v]overlay=0:0:shortest=1{vf}[o]",
                "-map", "[o]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", clip)
        else:
            run("ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud, "-c:v", "libx264", "-tune", "stillimage",
                "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "160k", "-shortest", clip) if not SHORT else run("ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud, "-vf", f"ass={ass}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "160k", "-shortest", clip)
        clips.append(clip)
    open(f"{OUT}/list.txt", "w").write("".join(f"file '{os.path.basename(c)}'\n" for c in clips))
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}/raw.mp4")
    # soft ambient pad under the voice (generated, so no licensing)
    run("ffmpeg", "-y", "-i", f"{OUT}/raw.mp4", "-filter_complex",
        "sine=f=196[a];sine=f=247[b];sine=f=294[c];[a][b][c]amix=inputs=3:normalize=0,lowpass=f=700,tremolo=f=0.15:d=0.5,volume=0.5[m];"
        "[0:a][m]amix=inputs=2:weights=1 0.07:duration=first:normalize=0[o]", "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", f"{OUT}/video.mp4")
    json.dump({"title": s["title"], "description": s["description"] + "\n\nGeneral education only, not personal financial advice.",
               "tags": s["tags"], "mode": MODE}, open(f"{OUT}/meta.json", "w"), indent=2)
    print("Done:", s["title"])

main()
