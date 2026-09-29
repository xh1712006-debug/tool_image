import os
import cv2
import json
import asyncio
import numpy as np
from datetime import datetime

class HeroScraper:
    def __init__(self, bot):
        self.bot = bot
        self.adb = bot.adb
        self.templates_dir = bot.templates_dir
        self.config_path = os.path.join(self.templates_dir, "roi_config.json")
        self.reader = None
        self.output_dir = os.path.join(os.path.dirname(self.templates_dir), "scraped_data")
        self.images_dir = os.path.join(self.output_dir, "Images")
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Data quản lý
        self.report_data = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_heroes_scanned": 0,
            "total_skins_scanned": 0,
            "heroes": []
        }
        
    def _init_ocr(self):
        if self.reader is None:
            print("[OCR] Đang tải AI nhận diện chữ... Vui lòng đợi.")
            import easyocr
            # Dùng tiếng Việt (vi) và Anh (en)
            self.reader = easyocr.Reader(['vi', 'en'], gpu=True)
            
    async def run_hero_scraping(self, max_heroes=129, max_skins=218):
        print("\n=======================================================")
        print("      BẮT ĐẦU CHIẾN DỊCH QUÉT KHO TƯỚNG & SKIN         ")
        print("=======================================================")
        
        # 1. Bấm vào Tướng ở sảnh
        import glob
        btn_heroes_list = glob.glob(os.path.join(self.templates_dir, "btn_menu_heroes_*.png"))
        print("[1] Tìm nút Tướng ở sảnh...")
        clicked = False
        for btn in btn_heroes_list:
            if await self._click_template(btn):
                clicked = True
                break
        if not clicked:
            print("[LỖI] Không tìm thấy nút Tướng (mẫu số 8). Dừng quét.")
            return
        await asyncio.sleep(0.8)
        
        # 2. Bấm vào vị tướng đầu tiên
        btn_first_list = glob.glob(os.path.join(self.templates_dir, "btn_first_hero_*.png"))
        print("[2] Tìm tướng đầu tiên...")
        clicked_first = False
        for btn in btn_first_list:
            if await self._click_template(btn):
                clicked_first = True
                break
        if not clicked_first:
            print("[LỖI] Không tìm thấy vị tướng đầu tiên (mẫu số 10).")
            return
        await asyncio.sleep(0.8)
        
        # Bắt đầu vòng lặp quét Tướng
        hero_count = 0
        skin_count = 0
        
        # Nạp OCR
        self._init_ocr()
        
        with open(self.config_path, "r") as f:
            rois = json.load(f)
            
        roi_status = rois.get("owned_status")
        if not roi_status:
            print("[LỖI] Chưa huấn luyện Vùng chữ Đã sở hữu (Số 14)!")
            return
            
        while hero_count < max_heroes:
            hero_count += 1
            print(f"\n---> [ĐANG QUÉT TƯỚNG THỨ {hero_count}]")
            
            # Tạo thư mục và data riêng cho Tướng này
            hero_folder_name = f"Tuong_{hero_count:03d}"
            hero_folder_path = os.path.join(self.images_dir, hero_folder_name)
            os.makedirs(hero_folder_path, exist_ok=True)
            
            current_hero_data = {
                "id": hero_count,
                "folder": hero_folder_name,
                "skins": []
            }
            
            # Vào tab Trang phục
            btn_skins_list = glob.glob(os.path.join(self.templates_dir, "btn_skins_tab_*.png"))
            for btn in btn_skins_list:
                if await self._click_template(btn):
                    break
            await asyncio.sleep(0.3)
            
            # Vuốt sang trái (lùi về Mặc định) 5 lần
            print("  -> Đang lướt về skin Mặc định...")
            for _ in range(5):
                await self.adb.swipe(300, 500, 1000, 500, duration_ms=10)
                await asyncio.sleep(0)
                
            # Lặp qua các Skin của tướng này
            seen_skins = set()
            
            while True:
                # Chụp ảnh kiểm tra
                screen = await self.bot.get_screenshot_cv2()
                h_screen, w_screen = screen.shape[:2]
                
                # Kiểm tra Đã sở hữu / Chưa sở hữu bằng phương pháp TÌM ẢNH (Template Matching)
                # Tìm xem có sự xuất hiện của nút MUA hoặc Giá tiền không
                import glob
                unowned_templates = glob.glob(os.path.join(self.templates_dir, "unowned_sign_*.png"))
                
                is_owned = True # Mặc định coi như đã có
                reason = "Không thấy dấu hiệu Chưa Sở Hữu"
                
                for unowned_img in unowned_templates:
                    if self.bot.find_template(screen, unowned_img, threshold=0.75):
                        is_owned = False
                        reason = f"Thấy dấu hiệu Chưa Sở Hữu ({os.path.basename(unowned_img)})"
                        break
                        
                current_skin_name = None
                file_suffix = f"skin_{datetime.now().strftime('%H%M%S')}_{hero_count}_{skin_count+1}"
                
                # Lấy tên tướng và skin để kiểm tra lặp (luôn đọc dù chưa sở hữu)
                roi_names = rois.get("names_region")
                if roi_names:
                    crop_names = screen[roi_names['y']:roi_names['y']+roi_names['h'], 
                                        roi_names['x']:roi_names['x']+roi_names['w']]
                    gray_names = cv2.cvtColor(crop_names, cv2.COLOR_BGR2GRAY)
                    gray_names = cv2.resize(gray_names, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    name_results = self.reader.readtext(gray_names, detail=0)
                    if name_results:
                        raw_name = "_".join(name_results)
                        clean_name = "".join([c if c.isalnum() else "_" for c in raw_name])
                        import re
                        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
                        if clean_name:
                            current_skin_name = clean_name
                            file_suffix = clean_name
                            
                # Kiểm tra nếu tên skin này đã từng xuất hiện (tránh vòng lặp vô hạn hoặc bấm không tác dụng)
                if current_skin_name:
                    if current_skin_name in seen_skins:
                        print("  -> Đã lặp lại skin cũ, đã quét hết skin của tướng này!")
                        break
                    seen_skins.add(current_skin_name)
                
                if is_owned:
                    skin_count += 1
                    self.report_data["total_skins_scanned"] += 1
                    filename = os.path.join(hero_folder_path, f"{file_suffix}.png")
                    print(f"  [+] Đã chụp ảnh Skin thứ {skin_count} -> {hero_folder_name}/{file_suffix}.png")
                    
                    # Hàm phụ để lưu ảnh có tiếng Việt trên Windows
                    def save_img_utf8(path, img):
                        is_success, im_buf_arr = cv2.imencode(".png", img)
                        if is_success:
                            with open(path, "wb") as f:
                                f.write(im_buf_arr.tobytes())

                    # Cắt ảnh mô hình nếu có tọa độ skin_capture_region
                    roi_capture = rois.get("skin_capture_region")
                    if roi_capture:
                        x, y, w, h = roi_capture['x'], roi_capture['y'], roi_capture['w'], roi_capture['h']
                        capture_img = screen[y:y+h, x:x+w]
                        save_img_utf8(filename, capture_img)
                    else:
                        save_img_utf8(filename, screen)
                    
                    # Lưu vào báo cáo
                    current_hero_data["skins"].append({
                        "skin_name": current_skin_name if current_skin_name else file_suffix,
                        "file_path": f"Images/{hero_folder_name}/{file_suffix}.png"
                    })
                else:
                    print(f"  [-] Bỏ qua skin này ({reason})")
                    
                # Bấm thẳng vào ảnh phụ (góc phải) để sang skin tiếp theo
                roi_next = rois.get("next_skin_region")
                if roi_next:
                    tap_x = roi_next['x'] + roi_next['w'] // 2
                    tap_y = roi_next['y'] + roi_next['h'] // 2
                else:
                    tap_x = int(w_screen * 0.85)
                    tap_y = int(h_screen * 0.5)
                    
                await self.adb.tap(tap_x, tap_y)
                await asyncio.sleep(0.5)
                    
            # Lưu Tướng vào Report và Cập nhật file JSON ngay lập tức để Web UI đọc được realtime
            self.report_data["total_heroes_scanned"] += 1
            self.report_data["heroes"].append(current_hero_data)
            
            json_path = os.path.join(self.output_dir, "database.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.report_data, f, ensure_ascii=False, indent=4)
            
            # Chuyển sang tướng tiếp theo
            btn_next_hero = os.path.join(self.templates_dir, "btn_next_hero_1.png")
            if not await self._click_template(btn_next_hero):
                print("[!] Không tìm thấy mũi tên sang tướng tiếp theo, có thể đã hết!")
                break
            await asyncio.sleep(0.8)
            
        # Kết thúc chiến dịch -> Ghi Báo Cáo
        self.report_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.report_data, f, ensure_ascii=False, indent=4)
            
        # 2. Ghi Markdown dễ đọc
        md_path = os.path.join(self.output_dir, "BaoCao_QuetSkin.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# BÁO CÁO KẾT QUẢ QUÉT KHO ĐỒ\n\n")
            f.write(f"- **Thời gian bắt đầu:** {self.report_data['start_time']}\n")
            f.write(f"- **Thời gian kết thúc:** {self.report_data['end_time']}\n")
            f.write(f"- **Tổng số Tướng đã quét:** {self.report_data['total_heroes_scanned']}\n")
            f.write(f"- **Tổng số Skin thu thập:** {self.report_data['total_skins_scanned']}\n\n")
            f.write(f"## Chi tiết từng tướng:\n")
            for h in self.report_data["heroes"]:
                f.write(f"### {h['folder']} (Sở hữu {len(h['skins'])} skin)\n")
                for s in h['skins']:
                    f.write(f"- {s['skin_name']} `({s['file_path']})`\n")
                    
        print("\n=======================================================")
        print(f"HOÀN THÀNH CHIẾN DỊCH! Đã quét {hero_count} tướng và thu thập {self.report_data['total_skins_scanned']} skin.")
        print(f"[1] Ảnh đã được phân loại gọn gàng trong: {self.images_dir}")
        print(f"[2] Data gốc lưu tại: {json_path}")
        print(f"[3] Báo cáo chi tiết xem tại: {md_path}")
        print("=======================================================\n")
        
    async def _click_template(self, template_path):
        if not os.path.exists(template_path):
            return False
        screen = await self.bot.get_screenshot_cv2()
        matches = self.bot.find_template(screen, template_path, threshold=0.75)
        if matches:
            x, y = matches[0]
            await self.adb.tap(x, y)
            return True
        return False
