import asyncio
from src.core.adb_controller import ADBController
from src.core.game_bot import GameBot

async def test_bot():
    adb = ADBController()
    bot = GameBot(adb)
    
    print("\n--- TEST: DỌN DẸP MÀN HÌNH ---")
    print("Bắt đầu khởi chạy Bot quét và dọn dẹp popup...")
    success = await bot.close_all_popups(max_attempts=15)
    
    if success:
        print("\n=> [TUYỆT VỜI] Màn hình đã hoàn toàn sạch sẽ, đang ở trang chủ!")
        print("Sẵn sàng cho bước tiếp theo: THU THẬP THÔNG TIN TÀI KHOẢN.")
    else:
        print("\n=> [CẢNH BÁO] Vẫn còn popup chưa tắt được hoặc quá số lần thử.")

if __name__ == '__main__':
    asyncio.run(test_bot())
