import os
import re
import asyncio
import threading
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Event Loop Fix ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode

# --- Bot Credentials ---
API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"
FIREBASE_URL = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com/settings.json"

# Default Settings (যদি ফায়ারবেস খালি থাকে)
DEFAULT_SETTINGS = {
    "target_channel": -1004308752538,
    "channel_tag": "@PhProMod",
    "footer_text": "⌲ @PhProMod\nShare It With Your Friends 👥",
    "remove_emojis": "⌲, 💫",
    "remove_bengali": True,
    "bold_first_line": True,
    "admin_pin": "1234" # আপনার ড্যাশবোর্ডের গোপন পাসওয়ার্ড
}

# Settings Fetcher
def get_settings():
    try:
        res = requests.get(FIREBASE_URL, timeout=5)
        if res.status_code == 200 and res.json():
            data = res.json()
            for key, val in DEFAULT_SETTINGS.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception as e:
        print(f"Firebase read error: {e}")
    return DEFAULT_SETTINGS

# Initialize Firebase if empty
try:
    check = requests.get(FIREBASE_URL, timeout=5)
    if not check.json():
        requests.put(FIREBASE_URL, json=DEFAULT_SETTINGS, timeout=5)
except Exception:
    pass

# --- Web Server & Admin Dashboard HTML ---
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Manager Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        label { display: block; margin-top: 15px; font-weight: bold; color: #94a3b8; font-size: 14px; }
        input[type="text"], input[type="password"], textarea { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; margin-top: 6px; }
        textarea { height: 80px; resize: vertical; }
        .checkbox-group { display: flex; align-items: center; margin-top: 15px; gap: 10px; }
        .checkbox-group input { width: 20px; height: 20px; accent-color: #38bdf8; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 14px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 25px; transition: 0.3s; }
        button:hover { background: #0369a1; }
        .status { text-align: center; margin-top: 15px; font-weight: bold; }
        .success { color: #4ade80; }
        .error { color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Bot Admin Panel</h2>
        
        <label>Admin Secret PIN:</label>
        <input type="password" id="pin" placeholder="Enter PIN to save (Default: 1234)">

        <label>Target Channel ID (মাইনাস সহ):</label>
        <input type="text" id="target_channel">

        <label>Channel Suffix Tag (ফাইলের নামের শেষে যা বসবে):</label>
        <input type="text" id="channel_tag">

        <label>Emojis to Remove (কমা দিয়ে লিখুন):</label>
        <input type="text" id="remove_emojis" placeholder="⌲, 💫">

        <label>Custom Footer / Share Text:</label>
        <textarea id="footer_text"></textarea>

        <div class="checkbox-group">
            <input type="checkbox" id="remove_bengali">
            <label style="margin: 0;">বাংলা টেক্সট স্বয়ংক্রিয়ভাবে রিমুভ করুন</label>
        </div>

        <div class="checkbox-group">
            <input type="checkbox" id="bold_first_line">
            <label style="margin: 0;">১ম লাইন Bold (মোটা) রাখুন</label>
        </div>

        <button onclick="saveSettings()">💾 Save Settings</button>
        <div id="status" class="status"></div>
    </div>

    <script>
        const FIREBASE_URL = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com/settings.json";

        async function loadSettings() {
            try {
                const res = await fetch(FIREBASE_URL);
                const data = await res.json();
                if(data) {
                    document.getElementById('target_channel').value = data.target_channel || "";
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('remove_emojis').value = data.remove_emojis || "";
                    document.getElementById('footer_text').value = data.footer_text || "";
                    document.getElementById('remove_bengali').checked = data.remove_bengali !== false;
                    document.getElementById('bold_first_line').checked = data.bold_first_line !== false;
                }
            } catch(e) {
                console.error(e);
            }
        }

        async function saveSettings() {
            const statusDiv = document.getElementById('status');
            const pin = document.getElementById('pin').value;
            
            statusDiv.innerHTML = "Saving...";
            statusDiv.className = "status";

            try {
                const res = await fetch(FIREBASE_URL);
                const currentData = await res.json();
                const actualPin = (currentData && currentData.admin_pin) ? currentData.admin_pin : "1234";

                if(pin !== actualPin) {
                    statusDiv.innerHTML = "❌ Invalid PIN! Default PIN is 1234";
                    statusDiv.className = "status error";
                    return;
                }

                const updatedData = {
                    ...currentData,
                    target_channel: document.getElementById('target_channel').value.trim(),
                    channel_tag: document.getElementById('channel_tag').value.trim(),
                    remove_emojis: document.getElementById('remove_emojis').value,
                    footer_text: document.getElementById('footer_text').value,
                    remove_bengali: document.getElementById('remove_bengali').checked,
                    bold_first_line: document.getElementById('bold_first_line').checked
                };

                await fetch(FIREBASE_URL, {
                    method: 'PUT',
                    body: JSON.stringify(updatedData)
                });

                statusDiv.innerHTML = "✅ Settings saved successfully to Firebase!";
                statusDiv.className = "status success";
            } catch(e) {
                statusDiv.innerHTML = "❌ Error saving: " + e.message;
                statusDiv.className = "status error";
            }
        }
        window.onload = loadSettings;
    </script>
</body>
</html>
"""

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), WebHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- Caption Cleaner with Firebase Settings ---
def clean_caption(text):
    s = get_settings()
    footer = s.get("footer_text", "⌲ @PhProMod\nShare It With Your Friends 👥")
    if not text:
        return footer

    # Emojis remove from Firebase
    emojis_str = s.get("remove_emojis", "")
    for emo in emojis_str.split(","):
        emo = emo.strip()
        if emo:
            text = text.replace(emo, "")

    # Bengali remove
    if s.get("remove_bengali", True):
        text = re.sub(r'[\u0980-\u09FF]+', '', text)

    # Links & @username
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return footer

    # First line Bold
    if s.get("bold_first_line", True):
        first_line = lines[0]
        first_line_clean = re.sub(r'^\*+|\*+$', '', first_line).strip()
        first_line = f"**{first_line_clean}**"
        lines[0] = first_line

    if len(lines) > 1:
        formatted_caption = f"{lines[0]}\n\n" + "\n".join(lines[1:]) + f"\n\n{footer}"
    else:
        formatted_caption = f"{lines[0]}\n\n{footer}"

    return formatted_caption

def clean_filename(original_name):
    s = get_settings()
    tag = s.get("channel_tag", "@PhProMod")
    if not original_name:
        original_name = "app.apk"
    base, ext = os.path.splitext(original_name)
    base_clean = re.sub(r'@\w+', '', base)
    base_clean = re.sub(r'\[.*?\]|\(.*?\)', '', base_clean)
    base_clean = re.sub(r'[\s\-_]+$', '', base_clean).strip()
    base_clean = " ".join(base_clean.split())
    if not base_clean:
        base_clean = "File"
    return f"{base_clean} {tag}{ext}"

bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 Hello! Bot connected with Firebase Realtime Dashboard.")

@bot.on_message(filters.private)
async def process_forwarded_post(client, message):
    s = get_settings()
    target_channel = int(s.get("target_channel", -1004308752538))
    status = await message.reply_text("⏳ Processing post with Firebase rules...")

    try:
        if message.video:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.video.file_name or "video.mp4")
            await status.edit_text("📥 Downloading video...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading video...")
            await client.send_video(chat_id=target_channel, video=file_path, caption=caption, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(file_path):
                os.remove(file_path)

        elif message.document:
            caption = clean_caption(message.caption)
            new_name = clean_filename(message.document.file_name)
            await status.edit_text("📥 Downloading APK/File...")
            file_path = await message.download(file_name=new_name)
            await status.edit_text("📤 Uploading APK/File...")
            await client.send_document(chat_id=target_channel, document=file_path, caption=caption, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(file_path):
                os.remove(file_path)

        elif message.photo:
            caption = clean_caption(message.caption)
            await status.edit_text("📤 Posting photo...")
            await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=caption, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            text = clean_caption(message.text)
            await status.edit_text("📤 Posting text...")
            await client.send_message(chat_id=target_channel, text=text, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Successfully posted using Firebase settings!")

    except Exception as e:
        await status.edit_text(f"❌ Failed: {str(e)}")

async def main():
    await bot.start()
    print(">>> Bot LIVE with Firebase Dashboard! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
