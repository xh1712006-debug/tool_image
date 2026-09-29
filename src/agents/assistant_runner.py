import asyncio
import os
import random
from typing import Dict, Any, Optional

from rich.console import Console
from playwright.async_api import BrowserContext, Page

from src.utils.account_gen import AccountItem
from src.browser.browser_engine import BrowserEngine
from src.network.proxy_manager import ProxyManager
from src.services.temp_mail_service import MailTmService
from src.services.temp_mail_web import TempMailWebClient
from src.storage.sqlite_repo import SqliteRepository
from src.storage.txt_exporter import TxtExporter

import sys

# Đảm bảo UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(highlight=False)


class AssistantRunner:
    """Bộ trợ lý điền form bán tự động (Human-in-the-loop) với 2 Tab song song,
    cơ chế mỗi tài khoản 1 IP khác nhau và tự động đổi IP mới khi gặp sự cố."""

    def __init__(
        self,
        browser_engine: BrowserEngine,
        proxy_manager: ProxyManager,
        sqlite_repo: SqliteRepository,
        txt_exporter: TxtExporter,
        use_proxy: bool = True,
        max_retries_per_account: int = 3,
        mail_provider: str = "auto",
    ):
        self.browser_engine = browser_engine
        self.proxy_manager = proxy_manager
        self.sqlite_repo = sqlite_repo
        self.txt_exporter = txt_exporter
        self.use_proxy = use_proxy
        self.max_retries_per_account = max_retries_per_account
        self.mail_provider = mail_provider

    @staticmethod
    async def _human_type(page: Page, element, text: str, field_name: str = ""):
        """Gõ phím mô phỏng người thật với khoảng cách ngẫu nhiên giữa các ký tự."""
        try:
            box = await element.bounding_box()
            if box:
                await page.mouse.move(
                    box["x"] + box["width"] / 2 + random.uniform(-10, 10),
                    box["y"] + box["height"] / 2 + random.uniform(-5, 5),
                    steps=random.randint(5, 10),
                )
                await asyncio.sleep(random.uniform(0.1, 0.25))
        except Exception:
            pass

        await element.click()
        await page.wait_for_timeout(random.randint(150, 300))
        await element.fill("")
        await page.wait_for_timeout(random.randint(80, 150))

        for char in text:
            await element.type(char, delay=random.randint(60, 130))
            if random.random() < 0.03:
                await asyncio.sleep(random.uniform(0.1, 0.25))

        console.print(f"  • Đã điền {field_name}: [cyan]{text}[/cyan]")
        await asyncio.sleep(random.uniform(0.5, 1.0))

    @classmethod
    async def is_datadome_hard_banned(cls, page: Page) -> tuple[bool, str]:
        """Chỉ trả về True khi IP THỰC SỰ BỊ CẤM / CHẶN TRUY CẬP (toàn màn hình bị chặn, không có slider captcha để kéo)."""
        try:
            # Nếu đang có thanh trượt Captcha ghép hình hiển thị thì KHÔNG PHẢI là cấm IP
            if await cls.is_slider_captcha_visible(page):
                return False, ""

            ban_keywords = [
                "truy cập tạm thời bị hạn chế",
                "robot trên cùng mạng",
                "điều gì đó về hành vi của trình duyệt đã thu hút sự chú ý",
                "access temporarily restricted",
                "access denied",
            ]

            # Chỉ quét nội dung text trên trang chính (main frame)
            main_text = (await page.main_frame.inner_text("body") or "").lower()
            for kw in ban_keywords:
                if kw in main_text:
                    return True, f"Garena cấm IP ({kw})"

        except Exception:
            pass
        return False, ""

    @staticmethod
    async def is_slider_captcha_visible(page: Page) -> bool:
        """Kiểm tra xem thanh trượt Captcha ghép hình của Garena / DataDome có đang hiển thị không."""
        try:
            selectors = [
                "div:has-text('Trượt sang phải')",
                "div:has-text('bảo vệ quyền truy cập')",
                "div:has-text('Slide right')",
                "div[id*='ddChallengeContainer']",
                "iframe[id*='ddChallengeBody']",
                "iframe[src*='captcha-delivery.com']",
                "iframe[src*='geo.captcha-delivery.com']",
                "iframe[title*='Verification system']",
                "#captcha-box",
                ".geetest_popup_wrap",
                ".slider-track",
                ".slider-btn",
                "div[role='dialog']",
            ]
            for sel in selectors:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return True
        except Exception:
            pass
        return False

    async def run_login_demo(
        self,
        account: AccountItem,
        demo_url: str = "http://127.0.0.1:8765/login",
    ) -> bool:
        """Thực thi luồng đăng nhập vào trang demo."""
        current_proxy = self.proxy_manager.get_current_proxy() if self.use_proxy else None
        retry_count = 0

        while retry_count < self.max_retries_per_account:
            retry_count += 1
            if current_proxy:
                console.print(f"[bold cyan][*] Kết nối IP riêng cho {account.username} (Lần {retry_count}):[/bold cyan] [yellow]{current_proxy}[/yellow]")
            else:
                console.print(f"[dim][*] Kết nối mạng trực tiếp cho {account.username} (Lần {retry_count})...[/dim]")

            context: Optional[BrowserContext] = None
            page_game: Optional[Page] = None
            try:
                # 1. Tạo BrowserContext ngụy trang
                context = await self.browser_engine.create_stealth_context(proxy=current_proxy)

                # 2. Mở trang đăng nhập demo
                console.print(f"[cyan][*] Bước 1: Mở trang đăng nhập ({demo_url})...[/cyan]")
                page_game = await context.new_page()
                await page_game.bring_to_front()
                try:
                    await page_game.goto(demo_url, wait_until="domcontentloaded", timeout=40000)
                except Exception as net_err:
                    console.print(f"[yellow][!] Lỗi tải trang qua IP {current_proxy}: {net_err}[/yellow]")
                    raise ConnectionError("Proxy timeout hoặc không kết nối được tới trang.")

                await asyncio.sleep(1.0)

                # 3. Điền thông tin vào form đăng nhập
                await page_game.wait_for_selector("input", timeout=15000)
                inputs = await page_game.query_selector_all("input")

                if len(inputs) >= 2:
                    console.print("[dim]Bắt đầu điền thông tin đăng nhập...[/dim]")
                    # Tên đăng nhập
                    await self._human_type(page_game, inputs[0], account.username, "Tên đăng nhập")
                    # Mật khẩu
                    await self._human_type(page_game, inputs[1], account.password, "Mật khẩu")

                # 4. Bấm nút Đăng Nhập
                submit_btn = await page_game.query_selector("button.btn-submit, button[type='submit']")
                if submit_btn and await submit_btn.is_visible():
                    console.print("[bold cyan][*] Đang bấm nút Đăng Nhập...[/bold cyan]")
                    try:
                        box = await submit_btn.bounding_box()
                        if box:
                            await page_game.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2, steps=8)
                    except Exception:
                        pass
                    await submit_btn.click()
                    await asyncio.sleep(2.0)

                # 5. Kiểm tra đăng nhập thành công
                success_alert = await page_game.query_selector("#success-alert")
                is_success = False
                if success_alert:
                    style = await success_alert.get_attribute("style") or ""
                    if "display: block" in style:
                        is_success = True

                if is_success:
                    if self.use_proxy:
                        self.proxy_manager.record_success()

                    console.print(f"\n[bold green][+] HOÀN TẤT ĐĂNG NHẬP:[/bold green] [cyan]{account.username}[/cyan]")
                    await asyncio.sleep(1.0)
                    return True
                else:
                    raise RuntimeError("Đã điền nhưng chưa thấy thông báo đăng nhập thành công")

            except (ConnectionError, PermissionError, Exception) as exc:
                console.print(f"[bold red][!] Gặp sự cố với {account.username}:[/bold red] {exc}")
                console.print("[dim]Tạm nghỉ 2 giây trước khi thử lại...[/dim]")
                await asyncio.sleep(2.0)
                if retry_count < self.max_retries_per_account and self.use_proxy:
                    console.print("[yellow][*] Đang tự động đổi sang IP mới để thử lại...[/yellow]")
                    current_proxy = await self.proxy_manager.mark_bad_and_get_replacement(current_proxy)
                    await asyncio.sleep(1.0)
                else:
                    if retry_count >= self.max_retries_per_account:
                        console.print(f"[red][X] Đã hết số lần thử lại cho tài khoản {account.username}.[/red]")
                    break

            finally:
                if getattr(self.browser_engine, "use_cdp", False):
                    if page_game:
                        try:
                            await page_game.close()
                        except Exception:
                            pass
                else:
                    if context:
                        try:
                            await context.close()
                        except Exception:
                            pass

        return False

    async def run_adb_login_game(self, username: str, password: str) -> bool:
        """Đăng nhập trực tiếp vào Game trên Điện thoại thông qua cáp Type-C (ADB)"""
        from src.core.adb_controller import ADBController
        from src.core.game_bot import GameBot
        adb = ADBController()
        bot = GameBot(adb)
        
        devices = await adb.get_devices()
        if not devices:
            console.print("[red][!] Không tìm thấy điện thoại nào! Vui lòng cắm cáp Type-C và bật Gỡ Lỗi USB (USB Debugging).[/red]")
            return False
            
        console.print(f"[cyan][*] Đã kết nối với điện thoại: {devices[0]}[/cyan]")
        
        # Bật màn hình hiển thị điện thoại lên PC cho người dùng thấy
        console.print("[cyan][*] Đang mở màn hình phản chiếu điện thoại (Scrcpy)...[/cyan]")
        adb.start_screen_mirror()
        await asyncio.sleep(2.0) # Đợi cửa sổ hiện lên
        
        # Tự động dọn dẹp các popup, sự kiện, thông báo...
        console.print("[cyan][*] [TỰ ĐỘNG] Đang kích hoạt MẮT THẦN (Computer Vision) để dọn dẹp màn hình...[/cyan]")
        await bot.close_all_popups(max_attempts=15)
        
        console.print(f"[cyan][*] Đang điều khiển điện thoại nhập tài khoản: {username}...[/cyan]")
        
        try:
            # TODO: Cần người dùng thay đổi tọa độ (X, Y) này cho khớp với màn hình điện thoại của họ!
            # 1. Chạm vào ô User (ví dụ: X=500, Y=600)
            await adb.tap(500, 600)
            await asyncio.sleep(1.0)
            await adb.type_text(username)
            await asyncio.sleep(1.0)
            
            # 2. Chạm vào ô Mật khẩu (ví dụ: X=500, Y=800)
            await adb.tap(500, 800)
            await asyncio.sleep(1.0)
            await adb.type_text(password)
            await asyncio.sleep(1.0)
            
            # 3. Chạm vào nút Đăng Nhập (ví dụ: X=500, Y=1000)
            await adb.tap(500, 1000)
            
            console.print("[bold green][+] Đã điều khiển điện thoại nhập xong Tài khoản & Mật khẩu![/bold green]")
            return True
        except Exception as e:
            console.print(f"[red][!] Lỗi điều khiển ADB: {e}[/red]")
            return False

    async def run_login_garena(
        self,
        username: str,
        password: str,
    ) -> bool:
        """Đăng nhập Garena bằng tài khoản cung cấp."""
        current_proxy = self.proxy_manager.get_current_proxy() if self.use_proxy else None
        
        console.print(f"[cyan][*] Bắt đầu đăng nhập vào Garena cho: {username}[/cyan]")
        context = None
        page_game = None
        try:
            context = await self.browser_engine.create_stealth_context(proxy=current_proxy)
            page_game = await context.new_page()
            await page_game.bring_to_front()
            
            login_url = "https://sso.garena.com/ui/login"
            await page_game.goto(login_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(2.0)
            
            inputs = await page_game.query_selector_all("input")
            if len(inputs) >= 2:
                console.print("[dim]Đang nhập tài khoản và mật khẩu...[/dim]")
                await self._human_type(page_game, inputs[0], username, "Tài khoản")
                await self._human_type(page_game, inputs[1], password, "Mật khẩu")
            
            submit_btn = await page_game.query_selector("button.btn-login, button[type='submit'], .btn-login")
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click()
            
            console.print("[bold green][+] Đã điền form đăng nhập xong! Bạn hãy kéo Captcha nếu có nhé.[/bold green]")
            # Chờ người dùng tự tương tác và đóng tab hoặc để nguyên
            for _ in range(60):
                if page_game.is_closed():
                    break
                await asyncio.sleep(1.0)
                
            return True
        except Exception as e:
            console.print(f"[red][!] Lỗi khi đăng nhập Garena: {e}[/red]")
            return False
        finally:
            if getattr(self.browser_engine, "use_cdp", False):
                if page_game:
                    try: await page_game.close()
                    except: pass
            else:
                if context:
                    try: await context.close()
                    except: pass

    async def run_account_lifecycle(
        self,
        account: AccountItem,
        profile: Dict[str, Any],
        run_id: int,
    ) -> bool:
        """Thực thi toàn bộ chu trình đăng ký cho 1 tài khoản với IP riêng biệt,
        tự động xoay IP khác nếu gặp lỗi chặn hoặc lỗi proxy."""
        game_url = profile.get("register_url", "https://sso.garena.com/universal/register")
        retry_count = 0

        # Lấy IP ban đầu cho tài khoản này
        current_proxy = None
        if self.use_proxy:
            current_proxy = await self.proxy_manager.get_next_proxy_for_account()

        while retry_count < self.max_retries_per_account:
            retry_count += 1
            if current_proxy:
                console.print(f"[bold cyan][*] Khoi tao IP rieng cho {account.username} (Lan {retry_count}):[/bold cyan] [yellow]{current_proxy}[/yellow]")
            else:
                console.print(f"[dim][*] Ket noi mang truc tiep cho {account.username} (Lan {retry_count})...[/dim]")

            context: Optional[BrowserContext] = None
            mail_service: Optional[MailTmService] = None
            page_mail: Optional[Page] = None
            page_game: Optional[Page] = None
            try:
                # 1. Tạo BrowserContext ngụy trang mới hoàn toàn cho tài khoản này
                context = await self.browser_engine.create_stealth_context(proxy=current_proxy)

                # 2. BƯỚC 1: Lấy email ảo (Mở Tab 1 hiển thị trực quan)
                email = None
                if self.mail_provider == "mailtm":
                    console.print("[cyan][*] Bước 1: Khởi tạo hòm thư ảo qua Mail.tm API...[/cyan]")
                    mail_service = MailTmService()
                    email = await mail_service.create_inbox()
                    console.print(f"[bold green][+] Đã tạo Email ảo thành công qua API:[/bold green] [cyan]{email}[/cyan]")
                else:
                    console.print(f"[cyan][*] Bước 1: Mở Tab 1 ({TempMailWebClient.URL}) để lấy email ảo...[/cyan]")
                    page_mail = await context.new_page()
                    try:
                        await page_mail.goto(TempMailWebClient.URL, wait_until="domcontentloaded", timeout=35000)
                        console.print("[yellow][*] Đang chờ lấy địa chỉ email từ giao diện web...[/yellow]")
                        email = await TempMailWebClient.get_email_from_page(page_mail, timeout_sec=30)
                    except Exception as tm_err:
                        console.print(f"[yellow][!] Lỗi lấy email từ web: {tm_err}[/yellow]")
                        raise ValueError(f"Bước 1 thất bại: Không lấy được email từ trang web: {tm_err}")

                if not email or "@" not in email:
                    raise ValueError("Không thể tạo được email ảo hợp lệ.")

                console.print(f"[bold green][+] Đã lấy được Email thành công:[/bold green] [cyan]{email}[/cyan]")

                # 3. BƯỚC 2: Mở Tab 2 (Garena SSO) để điền thông tin đăng ký
                console.print(f"[cyan][*] Bước 2: Mở Tab 2 ({game_url}) để đăng ký...[/cyan]")
                page_game = await context.new_page()
                await page_game.bring_to_front()
                try:
                    await page_game.goto(game_url, wait_until="domcontentloaded", timeout=40000)
                except Exception as net_err:
                    console.print(f"[yellow][!] Lỗi tải trang Garena qua IP {current_proxy}: {net_err}[/yellow]")
                    raise ConnectionError("Proxy timeout hoặc không kết nối được tới Garena")

                await asyncio.sleep(2.0)

                # 4. Kiểm tra xem có bị CẤM TRUY CẬP (Hard Ban) ngay khi tải trang không
                banned, reason = await self.is_datadome_hard_banned(page_game)
                if banned:
                    console.print(f"\n[bold red]╔══════════════════════════════════════════════════════════════════════════╗[/bold red]")
                    console.print(f"[bold red]║ [X] GARENA ĐÃ CHẶN IP NÀY NGAY KHI VÀO TRANG!                           ║[/bold red]")
                    console.print(f"[bold red]║ Chi tiết: {reason:<63}║[/bold red]")
                    console.print(f"[bold red]╚══════════════════════════════════════════════════════════════════════════╝[/bold red]")
                    raise PermissionError(f"IP bi Garena chan: {reason}")

                # 5. Điền thông tin vào form Garena
                await page_game.wait_for_selector("input", timeout=15000)
                inputs = await page_game.query_selector_all("input")

                if len(inputs) >= 4:
                    console.print("[dim]Bắt đầu nhập liệu chậm rãi mô phỏng người thật...[/dim]")
                    # Ô 0: Tên đăng nhập
                    await self._human_type(page_game, inputs[0], account.username, "Tên đăng nhập")

                    # Ô 1: Mật khẩu
                    await self._human_type(page_game, inputs[1], account.password, "Mật khẩu")

                    # Ô 2: Nhập lại mật khẩu
                    await self._human_type(page_game, inputs[2], account.password, "Nhập lại mật khẩu")

                    # Ô 3: Email
                    await self._human_type(page_game, inputs[3], email, "Email")

                # 6. Chọn Quốc gia: Việt Nam (dùng selector chuẩn xác select:not(.lang))
                try:
                    await page_game.wait_for_selector("select:not(.lang)", timeout=6000)
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                    await page_game.select_option("select:not(.lang)", value="VN")
                    console.print("  [+] Đã chọn Quốc gia: [bold green]Việt Nam (Viet Nam)[/bold green]")
                    await asyncio.sleep(0.8)
                except Exception as sel_err:
                    console.print(f"[dim]Không chọn được dropdown quốc gia: {sel_err}[/dim]")

                # 7. HIỂN THỊ HƯỚNG DẪN TRỢ LÝ ĐỂ NGƯỜI DÙNG CLICK BẰNG CHUỘT THẬT (TRÁNH BỊ DATADOME BẮT LỖI CDP CLICK)
                console.print(f"\n[bold yellow]╔══════════════════════════════════════════════════════════════════════════════════╗[/bold yellow]")
                console.print(f"[bold yellow]║ [!] TOOL ĐÃ ĐIỀN XONG 100% THÔNG TIN VÀO FORM GARENA CHO BẠN!                    ║[/bold yellow]")
                console.print(f"[bold yellow]║                                                                                  ║[/bold yellow]")
                console.print(f"[bold yellow]║  👉 BƯỚC 1: BẠN DÙNG CHUỘT THẬT CLICK VÀO NÚT 'Register Now' (Đăng ký ngay)      ║[/bold yellow]")
                console.print(f"[bold yellow]║  👉 BƯỚC 2: CLICK NÚT 'GET CODE' VỪA HIỆN RA VÀ KÉO THANH TRƯỢT CAPTCHA          ║[/bold yellow]")
                console.print(f"[bold yellow]║                                                                                  ║[/bold yellow]")
                console.print(f"[bold yellow]║ (Chuột thật của bạn click sẽ KHÔNG BAO GIỜ bị DataDome báo 'robot trên mạng'!)  ║[/bold yellow]")
                console.print(f"[bold yellow]║ Kéo Captcha xong, Garena gửi mã về -> Tool sẽ TỰ ĐỘNG lấy OTP và điền nốt cho bạn!║[/bold yellow]")
                console.print(f"[bold yellow]╚══════════════════════════════════════════════════════════════════════════════════╝[/bold yellow]")

                await page_game.bring_to_front()

                # Tool theo dõi: Chờ người dùng click Register Now hoặc GET CODE
                get_code_selectors = [
                    "button.secondary",
                    "button:has-text('GET CODE')",
                    "button:has-text('Get code')",
                    "button:has-text('Send code')",
                    "button:has-text('Send Code')",
                    "button:has-text('Gửi mã')",
                    "button:has-text('Lấy mã')",
                    ".btn-get-code",
                    ".btn-send-code",
                ]

                # Nếu sau 6 giây người dùng chưa bấm Register Now, tool sẽ hỗ trợ bấm nhẹ nhàng
                reg_clicked_by_user = False
                for _ in range(6):
                    if page_game.is_closed():
                        break
                    # Kiểm tra xem ô Verification Code hoặc nút GET CODE đã xuất hiện chưa
                    for sel in get_code_selectors:
                        btn = await page_game.query_selector(sel)
                        if btn and await btn.is_visible():
                            reg_clicked_by_user = True
                            break
                    if reg_clicked_by_user:
                        break
                    await asyncio.sleep(1.0)

                # Nếu người dùng chưa bấm sau 6 giây, tool hỗ trợ bấm Register Now lần 1
                if not reg_clicked_by_user:
                    submit_btn = await page_game.query_selector(
                        "button.primary, button:has-text('Register Now'), button:has-text('Đăng ký ngay'), button[type='submit']"
                    )
                    if submit_btn and await submit_btn.is_visible():
                        console.print("[dim]Hỗ trợ bấm nút 'Register Now' để mở ô nhập mã...[/dim]")
                        try:
                            box = await submit_btn.bounding_box()
                            if box:
                                await page_game.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2, steps=10)
                                await asyncio.sleep(0.4)
                        except Exception:
                            pass
                        await submit_btn.click()
                        await asyncio.sleep(2.0)

                # Kiểm tra hard ban
                banned, reason = await self.is_datadome_hard_banned(page_game)
                if banned:
                    console.print(f"\n[bold red]╔══════════════════════════════════════════════════════════════════════════╗[/bold red]")
                    console.print(f"[bold red]║ [X] GARENA ĐÃ CHẶN TRUY CẬP!                                             ║[/bold red]")
                    console.print(f"[bold red]║ Chi tiết: {reason:<63}║[/bold red]")
                    console.print(f"[bold red]╚══════════════════════════════════════════════════════════════════════════╝[/bold red]")
                    raise PermissionError(f"Garena chan IP: {reason}")

                # 8. THEO DÕI NÚT 'GET CODE' VÀ BƯỚC KÉO CAPTCHA
                console.print("[cyan][*] Đang chờ bạn bấm 'GET CODE' và kéo thanh trượt Captcha...[/cyan]")
                captcha_solved = False
                for sec in range(90):
                    if page_game.is_closed():
                        break
                    await asyncio.sleep(1.0)

                    # Kiểm tra hard ban
                    banned, reason = await self.is_datadome_hard_banned(page_game)
                    if banned:
                        raise PermissionError(f"Garena chan IP: {reason}")

                    # Dấu hiệu duy nhất và chắc chắn 100%: Nút GET CODE chuyển sang đếm ngược (vd: '60s', '59s', 'Resend' hoặc bị disabled)
                    for sel in get_code_selectors:
                        btn = await page_game.query_selector(sel)
                        if btn:
                            txt = (await btn.inner_text() or "").strip()
                            is_dis = await btn.is_disabled()
                            # Khi kéo Captcha thành công, nút GET CODE sẽ đổi thành đếm giây (vd '60s', '59s') hoặc mờ đi (disabled)
                            if any(c.isdigit() for c in txt) or is_dis or "resend" in txt.lower() or "đã gửi" in txt.lower():
                                captcha_solved = True
                                break

                    if captcha_solved:
                        break

                if captcha_solved:
                    console.print("[bold green][+] Garena đã xác thực Captcha thành công và bắt đầu gửi mã OTP! Chờ 4 giây...[/bold green]")
                    await asyncio.sleep(4.0)
                else:
                    console.print("[yellow][!] Chưa thấy Garena đếm ngược gửi mã (có thể bạn chưa kéo khớp Captcha). Thử kiểm tra hòm thư...[/yellow]")

                # 10. LẤY MÃ OTP TỪ HÒM THƯ (TAB 1 HOẶC API)
                otp_code = None
                if page_mail and not page_mail.is_closed():
                    console.print("[cyan][*] Bước 5: Chuyển sang Tab 1 để lấy mã OTP gửi về hòm thư...[/cyan]")
                    try:
                        await page_mail.bring_to_front()
                        otp_code = await TempMailWebClient.wait_for_otp_from_inbox(page_mail, timeout_sec=65)
                        console.print(f"[bold green][+] Bóc tách thành công mã OTP:[/bold green] [magenta]{otp_code}[/magenta]")
                    except Exception as otp_err:
                        console.print(f"[yellow][!] Chưa nhận được mã OTP: {otp_err}[/yellow]")
                elif mail_service:
                    console.print("[cyan][*] Bước 5: Đang theo dõi hòm thư Mail.tm trong nền để nhận mã OTP...[/cyan]")
                    try:
                        otp_code = await mail_service.wait_for_otp(timeout_sec=65)
                        console.print(f"[bold green][+] Bóc tách thành công mã OTP:[/bold green] [magenta]{otp_code}[/magenta]")
                    except Exception as otp_err:
                        console.print(f"[yellow][!] Chưa nhận được mã OTP từ Mail.tm: {otp_err}[/yellow]")

                # 11. QUAY LẠI TAB 2 (GARENA) ĐỂ ĐIỀN OTP VÀ HOÀN TẤT
                console.print("[cyan][*] Bước 6: Quay lại Tab 2 (Garena) để điền mã OTP và hoàn tất...[/cyan]")
                if not page_game.is_closed():
                    await page_game.bring_to_front()
                    if otp_code:
                        console.print(f"[bold cyan][*] Đang điền mã OTP ({otp_code}) vào ô Verification Code...[/bold cyan]")
                        otp_field = await page_game.query_selector("input[placeholder*='Verification'], input[type='tel'], input[placeholder*='Code']")
                        if otp_field:
                            await self._human_type(page_game, otp_field, otp_code, "Mã OTP")
                        else:
                            all_inps = await page_game.query_selector_all("input")
                            if len(all_inps) >= 5:
                                await self._human_type(page_game, all_inps[4], otp_code, "Mã OTP")

                        await asyncio.sleep(1.0)
                        # Bấm nút Register Now lần 2 để hoàn tất đăng ký
                        reg_final_btn = await page_game.query_selector("button.primary, button:has-text('Register Now'), button[type='submit']")
                        if reg_final_btn and await reg_final_btn.is_visible():
                            console.print("[bold cyan][*] Đang bấm nút 'Register Now' để hoàn tất tài khoản...[/bold cyan]")
                            try:
                                box = await reg_final_btn.bounding_box()
                                if box:
                                    await page_game.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2, steps=8)
                            except Exception:
                                pass
                            await reg_final_btn.click()
                            await asyncio.sleep(4.0)

                # Kiểm tra đăng ký thành công
                current_url = page_game.url
                body_text = await page_game.inner_text("body")
                if "success" in current_url.lower() or "login" in current_url.lower() or "thành công" in body_text.lower():
                    self.txt_exporter.append_account(
                        username=account.username,
                        password=account.password,
                        email=email,
                        game_name=account.game_name,
                        status="SUCCESS",
                    )
                    self.sqlite_repo.save_account(
                        run_id=run_id,
                        sequence_number=account.sequence_number,
                        username=account.username,
                        password=account.password,
                        email=email,
                        game_name=account.game_name,
                        status="SUCCESS",
                        proxy_address=current_proxy,
                    )
                    if self.use_proxy:
                        self.proxy_manager.record_success()

                    console.print(f"\n[bold green][+] HOÀN TẤT TÀI KHOẢN:[/bold green] [cyan]{account.username}[/cyan] -> Đã lưu vào file .txt")
                    await asyncio.sleep(2.0)
                    return True
                else:
                    if not otp_code:
                        raise TimeoutError("Không nhận được mã OTP từ hòm thư Temp-mail")
                    raise RuntimeError("Đã điền mã nhưng chưa phát hiện trang hoàn tất")

            except (ConnectionError, PermissionError, Exception) as exc:
                console.print(f"[bold red][!] Gặp sự cố với {account.username}:[/bold red] {exc}")
                console.print("[dim]Tạm nghỉ 3 giây trước khi chuyển lượt...[/dim]")
                await asyncio.sleep(3.0)
                if retry_count < self.max_retries_per_account and self.use_proxy:
                    console.print("[yellow][*] Đang tự động đổi sang IP mới để thử lại...[/yellow]")
                    current_proxy = await self.proxy_manager.mark_bad_and_get_replacement(current_proxy)
                    await asyncio.sleep(2.0)
                else:
                    if retry_count >= self.max_retries_per_account:
                        console.print(f"[red][X] Đã hết số lần thử lại cho tài khoản {account.username}.[/red]")
                    break

            finally:
                # Đảm bảo đóng hòm thư và dọn dẹp tab/context sạch sẽ trước khi sang tài khoản hoặc IP mới
                if mail_service:
                    try:
                        await mail_service.close()
                    except Exception:
                        pass

                if getattr(self.browser_engine, "use_cdp", False):
                    # Trong chế độ CDP Google Chrome thật: chỉ đóng các Tab của lượt chạy này
                    if page_mail:
                        try:
                            await page_mail.close()
                        except Exception:
                            pass
                    if page_game:
                        try:
                            await page_game.close()
                        except Exception:
                            pass
                else:
                    if context:
                        try:
                            await context.close()
                        except Exception:
                            pass

        return False
