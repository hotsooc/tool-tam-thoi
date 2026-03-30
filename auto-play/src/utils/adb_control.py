import subprocess
import cv2 as cv
import time
import os

class AdbHelper:
    def __init__(self, device_id=None):
        # Tự động tìm thư mục adb của LDPlayer nếu không có trong PATH
        self.adb_path = r"F:\LDPlayer\LDPlayer9\adb.exe" if os.path.exists(r"F:\LDPlayer\LDPlayer9\adb.exe") else "adb"
        
        self.device_id = device_id
        if not self.device_id:
            self.device_id = self.auto_detect_device()
            
    def auto_detect_device(self):
        # Thu tu dong ket noi toi cong mac dinh cua LDPlayer
        subprocess.run([self.adb_path, 'connect', '127.0.0.1:5555'], capture_output=True)
        # Quet thu xem co device nao khong
        result = subprocess.run([self.adb_path, 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:] # Bo qua dong 'List of devices attached'
        for line in lines:
            if 'device' in line and 'offline' not in line:
                return line.split()[0]
        return None # Khong tim thay

    def tap(self, x, y):
        self.shell(['input', 'tap', str(x), str(y)])
        
    def swipe(self, f_point, t_point, duration):
        (x1, y1) = f_point
        (x2, y2) = t_point
        self.shell(['input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)])
        
    def shell(self, cmd_args):
        # cmd_args phải là một list
        base_cmd = [self.adb_path]
        if self.device_id:
            base_cmd.extend(['-s', self.device_id])
        base_cmd.append('shell')
        base_cmd.extend(cmd_args)
        
        # Dùng subprocess.run để thực thi an toàn
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
        # Capture screen, pull and remove. Using adb directly, not via shell.
        base_adb = [self.adb_path]
        if self.device_id:
            base_adb.extend(['-s', self.device_id])
            
        subprocess.run([*base_adb, 'shell', 'screencap', '-p', '/sdcard/screen.png'], capture_output=True)
        subprocess.run([*base_adb, 'pull', '/sdcard/screen.png'], capture_output=True)
        subprocess.run([*base_adb, 'shell', 'rm', '/sdcard/screen.png'], capture_output=True)
        return cv.imread('screen.png')
