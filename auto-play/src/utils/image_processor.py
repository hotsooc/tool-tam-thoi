import cv2 as cv
from ultralytics import YOLO
import math

# ============================================================
# CLASS IDs từ model YOLO
# ============================================================
CLASS_NAMES = {
    0: 'ad',
    1: 'astromophy',   # quái
    2: 'blood_bottle',
    3: 'earth_square', # ĐẤT → cần đào
    4: 'grass',
    5: 'gray_square',  # ĐÁ → cần đào
    6: 'green_square', # XANH → đã đào xong
    7: 'mosqui',       # quái
    8: 'mouse',        # quái
    9: 'player',       # nhân vật
    10: 'tree',
    11: 'turtle',      # quái
}

# Class cần đào
DIG_CLASSES = {3, 5}  # earth_square, gray_square

# Class đã đào xong (nền xanh)
CLEARED_CLASS = 6  # green_square

# Class bỏ qua hoàn toàn
IGNORE_CLASSES = {0, 2, 4, 6, 9, 10}  # ad, blood_bottle, grass, green_square, player, tree


class ImageProcessor:

    def __init__(self, model_path, velocity=250):
        self.model = YOLO(model=model_path)
        self.velocity = velocity

    def find_target_and_player(self, img, campfire_mode=False, campfire_radius=250, prev_target=None):
        """
        Tìm (player_box, player_center, target_box, target_center, class_name)
        prev_target: Tọa độ (x, y) của mục tiêu cũ để ưu tiên khóa.
        """
        height, width, _ = img.shape
        center_img = (width // 2, height // 2)

        results = self.model(img, conf=0.75)[0]

        targets = []
        player_box = None
        player_center = center_img # fallback nếu ko thấy player

        for r in results.boxes:
            class_id = int(r.cls[0])
            x1, y1, x2, y2 = map(int, r.xyxy[0])
            center = ((x1 + x2) // 2, (y1 + y2) // 2)

            if class_id == 9: # player
                player_box = (x1, y1, x2, y2)
                # Tính chân player (lấy vị trí thấp hơn một chút)
                player_center = ((x1 + x2) // 2, y2 - int((y2 - y1) * 0.2))
                continue

            if class_id not in DIG_CLASSES:
                continue
            
            # Tính khoảng cách từ tâm ảnh cho campfire mode (hoặc từ player tùy ý)
            dist_to_center = self._distance(center_img, center)
            if campfire_mode and dist_to_center > campfire_radius:
                continue

            targets.append({
                'class_id': class_id,
                'class_name': CLASS_NAMES[class_id],
                'center': center,
                'box': (x1, y1, x2, y2),
            })

        if not targets:
            return player_box, player_center, None, None, None

        # --- LOGIC KHÓA MỤC TIÊU (STICKY) ---
        target = None
        if prev_target:
            # Tìm hòn đá cũ trong danh sách mới (cho phép lệch 100px do camera scroll)
            for t in targets:
                if self._distance(t['center'], prev_target) < 100:
                    target = t
                    break
        
        if not target:
            # Nếu ko có mục tiêu cũ, chọn hòn đá gần player nhất
            for t in targets:
                t['distance'] = self._distance(player_center, t['center'])
            target = min(targets, key=lambda x: x['distance'])

        return player_box, player_center, target['box'], target['center'], target['class_name']

    def is_player_on_rock(self, player_box, player_center, target_box):
        """
        Kiếm tra xem chân player đã đứng trúng TÂM viên đá chưa.
        Sử dụng sai số hẹp 15px để đảm bảo đào trúng.
        """
        if not player_box or not target_box:
            return False
            
        px, py = player_center
        tx1, ty1, tx2, ty2 = target_box
        
        t_center_x = (tx1 + tx2) // 2
        t_center_y = (ty1 + ty2) // 2
        
        # CHỈ CHO PHÉP SAI SỐ 15px quanh tâm đá
        if abs(px - t_center_x) < 15 and abs(py - t_center_y) < 15:
            return True
        return False

    def calc_steer_vector(self, img, a, b):
        """
        Tính hướng swipe.
        """
        height, _, _ = img.shape
        joystick_x = int(img.shape[1] * 0.25)
        joystick_y = int(height * 0.80)
        from_point = (joystick_x, joystick_y)

        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return from_point, from_point

        # Nếu ở rất gần (< 50px): Vuốt cực ngắn (60px) để "nhích" vào tâm
        # Nếu ở xa: Vuốt dài (300px) để chạy nhanh
        steer_len = 300 if length > 50 else 60
        
        norm_dx = (dx / length) * steer_len
        norm_dy = (dy / length) * steer_len
        to_point = (int(from_point[0] + norm_dx), int(from_point[1] + norm_dy))
        
        return from_point, to_point

    def is_target_cleared(self, img, target_center, radius=50):
        """
        Xác nhận đào xong dựa trên màu Đất Xanh (6).
        """
        results = self.model(img, conf=0.6)[0]
        found_rock = False
        found_green = False

        for r in results.boxes:
            class_id = int(r.cls[0])
            x1, y1, x2, y2 = map(int, r.xyxy[0])
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            dist = self._distance(center, target_center)

            if dist < radius:
                if class_id in {3, 5}: # Còn đá
                    found_rock = True
                if class_id == 6:     # Đã thành đất xanh
                    found_green = True

        # Ưu tiên thấy đất xanh là đào xong
        if found_green: return True
        # Nếu vẫn thấy đá thì chắc chắn chưa xong
        if found_rock: return False
        
        # Nếu ko thấy gì (có thể nhân vật che), coi như chưa xong để bot đứng lại chờ thêm 1-2 frame
        return False

    def _distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)