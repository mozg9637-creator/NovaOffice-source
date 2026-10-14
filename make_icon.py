from PIL import Image, ImageDraw, ImageFont

S = 512
grad = Image.new("RGB", (S, S))
px = grad.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S)
        px[x, y] = (int(75 + 80 * t), int(92 - 15 * t), 255)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=255)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
img.paste(grad, (0, 0), mask)
try:
    font = ImageFont.truetype("arialbd.ttf", 320)
except Exception:
    font = ImageFont.load_default()
ImageDraw.Draw(img).text((S / 2, S / 2), "N", font=font, fill="white", anchor="mm")
img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
