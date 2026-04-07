import os
import math
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from time import sleep
import time as ptime
import cv2 as cv
import sys
import datetime

# Global reference cho GUI để logger có thể truy cập
gui_instance = None


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
MOVE_WAIT      = 0.0   # Bỏ hoàn toàn wait sau move
DIG_BURST      = 1     # Đập 1 phát quét 1 hình (vì quét rất nhanh)
DIG_INTERVAL   = 0.0   # Bỏ delay
DIG_TIMEOUT    = 5.0    
SCAN_INTERVAL  = 0.0   # Quét full speed
CAMPFIRE_RADIUS = 250   # Bán kính vùng trại lửa

def custom_log(msg):
    # Log kèm timestamp millisecond
    now = datetime.datetime.now()
    timestamp = now.strftime("%H:%M:%S.%f")[:-3]
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    
    # Cập nhật lên giao diện nếu người dùng bật tích
    if gui_instance and gui_instance.logging_var.get():
        gui_instance.update_log_display(full_msg)



class BotThread(threading.Thread):
    def __init__(self, image_processor, adb_control, gui_app):
        super().__init__()
        self.image_processor = image_processor
        self.adb_control = adb_control
        self.gui_app = gui_app
        self.running = True
        self.daemon = True
        self.is_digging = False        # Đang đứng yên đào
        self.target_locked_pos = None  # Tâm của hòn đá đang khóa
        self.t_start_dig = 0           # Thời điểm bắt đầu đào

    def run(self):
        custom_log("[BOT] Thread started.")
        while self.running:
            try:
                # Kiểm tra trạng thái từ GUI: Chạy nếu một trong hai nút được tích
                is_auto = self.gui_app.auto_dig_var.get()
                is_campfire = self.gui_app.campfire_var.get()
                
                if not is_auto and not is_campfire:
                    self.gui_app.set_status("Tạm dừng...")
                    sleep(0.5)
                    continue

                # --- 1. LẤY ẢNH (MAX SPEED) ---
                t_start = ptime.perf_counter()
                if DEBUG:
                    ss = cv.imread(screen_path)
                else:
                    ss = self.adb_control.get_screenshot()

                t_img = ptime.perf_counter() - t_start

                if ss is None:
                    custom_log("[ERROR] Lỗi không lấy được ảnh màn hình.")
                    sleep(0.1)
                    continue

                # --- 2. XỬ LÝ KHI ĐANG ĐÀO (LOCK & DIG) ---
                if self.is_digging and self.target_locked_pos:
                    # Kiểm tra xem đất đã xanh chưa (xác nhận đào xong)
                    is_cleared = self.image_processor.is_target_cleared(ss, self.target_locked_pos)
                    elapsed = ptime.perf_counter() - self.t_start_dig
                    
                    # Nếu đã thấy đất xanh HOẶC đứng quá 3s (đề phòng AI check sai)
                    if is_cleared or elapsed > 3.0:
                        custom_log(f"[DIG] Đã đào xong mục tiêu sau {elapsed:.1f}s. Reset tìm mỏ mới.")
                        self.is_digging = False
                        self.target_locked_pos = None
                        continue
                    else:
                        self.gui_app.set_status(f"Đang đào... ({elapsed:.1f}s)")
                        # Không phát lệnh di chuyển, nhân vật tự đào
                        sleep(0.1)
                        continue

                # --- 3. TÌM MỤC TIÊU & PLAYER (HÀNH TRÌNH CHUYÊN TÂM) ---
                campfire_mode = self.gui_app.campfire_var.get()

                # BƯỚC A: Nếu chưa có mục tiêu khóa -> Quét toàn màn hình để chọn hòn gần nhất
                if self.target_locked_pos is None:
                    p_box, p_center, t_box, t_center, t_class = \
                        self.image_processor.find_target_and_player(ss, campfire_mode, CAMPFIRE_RADIUS)
                    
                    if t_center is None:
                        self.gui_app.set_status("Đang quét tìm Mỏ Đá...")
                        continue
                    
                    # KHÓA CHẶT MỤC TIÊU NÀY
                    self.target_locked_pos = t_center
                    custom_log(f"[LOCK] Đã chọn mỏ {t_class} tại {t_center}. Bắt đầu lao tới!")
                
                # BƯỚC B: Khi đã có mục tiêu -> Chỉ quét để xác định vị trí mình và hòn đá đó
                p_box, p_center, t_box, t_center, t_class = \
                    self.image_processor.find_target_and_player(ss, prev_target=self.target_locked_pos)
                
                if t_center is None:
                    # Lạc mất mục tiêu cũ (camera trượt quá nhanh hoặc đá vỡ sớm) -> Reset
                    self.target_locked_pos = None
                    continue

                # Tính khoảng cách chân nhân vật -> tâm hòn đá
                dist = math.sqrt((p_center[0]-t_center[0])**2 + (p_center[1]-t_center[1])**2)

                # --- 4. KIỂM TRA ĐÃ TỚI TÂM CHƯA ---
                if self.image_processor.is_player_on_rock(p_box, p_center, t_box):
                    # ĐÃ TỚI TÂM ĐÁ -> PHANH LẠI NGAY
                    self.gui_app.set_status("Đã tới tâm. Phanh!")
                    custom_log(f"[STOP] Tới tâm đá (Cách {dist:.0f}px). Phanh khẩn cấp để đào.")
                    
                    if not DEBUG:
                        # Vị trí nhân vật mặc định ở giữa màn hình (400, 240)
                        # Tap vào đây sẽ làm nhân vật đứng khựng lại
                        self.adb_control.tap(400, 240)
                    
                    self.is_digging = True
                    self.t_start_dig = ptime.perf_counter()
                else:
                    # CHƯA TỚI -> TIẾP TỤC DI CHUYỂN (KHÔNG quét hòn đá khác)
                    self.gui_app.set_status(f"Lao tới mỏ đã khóa (Còn {dist:.0f}px)...")
                    from_pt, to_pt = self.image_processor.calc_steer_vector(ss, p_center, t_center)
                    
                    if not DEBUG:
                        # Dùng swipe ngắn 400ms để không bị trôi quá lố
                        self.adb_control.swipe_async(from_pt, to_pt, 400)
                    
                    custom_log(f"-> Moving to {self.target_locked_pos} (Dist: {dist:.0f}px)")

            except Exception as e:
                custom_log(f"[ERROR] Logic error: {e}")
                sleep(0.5)

        custom_log("[BOT] Thread stopped.")

    def stop(self):
        self.running = False

