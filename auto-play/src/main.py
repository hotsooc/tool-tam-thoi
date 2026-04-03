import os
import math
from time import sleep
import cv2 as cv

from utils.image_processor import ImageProcessor
from utils.adb_control import AdbHelper

# ============================================================
# DEBUG MODE
# True  = dùng ảnh tĩnh screen.png, không cần LDPlayer/ADB
# False = chạy thật với ADB
# ============================================================
DEBUG = True

# ============================================================
# SETUP
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "best.pt")
screen_path = os.path.join(current_dir, "screen.png")

VELOCITY = 80       # Tốc độ swipe
DIG_WAIT = 1.2      # Chờ animation đào (giây)
MOVE_WAIT = 0.3     # Chờ nhân vật di chuyển (giây)
# SLEEP_TIME = 2.5  # Delay giữa frame -- TẮT để chạy nhanh nhất

image_processor = ImageProcessor(model_path, VELOCITY)

# Device ID tự động đọc từ config.tmp (do run_bot.bat tạo ra)
# Nếu chạy thủ công không qua bat thì dùng giá trị mặc định trong adb_control.py
adb_control = AdbHelper()  # Không cần truyền device_id, tự đọc từ config

# ============================================================
# KIỂM TRA TRƯỚC KHI CHẠY
# ============================================================
if not os.path.exists(model_path):
    print(f"[LỖI] Không tìm thấy model: {model_path}")
    print("      Hãy copy file best.pt vào thư mục auto-play/src/")
    exit(1)

if DEBUG:
    if not os.path.exists(screen_path):
        print(f"[LỖI] Không tìm thấy ảnh debug: {screen_path}")
        print("      Hãy đặt ảnh chụp màn hình game vào auto-play/src/screen.png")
        exit(1)
    print(f"[DEBUG] Đang chạy với ảnh tĩnh: {screen_path}")
else:
    print(f"[LIVE] Đang chạy với ADB device: {adb_control.device_id}")

print("Bot started! Nhấn Ctrl+C để thoát\n")

# ============================================================
# VÒNG LẶP CHÍNH
# ============================================================
while True:
    try:
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
                sleep(0.5)
                continue

        # Detect mục tiêu
        result = image_processor.find_target(ss)

        if result is None:
            print("[SCAN] Không tìm thấy mục tiêu, quét lại...")
            continue

        f_point, t_point, duration, target_center, target_class = result
        print(f"[TARGET] {target_class} tại {target_center} | swipe {f_point}→{t_point} | {int(duration)}ms")

        # Di chuyển tới mục tiêu
        if not DEBUG:
            adb_control.swipe(f_point, t_point, int(duration))

        sleep(MOVE_WAIT)

        # Tap đào
        if not DEBUG:
            adb_control.tap(target_center[0], target_center[1])

        print(f"[DIG] Đang đào {target_class}... chờ {DIG_WAIT}s")
        sleep(DIG_WAIT)

        # Kiểm tra đào xong chưa
        if not DEBUG:
            ss2 = adb_control.get_screenshot()
        else:
            ss2 = cv.imread(screen_path)

        if ss2 is not None:
            done = image_processor.is_target_cleared(ss2, target_center)
            if done:
                print(f"[DONE] Đào xong! Tìm mục tiêu mới...\n")
            else:
                print(f"[RETRY] Chưa xong, đào thêm...\n")
                if not DEBUG:
                    adb_control.tap(target_center[0], target_center[1])
                sleep(DIG_WAIT * 0.5)

        if DEBUG:
            print("\n[DEBUG] Nhấn Enter để chạy lại, Ctrl+C để thoát.")
            input()

    except KeyboardInterrupt:
        print("\nBot stopped by User.")
        break

print('Finished.')