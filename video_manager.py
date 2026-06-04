import cv2

class VideoManager:

    def __init__(self):
        self.camera_1 = None
        self.camera_2 = None

        self.front_camera_source = 0
        self.side_camera_source = 1

    def connect_camera(self, source):
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            return None

        ret, frame = cap.read()

        if not ret:
            cap.release()
            return None

        return cap

    def connect_single_camera(self, source):
        self.release_all()

        self.camera_1 = self.connect_camera(source)

        return self.camera_1 is not None

    def connect_dual_cameras(self, source_1, source_2):
        self.release_all()

        self.camera_1 = self.connect_camera(source_1)
        self.camera_2 = self.connect_camera(source_2)

        return (
            self.camera_1 is not None
            and self.camera_2 is not None
        )

    def release_all(self):
        if self.camera_1:
            self.camera_1.release()

        if self.camera_2:
            self.camera_2.release()

        self.camera_1 = None
        self.camera_2 = None

    def is_single_camera_ready(self):
        return self.camera_1 is not None

    def is_dual_camera_ready(self):
        return (
                self.camera_1 is not None
                and self.camera_2 is not None
        )

    def get_front_camera_source(self):
        return self.front_camera_source

    def get_side_camera_source(self):
        return self.side_camera_source