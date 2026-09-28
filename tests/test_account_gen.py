import pytest
from src.utils.account_gen import AccountGenerator


def test_generate_username_ivanclone():
    """Kiểm tra sinh tên tài khoản dạng ivanclone000, ivanclone001..."""
    gen = AccountGenerator(prefix="ivanclone", padding=3, use_underscore=False)
    assert gen.generate_username(0) == "ivanclone000"
    assert gen.generate_username(1) == "ivanclone001"
    assert gen.generate_username(2) == "ivanclone002"
    assert gen.generate_username(100) == "ivanclone100"


def test_generate_password():
    """Kiểm tra mật khẩu mặc định Longcon@1234."""
    gen = AccountGenerator()
    default_pwd = "Longcon@1234"
    assert gen.generate_password(default_password=default_pwd) == default_pwd


def test_generate_batch():
    """Kiểm tra sinh danh sách hàng loạt tài khoản ivanclone000 -> ivanclone005."""
    gen = AccountGenerator(prefix="ivanclone", padding=3, use_underscore=False)
    batch = gen.generate_batch(
        start_index=0,
        end_index=5,
        game_name="Garena",
        default_password="Longcon@1234",
    )
    assert len(batch) == 6
    assert batch[0].sequence_number == 0
    assert batch[0].username == "ivanclone000"
    assert batch[0].password == "Longcon@1234"
    assert batch[1].sequence_number == 1
    assert batch[1].username == "ivanclone001"
    assert batch[5].sequence_number == 5
    assert batch[5].username == "ivanclone005"
