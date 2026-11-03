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

# --- Firebase API Helpers ---
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
        "force_channel": "@PhProMod",
        "global_blocked_words": "scam, fraud, 18+",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 1. USER TELEGRAM MINI APP (HTML/JS)
# ==========================================
USER_MINIAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Channel Settings</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: sans-serif; background: var(--tg-theme-bg-color, #121824); color: var(--tg-theme-text-color, #fff); margin: 0; padding: 16px; }
        .card { background: var(--tg-theme-secondary-bg-color, #1e293b); border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h3 { margin-top: 0; color: #38bdf8; font-size: 16px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        label { display: block; font-size: 13px; color: #94a3b8; margin-top: 10px; font-weight: bold; }
        input[type="text"], textarea, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #fff; margin-top: 5px; box-sizing: border-box; font-size: 14px; }
        textarea { height: 70px; resize: none; }
        .note { font-size: 12px; color: #38bdf8; margin-top: 4px; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 14px; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 15px; }
        .alert { text-align: center; margin-top: 10px; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h3>⚙️ Setup Your Channel</h3>
        
        <label>Your Target Channel ID (e.g. -100xxxxxxxxxx):</label>
        <input type="text" id="target_channel" placeholder="-1001234567890">
        <div class="note">💡 Bot must be an Admin in your channel with 'Post Messages' permission.</div>

        <label>File Name Suffix Tag:</label>
        <input type="text" id="channel_tag" placeholder="@YourChannel">

        <label>Custom Post Footer Text:</label>
        <textarea id="footer_text" placeholder="⌲ @YourChannel&#10;Share with friends 👥"></textarea>

        <label>Language to Wipe Out / Remove:</label>
        <select id="remove_languages">
            <option value="bengali">Bengali (বাংলা)</option>
            <option value="hindi">Hindi (हिंदी)</option>
            <option value="arabic">Arabic (العربية)</option>
            <option value="urdu">Urdu (اردو)</option>
            <option value="all">Bengali + Hindi + Arabic</option>
            <option value="none">None (Keep All Languages)</option>
        </select>

        <label>Custom Words to Remove (comma-separated):</label>
        <input type="text" id="blocked_words" placeholder="badword1, @foreign_tag">

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
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('footer_text').value = data.footer_text || "";
                    if(data.remove_languages) document.getElementById('remove_languages').value = data.remove_languages;
                    document.getElementById('blocked_words').value = data.blocked_words || "";
                }
            } catch(e) {}
        }

        async function saveUserSettings() {
            const btn = document.getElementById('alert');
            btn.style.color = '#38bdf8';
            btn.innerText = "Saving settings...";

            const payload = {
                target_channel: document.getElementById('target_channel').value.trim(),
                channel_tag: document.getElementById('channel_tag').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                remove_languages: document.getElementById('remove_languages').value,
                blocked_words: document.getElementById('blocked_words').value,
                username: user.username || "",
                first_name: user.first_name || ""
            };

            await fetch(`${FIREBASE}/users/${user.id}.json`, {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });

            btn.style.color = '#4ade80';
            btn.innerText = "✅ Settings updated successfully!";
            setTimeout(() => { tg.close(); }, 1200);
        }
        window.onload = loadData;
    </script>
</body>
</html>
"""

# ==========================================
# 2. OWNER MASTER ADMIN PANEL (HTML/JS)
# ==========================================
OWNER_ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #080c14; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; }
        h1 { font-size: 22px; color: #38bdf8; margin: 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #0f172a; padding: 18px; border-radius: 12px; border: 1px solid #1e293b; text-align: center; }
        .stat-num { font-size: 28px; font-weight: bold; color: #38bdf8; margin-top: 5px; }
        .card { background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }
        h3 { margin-top: 0; color: #93c5fd; font-size: 16px; }
        input[type="text"], input[type="password"], textarea { width: 100%; padding: 10px; background: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #fff; margin-top: 6px; box-sizing: border-box; }
        button { background: #0284c7; color: #fff; border: none; padding: 10px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        button:hover { background: #0369a1; }
        .ban-btn { background: #ef4444; padding: 6px 12px; border-radius: 6px; }
        .unban-btn { background: #22c55e; padding: 6px 12px; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #1e293b; }
        .avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; background: #334155; }
        .user-cell { display: flex; align-items: center; gap: 10px; }
        .logs-box { max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; background: #030712; padding: 12px; border-radius: 8px; border: 1px solid #1e293b; }
        .log-item { padding: 8px; border-bottom: 1px solid #0f172a; display: flex; flex-direction: column; gap: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👑 Master SaaS Admin Control</h1>
            <div>
                <input type="password" id="admin_pin" placeholder="PIN (Default: 1234)" style="width: 140px; padding: 8px; margin: 0;">
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><div>Active Users</div><div class="stat-num" id="total_users">0</div></div>
            <div class="stat-card"><div>Posts Today</div><div class="stat-num" id="posts_today">0</div></div>
            <div class="stat-card"><div>Lifetime Posts</div><div class="stat-num" id="total_posts">0</div></div>
        </div>

        <!-- Global Settings -->
        <div class="card">
            <h3>🌐 Global Platform Policies</h3>
            <label>Mandatory Join Channel (Force Subscription):</label>
            <input type="text" id="force_channel" placeholder="@PhProMod">

            <label style="margin-top: 12px; display:block;">Global Prohibited Words (Posts containing these will be aborted):</label>
            <textarea id="global_blocked_words" placeholder="scam, 18+, betting"></textarea>

            <button style="margin-top: 12px;" onclick="saveGlobal()">💾 Save Global Config</button>
        </div>

        <!-- Registered Users with Profile Pictures -->
        <div class="card">
            <h3>👥 Registered Users Overview</h3>
            <table>
                <thead>
                    <tr>
                        <th>User Profile</th>
                        <th>Target Channel</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="users_table"></tbody>
            </table>
        </div>

        <!-- Live Post Stream (Realtime Interception) -->
        <div class="card">
            <h3>📡 Live User Forward Stream (Inspect what users are posting)</h3>
            <div class="logs-box" id="logs_container">Loading stream...</div>
        </div>
    </div>

    <script>
        const FIREBASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function loadAdmin() {
            try {
                const gRes = await fetch(`${FIREBASE}/global_config.json`);
                const gData = await gRes.json() || {};
                document.getElementById('force_channel').value = gData.force_channel || "";
                document.getElementById('global_blocked_words').value = gData.global_blocked_words || "";

                const today = new Date().toISOString().split('T')[0];
                const stats = gData.daily_stats || {};
                document.getElementById('posts_today').innerText = stats[today] || 0;
                let tot = 0;
                Object.values(stats).forEach(c => tot += c);
                document.getElementById('total_posts').innerText = tot;

                // Load Users
                const uRes = await fetch(`${FIREBASE}/users.json`);
                const users = await uRes.json() || {};
                const uKeys = Object.keys(users);
                document.getElementById('total_users').innerText = uKeys.length;

                let uHtml = "";
                for(let uid of uKeys) {
                    const u = users[uid];
                    const isBanned = u.is_banned === true;
                    const photo = u.photo_url || "https://cdn-icons-png.flaticon.com/512/149/149071.png";
                    uHtml += `<tr>
                        <td>
                            <div class="user-cell">
                                <img src="${photo}" class="avatar">
                                <div>
                                    <b>${u.first_name || 'User'}</b><br>
                                    <small style="color:#94a3b8">@${u.username || 'NoUsername'} | ID: ${uid}</small>
                                </div>
                            </div>
                        </td>
                        <td><code>${u.target_channel || 'Not Connected'}</code></td>
                        <td><span style="color:${isBanned?'#ef4444':'#22c55e'}; font-weight:bold;">${isBanned?'BANNED':'ACTIVE'}</span></td>
                        <td>
                            <button class="${isBanned?'unban-btn':'ban-btn'}" onclick="toggleBan('${uid}', ${!isBanned})">
                                ${isBanned?'Unban':'Ban User'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById('users_table').innerHTML = uHtml || "<tr><td colspan='4'>No users found.</td></tr>";

                // Load Logs
                const lRes = await fetch(`${FIREBASE}/post_logs.json`);
                const logs = await lRes.json() || {};
                const logArr = Object.values(logs).reverse().slice(0, 30);
                let logHtml = "";
                logArr.forEach(l => {
                    logHtml += `<div class="log-item">
                        <div><b>[${l.time}]</b> User: <b>${l.user_name}</b> (<code>${l.user_id}</code>) &rarr; Channel: <code>${l.channel}</code></div>
                        <div style="color: #94a3b8;">Original: <i>${l.content}</i></div>
                    </div>`;
                });
                document.getElementById('logs_container').innerHTML = logHtml || "No recent activity.";

            } catch(e) {}
        }

        async function saveGlobal() {
            const pin = document.getElementById('admin_pin').value;
            const gRes = await fetch(`${FIREBASE}/global_config.json`);
            const gData = await gRes.json() || {};
            if(pin !== (gData.admin_pin || "1234")) {
                alert("❌ Wrong Admin PIN!");
                return;
            }
            gData.force_channel = document.getElementById('force_channel').value.trim();
            gData.global_blocked_words = document.getElementById('global_blocked_words').value.trim();
            await fetch(`${FIREBASE}/global_config.json`, { method:'PUT', body:JSON.stringify(gData) });
            alert("✅ Global rules saved!");
        }

        async function toggleBan(uid, banStatus) {
            const pin = document.getElementById('admin_pin').value;
            const gRes = await fetch(`${FIREBASE}/global_config.json`);
            const gData = await gRes.json() || {};
            if(pin !== (gData.admin_pin || "1234")) {
                alert("❌ Wrong PIN!");
                return;
            }
            await fetch(`${FIREBASE}/users/${uid}/is_banned.json`, { method:'PUT', body:JSON.stringify(banStatus) });
            loadAdmin();
        }

        window.onload = loadAdmin;
        setInterval(loadAdmin, 15000);
    </script>
</body>
</html>
"""

# Route Handler for Server
class MasterRouter(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        # Admin Panel URL: /admin
        if self.path.startswith("/admin"):
            self.wfile.write(OWNER_ADMIN_HTML.encode('utf-8'))
        else:
            # Root URL: Mini App for normal Telegram users
            self.wfile.write(USER_MINIAPP_HTML.encode('utf-8'))
    def log_message(self, format, *args):
        return

def run_http():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), MasterRouter)
    s.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# --- Telegram Bot Engine ---
bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

async def check_force_sub(client, user_id):
    cfg = db_get("global_config")
    channel = cfg.get("force_channel", "").strip()
    if not channel: return True
    try:
        m = await client.get_chat_member(channel, user_id)
        return m.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False
    except:
        return True

LANG_DICT = {
    "bengali": r'[\u0980-\u09FF]+',
    "hindi": r'[\u0900-\u097F]+',
    "arabic": r'[\u0600-\u06FF]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    "all": r'[\u0980-\u09FF\u0900-\u097F\u0600-\u06FF]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""

    # Global Blocked Words
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    # User Blocked Words
    u_blocked = u_data.get("blocked_words", "")
    for word in u_blocked.split(","):
        w = word.strip()
        if w: text = re.sub(re.escape(w), '', text, flags=re.IGNORECASE)

    # Language Filter
    target_lang = u_data.get("remove_languages", "bengali").lower()
    if target_lang in LANG_DICT:
        text = re.sub(LANG_DICT[target_lang], '', text)

    # Emojis & Links
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

# Start Command with Web App Button
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    # Fetch User Profile Photo for Admin Panel
    photo_url = ""
    try:
        photos = [p async for p in client.get_chat_photos(message.from_user.id, limit=1)]
        if photos:
            # Use public Telegram avatar proxy or placeholder
            photo_url = f"https://t.me/i/userpic/320/{username}.jpg" if username else ""
    except:
        pass

    u_data = db_get(f"users/{user_id}")
    if not u_data:
        db_put(f"users/{user_id}", {
            "first_name": first_name,
            "username": username,
            "photo_url": photo_url,
            "target_channel": "",
            "channel_tag": "@MyChannel",
            "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "bengali",
            "blocked_words": "",
            "is_banned": False
        })
    elif photo_url and not u_data.get("photo_url"):
        db_put(f"users/{user_id}/photo_url", photo_url)

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this bot.")
        return

    # Check Force Sub
    subbed = await check_force_sub(client, message.from_user.id)
    if not subbed:
        cfg = db_get("global_config")
        ch = cfg.get("force_channel", "@PhProMod")
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Our Channel", url=f"https://t.me/{ch.replace('@','')}")],
            [InlineKeyboardButton("🔄 Verify & Refresh", callback_data="verify_sub")]
        ])
        await message.reply_text(f"⚠️ **Access Denied!**\n\nYou must join **{ch}** to use this bot.", reply_markup=btn)
        return

    # Open Settings via Telegram Mini App
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Open Settings (Mini App)", web_app=WebAppInfo(url=RENDER_URL))],
        [InlineKeyboardButton("📖 How to Connect Channel", callback_data="help_connect")]
    ])
    await message.reply_text(
        f"👋 **Welcome, {first_name}!**\n\n"
        "Click the button below to easily setup your channel, footer, and language filters without any commands!",
        reply_markup=btn
    )

