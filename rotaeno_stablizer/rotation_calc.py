import logging
import subprocess
from math import radians
from os import PathLike
from pathlib import Path
from subprocess import PIPE

import numpy as np
from rich.markup import escape

from .ffmpeg import get_ffmpeg

log = logging.getLogger("rich")


class RotationCalc:
    """通过画面计算旋转角度"""

    def __init__(self, version: int = 2, area: int = 8) -> None:
        if version not in [1, 2]:
            raise ValueError("Unsupport Rotation Version")
        self.method = self.compute_rotation_v2 if version == 2 else self.compute_rotation
        self.area = area
        self.color_to_degree_matrix = np.array([[2048, 1024, 512],
                                                [256, 128, 64],
                                                [32, 16, 8],
                                                [4, 2, 1]])

    def compute_rotation(self, input_array: np.ndarray) -> float:
        """V1 旋转计算方法（From https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer）"""

        left, right, center, sample = np.split(input_array, 4, axis=0)
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

    def compute_rotation_v2(self, input_array: np.ndarray) -> float:
        """V2 旋转计算方法"""
        # 将二进制颜色值转换为角度

        reshaped_array = input_array.reshape(self.area, 4, self.area,
                                             3)
        color_matrix = reshaped_array.mean(axis=(0, 2))

        color_to_degree = np.sum(self.color_to_degree_matrix *
                                 (color_matrix >= 127.5))
        rotation_degree = color_to_degree / 4096 * 360

        #assert isinstance(rotation_degree, float)
        return rotation_degree

    def export_ffmpeg_cmd(self,
                          video_name: PathLike | str,
                          fps: float | None = None,
                          codec: str | None = None):
        commands = []
        if codec is not None:
            commands += ["-c:v", codec]
        commands += ["-i", video_name]

        cs = self.area
        commands.append("-filter_complex")
        commands.append(
            "[0:v]split=4[top_left][top_right][bottom_left][bottom_right];"
        )

        commands[-1] += (
            f"[top_left]crop={cs}:{cs}:0:0[top_left];"
            f"[top_right]crop={cs}:{cs}:iw-{cs}:0[top_right];"
            f"[bottom_left]crop={cs}:{cs}:0:ih-{cs}[bottom_left];"
            f"[bottom_right]crop={cs}:{cs}:iw-{cs}:ih-{cs}[bottom_right];"
            "[top_left][top_right][bottom_left][bottom_right]hstack=inputs=4"
            f"{f',fps={fps}' if fps is not None else ''}[rotation];")

        commands += [
            "-map", "[rotation]", "-f", "rawvideo", "-pix_fmt",
            "rgb24", "pipe:"
        ]

        return commands

    def export_cmd(self,
                   video_name: str | PathLike,
                   fps: float,
                   codec: str | None = None):
        cmd = self.export_ffmpeg_cmd(video_name, fps, codec)
        commands = [get_ffmpeg(), "-loglevel", "error", *cmd]

        height, width = self.area * 4, self.area
        frame_size = height * width * 3
        pipe = subprocess.Popen(commands,
                                stdout=PIPE,
                                stderr=PIPE,
                                bufsize=frame_size + 1)
        log.debug("Running Commands: [bold green]" +
                  escape(" ".join(map(str, commands))),
                  extra={"markup": True})
        stdout = pipe.stdout
        assert stdout is not None
        i = 0
        while pipe.poll() is None:
            frame_raw = stdout.read(frame_size)
            frame = np.frombuffer(frame_raw, dtype=np.uint8)
            if frame.size == 0: break
            rotate = self.method(frame.reshape((height, width, 3)))
            i_then = i + 1 / fps
            yield f"{i}-{i_then} rotate angle {radians(rotate)};"
            i = i_then
            stdout.flush()
        pipe.wait()


if __name__ == "__main__":
    test = RotationCalc()
    for line in test.export_cmd(
            r"E:\Code\py-rotaeno-stablizer-gui\test\test_5s.mp4", 60):
        print(line)
