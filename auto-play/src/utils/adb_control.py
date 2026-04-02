import os
import subprocess
import cv2 as cv

# Đường dẫn tới adb.exe của LDPlayer
ADB_PATH = r"F:\LDPlayer\LDPlayer9\adb.exe"

class AdbHelper:
    def __init__(self, device_id=None):
        self.device_id = device_id
        
    def tap(self, x, y):
        self.shell(['input', 'tap', str(x), str(y)])
        
    def swipe(self, f_point, t_point, duration):
        (x1, y1) = f_point
        (x2, y2) = t_point
        self.shell(['input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)])
        
    def shell(self, cmd_args):
        base_cmd = [ADB_PATH]
        if self.device_id:
            base_cmd.extend(['-s', self.device_id])
        base_cmd.append('shell')
        base_cmd.extend(cmd_args)
        return subprocess.run(base_cmd, capture_output=True, text=True)

    def get_screen_size(self):
        result = self.shell(['wm', 'size'])
        return result.stdout if result else ""
    
    def get_screen_density(self):
        result = self.shell(['wm', 'density'])
        return result.stdout if result else ""
    
    def get_screen_resolution(self):
        result = self.shell(['wm', 'display'])
        return result.stdout if result else ""
    
    def get_screenshot(self):
        # Lưu screen.png cùng thư mục với file adb_control.py (tránh đọc ảnh cũ)
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screen.png')

        base_adb = [ADB_PATH]
        if self.device_id:
            base_adb.extend(['-s', self.device_id])

        # Chụp màn hình trên thiết bị
        result = subprocess.run(
            [*base_adb, 'shell', 'screencap', '-p', '/sdcard/screen.png'],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"[ADB] Chup man hinh that bai: {result.stderr.decode()}")
            return None

        # Pull về máy
        result = subprocess.run(
            [*base_adb, 'pull', '/sdcard/screen.png', save_path],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"[ADB] Pull file that bai: {result.stderr.decode()}")
            return None

        # Xoá file tạm trên thiết bị
        subprocess.run([*base_adb, 'shell', 'rm', '/sdcard/screen.png'], capture_output=True)

        # Đọc ảnh
        img = cv.imread(save_path)
        if img is None:
            print(f"[ADB] Khong doc duoc anh tu: {save_path}")
        return img