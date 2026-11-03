import os
import re
import asyncio
import threading
import json
import time
from datetime import datetime
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# Event Loop setup for Cloud Hosting
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant

# --- Bot Credentials ---
API_ID = 34563277
API_HASH = "7cc2cab7ad6241204f83c0a7fe52e5df"
BOT_TOKEN = "9243394920:AAGg8P8oWdJOETRt6yBvBhDEJTnkrEMKNlM"

# Super Admin Telegram ID (আপনার পার্সোনাল টেলিগ্রাম আইডি)
SUPER_ADMIN_ID = 34563277 # এখানে আপনার টেলিগ্রামের নিজস্ব ইউজার আইডি দিতে পারেন

# Firebase URL
FIREBASE_BASE_URL = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com"

# --- Firebase Helper Functions ---
def db_get(endpoint):
    try:
        r = requests.get(f"{FIREBASE_BASE_URL}/{endpoint}.json", timeout=5)
        return r.json() or {}
    except:
        return {}

def db_put(endpoint, data):
    try:
        requests.put(f"{FIREBASE_BASE_URL}/{endpoint}.json", json=data, timeout=5)
    except:
        pass

def db_post(endpoint, data):
    try:
        requests.post(f"{FIREBASE_BASE_URL}/{endpoint}.json", json=data, timeout=5)
    except:
        pass

# Ensure Global Config exists
global_cfg = db_get("global_config")
if not global_cfg:
    db_put("global_config", {
        "force_channel": "@PhProMod",
        "global_blocked_words": "scam, fraud, 18+, betting",
        "admin_pin": "1234",
        "daily_stats": {}
    })

