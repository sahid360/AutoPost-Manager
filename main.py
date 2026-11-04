import os
import re
import asyncio
import threading
import json
import time
from datetime import datetime
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"
FIREBASE_BASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com"
RENDER_URL = "https://autopost-manager-1.onrender.com"

# Anti-Flood Debounce
LAST_WARN_TIME = {}
def can_send_warning(uid):
    now = time.time()
    if uid in LAST_WARN_TIME and (now - LAST_WARN_TIME[uid]) < 5:
        return False
    LAST_WARN_TIME[uid] = now
    return True

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
        "global_blocked_words": "scam, fraud, 18+",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 1. PURE DARK MINI APP (HTML)
# ==========================================
USER_MINIAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Config</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root { --bg: #090d16; --card: #111827; --input: #030712; --border: #1f2937; --accent: #38bdf8; --text: #f9fafb; --muted: #9ca3af; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 14px; }
        .card { background: var(--card); border-radius: 14px; padding: 18px; border: 1px solid var(--border); box-shadow: 0 8px 20px rgba(0,0,0,0.6); }
        h3 { margin-top: 0; color: var(--accent); font-size: 16px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        label { display: block; font-size: 13px; color: var(--muted); margin-top: 14px; font-weight: 600; }
        input[type="text"], textarea { width: 100%; padding: 11px; border-radius: 8px; border: 1px solid var(--border); background: var(--input); color: #fff; margin-top: 6px; box-sizing: border-box; font-size: 14px; }
        textarea { height: 75px; resize: none; }
        .helper-link { font-size: 12px; color: var(--accent); margin-top: 5px; display: block; text-decoration: none; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 13px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 18px; }
        .alert { text-align: center; margin-top: 12px; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h3>⚡ AutoPost Channel / Group Setup</h3>
        <label>Target Channel or Group ID:</label>
        <input type="text" id="target_channel" placeholder="-100xxxxxxxxxx">
        <a class="helper-link" href="https://t.me/userinfobot" target="_blank">🔍 Get ID from @userinfobot</a>

        <label>Category:</label>
        <input type="text" id="channel_category" placeholder="Mod Apps, Movies, Tech, Gaming">

        <label>File Suffix Tag:</label>
        <input type="text" id="channel_tag" placeholder="@MyChannel">

        <label>Languages to Wipe Out (Keep empty for none):</label>
        <input type="text" id="remove_languages" placeholder="e.g. bengali, hindi, arabic, urdu">

        <label>Post Footer / Credits:</label>
        <textarea id="footer_text" placeholder="⌲ @MyChannel&#10;Share with friends 👥"></textarea>

        <button onclick="saveConfig()">💾 Save Settings</button>
        <div id="status_alert" class="alert"></div>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user = tg.initDataUnsafe?.user || { id: "demo_user", first_name: "User" };
        const FIREBASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function init() {
            try {
                const res = await fetch(`${FIREBASE}/users/${user.id}.json`);
                const data = await res.json();
                if(data) {
                    document.getElementById('target_channel').value = data.target_channel || "";
                    document.getElementById('channel_category').value = data.channel_category || "";
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('remove_languages').value = data.remove_languages || "";
                    document.getElementById('footer_text').value = data.footer_text || "";
                }
            } catch(e) {}
        }
        async function saveConfig() {
            const al = document.getElementById('status_alert');
            al.style.color = '#38bdf8'; al.innerText = "Saving settings...";
            const payload = {
                target_channel: document.getElementById('target_channel').value.trim(),
                channel_category: document.getElementById('channel_category').value.trim() || "General",
                channel_tag: document.getElementById('channel_tag').value.trim(),
                remove_languages: document.getElementById('remove_languages').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                username: user.username || "", first_name: user.first_name || ""
            };
            await fetch(`${FIREBASE}/users/${user.id}.json`, { method: 'PATCH', body: JSON.stringify(payload) });
            al.style.color = '#4ade80'; al.innerText = "✅ Successfully Saved!";
            setTimeout(() => tg.close(), 1200);
        }
        window.onload = init;
    </script>
</body>
</html>
"""

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(USER_MINIAPP_HTML.encode('utf-8'))
    def log_message(self, format, *args): return

def run_http():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), WebServer)
    s.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

async def get_missing_subs(client, user_id):
    cfg = db_get("global_config")
    channels = cfg.get("force_channels", "@PhProMod").split(",")
    missing = []
    for ch in channels:
        ch = ch.strip()
        if not ch: continue
        try:
            m = await client.get_chat_member(ch, user_id)
            if m.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                missing.append(ch)
        except Exception:
            pass
    return missing

LANG_PATTERNS = {
    "bengali": r'[\u0980-\u09FF]+', "bangla": r'[\u0980-\u09FF]+',
    "hindi": r'[\u0900-\u097F]+', "arabic": r'[\u0600-\u06FF]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+', "russian": r'[\u0400-\u04FF]+',
    "english": r'[a-zA-Z]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    user_langs = u_data.get("remove_languages", "")
    if user_langs:
        for lang in user_langs.split(","):
            k = lang.strip().lower()
            if k in LANG_PATTERNS: text = re.sub(LANG_PATTERNS[k], '', text)

    for emo in ["⌲", "💫"]: text = text.replace(emo, "")
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    footer = u_data.get("footer_text", "")
    if not lines: return footer

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

bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
USER_STEPS = {}

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    uid = str(message.from_user.id)
    u_data = db_get(f"users/{uid}")
    if not u_data:
        db_put(f"users/{uid}", {
            "first_name": message.from_user.first_name or "User",
            "username": message.from_user.username or "",
            "photo_url": f"https://t.me/i/userpic/320/{message.from_user.username}.jpg" if message.from_user.username else "",
            "target_channel": "", "channel_category": "General",
            "channel_tag": "@MyChannel", "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "", "is_banned": False
        })

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this bot.")
        return

    missing = await get_missing_subs(client, message.from_user.id)
    if missing:
        btns = [[InlineKeyboardButton(f"📢 Join {c}", url=f"https://t.me/{c.replace('@','').strip()}")] for c in missing]
        btns.append([InlineKeyboardButton("🔄 Verify Membership", callback_data="check_all_subs")])
        await message.reply_text("⚠️ **Join Required!** Please join our channels to use this bot:", reply_markup=InlineKeyboardMarkup(btns))
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Open Mini App Setup", web_app=WebAppInfo(url=RENDER_URL))],
        [InlineKeyboardButton("📡 Connect Channel / Group", callback_data="btn_connect_channel")],
        [InlineKeyboardButton("🏷 Suffix Tag", callback_data="btn_set_tag"), InlineKeyboardButton("📂 Category", callback_data="btn_set_category")],
        [InlineKeyboardButton("🌐 Wipe Languages", callback_data="btn_set_lang")],
        [InlineKeyboardButton("🔍 Get ID from @userinfobot", url="https://t.me/userinfobot")]
    ])
    await message.reply_text(f"👋 **Welcome, {message.from_user.first_name}!**\nManage settings via Mini App or buttons below:", reply_markup=keyboard)

@bot.on_callback_query()
async def callback_gate(client, cb):
    uid = str(cb.from_user.id)
    await cb.answer()

    if cb.data == "check_all_subs":
        missing = await get_missing_subs(client, cb.from_user.id)
        if not missing:
            try: await cb.message.edit_text("✅ All channels verified! Send `/start` to begin.")
            except: pass
        else:
            await cb.answer("❌ You still haven't joined all channels!", show_alert=True)
            
    elif cb.data == "btn_connect_channel":
        USER_STEPS[uid] = "WAIT_CH_ID"
        await cb.message.reply_text(
            "📍 **Step 1: Send your Channel or Group ID:**\n\n"
            "👉 e.g. `-100xxxxxxxxxx`\n\n"
            "⚠️ **Rules:**\n"
            "1. You must be the **Owner/Admin** of that channel/group.\n"
            "2. Make sure this bot is added as an **Admin with Post Messages**."
        )
    elif cb.data == "btn_set_category":
        USER_STEPS[uid] = "WAIT_CAT"
        await cb.message.reply_text("📂 Send your Channel / Group Category (e.g. Mod Apps, Movies, Tech):")
    elif cb.data == "btn_set_tag":
        USER_STEPS[uid] = "WAIT_TAG"
        await cb.message.reply_text("🏷 Send your File Suffix Tag (e.g. `@MyChannel`):")
    elif cb.data == "btn_set_lang":
        USER_STEPS[uid] = "WAIT_LANG"
        await cb.message.reply_text("🌐 Send language names to wipe out (e.g. `bengali, hindi, arabic`):")

@bot.on_message(filters.private & ~filters.command(["start", "help"]))
async def message_dispatcher(client, message):
    uid = str(message.from_user.id)
    u_data = db_get(f"users/{uid}")
    g_data = db_get("global_config")

    if u_data.get("is_banned", False):
        if can_send_warning(uid): await message.reply_text("🚫 You are banned from using this service.")
        return

    missing = await get_missing_subs(client, message.from_user.id)
    if missing:
        if can_send_warning(uid):
            await message.reply_text("⚠️ Unsubscribed from mandatory channels detected! Run `/start` to verify.")
        return

    # Handle Step-by-Step Inputs (With Admin Ownership Verification)
    step = USER_STEPS.get(uid)
    if step and message.text and not message.forward_date:
        txt = message.text.strip()
        if step == "WAIT_CH_ID":
            try:
                ch_target = int(txt) if (txt.startswith("-") or txt.isdigit()) else txt
                
                # SECURITY CHECK: Verify if the user is actually an Admin of this channel
                try:
                    user_member = await client.get_chat_member(ch_target, message.from_user.id)
                    if user_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                        await message.reply_text("❌ **Access Denied:** You are NOT an Admin or Owner of this channel/group!")
                        return
                except Exception as perm_err:
                    await message.reply_text(f"❌ **Verification Failed:** Make sure the bot is an Admin in that channel!\nError: `{perm_err}`")
                    return

                # Send confirmation into channel
                await client.send_message(ch_target, "🤖 **AutoPost Manager verified & connected successfully!**")
                db_put(f"users/{uid}/target_channel", ch_target)
                USER_STEPS.pop(uid, None)
                await message.reply_text(f"✅ Target (`{ch_target}`) connected and verified successfully!")
            except Exception as e:
                await message.reply_text(f"❌ Invalid Channel ID! Error: `{e}`")
            return
        elif step == "WAIT_CAT":
            db_put(f"users/{uid}/channel_category", txt)
            USER_STEPS.pop(uid, None)
            await message.reply_text(f"✅ Category set to: **{txt}**")
            return
        elif step == "WAIT_TAG":
            db_put(f"users/{uid}/channel_tag", txt)
            USER_STEPS.pop(uid, None)
            await message.reply_text(f"✅ Suffix Tag set to: `{txt}`")
            return
        elif step == "WAIT_LANG":
            db_put(f"users/{uid}/remove_languages", txt)
            USER_STEPS.pop(uid, None)
            await message.reply_text(f"✅ Language filter set to: `{txt}`")
            return

    # Target destination check
    target_raw = u_data.get("target_channel")
    if not target_raw:
        if can_send_warning(uid):
            btns = InlineKeyboardMarkup([
                [InlineKeyboardButton("📡 Connect Channel / Group", callback_data="btn_connect_channel")],
                [InlineKeyboardButton("⚙️ Open Mini App Settings", web_app=WebAppInfo(url=RENDER_URL))]
            ])
            await message.reply_text("⚠️ No channel/group connected yet! Click below to connect:", reply_markup=btns)
        return

    try:
        target_channel = int(target_raw) if str(target_raw).startswith("-") or str(target_raw).isdigit() else target_raw
    except:
        target_channel = target_raw

    # PROCESS AND FORWARD POST (NEVER CONNECTS ANY CHANNEL HERE)
    status = await message.reply_text("⏳ Processing post for your channel/group...")

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

        await status.edit_text("✅ Successfully posted to your channel/group!")

        # Post link inspection for Admin Panel
        post_link = ""
        f_chat = message.forward_from_chat
        if f_chat and f_chat.username and message.forward_from_message_id:
            post_link = f"https://t.me/{f_chat.username}/{message.forward_from_message_id}"
        elif u_data.get("channel_username") and sent_msg:
            post_link = f"https://t.me/{u_data['channel_username'].replace('@','')}/{sent_msg.id}"

        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": uid, "user_name": message.from_user.first_name or "User",
            "channel": target_channel, "category": u_data.get("channel_category", "General"),
            "post_link": post_link,
            "content": (message.caption or message.text or getattr(message.document, 'file_name', 'Media File'))[:45]
        })
        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        await status.edit_text(f"❌ Failed to post: {e}")

async def main():
    await bot.start()
    print(">>> AutoPost Secure Bot is Running! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
