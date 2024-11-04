import logging
import subprocess
from math import radians
from os import PathLike
from subprocess import PIPE
from typing import Generator, Any

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

    def compute_rotation(self, input_data: list[int]) -> float:
        """V1 旋转计算方法（From https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer）"""

        left = input_data[0:3]
        right = input_data[3:6]
        center = input_data[6:9]
        sample = input_data[9:12]
        calculate_distance = lambda point1, point2: ((point2[0] - point1[0])**2 +
                                                     (point2[1] - point1[1])**2 +
                                                     (point2[2] - point1[2])**2)**0.5

        center_dist = calculate_distance(center, sample)
        left_length = calculate_distance(left, center)
        left_dist = calculate_distance(left, sample)
        right_dist = calculate_distance(right, sample)

        dir_ = -1 if left_dist < right_dist else 1
        if left_length == 0:
            angle = 180.0
        else:
            angle = float((center_dist - left_length) / left_length * 180 * dir_ + 180)

        return -angle

    def compute_rotation_v2(self, input_data: list[int]) -> float:
        """V2 旋转计算方法"""

        mul_num = 1
        color_to_degree = 0
        for i in reversed(input_data):
            if i > 127.5:
                color_to_degree += mul_num
            mul_num *= 2
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
        commands.append("[0:v]split=4[top_left][top_right][bottom_left][bottom_right];")

        commands[-1] += (
            f"[top_left]crop={cs}:{cs}:0:0,scale=1:1:flags=fast_bilinear[top_left];"
            f"[top_right]crop={cs}:{cs}:iw-{cs}:0,scale=1:1:flags=fast_bilinear[top_right];"
            f"[bottom_left]crop={cs}:{cs}:0:ih-{cs},scale=1:1:flags=fast_bilinear[bottom_left];"
            f"[bottom_right]crop={cs}:{cs}:iw-{cs}:ih-{cs},scale=1:1:flags=fast_bilinear[bottom_right];"
            "[top_left][top_right][bottom_left][bottom_right]hstack=inputs=4"
            f"{f',fps={fps}' if fps is not None else ''}[rotation];")

        commands += [
            "-map", "[rotation]", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"
        ]

        return commands

    def export_num(
        self,
        video_name: str | PathLike,
        fps: float,
        codec: str | None = None
    ) -> Generator[tuple[tuple[float, float], float], Any, None]:
        cmd = self.export_ffmpeg_cmd(video_name, fps, codec)
        commands = [get_ffmpeg(), "-loglevel", "error", *cmd]

        frame_size = 12
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
        import time
        ts = []
        while pipe.poll() is None:
            frame = stdout.read(frame_size)
            if frame == b"": break
            a = time.time()
            rotate = self.method(list(frame))
            ts.append(time.time() - a)
            i_then = i + 1 / fps
            yield (i, i_then), rotate
            i = i_then
            stdout.flush()
        pipe.wait()

    def export_cmd(self,
                   video_name: str | PathLike,
                   fps: float,
                   codec: str | None = None) -> Generator[str, Any, None]:
        for (i, i_then), rotate in self.export_num(video_name, fps, codec):
            yield f"{i}-{i_then} rotate angle {radians(rotate)};"


if __name__ == "__main__":
    test = RotationCalc()
    for line in test.export_cmd(r"test\test_5s.mp4", 60):
        #print(line)
        ...
