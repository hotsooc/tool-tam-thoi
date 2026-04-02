import os
import math
from time import sleep
import cv2 as cv

from utils.image_processor import ImageProcessor
from utils.adb_control import AdbHelper

DEBUG = False

class VirtualTether:
    def __init__(self, max_radius):
        self.x = 0.0
        self.y = 0.0
        self.max_radius = max_radius
        
    def add_movement(self, dx, dy):
        self.x += dx
        self.y += dy
        
    def get_distance(self):
        return math.sqrt(self.x**2 + self.y**2)
        
    def is_out_of_bounds(self):
        return self.get_distance() > self.max_radius

    def reset_position(self):
        self.x = 0.0
        self.y = 0.0

current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "best.pt")
screen_path = os.path.join(current_dir, "screen.png")

velocity = 150
sleep_time = 1

image_processor = ImageProcessor(model_path, velocity)
adb_control = AdbHelper("127.0.0.1:5555")

MAX_RADIUS = 3000
tether = VirtualTether(MAX_RADIUS)

if not os.path.exists(model_path):
    print(f"[LỖI] Không tìm thấy model: {model_path}")
    print("      Hãy copy file best.pt vào thư mục auto-play/src/")
    exit(1)

if DEBUG:
    if not os.path.exists(screen_path):
        print(f"[LỖI] Không tìm thấy ảnh debug: {screen_path}")
        print("      Hãy đặt 1 ảnh chụp màn hình game vào auto-play/src/screen.png")
        exit(1)
    print(f"[DEBUG] Đang chạy với ảnh tĩnh: {screen_path}")
else:
    print(f"[LIVE] Đang chạy với ADB device: ")

print("Bot started...")
print("Nhấn Ctrl+C để thoát\n")

while True:
    try:
        if cv.waitKey(1) == ord('q'):
            cv.destroyAllWindows()
            break

        # Lấy ảnh màn hình
        if DEBUG:
            ss = cv.imread(screen_path)
            if ss is None:
                print(f"[LỖI] Không đọc được ảnh: {screen_path}")
                break
        else:
            ss = adb_control.get_screenshot()
            if ss is None:
                print("[ADB] Chụp màn hình thất bại, thử lại...")
                sleep(1)
                continue

        print(f"[INFO] Ảnh kích thước: {ss.shape[1]}x{ss.shape[0]}")

        # Xử lý ảnh và tìm mục tiêu
        try:
            f_point, t_point, duration, move_vector = image_processor.process_image(ss)
            tether.add_movement(move_vector[0], move_vector[1])

            if tether.is_out_of_bounds():
                print(f"[TETHER] CẢNH BÁO: Vượt {int(tether.get_distance())}/{MAX_RADIUS}px! Đang quay về...")

                reverse_dx, reverse_dy = -tether.x, -tether.y
                length = math.sqrt(reverse_dx**2 + reverse_dy**2)
                norm_dx = (reverse_dx / length) * 80
                norm_dy = (reverse_dy / length) * 80
                reverse_t_point = (int(f_point[0] + norm_dx), int(f_point[1] + norm_dy))

                if not DEBUG:
                    adb_control.swipe(f_point, reverse_t_point, 1000)
                else:
                    print(f"[DEBUG] Swipe ngược: {f_point} → {reverse_t_point}")

                tether.add_movement(norm_dx, norm_dy)

            else:
                if not DEBUG:
                    adb_control.swipe(f_point, t_point, int(duration))
                print(f"[SWIPE] {f_point} → {t_point} | duration={int(duration)}ms | roaming={int(tether.get_distance())}/{MAX_RADIUS}")

        except Exception as e:
            print(f"[SKIP] Không tìm thấy mục tiêu hoặc lỗi: {e}")

        # Trong DEBUG mode chỉ chạy 1 frame rồi dừng chờ
        if DEBUG:
            print("\n[DEBUG] Xong 1 frame. Nhấn Enter để chạy lại, hoặc Ctrl+C để thoát.")
            input()
        else:
            sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nBot stopped by User.")
        break

print('Finished.')