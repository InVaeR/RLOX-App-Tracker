from PIL import Image

SRC = "assets/images/icons/real-time.png"
DST = "assets/app.ico"

Image.open(SRC).save(DST, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
print(f"{DST} created")
