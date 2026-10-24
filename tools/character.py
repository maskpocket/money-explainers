"""Generate candidate looks for the Fricomind host character with Cloudflare FLUX (free tier). Saves PNGs to out/chars."""
import base64, os, requests

ACC, TOK = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
BASE = ("3D Pixar-style animated cartoon character, handsome young Black man in a suit, 23 years old, friendly confident smile, expressive eyes, "
        "front-facing, upper body, plain soft light grey studio background, high quality 3D render, smooth skin, sharp details, ")
LOOKS = {
    "s1_fedora_charcoal": "wearing a brown fedora hat and a sharp charcoal grey three-piece business suit, white shirt, burgundy tie, pocket square",
    "s2_flatcap_navy": "wearing a tweed flat cap and a tailored navy blue two-piece suit, light blue shirt, silver tie, gold watch",
    "s3_bowler_black": "wearing a black bowler hat and a classic black suit, crisp white shirt, slim black tie, white pocket square",
    "s4_trilby_tan": "wearing a cream trilby hat and a modern tan beige suit, white shirt open collar, brown leather shoes style, gold cufflinks",
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
