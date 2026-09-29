import asyncio
import cv2
import numpy as np
import os
from src.core.adb_controller import ADBController

async def main():
    adb = ADBController()
    print("Getting screenshot...")
    img_bytes = await adb.get_screencap_bytes()
    if img_bytes:
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        print("Screen shape:", img.shape)
        cv2.imwrite('screen_debug.png', img)
        print("Saved screen_debug.png")
    else:
        print("Failed to get screenshot.")

if __name__ == '__main__':
    asyncio.run(main())
