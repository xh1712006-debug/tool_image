import random
import string
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AccountItem:
    """Đối tượng lưu trữ thông tin cơ bản của một tài khoản cần tạo."""
    sequence_number: int
    username: str
    password: str
    game_name: str


class AccountGenerator:
    """Bộ sinh tên tài khoản tự tăng và quản lý mật khẩu."""

    def __init__(
        self,
        prefix: str = "ivanclone",
        padding: int = 3,
        use_underscore: bool = False,
        random_salt: bool = False,
    ):
        self.prefix = prefix
        self.padding = padding
        self.use_underscore = use_underscore
        self.random_salt = random_salt

    def generate_username(self, index: int, prefix: Optional[str] = None) -> str:
        """Sinh tên đăng nhập theo thứ tự tự tăng từ 0 đến 1000.
        
        Ví dụ: ivanclone000, ivanclone001, ivanclone002...
        """
        active_prefix = prefix if prefix is not None else self.prefix
        if self.padding <= 0:
            padded_index = str(index)
        else:
            padded_index = str(index).zfill(self.padding)

        if self.use_underscore:
            base_name = f"{active_prefix}_{padded_index}"
        else:
            base_name = f"{active_prefix}{padded_index}"

        if self.random_salt:
            salt = "".join(random.choices(string.ascii_lowercase + string.digits, k=2))
            return f"{base_name}_{salt}"

        return base_name

    def generate_password(self, default_password: Optional[str] = None, length: int = 12) -> str:
        """Trả về mật khẩu mặc định hoặc sinh mật khẩu ngẫu nhiên phức tạp."""
        if default_password:
            return default_password

        # Sinh mật khẩu ngẫu nhiên có chữ hoa, thường, số và ký tự đặc biệt
        uppercase = random.choice(string.ascii_uppercase)
        lowercase = random.choice(string.ascii_lowercase)
        digit = random.choice(string.digits)
        special = random.choice("@#$!%*?&")
        
        remaining = "".join(
            random.choices(string.ascii_letters + string.digits + "@#$!%*?&", k=max(length - 4, 4))
        )
        password_list = list(uppercase + lowercase + digit + special + remaining)
        random.shuffle(password_list)
        return "".join(password_list)

    def generate_batch(
        self,
        start_index: int,
        end_index: int,
        game_name: str,
        default_password: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> List[AccountItem]:
        """Tạo danh sách các tài khoản theo dải số chỉ định."""
        accounts = []
        for idx in range(start_index, end_index + 1):
            user = self.generate_username(idx, prefix=prefix)
            pwd = self.generate_password(default_password=default_password)
            accounts.append(
                AccountItem(
                    sequence_number=idx,
                    username=user,
                    password=pwd,
                    game_name=game_name,
                )
            )
        return accounts

    @classmethod
    def load_from_txt(cls, file_path: str) -> List[AccountItem]:
        """Tải danh sách tài khoản từ file txt (định dạng: username|password|email|game_name|status)."""
        import os
        if not os.path.exists(file_path):
            return []
        
        accounts = []
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                parts = line.strip().split("|")
                if len(parts) >= 2:
                    username = parts[0].strip()
                    password = parts[1].strip()
                    game_name = parts[3].strip() if len(parts) >= 4 else "DemoGame"
                    accounts.append(AccountItem(sequence_number=i, username=username, password=password, game_name=game_name))
        return accounts
