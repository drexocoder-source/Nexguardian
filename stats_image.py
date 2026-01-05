from PIL import Image, ImageDraw, ImageFont
import os

FONT_PATH = "assets/fonts.ttf"

def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def generate_stats_image(users, groups, ping, uptime="0h 0m"):
    width, height = 900, 450
    bg = (10, 10, 10)
    accent = (80, 170, 255)
    white = (240, 240, 240)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    def font(size):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except:
            return ImageFont.load_default()

    title_f = font(52)
    big_f = font(100)
    small_f = font(30)

    # =====================
    # TITLE
    # =====================
    title_text = "NEXORA GUARDIAN"
    tw, th = text_size(draw, title_text, title_f)
    draw.text(((width - tw) // 2, 25), title_text, font=title_f, fill=accent)

    # =====================
    # CIRCLE
    # =====================
    cx, cy, r = width // 2, height // 2 + 10, 130
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=accent, width=7)

    # =====================
    # CENTER NUMBER
    # =====================
    users_text = str(users)
    uw, uh = text_size(draw, users_text, big_f)
    draw.text((cx - uw // 2, cy - uh // 2 - 15), users_text, font=big_f, fill=white)

    label_text = "USERS"
    lw, lh = text_size(draw, label_text, small_f)
    draw.text((cx - lw // 2, cy + uh // 2 - 10), label_text, font=small_f, fill=accent)

    # =====================
    # BOTTOM STATS
    # =====================
    draw.text((110, height - 85), f"👥 Groups: {groups}", font=small_f, fill=white)
    draw.text((350, height - 85), f"⏱ Uptime: {uptime}", font=small_f, fill=white)
    draw.text((620, height - 85), f"📡 Ping: {ping} ms", font=small_f, fill=white)

    path = "stats.png"
    img.save(path)
    return path
