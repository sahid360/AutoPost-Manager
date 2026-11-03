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

# Memory State for BotFather-style button prompts
USER_STATES = {}

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

# Ensure Global Settings
g_cfg = db_get("global_config")
if not g_cfg:
    db_put("global_config", {
        "force_channels": "@PhProMod",
        "global_blocked_words": "scam, 18+, fraud, porn",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 1. PURE DARK THEME USER MINI APP (HTML/JS)
# ==========================================
USER_MINIAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Channel Config</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: #090d16;
            --card: #111827;
            --border: #1f2937;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --text: #f9fafb;
            --muted: #9ca3af;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 16px; }
        .box { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2 { margin-top: 0; font-size: 18px; color: var(--accent); text-align: center; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
        label { display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin-top: 14px; }
        input[type="text"], textarea { width: 100%; padding: 12px; background: #030712; border: 1px solid var(--border); border-radius: 8px; color: #fff; font-size: 14px; margin-top: 6px; box-sizing: border-box; outline: none; transition: 0.2s; }
        input[type="text"]:focus, textarea:focus { border-color: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }
        textarea { height: 75px; resize: none; }
        .help-tip { font-size: 12px; color: var(--accent); margin-top: 4px; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 14px; border: none; border-radius: 10px; font-size: 16px; font-weight: 700; cursor: pointer; margin-top: 20px; box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4); }
        button:hover { background: #0369a1; }
        #msg { text-align: center; margin-top: 12px; font-size: 14px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="box">
        <h2>⚡ Channel Control Center</h2>
        
        <label>🎯 Target Channel ID (e.g. -100xxxxxxxxxx):</label>
        <input type="text" id="target_channel" placeholder="-1001234567890">
        <div class="help-tip">💡 Forward post from channel to bot or use @userinfobot to get ID.</div>

        <label>📂 Channel Category:</label>
        <input type="text" id="channel_category" placeholder="Mod Apps, Movies, Tech, Gaming, News">

        <label>🏷️ File Suffix Tag:</label>
        <input type="text" id="channel_tag" placeholder="@MyChannel">

        <label>✍️ Custom Post Footer Credit:</label>
        <textarea id="footer_text" placeholder="⌲ @MyChannel&#10;Share with friends 👥"></textarea>

        <label>🌐 Languages to Wipe Out (comma-separated):</label>
        <input type="text" id="remove_languages" placeholder="bengali, hindi, arabic, urdu, russian">
        <div class="help-tip">Type any language names. These scripts will be removed automatically!</div>

        <label>🚫 Custom Words to Remove (comma-separated):</label>
        <input type="text" id="blocked_words" placeholder="badword1, @foreign_channel">

        <button onclick="saveMiniAppData()">💾 Save Configuration</button>
        <div id="msg"></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user = tg.initDataUnsafe?.user || { id: "test_user" };
        const FB = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function init() {
            try {
                const res = await fetch(`${FB}/users/${user.id}.json`);
                const d = await res.json();
                if(d) {
                    document.getElementById('target_channel').value = d.target_channel || "";
                    document.getElementById('channel_category').value = d.channel_category || "";
                    document.getElementById('channel_tag').value = d.channel_tag || "";
                    document.getElementById('footer_text').value = d.footer_text || "";
                    document.getElementById('remove_languages').value = d.remove_languages || "bengali";
                    document.getElementById('blocked_words').value = d.blocked_words || "";
                }
            } catch(e) {}
        }

        async function saveMiniAppData() {
            const m = document.getElementById('msg');
            m.style.color = '#38bdf8';
            m.innerText = "Syncing with cloud...";

            const payload = {
                target_channel: document.getElementById('target_channel').value.trim(),
                channel_category: document.getElementById('channel_category').value.trim() || "General",
                channel_tag: document.getElementById('channel_tag').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                remove_languages: document.getElementById('remove_languages').value.trim(),
                blocked_words: document.getElementById('blocked_words').value.trim(),
                username: user.username || "",
                first_name: user.first_name || "User"
            };

            await fetch(`${FB}/users/${user.id}.json`, {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });

            m.style.color = '#22c55e';
            m.innerText = "✅ Successfully Saved!";
            setTimeout(() => { tg.close(); }, 1200);
        }
        window.onload = init;
    </script>
</body>
</html>
"""

class MasterRouter(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(USER_MINIAPP_HTML.encode('utf-8'))
    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), MasterRouter)
    s.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- Telegram Bot Engine ---
bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Multi-channel Force Subscribe Check
async def check_all_force_subs(client, user_id):
    cfg = db_get("global_config")
    channels_str = cfg.get("force_channels", "@PhProMod")
    channels = [c.strip() for c in channels_str.split(",") if c.strip()]
    
    missing_channels = []
    for ch in channels:
        try:
            m = await client.get_chat_member(ch, user_id)
            if m.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                missing_channels.append(ch)
        except UserNotParticipant:
            missing_channels.append(ch)
        except Exception:
            pass # Skip if bot is not in the channel or invalid
    return missing_channels

# Comprehensive Multi-Language Detection Engine
LANGUAGE_MAP = {
    "bengali": r'[\u0980-\u09FF]+',
    "bangla": r'[\u0980-\u09FF]+',
    "hindi": r'[\u0900-\u097F]+',
    "arabic": r'[\u0600-\u06FF\u0750-\u077F]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    "russian": r'[\u0400-\u04FF]+',
    "cyrillic": r'[\u0400-\u04FF]+',
    "tamil": r'[\u0B80-\u0BFF]+',
    "telugu": r'[\u0C00-\u0C7F]+',
    "chinese": r'[\u4E00-\u9FFF]+',
    "japanese": r'[\u3040-\u309F\u30A0-\u30FF]+',
    "korean": r'[\uAC00-\uD7AF]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""

    # 1. Global Prohibited Words Check
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    # 2. User Blocked Words
    u_blocked = u_data.get("blocked_words", "")
    for word in u_blocked.split(","):
        w = word.strip()
        if w: text = re.sub(re.escape(w), '', text, flags=re.IGNORECASE)

    # 3. Dynamic User Languages Removal
    user_langs = u_data.get("remove_languages", "bengali")
    for lang in user_langs.split(","):
        l_clean = lang.strip().lower()
        if l_clean in LANGUAGE_MAP:
            text = re.sub(LANGUAGE_MAP[l_clean], '', text)

    # 4. Filter Specific Emojis & Links
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

# BotFather-Style Interactive Keyboard
def get_botfather_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Open Mini App Control", web_app=WebAppInfo(url=RENDER_URL))],
        [InlineKeyboardButton("🆔 Set Channel ID", callback_data="btn_set_id"), InlineKeyboardButton("📂 Channel Category", callback_data="btn_set_cat")],
        [InlineKeyboardButton("🏷️ Suffix File Tag", callback_data="btn_set_tag"), InlineKeyboardButton("✍️ Post Footer Text", callback_data="btn_set_foot")],
        [InlineKeyboardButton("🌐 Wipe Languages", callback_data="btn_set_lang"), InlineKeyboardButton("🚫 Block Custom Words", callback_data="btn_set_words")],
        [InlineKeyboardButton("❓ How to find Channel ID?", callback_data="btn_how_id")]
    ])

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    # Fetch User Avatar
    photo_url = f"https://t.me/i/userpic/320/{username}.jpg" if username else ""

    u_data = db_get(f"users/{user_id}")
    if not u_data:
        db_put(f"users/{user_id}", {
            "first_name": first_name,
            "username": username,
            "photo_url": photo_url,
            "target_channel": "",
            "channel_username": "",
            "channel_category": "General",
            "channel_tag": "@MyChannel",
            "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "bengali",
            "blocked_words": "",
            "is_banned": False
        })
    elif photo_url and not u_data.get("photo_url"):
        db_put(f"users/{user_id}/photo_url", photo_url)

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You have been banned by the Super Administrator.")
        return

    # Check Multiple Force Subscribe
    missing = await check_all_force_subs(client, message.from_user.id)
    if missing:
        buttons = []
        for ch in missing:
            link = f"https://t.me/{ch.replace('@','')}" if ch.startswith("@") else "https://t.me/"
            buttons.append([InlineKeyboardButton(f"📢 Join {ch}", url=link)])
        buttons.append([InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_all_subs")])
        await message.reply_text(
            "⚠️ **Access Restricted!**\n\nYou must join all our required channels before using this bot:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    welcome_text = (
        f"👋 **Welcome to AutoPost Manager, {first_name}!**\n\n"
        "Configure your channel using the interactive buttons below or via the Mini App:"
    )
    await message.reply_text(welcome_text, reply_markup=get_botfather_keyboard())

# Callback Query Handler for Buttons
@bot.on_callback_query()
async def callback_handler(client, cb):
    user_id = str(cb.from_user.id)
    data = cb.data

    if data == "verify_all_subs":
        missing = await check_all_force_subs(client, cb.from_user.id)
        if not missing:
            await cb.message.edit_text("✅ All subscriptions verified! Send `/start` to begin.")
        else:
            await cb.answer("❌ You haven't joined all channels yet!", show_alert=True)
        return

    if data == "btn_how_id":
        help_guide = (
            "🔍 **How to find your Channel ID:**\n\n"
            "1. Forward any message from your channel to [User Info Bot](https://t.me/userinfobot) (@userinfobot).\n"
            "2. The bot will send your channel ID (starts with `-100`, e.g., `-1001234567890`).\n"
            "3. Make sure to add this bot as an **Admin with Post Messages** permission in your channel!"
        )
        await cb.message.reply_text(help_guide, disable_web_page_preview=True)
        return

    # Button Prompts
    prompts = {
        "btn_set_id": ("target_channel", "👉 Please send your **Target Channel ID** (e.g. `-1001234567890`):"),
        "btn_set_cat": ("channel_category", "👉 Please send your **Channel Category** (e.g. `Mod Apps`, `Movies`, `Gaming`):"),
        "btn_set_tag": ("channel_tag", "👉 Please send your **Suffix File Tag** (e.g. `@MyChannel`):"),
        "btn_set_foot": ("footer_text", "👉 Please send your **Custom Footer Text**:"),
        "btn_set_lang": ("remove_languages", "👉 Please send **Languages to Wipe Out** (comma-separated, e.g. `bengali, hindi, arabic`):"),
        "btn_set_words": ("blocked_words", "👉 Please send **Custom Words to Delete** (comma-separated):")
    }

    if data in prompts:
        field, prompt_msg = prompts[data]
        USER_STATES[user_id] = field
        await cb.message.reply_text(prompt_msg)
        await cb.answer()

# Master Message & Forward Dispatcher
@bot.on_message(filters.private)
async def message_processor(client, message):
    user_id = str(message.from_user.id)
    u_data = db_get(f"users/{user_id}")
    g_data = db_get("global_config")

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this service.")
        return

    # Check Force Sub
    if await check_all_force_subs(client, message.from_user.id):
        await message.reply_text("⚠️ Unsubscribed detected! Run `/start` to verify required channels.")
        return

    # Check if user is replying to a BotFather-style button prompt
    if user_id in USER_STATES and message.text and not message.text.startswith("/"):
        field = USER_STATES.pop(user_id)
        val = message.text.strip()
        db_put(f"users/{user_id}/{field}", val)
        await message.reply_text(f"✅ **{field.replace('_', ' ').title()}** updated to:\n`{val}`", reply_markup=get_botfather_keyboard())
        return

    # Channel Auto-Detect via Forward
    if message.forward_from_chat:
        f_chat = message.forward_from_chat
        try:
            await client.send_message(f_chat.id, "🤖 **AutoPost Manager verified & successfully connected!**")
            db_put(f"users/{user_id}/target_channel", f_chat.id)
            db_put(f"users/{user_id}/channel_username", f_chat.username or "")
            await message.reply_text(f"🎉 **Channel Verified:** '{f_chat.title}' (`{f_chat.id}`) is successfully connected!")
            return
        except Exception as e:
            await message.reply_text(f"❌ **Permission Failed:** Make sure bot is an Admin with Post Messages in '{f_chat.title}'!")
            return

    target_channel = u_data.get("target_channel")
    if not target_channel:
        await message.reply_text("⚠️ Channel not connected yet! Use the buttons or Mini App to configure.", reply_markup=get_botfather_keyboard())
        return

    status = await message.reply_text("⏳ Processing post for your channel...")
    try:
        tag = u_data.get("channel_tag", "")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        sent_msg = None

        if message.video:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            new_name = clean_app_filename(message.video.file_name or "video.mp4", tag)
            fp = await message.download(file_name=new_name)
            sent_msg = await client.send_video(chat_id=target_channel, video=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(fp): os.remove(fp)

        elif message.document:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            new_name = clean_app_filename(message.document.file_name, tag)
            fp = await message.download(file_name=new_name)
            sent_msg = await client.send_document(chat_id=target_channel, document=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(fp): os.remove(fp)

        elif message.photo:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            sent_msg = await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=cap, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            cap = clean_post_text(message.text, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            sent_msg = await client.send_message(chat_id=target_channel, text=cap, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Successfully posted to your channel!")

        # Generate Clickable Telegram Review Link for Admin Panel
        post_link = ""
        if sent_msg:
            ch_user = u_data.get("channel_username")
            if ch_user:
                post_link = f"https://t.me/{ch_user}/{sent_msg.id}"
            else:
                raw_id = str(target_channel).replace("-100", "")
                post_link = f"https://t.me/c/{raw_id}/{sent_msg.id}"

        # Record activity into Firebase
        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": user_id,
            "user_name": message.from_user.first_name or "User",
            "channel": target_channel,
            "category": u_data.get("channel_category", "General"),
            "post_link": post_link,
            "content": (message.caption or message.text or message.document.file_name if message.document else "Media")[:40]
        })

        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        await status.edit_text(f"❌ Failed to post: {e}")

async def main():
    await bot.start()
    print(">>> SaaS Enterprise Bot is RUNNING! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
