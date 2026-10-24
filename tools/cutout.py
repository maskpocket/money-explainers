import os
from rembg import remove
from PIL import Image
os.makedirs("out", exist_ok=True)
remove(Image.open("assets/host.jpg").convert("RGB")).save("out/host_cut.png")
