import asyncio
import re
import random
import string
from abc import ABC, abstractmethod
from typing import Optional, List
import httpx


class BaseTempMailService(ABC):
    """Lớp cơ sở trừu tượng cho dịch vụ Email tạm thời."""

    @abstractmethod
    async def create_inbox(self) -> str:
        """Tạo một hòm thư ảo mới và trả về địa chỉ email."""
        pass

    @abstractmethod
    async def wait_for_otp(self, timeout_sec: int = 60, poll_interval_sec: int = 3) -> str:
        """Lắng nghe hộp thư đến và bóc tách mã OTP qua Regex."""
        pass


class MailTmService(BaseTempMailService):
    """Triển khai kết nối API Mail.tm (Dịch vụ thư điện tử tạm thời miễn phí)."""

    BASE_URL = "https://api.mail.tm"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient(timeout=15.0)
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.token: Optional[str] = None

    async def _get_domain(self) -> str:
        """Lấy danh sách domain khả dụng từ Mail.tm."""
        res = await self.client.get(f"{self.BASE_URL}/domains")
        res.raise_for_status()
        data = res.json()
        domains = data.get("hydra:member", [])
        if not domains:
            raise RuntimeError("Không tìm thấy domain khả dụng trên Mail.tm")
        # Chọn ngẫu nhiên một domain
        return random.choice(domains)["domain"]

    async def create_inbox(self) -> str:
        """Tạo một tài khoản email ảo mới trên Mail.tm."""
        domain = await self._get_domain()
        # Sinh tên hộp thư ngẫu nhiên 8 ký tự
        random_user = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.email = f"user_{random_user}@{domain}"
        self.password = f"TmpPass_{random_user}123@"

        # Đăng ký tài khoản email với cơ chế xử lý 429 Rate Limit
        max_attempts = 4
        for attempt in range(max_attempts):
            reg_res = await self.client.post(
                f"{self.BASE_URL}/accounts",
                json={"address": self.email, "password": self.password},
            )
            if reg_res.status_code == 429:
                retry_after = int(reg_res.headers.get("retry-after", "4"))
                # Đợi một chút rồi thử lại
                await asyncio.sleep(retry_after + 1)
                continue
            reg_res.raise_for_status()
            break

        # Đăng nhập lấy Bearer token để đọc hòm thư
        for attempt in range(max_attempts):
            token_res = await self.client.post(
                f"{self.BASE_URL}/token",
                json={"address": self.email, "password": self.password},
            )
            if token_res.status_code == 429:
                retry_after = int(token_res.headers.get("retry-after", "3"))
                await asyncio.sleep(retry_after + 1)
                continue
            token_res.raise_for_status()
            self.token = token_res.json()["token"]
            break

        return self.email

    async def wait_for_otp(self, timeout_sec: int = 60, poll_interval_sec: int = 3) -> str:
        """Thăm dò hòm thư định kỳ để tìm mã OTP xác thực bằng biểu thức chính quy."""
        if not self.token:
            raise RuntimeError("Chưa khởi tạo hòm thư hoặc thiếu token xác thực.")

        headers = {"Authorization": f"Bearer {self.token}"}
        elapsed = 0

        while elapsed < timeout_sec:
            await asyncio.sleep(poll_interval_sec)
            elapsed += poll_interval_sec

            try:
                res = await self.client.get(f"{self.BASE_URL}/messages", headers=headers)
                if res.status_code == 200:
                    messages = res.json().get("hydra:member", [])
                    if messages:
                        # Lấy thư mới nhất
                        msg_id = messages[0]["id"]
                        msg_detail_res = await self.client.get(
                            f"{self.BASE_URL}/messages/{msg_id}", headers=headers
                        )
                        if msg_detail_res.status_code == 200:
                            msg_data = msg_detail_res.json()
                            content = (
                                msg_data.get("text", "")
                                + " "
                                + msg_data.get("subject", "")
                                + " "
                                + str(msg_data.get("html", ""))
                            )
                            otp = self.extract_otp(content)
                            if otp:
                                return otp
            except httpx.HTTPError:
                # Bỏ qua lỗi mạng tạm thời trong lúc polling
                continue

        raise TimeoutError(f"Không nhận được mã OTP sau {timeout_sec} giây chờ đợi.")

    @staticmethod
    def extract_otp(content: str) -> Optional[str]:
        """Trích xuất mã số xác thực 4 đến 6 chữ số từ nội dung thư."""
        # Ưu tiên tìm các cụm từ ngữ cảnh: code: 123456, otp: 123456, ma: 123456
        context_patterns = [
            r"(?:code|otp|mã|xác nhận|verify|pin)[\s:]*([0-9]{4,6})",
            r"\b([0-9]{4,6})\b",
        ]
        for pattern in context_patterns:
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            if matches:
                # Trả về mã đầu tiên tìm thấy
                return matches[0]
        return None

    async def close(self):
        """Đóng kết nối HTTP Client."""
        await self.client.aclose()


class MockTempMailService(BaseTempMailService):
    """Dịch vụ Mail giả lập phục vụ kiểm thử đơn vị hoặc khi không có Internet."""

    def __init__(self, mock_otp: str = "889922"):
        self.mock_otp = mock_otp
        self.email: Optional[str] = None

    async def create_inbox(self) -> str:
        rand_id = "".join(random.choices(string.ascii_lowercase, k=6))
        self.email = f"mock_{rand_id}@mockmail.test"
        return self.email

    async def wait_for_otp(self, timeout_sec: int = 60, poll_interval_sec: int = 1) -> str:
        await asyncio.sleep(0.1)
        return self.mock_otp
