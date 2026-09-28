# Đặc Tả Luồng Nghiệp Vụ Toàn Diện (Account Creation Workflows)

Tài liệu này trực quan hóa toàn bộ chu trình hoạt động của hệ thống **Game Account Automation Engine**. Các luồng được thiết kế dạng module khép kín, có sơ đồ tương tác rõ ràng giúp người vận hành và AI Agent dễ dàng theo dõi, giám sát và gỡ lỗi.

---

## 1. Sơ Đồ Máy Trạng Thái Toàn Cục (Global State Machine)

Mỗi tài khoản từ dải số `1 đến 1000` sẽ trải qua một chu trình chuyển đổi trạng thái nghiêm ngặt dưới đây:

```mermaid
stateDiagram-v2
    [*] --> PENDING : Nạp vào Hàng đợi (Queue)
    PENDING --> PROXY_ASSIGNING : Lấy tác vụ
    PROXY_ASSIGNING --> PROXY_READY : Gán Proxy thành công
    PROXY_ASSIGNING --> RETRY : Lỗi Proxy (Thử lại)
    
    PROXY_READY --> MAIL_CREATING : Gọi Temp Mail API
    MAIL_CREATING --> MAIL_READY : Đã có Email ảo (10m)
    MAIL_CREATING --> RETRY : Lỗi API Mail
    
    MAIL_READY --> BROWSER_NAVIGATING : Mở phiên duyệt Playwright Stealth
    BROWSER_NAVIGATING --> FORM_FILLING : Tải xong trang đăng ký
    FORM_FILLING --> OTP_WAITING : Điền Form & Bấm "Gửi mã"
    
    OTP_WAITING --> OTP_RECEIVED : Bóc tách mã OTP thành công
    OTP_WAITING --> RETRY : Quá thời gian 60s (Timeout)
    
    OTP_RECEIVED --> SUBMITTING : Điền OTP & Bấm Đăng ký
    SUBMITTING --> SUCCESS : Đăng ký thành công (200 OK)
    SUBMITTING --> RETRY : Bị từ chối / Captcha / Lỗi mạng
    
    RETRY --> PENDING : Số lần thử < 3
    RETRY --> FAILED : Đã thử 3 lần thất bại
    
    SUCCESS --> EXPORTING : Ghi file .txt & Cập nhật SQLite
    FAILED --> EXPORTING : Ghi log thất bại
    EXPORTING --> [*] : Hoàn tất tác vụ
```

---

## 2. Chi Tiết 5 Luồng Hoạt Động Cốt Lõi

### 🔹 Luồng 1: Generator & Profile Configuration (Sinh ID 1-1000 & Hồ Sơ Game)

Luồng này chịu trách nhiệm chuẩn bị nguyên liệu đầu vào cho toàn bộ chu trình.

```mermaid
flowchart TD
    Start([Bắt đầu Phiên]) --> LoadProfile[Đọc Game Profile: game_name, register_url, selectors]
    LoadProfile --> ReadDB[Kiểm tra SQLite: Tìm số thứ tự đã hoàn thành]
    ReadDB --> DetermineRange[Xác định dải chạy: Start Index -> End Index]
    
    subgraph Sinh Dữ Liệu Tài Khoản
        DetermineRange --> GenUser["Sinh Username: f'{prefix}_{index:04d}'"]
        GenUser --> CheckPassRule{Chế độ Mật khẩu?}
        CheckPassRule -- Mặc định --> DefaultPass[Dùng mật khẩu cố định đã cài đặt]
        CheckPassRule -- Ngẫu nhiên --> RandomPass[Sinh mật khẩu phức tạp: Hoa + Thường + Số + Ký tự đặc biệt]
    end
    
    DefaultPass --> PushQueue[Đẩy vào Hàng đợi Xử lý - Task Queue]
    RandomPass --> PushQueue
```

* **Quy tắc sinh Username**:
  * Tùy biến mẫu: `{prefix}_{index:04d}` (Ví dụ: `valiant_0001` đến `valiant_1000`).
  * Có tùy chọn thêm hậu tố ngẫu nhiên (ví dụ: `valiant_0001_k8`) nhằm vô hiệu hóa các câu lệnh quét hàng loạt của Game Master (ví dụ: `SELECT * FROM users WHERE username LIKE 'valiant_%'`).
* **Hồ sơ Game (Game Profiles)**:
  * Lưu trữ độc lập tại `configs/game_profiles.json`, cho phép dùng chung 1 tool cho nhiều tựa game khác nhau chỉ bằng cách thay đổi cấu hình selector.

---

