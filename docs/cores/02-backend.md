# Thiết Kế Kiến Trúc Backend & Động Cơ Tự Động Hóa (Engine Architecture)

Tài liệu này đặc tả cấu trúc mã nguồn, các lớp trừu tượng (Abstract Layers) và mô hình điều phối tác vụ (Task Orchestration) cho công cụ tự động hóa.

---

## 1. Công Nghệ Nền Tảng (Core Stack)
- **Ngôn ngữ**: Python 3.10+ (hoặc Node.js TypeScript).
- **Trình duyệt Tự động hóa**: `playwright` kết hợp thư viện `playwright-stealth` (ẩn thuộc tính webdriver).
- **Giao tiếp Mạng & API**: `httpx` (hỗ trợ HTTP/2, async connection pooling) / `aiohttp`.
- **Cơ sở dữ liệu Cục bộ**: `sqlite3` (hoặc `aiosqlite`) với chuẩn WAL mode.
- **Xác thực dữ liệu**: `pydantic v2` định nghĩa Schema cấu hình và dữ liệu tài khoản.

---

## 2. Cấu Trúc Thư Mục Mã Nguồn Module Hóa (Modular Directory Layout)

Hệ thống được tổ chức theo từng module độc lập, phân tách rõ ràng giữa nghiệp vụ sinh dữ liệu, giao tiếp API bên ngoài, điều khiển trình duyệt và xuất báo cáo:

```text
📦 GameAccountCreator
 ┣ 📂 configs                     # Tệp cấu hình hệ thống & hồ sơ game
 ┃ ┣ 📜 app_config.yaml           # Cấu hình số luồng, timeout, chế độ delay
 ┃ ┣ 📜 game_profiles.json        # Định nghĩa selectors, URL đăng ký các game
 ┃ ┗ 📜 proxies.txt               # Danh sách proxy (ip:port:user:pass)
 ┣ 📂 src
 ┃ ┣ 📂 core                      # Động cơ tự động hóa cốt lõi
 ┃ ┃ ┣ 📜 account_gen.py          # Bộ sinh tên từ 1 đến 1000 & mật khẩu
 ┃ ┃ ┣ 📜 browser_engine.py       # Khởi tạo Playwright Stealth & Context
 ┃ ┃ ┣ 📜 proxy_manager.py        # Quản lý danh sách, kiểm tra sức khỏe & xoay IP
 ┃ ┃ ┗ 📜 task_orchestrator.py    # Điều phối luồng xử lý chính (Pipeline)
 ┃ ┣ 📂 services                  # Giao tiếp với các dịch vụ bên ngoài
 ┃ ┃ ┣ 📜 temp_mail_service.py    # Kết nối REST API Mail ảo & Regex bóc tách OTP
 ┃ ┃ ┗ 📜 captcha_solver.py       # Adapter giải Captcha tự động (Capsolver/2Captcha)
 ┃ ┣ 📂 storage                   # Quản lý dữ liệu đầu ra
 ┃ ┃ ┣ 📜 sqlite_repo.py          # Xử lý truy vấn SQLite, quản lý tiến trình Resume
 ┃ ┃ ┗ 📜 txt_exporter.py         # Ghi file .txt định dạng "|" kèm File Lock
 ┃ ┣ 📂 utils                     # Công cụ tiện ích bổ trợ
 ┃ ┃ ┣ 📜 human_emulation.py      # Delay ngẫu nhiên, mô phỏng gõ phím người thật
 ┃ ┃ ┗ 📜 logger.py               # Ghi log thời gian thực chuẩn định dạng
 ┃ ┗ 📜 main.py                   # Điểm khởi chạy ứng dụng (Entry Point)
 ┣ 📂 storage                     # Thư mục lưu dữ liệu SQLite & logs
 ┃ ┗ 📜 database.sqlite           # Tệp SQLite cục bộ
 ┣ 📂 output                      # Thư mục chứa kết quả xuất ra
 ┃ ┗ 📜 accounts_output.txt       # File kết quả dạng username|password|email|...
 ┣ 📜 requirements.txt            # Thư viện phụ thuộc
 ┗ 📜 README.md                   # Hướng dẫn cài đặt & vận hành
```

---

## 3. Thiết Kế Các Lớp Trừu Tượng Cốt Lõi (Core Interfaces)

### 3.1 Giao diện Dịch vụ Email Ảo (Temp Mail Interface)
Cho phép linh hoạt hoán đổi giữa nhiều nhà cung cấp mail (Mail.tm, GuerrillaMail, 1secmail hoặc Cloudflare) mà không phải sửa logic chính:

```python
from abc import ABC, abstractmethod

class ITempMailProvider(ABC):
    @abstractmethod
    async def create_inbox(self) -> str:
        """Tạo một hòm thư ảo mới và trả về địa chỉ email."""
        pass

    @abstractmethod
    async def wait_for_otp(self, email: str, timeout_sec: int = 60) -> str:
        """Lắng nghe hộp thư đến và bóc tách mã OTP qua Regex."""
        pass
```

### 3.2 Giao diện Xuất Dữ Liệu (Exporter Interface)
Hỗ trợ ghi nối an toàn nhiều luồng vào file `.txt`:

```python
class TxtExporter:
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def append_account(self, account_data: dict):
        """Ghi thông tin tài khoản ngăn cách bởi dấu | có khóa file an toàn."""
        line = (
            f"{account_data['username']}|"
            f"{account_data['password']}|"
            f"{account_data['email']}|"
            f"{account_data['game_name']}|"
            f"{account_data['status']}|"
            f"{account_data['created_at']}\n"
        )
        # Sử dụng aiofiles hoặc cơ chế lock file an toàn
        ...
```
