import os
import subprocess
import cv2 as cv
import numpy as np


def _load_config():
    adb_path = "adb"
    device_id = "127.0.0.1:5555"

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
        print(f"[CONFIG] ADB={adb_path} | Device={device_id}")
    else:
        adb_path = os.environ.get("ADB_PATH", adb_path)
        device_id = os.environ.get("DEVICE_ID", device_id)
        print(f"[CONFIG] Dùng mặc định: ADB={adb_path} | Device={device_id}")

    return adb_path, device_id


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
        """
        Dùng exec-out để đọc ảnh thẳng từ stdout — không cần pull file,
        nhanh hơn screencap+pull khoảng 2-3 lần.
        """
        base_adb = [self.adb]
        if self.device_id:
            base_adb.extend(['-s', self.device_id])

        try:
            result = subprocess.run(
                [*base_adb, 'exec-out', 'screencap', '-p'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0 or not result.stdout:
                print(f"[ADB] exec-out thất bại, thử fallback...")
                return self._get_screenshot_fallback()

            # Decode PNG bytes thẳng từ stdout
            img_array = np.frombuffer(result.stdout, dtype=np.uint8)
            img = cv.imdecode(img_array, cv.IMREAD_COLOR)

            if img is None:
                print("[ADB] Decode ảnh thất bại, thử fallback...")
                return self._get_screenshot_fallback()

            return img

        except subprocess.TimeoutExpired:
            print("[ADB] Timeout, thử fallback...")
            return self._get_screenshot_fallback()

    def _get_screenshot_fallback(self):
        """
        Fallback: dùng screencap + pull (chậm hơn nhưng ổn định hơn).
        """
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screen.png')
        base_adb = [self.adb]
        if self.device_id:
            base_adb.extend(['-s', self.device_id])

        subprocess.run([*base_adb, 'shell', 'screencap', '-p', '/sdcard/screen.png'], capture_output=True)
        result = subprocess.run([*base_adb, 'pull', '/sdcard/screen.png', save_path], capture_output=True)
        if result.returncode != 0:
            print(f"[ADB] Fallback cũng thất bại!")
            return None
        subprocess.run([*base_adb, 'shell', 'rm', '/sdcard/screen.png'], capture_output=True)

        img = cv.imread(save_path)
        return img