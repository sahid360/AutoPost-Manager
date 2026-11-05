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

# Global Settings Init
g_cfg = db_get("global_config")
if not g_cfg:
    db_put("global_config", {
        "force_channels": "@PhProMod",
        "global_blocked_words": "scam, fraud, 18+",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# ==========================================
# 100% ENGLISH UNIFIED MINI APP & ADMIN PANEL
# ==========================================
UNIFIED_WEB_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoPost Control Center</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: #070b14;
            --card: #0f172a;
            --input: #030712;
            --border: #1e293b;
            --accent: #38bdf8;
            --text: #f8fafc;
            --muted: #94a3b8;
            --danger: #ef4444;
            --success: #22c55e;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 14px; }
        .card { background: var(--card); border-radius: 14px; padding: 18px; border: 1px solid var(--border); box-shadow: 0 8px 20px rgba(0,0,0,0.6); margin-bottom: 15px; }
        h3 { margin-top: 0; color: var(--accent); font-size: 16px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        label { display: block; font-size: 13px; color: var(--muted); margin-top: 14px; font-weight: 600; }
        input[type="text"], input[type="password"], textarea, select { width: 100%; padding: 11px; border-radius: 8px; border: 1px solid var(--border); background: var(--input); color: #fff; margin-top: 6px; box-sizing: border-box; font-size: 14px; }
        textarea { height: 75px; resize: none; }
        .helper-link { font-size: 12px; color: var(--accent); margin-top: 5px; display: block; text-decoration: none; }
        button { width: 100%; background: #0284c7; color: #fff; padding: 13px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 18px; }
        .alert { text-align: center; margin-top: 12px; font-size: 14px; font-weight: bold; }
        
        /* Master Admin Styles */
        #admin_panel { display: none; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 15px 0; }
        .stat-card { background: #0b1120; border: 1px solid var(--border); padding: 12px; border-radius: 8px; text-align: center; }
        .stat-card-title { font-size: 12px; color: var(--muted); text-transform: uppercase; }
        .stat-num { font-size: 22px; font-weight: bold; color: var(--accent); margin-top: 4px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        .avatar { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; background: #1e293b; border: 1px solid var(--border); }
        .logs-box { max-height: 280px; overflow-y: auto; background: #030712; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-family: monospace; font-size: 11px; }
        .log-item { padding: 8px 0; border-bottom: 1px solid #111827; display: flex; gap: 10px; align-items: flex-start; }
        .hidden-admin-btn { background: transparent; border: 1px dashed #334155; color: #64748b; font-size: 11px; padding: 8px; border-radius: 8px; margin-top: 30px; }
        .btn-sm { padding: 5px 10px; font-size: 11px; border-radius: 6px; width: auto; margin-top: 0; }
        .btn-danger { background: var(--danger); }
    </style>
</head>
<body>

    <!-- 1. USER CONFIGURATION VIEW -->
    <div id="user_view">
        <div class="card">
            <h3>⚡ AutoPost Channel / Group Setup</h3>
            
            <label>Target Channel or Group ID:</label>
            <input type="text" id="target_channel" placeholder="-100xxxxxxxxxx">
            <a class="helper-link" href="https://t.me/userinfobot" target="_blank">🔍 Get ID from @userinfobot</a>

            <label>Channel Category:</label>
            <select id="channel_category">
                <option value="Mod Apps">Mod Apps & Games</option>
                <option value="Movies & Series">Movies & Web Series</option>
                <option value="Tech & Software">Tech & Software</option>
                <option value="Anime">Anime & Cartoons</option>
                <option value="Gaming">Gaming & Esports</option>
                <option value="News & Updates">News & Updates</option>
                <option value="Crypto & Airdrop">Crypto & Trading</option>
                <option value="Education">Education & Books</option>
                <option value="General">General / Others</option>
            </select>

            <label>File Suffix Tag:</label>
            <input type="text" id="channel_tag" placeholder="@MyChannel">

            <label>Languages to Wipe Out (Type names, comma-separated):</label>
            <input type="text" id="remove_languages" placeholder="e.g. bengali, hindi, arabic, urdu">

            <label>Custom Words to Remove (comma-separated):</label>
            <input type="text" id="blocked_words" placeholder="badword1, @foreignchannel, watermark">

            <label>Post Footer / Credits:</label>
            <textarea id="footer_text" placeholder="⌲ @MyChannel&#10;Share with friends 👥"></textarea>

            <button onclick="saveUserConfig()">💾 Save Settings</button>
            <div id="status_alert" class="alert"></div>
        </div>

        <button class="hidden-admin-btn" onclick="openAdminPortal()">🔒 Master Admin Portal</button>
    </div>

    <!-- 2. SECRET MASTER ADMIN PANEL (PROTECTED) -->
    <div id="admin_panel">
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; border: none; padding: 0;">👑 Master SaaS Admin Control</h3>
                <button class="btn-sm" style="background: #334155;" onclick="closeAdminPortal()">Exit</button>
            </div>

            <!-- 4 Precise Analytics Cards -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-card-title">Total Users</div>
                    <div class="stat-num" id="adm_total_users">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">Today Users</div>
                    <div class="stat-num" id="adm_today_users">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">Total Posts</div>
                    <div class="stat-num" id="adm_total_posts">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">Today Posts</div>
                    <div class="stat-num" id="adm_today_posts">0</div>
                </div>
            </div>

            <label>Change Admin Secret PIN:</label>
            <input type="password" id="new_admin_pin" placeholder="Enter new PIN">

            <label>Mandatory Join Channels (Comma-separated):</label>
            <input type="text" id="adm_force_channels" placeholder="@PhProMod, @ChannelTwo">

            <label>Global Blocked Words (Posts containing these will be blocked):</label>
            <textarea id="adm_global_words" placeholder="scam, 18+, fraud"></textarea>

            <button onclick="saveAdminPolicies()">💾 Save Global Policies</button>
        </div>

        <!-- Registered Users Overview with Avatar -->
        <div class="card">
            <h3>👥 Users Overview</h3>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr><th>Profile</th><th>Target Channel</th><th>Category</th><th>Action</th></tr>
                    </thead>
                    <tbody id="users_tbody"><tr><td colspan="4">Loading...</td></tr></tbody>
                </table>
            </div>
        </div>

        <!-- Live Post Stream with Clear History Button -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; border: none; padding: 0;">📡 Live Post Stream</h3>
                <button class="btn-sm btn-danger" onclick="clearAllLogs()">🗑️ Clear All Logs</button>
            </div>
            <div class="logs-box" id="logs_container">Loading stream...</div>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user = tg.initDataUnsafe?.user || { id: "demo_user", first_name: "User" };
        const FIREBASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";
        let CURRENT_ADMIN_PIN = "1234";

        async function init() {
            try {
                const res = await fetch(`${FIREBASE}/users/${user.id}.json`);
                const data = await res.json();
                if(data) {
                    document.getElementById('target_channel').value = data.target_channel || "";
                    if(data.channel_category) document.getElementById('channel_category').value = data.channel_category;
                    document.getElementById('channel_tag').value = data.channel_tag || "";
                    document.getElementById('remove_languages').value = data.remove_languages || "";
                    document.getElementById('blocked_words').value = data.blocked_words || "";
                    document.getElementById('footer_text').value = data.footer_text || "";
                }
                const gRes = await fetch(`${FIREBASE}/global_config.json`);
                const gData = await gRes.json();
                if(gData && gData.admin_pin) CURRENT_ADMIN_PIN = gData.admin_pin;
            } catch(e) {}
        }

        async function saveUserConfig() {
            const al = document.getElementById('status_alert');
            al.style.color = '#38bdf8'; al.innerText = "Saving settings...";
            const payload = {
                target_channel: document.getElementById('target_channel').value.trim(),
                channel_category: document.getElementById('channel_category').value,
                channel_tag: document.getElementById('channel_tag').value.trim(),
                remove_languages: document.getElementById('remove_languages').value.trim(),
                blocked_words: document.getElementById('blocked_words').value.trim(),
                footer_text: document.getElementById('footer_text').value,
                username: user.username || "", first_name: user.first_name || ""
            };
            await fetch(`${FIREBASE}/users/${user.id}.json`, { method: 'PATCH', body: JSON.stringify(payload) });
            al.style.color = '#4ade80'; al.innerText = "✅ Successfully Saved!";
            setTimeout(() => tg.close(), 1200);
        }

        async function openAdminPortal() {
            const entered = prompt("🔑 Enter Admin Secret Password / PIN:");
            if(!entered) return;

            const gRes = await fetch(`${FIREBASE}/global_config.json`);
            const gData = await gRes.json();
            const realPin = (gData && gData.admin_pin) ? gData.admin_pin : CURRENT_ADMIN_PIN;

            if(entered === realPin) {
                document.getElementById('user_view').style.display = 'none';
                document.getElementById('admin_panel').style.display = 'block';
                loadAdminData();
            } else {
                alert("❌ Wrong Admin PIN! Access Denied.");
            }
        }

        function closeAdminPortal() {
            document.getElementById('admin_panel').style.display = 'none';
            document.getElementById('user_view').style.display = 'block';
        }

        async function loadAdminData() {
            try {
                const gRes = await fetch(`${FIREBASE}/global_config.json`);
                const gData = await gRes.json() || {};
                document.getElementById('adm_force_channels').value = gData.force_channels || "";
                document.getElementById('adm_global_words').value = gData.global_blocked_words || "";
                document.getElementById('new_admin_pin').value = gData.admin_pin || "1234";

                const today = new Date().toISOString().split('T')[0];
                const stats = gData.daily_stats || {};
                document.getElementById('adm_today_posts').innerText = stats[today] || 0;
                let totPosts = 0; Object.values(stats).forEach(c => totPosts += c);
                document.getElementById('adm_total_posts').innerText = totPosts;

                // Load Users & Today Users Count
                const uRes = await fetch(`${FIREBASE}/users.json`);
                const users = await uRes.json() || {};
                const uKeys = Object.keys(users);
                document.getElementById('adm_total_users').innerText = uKeys.length;

                let todayUsersCount = 0;
                let uHtml = "";
                for(let uid of uKeys) {
                    const u = users[uid];
                    if(u.created_at === today) todayUsersCount++;
                    const isBanned = u.is_banned === true;
                    const photo = u.photo_url || "https://cdn-icons-png.flaticon.com/512/149/149071.png";

                    uHtml += `<tr>
                        <td>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <img src="${photo}" class="avatar" onerror="this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png'">
                                <div><b>${u.first_name || 'User'}</b><br><small>@${u.username || uid}</small></div>
                            </div>
                        </td>
                        <td><code>${u.target_channel || 'None'}</code></td>
                        <td>${u.channel_category || 'General'}</td>
                        <td>
                            <button class="btn-sm" style="background:${isBanned?'#22c55e':'#ef4444'};" onclick="toggleBan('${uid}', ${!isBanned})">
                                ${isBanned?'Unban':'Ban'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById('adm_today_users').innerText = todayUsersCount;
                document.getElementById('users_tbody').innerHTML = uHtml || "<tr><td colspan='4'>No users registered.</td></tr>";

                // Load Logs with Avatars
                const lRes = await fetch(`${FIREBASE}/post_logs.json`);
                const logs = await lRes.json() || {};
                const logArr = Object.values(logs).reverse().slice(0, 35);
                let lHtml = "";
                logArr.forEach(l => {
                    const btn = l.post_link ? `<a href="${l.post_link}" target="_blank" style="color:#38bdf8; font-weight:bold; margin-left:6px;">[View Post]</a>` : '';
                    const logAvatar = l.photo_url || "https://cdn-icons-png.flaticon.com/512/149/149071.png";
                    lHtml += `<div class="log-item">
                        <img src="${logAvatar}" class="avatar" style="width:28px; height:28px;" onerror="this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png'">
                        <div>
                            <b>[${l.time}]</b> ${l.user_name} &rarr; <code>${l.channel}</code> (${l.category}) ${btn}<br>
                            <span style="color:#94a3b8;">${l.content}</span>
                        </div>
                    </div>`;
                });
                document.getElementById('logs_container').innerHTML = lHtml || "No recent activity.";
            } catch(e) {}
        }

        async function clearAllLogs() {
            if(!confirm("Are you sure you want to clear all live post logs?")) return;
            await fetch(`${FIREBASE}/post_logs.json`, { method: 'DELETE' });
            loadAdminData();
        }

        async function saveAdminPolicies() {
            const gRes = await fetch(`${FIREBASE}/global_config.json`);
            const gData = await gRes.json() || {};
            const newPin = document.getElementById('new_admin_pin').value.trim();
            if(newPin) gData.admin_pin = newPin;
            gData.force_channels = document.getElementById('adm_force_channels').value.trim();
            gData.global_blocked_words = document.getElementById('adm_global_words').value.trim();

            await fetch(`${FIREBASE}/global_config.json`, { method:'PUT', body:JSON.stringify(gData) });
            alert("✅ Policies & PIN updated successfully!");
        }

        async function toggleBan(uid, banStatus) {
            await fetch(`${FIREBASE}/users/${uid}/is_banned.json`, { method:'PUT', body:JSON.stringify(banStatus) });
            loadAdminData();
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
        self.wfile.write(UNIFIED_WEB_APP_HTML.encode('utf-8'))
    def log_message(self, format, *args): return

def run_http():
    port = int(os.environ.get("PORT", 8080))
    s = HTTPServer(("0.0.0.0", port), WebServer)
    s.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# --- Force Subscription Check ---
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
    "chinese": r'[\u4E00-\u9FFF]+', "japanese": r'[\u3040-\u309F\u30A0-\u30FF]+',
    "korean": r'[\uAC00-\uD7AF\u1100-\u11FF]+', "english": r'[a-zA-Z]+'
}

def clean_post_text(text, u_data, g_data):
    if not text: text = ""
    g_blocked = g_data.get("global_blocked_words", "")
    for word in g_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None

    # User Blocked Words
    u_blocked = u_data.get("blocked_words", "")
    if u_blocked:
        for word in u_blocked.split(","):
            w = word.strip()
            if w: text = re.sub(re.escape(w), '', text, flags=re.IGNORECASE)

    # Dynamic Language Removal
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
    today = datetime.utcnow().strftime("%Y-%m-%d")
    u_data = db_get(f"users/{uid}")
    
    photo_url = f"https://t.me/i/userpic/320/{message.from_user.username}.jpg" if message.from_user.username else ""

    if not u_data:
        db_put(f"users/{uid}", {
            "first_name": message.from_user.first_name or "User",
            "username": message.from_user.username or "",
            "photo_url": photo_url,
            "created_at": today,
            "target_channel": "", "channel_category": "Mod Apps",
            "channel_tag": "@MyChannel", "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_languages": "", "blocked_words": "", "is_banned": False
        })
    elif photo_url and not u_data.get("photo_url"):
        db_put(f"users/{uid}/photo_url", photo_url)

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
        [InlineKeyboardButton("🏷 Suffix Tag", callback_data="btn_set_tag")],
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
            "🔍 **[Get ID from @userinfobot](https://t.me/userinfobot)** (Click to find ID)\n\n"
            "⚠️ **Rules:**\n"
            "1. You must be the **Owner/Admin** of that channel/group.\n"
            "2. Make sure this bot is added as an **Admin with Post Messages**."
        )
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

    # Handle Step-by-Step Inputs
    step = USER_STEPS.get(uid)
    if step and message.text and not message.forward_date:
        txt = message.text.strip()
        if step == "WAIT_CH_ID":
            try:
                ch_target = int(txt) if (txt.startswith("-") or txt.isdigit()) else txt
                try:
                    user_member = await client.get_chat_member(ch_target, message.from_user.id)
                    if user_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                        await message.reply_text("❌ **Access Denied:** You are NOT an Admin or Owner of this channel/group!")
                        return
                except Exception as perm_err:
                    await message.reply_text(f"❌ **Verification Failed:** Make sure the bot is an Admin in that channel!\nError: `{perm_err}`")
                    return

                await client.send_message(ch_target, "🤖 **AutoPost Manager verified & connected successfully!**")
                db_put(f"users/{uid}/target_channel", ch_target)
                USER_STEPS.pop(uid, None)
                await message.reply_text(f"✅ Target (`{ch_target}`) connected and verified successfully!")
            except Exception as e:
                await message.reply_text(f"❌ Invalid Channel ID! Error: `{e}`")
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

        post_link = ""
        f_chat = message.forward_from_chat
        if f_chat and f_chat.username and message.forward_from_message_id:
            post_link = f"https://t.me/{f_chat.username}/{message.forward_from_message_id}"
        elif u_data.get("channel_username") and sent_msg:
            post_link = f"https://t.me/{u_data['channel_username'].replace('@','')}/{sent_msg.id}"

        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user_id": uid, "user_name": message.from_user.first_name or "User",
            "photo_url": u_data.get("photo_url", ""),
            "channel": target_channel, "category": u_data.get("channel_category", "Mod Apps"),
            "post_link": post_link,
            "content": (message.caption or message.text or getattr(message.document, 'file_name', 'Media File'))[:45]
        })
        curr = db_get(f"global_config/daily_stats/{today}")
        db_put(f"global_config/daily_stats/{today}", (curr if isinstance(curr, int) else 0) + 1)

    except Exception as e:
        err_str = str(e)
        if "PEER_ID_INVALID" in err_str or "Peer id invalid" in err_str:
            await status.edit_text(
                "❌ **Failed to post: Peer ID Invalid!**\n\n"
                "👉 **Please forward ANY post from your channel to this bot**, so the bot can recognize your channel!"
            )
        else:
            await status.edit_text(f"❌ Failed to post: {err_str}")

async def main():
    await bot.start()
    print(">>> 100% English Multi-User SaaS Bot Running! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
