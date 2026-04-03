import os
import subprocess
import cv2 as cv

def _load_config():
    """
    Đọc ADB_PATH và DEVICE_ID từ:
    1. File config.tmp (được tạo bởi run_bot.bat)
    2. Biến môi trường
    3. Giá trị mặc định
    """
    adb_path = "adb"
    device_id = "127.0.0.1:5555"

    # Tìm config.tmp từ thư mục gốc project (2 cấp trên utils/)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(base_dir, "config.tmp")

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("ADB_PATH="):
                    adb_path = line[len("ADB_PATH="):]
                elif line.startswith("DEVICE_ID="):
                    device_id = line[len("DEVICE_ID="):]
        print(f"[CONFIG] Đọc từ config.tmp: ADB={adb_path} | Device={device_id}")
    else:
        # Fallback: biến môi trường
        adb_path = os.environ.get("ADB_PATH", adb_path)
        device_id = os.environ.get("DEVICE_ID", device_id)
        print(f"[CONFIG] Dùng mặc định: ADB={adb_path} | Device={device_id}")

    return adb_path, device_id


# Load config khi import module
ADB_PATH, DEFAULT_DEVICE_ID = _load_config()


class AdbHelper:
    def __init__(self, device_id=None):
        self.device_id = device_id or DEFAULT_DEVICE_ID
        self.adb = ADB_PATH

    def tap(self, x, y):
        self.shell(['input', 'tap', str(x), str(y)])

    def swipe(self, f_point, t_point, duration):
        (x1, y1) = f_point
        (x2, y2) = t_point
        self.shell(['input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)])

    def shell(self, cmd_args):
        base_cmd = [self.adb]
        if self.device_id:
            base_cmd.extend(['-s', self.device_id])
        base_cmd.append('shell')
        base_cmd.extend(cmd_args)
        return subprocess.run(base_cmd, capture_output=True, text=True)

    def get_screenshot(self):
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screen.png')

        base_adb = [self.adb]
        if self.device_id:
            base_adb.extend(['-s', self.device_id])

        # Chụp màn hình
        result = subprocess.run(
            [*base_adb, 'shell', 'screencap', '-p', '/sdcard/screen.png'],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"[ADB] Chụp màn hình thất bại: {result.stderr.decode()}")
            return None

        # Pull về máy
        result = subprocess.run(
            [*base_adb, 'pull', '/sdcard/screen.png', save_path],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"[ADB] Pull file thất bại: {result.stderr.decode()}")
            return None

        # Xoá file tạm
        subprocess.run([*base_adb, 'shell', 'rm', '/sdcard/screen.png'], capture_output=True)

        img = cv.imread(save_path)
        if img is None:
            print(f"[ADB] Không đọc được ảnh: {save_path}")
        return img