# --- Web Server & Super Admin Dashboard ---
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Master Admin Panel</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 15px; }
        .container { max-width: 900px; margin: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 15px; }
        h1 { font-size: 20px; color: #38bdf8; margin: 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #111827; padding: 16px; border-radius: 10px; border: 1px solid #1f2937; text-align: center; }
        .stat-num { font-size: 26px; font-weight: bold; color: #38bdf8; margin-top: 5px; }
        .card { background: #111827; padding: 20px; border-radius: 10px; border: 1px solid #1f2937; margin-bottom: 20px; }
        h3 { margin-top: 0; color: #93c5fd; font-size: 16px; }
        label { font-size: 13px; color: #9ca3af; display: block; margin-top: 10px; }
        input[type="text"], input[type="password"], textarea { width: 100%; padding: 10px; background: #1f2937; border: 1px solid #374151; border-radius: 6px; color: #fff; margin-top: 5px; box-sizing: border-box; }
        button { background: #0284c7; color: #fff; border: none; padding: 10px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 15px; }
        button:hover { background: #0369a1; }
        .ban-btn { background: #dc2626; padding: 5px 10px; font-size: 12px; }
        .unban-btn { background: #16a34a; padding: 5px 10px; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; }
        th { color: #9ca3af; }
        .logs-box { max-height: 250px; overflow-y: auto; font-family: monospace; font-size: 12px; background: #030712; padding: 10px; border-radius: 6px; }
        .log-item { padding: 4px 0; border-bottom: 1px solid #111827; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AutoPost Manager SaaS Control</h1>
            <div>
                <input type="password" id="admin_pin" placeholder="PIN (Default: 1234)" style="width: 120px; padding: 6px;">
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div>Total Users</div>
                <div class="stat-num" id="total_users">0</div>
            </div>
            <div class="stat-card">
                <div>Posts Today</div>
                <div class="stat-num" id="posts_today">0</div>
            </div>
            <div class="stat-card">
                <div>Total Lifetime Posts</div>
                <div class="stat-num" id="total_posts">0</div>
            </div>
        </div>

        <!-- Global Settings -->
        <div class="card">
            <h3>🌐 Global Platform Settings</h3>
            <label>Mandatory Join Channel (Force Sub):</label>
            <input type="text" id="force_channel" placeholder="@ChannelUsername">

            <label>Global Blocked Words (Posts containing these will be deleted/removed, comma-separated):</label>
            <textarea id="global_blocked_words" placeholder="badword1, scam, link"></textarea>

            <button onclick="saveGlobalConfig()">Save Global Settings</button>
        </div>

        <!-- Users Management -->
        <div class="card">
            <h3>👥 Registered Users Management</h3>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Target Channel</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="users_table"></tbody>
            </table>
        </div>

        <!-- Live Activity Logs -->
        <div class="card">
            <h3>📜 Live Posting Logs (Recent Activities)</h3>
            <div class="logs-box" id="logs_container">Loading activities...</div>
        </div>
    </div>

    <script>
        const FIREBASE_BASE = "https://autopost-manager-c91ed-default-rtdb.firebaseio.com";

        async function loadDashboard() {
            try {
                // Fetch Global Config
                const gRes = await fetch(`${FIREBASE_BASE}/global_config.json`);
                const gData = await gRes.json() || {};
                document.getElementById('force_channel').value = gData.force_channel || "";
                document.getElementById('global_blocked_words').value = gData.global_blocked_words || "";

                // Today stats
                const today = new Date().toISOString().split('T')[0];
                const stats = gData.daily_stats || {};
                document.getElementById('posts_today').innerText = stats[today] || 0;
                
                let totalPosts = 0;
                Object.values(stats).forEach(v => totalPosts += v);
                document.getElementById('total_posts').innerText = totalPosts;

                // Fetch Users
                const uRes = await fetch(`${FIREBASE_BASE}/users.json`);
                const users = await uRes.json() || {};
                const uKeys = Object.keys(users);
                document.getElementById('total_users').innerText = uKeys.length;

                let tableHtml = "";
                for(let uid of uKeys) {
                    const u = users[uid];
                    const isBanned = u.is_banned === true;
                    tableHtml += `<tr>
                        <td><b>${uid}</b><br><small>${u.username ? '@'+u.username : ''}</small></td>
                        <td>${u.target_channel || 'Not Connected'}</td>
                        <td><span style="color: ${isBanned ? '#ef4444' : '#22c55e'}">${isBanned ? 'Banned' : 'Active'}</span></td>
                        <td>
                            <button class="${isBanned ? 'unban-btn' : 'ban-btn'}" onclick="toggleBan('${uid}', ${!isBanned})">
                                ${isBanned ? 'Unban' : 'Ban'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById('users_table').innerHTML = tableHtml || "<tr><td colspan='4'>No users registered yet.</td></tr>";

                // Fetch Logs
                const lRes = await fetch(`${FIREBASE_BASE}/post_logs.json`);
                const logs = await lRes.json() || {};
                const logList = Object.values(logs).reverse().slice(0, 30);
                let logHtml = "";
                logList.forEach(l => {
                    logHtml += `<div class="log-item"><b>[${l.time}]</b> User: <code>${l.user}</code> posted to <code>${l.channel}</code>: <i>${l.title}</i></div>`;
                });
                document.getElementById('logs_container').innerHTML = logHtml || "No recent activity.";

            } catch(e) {
                console.error(e);
            }
        }

        async function saveGlobalConfig() {
            const pin = document.getElementById('admin_pin').value;
            const gRes = await fetch(`${FIREBASE_BASE}/global_config.json`);
            const gData = await gRes.json() || {};
            if(pin !== (gData.admin_pin || "1234")) {
                alert("❌ Invalid Admin PIN!");
                return;
            }

            gData.force_channel = document.getElementById('force_channel').value.trim();
            gData.global_blocked_words = document.getElementById('global_blocked_words').value.trim();

            await fetch(`${FIREBASE_BASE}/global_config.json`, {
                method: 'PUT',
                body: JSON.stringify(gData)
            });
            alert("✅ Global Settings Saved!");
        }

        async function toggleBan(uid, banStatus) {
            const pin = document.getElementById('admin_pin').value;
            const gRes = await fetch(`${FIREBASE_BASE}/global_config.json`);
            const gData = await gRes.json() || {};
            if(pin !== (gData.admin_pin || "1234")) {
                alert("❌ Invalid PIN!");
                return;
            }

            await fetch(`${FIREBASE_BASE}/users/${uid}/is_banned.json`, {
                method: 'PUT',
                body: JSON.stringify(banStatus)
            });
            loadDashboard();
        }

        window.onload = loadDashboard;
        setInterval(loadDashboard, 15000); // auto-refresh every 15s
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

# --- Telegram Bot Engine ---
bot = Client("ph_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Helper: Check Force Subscription
async def check_force_sub(client, user_id):
    cfg = db_get("global_config")
    channel = cfg.get("force_channel", "").strip()
    if not channel:
        return True
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        return False
    except UserNotParticipant:
        return False
    except Exception as e:
        return True # In case channel is invalid or bot not in force channel

# Language Filter Regex Table
LANG_REGEX = {
    "bengali": r'[\u0980-\u09FF]+',
    "arabic": r'[\u0600-\u06FF]+',
    "hindi": r'[\u0900-\u097F]+',
    "urdu": r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    "russian": r'[\u0400-\u04FF]+'
}

def clean_post_text(text, user_settings, global_settings):
    if not text:
        text = ""

    # 1. Global Blocked Words filter
    global_blocked = global_settings.get("global_blocked_words", "")
    for word in global_blocked.split(","):
        w = word.strip()
        if w and re.search(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE):
            return None # Cancel post if global blacklisted word found

    # 2. User Blocked Words
    user_blocked = user_settings.get("blocked_words", "")
    for word in user_blocked.split(","):
        w = word.strip()
        if w:
            text = re.sub(re.escape(w), '', text, flags=re.IGNORECASE)

    # 3. User Target Language Removal
    target_langs = user_settings.get("remove_languages", "bengali")
    for lang in target_langs.split(","):
        lang = lang.strip().lower()
        if lang in LANG_REGEX:
            text = re.sub(LANG_REGEX[lang], '', text)

    # 4. Remove unwanted symbols/emojis
    emojis = user_settings.get("remove_emojis", "⌲, 💫")
    for emo in emojis.split(","):
        emo = emo.strip()
        if emo:
            text = text.replace(emo, "")

    # 5. Clean external links & usernames
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'Share It With Your Friends.*', '', text, flags=re.IGNORECASE)

    # 6. Format lines & First Line Bold
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    footer = user_settings.get("footer_text", "")

    if not lines:
        return footer

    if user_settings.get("bold_first_line", True):
        first_line = lines[0]
        first_line_clean = re.sub(r'^\*+|\*+$', '', first_line).strip()
        lines[0] = f"**{first_line_clean}**"

    body = f"{lines[0]}\n\n" + "\n".join(lines[1:]) if len(lines) > 1 else lines[0]
    return f"{body}\n\n{footer}".strip() if footer else body.strip()

def clean_app_filename(original_name, channel_tag):
    if not original_name:
        original_name = "application.apk"
    base, ext = os.path.splitext(original_name)
    base_clean = re.sub(r'@\w+', '', base)
    base_clean = re.sub(r'\[.*?\]|\(.*?\)', '', base_clean)
    base_clean = re.sub(r'[\s\-_]+$', '', base_clean).strip()
    base_clean = " ".join(base_clean.split())
    if not base_clean:
        base_clean = "App"
    return f"{base_clean} {channel_tag}{ext}" if channel_tag else f"{base_clean}{ext}"

# --- Bot Commands ---

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""

    # Register User in DB
    u_data = db_get(f"users/{user_id}")
    if not u_data:
        db_put(f"users/{user_id}", {
            "username": username,
            "target_channel": "",
            "channel_tag": "@MyChannel",
            "footer_text": "⌲ @MyChannel\nShare with friends 👥",
            "remove_emojis": "⌲, 💫",
            "remove_languages": "bengali",
            "blocked_words": "",
            "bold_first_line": True,
            "is_banned": False
        })

    # Check Ban Status
    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this bot by the administrator.")
        return

    # Check Force Sub
    is_subbed = await check_force_sub(client, message.from_user.id)
    if not is_subbed:
        cfg = db_get("global_config")
        ch = cfg.get("force_channel", "@PhProMod")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Our Channel", url=f"https://t.me/{ch.replace('@','')}")],
                                    [InlineKeyboardButton("🔄 Verify & Refresh", callback_data="check_sub")]])
        await message.reply_text(f"⚠️ **Access Denied!**\n\nYou must join our official channel **{ch}** to use this bot.", reply_markup=btn)
        return

    # Welcome Menu
    msg = (
        "👋 **Welcome to AutoPost SaaS Manager!**\n\n"
        "You can use this bot to auto-post, rename files, and clean foreign links for your own Telegram channel.\n\n"
        "⚙️ **Commands:**\n"
        "• `/connect` - Connect & verify your channel\n"
        "• `/settings` - Set footer text, tags, and languages to remove\n"
        "• `/status` - Check current connection status"
    )
    await message.reply_text(msg)

@bot.on_callback_query(filters.regex("check_sub"))
async def sub_callback(client, callback_query):
    is_subbed = await check_force_sub(client, callback_query.from_user.id)
    if is_subbed:
        await callback_query.message.edit_text("✅ **Subscription verified!** Now send `/start` to begin.")
    else:
        await callback_query.answer("❌ You haven't joined the channel yet!", show_alert=True)

# Step 1: Channel Connect Command
@bot.on_message(filters.command("connect"))
async def connect_cmd(client, message):
    text = (
        "🔗 **How to connect your channel:**\n\n"
        "1. Add this bot to your channel as an **Administrator** with **Post Messages** permission.\n"
        "2. Forward ANY message from your channel to this bot right now.\n\n"
        "The bot will verify the permissions and lock your channel automatically!"
    )
    await message.reply_text(text)

# Step 2: Settings Command
@bot.on_message(filters.command("settings"))
async def settings_cmd(client, message):
    user_id = str(message.from_user.id)
    u_data = db_get(f"users/{user_id}")
    
    help_text = (
        "🛠 **Customize Your Formatting:**\n\n"
        "Send commands to change your preferences:\n"
        "• `/settag @YourTag` -> Set suffix name on files\n"
        "• `/setfooter Your custom footer text` -> Set post footer\n"
        "• `/remlang bengali,hindi` -> Languages to wipe out\n"
        "• `/blockwords word1,word2` -> Custom words to delete"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("settag"))
async def settag_cmd(client, message):
    tag = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if not tag:
        await message.reply_text("Usage: `/settag @YourChannel`")
        return
    db_put(f"users/{message.from_user.id}/channel_tag", tag)
    await message.reply_text(f"✅ Suffix tag set to: `{tag}`")

@bot.on_message(filters.command("setfooter"))
async def setfooter_cmd(client, message):
    footer = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    db_put(f"users/{message.from_user.id}/footer_text", footer)
    await message.reply_text("✅ Footer text updated!")

@bot.on_message(filters.command("remlang"))
async def remlang_cmd(client, message):
    langs = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    db_put(f"users/{message.from_user.id}/remove_languages", langs)
    await message.reply_text(f"✅ Language filter set to: `{langs}` (Supported: bengali, hindi, arabic, urdu, russian)")

# Forward Handler & Forward Processing
@bot.on_message(filters.private)
async def handle_user_posts(client, message):
    user_id = str(message.from_user.id)
    u_data = db_get(f"users/{user_id}")
    g_data = db_get("global_config")

    # 1. Ban Check
    if u_data.get("is_banned", False):
        await message.reply_text("🚫 You are banned from using this service.")
        return

    # 2. Force Sub Check
    is_subbed = await check_force_sub(client, message.from_user.id)
    if not is_subbed:
        await message.reply_text("⚠️ Unsubscribed detected! You must be a member of our channel to use the bot. Run `/start`.")
        return

    # 3. Channel Verification if user forwarded from their channel
    if message.forward_from_chat:
        f_chat = message.forward_from_chat
        try:
            # Test send permission
            test_msg = await client.send_message(f_chat.id, "🤖 **AutoPost Manager connected successfully to this channel!**")
            db_put(f"users/{user_id}/target_channel", f_chat.id)
            await message.reply_text(f"🎉 **Channel Verified:** '{f_chat.title}' (ID: `{f_chat.id}`) is now connected!\n\nNow simply forward any posts, APKs, or videos to post automatically!")
            return
        except Exception as e:
            await message.reply_text(f"❌ **Permission Error:** Make sure this bot is an **Admin with Post Messages** permission in **{f_chat.title}**!\nError: `{e}`")
            return

    # 4. Check if channel connected
    target_channel = u_data.get("target_channel")
    if not target_channel:
        await message.reply_text("⚠️ You haven't connected your channel yet! Send `/connect` first.")
        return

    status = await message.reply_text("⏳ Processing post for your channel...")

    try:
        tag = u_data.get("channel_tag", "")
        today_date = datetime.utcnow().strftime("%Y-%m-%d")

        # Process Media
        if message.video:
            clean_cap = clean_post_text(message.caption, u_data, g_data)
            if clean_cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            new_name = clean_app_filename(message.video.file_name or "video.mp4", tag)
            file_path = await message.download(file_name=new_name)
            await client.send_video(chat_id=target_channel, video=file_path, caption=clean_cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN, supports_streaming=True)
            if os.path.exists(file_path): os.remove(file_path)

        elif message.document:
            clean_cap = clean_post_text(message.caption, u_data, g_data)
            if clean_cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            new_name = clean_app_filename(message.document.file_name, tag)
            file_path = await message.download(file_name=new_name)
            await client.send_document(chat_id=target_channel, document=file_path, caption=clean_cap, file_name=new_name, parse_mode=ParseMode.MARKDOWN)
            if os.path.exists(file_path): os.remove(file_path)

        elif message.photo:
            clean_cap = clean_post_text(message.caption, u_data, g_data)
            if clean_cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            await client.send_photo(chat_id=target_channel, photo=message.photo.file_id, caption=clean_cap, parse_mode=ParseMode.MARKDOWN)

        elif message.text:
            clean_cap = clean_post_text(message.text, u_data, g_data)
            if clean_cap is None:
                await status.edit_text("❌ Post cancelled: Contains global blacklisted word.")
                return
            await client.send_message(chat_id=target_channel, text=clean_cap, parse_mode=ParseMode.MARKDOWN)

        await status.edit_text("✅ Posted successfully to your connected channel!")

        # Update Analytics in Firebase
        db_post("post_logs", {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "user": user_id,
            "channel": target_channel,
            "title": (message.caption or message.text or "Media")[:30] + "..."
        })
        curr_count = db_get(f"global_config/daily_stats/{today_date}")
        new_count = (curr_count if isinstance(curr_count, int) else 0) + 1
        db_put(f"global_config/daily_stats/{today_date}", new_count)

    except Exception as e:
        await status.edit_text(f"❌ Failed to post: {e}")

async def main():
    await bot.start()
    print(">>> Multi-User SaaS Bot is RUNNING! <<<")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
