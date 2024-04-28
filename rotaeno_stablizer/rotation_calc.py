from collections import deque

import numpy as np


class RotationCalc:
    """通过画面计算旋转角度"""

    def __init__(self, version: int = 2, window_size: int=3, ratio: int = 1) -> None:
        if version not in [1, 2]:
            raise ValueError("Unsupport Rotation Version")
        self.window_size = window_size
        self.deque = deque(maxlen=self.window_size)
        self.method = self.compute_rotation_v2 if version == 2 else self.compute_rotation
        self.wake_up_num = (self.window_size - 1) // 2
        self.ratio = ratio
        self.O = int(5 * ratio)
        self.S = int(3 * ratio)

    def get_points(
        self, frame: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # Sample colors

        bottom_left = frame[-self.O:-self.O + self.S, self.O:self.O + self.S].mean(axis=(0, 1))
        top_left = frame[self.O:self.O + self.S, self.O:self.O + self.S].mean(axis=(0, 1))
        bottom_right = frame[-self.O:-self.O + self.S, -self.O:-self.O + self.S].mean(axis=(0, 1))
        top_right = frame[self.O:self.O + self.S, -self.O:-self.O + self.S].mean(axis=(0, 1))
        return (top_left, top_right, bottom_left, bottom_right)

    def compute_rotation(self, left: np.ndarray, right: np.ndarray,
                         center: np.ndarray,
                         sample: np.ndarray) -> float:
        """V1 旋转计算方法（From https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer）"""
        center_dist = np.linalg.norm(
            np.array(center) - np.array(sample))
        left_length = np.linalg.norm(
            np.array(left) - np.array(center))
        left_dist = np.linalg.norm(np.array(left) - np.array(sample))
        right_dist = np.linalg.norm(
            np.array(right) - np.array(sample))

        dir_ = -1 if left_dist < right_dist else 1
        if left_length == 0:
            angle = 180.0
        else:
            angle = float((center_dist - left_length) / left_length *
                          180 * dir_ + 180)

        return -angle

    def compute_rotation_v2(self, top_left: np.ndarray,
                            top_right: np.ndarray,
                            bottom_left: np.ndarray,
                            bottom_right: np.ndarray) -> float:
        """V2 旋转计算方法"""
        # 将二进制颜色值转换为角度
        color_to_degree_matrix = np.array([[2048, 1024, 512],
                                           [256, 128, 64],
                                           [32, 16, 8], 
                                           [4, 2, 1]])
        color_matrix = np.vstack(
            (np.where(top_left >= 127.5, 1, 0), 
             np.where(top_right >= 127.5, 1, 0),
             np.where(bottom_left >= 127.5, 1, 0), 
             np.where(bottom_right >= 127.5, 1, 0)
            ))

        color_to_degree = np.sum(color_to_degree_matrix *
                                 color_matrix)
        rotation_degree = color_to_degree / 4096 * -360

        assert isinstance(rotation_degree, float)
        return -rotation_degree

    def wake_up(self, frames: list[np.ndarray]):
        """获取足够多的参数"""
        if len(frames) != self.wake_up_num:
            raise ValueError("Wrong angle count")
        angle = self.method(*self.get_points(frames[0][:,:,:3]))
        self.deque.append((angle - 360) if angle > 180 else angle)
        for frame in frames[1:]:
            angle = self.method(*self.get_points(frame[:,:,:3]))
            if abs(angle - self.deque[-1]) > 180:
                self.deque.append(angle - 360)
            else:
                self.deque.append(angle)

    def update(self, frame: np.ndarray | None = None) -> float:
        """更新数据，并返回平滑后的数据"""
        if frame is None:
            self.deque.popleft()
        else:
            angle = self.method(*self.get_points(frame[:,:,:3]))
            if abs(angle - self.deque[-1]) > 180:
                self.deque.append(angle - 360)
            else:
                self.deque.append(angle)
        return sum(self.deque) / len(self.deque)
