import os
import math
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from time import sleep, time
import cv2 as cv
import sys

from utils.image_processor import ImageProcessor
from utils.adb_control import AdbHelper

# ============================================================
# CONFIGURATION
# ============================================================
DEBUG = False
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "best.pt")
screen_path = os.path.join(current_dir, "screen.png")

# Bot settings
VELOCITY       = 180    
MOVE_WAIT      = 0.12   
DIG_BURST      = 2      
DIG_INTERVAL   = 0.02   
DIG_TIMEOUT    = 5.0    
SCAN_INTERVAL  = 0.05   
CAMPFIRE_RADIUS = 250   # Bán kính vùng trại lửa (Điều chỉnh nếu cần)

class BotThread(threading.Thread):
    def __init__(self, image_processor, adb_control, gui_app):
        super().__init__()
        self.image_processor = image_processor
        self.adb_control = adb_control
        self.gui_app = gui_app
        self.running = True
        self.daemon = True

    def run(self):
        print("[BOT] Thread started.")
        while self.running:
            try:
                # Kiểm tra trạng thái từ GUI: Chạy nếu một trong hai nút được tích
                is_auto = self.gui_app.auto_dig_var.get()
                is_campfire = self.gui_app.campfire_var.get()
                
                if not is_auto and not is_campfire:
                    self.gui_app.set_status("Tạm dừng...")
                    sleep(0.5)
                    continue

                # --- Lấy ảnh màn hình ---
                self.gui_app.set_status("Đang quét màn hình...")
                if DEBUG:
                    ss = cv.imread(screen_path)
                else:
                    ss = self.adb_control.get_screenshot()

                if ss is None:
                    sleep(0.3)
                    continue

                # --- Tìm mục tiêu ---
                self.gui_app.set_status("Đang quét màn hình...")
                campfire_mode = self.gui_app.campfire_var.get()
                result = self.image_processor.find_target(ss, campfire_mode, CAMPFIRE_RADIUS)
                
                if result is None:
                    if campfire_mode:
                        self.gui_app.set_status("Không thấy đá trong vùng trại lửa...")
                    else:
                        self.gui_app.set_status("Không thấy mục tiêu...")
                    sleep(SCAN_INTERVAL)
                    continue

                f_point, t_point, duration, target_center, target_class = result
                self.gui_app.set_status(f"Mục tiêu: {target_class}")
                print(f"[TARGET] {target_class} @ {target_center} | {int(duration)}ms")

                # --- Di chuyển ---
                if not DEBUG:
                    self.adb_control.swipe(f_point, t_point, int(duration))
                
                if MOVE_WAIT > 0:
                    sleep(MOVE_WAIT)

                # --- Đào (Burst Tapping) ---
                dig_start = time()
                
                while True:
                    if not self.gui_app.auto_dig_var.get(): break
                    
                    elapsed = time() - dig_start
                    if elapsed > DIG_TIMEOUT:
                        print(f"[TIMEOUT] Bỏ qua mục tiêu này")
                        break

                    # Thực hiện 1 đợt Burst Tap
                    self.gui_app.set_status(f"Đang đào {target_class}...")
                    for _ in range(DIG_BURST):
                        if not DEBUG:
                            self.adb_control.tap(target_center[0], target_center[1])
                        if DIG_INTERVAL > 0:
                            sleep(DIG_INTERVAL)
                    
                    # Sau burst mới chụp ảnh kiểm tra 1 lần
                    if not DEBUG:
                        ss2 = self.adb_control.get_screenshot()
                    else:
                        ss2 = cv.imread(screen_path)
                        # Trong DEBUG mode giả lập đào xong sau 1 burst
                        sleep(0.5)
                        break

                    if ss2 is not None:
                        if self.image_processor.is_target_cleared(ss2, target_center):
                            print(f"[DONE] Đã xong mục tiêu.")
                            break

            except Exception as e:
                print(f"[ERROR] Logic error: {e}")
                sleep(1)

        print("[BOT] Thread stopped.")

    def stop(self):
        self.running = False

class TreasureHunterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Treasure Hunter Bot")
        self.root.geometry("300x200")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # Style
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TCheckbutton", padding=5)

        # Main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="HUNTER BOT v2.0", font=("Helvetica", 12, "bold"))
        title_label.pack(pady=(0, 10))

        # Checkbox Auto
        self.auto_dig_var = tk.BooleanVar(value=False)
        self.auto_check = ttk.Checkbutton(
            main_frame, 
            text="Auto đào đá", 
            variable=self.auto_dig_var
        )
        self.auto_check.pack(pady=5)

        # Checkbox Trại Lửa
        self.campfire_var = tk.BooleanVar(value=False)
        self.campfire_check = ttk.Checkbutton(
            main_frame, 
            text="Auto đào đá trại lửa", 
            variable=self.campfire_var
        )
        self.campfire_check.pack(pady=5)

        # Status Line
        self.status_var = tk.StringVar(value="Đang đợi lệnh...")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=10)

        # Exit Button
        self.exit_btn = ttk.Button(main_frame, text="Exit", command=self.on_exit)
        self.exit_btn.pack(side=tk.BOTTOM, pady=5)

        # Logic initialization
        self.init_logic()

    def init_logic(self):
        if not os.path.exists(model_path):
            messagebox.showerror("Lỗi", f"Không thấy model tại: {model_path}")
            sys.exit(1)

        self.image_processor = ImageProcessor(model_path, VELOCITY)
        self.adb_control = AdbHelper()

        # Khởi chạy bot thread nhưng ở trạng thái chờ (auto_dig_var = False)
        self.bot_thread = BotThread(self.image_processor, self.adb_control, self)
        self.bot_thread.start()

    def set_status(self, text):
        self.status_var.set(text)

    def on_toggle_auto(self):
        if self.auto_dig_var.get():
            print("[GUI] Auto ON")
        else:
            print("[GUI] Auto OFF")

    def on_exit(self):
        if messagebox.askokcancel("Thoát", "Bạn muốn tắt Bot?"):
            self.bot_thread.stop()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TreasureHunterGUI(root)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    
    root.mainloop()