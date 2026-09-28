import pytest
from src.network.proxy_manager import ProxyManager


def test_proxy_normalize():
    pm = ProxyManager(auto_fetch=False)
    assert pm._normalize_proxy("1.2.3.4:8080") == "http://1.2.3.4:8080"
    assert pm._normalize_proxy("http://5.6.7.8:3128") == "http://5.6.7.8:3128"
    assert pm._normalize_proxy("socks5://1.1.1.1:1080") == "socks5://1.1.1.1:1080"
    assert pm._normalize_proxy("103.152.112.50:8080:userdemo:passdemo") == "http://userdemo:passdemo@103.152.112.50:8080"
    assert pm._normalize_proxy("") == ""


@pytest.mark.asyncio
async def test_per_account_proxy_rotation():
    proxies = ["10.0.0.1:8080", "10.0.0.2:8080", "10.0.0.3:8080"]
    pm = ProxyManager(proxy_list=proxies, auto_fetch=False, rotate_every=1)

    p1 = await pm.get_next_proxy_for_account()
    p2 = await pm.get_next_proxy_for_account()
    p3 = await pm.get_next_proxy_for_account()

    assert p1 == "http://10.0.0.2:8080"
    assert p2 == "http://10.0.0.3:8080"
    assert p3 == "http://10.0.0.1:8080"
    assert p1 != p2
    assert p2 != p3


@pytest.mark.asyncio
async def test_mark_bad_and_failover():
    proxies = ["10.0.0.1:8080", "10.0.0.2:8080"]
    pm = ProxyManager(proxy_list=proxies, auto_fetch=False, rotate_every=1)

    bad = "http://10.0.0.1:8080"
    replacement = await pm.mark_bad_and_get_replacement(bad)

    assert bad in pm.bad_proxies
    assert bad not in pm.live_proxies
    assert replacement == "http://10.0.0.2:8080"
    assert len(pm.live_proxies) == 1


@pytest.mark.asyncio
async def test_single_rotating_proxy_never_exhausted():
    # Khi dùng 1 Proxy xoay cổng duy nhất, việc mark bad không làm mất proxy
    pm = ProxyManager(proxy_list=["103.1.2.3:8888"], auto_fetch=False)
    p1 = await pm.get_next_proxy_for_account()
    assert p1 == "http://103.1.2.3:8888"

    # Khi gặp lỗi, proxy xoay vẫn còn được giữ lại
    p_retry = await pm.mark_bad_and_get_replacement(p1)
    assert p_retry == "http://103.1.2.3:8888"
    assert len(pm.live_proxies) == 1
