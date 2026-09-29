import os
import cv2
import json
import asyncio
import numpy as np

class ProfileScraper:
    def __init__(self, bot):
        self.bot = bot
        self.adb = bot.adb
        self.templates_dir = bot.templates_dir
        self.config_path = os.path.join(self.templates_dir, "roi_config.json")
        self.reader = None
        
    def _init_ocr(self):
        if self.reader is None:
            print("[OCR] Đang tải mô hình Trí Tuệ Nhân Tạo (EasyOCR) để đọc chữ... Vui lòng đợi vài giây.")
            import easyocr
            # Chỉ đọc số (en) để tốc độ siêu nhanh
            self.reader = easyocr.Reader(['en'], gpu=False)
            
    async def extract_info(self):
        print("\n=======================================================")
        print("      TIẾN HÀNH TRÍCH XUẤT THÔNG TIN TÀI KHOẢN         ")
        print("=======================================================")
        
        # 1. Bấm vào Avatar để vào trang hồ sơ
        # Do script tự đặt tên thành btn_1.png thay vì btn_profile_1.png
        avatar_template = os.path.join(self.templates_dir, "btn_1.png")
        if not os.path.exists(avatar_template):
            avatar_template = os.path.join(self.templates_dir, "btn_profile_1.png")
            if not os.path.exists(avatar_template):
                print("[LỖI] Không tìm thấy mẫu nút Avatar (btn_1.png). Bạn đã cắt chưa?")
                return None
                
        print("[1] Đang dùng 'Mắt Thần' tìm nút Avatar trên trang chủ...")
        screen_img = await self.bot.get_screenshot_cv2()
        matches = self.bot.find_template(screen_img, avatar_template, threshold=0.7)
        if not matches:
            print("[LỖI] Không tìm thấy Avatar trên màn hình! Có vẻ điện thoại chưa ở sảnh chính.")
            return None
            
        x, y = matches[0]
        print(f"  [+] Đã tìm thấy Avatar tại tọa độ ({x}, {y}). Đang tự động bấm vào...")
        await self.adb.tap(x, y)
        print("  [+] Đang đợi trang Hồ Sơ load xong...")
        await asyncio.sleep(4.0) # Đợi trang hồ sơ load
        
        # 2. Đọc cấu hình vùng khoanh (ROI)
        if not os.path.exists(self.config_path):
            print("[LỖI] Không tìm thấy file tọa độ roi_config.json!")
            return None
            
        with open(self.config_path, "r") as f:
            rois = json.load(f)
            
        print("[2] Đã vào trang Hồ Sơ. Đang chụp ảnh màn hình và bóc tách dữ liệu...")
        profile_img = await self.bot.get_screenshot_cv2()
        
        self._init_ocr()
        
        print("\n[3] BẮT ĐẦU QUÉT OCR ĐỌC SỐ...")
        results = {}
        for key, vn_name in [("level", "Cấp độ"), ("heroes", "Số Tướng"), ("skins", "Số Trang Phục")]:
            if key in rois:
                r = rois[key]
                # Cắt đúng vùng người dùng đã khoanh (y:y+h, x:x+w)
                crop = profile_img[r['y']:r['y']+r['h'], r['x']:r['x']+r['w']]
                
                # Tiền xử lý ảnh (trắng đen, phóng to x3) để OCR đọc chuẩn xác nhất
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                
                # Có thể lưu ra file tạm để debug
                cv2.imwrite(os.path.join(self.templates_dir, f"debug_{key}.png"), gray)
                
                # Dùng AI đọc text (chỉ cho phép đọc số 0-9)
                text_result = self.reader.readtext(gray, allowlist='0123456789', detail=0)
                
                if text_result:
                    value = text_result[0]
                else:
                    value = "Không thể đọc"
                    
                results[key] = value
                print(f"  -> {vn_name.upper()}: [ {value} ]")
            else:
                print(f"  -> {vn_name.upper()}: Bỏ qua (Chưa huấn luyện)")
                
        print("\n================= KẾT QUẢ TỔNG HỢP ====================")
        print(f"🌟 Cấp độ     : {results.get('level', 'N/A')}")
        print(f"⚔️ Số Tướng   : {results.get('heroes', 'N/A')}")
        print(f"👕 Trang Phục : {results.get('skins', 'N/A')}")
        print("=======================================================\n")
        
        # 3. Thoát ra lại trang chủ
        print("[4] Đang click Mũi tên góc trái để thoát về trang chủ...")
        clicked_back = False
        import glob
        back_templates = glob.glob(os.path.join(self.templates_dir, "back_*.png"))
        
        for back_template in back_templates:
            matches = self.bot.find_template(profile_img, back_template, threshold=0.7)
            if matches:
                bx, by = matches[0]
                print(f"  -> Tìm thấy nút Quay lại từ mẫu {os.path.basename(back_template)}")
                await self.adb.tap(bx, by)
                clicked_back = True
                await asyncio.sleep(2.0)
                break
                
        if not clicked_back:
            # Nếu không tìm thấy bằng template, thì gõ cứng tọa độ góc trái (fallback)
            print("  -> Không tìm thấy mẫu nút Quay lại, thử bấm tọa độ góc trái (60, 55)")
            await self.adb.tap(60, 55)
            
        return results