### 🔹 Luồng 2: Temp Mail Service & Auto OTP Extractor (Mail Ảo & Bóc Tách Mã)

Quy trình tự động hóa tương tác với dịch vụ email tạm thời thông qua REST API tốc độ cao:

```mermaid
sequenceDiagram
    autonumber
    participant Worker as Worker Engine
    participant MailAPI as Temp Mail REST API
    participant MailBox as Hòm thư Ảo
    participant GameSrv as Game Mail Server

    Worker->>MailAPI: POST /accounts (Khởi tạo hòm thư mới)
    MailAPI-->>Worker: Trả về địa chỉ Email (ví dụ: gamer_91@tmpbox.org) & Token truy cập
    Note over Worker: Lưu email vào thông tin phiên đăng ký
    
    Worker->>GameSrv: Form kích hoạt gửi mã OTP tới gamer_91@tmpbox.org
    GameSrv-->>MailBox: Gửi email xác nhận (chứa mã: 948210)
    
    loop Polling hòm thư (Mỗi 3 - 5 giây, Timeout = 60s)
        Worker->>MailAPI: GET /messages (Lấy danh sách thư mới)
        alt Hòm thư chưa có thư mới
            MailAPI-->>Worker: [] (Trống)
            Worker->>Worker: Tạm dừng (Sleep) 3s
        else Đã nhận được thư từ Game
            MailAPI-->>Worker: [Message Object] (ID thư)
            Worker->>MailAPI: GET /messages/{id} (Lấy nội dung thư)
            MailAPI-->>Worker: Nội dung Text / HTML của thư
            Worker->>Worker: Chạy Regex: r"\b\d{4,6}\b" để trích xuất OTP
            Note over Worker: Trích xuất thành công OTP: 948210
        end
    end
```

* **Xử lý sự cố (Error Handling)**:
  * Nếu quá 60s không thấy thư về -> Đánh dấu `MAIL_TIMEOUT`, hủy email hiện tại và cấp email mới để thử lại.

---

### 🔹 Luồng 3: Registration Engine & Form Automation (Tự Động Điền Form)

Sử dụng **Playwright Stealth** điều khiển trình duyệt không để lại dấu vết tự động hóa:

```mermaid
sequenceDiagram
    autonumber
    participant Worker as Worker Engine
    participant Browser as Playwright Stealth Browser
    participant Page as Web Page Đăng Ký
    participant GameSrv as Game Backend API

    Worker->>Browser: Mở Context với User-Agent & Viewport ngẫu nhiên
    Browser->>Page: Truy cập URL Đăng Ký
    Page-->>Browser: Tải hoàn tất DOM
    
    Worker->>Page: Focus vào ô "Tên đăng nhập"
    Worker->>Page: Gõ Username (Mô phỏng delay người gõ: 60-120ms/phím)
    
    Worker->>Page: Focus vào ô "Email"
    Worker->>Page: Gõ Email ảo vừa lấy từ Luồng 2
    
    Worker->>Page: Focus vào ô "Mật khẩu"
    Worker->>Page: Gõ Password
    
    Worker->>Page: Focus vào ô "Nhập lại Mật khẩu"
    Worker->>Page: Gõ Re-enter Password
    
    Worker->>Page: Click nút "Gửi mã OTP"
    Note over Worker: Chờ Luồng 2 trích xuất được mã OTP
    
    Worker->>Page: Focus vào ô "Mã xác thực OTP"
    Worker->>Page: Gõ mã OTP
    
    Worker->>Page: Click nút "Hoàn tất Đăng Ký"
    Page->>GameSrv: Gửi Payload Đăng Ký
    GameSrv-->>Page: Phản hồi Thành Công (Redirect hoặc Thông Báo)
    Page-->>Worker: Xác nhận trạng thái Đăng ký Thành Công!
```

---

### 🔹 Luồng 4: Lớp Phòng Vệ Chống Ban (Anti-Detection & Evasion Strategy)

Đây là lớp phòng thủ cốt lõi để đảm bảo tool chạy an toàn 1000 tài khoản mà không bị chặn dải IP hoặc bị khóa tài khoản hàng loạt:

