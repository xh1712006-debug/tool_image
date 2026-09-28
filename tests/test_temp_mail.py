import pytest
from src.services.temp_mail_service import MailTmService, MockTempMailService


def test_extract_otp_from_various_formats():
    """Kiểm tra bóc tách mã OTP từ các định dạng email thực tế khác nhau."""
    # Định dạng tiếng Anh phổ biến
    text1 = "Your verification code is 481920. Please do not share it."
    assert MailTmService.extract_otp(text1) == "481920"

    # Định dạng tiếng Việt
    text2 = "Mã xác nhận đăng ký tài khoản của bạn là: 928341"
    assert MailTmService.extract_otp(text2) == "928341"

    # Định dạng OTP 4 số
    text3 = "OTP code: 5821. Valid for 5 minutes."
    assert MailTmService.extract_otp(text3) == "5821"

    # Định dạng nằm trong mã HTML
    html_text = "<div class='otp-box'><h2>Mã OTP: <b>773321</b></h2></div>"
    assert MailTmService.extract_otp(html_text) == "773321"


@pytest.mark.asyncio
async def test_mock_temp_mail_service():
    """Kiểm tra quy trình hoạt động của Mock Temp Mail Service."""
    service = MockTempMailService(mock_otp="654321")
    email = await service.create_inbox()
    assert email.endswith("@mockmail.test")

    otp = await service.wait_for_otp(timeout_sec=5)
    assert otp == "654321"
