import asyncio
import os
import random
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)


def find_chrome_executable() -> str:
    """Tìm đường dẫn tệp thực thi Google Chrome trên máy Windows."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        val, _ = winreg.QueryValueEx(key, "")
        if os.path.exists(val):
            return val
    except Exception:
        pass

    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "chrome.exe"


def is_cdp_ready(port: int = 9222) -> bool:
    """Kiểm tra xem cổng CDP của Chrome đã mở và sẵn sàng nhận kết nối hay chưa."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def is_chrome_running() -> bool:
    """Kiểm tra xem Chrome có đang chạy tiến trình trên máy hay không."""
    try:
        res = subprocess.run(["tasklist", "/fi", "imagename eq chrome.exe"], capture_output=True, text=True)
        return "chrome.exe" in res.stdout
    except Exception:
        return False


def ensure_chrome_junction(link_dir: str, src_dir: str):
    """Tạo liên kết thư mục (Junction) để Chrome cho phép mở cổng remote debugging với profile thật."""
    if not os.path.exists(link_dir):
        os.makedirs(os.path.dirname(link_dir), exist_ok=True)
        subprocess.run(f'cmd /c mklink /J "{link_dir}" "{src_dir}"', shell=True, capture_output=True)


def get_chrome_profile_email(profile_name: str = "Default") -> str:
    """Lấy địa chỉ email Google liên kết với Profile Chrome tương ứng."""
    try:
        import json
        local_state_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State")
        if os.path.exists(local_state_path):
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            if profile_name in info_cache:
                return info_cache[profile_name].get("user_name", "")
    except Exception:
        pass
    return ""