```mermaid
graph TD
    subgraph 1. Quản lý Mạng - IP Layer
        ProxyPool[Proxy Pool: Dân Cư / 4G Xoay] -->|Cấp Proxy riêng| RequestWorker[Tác vụ Đăng ký]
        RequestWorker -->|Kiểm tra IP sau mỗi N acc| RotateCheck{Đã tạo đủ N acc?}
        RotateCheck -- Đúng --> TriggerRotate[Gửi API xoay IP mới]
        RotateCheck -- Sai --> KeepIP[Tiếp tục phiên hiện tại]
    end

    subgraph 2. Ngụy Trang Trình Duyệt - Fingerprint Layer
        StealthEngine[Playwright Stealth Engine] --> HideWebDriver[Vô hiệu hóa navigator.webdriver = undefined]
        StealthEngine --> SpoofCanvas[Xáo trộn Canvas Fingerprint & WebGL Hash]
        StealthEngine --> RandomAudio[Giả lập AudioContext]
        StealthEngine --> RotateUA[Xoay User-Agent Chrome/Edge mới nhất]
    end

    subgraph 3. Mô Phỏng Hành Vi - Behavioral Layer
        HumanSim[Mô phỏng Con người] --> Jitter[Thêm độ trễ ngẫu nhiên Jitter: 1.5s - 4.5s]
        HumanSim --> TypingCurve[Tốc độ gõ phím biến thiên tự nhiên]
        HumanSim --> MouseCurve[Di chuyển chuột theo đường cong Bezier]
    end
```

---

### 🔹 Luồng 5: State Persistence & Exporter (Quản lý Tiến Trình & Xuất Dữ Liệu)

Đảm bảo an toàn dữ liệu, chống mất mát khi gặp sự cố phần cứng, mất điện hoặc đứt cáp mạng:

```mermaid
flowchart LR
    SuccessEvent([Đăng ký Thành Công]) --> PrepareData[Chuẩn bị Dữ liệu Format]
    
    subgraph Ghi Dữ Liệu Kép - Dual Storage
        PrepareData --> BuildString["Tạo chuỗi: username|password|email|game|SUCCESS|created_at"]
        BuildString --> LockFile[Thực hiện File Lock]
        LockFile --> AppendTxt[Ghi nối vào file accounts_output.txt]
        AppendTxt --> UnlockFile[Giải phóng File Lock]
        
        PrepareData --> SQLiteInsert["INSERT INTO accounts (username, password, email, status, ...)"]
        SQLiteInsert --> CommitDB[Commit Transaction SQLite]
    end
    
    UnlockFile --> NotifyUser[Cập nhật Giao diện: Tăng số lượng Thành công]
    CommitDB --> NotifyUser
```

* **Định dạng file xuất chuẩn `.txt`**:
  ```text
  dragon_0001|PassSecret123@|vnl_84920@tmpmail.com|VõLâmTruyềnKỳ|SUCCESS|2026-09-21 11:05:12
  dragon_0002|PassSecret123@|vnl_19284@tmpmail.com|VõLâmTruyềnKỳ|SUCCESS|2026-09-21 11:05:45
  ```
* **Cơ chế Tiếp tục khi khởi động lại (Resume Mechanism)**:
  * Khi khởi động lại, tool tự động kiểm tra cơ sở dữ liệu `local_store.db`:
    `SELECT MAX(sequence_number) FROM accounts WHERE game_name = 'VõLâmTruyềnKỳ' AND status = 'SUCCESS'`
  * Nếu tìm thấy số `452`, tool tự động bắt đầu từ số `453`, bỏ qua các tài khoản đã tạo thành công trước đó.

---

## 3. Ma Trận Xử Lý Lỗi & Kịch Bản Phục Hồi (Error Matrix & Recovery)

| Tình Huống Lỗi | Nguyên Nhân Phổ Biến | Hành Động Phục Hồi Tự Động của Tool |
| :--- | :--- | :--- |
| **Email Timeout (>60s)** | Server game gửi mail chậm hoặc hòm thư ảo bị nghẽn | Hủy hòm thư hiện tại, tạo hòm thư ảo mới, bấm "Gửi lại mã" (Thử tối đa 2 lần). |
| **IP Rate Limit (HTTP 429)** | Tạo quá nhiều tài khoản trên 1 địa chỉ IP | Kích hoạt xoay Proxy ngay lập tức, tạm dừng (Sleep) 30s trước khi thử lại tài khoản đó. |
| **Tên tài khoản đã tồn tại** | Đã có người khác đăng ký username này | Tự động thêm hậu tố ngẫu nhiên (ví dụ: `_x1`) và thử đăng ký lại ngay lập tức. |
| **Phát hiện Captcha (Turnstile/reCAPTCHA)** | Hành vi bị nghi ngờ bot | Kích hoạt Module Giải Captcha (2Captcha/Capsolver API) hoặc thông báo người dùng can thiệp thủ công. |
| **Mất kết nối mạng / Crash tool** | Sự cố môi trường máy tính | Khi bật lại tool, SQLite tự động nạp vị trí lưu gần nhất và tiếp tục chạy bình thường. |
