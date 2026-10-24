import asyncio, sys, os
sys.path.insert(0, ".")
import edge_tts
from PIL import Image
import puppet

TEXT = ("Nineteen years old, and he made his first thousand dollars from his phone. No boss, no office. "
        "Here is exactly how he did it, and how you can start today.")
os.makedirs("out", exist_ok=True)
asyncio.run(edge_tts.Communicate(TEXT, "en-US-ChristopherNeural", rate="-4%", pitch="-6Hz").save("out/line.mp3"))
bg = Image.new("RGB", (1080, 1920), (14, 22, 48))
puppet.render("out/line.mp3", "out/puppet_test.mp4", bg)
os.system("ffmpeg -y -v error -i out/puppet_test.mp4 -vf fps=2,tile=6x3 -frames:v 1 out/sheet.png")
