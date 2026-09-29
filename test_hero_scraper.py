import asyncio
from src.core.adb_controller import ADBController
from src.core.game_bot import GameBot
from src.core.hero_scraper import HeroScraper

async def test_hero_scraper():
    adb = ADBController()
    bot = GameBot(adb)
    scraper = HeroScraper(bot)
    
    # Tải AI Nhận diện chữ ngay khi vừa bật (Chỉ tải 1 lần)
    scraper._init_ocr()
    print("\n[OK] Đã nạp AI xong! Cỗ máy đã trong trạng thái sạc đầy năng lượng!")
    
    while True:
        # Chờ người dùng ra lệnh để không bị tắt chương trình
        cmd = await asyncio.to_thread(input, "\n👉 [LỆNH] Nhấn phím ENTER để BẮT ĐẦU QUÉT (hoặc gõ 'q' rồi Enter để thoát): ")
        if cmd.strip().lower() == 'q':
            break
            
        await scraper.run_hero_scraping(max_heroes=129, max_skins=218)

if __name__ == '__main__':
    asyncio.run(test_hero_scraper())
