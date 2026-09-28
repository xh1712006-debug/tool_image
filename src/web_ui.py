import http.server
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

# Queue để giao tiếp giữa Web UI và luồng chạy Bot (async)
BOT_JOB_QUEUE = []

HTML_FORM = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Bảng Điều Khiển Bot</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); width: 360px; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 6px; font-size: 13px; color: #94a3b8; }
        input { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; }
        input:focus { outline: none; border-color: #38bdf8; }
        .btn-submit { width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; font-size: 15px; transition: 0.2s; }
        .btn-submit:hover { background: #059669; }
        .success-msg { display: none; background: #065f46; color: #6ee7b7; padding: 12px; border-radius: 6px; text-align: center; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Bảng Điều Khiển Bot Đăng Nhập</h2>
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
            <div id="success-alert" class="success-msg">Đã gửi lệnh cho Bot! Đang mở trình duyệt...</div>
        </form>
    </div>

    <script>
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
                BOT_JOB_QUEUE.append({"username": u, "password": p})
            
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
