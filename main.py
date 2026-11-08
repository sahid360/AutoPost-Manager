import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto
)

# ইউজারদের текущ QR স্টেট (টেক্সট, কালার, টাইটেল)
USER_QR_DATA = {}

# কালার কোড ম্যাপ
COLOR_PALETTE = {
    "blue": "#0284c7",
    "green": "#16a34a",
    "purple": "#9333ea",
    "red": "#dc2626",
    "black": "#000000"
}

# এক সিরিয়ালে ৫টি কালার ও নিচে Add Name বাটন
def get_qr_keyboard():
    return InlineKeyboardMarkup([
        # Row 1: এক সিরিয়ালে ৫টি কালার
        [
            InlineKeyboardButton("🔵 Blue", callback_data="col_blue"),
            InlineKeyboardButton("🟢 Green", callback_data="col_green"),
            InlineKeyboardButton("🟣 Purple", callback_data="col_purple"),
            InlineKeyboardButton("🔴 Red", callback_data="col_red"),
            InlineKeyboardButton("⚫ Black", callback_data="col_black")
        ],
        # Row 2: Add Name বাটন নিচে
        [
            InlineKeyboardButton("🏷 Add Name / Title", callback_data="add_qr_name")
        ]
    ])

# QR কোড তৈরি করার ইঞ্জিন (বড় নামের ফন্ট সহ)
def generate_custom_qr(data_text, color_name="black", title_text=""):
    fill_hex = COLOR_PALETTE.get(color_name, "#000000")

    # 1. Base QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=fill_hex, back_color="white").convert("RGB")

    # 2. নাম বড় করে যুক্ত করার জন্য ক্যানভাস তৈরি
    if title_text:
        title_text = title_text.strip()
        padding_top = 70  # বড় ফন্টের জন্য উপরের ফাঁকা জায়গা
        total_width = qr_img.width
        total_height = qr_img.height + padding_top

        final_img = Image.new("RGB", (total_width, total_height), "white")
        final_img.paste(qr_img, (0, padding_top))

        draw = ImageDraw.Draw(final_img)
        
        # বড় ফন্ট সেটআপ (সিস্টেম ফন্ট অথবা ডিফল্ট)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()

        # নাম মাঝখানে বসানো (Center aligned)
        bbox = draw.textbbox((0, 0), title_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = max(10, (total_width - text_w) // 2)
        text_y = 20

        draw.text((text_x, text_y), title_text, fill=fill_hex, font=font)
        output_path = f"qr_{color_name}.png"
        final_img.save(output_path)
        return output_path
    else:
        output_path = f"qr_{color_name}.png"
        qr_img.save(output_path)
        return output_path

# যখন ইউজার লিংক বা লেখা পাঠাবে (QR তৈরির জন্য)
@bot.on_message(filters.command("qr") & filters.private)
async def qr_create_cmd(client, message):
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if not text:
        await message.reply_text("👉 Usage: `/qr your-link-or-text`")
        return

    uid = str(message.from_user.id)
    USER_QR_DATA[uid] = {
        "text": text,
        "color": "black",
        "title": ""
    }

    qr_path = generate_custom_qr(text, color_name="black")
    await message.reply_photo(
        photo=qr_path,
        caption="✨ **Your Custom QR Code**\nSelect a color or add a name below:",
        reply_markup=get_qr_keyboard()
    )
    if os.path.exists(qr_path):
        os.remove(qr_path)

# বাটন ক্লিক হ্যান্ডলার (ইন-প্লেস ছবি আপডেট)
@bot.on_callback_query(filters.regex(r"^(col_|add_qr_name)"))
async def qr_button_click(client, cb):
    uid = str(cb.from_user.id)
    data = USER_QR_DATA.get(uid)

    if not data:
        await cb.answer("⚠️ Session expired! Send `/qr your-text` again.", show_alert=True)
        return

    # ১. কালার পরিবর্তনের বাটন চাপলে
    if cb.data.startswith("col_"):
        new_color = cb.data.replace("col_", "")
        data["color"] = new_color
        await cb.answer(f"Color: {new_color.capitalize()}")

        # নতুন কালার দিয়ে ছবি তৈরি
        new_qr_path = generate_custom_qr(data["text"], color_name=new_color, title_text=data["title"])

        # আগের ছবি রিপ্লেস করে নতুন ছবি সেট করা
        try:
            await cb.edit_message_media(
                media=InputMediaPhoto(
                    media=new_qr_path,
                    caption=f"✨ **Color Updated: {new_color.capitalize()}**" + (f"\n🏷 Name: **{data['title']}**" if data['title'] else "")
                ),
                reply_markup=get_qr_keyboard()
            )
        except Exception as e:
            pass
        finally:
            if os.path.exists(new_qr_path):
                os.remove(new_qr_path)

    # ২. Add Name বাটন চাপলে
    elif cb.data == "add_qr_name":
        await cb.answer()
        # স্টেট সংরক্ষণ করে নাম চাইতে বলা
        USER_STEPS[uid] = "WAIT_QR_TITLE"
        await cb.message.reply_text("🏷 **Send the Title / Name you want on your QR code:**")
