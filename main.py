<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Canva Pro Team & Admin</title>
  
  <!-- ✅ SDKs -->
  <script src="https://telegram.org/js/telegram-web-app.js?56"></script>
  <script src="https://richinfo.co/richpartners/telegram/js/tg-ob.js"></script>
  <script type="text/javascript" src="https://cdn.tgads.space/assets/js/adexium-widget.min.js"></script>
  <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
  <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-database.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    /* ================= GLOBAL CSS ================= */
    :root { 
        --primary: #6200ea; --secondary: #03dac5; --light: #ffffff; --dark: #121212; 
        --card-bg: #1f1f1f; --text-color: #ffffff; --ad-bg: #222; --ad-item-bg: #333; 
        --border-color: #444; --info: #17a2b8; --green-status: #28a745; --red-status: #dc3545; 
        --danger: #dc3545; --warning: #ffc107; --success: #28a745; 
        --social-btn-padding: 6px 12px; --social-btn-font: 10.5px; 
        --wa-btn-padding: 6px 12px; --wa-btn-font: 10.5px; 
        --highlight-bg: #444; --highlight-text: #fff;
    }
    body.light-mode { 
        --dark: #f0f2f5; --card-bg: #ffffff; --text-color: #000000; 
        --ad-bg: #f9f9f9; --ad-item-bg: #f1f1f1; --border-color: #dddddd; 
        background: #f0f2f5 !important; --highlight-bg: #e0e0e0; --highlight-text: #000;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    body { background: linear-gradient(135deg, var(--dark), #1a1a2e); color: var(--text-color); min-height: 100vh; display: flex; flex-direction: column; align-items: center; transition: all 0.4s ease; padding: 10px; padding-bottom: 75px; text-align: center; overflow-x: hidden;}
    
    #preloader { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--dark); color: var(--light); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 99999; transition: opacity 0.5s ease, visibility 0.5s ease; }
    #preloader-logo { max-width: 120px; height: auto; animation: logo-pulse 2s infinite; border-radius: 10px; }
    @keyframes logo-pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    .fade-out { opacity: 0; visibility: hidden; }
    
    #mode-toggle { padding: 4px 5px; background: transparent; color: var(--text-color); border: none; border-radius: 100px; cursor: pointer; font-size: 20px; transition: all 0.3s ease; z-index: 1100; position: absolute; top: 15px; right: 15px;}
    body.light-mode #mode-toggle { color: #000; }
    
    .ad-notification { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(40, 167, 69, 0.95); backdrop-filter: blur(5px); color: white; padding: 10px 20px; border-radius: 30px; z-index: 9999999 !important; display: none; font-size: 13.5px; font-weight: bold; white-space: nowrap; box-shadow: 0 8px 20px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); animation: slideDown 0.3s ease-out; }
    .ad-notification.error { background: rgba(220, 53, 69, 0.95) !important; border-color: rgba(255, 0, 0, 0.5); }
    @keyframes slideDown { 0% { top: -20px; opacity: 0; } 100% { top: 20px; opacity: 1; } }

    .custom-modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 10000; }
    .modal-box { background: var(--card-bg); padding: 25px 20px 20px 20px; border-radius: 16px; width: 95%; max-width: 450px; text-align: center; border: 1px solid var(--border-color); position: relative; animation: pop-in 0.3s ease; box-shadow: 0 10px 30px rgba(0,0,0,0.4); max-height: 95vh; overflow-y: auto; }
    .modal-input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--ad-bg); color: var(--text-color); margin-bottom: 15px; box-sizing: border-box; outline: none; font-size: 14px; text-align: center; }
    .clean-close-icon-new { position: absolute; top: 15px; right: 15px; background: rgba(128,128,128,0.1); width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; border: 1px solid var(--border-color); cursor: pointer; color: var(--text-color); transition: 0.2s; }
    body.light-mode .clean-close-icon-new { border-color: #e0e0e0; color: #666; background: #f0f0f0; }

    /* ================= USER SITE CSS ================= */
    #user-site-wrapper { width: 100%; display: flex; flex-direction: column; align-items: center; }
    .user-container { width: 100%; max-width: 500px; background: var(--card-bg); border-radius: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); overflow: hidden; padding-bottom: 20px; margin-bottom: 20px; transition: all 0.4s ease; display: none; }
    .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: var(--card-bg); border-top: 1px solid var(--border-color); display: flex; justify-content: space-around; align-items: center; padding: 10px 5px; z-index: 1000; box-shadow: 0 -4px 15px rgba(0,0,0,0.3); }
    .nav-item { display: flex; flex-direction: column; align-items: center; gap: 4px; color: #888; cursor: pointer; font-size: 11px; font-weight: bold; transition: 0.3s; flex: 1; text-align: center; position: relative; }
    .nav-item.active { color: var(--secondary); }
    .nav-icon { font-size: 22px; margin-bottom: 2px; }
    .nav-dot { position: absolute; top: -2px; right: 25px; width: 8px; height: 8px; background-color: var(--red-status); border-radius: 50%; box-shadow: 0 0 8px var(--red-status); display: none; animation: pulse-dot 1.5s infinite; }
    .tab-content { display: none; animation: pop-in 0.4s ease; }
    .tab-content.active { display: block; }
    .content { padding: 25px; padding-top: 10px; } 
    
    .banner-slider-container { width: 100%; height: 150px; overflow: hidden; position: relative; margin-bottom: 0px; background: #000; border-top-left-radius: 20px; border-top-right-radius: 20px; }
    .banner-slide { width: 100%; height: 100%; position: absolute; top: 0; left: 0; opacity: 0; transition: opacity 1s ease-in-out; cursor: pointer; display: flex; justify-content: center; align-items: center; background-color: #1a1a1a; }
    .banner-slide.active { opacity: 1; }
    .banner-slide img, .banner-slide iframe { width: 100%; height: 100%; object-fit: cover; border: none; }
    .mute-toggle { position: absolute; bottom: 5px; right: 5px; background: transparent; color: white; border: none; border-radius: 50%; width: 30px; height: 30px; line-height: 30px; text-align: center; font-size: 14px; cursor: pointer; z-index: 100; display: none; }
    .progress-container { width: 100%; background: #333; border-radius: 12px; margin-bottom: 25px; overflow: hidden; height: 30px; display: flex; border: 1px solid var(--border-color); }
    .step-inner { display: flex; width: 100%; height: 100%; }
    .step-box { flex: 1; text-align: center; line-height: 27px; font-size: 14px; font-weight: bold; color: #fff; background-color: #444; transition: background 0.3s ease; white-space: nowrap; overflow: hidden; }
    .step-box.active-pulse { animation: pulse-animation 1.5s infinite; box-shadow: inset 0 0 10px rgba(255,255,255,0.5); }
    
    .btn-3d { padding: 14px 20px; border: none; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; color: var(--light); background: linear-gradient(135deg, var(--primary), #8e24aa); transition: 0.3s ease; box-shadow: 0 4px 10px rgba(98,0,234,0.3); width: 100%; }
    .btn-3d:hover { transform: translateY(-2px); filter: brightness(1.1); }
    #canva-pro-btn { font-size: 22px; padding: 16px 24px; letter-spacing: 0.5px; white-space: normal; line-height: 1.3; }
    .btn-small { padding: 10px 15px; font-size: 14px; width: auto; }
    
    .task-card { display: flex; align-items: center; justify-content: space-between; background: var(--card-bg); padding: 14px 10px; border-radius: 14px; margin-bottom: 10px; border: 1px solid var(--border-color); box-shadow: 0 4px 10px rgba(0,0,0,0.15); gap: 8px; }
    body.light-mode .task-card { background: #ffffff; border-color: #ddd; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .task-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
    .task-logo { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; background: var(--ad-bg); border: 1px solid var(--border-color); flex-shrink: 0; display:flex; justify-content:center; align-items:center; font-size:20px; }
    .task-info { display: flex; flex-direction: column; gap: 5px; text-align: left; flex: 1; min-width: 0; }
    .task-title { font-weight: bold; font-size: 14px; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .task-info-bottom { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; overflow: hidden; }
    .task-reward { font-size: 13px; font-weight: 800; color: #ffc107; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; flex-shrink: 0; }
    .task-progress-wrap { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
    .task-progress-track { width: 35px; height: 4px; background: #444; border-radius: 4px; overflow: hidden; flex-shrink: 0; }
    .task-progress-fill { height: 100%; background: linear-gradient(90deg, #ff7b00, #ff9e00); border-radius: 4px; transition: width 0.3s ease; }
    .task-progress-text { font-size: 10px; color: #888; font-weight: bold; white-space: nowrap; flex-shrink: 0;}
    .task-btn-start { background: linear-gradient(135deg, #ff7b00, #ff9e00); color: #fff; font-weight: 800; border: none; border-radius: 8px; cursor: pointer; flex-shrink: 0; box-shadow: 0 4px 10px rgba(255, 123, 0, 0.3); text-transform: uppercase; transition: 0.2s; padding: var(--social-btn-padding); font-size: var(--social-btn-font); }
    .task-btn-start.pending { background: linear-gradient(135deg, #f39c12, #f1c40f); color: #000; cursor: default; }
    .task-btn-start.cooldown { background: #555 !important; color: #fff !important; box-shadow: none !important; cursor: default !important; }
    .task-btn-start.completed { background: rgba(40, 167, 69, 0.15) !important; box-shadow: none !important; border: 1px solid var(--success) !important; color: var(--success) !important; cursor: default !important; }
    
    .points-display { font-size: 15px; font-weight: bold; color: var(--warning); display: flex; align-items: center; gap: 5px; background: var(--ad-item-bg); padding: 6px 12px; border-radius: 10px; border: 1px solid var(--border-color); white-space: nowrap; }
    body.light-mode .points-display { background: #fff3cd; border-color: #ffeeba; color: #856404; }
    
    .activity-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 14px; padding: 12px; margin-bottom: 12px; display: flex; gap: 12px; align-items: center; transition: 0.3s; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    body.light-mode .activity-card { background: #fff; border-color: #eee; }
    .act-logo-wrap { position: relative; width: 48px; height: 48px; flex-shrink: 0; }
    .act-main-logo { width: 100%; height: 100%; border-radius: 10px; object-fit: cover; border: 1px solid var(--border-color); background: var(--ad-bg); }
    .act-user-avatar { position: absolute; bottom: -4px; right: -4px; width: 22px; height: 22px; border-radius: 50%; border: 2px solid var(--card-bg); object-fit: cover; }
    body.light-mode .act-user-avatar { border-color: #fff; }
    .act-details { flex: 1; overflow: hidden; display: flex; flex-direction: column; justify-content: center; gap: 4px; text-align: left; }
    .act-header { display: flex; justify-content: space-between; align-items: center; }
    .act-user-name { font-weight: bold; font-size: 14px; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px; display: inline-block; vertical-align: middle; }
    body.light-mode .act-user-name { color: #000; }
    .act-username { font-size: 11px; color: #888; font-weight: normal; margin-left: 4px; }
    .act-time { font-size: 11px; color: #aaa; flex-shrink: 0; }
    .act-status { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* ================= ADMIN PANEL CSS ================= */
    #admin-panel-wrapper { display: none; width: 100%; }
    .admin-container { width: 100%; max-width: 800px; background: transparent; border-radius: 20px; overflow: hidden; padding: 0px; transition: all 0.4s ease; margin: 0 auto; }
    .admin-card { background: var(--card-bg); padding: 25px; border-radius: 20px; margin-bottom: 25px; border: none; text-align: left; width: 100%; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    body.light-mode .admin-card { box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
    .admin-card h2 { color: var(--secondary); margin-bottom: 15px; font-size: 24px; border-bottom: 2px solid var(--primary); padding-bottom: 10px; }
    
    #admin-nav { display: flex; justify-content: space-around; margin-bottom: 20px; border-bottom: 3px solid var(--border-color); padding-bottom: 5px; flex-wrap: wrap; gap: 5px; }
    .admin-nav-item { flex: 1; padding: 8px 4px; cursor: pointer; font-weight: bold; color: #999; transition: all 0.3s ease; border-bottom: 3px solid transparent; font-size: 13px; text-align: center; min-width: 70px; }
    .admin-nav-item.active { color: var(--secondary); border-bottom: 3px solid var(--secondary); }
    .admin-tab-content { display: none; }
    .admin-tab-content.active { display: block; }
    
    .admin-stat-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .admin-stat-item { background: var(--card-bg); padding: 10px; border-radius: 10px; border: 1px solid var(--border-color); display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 13px; min-height: 70px; text-align: center; }
    .admin-stat-item span { font-size: 24px; font-weight: bold; color: var(--secondary); margin-top: 5px; }

    .admin-btn { background: var(--secondary); color: #000; border: none; border-radius: 8px; padding: 12px 25px; cursor: pointer; font-weight: 600; font-size: 16px; }
    .admin-btn-sm { padding: 5px 10px; font-size: 12px; margin: 0 5px; }
    .admin-btn-success { background: var(--success); color: #fff; }
    .admin-btn-danger { background: var(--danger); color: #fff; }
    .admin-btn-primary { background: var(--primary); color: #fff; }
    .admin-btn-warning { background: var(--warning); color: #000; }
    
    .form-grid { display: flex; flex-direction: column; gap: 12px; margin-bottom: 15px; }
    .form-grid label { font-size: 14px; font-weight: 600; color: #bbb; display: block; }
    .admin-input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--ad-item-bg); color: var(--text-color); font-size: 15px; outline: none; }
    
    .toggle-switch { position: relative; display: inline-block; width: 46px; height: 24px; flex-shrink: 0;}
    .toggle-switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #555; transition: .4s; border-radius: 34px; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: var(--success); }
    input:checked + .slider:before { transform: translateX(22px); }

    #hidden-admin-trigger { position: fixed; bottom: 0; right: 0; width: 60px; height: 60px; z-index: 99999; background: transparent; cursor: pointer; }
  </style>
</head>
<body class="light-mode">
    
    <!-- ✅ PRELOADER -->
    <div id="preloader"><img id="preloader-logo" src="" alt="Loading Logo" style="display:none;"></div>
    <div class="ad-notification" id="ad-notification">Notification</div>
    <button id="mode-toggle" onclick="toggleMode()">🌙</button>
    
    <!-- ✅ HIDDEN BUTTON FOR ADMIN -->
    <div id="hidden-admin-trigger" onclick="handleHiddenAdminClick()"></div>

    <!-- ✅ PASSWORD MODAL FOR ADMIN -->
    <div id="admin-password-modal" class="custom-modal-overlay">
        <div class="modal-box">
            <h3 style="color:var(--primary); margin-bottom:15px;">🔒 Admin Access</h3>
            <p style="font-size:14px; color:#aaa; margin-bottom:15px;">Enter admin password to continue.</p>
            <input type="password" id="hidden-admin-pass-input" class="modal-input" placeholder="Password...">
            <div style="display:flex; gap:10px;">
                <button class="btn-3d" style="background:#666; padding:10px;" onclick="document.getElementById('admin-password-modal').style.display='none'">Cancel</button>
                <button class="btn-3d" style="padding:10px;" onclick="verifyAdminPassword()">Login</button>
            </div>
        </div>
    </div>
