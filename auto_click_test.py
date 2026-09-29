import asyncio
import cv2
import numpy as np
from src.core.adb_controller import ADBController

async def main():
    adb = ADBController()
    print("Capturing screen...")
    img_bytes = await adb.get_screencap_bytes()
    if not img_bytes:
        print("Failed to get screenshot.")
        return
        
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    
    # Check top-left for Back arrow (ROI: x 0-250, y 0-150)
    roi = img[0:150, 0:250]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid = [c for c in contours if cv2.contourArea(c) > 30]
    if valid:
        c = max(valid, key=cv2.contourArea)
        M = cv2.moments(c)
        if M['m00'] != 0:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            print(f"FOUND BACK ARROW AT: {cx}, {cy}")
            
            # Draw circle
            cv2.circle(img, (cx, cy), 30, (0, 0, 255), 5)
            cv2.imwrite("click_debug.png", img)
            
            print(f"Clicking at {cx}, {cy}...")
            await adb.tap(cx, cy)
            print("CLICKED!")
            return

    print("BACK ARROW NOT FOUND IN TOP LEFT. Searching for X or Bỏ qua...")
    
    # Try finding Bỏ qua (Skip) button at top right (ROI: x w-400:w, y 0:200)
    roi2 = img[0:200, w-400:w]
    gray2 = cv2.cvtColor(roi2, cv2.COLOR_BGR2GRAY)
    _, thresh2 = cv2.threshold(gray2, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid2 = [c for c in contours if cv2.contourArea(c) > 30]
    if valid2:
        c = max(valid2, key=cv2.contourArea)
        M = cv2.moments(c)
        if M['m00'] != 0:
            cx = int(M['m10']/M['m00']) + w - 400
            cy = int(M['m01']/M['m00'])
            print(f"FOUND BUTTON AT TOP RIGHT: {cx}, {cy}")
            
            cv2.circle(img, (cx, cy), 30, (0, 0, 255), 5)
            cv2.imwrite("click_debug.png", img)
            
            await adb.tap(cx, cy)
            print("CLICKED!")
            return
            
    print("Could not find any clear button.")
    cv2.imwrite("click_debug.png", img)

if __name__ == '__main__':
    asyncio.run(main())
