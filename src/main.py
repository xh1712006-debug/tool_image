import argparse
import asyncio
import io
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

# Đảm bảo console Windows hỗ trợ xuất UTF-8 tiếng Việt
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Đảm bảo đường dẫn gốc của dự án luôn nằm trong sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yaml
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from src.utils.account_gen import AccountGenerator
from src.agents.assistant_runner import AssistantRunner
from src.browser.browser_engine import BrowserEngine, get_chrome_profile_email
from src.network.proxy_manager import ProxyManager
from src.core.task_orchestrator import TaskOrchestrator
from src.demo.demo_server import DemoGameServer
from src.services.temp_mail_service import MailTmService, MockTempMailService
from src.storage.sqlite_repo import SqliteRepository
from src.storage.txt_exporter import TxtExporter

console = Console()


def load_yaml_config(path: str = "configs/app_config.yaml") -> dict:
    """Đọc tệp cấu hình YAML của ứng dụng."""
    full_path = os.path.join(PROJECT_ROOT, path)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_game_profiles(path: str = "configs/game_profiles.json") -> dict:
    """Đọc tệp hồ sơ cấu hình các tựa game."""
    full_path = os.path.join(PROJECT_ROOT, path)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


async def main():
    parser = argparse.ArgumentParser(description="Game Account Automation Engine v1.0")
    parser.add_argument("--game", type=str, default="Garena", help="Tên game trong configs/game_profiles.json (Ví dụ: Garena, GameDemo)")
    parser.add_argument("--start", type=int, default=0, help="Số thứ tự bắt đầu (Mặc định: 0 cho ivanclone000)")
    parser.add_argument("--end", type=int, default=10, help="Số thứ tự kết thúc (Mặc định: 10)")
    parser.add_argument("--prefix", type=str, default="ivanclone", help="Tiền tố tên tài khoản (Mặc định: ivanclone)")
    parser.add_argument("--password", type=str, default="Longcon@1234", help="Mật khẩu mặc định dùng chung")
    parser.add_argument("--proxy", type=str, default=None, help="Địa chỉ Proxy tĩnh cố định (Ví dụ: http://ip:port)")
    parser.add_argument("--no-proxy", action="store_true", help="Không sử dụng Proxy (chạy trực tiếp qua IP máy tính / 4G)")
    parser.add_argument("--resume", action="store_true", help="Tự động tiếp tục từ vị trí đã thành công gần nhất")
    parser.add_argument("--concurrency", type=int, default=None, help="Số lượng luồng chạy đồng thời")
    parser.add_argument("--headless", action="store_true", default=False, help="Chạy ẩn cửa sổ trình duyệt")
    parser.add_argument("--assistant", action="store_true", help="Kích hoạt chế độ Trợ lý Bán tự động")
    parser.add_argument("--mock-mail", action="store_true", help="Sử dụng dịch vụ Mail giả lập (dùng cho test)")
    parser.add_argument("--real-mail", action="store_true", help="Bắt buộc sử dụng Mail.tm REST API")
    parser.add_argument("--mail-provider", type=str, default="auto", choices=["auto", "mailtm", "web"], help="Dịch vụ email: auto (tối ưu tự động / fallback), mailtm (API Mail.tm, tối ưu cho WiFi), web (temp-mail.org)")
    parser.add_argument("--cdp", action="store_true", help="Kết nối và chạy trực tiếp trên Google Chrome thật của máy (có sẵn tài khoản Gmail)")
    parser.add_argument("--cdp-profile", type=str, default="Default", help="Tên Profile Chrome muốn dùng (Default, 'Profile 2', 'Profile 3'...)")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Cổng kết nối Remote Debugging CDP của Chrome (Mặc định: 9222)")
    args = parser.parse_args()

    # Nạp cấu hình
    app_cfg = load_yaml_config()
    profiles = load_game_profiles()

    if args.game not in profiles:
        console.print(f"[bold red]Lỗi:[/bold red] Không tìm thấy hồ sơ game '[yellow]{args.game}[/yellow]' trong configs/game_profiles.json!")
        console.print(f"Các game khả dụng: {list(profiles.keys())}")
        return

    profile = profiles[args.game]
    gen_cfg = app_cfg.get("generator", {})
    workers_cfg = app_cfg.get("workers", {})
    storage_cfg = app_cfg.get("storage", {})

    prefix = args.prefix
    padding = 3  # Định dạng ivanclone000, ivanclone001...
    random_salt = gen_cfg.get("random_salt", False)
    default_password = args.password
    concurrency = args.concurrency or workers_cfg.get("concurrency", 1)
    output_txt = os.path.join(PROJECT_ROOT, storage_cfg.get("output_txt_path", "output/accounts_output.txt"))
    sqlite_path = os.path.join(PROJECT_ROOT, storage_cfg.get("sqlite_db_path", "storage/database.sqlite"))

    # Khởi tạo lưu trữ và kiểm tra Resume
    if storage_cfg.get("use_postgres", False):
        from src.storage.postgres_repo import PostgresRepository
        dsn = os.getenv("POSTGRES_DSN")
        if not dsn:
            dsn = storage_cfg.get("postgres_dsn", "postgresql://postgres:postgres@localhost:5432/tool_image")
            
        console.print(f"[cyan][*] Đang sử dụng cơ sở dữ liệu PostgreSQL...[/cyan]")
        try:
            repo = PostgresRepository(dsn=dsn)
        except Exception as e:
            console.print(f"[red][!] Lỗi kết nối PostgreSQL: {e}[/red]")
            console.print("[yellow]=> Hãy mở pgAdmin và chạy file sql.txt để tạo bảng (hoặc sửa dsn trong file .env)[/yellow]")
            return
    else:
        repo = SqliteRepository(sqlite_path)
    
    txt_exporter = TxtExporter(output_txt)

    if args.resume:
        start_index = repo.get_resume_index(args.game)
        console.print(f"[bold green]Tính năng Resume kích hoạt:[/bold green] Bắt đầu tiếp tục từ tài khoản số [cyan]{start_index}[/cyan]")
    else:
        start_index = args.start

    end_index = args.end

    if start_index > end_index:
        console.print(f"[bold green]Thông báo:[/bold green] Dải số {start_index} -> {end_index} đã hoàn tất từ trước!")
        return

    total_tasks = end_index - start_index + 1

    # Tự động kích hoạt demo server nếu là URL cục bộ
    demo_server = None
    if "127.0.0.1" in profile.get("register_url", "") or "localhost" in profile.get("register_url", ""):
        demo_server = DemoGameServer()
        demo_server.start()

    # Nhận diện chế độ Trợ lý (Assistant Mode)
    is_assistant_mode = args.assistant or (args.game == "Garena")

    start_name = f"{prefix}{str(start_index).zfill(padding)}"
    end_name = f"{prefix}{str(end_index).zfill(padding)}"

    use_proxy = not args.no_proxy

    # In thông tin khởi động
    header_table = Table.grid(padding=(0, 2))
    header_table.add_column(style="bold cyan", justify="right")
    header_table.add_column(style="white")
    header_table.add_row("Tựa Game:", f"[yellow]{profile.get('name', args.game)}[/yellow]")
    header_table.add_row("URL Đăng Ký:", f"[blue]{profile.get('register_url')}[/blue]")
    # Xác định dịch vụ email
    mail_prov = args.mail_provider
    if args.real_mail:
        mail_prov = "mailtm"
    mail_desc = "Mail.tm REST API" if mail_prov == "mailtm" else "Web temp-mail.org (Tab 1 trực quan)"

    header_table.add_row("Chế độ Vận hành:", "[bold magenta]Trợ lý Điền Form + Nhận diện Captcha[/bold magenta]" if is_assistant_mode else "Tự động hoàn toàn")
    header_table.add_row("Dải tài khoản:", f"{start_name} -> {end_name} (Tổng: {total_tasks} acc)")
    header_table.add_row("Mật khẩu dùng chung:", f"[green]{default_password}[/green]")
    header_table.add_row("Quốc gia mặc định:", "[bold green]Việt Nam (VN)[/bold green]")
    header_table.add_row("Cơ chế Proxy / IP:", "[bold green]Tự động lấy & xoay IP mỗi tài khoản + Tự đổi khi lỗi[/bold green]" if use_proxy else "[yellow]Mạng WiFi trực tiếp (--no-proxy)[/yellow]")
    if args.cdp:
        email_acc = get_chrome_profile_email(args.cdp_profile)
        email_display = f" ({email_acc})" if email_acc else ""
        header_table.add_row("Trình duyệt:", f"[bold green]Google Chrome Thật - Profile '{args.cdp_profile}'{email_display}[/bold green]")
    header_table.add_row("Dịch vụ Email:", f"[bold cyan]{mail_desc}[/bold cyan]")
    header_table.add_row("File xuất kết quả:", f"[magenta]{output_txt}[/magenta]")

    console.print(Panel(header_table, title="[bold blue]GAME ACCOUNT AUTOMATION ENGINE (PER-ACCOUNT IP ROTATION)[/bold blue]", expand=False))

    # Bật Web UI Controller
    from src.web_ui import WebUIControlPanel, BOT_JOB_QUEUE
    web_ui = WebUIControlPanel()
    web_ui.start()
    console.print("[bold green]================================================[/bold green]")
    console.print(f"[bold green]🚀 ĐÃ BẬT BẢNG ĐIỀU KHIỂN BOT TẠI: http://127.0.0.1:8765[/bold green]")
    console.print("[bold green]Hãy mở link trên bằng trình duyệt của bạn để nhập tài khoản![/bold green]")
    console.print("[bold green]================================================[/bold green]")

    # Khởi tạo Proxy Manager thông minh
    if args.proxy:
        proxy_manager = ProxyManager([args.proxy], auto_fetch=False, rotate_every=1)
    else:
        proxy_manager = ProxyManager.from_file(
            os.path.join(PROJECT_ROOT, "configs/proxies.txt"),
            auto_fetch=use_proxy,
            rotate_every=1,
        )

    if use_proxy:
        await proxy_manager.ensure_live_proxies(min_needed=3)

    browser_engine = BrowserEngine(
        headless=args.headless,
        use_cdp=args.cdp,
        cdp_port=args.cdp_port,
        cdp_profile=args.cdp_profile,
    )
    await browser_engine.start()

    runner = AssistantRunner(
        browser_engine=browser_engine,
        proxy_manager=proxy_manager,
        sqlite_repo=repo,
        txt_exporter=txt_exporter,
        use_proxy=use_proxy,
        mail_provider=mail_prov,
    )

    try:
        console.print("\n[yellow][*] Đang chờ lệnh từ Bảng Điều Khiển...[/yellow]")
        while True:
            if BOT_JOB_QUEUE:
                job = BOT_JOB_QUEUE.pop(0)
                
                if job.get("action") == "clean_popups":
                    from src.core.adb_controller import ADBController
                    from src.core.game_bot import GameBot
                    console.print("\n[bold yellow]═══════════ NHẬN LỆNH DỌN DẸP POPUP TỪ WEB ═══════════[/bold yellow]")
                    adb = ADBController()
                    bot = GameBot(adb)
                    await bot.close_all_popups(max_attempts=15)
                    console.print("\n[yellow][*] Tiếp tục chờ lệnh mới từ Bảng Điều Khiển...[/yellow]")
                else:
                    u = job.get("username", "")
                    p = job.get("password", "")
                    console.print(f"\n[bold blue]═══════════ ĐÃ NHẬN LỆNH ĐĂNG NHẬP: {u} ═══════════[/bold blue]")
                    # Chạy đăng nhập trên điện thoại qua ADB
                    await runner.run_adb_login_game(username=u, password=p)
                    console.print("\n[yellow][*] Tiếp tục chờ lệnh mới từ Bảng Điều Khiển...[/yellow]")
            else:
                await asyncio.sleep(1.0)
    finally:
        try:
            await browser_engine.close()
        except Exception:
            pass
        web_ui.stop()
    return

    # Chế độ tự động thông thường qua Headless / TaskOrchestrator
    browser_engine = BrowserEngine(
        headless=args.headless,
        use_cdp=args.cdp,
        cdp_port=args.cdp_port,
        cdp_profile=args.cdp_profile,
    )
    await browser_engine.start()

    def mail_factory():
        if (args.mock_mail or "127.0.0.1" in profile.get("register_url", "")) and not args.real_mail:
            return MockTempMailService(mock_otp="889922")
        return MailTmService()

    orchestrator = TaskOrchestrator(
        browser_engine=browser_engine,
        mail_service_factory=mail_factory,
        proxy_manager=proxy_manager,
        sqlite_repo=sqlite_repo,
        txt_exporter=txt_exporter,
    )

    semaphore = asyncio.Semaphore(concurrency)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            overall_task = progress.add_task("[cyan]Tiến trình tổng thể...", total=total_tasks)

            async def worker_wrapper(acc):
                async with semaphore:
                    def update_cb(u, msg):
                        progress.update(overall_task, description=f"[cyan]Xử lý {u}: [white]{msg}[/white]")

                    await orchestrator.process_account(
                        account=acc,
                        profile=profile,
                        run_id=run_id,
                        on_status_update=update_cb,
                    )
                    progress.advance(overall_task)

            tasks = [worker_wrapper(acc) for acc in accounts]
            await asyncio.gather(*tasks)

    finally:
        try:
            await browser_engine.close()
        except Exception:
            pass
        if demo_server:
            demo_server.stop()

    stats = sqlite_repo.get_run_stats(run_id)
    console.print("\n[bold green]══════════════ HOÀN TẤT PHIÊN ĐĂNG KÝ ══════════════[/bold green]")
    console.print(f"✔ Thành công: [bold green]{stats['total_success']}[/bold green] tài khoản")
    console.print(f"✖ Thất bại: [bold red]{stats['total_failed']}[/bold red] tài khoản")
    console.print(f"📂 Kết quả đã lưu vào: [cyan]{output_txt}[/cyan] (Ngăn cách bằng dấu |)")


if __name__ == "__main__":
    asyncio.run(main())
