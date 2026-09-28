# Game Account Automation Engine (GameAccAuto) 🚀🤖

**Game Account Automation Engine** là hệ thống tự động hóa đăng ký tài khoản game hàng loạt (1 - 1000) chuyên nghiệp, tích hợp dịch vụ Email ảo lấy mã OTP tự động, phòng vệ chống ban (Anti-Ban / Anti-Detection) và lưu trữ xuất file chuẩn hóa. 

Dự án được phát triển và vận hành dựa trên bộ khung **AgenticAI** - chuẩn hóa quy trình cộng tác giữa **Lập trình viên (User)** và **AI Agent (Antigravity)**.

---

## 📁 Cấu Trúc Thư Mục Hệ Thống (Directory Structure)

```text
📦 AIgent (GameAccAuto Project)
 ┣ 📂 .antigravity            # "Bộ não" vận hành & quy tắc của AI Agent
 ┃ ┣ 📂 rules                 # Các quy định lập trình bắt buộc
 ┃ ┗ 📂 skills                # Vòng đời phát triển (Generate - Review - Test - Push)
 ┣ 📂 docs                    # Kho tri thức kỹ thuật & Đặc tả hệ thống (Source of Truth)
 ┃ ┣ 📂 cores                 # Các tài liệu đặc tả nền tảng hệ thống
 ┃ ┣ 📂 features              # Đặc tả chi tiết các phân hệ nghiệp vụ & luồng hoạt động
 ┃ ┗ 📂 walkthroughs          # Hướng dẫn dành cho người vận hành
 ┣ 📂 src                     # Mã nguồn chính của hệ thống
 ┃ ┣ 📂 agents                # Agent thực thi logic (VD: assistant_runner.py)
 ┃ ┣ 📂 browser               # Tương tác trình duyệt & giả lập hành vi
 ┃ ┣ 📂 core                  # Lõi điều phối (VD: task_orchestrator.py)
 ┃ ┣ 📂 demo                  # Server giả lập phục vụ quá trình test
 ┃ ┣ 📂 network               # Xử lý xoay proxy chống ban
 ┃ ┣ 📂 services              # Các dịch vụ bên ngoài (VD: Temp Mail API)
 ┃ ┣ 📂 storage               # Tương tác Database SQLite & xuất file Text
 ┃ ┗ 📂 utils                 # Tiện ích tạo tài khoản, sinh chuỗi ngẫu nhiên
 ┣ 📜 ANTIGRAVITY.md          # Bản đồ định hướng chính cho AI Agent
 ┗ 📜 PROJECT_REQUIREMENTS.md # Yêu cầu nghiệp vụ chi tiết của sản phẩm (SRS)
```

---

## 🔄 5 Luồng Nghiệp Vụ Cốt Lõi (Core Workflows)

Hệ thống vận hành theo 5 luồng độc lập, xem chi tiết và sơ đồ tương tác tại [01-account-creation-workflow.md](file:///d:/project-test%28couse%29/tool_longcon/AIgent/docs/features/01-account-creation-workflow.md):

1. **Luồng 1: Generator & Profile Configuration**: Tự động sinh tên tuần tự từ 1 đến 1000 (`prefix_0001` -> `prefix_1000`), mật khẩu mặc định hoặc ngẫu nhiên, quản lý cấu hình đa game.
2. **Luồng 2: Temp Mail & Auto OTP Extractor**: Tạo email ảo 10 phút qua REST API, tự động Polling hòm thư và Regex trích xuất mã OTP trong 60s.
3. **Luồng 3: Registration Engine**: Điều khiển Playwright Stealth tự động điền form, mô phỏng gõ phím và hành vi người thật.
4. **Luồng 4: Anti-Ban & Anti-Detection**: Xoay IP qua Proxy Dân cư/4G, làm giả dấu vân tay trình duyệt (Canvas, WebGL, AudioContext) và thêm độ trễ ngẫu nhiên (Jitter).
5. **Luồng 5: State Persistence & Exporter**: Ghi dữ liệu thời gian thực ra file `.txt` phân tách bằng dấu `|` (`username|password|email|...`) và lưu song song vào SQLite để khôi phục tiến trình khi gặp sự cố.

---

## 🛠️ Hướng Dẫn Vận Hành Nhanh

Xem hướng dẫn chi tiết tại [01-quickstart-guide.md](file:///d:/project-test%28couse%29/tool_longcon/AIgent/docs/walkthroughs/01-quickstart-guide.md):

1. **Cài đặt môi trường**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **Chạy công cụ**:
   ```bash
   # Tạo từ 1 đến 1000 cho game mẫu
   python src/main.py --game GameMau --start 1 --end 1000

   # Tiếp tục phiên chạy dang dở (Resume)
   python src/main.py --game GameMau --resume
   ```
3. **Kết quả**: Được lưu tự động tại `output/accounts_output.txt`.

---

## 🤝 Chu Trình Phát Triển Với AI Agent (Antigravity)

Quy trình phát triển trong dự án tuân thủ nghiêm ngặt chu trình 4 bước: **Generate -> Review -> Test -> Push**:
- Mã nguồn đặt tên bằng Tiếng Anh.
- Chú thích (comments) trong mã nguồn viết hoàn toàn bằng **Tiếng Việt**.
- Tài liệu đặc tả kỹ thuật trong `docs/` là nguồn sự thật (Source of Truth), luôn đồng bộ sau khi test pass 100%.