class BrowserEngine:
    """Động cơ điều khiển trình duyệt tự động hóa với Google Chrome thật kết hợp chống WAF phát hiện bot."""

    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
    ]

    def __init__(
        self,
        headless: bool = True,
        use_cdp: bool = False,
        cdp_port: int = 9222,
        cdp_profile: str = "Default",
    ):
        self.headless = headless
        self.use_cdp = use_cdp
        self.cdp_port = cdp_port
        self.cdp_profile = cdp_profile
        self.playwright = None
        self.browser: Optional[Browser] = None

    async def start(self):
        """Khởi động Playwright với Google Chrome thật (qua launch hoặc CDP kết nối tài khoản Gmail)."""
        if not self.playwright:
            self.playwright = await async_playwright().start()

        # 1. Chế độ CDP: Sử dụng trực tiếp Google Chrome thật có sẵn tài khoản Gmail của máy
        if self.use_cdp:
            if not is_cdp_ready(self.cdp_port):
                # Nếu Chrome đang chạy thường chưa bật port debug, khởi động lại để kích hoạt cờ CDP
                if is_chrome_running():
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
                    await asyncio.sleep(1.5)

                chrome_exe = find_chrome_executable()
                user_data_src = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                link_dir = os.path.join(PROJECT_ROOT, "storage", "chrome_profile_link")
                ensure_chrome_junction(link_dir, user_data_src)

                cmd = [
                    chrome_exe,
                    f"--remote-debugging-port={self.cdp_port}",
                    f"--user-data-dir={link_dir}",
                    f"--profile-directory={self.cdp_profile}",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--start-maximized",
                ]
                subprocess.Popen(cmd)

                # Chờ Chrome sẵn sàng trên cổng CDP
                for _ in range(15):
                    if is_cdp_ready(self.cdp_port):
                        break
                    await asyncio.sleep(1.0)

            # Kết nối Playwright tới Chrome qua CDP
            self.browser = await self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
            return

        # 2. Chế độ thông thường: Khởi động cửa sổ Chromium/Chrome mới
        try:
            # Sử dụng Google Chrome thật có sẵn trên máy (channel='chrome') và tắt cờ automation
            self.browser = await self.playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--start-maximized",
                ],
                ignore_default_args=["--enable-automation"],
            )
        except Exception:
            # Fallback sang Chromium mặc định nếu không gọi được Chrome
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                ],
                ignore_default_args=["--enable-automation"],
            )

    async def create_stealth_context(self, proxy: Optional[str] = None) -> BrowserContext:
        """Tạo hoặc tái sử dụng Browser Context (khi dùng CDP trả về chính Profile của người dùng)."""
        if not self.browser or not self.browser.is_connected():
            await self.start()

        # Trong chế độ CDP, sử dụng trực tiếp Context chứa toàn bộ cookie & Gmail của người dùng
        if self.use_cdp:
            ctx = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
            try:
                await ctx.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = window.chrome || { runtime: {} };
                """)
            except Exception:
                pass
            return ctx

        proxy_config = None
        if proxy:
            from urllib.parse import urlparse
            parsed = urlparse(proxy)
            if parsed.hostname and parsed.port:
                scheme = parsed.scheme or "http"
                proxy_config = {"server": f"{scheme}://{parsed.hostname}:{parsed.port}"}
                if parsed.username:
                    proxy_config["username"] = parsed.username
                if parsed.password:
                    proxy_config["password"] = parsed.password
            else:
                proxy_config = {"server": proxy}

        # Lưu ý quan trọng: KHÔNG ép buộc User-Agent cũ để tránh lệch với Client Hints (userAgentData)
        # của Chrome thật. Giữ nguyên User-Agent và window.chrome gốc tự nhiên của máy.
        context = await self.browser.new_context(
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            proxy=proxy_config,
            no_viewport=True,
        )

        return context

    async def type_human_like(
        self,
        page: Page,
        selector: str,
        text: str,
        min_delay_ms: int = 60,
        max_delay_ms: int = 140,
    ):
        """Mô phỏng thao tác gõ phím của con người với độ trễ ngẫu nhiên giữa các ký tự."""
        await page.wait_for_selector(selector, state="visible", timeout=10000)
        await page.click(selector)
        await page.fill(selector, "")

        for char in text:
            await page.type(selector, char, delay=random.randint(min_delay_ms, max_delay_ms))
            if random.random() < 0.02:
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def register_account(
        self,
        context: BrowserContext,
        profile: Dict[str, Any],
        username: str,
        password: str,
        email: str,
        otp_fetcher: Callable[[], Any],
    ) -> bool:
        """Thực hiện chu trình điền form đăng ký tự động trên web game."""
        page = await context.new_page()
        try:
            url = profile["register_url"]
            selectors = profile.get("selectors", {})

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(1.0, 2.0))

            inputs = await page.query_selector_all("input")
            if len(inputs) >= 4:
                await inputs[0].fill(username)
                await inputs[1].fill(password)
                await inputs[2].fill(password)
                await inputs[3].fill(email)
            else:
                if "username_input" in selectors:
                    await self.type_human_like(page, selectors["username_input"], username)
                if "password_input" in selectors:
                    await self.type_human_like(page, selectors["password_input"], password)
                if "repassword_input" in selectors and selectors["repassword_input"]:
                    await self.type_human_like(page, selectors["repassword_input"], password)
                if "email_input" in selectors:
                    await self.type_human_like(page, selectors["email_input"], email)

            # Chọn quốc gia VN nếu có
            try:
                select_elem = await page.query_selector("div.field select, form select, select")
                if select_elem:
                    await page.select_option("div.field select, form select, select", value="VN")
            except Exception:
                pass

            if "send_otp_btn" in selectors and selectors["send_otp_btn"]:
                await page.click(selectors["send_otp_btn"])
                await asyncio.sleep(1.0)

            if "otp_input" in selectors and selectors["otp_input"]:
                otp_code = await otp_fetcher()
                await self.type_human_like(page, selectors["otp_input"], str(otp_code))

            if "submit_btn" in selectors:
                await asyncio.sleep(random.uniform(1.0, 2.0))
                await page.click(selectors["submit_btn"])
                await asyncio.sleep(3.0)

            return True

        finally:
            await page.close()

    async def close(self):
        """Đóng Browser và giải phóng tài nguyên Playwright một cách an toàn."""
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
