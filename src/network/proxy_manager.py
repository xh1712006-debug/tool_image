import asyncio
import os
import random
from typing import List, Optional, Set
import aiohttp
from rich.console import Console

import sys

# Đảm bảo UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(highlight=False)


class ProxyManager:
    """Quản lý danh sách Proxy, kiểm tra hoạt động, tự động tìm kiếm proxy sống,
    đảm bảo mỗi tài khoản một IP khác nhau và tự động đổi IP khi gặp sự cố."""

    FREE_PROXY_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=elite",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ]

    CHECK_URL = "http://httpbin.org/ip"

    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        auto_fetch: bool = True,
        rotate_every: int = 1,
    ):
        self.raw_proxies: List[str] = [self._normalize_proxy(p) for p in (proxy_list or []) if p.strip()]
        self.live_proxies: List[str] = list(self.raw_proxies)
        self.bad_proxies: Set[str] = set()
        self.auto_fetch = auto_fetch
        self.rotate_every = rotate_every
        self.current_index = 0
        self.usage_count = 0
        self.last_used_proxy: Optional[str] = None

    @staticmethod
    def _normalize_proxy(proxy: str) -> str:
        """Đảm bảo chuỗi proxy có tiền tố protocol chuẩn và hỗ trợ cả định dạng ip:port:user:pass."""
        proxy = proxy.strip()
        if not proxy:
            return ""
        if not (proxy.startswith("http://") or proxy.startswith("https://") or proxy.startswith("socks5://")):
            parts = proxy.split(":")
            if len(parts) == 4:
                # Dạng ip:port:user:pass phổ biến
                ip, port, user, pwd = parts
                return f"http://{user}:{pwd}@{ip}:{port}"
            elif len(parts) == 2:
                return f"http://{proxy}"
            return f"http://{proxy}"
        return proxy

    @classmethod
    def from_file(cls, file_path: str, auto_fetch: bool = True, rotate_every: int = 1) -> "ProxyManager":
        """Nạp danh sách proxy từ tệp văn bản configs/proxies.txt."""
        if not os.path.exists(file_path):
            return cls([], auto_fetch=auto_fetch, rotate_every=rotate_every)

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]
        
        # Nếu đã có proxy do người dùng chỉ định thì không tự kéo proxy miễn phí công khai
        has_custom = len(lines) > 0
        effective_auto_fetch = auto_fetch and not has_custom
        return cls(lines, auto_fetch=effective_auto_fetch, rotate_every=rotate_every)

    async def ensure_live_proxies(self, min_needed: int = 5) -> int:
        """Tự động tải và kiểm tra danh sách proxy nếu số lượng proxy khả dụng còn ít."""
        if len(self.live_proxies) > 0 and not self.auto_fetch:
            return len(self.live_proxies)

        if len(self.live_proxies) >= min_needed:
            return len(self.live_proxies)

        if not self.auto_fetch:
            return len(self.live_proxies)

        console.print(f"[cyan][*] Đang tự động quét và kiểm tra Proxy sống từ nguồn mở (cần thêm ít nhất {min_needed})...[/cyan]")
        fetched = await self._fetch_proxies_from_apis()
        candidates = [p for p in fetched if p not in self.bad_proxies and p not in self.live_proxies]
        
        # Lấy ngẫu nhiên mẫu tối đa 40 proxy để kiểm tra nhanh
        sample = random.sample(candidates, min(len(candidates), 40)) if candidates else []
        valid_proxies = await self._fast_filter_live_proxies(sample)

        for p in valid_proxies:
            if p not in self.live_proxies and p not in self.bad_proxies:
                self.live_proxies.append(p)

        console.print(f"[bold green][+] Đã tìm thấy {len(valid_proxies)} Proxy mới còn sống! (Tổng khả dụng: {len(self.live_proxies)})[/bold green]")
        return len(self.live_proxies)

    async def _fetch_proxies_from_apis(self) -> List[str]:
        """Tải danh sách proxy thô từ các API công khai."""
        candidates = []
        async with aiohttp.ClientSession() as session:
            for url in self.FREE_PROXY_SOURCES:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            for line in text.splitlines():
                                p = self._normalize_proxy(line)
                                if p:
                                    candidates.append(p)
                            if candidates:
                                break
                except Exception:
                    continue
        return candidates

    async def _fast_filter_live_proxies(self, proxies: List[str]) -> List[str]:
        """Kiểm tra bất đồng bộ tính khả dụng của danh sách proxy trong thời gian tối đa 2.5 giây."""
        live = []
        timeout = aiohttp.ClientTimeout(total=2.5)

        async with aiohttp.ClientSession() as session:
            async def check(proxy_url):
                try:
                    async with session.get(self.CHECK_URL, proxy=proxy_url, timeout=timeout) as resp:
                        if resp.status == 200:
                            return proxy_url
                except Exception:
                    pass
                return None

            tasks = [check(p) for p in proxies]
            results = await asyncio.gather(*tasks)
            live = [r for r in results if r]
        return live

    def get_current_proxy(self) -> Optional[str]:
        """Lấy proxy hiện tại mà không tăng chỉ mục."""
        if not self.live_proxies:
            return None
        return self.live_proxies[self.current_index % len(self.live_proxies)]

    async def get_next_proxy_for_account(self) -> Optional[str]:
        """Cấp 1 Proxy mới riêng biệt cho tài khoản tiếp theo (đảm bảo mỗi tài khoản 1 IP khác)."""
        if self.auto_fetch and len(self.live_proxies) < 3:
            await self.ensure_live_proxies(min_needed=5)

        if not self.live_proxies:
            return None

        # Chuyển sang proxy tiếp theo
        self.current_index = (self.current_index + 1) % len(self.live_proxies)
        proxy = self.live_proxies[self.current_index]
        self.last_used_proxy = proxy
        self.usage_count = 0
        return proxy

    async def mark_bad_and_get_replacement(self, bad_proxy: Optional[str] = None) -> Optional[str]:
        """Khi gặp lỗi (hoặc bị Garena chặn), đưa proxy hỏng vào danh sách đen và trả về 1 proxy thay thế còn sống ngay lập tức.
        Nếu chỉ có 1 proxy duy nhất (ví dụ Proxy Xoay Cổng), sẽ giữ lại và chờ cổng proxy đổi IP mới."""
        target = bad_proxy or self.last_used_proxy or self.get_current_proxy()

        # Nếu chỉ có duy nhất 1 proxy (Proxy xoay cổng), không loại bỏ mà chỉ chờ nó xoay IP
        if len(self.live_proxies) <= 1:
            console.print(f"[yellow][!] Proxy xoay cổng gặp sự cố/chặn, tạm chờ 3 giây để cổng proxy tự cấp IP mới...[/yellow]")
            await asyncio.sleep(3.0)
            return self.get_current_proxy()

        if target:
            self.bad_proxies.add(target)
            if target in self.live_proxies:
                self.live_proxies.remove(target)
            console.print(f"[yellow][!] Đã loại bỏ Proxy lỗi/bị chặn:[/yellow] [dim]{target}[/dim]")

        # Đảm bảo còn proxy sống
        if len(self.live_proxies) < 2 and self.auto_fetch:
            await self.ensure_live_proxies(min_needed=5)

        if not self.live_proxies:
            console.print("[red][X] Không còn proxy nào khả dụng trong pool.[/red]")
            return None

        # Lấy proxy mới khác biệt
        self.current_index = self.current_index % len(self.live_proxies)
        new_proxy = self.live_proxies[self.current_index]
        self.last_used_proxy = new_proxy
        console.print(f"[bold green][+] Đã tự động đổi sang IP mới:[/bold green] [cyan]{new_proxy}[/cyan]")
        return new_proxy

    def record_success(self):
        """Ghi nhận tài khoản hoàn thành thành công."""
        self.usage_count += 1

    def rotate_next(self) -> Optional[str]:
        """Xoay sang proxy tiếp theo (chế độ đồng bộ tương thích)."""
        if not self.live_proxies:
            return None
        self.current_index = (self.current_index + 1) % len(self.live_proxies)
        self.usage_count = 0
        return self.get_current_proxy()
