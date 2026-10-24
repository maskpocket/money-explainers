"""List free talking-face / video Spaces on Hugging Face and print their API so we can call them."""
import os, asyncio
from huggingface_hub import HfApi
from gradio_client import Client

tok = os.environ.get("HF_TOKEN") or None
print("token set:", bool(tok))
api = HfApi(token=tok)
seen = []
for q in ["sadtalker", "musetalk", "latentsync", "hallo", "talking head", "ltx-video", "wan2.1 image to video", "liveportrait"]:
    try:
        for s in api.list_spaces(search=q, sort="likes", limit=4):
            if s.id not in seen and s.sdk == "gradio":
                seen.append(s.id); print(q, "->", s.id, s.likes, s.runtime.stage if s.runtime else "")
    except Exception as e:
        print("search fail", q, e)
for sid in ["vinthony/SadTalker","fffiloni/LatentSync","multimodalart/MoDA-fast-talking-head","Skywork/skyreels-a1-talking-head","fffiloni/tts-hallo-talking-portrait","KlingTeam/LivePortrait","Lightricks/ltx-video-distilled","MarkoVidrih/image-to-talking-head"]:
    print("\n=====", sid)
    try:
        c = Client(sid, token=tok, verbose=False)
        c.view_api(print_info=True, return_format=None)
    except Exception as e:
        print("unusable:", str(e)[:200])
