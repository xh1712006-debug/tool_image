import cv2
import numpy as np
import os
import subprocess

def get_adb_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    adb_path = os.path.join(base_dir, "adb", "platform-tools", "adb.exe")
    if not os.path.exists(adb_path):
        adb_path = "adb"
    return adb_path

def get_screenshot():
    print("Đang chụp ảnh màn hình từ điện thoại...")
    adb_path = get_adb_path()
    result = subprocess.run([adb_path, 'exec-out', 'screencap', '-p'], capture_output=True)
    if result.returncode != 0 or not result.stdout:
        print("Không thể chụp màn hình. Vui lòng kiểm tra kết nối ADB.")
        return None
        
    nparr = np.frombuffer(result.stdout, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def main():
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    img = get_screenshot()
    if img is None:
        return
        
    print("\n--- HƯỚNG DẪN CẮT MẪU (TEMPLATE) ---")
    print("1. Một cửa sổ sẽ hiện ra hiển thị màn hình game của bạn.")
    print("2. Dùng chuột KÉO VÀ THẢ để tạo một ô vuông bao quanh nút X (hoặc Mũi tên, Bỏ qua).")
    print("3. Cố gắng kéo ô vuông vừa khít, TRÁNH lấy quá nhiều cảnh nền xung quanh.")
    print("4. Nhấn nút ENTER hoặc SPACE trên bàn phím để LƯU mẫu.")
    print("5. Nhấn phím ESC nếu bạn chọn sai hoặc muốn hủy bỏ.")
    print("--------------------------------------\n")
    
    # Scale ảnh xuống nếu quá to để dễ chọn trên màn hình máy tính
    scale_percent = 80 # Tỷ lệ thu nhỏ
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized_img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

    # Hiển thị cửa sổ chọn ROI
    window_name = "Chon vung (Keo chuot -> An Enter)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)
    
    # Hàm selectROI tự động xử lý chuột
    roi = cv2.selectROI(window_name, resized_img, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()
    
    if roi[2] > 0 and roi[3] > 0:
        # Tính toán lại tọa độ trên ảnh gốc do lúc nãy đã resize
        x = int(roi[0] / (scale_percent / 100))
        y = int(roi[1] / (scale_percent / 100))
        w = int(roi[2] / (scale_percent / 100))
        h = int(roi[3] / (scale_percent / 100))
        
        # Cắt ảnh
        cropped_template = img[y:y+h, x:x+w]
        
        # Hỏi người dùng muốn lưu tên gì
        print("\n[HUẤN LUYỆN BOT] Bạn vừa khoanh vùng xong! Hãy chọn mục đích:")
        print("=== CHỨC NĂNG CƠ BẢN ===")
        print("1. Nút tắt / Dấu X")
        print("2. Nút Bỏ qua")
        print("3. Nút Quay lại")
        print("4. Nút Avatar / Hồ sơ")
        print("=== VÙNG LẤY THÔNG TIN HỒ SƠ (Đọc Số) ===")
        print("5. Vùng chứa Cấp độ")
        print("6. Vùng chứa Số lượng Tướng")
        print("7. Vùng chứa Số lượng Trang phục")
        print("=== CHỨC NĂNG QUÉT KHO ĐỒ (Tướng & Skin) ===")
        print("8. Nút 'Tướng' (ở sảnh chính)")
        print("9. Nút 'Tất cả tướng'")
        print("10. Vị trí Tướng đầu tiên (Chỉ cần khoanh 1 ô nhỏ ở giữa tướng số 1)")
        print("11. Nút 'Trang phục' (Bên trong chi tiết tướng)")
        print("12. Nút mũi tên 'Chuyển Skin TIẾP THEO' (Sang phải)")
        print("13. Nút mũi tên 'Chuyển Tướng Tiếp Theo'")
        print("14. Nút/Hình 'MUA TRANG PHỤC' hoặc 'GIÁ TIỀN' (Dấu hiệu Chưa Sở Hữu - AI tìm bằng hình ảnh)")
        print("15. Vùng chứa TÊN TƯỚNG và TÊN SKIN (Để AI đọc và đặt tên file ảnh)")
        print("16. Vùng chứa ẢNH NHỎ bên phải (Để AI biết chính xác vị trí BẤM sang skin tiếp theo)")
        print("17. Vùng chụp HÌNH ẢNH MÔ HÌNH TƯỚNG (Nếu khoanh, AI chỉ cắt lưu vùng này thay vì toàn bộ màn hình)")
        print("Nhập số từ 1 đến 17:")
        choice = input("> ").strip()
        
        import json
        config_path = os.path.join(templates_dir, "roi_config.json")
        
        if choice in ['5', '6', '7', '15', '16', '17']:
            # Lưu tọa độ (ROI)
            roi_name = ""
            if choice == '5': roi_name = "level"
            elif choice == '6': roi_name = "heroes"
            elif choice == '7': roi_name = "skins"
            elif choice == '15': roi_name = "names_region"
            elif choice == '16': roi_name = "next_skin_region"
            elif choice == '17': roi_name = "skin_capture_region"
            
            roi_data = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    roi_data = json.load(f)
                    
            roi_data[roi_name] = {"x": x, "y": y, "w": w, "h": h}
            
            with open(config_path, "w") as f:
                json.dump(roi_data, f, indent=4)
                
            print(f"\n[THÀNH CÔNG] Đã lưu TOẠ ĐỘ vùng {roi_name.upper()} vào file {config_path}")
            print(f"Toạ độ: x={x}, y={y}, rộng={w}, cao={h}")
            
        else:
            filename = "unknown.png"
            if choice == '1': filename = "close_x.png"
            elif choice == '2': filename = "skip.png"
            elif choice == '3': filename = "back.png"
            elif choice == '4': filename = "btn_profile.png"
            elif choice == '8': filename = "btn_menu_heroes.png"
            elif choice == '9': filename = "btn_all_heroes.png"
            elif choice == '10': filename = "btn_first_hero.png"
            elif choice == '11': filename = "btn_skins_tab.png"
            elif choice == '12': filename = "btn_next_skin.png"
            elif choice == '13': filename = "btn_next_hero.png"
            elif choice == '14': filename = "unowned_sign.png"
                
            # Tìm tên file khả dụng
            base, ext = os.path.splitext(filename)
            counter = 1
            final_path = os.path.join(templates_dir, f"{base}_{counter}{ext}")
            while os.path.exists(final_path):
                counter += 1
                final_path = os.path.join(templates_dir, f"{base}_{counter}{ext}")
                
            cv2.imwrite(final_path, cropped_template)
            print(f"\n[THÀNH CÔNG] Đã lưu mẫu HÌNH ẢNH vào: {final_path}")
            
        print("=> Bạn có thể tiếp tục chạy lại lệnh này để huấn luyện các nút khác!")
    else:
        print("\n[HỦY] Không có vùng nào được chọn.")

if __name__ == '__main__':
    main()
