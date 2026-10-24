"""Talking cartoon host: the mouth, blink and bounce follow the loudness of the voice."""
import subprocess, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FPS = 30
MOUTH = (520, 612)
EYES = ((415, 440), (610, 437))
SKIN = (96, 52, 36)


def loudness(audio):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int(len(a) / 16000 * FPS) + 1
    r = np.array([np.sqrt(np.mean(a[int(i * 16000 / FPS):int((i + 1) * 16000 / FPS)] ** 2) + 1e-9) for i in range(n)])
    r = r / (np.percentile(r, 95) + 1e-6)
    out, v = [], 0.0
    for x in np.clip(r, 0, 1):
        v += (x - v) * (0.6 if x > v else 0.35)
        out.append(v)
    return out


def face(base, open_, blink, bounce):
    im = base.copy()
    d = ImageDraw.Draw(im, "RGBA")
    if open_ > 0.08:
        w, h = 52 + 38 * open_, 8 + 52 * open_
        x, y = MOUTH[0], MOUTH[1] + h * 0.15
        d.ellipse([x - w - 6, y - h - 6, x + w + 6, y + h + 6], fill=(150, 70, 75, 255))
        d.ellipse([x - w, y - h, x + w, y + h], fill=(55, 12, 20, 255))
        d.ellipse([x - w * .55, y + h * .25, x + w * .55, y + h * .95], fill=(190, 80, 90, 255))
        d.rectangle([x - w * .7, y - h * .95, x + w * .7, y - h * .45], fill=(245, 245, 240, 255))
        d.ellipse([x - w, y - h, x + w, y + h], outline=(150, 70, 75, 255), width=7)
    if blink:
        for ex, ey in EYES:
            d.ellipse([ex - 62, ey - 34, ex + 62, ey + 34], fill=SKIN + (255,))
            d.arc([ex - 52, ey - 16, ex + 52, ey + 16], 10, 170, fill=(20, 8, 6, 255), width=6)
    s = 1 + 0.012 * bounce
    W = base.width
    im = im.resize((int(W * s),) * 2, Image.BICUBIC)
    o = (im.width - W) // 2
    return im.crop((o, o + int(bounce * -6), o + W, o + int(bounce * -6) + W))


def render(audio, out, bg, W=1080, H=1920, face_w=1080):
    """bg: PIL image (W x H) the host stands on. Writes an mp4 with the audio."""
    base = Image.open("assets/host.jpg").convert("RGB")
    lev = loudness(audio)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", audio, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    nxt, blink_left = random.randint(60, 120), 0
    for i, v in enumerate(lev):
        if blink_left: blink_left -= 1
        elif i >= nxt: blink_left, nxt = 4, i + random.randint(70, 140)
        f = face(base, v, blink_left > 0, v).resize((face_w, face_w), Image.LANCZOS)
        fr = bg.copy(); fr.paste(f, ((W - face_w) // 2, H - face_w - 60))
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
