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

    def __init__(self, model_path, velocity=80):
        self.model = YOLO(model=model_path)
        self.velocity = velocity

    def find_target(self, img):
        """
        Tìm mục tiêu cần đào gần nhất.
        Trả về (from_point, to_point, duration, target_center, class_name)
        hoặc None nếu không tìm thấy.
        """
        height, width, _ = img.shape
        center_img = (width // 2, height // 2)

        results = self.model(img, conf=0.75)[0]

        targets = []
        for r in results.boxes:
            class_id = int(r.cls[0])

            # Chỉ lấy class cần đào
            if class_id not in DIG_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, r.xyxy[0])
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            dist = self._distance(center_img, center)

            targets.append({
                'class_id': class_id,
                'class_name': CLASS_NAMES[class_id],
                'center': center,
                'distance': dist,
                'box': (x1, y1, x2, y2),
            })

        if not targets:
            return None

        # Chọn mục tiêu gần nhất
        target = min(targets, key=lambda x: x['distance'])

        # Tính swipe
        from_point, to_point, duration = self._calc_swipe(img, center_img, target['center'])

        return (from_point, to_point, duration, target['center'], target['class_name'])

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

    def _calc_swipe(self, img, a, b):
        """
        Tính điểm swipe từ vùng joystick (75% chiều cao) hướng về mục tiêu.
        Swipe ngắn cố định 50px để điều khiển nhân vật.
        """
        height, _, _ = img.shape

        # Điểm bắt đầu swipe = vùng joystick (góc dưới trái màn hình)
        joystick_x = int(img.shape[1] * 0.25)  # 25% từ trái
        joystick_y = int(height * 0.80)         # 80% từ trên (vùng joystick)
        from_point = (joystick_x, joystick_y)

        # Hướng từ tâm màn hình tới mục tiêu
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return from_point, from_point, 100

        # Swipe 50px theo hướng mục tiêu
        norm_dx = (dx / length) * 50
        norm_dy = (dy / length) * 50
        to_point = (int(from_point[0] + norm_dx), int(from_point[1] + norm_dy))

        # Duration dựa trên khoảng cách thật
        duration = max(200, length / self.velocity * 1000)

        return from_point, to_point, duration

    def _distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)