import os
from pathlib import Path
from time import sleep
import cv2 as cv
from PIL import Image

from utils.capture_window import WindowCapture
from utils.image_processor import ImageProcessor
from utils.adb_control import AdbHelper

window_name = "LDPlayer"

# Tự động lấy đường dẫn cùng cấp với thư mục chứa file main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "best.pt")

velocity = 80
sleep_time = 2.5
scale  = 1.0

window_capture = WindowCapture(window_name, scale)
image_processor = ImageProcessor(model_path, velocity)
adb_control = AdbHelper("emulator-5554")

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
            f_point, t_point, duration = image_processor.process_image(ss)
            adb_control.swipe(f_point, t_point, int(duration))    
            print("Swipe from {} to {} in {} ms".format(f_point, t_point, int(duration)))
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