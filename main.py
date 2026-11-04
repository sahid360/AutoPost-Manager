import os
import re
import asyncio
import threading
import json
from datetime import datetime
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from pyrogram.errors import UserNotParticipant

API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"
FIREBASE_BASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com"
RENDER_URL = "https://autopost-manager-1.onrender.com"

# --- Firebase Helpers ---
def db_get(path):
    try:
        r = requests.get(f"{FIREBASE_BASE}/{path}.json", timeout=5)
        return r.json() or {}
    except:
        return {}

def db_put(path, data):
    try:
        requests.put(f"{FIREBASE_BASE}/{path}.json", json=data, timeout=5)
    except:
        pass

def db_post(path, data):
    try:
        requests.post(f"{FIREBASE_BASE}/{path}.json", json=data, timeout=5)
    except:
        pass

# Global Config Init
g_cfg = db_get("global_config")
if not g_cfg:
    db_put("global_config", {
        "force_channels": "@PhProMod",
        "global_blocked_words": "scam, fraud, 18+, betting",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 1. PURE DARK TELEGRAM MINI APP
# ==========================================
USER_MINIAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Config</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: #090d16;
            --card: #111827;
            --input-bg: #030712;
            --border: #1f2937;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --text: #f9fafb;
            --muted: #9ca3af;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 14px; }
        .card { background: var(--card); border-radius: 14px; padding: 18px; border: 1px solid var(--border); box-shadow: 0 8px 20px rgba(0,0,0,0.6); }
        h3 { margin-top: 0; color: var(--accent); font-size: 17px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        label { display: block; font-size: 13px; color: var(--muted); margin-top: 14px; font-weight: 600; }
        input[type="text"], textarea { width: 100%; padding: 11px; border-radius: 8px; border: 1px solid var(--border); background: var(--input-bg); color: #fff; margin-top: 6px; box-sizing: border-box; font-size: 14px; transition: 0.2s; }
        input:focus, textarea:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 10px var(--accent-glow); }
        textarea { height: 75px; resize: none; }
        .helper-link { font-size: 12px; color: var(--accent); margin-top: 5px; display: block; text-decoration: none; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 13px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 18px; transition: 0.2s; }
        button:hover { background: #0369a1; }
        .alert { text-align: center; margin-top: 12px; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h3>⚡ AutoPost Channel Setup</h3>

        <label>Target Channel ID:</label>
        <input type="text" id="target_channel" placeholder="-1001234567890">
        <a class="helper-link" href="https://t.me/userinfobot" target="_blank">🔍 Don't know Channel ID? Click to open @userinfobot</a>

        <label>Channel Public Username (Optional):</label>
        <input type="text" id="channel_username" placeholder="@MyChannel">

        <label>Channel Category:</label>
        <input type="text" id="channel_category" placeholder="e.g. Mod Apps, Movies, Tech, Anime">

        <label>File Suffix Tag:</label>
        <input type="text" id="channel_tag" placeholder="@MyChannel">

        <label>Languages to Wipe Out (Type names separated by comma):</label>
        <input type="text" id="remove_languages" placeholder="bengali, hindi, arabic, urdu, russian">

        <label>Post Footer / Credits:</label>
        <textarea id="footer_text" placeholder="⌲ @MyChannel&#10;Share with friends 👥"></textarea>

        <button onclick="saveConfig()">💾 Save Settings</button>
        <div id="status_alert" class="alert"></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user = tg.initDataUnsafe?.user || { id: "test_user", first_name: "User" };
        const FIREBASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function init() {
            try {
                const res = await fetch(`${FIREBASE}/users/${user.id}.json`);
                const data = await res.json();
                if(data) {
                    document.getElementById('target_channel').value = data.target_channel || "";
                    document.getElementById('channel_username').value = data.channel_username || "";
                    document.getElementById('channel_category').value = data.channel_category || "";
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('remove_languages').value = data.remove_languages || "bengali";
                    document.getElementById('footer_text').value = data.footer_text || "";
                }
            } catch(e) {}
        }

        async function saveConfig() {
            const al = document.getElementById('status_alert');
            al.style.color = '#38bdf8';
            al.innerText = "Saving settings...";

            const payload = {
                target_channel: document.getElementById('target_channel').value.trim(),
                channel_username: document.getElementById('channel_username').value.trim(),
                channel_category: document.getElementById('channel_category').value.trim() || "General",
                channel_tag: document.getElementById('channel_tag').value.trim(),
                remove_languages: document.getElementById('remove_languages').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                username: user.username || "",
                first_name: user.first_name || ""
            };

            await fetch(`${FIREBASE}/users/${user.id}.json`, { method: 'PATCH', body: JSON.stringify(payload) });
            al.style.color = '#4ade80';
            al.innerText = "✅ Successfully Saved!";
            setTimeout(() => tg.close(), 1200);
        }
        window.onload = init;
    </script>
</body>
</html>
"""

# Web Routing (Mini App on Root /)
class WebRouting(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(USER_MINIAPP_HTML.encode('utf-8'))
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), WebRouting)
    s.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- Language Script Engine ---
LANG_PATTERNS = {
    "bengali": r'[\u0980-\u09FF]+',
    "bangla": r'[\u0980-\u09FF]+',
    "hindi": r'[\u0900-\u097F]+',
    "arabic": r'[\u0600-\u06FF]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    "russian": r'[\u0400-\u04FF]+',
    "chinese": r'[\u4E00-\u9FFF]+',
    "japanese": r'[\u3040-\u309F\u30A0-\u30FF]+',
    "korean": r'[\uAC00-\uD7AF\u1100-\u11FF]+',
    "english": r'[a-zA-Z]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""

    # Global Blocklist
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    # Dynamic Language Removal from user input
    user_langs = u_data.get("remove_languages", "bengali")
    for lang in user_langs.split(","):
        lang_key = lang.strip().lower()
        if lang_key in LANG_PATTERNS:
            text = re.sub(LANG_PATTERNS[lang_key], '', text)

    # Clean Emojis & links
    for emo in ["⌲", "💫"]:
        text = text.replace(emo, "")
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    footer = u_data.get("footer_text", "")
    if not lines: return footer

    # First line Bold
    first_line = re.sub(r'^\*+|\*+$', '', lines[0]).strip()
    lines[0] = f"**{first_line}**"
    body = f"{lines[0]}\n\n" + "\n".join(lines[1:]) if len(lines) > 1 else lines[0]
    return f"{body}\n\n{footer}".strip() if footer else body.strip()

def clean_app_filename(name, tag):
    if not name: name = "app.apk"
    base, ext = os.path.splitext(name)
    base_clean = re.sub(r'@\w+', '', base)
    base_clean = re.sub(r'\[.*?\]|\(.*?\)', '', base_clean)
    base_clean = re.sub(r'[\s\-_]+$', '', base_clean).strip()
    base_clean = " ".join(base_clean.split())
    if not base_clean: base_clean = "App"
    return f"{base_clean} {tag}{ext}" if tag else f"{base_clean}{ext}"

# Multiple Channels Force Sub Check
async def check_all_force_subs(client, user_id):
    cfg = db_get("global_config")
    channels_str = cfg.get("force_channels", "@PhProMod")
    unsubbed = []
    for ch in channels_str.split(","):
        ch = ch.strip()
        if not ch: continue
        try:
            m = await client.get_chat_member(ch, user_id)
            if m.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                unsubbed.append(ch)
        except:
            unsubbed.append(ch)
    return unsubbed

# --- Bot Engine ---
bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# User state storage for BotFather-style flow
USER_STEPS = {}

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "User"

    photo_url = f"https://t.me/i/userpic/320/{username}.jpg" if username else ""
    u_data = db_get(f"users/{user_id}")
    if not u_data:
        db_put(f"users/{user_id}", {
            "first_name": first_name, "username": username, "photo_url": photo_url,
            "target_channel": "", "channel_username": "", "channel_category": "General",
            "channel_tag": "@MyChannel", "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "bengali", "is_banned": False
        })

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this bot.")
        return

    # Check Multiple Force Subs
    unsubbed = await check_all_force_subs(client, message.from_user.id)
    if unsubbed:
        buttons = []
        for ch in unsubbed:
            buttons.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','').strip()}")])
        buttons.append([InlineKeyboardButton("🔄 Verify All Channels", callback_data="check_all_subs")])
        await message.reply_text("⚠️ **Access Denied!**\nYou must join all our mandatory channels to use this bot:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # BotFather-style interactive keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Open Mini App Setup", web_app=WebAppInfo(url=RENDER_URL))],
        [InlineKeyboardButton("📢 Connect Channel via Bot", callback_data="btn_connect_channel")],
        [InlineKeyboardButton("🏷 Set Suffix Tag", callback_data="btn_set_tag"), InlineKeyboardButton("📂 Set Category", callback_data="btn_set_category")],
        [InlineKeyboardButton("🌐 Set Languages to Wipe", callback_data="btn_set_lang")],
        [InlineKeyboardButton("🔍 Get Channel ID (@userinfobot)", url="https://t.me/userinfobot")]
    ])

    await message.reply_text(
        f"👋 **Welcome, {first_name}!**\n\n"
        "You can manage all your settings easily via **Mini App** or step-by-step using the buttons below:",
        reply_markup=keyboard
    )

@bot.on_callback_query()
async def callback_handler(client, cb):
    uid = str(cb.from_user.id)
    if cb.data == "check_all_subs":
        unsub = await check_all_force_subs(client, cb.from_user.id)
        if not unsub:
            await cb.message.edit_text("✅ All channels verified! Send `/start` to begin.")
        else:
            await cb.answer("❌ You still haven't joined all channels!", show_alert=True)

    elif cb.data == "btn_connect_channel":
        USER_STEPS[uid] = "WAITING_CHANNEL_ID"
        await cb.message.reply_text(
            "📍 **Step 1: Send Your Target Channel ID**\n\n"
            "1. Make sure this bot is an **Admin** in your channel with **Post Messages** permission.\n"
            "2. Send your Channel ID here (e.g. `-100xxxxxxxxxx`).\n\n"
            "👉 Don't know your Channel ID? Use [@userinfobot](https://t.me/userinfobot) to get it."
        )
    elif cb.data == "btn_set_category":
        USER_STEPS[uid] = "WAITING_CATEGORY"
        await cb.message.reply_text("📂 Please send your **Channel Category** (e.g. Mod Apps, Movies, Tech, Anime):")
    elif cb.data == "btn_set_tag":
        USER_STEPS[uid] = "WAITING_TAG"
        await cb.message.reply_text("🏷 Send your **File Suffix Tag** (e.g. `@MyChannel`):")
    elif cb.data == "btn_set_lang":
        USER_STEPS[uid] = "WAITING_LANG"
        await cb.message.reply_text("🌐 Send languages to wipe out separated by comma (e.g. `bengali, hindi, arabic, urdu`):")

# Message & Forward Router
@bot.on_message(filters.private)
async def message_dispatcher(client, message):
    uid = str(message.from_user.id)
    u_data = db_get(f"users/{uid}")
    g_data = db_get("global_config")

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this service.")
        return

    # Check Subscriptions
    if await check_all_force_subs(client, message.from_user.id):
        pass
    else:
        await message.reply_text("⚠️ Unsubscribed from mandatory channels detected! Run `/start` to verify.")
        return

    # Handle Step-by-Step Inputs
    step = USER_STEPS.get(uid)
    if step == "WAITING_CHANNEL_ID":
        ch_id = message.text.strip()
        try:
            ch_int = int(ch_id)
            # Test send
            await client.send_message(ch_int, "🤖 **Channel connected successfully!**")
            db_put(f"users/{uid}/target_channel", ch_int)
            USER_STEPS.pop(uid, None)
            await message.reply_text(f"✅ Target Channel (`{ch_int}`) successfully connected and verified!")
        except Exception as e:
            await message.reply_text(f"❌ Failed to verify! Ensure bot is Admin with 'Post Messages' permission in that channel.\nError: `{e}`")
        return

    elif step == "WAITING_CATEGORY":
        cat = message.text.strip()
        db_put(f"users/{uid}/channel_category", cat)
        USER_STEPS.pop(uid, None)
        await message.reply_text(f"✅ Channel Category saved as: **{cat}**")
        return

    elif step == "WAITING_TAG":
        tag = message.text.strip()
        db_put(f"users/{uid}/channel_tag", tag)
        USER_STEPS.pop(uid, None)
        await message.reply_text(f"✅ Suffix Tag saved as: `{tag}`")
        return

    elif step == "WAITING_LANG":
        langs = message.text.strip()
        db_put(f"users/{uid}/remove_languages", langs)
        USER_STEPS.pop(uid, None)
        await message.reply_text(f"✅ Language filter set to: `{langs}`")
        return

    # Auto-Connect if post forwarded from user's channel
    if message.forward_from_chat:
        f_chat = message.forward_from_chat
        try:
            await client.send_message(f_chat.id, "🤖 **AutoPost Manager verified & connected to this channel!**")
            db_put(f"users/{uid}/target_channel", f_chat.id)
            if f_chat.username:
                db_put(f"users/{uid}/channel_username", f"@{f_chat.username}")
            await message.reply_text(f"🎉 **Channel Verified:** '{f_chat.title}' (`{f_chat.id}`) is connected!")
            return
        except Exception as e:
            await message.reply_text(f"❌ Permission error in '{f_chat.title}'. Ensure bot is an Admin!")
            return

    target_channel = u_data.get("target_channel")
    if not target_channel:
        await message.reply_text("⚠️ No target channel connected yet! Use `/start` to configure.")
        return

    status = await message.reply_text("⏳ Processing post for your channel...")

    try:
        tag = u_data.get("channel_tag", "")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        sent_msg = None

        if message.video:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Cancelled: Global blacklisted word found.")
                return
            new_name = clean_app_filename(message.video.file_name or "video.mp4", tag)
            fp = await message.download(file_name=new_name)
            sent_msg = await client.send_video(chat_id=target_channel, video=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(fp): os.remove(fp)

        elif message.document:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Cancelled: Global blacklisted word found.")
                return
            new_name = clean_app_filename(message.document.file_name, tag)
            fp = await message.download(file_name=new_name)
            sent_msg = await client.send_document(chat_id=target_channel, document=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(fp): os.remove(fp)

        elif message.photo:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Cancelled: Global blacklisted word found.")
                return
            sent_msg = await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=cap, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            cap = clean_post_text(message.text, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Cancelled: Global blacklisted word found.")
                return
            sent_msg = await client.send_message(chat_id=target_channel, text=cap, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Successfully posted to your channel!")

        # Generate Telegram Post Direct Link for Admin Panel Inspection
        post_link = ""
        f_chat = message.forward_from_chat
        if f_chat and f_chat.username and message.forward_from_message_id:
            post_link = f"https://t.me/{f_chat.username}/{message.forward_from_message_id}"
        elif u_data.get("channel_username") and sent_msg:
            post_link = f"https://t.me/{u_data['channel_username'].replace('@','')}/{sent_msg.id}"

        # Save activity to Firebase
        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": uid,
            "user_name": message.from_user.first_name or "User",
            "channel": target_channel,
            "category": u_data.get("channel_category", "General"),
            "post_link": post_link,
            "content": (message.caption or message.text or getattr(message.document, 'file_name', 'Media File'))[:45]
        })

        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        await status.edit_text(f"❌ Failed: {e}")

async def main():
    await bot.start()
    print(">>> Multi-User SaaS Bot Ready! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
