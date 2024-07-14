import logging
import math
import threading
import time
import traceback
import urllib.request
from collections import deque
from os import PathLike
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from tkinter.ttk import Progressbar


import cv2
import numpy as np
from rich import get_console
from rich import print as rprint
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from . import ffmpeg
from .rotation_calc import RotationCalc
from .utils import FPSColumn, paste_image

@dataclass
class PaintMsg:
    video_resize: tuple[int, int]
    video_crop: tuple[int, int]
    output_size: tuple[int, int]
    circle_radius: float
    circle_thickness: float
    resize_ratio: float
    background: np.ndarray
    image_alpha: np.ndarray

    def __repr__(self):
        fields = (
            f'{name}={value if not isinstance(value, np.ndarray) else f"array(shape={value.shape})"}'
            for field in self.__dataclass_fields__.values() if field.repr
            for name, value in ((field.name, self.__getattribute__(field.name)),)
            )
        return f'{self.__class__.__name__}({", ".join(fields)})'

FORMAT = "%(message)s"
logging.basicConfig(level="INFO",
                    format=FORMAT,
                    datefmt="[%X]",
                    handlers=[RichHandler(rich_tracebacks=True)])

log = logging.getLogger("rich")


def ceil_even(num: tuple[float, float]) -> tuple[int, int]:
    ceil_single = lambda n: math.ceil(n / 2) * 2
    return (ceil_single(num[0]), ceil_single(num[1]))


