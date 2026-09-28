import asyncio
from typing import Callable, Optional, Dict, Any

from src.utils.account_gen import AccountItem
from src.browser.browser_engine import BrowserEngine
from src.network.proxy_manager import ProxyManager
from src.services.temp_mail_service import BaseTempMailService, MailTmService
from src.storage.sqlite_repo import SqliteRepository
from src.storage.txt_exporter import TxtExporter


class TaskOrchestrator:
    """Bộ điều phối liên kết toàn bộ 5 luồng: Sinh tài khoản, Mail ảo, Trình duyệt, Chống ban và Lưu trữ."""

    def __init__(
        self,
        browser_engine: BrowserEngine,
        mail_service_factory: Callable[[], BaseTempMailService],
        proxy_manager: ProxyManager,
        sqlite_repo: SqliteRepository,
        txt_exporter: TxtExporter,
        max_retries: int = 3,
    ):
        self.browser_engine = browser_engine
        self.mail_service_factory = mail_service_factory
        self.proxy_manager = proxy_manager
        self.sqlite_repo = sqlite_repo
        self.txt_exporter = txt_exporter
        self.max_retries = max_retries

    async def process_account(
        self,
        account: AccountItem,
        profile: Dict[str, Any],
        run_id: int,
        on_status_update: Optional[Callable[[str, str], None]] = None,
    ) -> bool:
        """Thực thi chu trình tạo 1 tài khoản hoàn chỉnh với cơ chế tự động thử lại khi lỗi."""
        retries = 0

        while retries < self.max_retries:
            retries += 1
            proxy = self.proxy_manager.get_current_proxy()
            mail_service = self.mail_service_factory()

            try:
                if on_status_update:
                    on_status_update(account.username, f"Đang tạo email ảo (Lần thử {retries}/{self.max_retries})")

                # 1. Khởi tạo Email tạm thời
                email = await mail_service.create_inbox()

                if on_status_update:
                    on_status_update(account.username, f"Đã có email {email} -> Mở trình duyệt")

                # 2. Khởi tạo Context trình duyệt ẩn danh ngụy trang vân tay
                context = await self.browser_engine.create_stealth_context(proxy=proxy)

                async def fetch_otp():
                    if on_status_update:
                        on_status_update(account.username, "Đang chờ nhận mã OTP từ hòm thư...")
                    timeout = profile.get("otp_wait_seconds", 60)
                    return await mail_service.wait_for_otp(timeout_sec=timeout)

                # 3. Điền Form đăng ký và nhận OTP
                try:
                    await self.browser_engine.register_account(
                        context=context,
                        profile=profile,
                        username=account.username,
                        password=account.password,
                        email=email,
                        otp_fetcher=fetch_otp,
                    )
                finally:
                    await context.close()

                # 4. Ghi nhận thành công vào file .txt và SQLite
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
                    proxy_address=proxy,
                )

                # Xoay vòng Proxy nếu đã tạo đủ ngưỡng
                self.proxy_manager.record_success()

                if on_status_update:
                    on_status_update(account.username, "Đăng ký THÀNH CÔNG! Đã lưu file .txt")

                return True

            except Exception as e:
                error_msg = str(e)
                if on_status_update:
                    on_status_update(account.username, f"Lỗi: {error_msg} (Thử lại {retries}/{self.max_retries})")

                # Nếu là lần thử cuối cùng và vẫn lỗi -> ghi nhận thất bại
                if retries >= self.max_retries:
                    self.sqlite_repo.save_account(
                        run_id=run_id,
                        sequence_number=account.sequence_number,
                        username=account.username,
                        password=account.password,
                        email=email if "email" in locals() else "N/A",
                        game_name=account.game_name,
                        status="FAILED",
                        proxy_address=proxy,
                        error_reason=error_msg,
                    )
                    # Ghi nhận tài khoản lỗi vào file .txt để người dùng kiểm soát
                    self.txt_exporter.append_account(
                        username=account.username,
                        password=account.password,
                        email=email if "email" in locals() else "N/A",
                        game_name=account.game_name,
                        status="FAILED",
                    )
                    return False

                # Xoay proxy ngay nếu nghi ngờ bị chặn IP
                self.proxy_manager.rotate_next()
                await asyncio.sleep(2.0)
