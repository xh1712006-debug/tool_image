# Hướng Dẫn Vận Hành & Theo Dõi Tiến Trình (Operator Quickstart Guide)

Tài liệu này hướng dẫn chi tiết cách cấu hình, khởi chạy và theo dõi công cụ **Game Account Automation Engine** một cách an toàn và dễ dàng nhất.

---

## 1. Chuẩn Bị Môi Trường & Cài Đặt

1. **Yêu cầu hệ thống**:
   - Python 3.10 trở lên trên Windows / macOS / Linux.
   - Trình duyệt Chromium được cài đặt tự động qua Playwright.

2. **Cài đặt thư viện phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## 2. Cấu Hình Trước Khi Chạy

Tất cả các tham số đều được quản lý tập trung trong thư mục `configs/`:

### 2.1 Cấu hình Game trong `configs/game_profiles.json`
Định nghĩa thông tin cổng đăng ký của game bạn muốn chạy:
```json
{
  "GameMau": {
    "name": "Game Mẫu",
    "register_url": "https://example-game.com/register",
    "selectors": {
      "username_input": "#txtUsername",
      "email_input": "#txtEmail",
      "password_input": "#txtPassword",
      "repassword_input": "#txtConfirmPassword",
      "send_otp_btn": "#btnSendOtp",
      "otp_input": "#txtOtpCode",
      "submit_btn": "#btnSubmitRegister"
    },
    "default_password": "GamePassword123@",
    "otp_wait_seconds": 60
  }
}
```

### 2.2 Cấu hình Chống Ban trong `configs/app_config.yaml`
```yaml
generator:
  prefix: "gamer"
  start_index: 1
  end_index: 1000
  padding: 4 # gamer_0001 -> gamer_1000

workers:
  concurrency: 3 # Số tài khoản chạy song song cùng lúc

anti_ban:
  use_proxy: true
  proxy_rotation_every: 2 # Đổi IP sau mỗi 2 tài khoản
  human_typing_delay_ms: [60, 140]
  step_jitter_sec: [2, 5]

storage:
  output_txt_path: "output/accounts_output.txt"
  sqlite_db_path: "storage/database.sqlite"
```

---

## 3. Cách Khởi Chạy & Theo Dõi Tiến Trình

1. **Khởi chạy bình thường**:
   ```bash
   python src/main.py --game GameMau --start 1 --end 1000
   ```

2. **Bảng điều khiển theo dõi**:
   - Màn hình Console sẽ lập tức hiển thị bảng tiến trình (Progress Bar), tỷ lệ thành công, số worker đang hoạt động và địa chỉ IP Proxy đang gán cho từng worker.

3. **Tính năng Khôi phục khi gặp sự cố (Resume)**:
   - Nếu trong quá trình chạy bị cúp điện hoặc rớt mạng ở tài khoản thứ 350:
     ```bash
     python src/main.py --game GameMau --resume
     ```
   - Tool sẽ tự động đọc cơ sở dữ liệu SQLite và tiếp tục chạy từ tài khoản 351, không tạo lại các tài khoản đã thành công.

---

## 4. Quản Lý Kết Quả Đầu Ra

Kết quả tài khoản được tự động ghi vào tệp `output/accounts_output.txt`:
```text
gamer_0001|GamePassword123@|vnl_84920@tmpmail.com|GameMau|SUCCESS|2026-09-21 11:05:12
gamer_0002|GamePassword123@|vnl_19284@tmpmail.com|GameMau|SUCCESS|2026-09-21 11:05:45
gamer_0003|GamePassword123@|vnl_58291@tmpmail.com|GameMau|SUCCESS|2026-09-21 11:06:18
```
Mỗi trường dữ liệu ngăn cách bằng ký tự `|` giúp bạn dễ dàng import vào Excel, Google Sheets hoặc các phần mềm quản lý tài khoản khác.
