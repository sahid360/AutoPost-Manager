from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
import os
import re
import sqlite3
import threading
import time
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import qrcode
import requests
import telebot
from telebot import types

# === আপনার আপডেটেড নতুন Bot Token ===
BOT_TOKEN = "9163046758:AAH_F4G9opMsa3CVZavt2pXx0Ey9eOhYBE0"
BOT_USERNAME = "@QRCodeMakerTBot"
DEFAULT_ADMIN_PASS = "Admin"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_sessions = {}
DB_FILE = "bot_master.db"


# === ডাটাবেস সেটআপ ===
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        is_banned INTEGER DEFAULT 0,
        first_seen DATE DEFAULT CURRENT_DATE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS force_chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_username TEXT UNIQUE,
        chat_title TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS channel_joins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_username TEXT,
        user_id INTEGER,
        UNIQUE(chat_username, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_name TEXT,
        act_type TEXT,
        data_input TEXT,
        data_output TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        act_type TEXT,
        act_date DATE DEFAULT CURRENT_DATE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        photo_url TEXT,
        btn_text TEXT,
        btn_url TEXT,
        views INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    c.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_pass', ?)",
        (DEFAULT_ADMIN_PASS,),
    )
    c.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status',"
        " 'on')"
    )
    conn.commit()
    conn.close()


init_db()


