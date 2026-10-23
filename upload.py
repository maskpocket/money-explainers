"""Upload out/video.mp4 to the Fricomind YouTube channel using out/meta.json."""
import json, os, sys
import requests

def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def main():
    meta = json.load(open("out/meta.json"))
    title = meta["title"][:100]
    if meta.get("mode") == "short" and "#shorts" not in title.lower():
        title = (title[:90] + " #shorts")
    desc = meta["description"] + ("\n\n#shorts" if meta.get("mode") == "short" and "#shorts" not in meta["description"].lower() else "")
    body = {"snippet": {"title": title, "description": desc[:4900], "tags": [t.lstrip("#") for t in meta.get("tags", [])][:15],
                        "categoryId": "27"},
            "status": {"privacyStatus": os.environ.get("PRIVACY", "public"), "selfDeclaredMadeForKids": False}}
    h = {"Authorization": "Bearer " + token()}
    data = open("out/video.mp4", "rb").read()
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={**h, "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))},
                      json=body, timeout=60)
    if r.status_code != 200:
        sys.exit(f"Upload start failed: {r.status_code} {r.text[:500]}")
    r = requests.put(r.headers["Location"], data=data, headers={"Content-Type": "video/mp4"}, timeout=600)
    if r.status_code not in (200, 201):
        sys.exit(f"Upload failed: {r.status_code} {r.text[:500]}")
    j = r.json()
    if meta.get("mode") != "short" and os.path.exists("out/thumb.jpg"):
        t = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=" + j["id"],
                          headers={**h, "Content-Type": "image/jpeg"}, data=open("out/thumb.jpg", "rb").read(), timeout=120)
        print("Thumbnail:", t.status_code)
    print("Uploaded:", j["id"], "privacy:", j["status"]["privacyStatus"])

main()
