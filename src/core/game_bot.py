import cv2
import numpy as np
import time
import os
import asyncio
from typing import List, Tuple
from src.core.adb_controller import ADBController

class GameBot:
    def __init__(self, adb: ADBController):
        self.adb = adb
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)

    async def get_screenshot_cv2(self) -> np.ndarray:
        """Lấy ảnh màn hình hiện tại dưới dạng numpy array (Bảng màu BGR của OpenCV)"""
        image_bytes = await self.adb.get_screencap_bytes()
        if not image_bytes:
            return None
        # Chuyển bytes thành mảng numpy
        nparr = np.frombuffer(image_bytes, np.uint8)
        # Giải mã ảnh
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def find_template(self, screen_img: np.ndarray, template_path: str, threshold: float = 0.8) -> list:
        """Tìm tất cả các vị trí khớp với template trên màn hình"""
        if not os.path.exists(template_path):
            return []
            
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            return []

        h, w = template.shape[:2]
        
        # Áp dụng template matching
        res = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        
        matches = []
        for pt in zip(*loc[::-1]):
            # pt là (x, y) góc trên cùng bên trái
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            matches.append((center_x, center_y))
            
        if len(matches) > 1000:
            print(f"  -> [CẢNH BÁO] Ảnh mẫu '{os.path.basename(template_path)}' khớp tới {len(matches)} điểm! Có thể bạn đã khoanh một vùng quá đơn sắc (đen thui/trắng bóc). Đang tự động bỏ qua để tránh treo máy.")
            return []
            
        # Lọc các điểm trùng lặp (nếu template match nhiều pixel gần nhau)
        filtered_matches = []
        for match in matches:
            is_duplicate = False
            for f_match in filtered_matches:
                if abs(match[0] - f_match[0]) < w and abs(match[1] - f_match[1]) < h:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_matches.append(match)
                
        return filtered_matches

    async def close_all_popups(self, max_attempts: int = 15, threshold: float = 0.8) -> bool:
        """
        Quét và đóng toàn bộ các cửa sổ popup bằng cách tìm dấu X, nút 'Bỏ qua', hoặc 'Quay lại'.
        Lặp lại liên tục cho đến khi không còn dấu hiệu nào hoặc đạt max_attempts.
        """
        print("Đang kiểm tra và đóng các popup / Bỏ qua / Quay lại...")
        
        # Lấy danh sách các mẫu dấu X (close_x_*.png), nút Bỏ qua (skip_*.png) và Mũi tên (back_*.png)
        template_files = [f for f in os.listdir(self.templates_dir) if (f.startswith("close") or f.startswith("skip") or f.startswith("back")) and f.endswith(".png")]
        
        if not template_files:
            print(f"Chưa có mẫu nhận diện nào trong thư mục: {self.templates_dir}")
            print("Vui lòng lưu các mẫu: nút X (close_x_1.png), Bỏ qua (skip_1.png), Quay lại (back_1.png) vào thư mục 'templates'")
            return False

        attempts = 0
        while attempts < max_attempts:
            screen_img = await self.get_screenshot_cv2()
            if screen_img is None:
                print("Lỗi không lấy được ảnh màn hình!")
                break
                
            found_any = False
            
            for template_name in template_files:
                template_path = os.path.join(self.templates_dir, template_name)
                matches = self.find_template(screen_img, template_path, threshold)
                
                if matches:
                    found_any = True
                    for (x, y) in matches:
                        print(f"Phát hiện mẫu '{template_name}' tại ({x}, {y}). Tiến hành click...")
                        await self.adb.tap(x, y)
                        await asyncio.sleep(2.0) # Đợi hiệu ứng màn hình hoàn tất
                    
                    # Thoát vòng lặp template để chụp lại ảnh màn hình mới
                    break 
                    
            if not found_any:
                print("Không còn dấu X, Bỏ qua hay Quay lại nào trên màn hình. Đã về trang chủ an toàn.")
                return True
                
            attempts += 1
            
        print("Đã đạt giới hạn số lần thử đóng popup.")
        return False
