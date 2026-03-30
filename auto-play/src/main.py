import os
import math
from pathlib import Path
from time import sleep
import cv2 as cv
from PIL import Image

from utils.capture_window import WindowCapture
from utils.image_processor import ImageProcessor
from utils.adb_control import AdbHelper

window_name = "LDPlayer"

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

# Tự động lấy đường dẫn cùng cấp với thư mục chứa file main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "best.pt")

velocity = 80
sleep_time = 2.5
scale  = 1.0

window_capture = WindowCapture(window_name, scale)
image_processor = ImageProcessor(model_path, velocity)
adb_control = AdbHelper("emulator-5554")

MAX_RADIUS = 3000 # Giới hạn 3000 pixel ảo trong game (~20-30 lần vuốt)
tether = VirtualTether(MAX_RADIUS)

print("Bot started...")

while(True):
    try:
        if cv.waitKey(1) == ord('q'):
            cv.destroyAllWindows()
            break
            
        ss = adb_control.get_screenshot()
        if ss is None:
            print("Failed to capture screen, retrying...")
            sleep(1)
            continue
            
        # Thử tìm kiếm và vuốt mục tiêu
        try:
            f_point, t_point, duration, move_vector = image_processor.process_image(ss)
            
            # Ghi nhận khoảng cách vào Dây Xích Ảo
            tether.add_movement(move_vector[0], move_vector[1])
            
            if tether.is_out_of_bounds():
                print(f"[{int(tether.get_distance())}/{MAX_RADIUS}] CANH BAO: Vuot khoang cach an toan! Tu dong quay ve...")
                # Tạo lệnh vuốt ngược lại với chiều của vị trí hiện tại
                # Vector từ hiện tại về (0,0) là (-x, -y)
                reverse_dx, reverse_dy = -tether.x, -tether.y
                length = math.sqrt(reverse_dx**2 + reverse_dy**2)
                
                # Chiều dài cố định của 1 cú vuốt thường là ~50-80px như bộ tính toán
                norm_dx = (reverse_dx / length) * 80
                norm_dy = (reverse_dy / length) * 80
                
                reverse_t_point = (int(f_point[0] + norm_dx), int(f_point[1] + norm_dy))
                
                adb_control.swipe(f_point, reverse_t_point, 1000)
                
                # Trừ dần khoảng cách đã lùi về
                tether.add_movement(norm_dx, norm_dy)
            else:
                # Đánh quái bình thường
                adb_control.swipe(f_point, t_point, int(duration))    
                print(f"Normal Swipe from {f_point} to {t_point} | Current roaming: {int(tether.get_distance())}/{MAX_RADIUS}")
                
        except Exception as e:
            # Nếu không tìm thấy target hoặc lỗi nội bộ, bot sẽ nghỉ một chút thay vì crash
            print(f"Skipping frame (no target or error): {e}")

        # Chụp màn hình để log (có thể bỏ comment nếu cần)
        # ss = adb_control.get_screenshot()
        # gray_img = cv.cvtColor(ss, cv.COLOR_BGR2GRAY)
        # im = Image.fromarray(gray_img)
        # os.makedirs("images", exist_ok=True)
        # im.save(f"./images/img_{len(os.listdir('images'))}.jpg")
        
        sleep(sleep_time)
        
    except KeyboardInterrupt:
        print("Bot stopped by User.")
        break
    
print('Finished.')