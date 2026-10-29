import os
import re
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Event Loop Fix ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle

# Web Server for Render
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

# --- Bot Credentials ---
API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"
TARGET_CHANNEL = -1004308752538

bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# আপনার পছন্দের ক্যাপশন ফরম্যাট
def clean_caption(text):
    footer = "⌲ @PhProMod\nShare It With Your Friends 👥"
    if not text:
        return footer
    
    # অন্যের সব লিংক ও ওয়েবসাইট রিমুভ
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    # অন্যের @username রিমুভ
    text = re.sub(r'@\w+', '', text)
    # আগের কোনো Share লেখা থাকলে তা রিমুভ
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)
    
    clean_text = text.strip()
    return f"{clean_text}\n\n{footer}"

# ফাইলের আসল নাম রেখে শেষে @PhProMod যোগ করার ফাংশন
def clean_filename(original_name):
    if not original_name:
        original_name = "app.apk"
        
    base, ext = os.path.splitext(original_name)
    
    # অন্যের @username এবং ব্র্যাকেট রিমুভ
    base_clean = re.sub(r'@\w+', '', base)
    base_clean = re.sub(r'\[.*?\]|\(.*?\)', '', base_clean)
    
    # নামের শেষের অপ্রয়োজনীয় ড্যাশ (-) বা স্পেস বাদ দেওয়া
    base_clean = re.sub(r'[\s\-_]+$', '', base_clean).strip()
    base_clean = " ".join(base_clean.split())
    
    if not base_clean:
        base_clean = "File"
        
    # আসল নামের শেষে আপনার নাম যোগ হবে: App name @PhProMod.apk
    return f"{base_clean} @PhProMod{ext}"

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

async def main():
    await bot.start()
    print(">>> 24/7 Cloud Bot is LIVE and Running! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
