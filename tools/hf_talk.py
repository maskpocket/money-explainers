"""Make the host talk with a free open-source model on a Hugging Face Space (MoDA first, LatentSync as fallback)."""
import os, asyncio, shutil, subprocess, edge_tts
from gradio_client import Client, handle_file

tok = os.environ.get("HF_TOKEN") or None
os.makedirs("out", exist_ok=True)
LINE = "Nobody is coming to save you. At twenty three, I learned that the hard way. Here is what I did about it."
asyncio.run(edge_tts.Communicate(LINE, "en-US-ChristopherNeural", rate="-4%", pitch="-6Hz").save("out/line.mp3"))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "out/line.mp3", "-ar", "16000", "-ac", "1", "out/line.wav"], check=True)

def moda():
    c = Client("multimodalart/MoDA-fast-talking-head", token=tok, verbose=False)
    r = c.predict(source_image_path=handle_file("assets/host.jpg"), driving_audio_path=handle_file("out/line.wav"),
                  emotion_name="Neutral", cfg_scale=1.2, api_name="/generate_motion")
    return r["video"] if isinstance(r, dict) else r

def latentsync():
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", "assets/host.jpg", "-i", "out/line.wav", "-t", "8",
                    "-r", "25", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", "out/still.mp4"], check=True)
    c = Client("fffiloni/LatentSync", token=tok, verbose=False)
    return c.predict(input_video_path={"video": handle_file("out/still.mp4")}, input_audio_path=handle_file("out/line.wav"),
                     api_name="/generate_lip_sync_video")

for name, fn in (("moda", moda), ("latentsync", latentsync)):
    try:
        p = fn(); p = p["video"] if isinstance(p, dict) else p
        shutil.copy(p, f"out/talk_{name}.mp4"); print("OK", name, p)
    except Exception as e:
        print("FAIL", name, str(e)[:400])
