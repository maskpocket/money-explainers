"""Upload out/video.mp4 to the Fricomind Facebook Page using out/meta.json."""
import json, os, sys
import requests

def main():
    meta = json.load(open("out/meta.json"))
    desc = (meta["title"] + "\n\n" + meta["description"])[:4900]
    published = os.environ.get("FB_PUBLISHED", "false") == "true"
    r = requests.post(f"https://graph.facebook.com/v21.0/{os.environ['FB_PAGE_ID']}/videos",
                      data={"access_token": os.environ["FB_PAGE_TOKEN"], "title": meta["title"][:100],
                            "description": desc, "published": "true" if published else "false"},
                      files={"source": open("out/video.mp4", "rb")}, timeout=900)
    if r.status_code != 200:
        sys.exit(f"Facebook upload failed: {r.status_code} {r.text[:500]}")
    print("Facebook video:", r.json().get("id"), "published:", published)

main()
