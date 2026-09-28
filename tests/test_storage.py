import os
import tempfile
import pytest
from src.storage.txt_exporter import TxtExporter
from src.storage.sqlite_repo import SqliteRepository


def test_txt_exporter_format_and_append():
    """Kiểm tra xuất file .txt đúng chuẩn định dạng ngăn cách bởi dấu |."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = os.path.join(tmp_dir, "test_output.txt")
        exporter = TxtExporter(out_file)

        line1 = exporter.append_account(
            username="gamer_0001",
            password="Password123@",
            email="user1@tmp.org",
            game_name="VõLâm",
            status="SUCCESS",
            created_at="2026-09-21 12:00:00",
        )
        assert line1 == "gamer_0001|Password123@|user1@tmp.org|VõLâm|SUCCESS|2026-09-21 12:00:00"

        line2 = exporter.append_account(
            username="gamer_0002",
            password="Password123@",
            email="user2@tmp.org",
            game_name="VõLâm",
            status="FAILED",
            created_at="2026-09-21 12:00:15",
        )
        assert line2 == "gamer_0002|Password123@|user2@tmp.org|VõLâm|FAILED|2026-09-21 12:00:15"

        lines = exporter.read_all_lines()
        assert len(lines) == 2
        # Kiểm tra số lượng trường dữ liệu (6 trường)
        parts = lines[0].split("|")
        assert len(parts) == 6
        assert parts[0] == "gamer_0001"
        assert parts[3] == "VõLâm"


def test_sqlite_repo_and_resume_index():
    """Kiểm tra lưu trữ SQLite và tính năng Resume khi khởi động lại."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test.sqlite")
        repo = SqliteRepository(db_file)

        # Chưa có tài khoản nào -> Resume index = 1
        assert repo.get_resume_index("GameA") == 1

        run_id = repo.start_run("Run1", "GameA", 1, 100)
        assert run_id > 0

        # Lưu tài khoản 1 thành công
        repo.save_account(
            run_id=run_id,
            sequence_number=1,
            username="player_0001",
            password="pwd",
            email="e1@mail.com",
            game_name="GameA",
            status="SUCCESS",
        )

        # Lưu tài khoản 2 thành công
        repo.save_account(
            run_id=run_id,
            sequence_number=2,
            username="player_0002",
            password="pwd",
            email="e2@mail.com",
            game_name="GameA",
            status="SUCCESS",
        )

        # Lưu tài khoản 3 thất bại
        repo.save_account(
            run_id=run_id,
            sequence_number=3,
            username="player_0003",
            password="pwd",
            email="e3@mail.com",
            game_name="GameA",
            status="FAILED",
            error_reason="Timeout",
        )

        # Resume index cho GameA phải là 3 (vì số lớn nhất thành công là 2, nên chạy tiếp từ 2+1=3)
        assert repo.get_resume_index("GameA") == 3

        # Kiểm tra thống kê
        stats = repo.get_run_stats(run_id)
        assert stats["total_success"] == 2
        assert stats["total_failed"] == 1
