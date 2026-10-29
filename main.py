import os
import re
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters

# Cloud Server Health Check Web Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")
    def log_message(self, format, *args):
        return

def start_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# Fix for Python 3.10+ event loop in cloud environments
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# --- Bot Credentials ---
API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"

TARGET_CHANNEL = -1004308752538

MY_LINK = "https://t.me/PhProMod"
MY_USERNAME = "@PhProMod"

bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

def clean_caption(text):
    if not text:
        return f"\n\n📢 Join: {MY_LINK}\n👤 Credit: {MY_USERNAME}"
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    clean_text = text.strip()
    return f"{clean_text}\n\n📢 Join: {MY_LINK}\n👤 Credit: {MY_USERNAME}"

def clean_filename(original_name):
    if not original_name:
        original_name = "file"
    name_clean = re.sub(r'@\w+', '', original_name)
    name_clean = re.sub(r'\[.*?\]|\(.*?\)', '', name_clean).strip()
    name_clean = " ".join(name_clean.split())
    return f"[PhProMod] {name_clean}"

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Hello! The 24/7 Cloud Bot is Active and Ready.")

@bot.on_message(filters.private)
async def process_forwarded_post(client, message):
    print("New post received! Processing...")
    status = await message.reply_text("⏳ Processing post, please wait...")

    try:
        # Video
        if message.video:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.video.file_name or "video.mp4")
            await status.edit_text("📥 Downloading video...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading video to your channel...")
            await client.send_video(chat_id=TARGET_CHANNEL, video=file_path, caption=caption, file_name=new_name, supports_streaming=True)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Document / APK / File
        elif message.document:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.document.file_name)
            await status.edit_text("📥 Downloading file...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading file to your channel...")
            await client.send_document(chat_id=TARGET_CHANNEL, document=file_path, caption=caption, file_name=new_name)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Photo
        elif message.photo:
            caption = clean_caption(message.caption)
            await status.edit_text("📤 Posting photo to your channel...")
            await client.send_photo(chat_id=TARGET_CHANNEL, photo=message.photo.file_id, caption=caption)

        # Text
        elif message.text:
            text = clean_caption(message.text)
            await status.edit_text("📤 Posting text to your channel...")
            await client.send_message(chat_id=TARGET_CHANNEL, text=text)

        await status.edit_text("✅ Successfully posted to your channel!")

    except Exception as e:
        await status.edit_text(f"❌ Failed to post: {str(e)}")

print("24/7 Cloud Bot is starting...")
bot.run()
