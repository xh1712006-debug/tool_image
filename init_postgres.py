import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.storage.postgres_repo import PostgresRepository

# Lấy chuỗi kết nối từ file .env, nếu không có thì lấy mặc định
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:170106@localhost:5432/tool_image")

def main():
    print(f"Connecting to PostgreSQL at: {POSTGRES_DSN}")
    try:
        repo = PostgresRepository(dsn=POSTGRES_DSN)
        print("[+] Successfully created tables 'task_runs' and 'accounts' in 'tool_image' database!")
    except Exception as e:
        print(f"[-] Error connecting to PostgreSQL: {e}")
        print("=> Hint: Check if password, user, or port (5433/5432) are correct.")

if __name__ == "__main__":
    main()
