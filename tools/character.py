"""Generate candidate looks for the Fricomind host character with Cloudflare FLUX (free tier). Saves PNGs to out/chars."""
import base64, os, requests

ACC, TOK = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
BASE = ("3D Pixar-style animated cartoon character, handsome young Black man, 23 years old, friendly confident smile, expressive eyes, "
        "front-facing, upper body, plain soft light grey studio background, high quality 3D render, smooth skin, sharp details, ")
LOOKS = {
    "a_snapback": "black snapback cap, olive bomber jacket, white t-shirt, small gold chain",
    "b_fedora": "stylish brown fedora hat, navy blazer over a cream turtleneck, neat short beard",
    "c_beanie": "mustard beanie, grey hoodie under a denim jacket, round glasses",
    "d_flatcap": "tweed flat cap, burgundy sweater over a collared shirt, smart watch, light stubble",
}
os.makedirs("out/chars", exist_ok=True)
for name, look in LOOKS.items():
    try:
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{ACC}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                          headers={"Authorization": "Bearer " + TOK}, json={"prompt": BASE + look, "steps": 6}, timeout=120)
        r.raise_for_status()
        open(f"out/chars/{name}.jpg", "wb").write(base64.b64decode(r.json()["result"]["image"]))
        print("ok", name)
    except Exception as e:
        print("failed", name, e, getattr(r, "text", "")[:300])
