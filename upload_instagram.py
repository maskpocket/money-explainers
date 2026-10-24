"""Post out/video.mp4 as an Instagram Reel on @fricomind using out/meta.json (resumable upload, no public URL needed)."""
import json, os, sys, time
import requests

G = "https://graph.facebook.com/v21.0"

def main():
    meta = json.load(open("out/meta.json"))
    token, ig = os.environ["FB_PAGE_TOKEN"], os.environ["IG_USER_ID"]
    path = "out/video_h.mp4" if os.path.exists("out/video_h.mp4") else "out/video.mp4"
    caption = (meta["title"] + "\n\n" + meta["description"])[:2000]
    r = requests.post(f"{G}/{ig}/media", data={"media_type": "REELS", "upload_type": "resumable",
                      "caption": caption, "access_token": token}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"Instagram container failed: {r.status_code} {r.text[:500]}")
    cid = r.json()["id"]
    data = open(path, "rb").read()
    u = requests.post(f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}", data=data, timeout=900,
                      headers={"Authorization": "OAuth " + token, "offset": "0", "file_size": str(len(data))})
    if u.status_code != 200:
        sys.exit(f"Instagram upload failed: {u.status_code} {u.text[:500]}")
    for _ in range(60):
        s = requests.get(f"{G}/{cid}", params={"fields": "status_code,status", "access_token": token}, timeout=60).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            sys.exit(f"Instagram processing failed: {s}")
        time.sleep(5)
    else:
        sys.exit("Instagram processing timed out")
    p = requests.post(f"{G}/{ig}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60)
    if p.status_code != 200:
        sys.exit(f"Instagram publish failed: {p.status_code} {p.text[:500]}")
    print("Instagram reel:", p.json().get("id"))

main()