@bot.on_callback_query()
async def callback_gate(client, cb):
    if cb.data == "verify_sub":
        if await check_force_sub(client, cb.from_user.id):
            await cb.message.edit_text("✅ Verified! Send `/start` to access.")
        else:
            await cb.answer("❌ You have not joined our channel yet!", show_alert=True)
    elif cb.data == "help_connect":
        await cb.message.reply_text(
            "📌 **How to connect your channel:**\n\n"
            "1. Add this bot as an **Administrator** in your channel with **Post Messages** permission.\n"
            "2. Forward ANY message from your channel to this bot.\n"
            "3. The bot will automatically verify and connect your channel!"
        )

# Message & Forward Processor
@bot.on_message(filters.private)
async def message_dispatcher(client, message):
    user_id = str(message.from_user.id)
    u_data = db_get(f"users/{user_id}")
    g_data = db_get("global_config")

    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this service.")
        return

    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text("⚠️ You must join our channel to use this bot! Run `/start`.")
        return

    # Channel Auto-Detect via Forward
    if message.forward_from_chat:
        f_chat = message.forward_from_chat
        try:
            await client.send_message(f_chat.id, "🤖 **AutoPost Manager verified & connected to this channel!**")
            db_put(f"users/{user_id}/target_channel", f_chat.id)
            await message.reply_text(f"🎉 **Channel Verified:** '{f_chat.title}' (`{f_chat.id}`) is successfully connected!")
            return
        except Exception as e:
            await message.reply_text(f"❌ **Permission Failed:** Make sure bot is an Admin with Post Messages in '{f_chat.title}'!")
            return

    target_channel = u_data.get("target_channel")
    if not target_channel:
        await message.reply_text("⚠️ Channel not connected yet! Forward a post from your channel or setup in the Mini App.")
        return

    status = await message.reply_text("⏳ Processing post for your channel...")
    try:
        tag = u_data.get("channel_tag", "")
        today = datetime.utcnow().strftime("%Y-%m-%d")

        if message.video:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            new_name = clean_app_filename(message.video.file_name or "video.mp4", tag)
            fp = await message.download(file_name=new_name)
            await client.send_video(chat_id=target_channel, video=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(fp): os.remove(fp)

        elif message.document:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            new_name = clean_app_filename(message.document.file_name, tag)
            fp = await message.download(file_name=new_name)
            await client.send_document(chat_id=target_channel, document=fp, caption=cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(fp): os.remove(fp)

        elif message.photo:
            cap = clean_post_text(message.caption, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=cap, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            cap = clean_post_text(message.text, u_data, g_data)
            if cap is None:
                await status.edit_text("❌ Post cancelled: Contains blacklisted word.")
                return
            await client.send_message(chat_id=target_channel, text=cap, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Successfully posted to your channel!")

        # Log for Owner Admin Panel
        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": user_id,
            "user_name": message.from_user.first_name or "User",
            "channel": target_channel,
            "content": (message.caption or message.text or message.document.file_name if message.document else "Media")[:40]
        })
        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        await status.edit_text(f"❌ Failed to post: {e}")

async def main():
    await bot.start()
    print(">>> SaaS Bot with Dedicated Admin & MiniApp Live! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
