import pytest
from unittest.mock import MagicMock
from src.agents.assistant_runner import AssistantRunner

def test_assistant_runner_init_defaults():
    mock_browser = MagicMock()
    mock_proxy = MagicMock()
    mock_repo = MagicMock()
    mock_exporter = MagicMock()

    runner = AssistantRunner(
        browser_engine=mock_browser,
        proxy_manager=mock_proxy,
        sqlite_repo=mock_repo,
        txt_exporter=mock_exporter,
        use_proxy=False,
        mail_provider="mailtm",
    )
    assert runner.mail_provider == "mailtm"
    assert runner.use_proxy is False


def test_browser_engine_cdp_init():
    from src.browser.browser_engine import BrowserEngine, find_chrome_executable, get_chrome_profile_email
    engine = BrowserEngine(headless=False, use_cdp=True, cdp_port=9222, cdp_profile="Default")
    assert engine.use_cdp is True
    assert engine.cdp_port == 9222
    assert engine.cdp_profile == "Default"

    exe = find_chrome_executable()
    assert exe is not None and len(exe) > 0

    email = get_chrome_profile_email("Default")
    # Trên máy của user, Default là xh1712006@gmail.com
    assert "@" in email
