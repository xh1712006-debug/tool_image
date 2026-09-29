# 🚀 Tool Auto Quét Kho Đồ Tướng & Skin Liên Quân Mobile (AI OCR + ADB)

Đây là công cụ tự động hóa hoàn toàn việc quét, thống kê và lưu trữ hình ảnh Tướng/Skin trong game Liên Quân Mobile. Công cụ sử dụng công nghệ nhận diện hình ảnh (Computer Vision), AI đọc chữ (OCR) và giả lập thao tác (ADB) để đạt độ an toàn 100% (Không can thiệp API/RAM game).

---

## 🔥 Tính năng nổi bật

- **Nhận diện Tướng & Trang phục bằng AI (EasyOCR + OpenCV):** Đọc tên skin ngay trên màn hình để đặt tên file ảnh chuẩn xác.
- **Giả lập thao tác người dùng (ADB):** Tự động bấm, vuốt mượt mà. Đảm bảo an toàn 100%, không lo khóa tài khoản.
- **Tốc độ "Bàn thờ" (Extreme Speed):** Tối ưu hóa thời gian chờ (delay) giúp quét 1000 skin chỉ trong khoảng 10-15 phút (tùy tốc độ xử lý của máy tính và điện thoại).
- **Cơ chế chống lặp thông minh:** Tự động phát hiện khi đã quét hết skin của một tướng để chuyển sang tướng tiếp theo.
- **Giao diện Web UI:** Theo dõi tiến độ quét và quản lý thư viện ảnh trực tiếp trên trình duyệt.

---

## ⚙️ Yêu cầu hệ thống

1. **Hệ điều hành:** Windows 10/11.
2. **Ngôn ngữ:** Python 3.11.
3. **Phần cứng:**
   - Ưu tiên có Card đồ họa rời (NVIDIA GPU) để chạy AI EasyOCR nhanh nhất. (Nếu không có sẽ dùng CPU).
   - Thiết bị Android (hoặc giả lập Android như LDPlayer, Nox, Bluestacks).
4. **Cài đặt Android:** Thiết bị/Giả lập phải được bật tính năng **USB Debugging (Gỡ lỗi USB)**.

---

## 🛠 Hướng dẫn Cài đặt & Chạy Tool

### Bước 1: Cài đặt thư viện Python
Mở Terminal/PowerShell và chạy lệnh:
```powershell
# Bật môi trường ảo (nếu có)
.\.venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### Bước 2: Thiết lập Game
1. Mở game Liên Quân Mobile trên điện thoại hoặc giả lập.
2. Đăng nhập vào tài khoản cần quét.
3. **Quan trọng:** Để nguyên màn hình ở **SẢNH CHÍNH** của game.

### Bước 3: Chạy Tool Quét (Chế độ Tối đa tốc độ)
Mở Terminal và chạy lệnh sau để bật tool:
```powershell
$env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe test_hero_scraper.py
```
- Tool sẽ khởi động và tải AI Nhận diện chữ (Mất khoảng vài chục giây cho lần đầu).
- Sau khi tải xong, màn hình Terminal sẽ hiện: **`[SẴN SÀNG] Nhấn phím ENTER để BẮT ĐẦU QUÉT`**.
- Bạn chỉ cần bấm Enter, rồi bỏ tay khỏi chuột/bàn phím để Tool tự động làm việc.
- Sau khi quét xong nick 1, bạn có thể tự tay chuyển acc khác trong game, sau đó lại bấm Enter ở Terminal để quét nick 2 (Không cần tải lại AI).

---

## 📂 Cấu trúc thư mục Output

Tất cả ảnh chụp và báo cáo sẽ được tự động phân loại và lưu tại thư mục `scraped_data/`:
```text
scraped_data/
├── BaoCao_QuetSkin.md      # Báo cáo tổng hợp số lượng Tướng/Skin
├── database.json           # Dữ liệu dạng JSON dùng cho Web UI
└── Images/                 # Thư mục chứa ảnh đã phân loại
    ├── Tuong_001/          # Ảnh của tướng 1
    │   ├── Ten_Skin_1.png
    │   └── Ten_Skin_2.png
    ├── Tuong_002/
    └── ...
```

---

## ⚠️ Lưu ý Quan Trọng
- **Tuyệt đối không chạm vào màn hình/chuột** của giả lập điện thoại trong lúc Tool đang chạy để tránh việc click nhầm.
- Tool ưu tiên tốc độ quét bằng cách giảm độ trễ xuống mức tối thiểu. Nếu máy tính hoặc giả lập của bạn bị lag, game không kịp hiển thị hiệu ứng đổi skin, bạn có thể tự tăng thêm thời gian nghỉ `asyncio.sleep()` trong file `src/core/hero_scraper.py`.
- Các file mẫu nhận diện (Template Matching) nằm trong thư mục `templates/`. Không được xóa thư mục này vì Tool dùng nó để làm hệ quy chiếu click màn hình.