class TreasureHunterGUI:
    def __init__(self, root):
        global gui_instance
        gui_instance = self
        
        self.root = root
        self.root.title("Treasure Hunter Bot")
        self.root.geometry("400x500") # Tăng kích thước để chứa log
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)

        # Style
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TCheckbutton", padding=5)

        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="HUNTER BOT v2.1", font=("Helvetica", 12, "bold"))
        title_label.pack(pady=(0, 5))

        # Checkbox Auto
        self.auto_dig_var = tk.BooleanVar(value=False)
        self.auto_check = ttk.Checkbutton(
            main_frame, 
            text="Auto đào đá", 
            variable=self.auto_dig_var
        )
        self.auto_check.pack(fill=tk.X)

        # Checkbox Trại Lửa
        self.campfire_var = tk.BooleanVar(value=False)
        self.campfire_check = ttk.Checkbutton(
            main_frame, 
            text="Auto đào đá trại lửa", 
            variable=self.campfire_var
        )
        self.campfire_check.pack(fill=tk.X)

        # Checkbox Hiển thị Log
        self.logging_var = tk.BooleanVar(value=True)
        self.logging_check = ttk.Checkbutton(
            main_frame, 
            text="Hiển thị Log chi tiết", 
            variable=self.logging_var,
            command=self.toggle_log_display
        )
        self.logging_check.pack(fill=tk.X)


        # Status Line
        self.status_var = tk.StringVar(value="Đang đợi lệnh...")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue", font=("Helvetica", 10, "italic"))
        self.status_label.pack(pady=5)

        # Log Display Area (Wrapped in a frame for easy hiding)
        self.log_frame = ttk.Frame(main_frame)
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(self.log_frame, text="Console Log:").pack(anchor=tk.W)
        self.log_area = scrolledtext.ScrolledText(self.log_frame, height=15, font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=2)
        self.log_area.config(state=tk.DISABLED)

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

    def toggle_log_display(self):
        if self.logging_var.get():
            self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            self.root.geometry("400x500")
        else:
            self.log_frame.pack_forget()
            self.root.geometry("400x200") # Thu nhỏ khi ẩn log

    def update_log_display(self, message):
        # Hàm thread-safe để cập nhật log lên UI
        def append():
            try:
                self.log_area.config(state=tk.NORMAL)
                self.log_area.insert(tk.END, message + "\n")
                self.log_area.see(tk.END) # Tự động cuộn xuống
                self.log_area.config(state=tk.DISABLED)
                
                # Giới hạn số dòng để tránh lag (giữ 100 dòng cuối)
                line_count = int(self.log_area.index('end-1c').split('.')[0])
                if line_count > 105:
                    self.log_area.config(state=tk.NORMAL)
                    self.log_area.delete('1.0', '6.0')
                    self.log_area.config(state=tk.DISABLED)
            except:
                pass

        self.root.after(0, append)

    def on_toggle_auto(self):
        if self.auto_dig_var.get():
            custom_log("[GUI] Auto ON")
        else:
            custom_log("[GUI] Auto OFF")

    def on_exit(self):
        if messagebox.askokcancel("Thoát", "Bạn muốn tắt Bot?"):
            if hasattr(self, 'bot_thread'):
                self.bot_thread.stop()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TreasureHunterGUI(root)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    
    root.mainloop()