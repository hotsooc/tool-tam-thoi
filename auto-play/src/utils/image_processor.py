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

    def find_target_and_player(self, img, campfire_mode=False, campfire_radius=250):
        """
        Tìm (player_box, player_center, target_box, target_center, class_name)
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

        # Sắp xếp targets theo khoảng cách tới player
        for t in targets:
            t['distance'] = self._distance(player_center, t['center'])
            
        target = min(targets, key=lambda x: x['distance'])

        return player_box, player_center, target['box'], target['center'], target['class_name']

    def is_player_on_rock(self, player_box, player_center, target_box):
        """
        Đánh giá chân player đã đè vào vùng diện tích của viên đá chưa.
        target_box: (x1, y1, x2, y2)
        """
        if not player_box or not target_box:
            return False
            
        px, py = player_center
        tx1, ty1, tx2, ty2 = target_box
        
        # Mở rộng bounding box đá một chút để tolerance
        padding = 10
        tx1 -= padding; ty1 -= padding
        tx2 += padding; ty2 += padding
        
        # Kiểm tra chân player có nằm trong vùng đá mở rộng không
        if tx1 <= px <= tx2 and ty1 <= py <= ty2:
            return True
        return False

    def calc_steer_vector(self, img, a, b):
        """
        Tính hướng swipe nhưng vuốt thật xa để dùng cho swipe_async (Chạy như bay).
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

        # Vuốt lố hẳn ra 300px để nhân vật max speed
        norm_dx = (dx / length) * 300
        norm_dy = (dy / length) * 300
        to_point = (int(from_point[0] + norm_dx), int(from_point[1] + norm_dy))
        
        return from_point, to_point

    def is_target_cleared(self, img, target_center, radius=40):
        """
        Kiểm tra xem vị trí target_center đã trở thành green_square chưa.
        Quét các object trong vùng bán kính `radius` quanh điểm đó.
        """
        results = self.model(img, conf=0.6)[0]

        for r in results.boxes:
            class_id = int(r.cls[0])
            x1, y1, x2, y2 = map(int, r.xyxy[0])
            center = ((x1 + x2) // 2, (y1 + y2) // 2)

            # Nếu vị trí gần target mà là green_square → đào xong
            if class_id == CLEARED_CLASS:
                if self._distance(center, target_center) < radius:
                    return True

            # Nếu vẫn còn earth/gray tại vị trí đó → chưa xong
            if class_id in DIG_CLASSES:
                if self._distance(center, target_center) < radius:
                    return False

        # Không tìm thấy gì tại vị trí đó → coi như đào xong
        return True

    def _distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)