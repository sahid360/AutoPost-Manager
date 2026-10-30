import os
import re
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Event Loop Fix for Python 3.11+ ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode

# Web Server for Render Keep-Alive
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive 24/7!")
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheck)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- Credentials ---
API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"
TARGET_CHANNEL = -1004308752538

bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# টেক্সট ফিল্টার ও সুন্দর ফরম্যাটিং ফাংশন
def clean_caption(text):
    footer = "⌲ @PhProMod\nShare It With Your Friends 👥"
    if not text:
        return footer

    # ১. নির্দিষ্ট ইমোজি (⌲, 💫) রিমুভ
    text = text.replace("⌲", "").replace("💫", "")

    # ২. বাংলা লেখা থাকলে তা সম্পূর্ণ রিমুভ
    text = re.sub(r'[\u0980-\u09FF]+', '', text)

    # ৩. লিংক এবং অন্যের @username রিমুভ
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)

    # ৪. পুরোনো শেয়ার বা ক্রেডিট লাইন রিমুভ
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    # ফাঁকা লাইনগুলো গুছিয়ে সাজানো
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return footer

    # প্রথম লাইনকে Bold করা
    first_line = lines[0]
    first_line_clean = re.sub(r'^\*+|\*+$', '', first_line).strip()
    bold_first_line = f"**{first_line_clean}**"

    # বাকি সব লাইন সাজিয়ে প্রথম লাইনের পর এক স্পেস ফাঁকা দেওয়া
    remaining_text = "\n".join(lines[1:])
    if remaining_text:
        formatted_caption = f"{bold_first_line}\n\n{remaining_text}\n\n{footer}"
    else:
        formatted_caption = f"{bold_first_line}\n\n{footer}"

    return formatted_caption

# ফাইলের নাম ঠিক করার ফাংশন
def clean_filename(original_name):
    if not original_name:
        original_name = "app.apk"
    base, ext = os.path.splitext(original_name)
    base_clean = re.sub(r'@\w+', '', base)
    base_clean = re.sub(r'\[.*?\]|\(.*?\)', '', base_clean)
    base_clean = re.sub(r'[\s\-_]+$', '', base_clean).strip()
    base_clean = " ".join(base_clean.split())
    if not base_clean:
        base_clean = "File"
    return f"{base_clean} @PhProMod{ext}"

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Hello! The Smart Formatter Bot is Active.")

@bot.on_message(filters.private)
async def process_forwarded_post(client, message):
    status = await message.reply_text("⏳ Processing and beautifying post...")

    try:
        # ১. ভিডিও
        if message.video:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.video.file_name or "video.mp4")
            await status.edit_text("📥 Downloading video...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading video to your channel...")
            await client.send_video(
                chat_id=TARGET_CHANNEL,
                video=file_path,
                caption=caption,
                file_name=new_name,
                parse_mode=ParseMode.MARKDOWN,
                supports_streaming=True
            )
            if os.path.exists(file_path):
                os.remove(file_path)

        # ২. APK বা ডকুমেন্ট
        elif message.document:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.document.file_name)
            await status.edit_text("📥 Downloading APK/File...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading APK/File to your channel...")
            await client.send_document(
                chat_id=TARGET_CHANNEL,
                document=file_path,
                caption=caption,
                file_name=new_name,
                parse_mode=ParseMode.MARKDOWN
            )
            if os.path.exists(file_path):
                os.remove(file_path)

        # ৩. ছবি
        elif message.photo:
            caption = clean_caption(message.caption)
            await status.edit_text("📤 Posting photo...")
            await client.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=message.photo.file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )

        # ৪. সাধারণ লেখা
        elif message.text:
            text = clean_caption(message.text)
            await status.edit_text("📤 Posting text...")
            await client.send_message(
                chat_id=TARGET_CHANNEL,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )

        await status.edit_text("✅ Successfully formatted & posted to channel!")

    except Exception as e:
        await status.edit_text(f"❌ Failed: {str(e)}")

async def main():
    await bot.start()
    print(">>> Bot is running! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
