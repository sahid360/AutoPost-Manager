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

# Memory State for BotFather-like Wizard
USER_STATES = {}

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

# Ensure Global Config
g_cfg = db_get("global_config")
if not g_cfg:
    db_put("global_config", {
        "force_channels": "@PhProMod",
        "global_blocked_words": "scam, fraud, 18+, betting",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 1. PURE DARK USER TELEGRAM MINI APP
# ==========================================
USER_MINIAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Channel Settings</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #05070e; color: #f8fafc; margin: 0; padding: 16px; }
        .card { background: #0e1424; border-radius: 14px; padding: 20px; border: 1px solid #1e293b; box-shadow: 0 10px 25px rgba(0,0,0,0.7); }
        h3 { margin-top: 0; color: #38bdf8; font-size: 18px; border-bottom: 1px solid #1e293b; padding-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        label { display: block; font-size: 13px; color: #94a3b8; margin-top: 14px; font-weight: 600; }
        input[type="text"], textarea, select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #1e293b; background: #05070e; color: #fff; margin-top: 6px; box-sizing: border-box; font-size: 14px; }
        input:focus, textarea:focus, select:focus { border-color: #38bdf8; outline: none; }
        textarea { height: 70px; resize: none; }
        .guide-box { background: #080d1a; padding: 12px; border-radius: 8px; margin-top: 6px; font-size: 12px; color: #38bdf8; border: 1px dashed #1e293b; line-height: 1.5; }
        .guide-box a { color: #60a5fa; text-decoration: underline; font-weight: bold; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 14px; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; transition: 0.2s; }
        button:hover { background: #0369a1; }
        .alert { text-align: center; margin-top: 12px; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h3>⚙️ Channel Configuration</h3>
        
        <label>Target Channel ID (e.g. -100xxxxxxxxxx):</label>
        <input type="text" id="target_channel" placeholder="-1001234567890">
        <div class="guide-box">
            💡 <b>How to find ID?</b> Add bot as Admin with Post permission, then forward any post from your channel to <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a> to copy your channel ID.
        </div>

        <label>Channel Category (Required):</label>
        <select id="channel_category">
            <option value="Mod APKs">📱 Mod APKs & Apps</option>
            <option value="Movies">🎬 Movies & Web Series</option>
            <option value="Tech">💻 Tech & Tutorials</option>
            <option value="Gaming">🎮 Gaming & Streaming</option>
            <option value="News">📰 News & Updates</option>
            <option value="Crypto">💰 Crypto & Airdrops</option>
            <option value="Other">📦 Other / General</option>
        </select>

        <label>File Name Suffix Tag:</label>
        <input type="text" id="channel_tag" placeholder="@YourChannel">

        <label>Custom Post Footer Text:</label>
        <textarea id="footer_text" placeholder="⌲ @YourChannel&#10;Share with friends 👥"></textarea>

        <label>Languages to Wipe Out (Type names, comma-separated):</label>
        <input type="text" id="remove_languages" placeholder="bengali, hindi, arabic, urdu">

        <label>Custom Words to Remove (comma-separated):</label>
        <input type="text" id="blocked_words" placeholder="badword, @other_channel">

        <button onclick="saveUserSettings()">💾 Save Configuration</button>
        <div id="alert" class="alert"></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user = tg.initDataUnsafe?.user || { id: "demo_user", first_name: "User" };
        const FIREBASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function loadData() {
            try {
                const res = await fetch(`${FIREBASE}/users/${user.id}.json`);
                const data = await res.json();
                if (data) {
                    document.getElementById('target_channel').value = data.target_channel || "";
                    if(data.channel_category) document.getElementById('channel_category').value = data.channel_category;
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('footer_text').value = data.footer_text || "";
                    document.getElementById('remove_languages').value = data.remove_languages || "bengali";
                    document.getElementById('blocked_words').value = data.blocked_words || "";
                }
            } catch(e) {}
        }

        async function saveUserSettings() {
            const alertDiv = document.getElementById('alert');
            const targetChannel = document.getElementById('target_channel').value.trim();

            if(!targetChannel) {
                alertDiv.style.color = '#ef4444';
                alertDiv.innerText = "❌ Channel ID is required!";
                return;
            }

            alertDiv.style.color = '#38bdf8';
            alertDiv.innerText = "Saving settings...";

            const payload = {
                target_channel: targetChannel,
                channel_category: document.getElementById('channel_category').value,
                channel_tag: document.getElementById('channel_tag').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                remove_languages: document.getElementById('remove_languages').value.trim(),
                blocked_words: document.getElementById('blocked_words').value.trim(),
                username: user.username || "",
                first_name: user.first_name || ""
            };

            await fetch(`${FIREBASE}/users/${user.id}.json`, {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });

            alertDiv.style.color = '#4ade80';
            alertDiv.innerText = "✅ Saved successfully!";
            setTimeout(() => { tg.close(); }, 1200);
        }
        window.onload = loadData;
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

def run_http():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), MasterRouter)
    s.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# --- Telegram Bot Core ---
bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Multi-channel Force Subscribe Checker
async def check_all_force_subs(client, user_id):
    cfg = db_get("global_config")
    raw_channels = cfg.get("force_channels", "@PhProMod")
    unsubbed_channels = []
    
    for ch in raw_channels.split(","):
        ch = ch.strip()
        if not ch: continue
        try:
            m = await client.get_chat_member(ch, user_id)
            if m.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                unsubbed_channels.append(ch)
        except UserNotParticipant:
            unsubbed_channels.append(ch)
        except Exception:
            pass # ignore invalid channel names
            
    return unsubbed_channels

# Dynamic Language Clean Engine
LANGUAGE_PATTERNS = {
    "bengali": r'[\u0980-\u09FF]+',
    "bangla": r'[\u0980-\u09FF]+',
    "hindi": r'[\u0900-\u097F]+',
    "arabic": r'[\u0600-\u06FF]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    "russian": r'[\u0400-\u04FF]+',
    "chinese": r'[\u4e00-\u9fff]+',
    "japanese": r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+',
    "korean": r'[\uac00-\ud7af]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""

    # Global Blocked Words
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    # User Custom Blocked Words
    u_blocked = u_data.get("blocked_words", "")
    for word in u_blocked.split(","):
        w = word.strip()
        if w: text = re.sub(re.escape(w), '', text, flags=re.IGNORECASE)

    # Dynamic Languages Removal (Typed by user)
    typed_langs = u_data.get("remove_languages", "bengali").lower()
    for lang in typed_langs.split(","):
        lang = lang.strip()
        if lang in LANGUAGE_PATTERNS:
            text = re.sub(LANGUAGE_PATTERNS[lang], '', text)

    # Remove Emojis & Foreign Links
    for emo in ["⌲", "💫"]:
        text = text.replace(emo, "")
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    footer = u_data.get("footer_text", "")
    if not lines: return footer

    # First Line Bold & Format
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

# --- BotFather-like Interactive Menus ---

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Connect / Change Channel", callback_data="btn_connect_channel")],
        [InlineKeyboardButton("⚙️ Open Mini App Settings", web_app=WebAppInfo(url=RENDER_URL))],
        [InlineKeyboardButton("ℹ️ Connection Status", callback_data="btn_my_status")]
    ])

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    # Register in DB with Profile Photo URL
    photo_url = f"https://t.me/i/userpic/320/{username}.jpg" if username else ""
    u_data = db_get(f"users/{user_id}")
    if not u_data:
        db_put(f"users/{user_id}", {
            "first_name": first_name,
            "username": username,
            "photo_url": photo_url,
            "target_channel": "",
            "target_channel_username": "",
            "channel_category": "Other",
            "channel_tag": "@MyChannel",
            "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "bengali",
            "blocked_words": "",
            "is_banned": False
        })

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this bot.")
        return

    # Check Multi-channel Force Subs
    unsubbed = await check_all_force_subs(client, message.from_user.id)
    if unsubbed:
        btn_rows = []
        for ch in unsubbed:
            btn_rows.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}")])
        btn_rows.append([InlineKeyboardButton("🔄 Verify & Continue", callback_data="btn_verify_subs")])
        await message.reply_text("⚠️ **Access Denied!**\nYou must join all our mandatory channels to use this bot:", reply_markup=InlineKeyboardMarkup(btn_rows))
        return

    await message.reply_text(
        f"👋 **Welcome, {first_name}!**\n\n"
        "I am your automated channel publisher bot. I can auto-rename files, remove foreign tags, wipe specific languages, and post cleanly to your channel.\n\n"
        "Select an option below to get started:",
        reply_markup=get_main_keyboard()
    )

@bot.on_callback_query()
async def callback_dispatcher(client, cb):
    user_id = str(cb.from_user.id)

    if cb.data == "btn_verify_subs":
        unsubbed = await check_all_force_subs(client, cb.from_user.id)
        if not unsubbed:
            await cb.message.edit_text("✅ **Subscription verified!**", reply_markup=get_main_keyboard())
        else:
            await cb.answer("❌ You haven't joined all required channels!", show_alert=True)

    elif cb.data == "btn_connect_channel":
        USER_STATES[user_id] = "waiting_channel_id"
        help_msg = (
            "📌 **Step 1: Get Channel ID & Add Admin**\n\n"
            "1. Add this bot as an **Administrator** in your channel with **Post Messages** permission.\n"
            "2. How to get your Channel ID:\n"
            "   👉 Forward any post from your channel to 👉 [@userinfobot](https://t.me/userinfobot)\n"
            "   👉 Copy the ID (starts with `-100`).\n\n"
            "✍️ **Now reply and send your Channel ID here:** (or forward a post from your channel)"
        )
        await cb.message.reply_text(help_msg, disable_web_page_preview=True)

    elif cb.data == "btn_my_status":
        u = db_get(f"users/{user_id}")
        st = (
            "📊 **Your Bot Status:**\n\n"
            f"• Target Channel: `{u.get('target_channel') or 'Not Set'}`\n"
            f"• Channel Username: `{u.get('target_channel_username') or 'None/Private'}`\n"
            f"• Category: `{u.get('channel_category') or 'Not Set'}`\n"
            f"• Suffix Tag: `{u.get('channel_tag') or 'None'}`\n"
            f"• Removing Languages: `{u.get('remove_languages') or 'None'}`"
        )
        await cb.message.reply_text(st, reply_markup=get_main_keyboard())

    elif cb.data.startswith("set_cat_"):
        cat = cb.data.replace("set_cat_", "")
        db_put(f"users/{user_id}/channel_category", cat)
        USER_STATES.pop(user_id, None)
        await cb.message.edit_text(f"🎉 **Category Selected:** `{cat}`\n\n✅ **Channel setup is 100% complete!**\nNow simply forward any post, video, or APK to this bot!")

# State & Post Handler
@bot.on_message(filters.private)
async def main_receiver(client, message):
    user_id = str(message.from_user.id)
    u_data = db_get(f"users/{user_id}")
    g_data = db_get("global_config")

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this service.")
        return

    # Check Force Sub
    if await check_all_force_subs(client, message.from_user.id):
        pass # OK

    # State: Channel Connect Flow
    if USER_STATES.get(user_id) == "waiting_channel_id" or message.forward_from_chat:
        target_id = None
        target_title = "Channel"
        target_username = ""

        if message.forward_from_chat:
            target_id = message.forward_from_chat.id
            target_title = message.forward_from_chat.title
            target_username = f"@{message.forward_from_chat.username}" if message.forward_from_chat.username else "Private"
        elif message.text and ("-100" in message.text or message.text.startswith("-")):
            try:
                target_id = int(message.text.strip())
                chat = await client.get_chat(target_id)
                target_title = chat.title
                target_username = f"@{chat.username}" if chat.username else "Private"
            except Exception as e:
                await message.reply_text(f"❌ Invalid Channel ID or Bot is not an Admin! Error: `{e}`")
                return

        if target_id:
            try:
                await client.send_message(target_id, "🤖 **AutoPost Manager successfully connected to this channel!**")
                db_put(f"users/{user_id}/target_channel", target_id)
                db_put(f"users/{user_id}/target_channel_username", target_username)
                
                # Ask Category via BotFather-like buttons
                cat_btns = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Mod APKs", callback_data="set_cat_Mod APKs"), InlineKeyboardButton("🎬 Movies", callback_data="set_cat_Movies")],
                    [InlineKeyboardButton("💻 Tech & Tips", callback_data="set_cat_Tech"), InlineKeyboardButton("🎮 Gaming", callback_data="set_cat_Gaming")],
                    [InlineKeyboardButton("📰 News & Updates", callback_data="set_cat_News"), InlineKeyboardButton("💰 Crypto", callback_data="set_cat_Crypto")],
                    [InlineKeyboardButton("📦 Other / General", callback_data="set_cat_Other")]
                ])
                await message.reply_text(
                    f"✅ **Channel Verified:** '{target_title}' (`{target_id}`)\n\n"
                    "👉 **Now choose your Channel Category:**",
                    reply_markup=cat_btns
                )
                return
            except Exception as e:
                await message.reply_text(f"❌ **Permission Failed:** Make sure bot is an Admin with 'Post Messages' in '{target_title}'! Error: `{e}`")
                return

    # Normal Forward/Post Processing
    target_channel = u_data.get("target_channel")
    if not target_channel:
        await message.reply_text("⚠️ No channel connected yet! Click below to connect:", reply_markup=get_main_keyboard())
        return

    status = await message.reply_text("⏳ Processing post for your channel...")
    try:
        tag = u_data.get("channel_tag", "")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        posted_msg = None

        if message.video:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            new_name = clean_app_filename(message.video.file_name or "video.mp4", tag)
            fp = await message.download(file_name=new_name)
            posted_msg = await client.send_video(chat_id=target_channel, video=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(fp): os.remove(fp)

        elif message.document:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            new_name = clean_app_filename(message.document.file_name, tag)
            fp = await message.download(file_name=new_name)
            posted_msg = await client.send_document(chat_id=target_channel, document=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(fp): os.remove(fp)

        elif message.photo:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            posted_msg = await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=cap, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            cap = clean_post_text(message.text, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            posted_msg = await client.send_message(chat_id=target_channel, text=cap, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Successfully posted to your channel!")

        # Generate Clickable Post Link for Live Monitor
        post_link = ""
        if posted_msg:
            ch_user = u_data.get("target_channel_username", "")
            if ch_user and ch_user != "Private":
                post_link = f"https://t.me/{ch_user.replace('@','')}/{posted_msg.id}"
            else:
                cid_clean = str(target_channel).replace("-100", "")
                post_link = f"https://t.me/c/{cid_clean}/{posted_msg.id}"

        # Save to Firebase Logs
        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": user_id,
            "user_name": message.from_user.first_name or "User",
            "channel_id": target_channel,
            "channel_username": u_data.get("target_channel_username", "Private"),
            "category": u_data.get("channel_category", "General"),
            "post_link": post_link,
            "content": (message.caption or message.text or message.document.file_name if message.document else "Media")[:40]
        })
        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        await status.edit_text(f"❌ Failed: {e}")

async def main():
    await bot.start()
    print(">>> SaaS Bot with Dark MiniApp & Wizard LIVE! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
