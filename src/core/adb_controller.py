import asyncio
import subprocess
import os

class ADBController:
    """Điều khiển thiết bị Android qua cáp Type-C (ADB)"""
    def __init__(self, adb_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not adb_path:
            # Đường dẫn mặc định tải từ setup_adb.py
            self.adb_path = os.path.join(base_dir, "adb", "platform-tools", "adb.exe")
        else:
            self.adb_path = adb_path
            
        self.scrcpy_path = os.path.join(base_dir, "scrcpy", "scrcpy.exe")

    def start_screen_mirror(self):
        """Mở cửa sổ hiển thị màn hình điện thoại (scrcpy)"""
        if os.path.exists(self.scrcpy_path):
            # Mở scrcpy dưới nền (không chờ kết thúc)
            # --window-title "Màn hình Game"
            subprocess.Popen([self.scrcpy_path, "--window-title", "Màn HÌnh Điện Thoại Của Bạn"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        return False

    async def run_adb(self, *args):
        """Chạy lệnh ADB và trả về output"""
        cmd = [self.adb_path] + list(args)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')

    async def get_screencap_bytes(self) -> bytes:
        """Chụp màn hình và trả về dữ liệu byte thô (PNG)"""
        cmd = [self.adb_path, 'exec-out', 'screencap', '-p']
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return stdout

    async def get_devices(self):
        """Kiểm tra danh sách thiết bị đang kết nối"""
        stdout, _ = await self.run_adb("devices")
        lines = stdout.strip().split('\n')[1:]
        devices = []
        for line in lines:
            if '\t' in line:
                dev_id, dev_state = line.split('\t')
                if dev_state.strip() == 'device':
                    devices.append(dev_id.strip())
        return devices

    async def tap(self, x: int, y: int):
        """Chạm vào tọa độ (x, y) trên màn hình"""
        await self.run_adb("shell", "input", "tap", str(x), str(y))

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Giả lập thao tác vuốt (kéo) màn hình từ (x1, y1) đến (x2, y2)"""
        await self.run_adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))

    async def type_text(self, text: str):
        """Nhập chữ vào điện thoại"""
        # ADB shell input text không hỗ trợ khoảng trắng trực tiếp dễ dàng, phải escape
        escaped_text = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
        await self.run_adb("shell", "input", "text", escaped_text)