# === হেল্পার ডাটাবেস ফাংশন ===
def get_setting(key, default=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO"
        " UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def is_bot_active():
    return get_setting("bot_status", "on") == "on"


def register_user(user):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO users (user_id, first_name, username, first_seen) 
                     VALUES (?, ?, ?, CURRENT_DATE) 
                     ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username""",
            (user.id, user.first_name, user.username or "None"),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")


def is_user_banned(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row["is_banned"])


def log_user_action(user_id, user_name, act_type, data_in, data_out):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO logs (user_id, user_name, act_type, data_input, data_output) 
                     VALUES (?, ?, ?, ?, ?)""",
            (user_id, user_name, act_type, data_in, data_out),
        )
        c.execute(
            "INSERT INTO activity (act_type, act_date) VALUES (?, CURRENT_DATE)",
            (act_type,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log Error: {e}")


# === নিরাপদ Force Subscribe চেকার ===
def check_user_membership(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT chat_username, chat_title FROM force_chats")
    chats = c.fetchall()

    if not chats:
        conn.close()
        return True, []

    missing_chats = []
    for chat in chats:
        username = chat["chat_username"].strip()
        try:
            member = bot.get_chat_member(username, user_id)
            if member.status in ["member", "administrator", "creator"]:
                c.execute(
                    "INSERT OR IGNORE INTO channel_joins (chat_username,"
                    " user_id) VALUES (?, ?)",
                    (username, user_id),
                )
            else:
                missing_chats.append(chat)
        except Exception:
            pass

    conn.commit()
    conn.close()
    return (False, missing_chats) if missing_chats else (True, [])


def make_join_keyboard(missing_chats):
    markup = types.InlineKeyboardMarkup()
    for chat in missing_chats:
        uname = chat["chat_username"].replace("@", "")
        markup.add(
            types.InlineKeyboardButton(
                f"📢 Join {chat['chat_title']}", url=f"https://t.me/{uname}"
            )
        )
    markup.add(
        types.InlineKeyboardButton(
            "✅ Check Membership (যাচাই করুন)", callback_data="recheck_join"
        )
    )
    return markup


# === QR কোড ওয়াটারমার্কসহ তৈরি ===
def generate_styled_qr(link, color_hex="#000000", label_text=None):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(
        fill_color=color_hex, back_color="white"
    ).convert("RGB")

    w, h = qr_img.size
    header_height = 80 if label_text else 0
    footer_height = 36

    combined_img = Image.new(
        "RGB", (w, h + header_height + footer_height), "white"
    )
    combined_img.paste(qr_img, (0, header_height))
    draw = ImageDraw.Draw(combined_img)

    if label_text:
        try:
            font_title = ImageFont.load_default(size=26)
        except:
            font_title = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label_text, font=font_title)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = max((w - text_w) // 2, 10)
        text_y = (header_height - text_h) // 2
        draw.text(
            (text_x, text_y), label_text, fill=color_hex, font=font_title
        )
        draw.text(
            (text_x + 1, text_y), label_text, fill=color_hex, font=font_title
        )

    try:
        font_wm = ImageFont.load_default(size=13)
    except:
        font_wm = ImageFont.load_default()

    wm_text = BOT_USERNAME
    bbox_wm = draw.textbbox((0, 0), wm_text, font=font_wm)
    wm_w = bbox_wm[2] - bbox_wm[0]

    total_h = h + header_height + footer_height
    y_pos = total_h - footer_height + 8
    icon_size = 18
    total_wm_width = icon_size + 6 + wm_w
    x_pos = w - total_wm_width - 15

    draw.ellipse(
        [x_pos, y_pos, x_pos + icon_size, y_pos + icon_size], fill="#0088cc"
    )
    draw.polygon(
        [
            (x_pos + 4, y_pos + 9),
            (x_pos + 14, y_pos + 5),
            (x_pos + 10, y_pos + 14),
            (x_pos + 8, y_pos + 10),
        ],
        fill="white",
    )
    draw.text(
        (x_pos + icon_size + 6, y_pos + 2),
        wm_text,
        fill="#64748b",
        font=font_wm,
    )

    bio = io.BytesIO()
    combined_img.save(bio, "PNG")
    bio.seek(0)
    return bio


def get_qr_buttons():
    markup = types.InlineKeyboardMarkup()
    row1 = [
        types.InlineKeyboardButton("🔵", callback_data="col_#0066FF"),
        types.InlineKeyboardButton("🟢", callback_data="col_#009944"),
        types.InlineKeyboardButton("🟣", callback_data="col_#7700AA"),
        types.InlineKeyboardButton("🔴", callback_data="col_#DD0022"),
        types.InlineKeyboardButton("⚫", callback_data="col_#000000"),
    ]
    row2 = [
        types.InlineKeyboardButton(
            "🏷️ Add Name / Title", callback_data="set_label"
        )
    ]
    markup.row(*row1)
    markup.row(*row2)
    return markup


# === রিয়েল-টাইম অ্যাডমিন প্যানেল ও ওয়েব সার্ভার ===
class WebAdminHandler(BaseHTTPRequestHandler):

    def is_authenticated(self):
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            cookie = SimpleCookie(cookie_header)
            if "admin_logged" in cookie:
                return cookie["admin_logged"].value == "true"
        return False

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        params = urllib.parse.parse_qs(post_data)

        if self.path == "/admin/login":
            entered_pass = params.get("password", [""])[0].strip()
            if entered_pass == get_setting("admin_pass", DEFAULT_ADMIN_PASS):
                self.send_response(303)
                self.send_header(
                    "Set-Cookie", "admin_logged=true; Path=/; Max-Age=604800"
                )
                self.send_header("Location", "/admin")
                self.end_headers()
            else:
                self.send_response(303)
                self.send_header("Location", "/admin?error=wrong_pass")
                self.end_headers()
            return

        if self.path == "/admin/logout":
            self.send_response(303)
            self.send_header("Set-Cookie", "admin_logged=; Path=/; Max-Age=0")
            self.send_header("Location", "/admin")
            self.end_headers()
            return

        if not self.is_authenticated():
            self.send_response(403)
            self.end_headers()
            return

        if self.path == "/admin/toggle_status":
            current_status = get_setting("bot_status", "on")
            new_status = "off" if current_status == "on" else "on"
            set_setting("bot_status", new_status)

        elif self.path == "/admin/change_pass":
            old_p = params.get("old_pass", [""])[0].strip()
            new_p = params.get("new_pass", [""])[0].strip()
            if (
                old_p == get_setting("admin_pass", DEFAULT_ADMIN_PASS)
                and new_p
            ):
                set_setting("admin_pass", new_p)

        elif self.path == "/admin/add_chat":
            chat_user = params.get("chat_username", [""])[0].strip()
            chat_title = params.get("chat_title", ["Channel"])[0].strip()
            if chat_user:
                if not chat_user.startswith("@"):
                    chat_user = f"@{chat_user}"
                conn = get_db()
                c = conn.cursor()
                c.execute(
                    "INSERT OR IGNORE INTO force_chats (chat_username,"
                    " chat_title) VALUES (?, ?)",
                    (chat_user, chat_title),
                )
                conn.commit()
                conn.close()

        elif self.path == "/admin/del_chat":
            chat_id = params.get("id", [""])[0]
            if chat_id:
                conn = get_db()
                c = conn.cursor()
                c.execute("DELETE FROM force_chats WHERE id = ?", (chat_id,))
                conn.commit()
                conn.close()

        elif self.path == "/admin/toggle_ban":
            target_id = params.get("user_id", [""])[0]
            if target_id:
                conn = get_db()
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET is_banned = 1 - is_banned WHERE user_id"
                    " = ?",
                    (target_id,),
                )
                conn.commit()
                conn.close()

        elif self.path == "/admin/clear_logs":
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM logs")
            conn.commit()
            conn.close()

        elif self.path == "/admin/send_sponsor":
            text = params.get("text", [""])[0].strip()
            photo_url = params.get("photo_url", [""])[0].strip()
            btn_text = params.get("btn_text", [""])[0].strip()
            btn_url = params.get("btn_url", [""])[0].strip()
            if text:
                conn = get_db()
                c = conn.cursor()
                c.execute(
                    """INSERT INTO sponsors (text, photo_url, btn_text, btn_url) 
                             VALUES (?, ?, ?, ?)""",
                    (text, photo_url, btn_text, btn_url),
                )
                sponsor_id = c.lastrowid
                conn.commit()
                conn.close()
                threading.Thread(
                    target=broadcast_sponsor, args=(sponsor_id,)
                ).start()

        elif self.path == "/admin/del_sponsor":
            s_id = params.get("id", [""])[0]
            if s_id:
                conn = get_db()
                c = conn.cursor()
                c.execute("DELETE FROM sponsors WHERE id = ?", (s_id,))
                conn.commit()
                conn.close()

        self.send_response(303)
        self.send_header("Location", "/admin")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/track_click"):
            parsed = urllib.parse.urlparse(self.path)
            sp_id = urllib.parse.parse_qs(parsed.query).get("id", [None])[0]
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT btn_url FROM sponsors WHERE id = ?", (sp_id,))
            row = c.fetchone()
            if row:
                c.execute(
                    "UPDATE sponsors SET clicks = clicks + 1 WHERE id = ?",
                    (sp_id,),
                )
                conn.commit()
                target_url = row["btn_url"]
            else:
                target_url = "https://t.me"
            conn.close()
            self.send_response(302)
            self.send_header("Location", target_url)
            self.end_headers()
            return

        if self.path.startswith("/admin/api/data"):
            if not self.is_authenticated():
                self.send_response(401)
                self.end_headers()
                return

            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            date_filter = q.get("filter", ["today"])[0]

            conn = get_db()
            c = conn.cursor()

            days_map = {
                "today": 0,
                "3d": 3,
                "7d": 7,
                "15d": 15,
                "1m": 30,
                "6m": 180,
                "1y": 365,
            }
            days_back = days_map.get(date_filter, 0)

            if days_back == 0:
                where_user = "WHERE first_seen = CURRENT_DATE"
                where_act = "WHERE act_date = CURRENT_DATE"
            else:
                target_date = (
                    datetime.now() - timedelta(days=days_back)
                ).strftime("%Y-%m-%d")
                where_user = f"WHERE first_seen >= '{target_date}'"
                where_act = f"WHERE act_date >= '{target_date}'"

            c.execute(f"SELECT COUNT(*) FROM users {where_user}")
            users_count = c.fetchone()[0]
            c.execute(
                f"SELECT COUNT(*) FROM activity {where_act} AND act_type ="
                " 'qr_gen'"
            )
            gen_count = c.fetchone()[0]
            c.execute(
                f"SELECT COUNT(*) FROM activity {where_act} AND act_type ="
                " 'qr_scan'"
            )
            scan_count = c.fetchone()[0]

            c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 25")
            logs_raw = c.fetchall()
            logs_list = [
                {
                    "user_name": l["user_name"],
                    "user_id": l["user_id"],
                    "act_type": l["act_type"],
                    "data_input": l["data_input"],
                    "data_output": l["data_output"],
                    "time": (
                        l["created_at"].split()[1][:5]
                        if " " in l["created_at"]
                        else ""
                    ),
                }
                for l in logs_raw
            ]

            chart_labels = []
            chart_gen = []
            chart_scan = []
            for i in range(6, -1, -1):
                day_str = (datetime.now() - timedelta(days=i)).strftime(
                    "%Y-%m-%d"
                )
                display_day = (datetime.now() - timedelta(days=i)).strftime(
                    "%d %b"
                )
                chart_labels.append(display_day)
                c.execute(
                    "SELECT COUNT(*) FROM activity WHERE act_type='qr_gen' AND"
                    " act_date=?",
                    (day_str,),
                )
                chart_gen.append(c.fetchone()[0])
                c.execute(
                    "SELECT COUNT(*) FROM activity WHERE act_type='qr_scan' AND"
                    " act_date=?",
                    (day_str,),
                )
                chart_scan.append(c.fetchone()[0])

            conn.close()

            json_resp = json.dumps(
                {
                    "users": users_count,
                    "gen": gen_count,
                    "scan": scan_count,
                    "logs": logs_list,
                    "chart_labels": chart_labels,
                    "chart_gen": chart_gen,
                    "chart_scan": chart_scan,
                }
            )

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json_resp.encode("utf-8"))
            return

        if self.path.startswith("/admin"):
            if not self.is_authenticated():
                login_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Admin Login</title>
                    <style>
                        body { background: #090d16; color: #fff; font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                        .card { background: #131b2e; padding: 25px; border-radius: 14px; border: 1px solid #1e293b; width: 300px; text-align: center; }
                        input, button { width: 100%; padding: 12px; margin-top: 10px; border-radius: 8px; border: 1px solid #334155; box-sizing: border-box; }
                        input { background: #090d16; color: #fff; }
                        button { background: #0284c7; color: #fff; border: none; font-weight: bold; cursor: pointer; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h2>🔐 Admin Access</h2>
                        <form action="/admin/login" method="POST">
                            <input type="password" name="password" placeholder="Enter Admin Password" required autofocus>
                            <button type="submit">Unlock Dashboard</button>
                        </form>
                    </div>
                </body>
                </html>
                """
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(login_html.encode("utf-8"))
                return

            conn = get_db()
            c = conn.cursor()
            c.execute(
                """SELECT fc.*, (SELECT COUNT(*) FROM channel_joins cj WHERE cj.chat_username = fc.chat_username) as joins 
                         FROM force_chats fc"""
            )
            chats = c.fetchall()

            c.execute("SELECT * FROM users ORDER BY first_seen DESC LIMIT 20")
            users = c.fetchall()

            c.execute("SELECT * FROM sponsors ORDER BY id DESC LIMIT 5")
            sponsors = c.fetchall()

            bot_on = is_bot_active()
            conn.close()

            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>QR Studio - Master Dashboard</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body {{ font-family: system-ui, -apple-system, sans-serif; background: #090d16; color: #f1f5f9; margin: 0; padding: 12px; }}
                    .container {{ max-width: 650px; margin: 0 auto; }}
                    .box {{ background: #131b2e; border-radius: 14px; padding: 16px; margin-bottom: 16px; border: 1px solid #1e293b; }}
                    h2, h3 {{ margin-top: 0; color: #38bdf8; display: flex; justify-content: space-between; align-items: center; }}
                    
                    .filter-bar {{ display: flex; gap: 5px; overflow-x: auto; margin-bottom: 15px; padding-bottom: 4px; }}
                    .filter-btn {{ padding: 6px 12px; font-size: 11px; background: #090d16; border: 1px solid #334155; border-radius: 20px; color: #94a3b8; cursor: pointer; white-space: nowrap; }}
                    .filter-btn.active {{ background: #0284c7; color: #fff; border-color: #0284c7; }}

                    .grid-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 15px; }}
                    .stat-item {{ background: #090d16; padding: 12px 6px; border-radius: 10px; text-align: center; border: 1px solid #1e293b; }}
                    .stat-item b {{ font-size: 22px; color: #38bdf8; display: block; }}
                    .stat-item span {{ font-size: 11px; color: #94a3b8; }}
                    
                    .history-box {{ max-height: 280px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }}
                    .history-item {{ background: #090d16; padding: 10px; border-radius: 8px; display: flex; gap: 10px; align-items: center; border: 1px solid #1e293b; font-size: 12px; }}
                    .avatar {{ width: 34px; height: 34px; border-radius: 50%; background: #0284c7; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }}

                    input, textarea, button {{ width: 100%; padding: 10px; margin-top: 6px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #334155; background: #090d16; color: #fff; box-sizing: border-box; }}
                    button {{ background: #0284c7; font-weight: bold; cursor: pointer; border: none; }}
                    button.red {{ background: #e11d48; }}
                    button.green {{ background: #16a34a; }}
                    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
                    th, td {{ padding: 8px; border-bottom: 1px solid #1e293b; text-align: left; }}
                    th {{ color: #94a3b8; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h2 style="margin:0;">📊 Master Dashboard</h2>
                        <form action="/admin/logout" method="POST" style="margin:0;"><button style="padding:5px 10px;background:#e11d48;font-size:11px;width:auto;">Logout</button></form>
                    </div>

                    <div class="box">
                        <div class="filter-bar">
                            <button class="filter-btn active" onclick="setFilter('today', this)">Today</button>
                            <button class="filter-btn" onclick="setFilter('3d', this)">3 Days</button>
                            <button class="filter-btn" onclick="setFilter('7d', this)">7 Days</button>
                            <button class="filter-btn" onclick="setFilter('15d', this)">15 Days</button>
                            <button class="filter-btn" onclick="setFilter('1m', this)">1 Month</button>
                            <button class="filter-btn" onclick="setFilter('6m', this)">6 Months</button>
                            <button class="filter-btn" onclick="setFilter('1y', this)">1 Year</button>
                        </div>
                        <div class="grid-stats">
                            <div class="stat-item"><b id="stat_users">...</b><span>👥 Total Users</span></div>
                            <div class="stat-item"><b id="stat_gen">...</b><span>📱 QR Gen</span></div>
                            <div class="stat-item"><b id="stat_scan">...</b><span>🔍 QR Scan</span></div>
                        </div>
                        <div style="background:#090d16;padding:10px;border-radius:10px;border:1px solid #1e293b;">
                            <canvas id="growthChart" height="170"></canvas>
                        </div>
                    </div>

                    <div class="box" style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <h3 style="margin:0;font-size:16px;">⚡ Bot Status Control</h3>
                            <small style="color:{'#22c55e' if bot_on else '#ef4444'};font-weight:bold;">
                                {'🟢 Bot is LIVE & Active' if bot_on else '🔴 Bot is PAUSED (Under Maintenance)'}
                            </small>
                        </div>
                        <form action="/admin/toggle_status" method="POST" style="margin:0;width:auto;">
                            <button class="{'red' if bot_on else 'green'}" style="padding:8px 16px;width:auto;margin:0;">
                                {'Turn OFF Bot' if bot_on else 'Turn ON Bot'}
                            </button>
                        </form>
                    </div>

                    <div class="box">
                        <h3>📢 Required Channels / Groups</h3>
                        <form action="/admin/add_chat" method="POST">
                            <input name="chat_username" placeholder="@ChannelUsername (must make bot admin)" required>
                            <input name="chat_title" placeholder="Display Title (e.g. Official Channel)" required>
                            <button type="submit">➕ Add Channel / Group</button>
                        </form>
                        <table>
                            <tr><th>Channel</th><th>Joined</th><th>Action</th></tr>
                            {"".join(f'''<tr>
                                <td><b>{c["chat_title"]}</b><br><small>{c["chat_username"]}</small></td>
                                <td><b style="color:#38bdf8;">👥 {c["joins"]} Joined</b></td>
                                <td>
                                    <form action="/admin/del_chat" method="POST" style="margin:0;">
                                        <input type="hidden" name="id" value="{c["id"]}">
                                        <button class="red" style="padding:4px 8px;margin:0;width:auto;">Remove</button>
                                    </form>
                                </td>
                            </tr>''' for c in chats)}
                        </table>
                    </div>

                    <div class="box">
                        <h3>User Management 👥</h3>
                        <table>
                            <tr><th>User</th><th>Status</th><th>Action</th></tr>
                            {"".join(f'''<tr>
                                <td style="display:flex;align-items:center;gap:8px;">
                                    <div class="avatar">{u["first_name"][0] if u["first_name"] else 'U'}</div>
                                    <div><b>{u["first_name"]}</b><br><small style="color:#94a3b8;">@{u["username"]} ({u["user_id"]})</small></div>
                                </td>
                                <td>{"🔴 Banned" if u["is_banned"] else "🟢 Active"}</td>
                                <td>
                                    <form action="/admin/toggle_ban" method="POST" style="margin:0;">
                                        <input type="hidden" name="user_id" value="{u["user_id"]}">
                                        <button class="{'green' if u['is_banned'] else 'red'}" style="padding:4px 8px;margin:0;width:auto;font-size:11px;">
                                            {"Unban" if u["is_banned"] else "Ban"}
                                        </button>
                                    </form>
                                </td>
                            </tr>''' for u in users)}
                        </table>
                    </div>

                    <div class="box">
                        <h3>📣 Sponsor Broadcast Box</h3>
                        <form action="/admin/send_sponsor" method="POST">
                            <textarea name="text" rows="2" placeholder="Sponsor Message..." required></textarea>
                            <input name="photo_url" placeholder="Photo URL (Optional, https://...)">
                            <input name="btn_text" placeholder="Button Text (e.g. Open Site)">
                            <input name="btn_url" placeholder="Button Link (https://...)">
                            <button type="submit" class="green">🚀 Broadcast</button>
                        </form>
                        <table>
                            <tr><th>Message</th><th>Views</th><th>Clicks</th><th>Action</th></tr>
                            {"".join(f'''<tr>
                                <td>{s["text"][:20]}...</td>
                                <td>👁️ {s["views"]}</td>
                                <td>🎯 {s["clicks"]}</td>
                                <td>
                                    <form action="/admin/del_sponsor" method="POST" style="margin:0;">
                                        <input type="hidden" name="id" value="{s["id"]}">
                                        <button class="red" style="padding:4px 8px;margin:0;width:auto;">Del</button>
                                    </form>
                                </td>
                            </tr>''' for s in sponsors)}
                        </table>
                    </div>

                    <div class="box">
                        <h3>🔐 Change Admin Password</h3>
                        <form action="/admin/change_pass" method="POST">
                            <input type="password" name="old_pass" placeholder="Current Password" required>
                            <input type="password" name="new_pass" placeholder="New Password" required>
                            <button type="submit">Update Password</button>
                        </form>
                    </div>

                    <div class="box">
                        <h3>
                            <span>📜 Live Activity History</span>
                            <form action="/admin/clear_logs" method="POST" style="margin:0;" onsubmit="return confirm('Clear all history?')">
                                <button class="red" style="padding:4px 10px;font-size:11px;margin:0;width:auto;">🗑️ Clear</button>
                            </form>
                        </h3>
                        <div class="history-box" id="logs_container">
                            <div style="text-align:center;color:#94a3b8;">Loading live logs...</div>
                        </div>
                    </div>
                </div>

                <script>
                    let currentFilter = 'today';
                    let chartInstance = null;

                    function setFilter(filter, el) {{
                        currentFilter = filter;
                        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                        el.classList.add('active');
                        fetchData();
                    }}

                    async function fetchData() {{
                        try {{
                            const res = await fetch('/admin/api/data?filter=' + currentFilter);
                            if (res.status === 401) return location.reload();
                            const data = await res.json();

                            document.getElementById('stat_users').innerText = data.users;
                            document.getElementById('stat_gen').innerText = data.gen;
                            document.getElementById('stat_scan').innerText = data.scan;

                            const container = document.getElementById('logs_container');
                            if (data.logs.length === 0) {{
                                container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;">No activity history yet</div>';
                            }} else {{
                                container.innerHTML = data.logs.map(l => `
                                    <div class="history-item">
                                        <div class="avatar">${{l.user_name ? l.user_name[0] : 'U'}}</div>
                                        <div style="flex:1;overflow:hidden;">
                                            <b>${{l.user_name}}</b> <small style="color:#64748b;">${{l.time}}</small><br>
                                            <span style="color:#38bdf8;">${{l.act_type === 'qr_gen' ? '📱 Created QR' : '🔍 Scanned QR'}}</span>: 
                                            <small style="color:#94a3b8;word-break:break-all;">${{l.act_type === 'qr_gen' ? l.data_input : l.data_output}}</small>
                                        </div>
                                    </div>
                                `).join('');
                            }}

                            if (!chartInstance) {{
                                const ctx = document.getElementById('growthChart').getContext('2d');
                                chartInstance = new Chart(ctx, {{
                                    type: 'line',
                                    data: {{
                                        labels: data.chart_labels,
                                        datasets: [
                                            {{ label: 'QR Created', data: data.chart_gen, borderColor: '#38bdf8', tension: 0.3, fill: false }},
                                            {{ label: 'QR Scanned', data: data.chart_scan, borderColor: '#a855f7', tension: 0.3, fill: false }}
                                        ]
                                    }},
                                    options: {{
                                        responsive: true,
                                        plugins: {{ legend: {{ labels: {{ color: '#94a3b8', boxWidth: 12 }} }} }},
                                        scales: {{
                                            x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }},
                                            y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8', beginAtZero: true }} }}
                                        }}
                                    }}
                                }});
                            }} else {{
                                chartInstance.data.labels = data.chart_labels;
                                chartInstance.data.datasets[0].data = data.chart_gen;
                                chartInstance.data.datasets[1].data = data.chart_scan;
                                chartInstance.update();
                            }}
                        }} catch (e) {{ console.error(e); }}
                    }}

                    fetchData();
                    setInterval(fetchData, 4000);
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is alive!")


def broadcast_sponsor(sponsor_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM sponsors WHERE id = ?", (sponsor_id,))
    sp = c.fetchone()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = c.fetchall()

    views = 0
    markup = None

    if sp["btn_text"] and sp["btn_url"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                sp["btn_text"],
                url=f"https://search-gram.onrender.com/track_click?id={sponsor_id}",
            )
        )

    for u in users:
        uid = u["user_id"]
        try:
            if sp["photo_url"]:
                bot.send_photo(
                    uid,
                    sp["photo_url"],
                    caption=f"📣 <b>Sponsored Post:</b>\n\n{sp['text']}",
                    reply_markup=markup,
                )
            else:
                bot.send_message(
                    uid,
                    f"📣 <b>Sponsored Post:</b>\n\n{sp['text']}",
                    reply_markup=markup,
                )
            views += 1
        except Exception:
            pass

    c.execute(
        "UPDATE sponsors SET views = ? WHERE id = ?", (views, sponsor_id)
    )
    conn.commit()
    conn.close()


def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), WebAdminHandler)
    server.serve_forever()


threading.Thread(target=run_web, daemon=True).start()


# === টেলিগ্রাম বট মেসেজ হ্যান্ডলারস ===
def is_valid_link(text):
    pattern = re.compile(
        r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/[^\s]*)?$",
        re.IGNORECASE,
    )
    return bool(pattern.match(text.strip()))


@bot.message_handler(commands=["start"])
def send_welcome(message):
    uid = message.from_user.id
    register_user(message.from_user)

    if not is_bot_active():
        bot.reply_to(
            message,
            "⚠️ <b>সাময়িক সময়ের জন্য bot বন্ধ আছে কারণ বট এর আপডেট"
            " কাজ চলছে।</b>",
        )
        return

    if is_user_banned(uid):
        bot.reply_to(
            message,
            "⛔ <b>Access Denied!</b> You are banned from using this bot.",
        )
        return

    is_ok, missing = check_user_membership(uid)
    if not is_ok:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Access Locked!</b>\nPlease join our required channels/groups to use this bot:",
            reply_markup=make_join_keyboard(missing),
        )
        return

    text = (
        f"👋 <b>Hello {message.from_user.first_name}!</b>\n\n"
        "Welcome to <b>Smart Link ⇄ QR Studio</b>.\n\n"
        "• Send any <b>Link</b> ➔ Instant QR Code with custom colors & title\n"
        "• Send any <b>QR Image</b> ➔ Instant Clickable Browser Link\n\n"
        "⚠️ <i>Note: Plain text is not accepted. Only valid links!</i>"
    )
    bot.reply_to(message, text)


# 1. QR CODE SCANNER
@bot.message_handler(content_types=["photo"])
def handle_qr_scan(message):
    uid = message.from_user.id
    register_user(message.from_user)

    if not is_bot_active():
        bot.reply_to(
            message,
            "⚠️ <b>সাময়িক সময়ের জন্য bot বন্ধ আছে কারণ বট এর আপডেট"
            " কাজ চলছে।</b>",
        )
        return

    if is_user_banned(uid):
        bot.reply_to(message, "⛔ You are banned.")
        return

    is_ok, missing = check_user_membership(uid)
    if not is_ok:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Please join our channels/groups first!</b>",
            reply_markup=make_join_keyboard(missing),
        )
        return

    wait_msg = bot.reply_to(message, "🔍 Scanning QR Code, please wait...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        image_bytes = bot.download_file(file_info.file_path)

        files = {"file": ("qrcode.png", image_bytes, "image/png")}
        response = requests.post(
            "https://api.qrserver.com/v1/read-qr-code/",
            files=files,
            timeout=15,
        )
        data = response.json()

        qr_result = None
        if (
            data
            and len(data) > 0
            and "symbol" in data[0]
            and data[0]["symbol"][0]["data"]
        ):
            qr_result = data[0]["symbol"][0]["data"]

        bot.delete_message(message.chat.id, wait_msg.message_id)

        if qr_result:
            log_user_action(
                uid,
                message.from_user.first_name,
                "qr_scan",
                "QR Photo",
                qr_result,
            )
            markup = types.InlineKeyboardMarkup()
            if qr_result.startswith(("http://", "https://")):
                markup.add(
                    types.InlineKeyboardButton(
                        "🌐 Open Link in Browser", url=qr_result
                    )
                )

            response_text = (
                "✅ <b>QR Code Decoded Successfully!</b>\n\n"
                f"🔗 <b>Extracted Link:</b>\n{qr_result}"
            )
            bot.reply_to(
                message,
                response_text,
                reply_markup=markup,
                disable_web_page_preview=False,
            )
        else:
            bot.reply_to(
                message,
                "❌ <b>Failed to decode!</b> No valid QR Code found. Please send a clear image.",
            )

    except Exception as e:
        print(f"Scan Error: {e}")
        bot.edit_message_text(
            "⚠️ Error scanning the image.", message.chat.id, wait_msg.message_id
        )


# 2. QR CODE GENERATOR & CUSTOM LABEL
@bot.message_handler(func=lambda msg: True)
def handle_text_or_link(message):
    uid = message.from_user.id
    register_user(message.from_user)

    if not is_bot_active():
        bot.reply_to(
            message,
            "⚠️ <b>সাময়িক সময়ের জন্য bot বন্ধ আছে কারণ বট এর আপডেট"
            " কাজ চলছে।</b>",
        )
        return

    if is_user_banned(uid):
        bot.reply_to(message, "⛔ You are banned.")
        return

    is_ok, missing = check_user_membership(uid)
    if not is_ok:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Please join our channels/groups first!</b>",
            reply_markup=make_join_keyboard(missing),
        )
        return

    text = message.text.strip()

    if user_sessions.get(uid, {}).get("awaiting_label"):
        user_sessions[uid]["awaiting_label"] = False
        user_sessions[uid]["label"] = text
        link = user_sessions[uid]["link"]
        color = user_sessions[uid]["color"]
        msg_id = user_sessions[uid].get("last_qr_msg_id")

        prompt_id = user_sessions[uid].get("prompt_msg_id")
        if prompt_id:
            try:
                bot.delete_message(uid, prompt_id)
            except:
                pass
        try:
            bot.delete_message(uid, message.message_id)
        except:
            pass

        bio = generate_styled_qr(link, color_hex=color, label_text=text)

        try:
            caption_text = (
                f"📱 <b>QR Code Updated!</b>\n\n"
                f"🔗 <b>Link:</b> {link}\n"
                f"🏷️ <b>Title:</b> {text}"
            )
            media = types.InputMediaPhoto(
                bio.getvalue(), caption=caption_text, parse_mode="HTML"
            )
            bot.edit_message_media(
                media,
                chat_id=uid,
                message_id=msg_id,
                reply_markup=get_qr_buttons(),
            )
        except Exception as e:
            print(f"Edit error: {e}")
        return

    if is_valid_link(text):
        formatted_link = (
            text if text.startswith(("http://", "https://")) else f"https://{text}"
        )
        log_user_action(
            uid,
            message.from_user.first_name,
            "qr_gen",
            formatted_link,
            "QR Created",
        )

        wait_msg = bot.reply_to(message, "⏳ Generating QR Code...")
        bio = generate_styled_qr(formatted_link, color_hex="#000000")

        bot.delete_message(message.chat.id, wait_msg.message_id)

        caption_text = (
            f"📱 <b>QR Code Generated Successfully!</b>\n\n"
            f"🔗 <b>Link:</b> {formatted_link}"
        )

        sent = bot.send_photo(
            message.chat.id,
            bio,
            caption=caption_text,
            reply_markup=get_qr_buttons(),
            reply_to_message_id=message.message_id,
        )

        user_sessions[uid] = {
            "link": formatted_link,
            "color": "#000000",
            "label": None,
            "awaiting_label": False,
            "last_qr_msg_id": sent.message_id,
        }

    else:
        bot.reply_to(
            message,
            "❌ <b>Invalid Input!</b>\n\n"
            "This bot only accepts valid website <b>Links/URLs</b> (e.g. <code>https://google.com</code>).\n"
            "Normal text messages cannot be converted.",
        )


# 3. বাটন হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data == "recheck_join":
        is_ok, missing = check_user_membership(uid)
        if is_ok:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "✅ <b>Verification Successful!</b> You can now use the bot.",
            )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ You still haven't joined all required channels!",
                show_alert=True,
            )
        return

    session = user_sessions.get(uid)
    if not session or not session.get("link"):
        bot.answer_callback_query(
            call.id, "Please send a new link first!", show_alert=True
        )
        return

    if data.startswith("col_"):
        selected_color = data.replace("col_", "")
        session["color"] = selected_color

        bio = generate_styled_qr(
            session["link"],
            color_hex=selected_color,
            label_text=session["label"],
        )

        title_info = session["label"] if session["label"] else "None"
        caption_text = (
            f"📱 <b>QR Code Updated!</b>\n\n"
            f"🔗 <b>Link:</b> {session['link']}\n"
            f"🏷️ <b>Title:</b> {title_info}"
        )

        try:
            media = types.InputMediaPhoto(
                bio.getvalue(), caption=caption_text, parse_mode="HTML"
            )
            bot.edit_message_media(
                media,
                chat_id=uid,
                message_id=call.message.message_id,
                reply_markup=get_qr_buttons(),
            )
            bot.answer_callback_query(call.id, "🎨 Color updated!")
        except Exception as e:
            print(f"Edit error: {e}")
            bot.answer_callback_query(call.id)

    elif data == "set_label":
        session["awaiting_label"] = True
        session["last_qr_msg_id"] = call.message.message_id
        bot.answer_callback_query(call.id)
        prompt = bot.send_message(
            uid,
            "✍️ <b>Send the Name or Brand Title</b> you want to display on your QR Code:",
        )
        session["prompt_msg_id"] = prompt.message_id


# === ক্র্যাশ-প্রুফ সেফ রানার ===
print("QR Studio Master Server Started...")

while True:
    try:
        me = bot.get_me()
        print(f"SUCCESS: Connected to Telegram as @{me.username}!")
        bot.infinity_polling(skip_pending=True, timeout=20)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 401:
            print(
                "CRITICAL: 401 Unauthorized! The token in main.py is INVALID."
            )
            time.sleep(25)
        else:
            print(f"Telegram Connection Error: {e}")
            time.sleep(5)
    except Exception as e:
        print(f"General Loop Error: {e}")
        time.sleep(5)
