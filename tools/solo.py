"""One presenter in a cinema, ~3 minute talk: script (Groq) -> FLUX close-up -> voice (edge-tts) -> MoDA talking face in a few long clips -> 1080x1920 mp4 with karaoke captions."""
import asyncio, base64, json, os, subprocess, sys, time
import edge_tts, requests
from gradio_client import Client, handle_file
sys.path.insert(0, ".")
from captions import captions
from speech import speakable

TOPIC = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else "how to get financial help and start making your first money as a young person"
HF = os.environ.get("HF_TOKEN") or None
ACC, TOK = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
VOICE = "en-US-ChristopherNeural"
SHOT = ("3D Pixar-style animated cartoon, close-up head and shoulders portrait of a handsome young Black man, 25 years old, tweed flat cap, navy blue suit, light blue shirt, silver tie, "
        "sitting in a plush red velvet seat inside a luxury cinema, warm golden light, giant glowing screen blurred behind, facing the camera, front-facing, "
        "hands out of frame, mouth closed, confident friendly expression, high quality 3D render, sharp details")
os.makedirs("out/solo", exist_ok=True)


def run(*a): subprocess.run(a, check=True, capture_output=True)
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)


PROMPT = f"""Write a 3 minute talk to camera by KOFI, a 25 year old who started from nothing, speaking to young people in a cinema lobby mood, about: "{TOPIC}".
Total about 430 words, split into exactly 6 parts of 65-80 words each. Part 1 opens with a scroll-stopping line under 12 words. Include one real story with a first name, an age and exact numbers (digits), where to look for help (family, savings groups, small grants, mentors, learning a skill), three simple moves, and a challenge to do today. Last part asks viewers to follow.
Real spoken English, contractions, short sentences, warm and motivating, no jargon, no get-rich promises, no hype words. General education only, not financial advice.
Return ONLY JSON: {{"title": str (under 60 chars, add #shorts), "description": str, "tags": [str], "parts": [str]}}"""


def llm(p):
    for m in ("openai/gpt-oss-120b", "llama-3.3-70b-versatile"):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
                              json={"model": m, "messages": [{"role": "user", "content": p}]}, timeout=120)
            r.raise_for_status(); t = r.json()["choices"][0]["message"]["content"]
            return json.loads(t[t.index("{"):t.rindex("}") + 1])
        except Exception as e:
            print("groq", m, "failed:", e)
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{ACC}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                      headers={"Authorization": "Bearer " + TOK}, json={"messages": [{"role": "user", "content": p}], "max_tokens": 4096, "response_format": {"type": "json_object"}}, timeout=180)
    res = r.json()["result"]["response"]
    return res if isinstance(res, dict) else json.loads(res)


def flux(prompt, path):
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{ACC}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                      headers={"Authorization": "Bearer " + TOK}, json={"prompt": prompt, "steps": 6}, timeout=120)
    r.raise_for_status()
    open(path, "wb").write(base64.b64decode(r.json()["result"]["image"]))


async def tts(text, path):
    words = []
    with open(path, "wb") as f:
        async for ch in edge_tts.Communicate(speakable(text), VOICE, rate="-4%", boundary="WordBoundary").stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7; words.append((st, st + ch["duration"] / 1e7, ch["text"]))
    return words


def talk(wav, i):
    for t in range(3):
        try:
            c = Client("multimodalart/MoDA-fast-talking-head", token=HF, verbose=False)
            r = c.predict(source_image_path=handle_file("out/solo/kofi.jpg"), driving_audio_path=handle_file(wav),
                          emotion_name="Neutral", cfg_scale=1.2, api_name="/generate_motion")
            return r["video"] if isinstance(r, dict) else r
        except Exception as e:
            print("moda try", t, i, str(e)[:200]); time.sleep(20)
    return None


data = llm(PROMPT); parts_txt = data["parts"]; print(data["title"], len(parts_txt), "parts", sum(len(p.split()) for p in parts_txt), "words")
json.dump(data, open("out/solo/script.json", "w"), indent=1)
flux(SHOT, "out/solo/kofi.jpg")

# slow push-in on the still when MoDA is unavailable; blurred backdrop + vignette around the 1080 square clip
FG = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.2[bg];"
      "[b]scale=1080:1080[fg];[bg][fg]overlay=0:260,vignette=PI/5[v]")
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest"]
parts, words_all, t0, fails = [], [], 0.0, 0
for i, txt in enumerate(parts_txt):
    mp3, wav, part = f"out/solo/l{i}.mp3", f"out/solo/l{i}.wav", f"out/solo/p{i}.mp4"
    w = asyncio.run(tts(txt, mp3))
    run("ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "16000", "-ac", "1", wav)
    clip = talk(wav, i)
    if clip:
        run("ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-i", mp3, "-filter_complex", FG, "-map", "[v]", "-map", "1:a", "-r", "30", *ENC, part)
    else:
        fails += 1
        run("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", "out/solo/kofi.jpg", "-i", mp3,
            "-filter_complex", FG, "-map", "[v]", "-map", "1:a", *ENC, part)
    d = dur(part); words_all += [(a + t0, b + t0, x) for a, b, x in w]; t0 += d
    parts.append(part); print("part", i, round(d, 1), "s", "(moda)" if clip else "(still)")

open("out/solo/list.txt", "w").write("".join(f"file 'p{i}.mp4'\n" for i in range(len(parts))))
run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "out/solo/list.txt", "-c", "copy", "out/solo/all.mp4")
captions(words_all, "out/solo/cap.ass", 1080, 1920)
run("ffmpeg", "-y", "-loglevel", "error", "-i", "out/solo/all.mp4", "-vf", "ass=out/solo/cap.ass", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "out/solo.mp4")
print("TOTAL", round(t0, 1), "s;", fails, "parts fell back to still")
run("ffmpeg", "-y", "-loglevel", "error", "-i", "out/solo.mp4", "-vf", "fps=1/10,scale=270:-1,tile=6x3", "-frames:v", "1", "out/solo_sheet.png")
