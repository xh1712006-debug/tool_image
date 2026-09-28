# Thiết Kế Giao Diện Giám Sát & Theo Dõi Tiến Trình (Monitoring & UI Design)

Để người vận hành dễ dàng theo dõi toàn bộ trạng thái chạy của 1000 tài khoản trong thời gian thực, hệ thống hỗ trợ 2 hình thức giao diện: **Terminal TUI Dashboard** (mặc định) và **Web/Desktop GUI Dashboard**.

---

## 1. Giao Diện Dòng Lệnh Hiện Đại (Modern Terminal UI - Rich TUI)

Sử dụng thư viện `rich` để dựng bảng điều khiển thời gian thực ngay trên cửa sổ Console/PowerShell mà không cần bật trình duyệt:

```text
┌─────────────────────────── GAME ACCOUNT AUTOMATION ENGINE v1.0 ───────────────────────────┐
│ Game: [Võ Lâm Truyền Kỳ] │ Dải chạy: 0001 -> 1000 │ Luồng: 3 Workers │ Proxy Pool: 15 Sạch │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ Tiến độ: [█████████████████████████----------------] 52.4% (524/1000)                      │
│ Thành công: 512 (97.7%) │ Thất bại: 12 (2.3%) │ Tốc độ: ~14 acc/phút │ Ước tính: 34 phút  │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ WORKER STATUS                                                                             │
│ • Worker #1: [dragon_0522] - Đang chờ OTP từ Mail (gamer_91@tmp.org) [12s]                │
│ • Worker #2: [dragon_0523] - Đang điền Form Đăng Ký (Proxy: 103.45.xx:8080)               │
│ • Worker #3: [dragon_0524] - Đăng ký THÀNH CÔNG -> Đang ghi file .txt                     │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ NHẬT KÝ THỜI GIAN THỰC (LIVE LOGS)                                                        │
│ [11:15:20] [INFO] [Worker 3] Hoàn tất dragon_0521 -> Đã lưu vào accounts_output.txt       │
│ [11:15:22] [WARN] [Worker 1] Mail timeout lần 1 -> Đang tự động đổi mail mới              │
│ [11:15:25] [INFO] [Worker 2] Đã kết nối Proxy Dân Cư IP 103.45.xx.xx (Độ trễ 45ms)       │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Giao Diện Đồ Họa Nâng Cao (Web / Desktop GUI Dashboard - Tùy chọn)

Nếu nâng cấp lên giao diện đồ họa hoàn chỉnh:
- **Desktop App**: Sử dụng **CustomTkinter** hoặc **Flet (Flutter for Python)** để đóng gói thành 1 file `.exe` duy nhất cho Windows.
- **Web App Dashboard**: Sử dụng **FastAPI** làm Backend phục vụ WebSocket và **Vite + React** làm giao diện điều khiển qua trình duyệt:
  - Form chọn game từ danh sách `game_profiles.json`.
  - Ô nhập số lượng (Start Index, End Index).
  - Nút **[BẮT ĐẦU CHẠY]**, **[TẠM DỪNG]**, **[TIẾP TỤC (RESUME)]**.
  - Bảng danh sách tài khoản đã tạo thành công với nút **[TẢI FILE .TXT]**.
