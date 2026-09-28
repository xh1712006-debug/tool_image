import asyncio
import re
from typing import Optional
from playwright.async_api import Page


class TempMailWebClient:
    """Điều khiển tự động giao diện trang web https://temp-mail.org/vi/ trên một Tab trình duyệt trực quan."""

    URL = "https://temp-mail.org/vi/"

    @classmethod
    async def get_email_from_page(cls, page: Page, timeout_sec: int = 40) -> str:
        """Mở trang temp-mail.org và chờ lấy địa chỉ email hiển thị trên ô #mail."""
        if cls.URL not in page.url:
            await page.goto(cls.URL, wait_until="domcontentloaded", timeout=45000)

        # Chờ ô nhập email xuất hiện trên giao diện
        await page.wait_for_selector("#mail, input.emailbox-input", timeout=timeout_sec * 1000)

        elapsed = 0
        while elapsed < timeout_sec:
            try:
                email_val = await page.input_value("#mail")
                if (
                    email_val
                    and "@" in email_val
                    and "." in email_val
                    and not any(k in email_val.lower() for k in ["đang tải", "loading", "..."])
                ):
                    return email_val.strip()
            except Exception:
                pass

            await asyncio.sleep(1.0)
            elapsed += 1

        raise TimeoutError(f"Hết thời gian {timeout_sec}s: Chưa lấy được email từ temp-mail.org.")

    @classmethod
    async def delete_and_get_new_email(cls, page: Page, timeout_sec: int = 30) -> str:
        """Bấm nút 'Xoá' để hủy email cũ và tự động lấy một email mới toanh từ temp-mail.org."""
        old_email = ""
        try:
            old_email = await page.input_value("#mail")
        except Exception:
            pass

        # Bấm nút Xoá (#click-to-delete)
        delete_selectors = ["#click-to-delete", "button:has-text('Xoá')", "a:has-text('Xoá')", ".btn-delete"]
        clicked = False
        for sel in delete_selectors:
            try:
                if await page.is_visible(sel):
                    await page.click(sel)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            await page.reload(wait_until="domcontentloaded")

        # Chờ email mới khác với email cũ
        elapsed = 0
        while elapsed < timeout_sec:
            try:
                new_email = await page.input_value("#mail")
                if (
                    new_email
                    and "@" in new_email
                    and "." in new_email
                    and new_email != old_email
                    and not any(k in new_email.lower() for k in ["đang tải", "loading", "..."])
                ):
                    return new_email.strip()
            except Exception:
                pass
            await asyncio.sleep(1.0)
            elapsed += 1

        return await cls.get_email_from_page(page, timeout_sec=timeout_sec)

    @classmethod
    async def wait_for_otp_from_inbox(cls, page: Page, timeout_sec: int = 65) -> str:
        """Lắng nghe danh sách thư mới trong bảng hộp thư của temp-mail.org và bóc tách mã OTP."""
        elapsed = 0

        while elapsed < timeout_sec:
            try:
                mail_items = await page.query_selector_all(
                    ".inbox-dataList ul > li a, .inbox-dataList a.viewLink"
                )
                for item in mail_items:
                    try:
                        if await item.is_visible():
                            txt = (await item.inner_text() or "").strip().lower()
                            if len(txt) > 3:
                                await item.click(timeout=3000)
                                await asyncio.sleep(1.5)
                                content = await page.inner_text("body")
                                otp = cls.extract_otp(content)
                                if otp:
                                    return otp
                    except Exception:
                        continue
            except Exception:
                pass

            await asyncio.sleep(1.5)
            elapsed += 1.5

        raise TimeoutError(f"Chưa nhận được thư OTP từ Garena trong {timeout_sec}s.")

    @staticmethod
    def extract_otp(content: str) -> Optional[str]:
        """Bóc tách mã OTP từ nội dung thư bằng biểu thức chính quy."""
        context_patterns = [
            r"(?:code|otp|mã|xác nhận|verify|pin)[\s:]*([0-9]{4,6})",
            r"\b([0-9]{6})\b",
            r"\b([0-9]{4})\b",
        ]
        for pattern in context_patterns:
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            if matches:
                return matches[0]
        return None
