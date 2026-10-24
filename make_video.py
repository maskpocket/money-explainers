"""Make one money-explainer video: topic -> script (Gemini) -> voice (edge-tts) -> slides (Pillow) -> mp4 (ffmpeg)."""
import asyncio, json, os, subprocess, sys, textwrap
import edge_tts, requests
from captions import captions
from speech import speakable
from PIL import Image, ImageDraw, ImageFont

MODE = (sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].strip() else os.environ.get("MODE", "long")).lower()
SHORT = MODE == "short"
W, H = (1080, 1920) if SHORT else (1920, 1080)
BRAND = "Fricomind"
VOICE = os.environ.get("VOICE", "en-US-ChristopherNeural")
GROQ_MODELS = [os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"), "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
HUMAN = (" Write exactly like a real person talking to a friend: contractions, short sentences, an occasional question, natural spoken rhythm."
         " Never use the words delve, landscape, crucial, navigate, unlock, journey, game-changer, or phrases like in todays world or lets dive in."
         " Write every number as digits (like $3,000 or 5%); the narrator will say them aloud. The keyword must be something a camera can film"
         " that matches the scene (like piggy bank coins, person counting cash, laptop budget spreadsheet), never abstract or an animal unless the topic is that animal.")
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
    err = None
    for m in GROQ_MODELS:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
                json={"model": m, "messages": [{"role": "user", "content": p}]}, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            err = e; print("groq model", m, "failed:", e)
    raise err

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
    p = (PROMPT_SHORT if SHORT else PROMPT).format(topic=topic) + HUMAN
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
    pos = []
    im = Image.new("RGBA", (W, H), BG + (165,) if overlay else BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 24, H], fill=ACCENT)
    y = 420 if SHORT else 170
    for line in textwrap.wrap(heading, 13 if SHORT else 28):
        d.text((100 if SHORT else 140, y), line, font=font(92 if SHORT else 96, True), fill=INK); y += 112 if SHORT else 120
    y += 50
    for b in bullets:
        bx = 100 if SHORT else 140; sz = 52 if SHORT else 46; pos.append((bx + sz // 2, y + (86 if SHORT else 78) // 2 - 4, sz))
        d.ellipse([bx, pos[-1][1] - sz // 2, bx + sz, pos[-1][1] + sz // 2], outline=ACCENT, width=5)
        for i, line in enumerate(textwrap.wrap(b, 20 if SHORT else 42)):
            d.text((bx + sz + 28, y), line, font=font(64 if SHORT else 58), fill=INK); y += 86 if SHORT else 78
        y += 26
    d.text((100 if SHORT else 140, 90 if SHORT else 60), BRAND, font=font(44, True), fill=ACCENT)
    if not SHORT: d.rectangle([140, H - 90, 140 + int((W - 280) * n / total), H - 80], fill=ACCENT)
    im.convert("RGBA" if overlay else "RGB").save(path)
    return pos

def tick(path, x, y, sz):
    """Transparent full-frame overlay holding one filled green circle with a white check."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = sz // 2
    d.ellipse([x - r, y - r, x + r, y + r], fill=ACCENT)
    d.line([(x - r * .45, y), (x - r * .1, y + r * .38), (x + r * .5, y - r * .38)], fill=(255, 255, 255), width=max(6, sz // 8), joint="curve")
    im.save(path)

USED_CLIPS = set()

def stock(keyword, path):
    """Download one Pixabay stock clip for the keyword. Returns the path, or None if nothing usable."""
    try:
        r = requests.get("https://pixabay.com/api/videos/", params={"key": os.environ["PIXABAY_API_KEY"], "q": keyword,
            "safesearch": "true", "per_page": 12}, timeout=30)
        r.raise_for_status()
        for h in r.json().get("hits", []):
            v = h["videos"].get("medium") or h["videos"].get("small")
            if v and v.get("url") and v["url"] not in USED_CLIPS:
                USED_CLIPS.add(v["url"])
                open(path, "wb").write(requests.get(v["url"], timeout=120).content)
                return path
    except Exception as e:
        print("stock failed for", keyword, ":", e)
    return None

def thumb(title, topic):
    """1280x720 thumbnail: big bold title on the brand background."""
    im = Image.new("RGB", (1280, 720), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 40, 720], fill=ACCENT); d.text((90, 70), BRAND.upper(), font=font(52, True), fill=ACCENT)
    t = title.replace("#shorts", "").strip(); y = 190
    for line in textwrap.wrap(t, 18)[:4]:
        d.text((90, y), line, font=font(104, True), fill=INK); y += 125
    im.save(f"{OUT}/thumb.jpg", quality=90)

def run(*a): subprocess.run(a, check=True, capture_output=True)

async def voice(text, path):
    """Save the narration and return [(start_s, end_s, word)] from the speech engine's word timings."""
    words = []
    with open(path, "wb") as f:
        async for ch in edge_tts.Communicate(speakable(text), VOICE, rate="-4%", pitch="-6Hz", boundary="WordBoundary").stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7; words.append((st, st + ch["duration"] / 1e7, ch["text"]))
    return words

AREAS = ["budgeting", "saving", "debt", "credit scores", "banking", "investing basics", "stocks and ETFs", "inflation and prices",
         "taxes", "retirement", "insurance", "scams and fraud", "money mindset", "wealth habits of rich people", "money mindset", "building wealth from nothing", "money habits and psychology", "side income", "housing costs",
         "student money", "family money", "big purchases", "emergency planning", "financial history and myths"]

def _words(s): return set(w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) > 3)

def pick_topic():
    """Ask the AI for fresh topics, skip anything close to one already used, record the pick in used_topics.txt."""
    used = [l.strip() for l in open("used_topics.txt", encoding="utf-8") if l.strip()] if os.path.exists("used_topics.txt") else []
    area = AREAS[int(os.environ.get("GITHUB_RUN_NUMBER", "0")) % len(AREAS)]
    recent = "\n".join(used[-60:])
    p = (f'Suggest 25 different YouTube video topics for beginners about personal finance and a money-minded, wealth-building mindset, focused on: {area}. '
         f'Each is a short plain title (4-10 words), specific and not generic. Do NOT repeat or closely resemble these:\n{recent}\n'
         'Return ONLY a JSON array of strings.')
    for fn in (_groq, _cloudflare):
        try:
            raw = fn(p); ideas = json.loads(raw[raw.index('['):raw.rindex(']') + 1])
            for t in ideas:
                w = _words(t)
                if w and all(len(w & _words(u)) / len(w | _words(u)) < 0.6 for u in used):
                    open("used_topics.txt", "a", encoding="utf-8").write(t.strip() + "\n"); return t.strip()
        except Exception as e:
            print("topic ideas failed:", e)
    fall = [l.strip() for l in open("topics.txt") if l.strip()]
    return fall[int(os.environ.get("GITHUB_RUN_NUMBER", "0")) % len(fall)]

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else pick_topic()
    os.makedirs(OUT, exist_ok=True)
    s = script(topic); sc = s["scenes"]
    sc.append({"heading": BRAND, "bullets": ["General education only.", "Not personal financial advice."],
               "narration": "General education only, not financial advice."})
    clips = []
    for i, c in enumerate(sc):
        img, aud, clip = f"{OUT}/s{i}.png", f"{OUT}/s{i}.mp3", f"{OUT}/s{i}.mp4"
        words = asyncio.run(voice(c["narration"], aud)); ass = f"{OUT}/s{i}.ass"
        if SHORT: captions(words, ass, W, H)
        bg = stock(c["keyword"], f"{OUT}/s{i}_bg.mp4") if c.get("keyword") and os.environ.get("PIXABAY_API_KEY") else None
        pos = slide(img, c["heading"], c["bullets"], i + 1, len(sc), overlay=bool(bg))
        n = len(pos); ticks = []
        for k, (x, y, sz) in enumerate(pos):
            tp = f"{OUT}/s{i}_t{k}.png"; tick(tp, x, y, sz)
            idx = min(len(words) - 1, int(len(words) * (k + 1) / (n + 1))) if words else 0
            ticks.append((tp, words[idx][1] if words else 1.0))
        ins = ["-stream_loop", "-1", "-i", bg] if bg else ["-f", "lavfi", "-i", f"color=c=0x0d1b2a:s={W}x{H}:r=24"]
        ins += ["-loop", "1", "-i", img, "-i", aud]
        for tp, _ in ticks: ins += ["-loop", "1", "-i", tp]
        f = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=24[v0];[v0][1:v]overlay=0:0:shortest=1[v1]"
        last = "v1"
        for k, (_, t0) in enumerate(ticks):
            f += f";[{last}][{3 + k}:v]overlay=0:0:enable='gte(t,{t0:.2f})':shortest=1[v{k + 2}]"; last = f"v{k + 2}"
        f += f";[{last}]{'ass=' + ass if SHORT else 'null'}[o]"
        run("ffmpeg", "-y", *ins, "-filter_complex", f, "-map", "[o]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "24", "-c:a", "aac", "-b:a", "160k", "-shortest", clip)
        clips.append(clip)
    open(f"{OUT}/list.txt", "w").write("".join(f"file '{os.path.basename(c)}'\n" for c in clips))
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}/raw.mp4")
    # background music bed (generated, so no licensing)
    import music; music.make(f"{OUT}/music.wav")
    dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{OUT}/raw.mp4"]).decode().strip()
    run("ffmpeg", "-y", "-i", f"{OUT}/raw.mp4", "-stream_loop", "-1", "-i", f"{OUT}/music.wav", "-filter_complex",
        "[1:a]volume=0.4[m];[0:a][m]amix=inputs=2:weights=1 0.5:duration=first:normalize=0,alimiter=limit=0.95[o]",
        "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", dur, f"{OUT}/video.mp4")
    thumb(s["title"], topic)
    json.dump({"title": s["title"], "description": s["description"] + "\n\nGeneral education only, not personal financial advice.",
               "tags": s["tags"], "mode": MODE}, open(f"{OUT}/meta.json", "w"), indent=2)
    print("Done:", s["title"])

main()
