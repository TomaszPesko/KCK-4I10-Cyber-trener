import cv2


class VideoManager:
    def __init__(self):
        self.camera_1 = None
        self.camera_2 = None

    def connect_camera(self, source):
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
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