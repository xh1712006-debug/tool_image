import http.server
import json
import threading
import time
import os
import subprocess
from urllib.parse import parse_qs, urlparse

# Queue để giao tiếp giữa Web UI và luồng chạy Bot (async)
BOT_JOB_QUEUE = []

def get_adb_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    adb_path = os.path.join(base_dir, "adb", "platform-tools", "adb.exe")
    if not os.path.exists(adb_path):
        adb_path = "adb"
    return adb_path

def get_connected_devices():
    adb_path = get_adb_path()
    try:
        result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]
            devices = []
            for line in lines:
                if '\t' in line:
                    dev_id, dev_state = line.split('\t')
                    if dev_state.strip() == 'device':
                        devices.append(dev_id.strip())
            return devices
    except Exception:
        pass
    return []

def get_device_screen():
    adb_path = get_adb_path()
    try:
        # Lấy ảnh màn hình thiết bị dưới dạng byte PNG
        result = subprocess.run([adb_path, 'exec-out', 'screencap', '-p'], capture_output=True, timeout=15)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception:
        pass
    return None


HTML_FORM = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Bảng Điều Khiển Bot</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { display: flex; flex-direction: row; gap: 30px; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); width: 850px; max-width: 95vw; height: 500px; }
        .left-panel { flex: 1; border-right: 1px solid #334155; padding-right: 30px; display: flex; flex-direction: column; justify-content: center; }
        .right-panel { flex: 1; padding-left: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        
        h2 { text-align: center; color: #38bdf8; margin-top: 0; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #94a3b8; }
        input { width: 100%; padding: 12px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; font-size: 15px; }
        input:focus { outline: none; border-color: #38bdf8; }
        .btn-submit { width: 100%; padding: 14px; background: #10b981; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 15px; font-size: 16px; transition: 0.2s; }
        .btn-submit:hover { background: #059669; }
        .success-msg { display: none; background: #065f46; color: #6ee7b7; padding: 12px; border-radius: 6px; text-align: center; margin-top: 15px; font-weight: bold; }
        
        .phone-container { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .phone-screen { max-width: 100%; max-height: 400px; border-radius: 8px; border: 2px solid #334155; display: none; object-fit: contain; background: #000; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .status-msg { margin-top: 15px; font-weight: bold; font-size: 16px; text-align: center; }
        .status-connected { color: #10b981; }
        .status-disconnected { color: #ef4444; }
        .icon-disconnected { font-size: 48px; color: #ef4444; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Nửa trái: Form đăng nhập -->
        <div class="left-panel">
            <h2>Bảng Điều Khiển Bot</h2>
            <form id="login-form" onsubmit="handleSubmit(event)">
                <div class="form-group">
                    <label>Tài khoản Game:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label>Mật khẩu Game:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" id="btn-submit" class="btn-submit">🚀 Chạy Bot Đăng Nhập</button>
                <button type="button" class="btn-submit" style="background: #eab308; margin-top: 10px;" onclick="handleCleanPopups()">🧹 Dọn Dẹp Popup & Sự Kiện</button>
                <button type="button" class="btn-submit" style="background: #8b5cf6; margin-top: 10px;" onclick="window.open('/gallery', '_blank')">🖼️ Xem Thư Viện Kho Đồ</button>
                <div id="success-alert" class="success-msg">Đã gửi lệnh cho Bot! Đang xử lý...</div>
            </form>
        </div>

        <!-- Nửa phải: Hiển thị điện thoại -->
        <div class="right-panel">
            <h2 style="color: #c084fc;">Thiết Bị Kết Nối</h2>
            <div class="phone-container">
                <div id="disconnected-icon" class="icon-disconnected">📱❌</div>
                <img id="phone-img" class="phone-screen" alt="Màn hình điện thoại" />
                <div id="device-status" class="status-msg status-disconnected">Đang kiểm tra kết nối...</div>
            </div>
        </div>
    </div>

    <script>
        function handleCleanPopups() {
            document.getElementById('success-alert').innerText = 'Đang ra lệnh cho Bot dọn dẹp màn hình...';
            document.getElementById('success-alert').style.display = 'block';
            fetch('/api/clean_popups', { method: 'POST' })
            .then(r => r.json())
            .then(d => {
                setTimeout(() => {
                    document.getElementById('success-alert').style.display = 'none';
                    document.getElementById('success-alert').innerText = 'Đã gửi lệnh cho Bot! Đang mở trình duyệt...';
                }, 3000);
            });
        }

        function handleSubmit(e) {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            
            document.getElementById('success-alert').style.display = 'block';
            document.getElementById('btn-submit').innerText = 'Đang chạy...';
            document.getElementById('btn-submit').disabled = true;

            fetch('/api/run_bot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'username=' + encodeURIComponent(u) + '&password=' + encodeURIComponent(p)
            })
            .then(r => r.json())
            .then(d => {
                setTimeout(() => {
                    document.getElementById('btn-submit').innerText = '🚀 Chạy Bot Đăng Nhập';
                    document.getElementById('btn-submit').disabled = false;
                    document.getElementById('success-alert').style.display = 'none';
                    document.getElementById('username').value = '';
                    document.getElementById('password').value = '';
                }, 3000);
            });
        }

        let isFetchingScreen = false;

        function checkDeviceStatus() {
            fetch('/api/device_status')
            .then(r => r.json())
            .then(data => {
                const statusEl = document.getElementById('device-status');
                const imgEl = document.getElementById('phone-img');
                const iconEl = document.getElementById('disconnected-icon');
                
                if (data.connected) {
                    statusEl.innerText = 'Đã kết nối: ' + data.devices[0];
                    statusEl.className = 'status-msg status-connected';
                    
                    if (!isFetchingScreen) {
                        isFetchingScreen = true;
                        iconEl.style.display = 'none';
                        imgEl.style.display = 'block';
                        
                        fetch('/api/screen')
                            .then(r => {
                                if (!r.ok) throw new Error('Không thể tải ảnh màn hình');
                                return r.blob();
                            })
                            .then(blob => {
                                const url = URL.createObjectURL(blob);
                                imgEl.onload = () => URL.revokeObjectURL(url);
                                imgEl.src = url;
                            })
                            .catch(err => console.error('Lỗi tải ảnh:', err))
                            .finally(() => {
                                isFetchingScreen = false;
                            });
                    }
                } else {
                    statusEl.innerText = 'Chưa kết nối điện thoại';
                    statusEl.className = 'status-msg status-disconnected';
                    imgEl.style.display = 'none';
                    iconEl.style.display = 'block';
                }
            })
            .catch(err => console.error('Lỗi kiểm tra thiết bị:', err))
            .finally(() => {
                // Chờ 2 giây trước khi gọi lại
                setTimeout(checkDeviceStatus, 2000);
            });
        }

        // Khởi động
        checkDeviceStatus();
    </script>
</body>
</html>
"""

class WebUIHandler(http.server.SimpleHTTPRequestHandler):
    """Xử lý yêu cầu HTTP cho Bảng điều khiển Web."""
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FORM.encode("utf-8"))
        elif parsed.path == "/api/device_status":
            devices = get_connected_devices()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"connected": len(devices) > 0, "devices": devices}).encode("utf-8"))
        elif parsed.path == "/api/screen":
            img_data = get_device_screen()
            if img_data:
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(img_data)
            else:
                self.send_response(404)
                self.end_headers()
        elif parsed.path.startswith("/scraped_data/"):
            import urllib.parse
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            decoded_path = urllib.parse.unquote(parsed.path)
            file_path = os.path.join(base_dir, decoded_path.lstrip("/"))
            if os.path.abspath(file_path).startswith(os.path.abspath(os.path.join(base_dir, "scraped_data"))):
                if os.path.exists(file_path):
                    self.send_response(200)
                    if file_path.endswith('.png'):
                        self.send_header("Content-Type", "image/png")
                    elif file_path.endswith('.json'):
                        self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                    return
            self.send_response(404)
            self.end_headers()
        elif parsed.path == "/gallery":
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "scraped_data", "database.json")
            data = {"heroes": []}
            debug_msg = ""
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    debug_msg = f"Đã đọc file JSON thành công: {json_path} (Tướng: {len(data.get('heroes', []))})"
                except Exception as e:
                    debug_msg = f"Lỗi đọc file JSON ({json_path}): {str(e)}"
            else:
                debug_msg = f"Không tìm thấy file: {json_path}"
            
            html = """<!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="UTF-8">
                <title>Thư Viện Tướng & Skin</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #fff; padding: 20px; }
                    .hero-section { margin-bottom: 40px; background: #1e293b; padding: 20px; border-radius: 12px; }
                    h2 { color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-top: 0; }
                    .skin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }
                    .skin-card { background: #0f172a; border-radius: 8px; overflow: hidden; border: 1px solid #334155; text-align: center; }
                    .skin-card img { width: 100%; height: auto; display: block; object-fit: contain; background: #000; }
                    .skin-card p { padding: 10px; margin: 0; font-size: 14px; font-weight: bold; color: #94a3b8; }
                    .nav { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
                    .nav a { color: #10b981; text-decoration: none; font-weight: bold; font-size: 16px; display: inline-block; padding: 10px 20px; background: #064e3b; border-radius: 6px; }
                    .btn-danger { background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
                    .btn-danger:hover { background: #dc2626; }
                    .debug { margin-top: 20px; color: #fbbf24; font-size: 12px; font-family: monospace; text-align: center; }
                </style>
                <script>
                    function deleteAll() {
                        if (confirm('Bạn có CHẮC CHẮN muốn XÓA TOÀN BỘ dữ liệu kho đồ và ảnh không? Hành động này không thể hoàn tác!')) {
                            fetch('/api/delete_all', { method: 'POST' })
                                .then(() => window.location.reload());
                        }
                    }
                    function deleteHero(folderName) {
                        if (confirm('Xóa dữ liệu tướng ' + folderName + '?')) {
                            fetch('/api/delete_hero', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                body: 'folder=' + encodeURIComponent(folderName)
                            }).then(() => window.location.reload());
                        }
                    }
                </script>
            </head>
            <body>
                <div class="nav">
                    <a href="/">← Quay lại Bảng Điều Khiển</a>
                    <button class="btn-danger" onclick="deleteAll()">🗑️ Xóa Tất Cả Dữ Liệu</button>
                </div>
                <h1 style="color: #c084fc; text-align: center;">🖼️ THƯ VIỆN KHO ĐỒ</h1>
            """
            
            for hero in data.get("heroes", []):
                folder_name = hero.get("folder", "")
                html += f'<div class="hero-section"><div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px;"><h2>Tướng: {folder_name}</h2> <button class="btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="deleteHero(\'{folder_name}\')">Xóa Tướng Này</button></div><div class="skin-grid">'
                for skin in hero.get("skins", []):
                    img_url = f"/scraped_data/{skin['file_path']}"
                    html += f'<div class="skin-card"><img src="{img_url}" alt="{skin["skin_name"]}" loading="lazy"><p>{skin["skin_name"]}</p></div>'
                html += '</div></div>'
                
            if not data.get("heroes"):
                html += "<p style='text-align: center; color: #ef4444;'>Chưa có dữ liệu. Vui lòng chạy Tool quét kho đồ trước!</p>"
                
            html += f'<div class="debug">{debug_msg}</div>'
            html += "</body></html>"
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run_bot":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            
            u = params.get('username', [''])[0]
            p = params.get('password', [''])[0]
            
            if u and p:
                BOT_JOB_QUEUE.append({"action": "login", "username": u, "password": p})
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        elif parsed.path == "/api/clean_popups":
            BOT_JOB_QUEUE.append({"action": "clean_popups"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        elif parsed.path == "/api/delete_all":
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            scraped_dir = os.path.join(base_dir, "scraped_data")
            import shutil
            if os.path.exists(scraped_dir):
                shutil.rmtree(scraped_dir)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        elif parsed.path == "/api/delete_hero":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            folder = params.get('folder', [''])[0]
            
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "scraped_data", "database.json")
            if folder and os.path.exists(json_path):
                import shutil
                img_dir = os.path.join(base_dir, "scraped_data", "Images", folder)
                if os.path.exists(img_dir):
                    shutil.rmtree(img_dir)
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["heroes"] = [h for h in data.get("heroes", []) if h.get("folder") != folder]
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))


class WebUIControlPanel:
    """Quản lý server Web UI dưới nền."""
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        self.server = http.server.ThreadingHTTPServer((self.host, self.port), WebUIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

