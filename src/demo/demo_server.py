import http.server
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

# Lưu mã OTP tạm thời cho email
ACTIVE_OTPS = {}

HTML_FORM = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Cổng Đăng Nhập Game Mẫu Demo</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); width: 360px; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 6px; font-size: 13px; color: #94a3b8; }
        input { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; }
        input:focus { outline: none; border-color: #38bdf8; }
        .btn-submit { width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; font-size: 15px; }
        .success-msg { display: none; background: #065f46; color: #6ee7b7; padding: 12px; border-radius: 6px; text-align: center; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Đăng Nhập Tài Khoản</h2>
        <form id="login-form" onsubmit="handleSubmit(event)">
            <div class="form-group">
                <label>Tên đăng nhập:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label>Mật khẩu:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" id="btn-submit" class="btn-submit">Đăng Nhập</button>
            <div id="success-alert" class="success-msg">🎉 Đăng nhập thành công!</div>
        </form>
    </div>

    <script>
        function handleSubmit(e) {
            e.preventDefault();
            document.getElementById('success-alert').style.display = 'block';
            document.getElementById('btn-submit').innerText = 'Đã Đăng Nhập!';
            document.getElementById('btn-submit').disabled = true;
        }
    </script>
</body>
</html>
"""


class DemoGameHandler(http.server.SimpleHTTPRequestHandler):
    """Xử lý yêu cầu HTTP cho cổng game demo cục bộ."""

    def log_message(self, format, *args):
        # Tắt log mặc định để màn hình không bị rác
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/login"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FORM.encode("utf-8"))
        elif parsed.path == "/api/send-otp":
            query = parse_qs(parsed.query)
            email = query.get("email", ["default@test.com"])[0]
            otp = "889922"
            ACTIVE_OTPS[email] = otp
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "otp": otp}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class DemoGameServer:
    """Quản lý khởi chạy server game demo dưới nền."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Khởi động server trên một thread riêng."""
        self.server = http.server.ThreadingHTTPServer((self.host, self.port), DemoGameHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        """Dừng server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()


if __name__ == "__main__":
    server = DemoGameServer()
    server.start()
    print(f"Demo Game Server đang chạy tại: http://127.0.0.1:8765/login")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
