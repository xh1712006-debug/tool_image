import asyncio
from src.core.adb_controller import ADBController
from src.core.game_bot import GameBot
from src.core.profile_scraper import ProfileScraper

async def test_scraper():
    adb = ADBController()
    bot = GameBot(adb)
    scraper = ProfileScraper(bot)
    
    await scraper.extract_info()

if __name__ == '__main__':
    asyncio.run(test_scraper())