class Rotaeno:

    def __init__(self,
                 rotation_version: int = 2,
                 circle_crop: bool = False,
                 auto_crop: bool = True,
                 display_all: bool = True,
                 height: int | None = None,
                 background: str | PathLike | None = None,
                 spectrogram_circle: bool = False,
                 window_size: int = 3):
        """_summary_

        Args:
            rotation_version (int, optional): 使用串流版本. Defaults to 2.
            circle_crop (bool, optional): 是否采用圆形裁切，裁切后，视频将会变为 16:9. Defaults to True.
            auto_crop (bool, optional): 将输入视频裁切成 16:9. Defaults to True.
            display_all (bool, optional): 是否适当缩小视频以保证所有都能看到，开启后视频比例会变为 1:1. Defaults to True.
            height (int | None, optional): 输出视频高度，如为 None，则将由软件自行设置. Defaults to None.
            background (PathLike | None, optional): 背景，默认为纯黑背景. Defaults to None.
            spectrogram_circle (bool, optional): 是否需要带有频谱图的圆圈. Defaults to False.
        """

        self.rotation_method = RotationCalc(rotation_version,
                                            window_size)
        self.circle_crop = circle_crop
        self.auto_crop = auto_crop
        self.spectrogram_circle = spectrogram_circle
        self.display_all = display_all
        self.height = height if height != 0 else None

        if isinstance(background,
                      str) and background.startswith("http"):
            log.debug(f"Downloading {background}")
            with urllib.request.urlopen(background) as f:
                r = f.read()
            background_data = np.frombuffer(r, np.uint8)
            self.background = cv2.imdecode(background_data, 1)
            log.debug(f"Download Success, Size={self.background.shape}")
        elif background is not None:
            background_data = np.fromfile(background, dtype=np.uint8)
            self.background = cv2.imdecode(background_data, 1)
        else:
            self.background = None

        self.con = get_console()

    def generate_background(self, width: int, height: int, r: float,
                            thickness: float) -> np.ndarray:

        brightness = 0.2
        background_np = np.zeros((height, width, 4), dtype=np.uint8)
        if self.background is not None:
            # 为了支持中文路径的操作
            background = cv2.resize(self.background,
                                    (int(r * 2), int(r * 2)))
            background = np.multiply(background, brightness).astype(np.uint8)

            offset_x = int((width - r * 2) / 2)
            offset_y = int((height - r * 2) / 2)

            background_np = paste_image(background_np, background,
                                        offset_x, offset_y)
        cv2.circle(background_np, (width // 2, height // 2),
                   int(r), (255, 255, 255, 255),
                   int(thickness),
                   lineType=cv2.LINE_AA)
        return background_np

    def _get_video_info(self,
                        height: int,
                        width: int,
                        output_height_want: int | None = None):

        aspect_ratio = 16 / 9

        # ciricle radius is from https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer

        if self.auto_crop:
            video_ratio = width / height
            if math.isclose(video_ratio, aspect_ratio, rel_tol=1e-03):
                video_crop = (width, height)
            elif video_ratio < aspect_ratio:
                video_crop = (width, width / aspect_ratio)
            else:  #if video_ratio > aspect_ratio
                video_crop = (height * aspect_ratio, height)
        else:
            video_crop = (width, height)

        if self.display_all:
            video_a = (math.sqrt(video_crop[0]**2 + video_crop[1]**2)
                       if not self.circle_crop else video_crop[0])

        if output_height_want is not None:
            if self.display_all:
                resize_ratio = video_a / output_height_want
                video_a = output_height_want
                video_crop = (video_crop[0] / resize_ratio,
                                video_crop[1] / resize_ratio)
            else:
                resize_ratio = video_crop[1] / output_height_want
                video_crop = (width / resize_ratio,
                                output_height_want)
            video_resize = (width / resize_ratio,
                            height / resize_ratio)
        else:
            resize_ratio = 1
            video_resize = (width, height)

        circle_radius = (1.5575 * video_crop[1]) // 2
        circle_thickness = max(video_crop[1] // 120, 1)

        if self.display_all:
            output_size = (video_a, video_a)
        elif self.circle_crop:
            output_size = video_crop
        else:
            output_size = (math.sqrt(video_crop[0]**2 +
                                     video_crop[1]**2), video_crop[1])

        video_resize = ceil_even(video_resize)
        video_crop = ceil_even(video_crop)
        output_size = ceil_even(output_size)

        if self.circle_crop:
            alpha = np.zeros(video_crop[::-1], dtype=np.uint8)
            alpha = cv2.circle(
                alpha, (video_crop[0] // 2, video_crop[1] // 2),
                video_crop[0] // 2, (255, ),
                thickness=-1,
                lineType=cv2.LINE_AA)
            #print("2", time.time() - t)
        else:

            alpha = np.full(video_crop[::-1], 255, dtype=np.uint8)

        background = self.generate_background(*output_size,
                                              circle_radius,
                                              circle_thickness)


        return PaintMsg(video_resize=video_resize,
                        video_crop=video_crop,
                        output_size=output_size,
                        circle_radius=circle_radius,
                        circle_thickness=circle_thickness,
                        resize_ratio = resize_ratio,
                        background=background,
                        image_alpha=alpha)

    def process_frame(self, frame: np.ndarray, angle: float):
        """

        Args:
            frame (av.VideoFrame): 帧
            height (int): 输出帧高度
            width (int): 输出帧宽度
        """
        height, width = frame.shape[:2]

        if self.paint_msg.video_resize != self.paint_msg.video_crop:
            if self.paint_msg.video_crop[1] != height:
                offset = (height - self.paint_msg.video_crop[1]) // 2
                frame = frame[offset:-offset, :, :]
                height = self.paint_msg.video_crop[1]
            elif self.paint_msg.video_crop[0] != width:
                offset = (width - self.paint_msg.video_crop[0]) // 2
                frame = frame[:, offset:-offset, :]
                width = self.paint_msg.video_crop[0]
        # 绘制圆形 alpha 通道

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
        if self.circle_crop:
            frame[:,:,3] = self.paint_msg.image_alpha

        # 获取变换矩阵
        M = cv2.getRotationMatrix2D(
            (frame.shape[1] // 2, frame.shape[0] // 2), angle, 1)
        M[0, 2] += (self.paint_msg.output_size[0] - width) // 2
        M[1, 2] += (self.paint_msg.output_size[1] - height) // 2
        rotated_frame = cv2.warpAffine(
            frame,
            M,
            self.paint_msg.output_size,
        )
        return rotated_frame

    def process_video(self, input_reader: ffmpeg.FFMpegReader, output_writer: ffmpeg.FFMpegWriter, frame_callback: Callable):
        # 先给稳定器投喂点数据
        wakeup_elems = []
        for _ in range(self.rotation_method.wake_up_num + 1):  # 修正这里的帧数获取
            frame = input_reader.queue.get()
            wakeup_elems.append(frame)
            input_reader.queue.task_done()
        self.rotation_method.wake_up(wakeup_elems)
        angle_deque = deque(wakeup_elems, maxlen=self.rotation_method.window_size)

        for f in input_reader.read():
            if f is None:
                break
            angle_deque.append(f)
            angle = self.rotation_method.update(f)
            a = self.process_frame(angle_deque[self.rotation_method.wake_up_num], angle)
            output_writer.queue.put(a)
            frame_callback()
        for f in range(self.rotation_method.wake_up_num):
            output_writer.queue.put(self.process_frame(angle_deque.popleft(), self.rotation_method.update()))
            frame_callback()
        output_writer.queue.put(None)


    def process_video_cli(self, input_reader: ffmpeg.FFMpegReader,
                      output_writer: ffmpeg.FFMpegWriter, frame_count: int):
        with Progress(
            TextColumn(
                "[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(), TimeElapsedColumn(),
            TimeRemainingColumn(), FPSColumn()) as progress:
            
            task = progress.add_task(
                ":hourglass_flowing_sand:[2/3]Rendering Video",
                total=frame_count)
            self.process_video(input_reader, output_writer, lambda: progress.advance(task))
        

    def run_gui(self,
            input_reader: ffmpeg.FFMpegReader,
            output_video: str | PathLike,
            codec: str,
            bitrate: str,
            fps: float | None = None,
            progressbar: "Progressbar | None" = None):
        assert progressbar is not None
        if fps:
            input_reader.fps = fps
        with self.con.status("[1/3]Loading Video...") as status:
            self.paint_msg = self._get_video_info(
                input_reader.info["height"],
                input_reader.info["width"], self.height)
            log.debug(f"Paint Msg: {self.paint_msg}", )

            # 又是一个支持中文路径小技巧
            if self.background is not None:
                bg_temp_path = Path("temp.png")
                cv2.imencode('.png', self.paint_msg.background,
                            [cv2.IMWRITE_PNG_COMPRESSION, 9
                            ])[1].tofile(bg_temp_path)
                log.debug(
                    f"Save background image in {bg_temp_path.absolute()}")
            else:
                bg_temp_path = None
            fps_output = (input_reader.info["fps"]
                          if input_reader.hope_fps is None else
                          input_reader.hope_fps)
            if fps: fps_output = fps

            width, height = self.paint_msg.output_size

            log.debug(
                f"Output Video Width: {width}, Height: {height}")
            output_writer = ffmpeg.FFMpegWriter(
                output_video,
                width=width,
                height=height,
                fps=fps_output,
                encoder=codec,
                bitrate=bitrate,
                background_image=bg_temp_path)
        rprint(":white_check_mark:[1/3]Loading Video... Complete")

        frame_count = int(input_reader.info["duration"] * fps_output)

        if (self.height is not None and input_reader.info["height"]
                != self.paint_msg.video_resize[1]):
            log.debug(
                "Resize Input Video to "
                f"{self.paint_msg.video_resize[0]}x{self.paint_msg.video_resize[1]}"
            )
            input_reader.resize = self.paint_msg.video_resize

        event = threading.Event()
        is_exception = threading.Event()
        exception_arg = None

        def excepthook(args):
            nonlocal exception_arg
            traceback.print_exception(args.exc_type, args.exc_value,
                                    args.exc_traceback)
            exception_arg = args
            is_exception.set()
            event.set()

        threading.excepthook = excepthook

        list_task = [
            threading.Thread(target=input_reader.start_process,
                            daemon=True),
            threading.Thread(
                target=self.process_video,
                args=[input_reader, output_writer, lambda: progressbar.step(100 / frame_count)],
                daemon=True),
            threading.Thread(target=output_writer.start_process,
                            daemon=True)
        ]

        for i in list_task:
            log.debug(f"Start Thread {i}")
            i.start()


        def join_hook():
            for i in list_task:
                i.join()
            event.set()

        threading.Thread(target=join_hook, daemon=True).start()

        event.wait()
        if is_exception.is_set():
            return False, exception_arg

        rprint(":white_check_mark:[2/3]Rendering Video... Complete")

        # 删了临时文件
        bg_temp_path.unlink()
        log.debug(f"Del {bg_temp_path.absolute()}")
        with self.con.status("[3/3]Coping audio...") as status:
            ffmpeg.audio_copy(input_reader.input_file, output_video)
        rprint(":white_check_mark:[3/3]Coping audio... Complete")
        return True, None

    def run(self,
            input_video: str | PathLike,
            output_video: str | PathLike,
            codec: str,
            bitrate: str,
            fps: float | None = None):
        with self.con.status("[1/3]Loading Video...") as status:
            input_reader = ffmpeg.FFMpegReader(input_video, fps)
            self.paint_msg = self._get_video_info(
                input_reader.info["height"],
                input_reader.info["width"], self.height)
            log.debug(f"Paint Msg: {self.paint_msg}", )

            # 又是一个支持中文路径小技巧
            bg_temp_path = Path("temp.png")
            cv2.imencode('.png', self.paint_msg.background,
                        [cv2.IMWRITE_PNG_COMPRESSION, 9
                        ])[1].tofile(bg_temp_path)
            log.debug(
                f"Save background image in {bg_temp_path.absolute()}")
            fps_output = (input_reader.info["fps"]
                          if input_reader.hope_fps is None else
                          input_reader.hope_fps)

            width, height = self.paint_msg.output_size

            log.debug(
                f"Output Video Width: {width}, Height: {height}")
            output_writer = ffmpeg.FFMpegWriter(
                output_video,
                width=width,
                height=height,
                fps=fps_output,
                encoder=codec,
                bitrate=bitrate,
                background_image=bg_temp_path)
        rprint(":white_check_mark:[1/3]Loading Video... Complete")

        frame_count = int(input_reader.info["duration"] * fps_output)

        if (self.height is not None and input_reader.info["height"]
                != self.paint_msg.video_resize[1]):
            log.debug(
                "Resize Input Video to "
                f"{self.paint_msg.video_resize[0]}x{self.paint_msg.video_resize[1]}"
            )
            input_reader.resize = self.paint_msg.video_resize

        event = threading.Event()
        is_exception = threading.Event()

        def excepthook(args):
            traceback.print_exception(args.exc_type, args.exc_value,
                                    args.exc_traceback)
            is_exception.set()
            event.set()

        threading.excepthook = excepthook

        list_task = [
            threading.Thread(target=input_reader.start_process,
                            daemon=True),
            threading.Thread(
                target=self.process_video_cli,
                args=[input_reader, output_writer, frame_count],
                daemon=True),
            threading.Thread(target=output_writer.start_process,
                            daemon=True)
        ]



        for i in list_task:
            log.debug(f"Start Thread {i}")
            i.start()



        def join_hook():
            for i in list_task:
                i.join()
            event.set()

        threading.Thread(target=join_hook, daemon=True).start()

        event.wait()
        if is_exception.is_set():
            exit()

        rprint(":white_check_mark:[2/3]Rendering Video... Complete")

        # 删了临时文件
        bg_temp_path.unlink()
        log.debug(f"Del {bg_temp_path.absolute()}")
        with self.con.status("[3/3]Coping audio...") as status:
            ffmpeg.audio_copy(input_video, output_video)
        rprint(":white_check_mark:[3/3]Coping audio... Complete")


if __name__ == "__main__":
    a = Rotaeno(
        background="Songs_today-is-not-tomorrow.png",
        circle_crop=True,
        #auto_crop=False,
        display_all=True,
        window_size=5)
    a.run("test.mp4", "test_a.mp4", "hevc_nvnec", "8m")
