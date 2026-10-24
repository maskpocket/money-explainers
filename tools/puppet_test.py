import asyncio, sys, os, io, base64, requests
sys.path.insert(0, ".")
import edge_tts
from PIL import Image
import puppet

TEXT = ("Nineteen years old, and he made his first thousand dollars from his phone. No boss, no office. "
        "Here is exactly how he did it, and how you can start today.")
os.makedirs("out", exist_ok=True)
asyncio.run(edge_tts.Communicate(TEXT, "en-US-ChristopherNeural", rate="-4%", pitch="-6Hz").save("out/line.mp3"))

ACC, TOK = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{ACC}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                  headers={"Authorization": "Bearer " + TOK}, timeout=120,
                  json={"prompt": "modern bright home office desk with laptop and phone, city skyline through the window, warm light, 3D Pixar-style render, no people", "steps": 6})
scene = Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"]))).convert("RGB")
scene.save("out/scene.jpg")


def bg(i, n, W=1080, H=1920):
    z = 1.0 + 0.12 * i / max(n, 1)
    c = scene.crop((int(scene.width / 2 - scene.height * W / H / 2 / z), int(scene.height * (1 - 1 / z) / 2),
                    int(scene.width / 2 + scene.height * W / H / 2 / z), int(scene.height * (1 + 1 / z) / 2)))
    return c.resize((W, H), Image.BICUBIC)


puppet.render("out/line.mp3", "out/puppet_test.mp4", bg)
os.system("ffmpeg -y -v error -i out/puppet_test.mp4 -vf fps=1,scale=270:-1,tile=6x3 -frames:v 1 out/sheet.png")
