import logging
import math
import os
import queue
import time
from collections import deque
from itertools import islice
from pathlib import Path
from typing import NamedTuple
import threading

import cv2
import numpy as np
from rich import get_console
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

PaintMsg = NamedTuple("PaintMsg",
                      real_height=int,
                      real_width=int,
                      circle_radius=float,
                      circle_thickness=float,
                      background=np.ndarray,
                      video_a=int | None,
                      image_alpha=np.ndarray)

FORMAT = "%(message)s"
logging.basicConfig(level="INFO",
                    format=FORMAT,
                    datefmt="[%X]",
                    handlers=[RichHandler(rich_tracebacks=True)])

log = logging.getLogger("rich")


def ceil_even(num: float) -> int:
    return math.ceil(num / 2) * 2


class Rotaeno:

    def __init__(self,
                 rotation_version: int = 2,
                 circle_crop: bool = False,
                 auto_crop: bool = True,
                 display_all: bool = True,
                 height: int | None = None,
                 background_path: str | os.PathLike | None = None,
                 spectrogram_circle: bool = False,
                 window_size: int = 3):
        """_summary_

        Args:
            rotation_version (int, optional): 使用串流版本. Defaults to 2.
            circle_crop (bool, optional): 是否采用圆形裁切，裁切后，视频将会变为 16:9. Defaults to True.
            auto_crop (bool, optional): 将输入视频裁切成 16:9. Defaults to True.
            display_all (bool, optional): 是否适当缩小视频以保证所有都能看到，开启后视频比例会变为 1:1. Defaults to True.
            height (int | None, optional): 输出视频高度，如为 None，则将由软件自行设置. Defaults to None.
            background (os.PathLike | None, optional): 背景，默认为纯黑背景. Defaults to None.
            spectrogram_circle (bool, optional): 是否需要带有频谱图的圆圈. Defaults to False.
        """

        self.rotation_method = RotationCalc(rotation_version,
                                            window_size)
        self.circle_crop = circle_crop
        self.auto_crop = auto_crop
        self.background_path = background_path
        self.spectrogram_circle = spectrogram_circle
        self.display_all = display_all
        self.height = height

        self.con = get_console()
        self.read_frame_queue = queue.Queue(5)  # 最多存放5帧
        self.event = threading.Event()

    def generate_background(self, width: int, height: int, r: float,
                            thickness: float) -> np.ndarray:

        brightness = 0.2
        background_np = np.zeros((height, width, 3), dtype=np.uint8)
        if self.background_path is not None:
            # 为了支持中文路径的操作
            background: np.ndarray = cv2.imdecode(
                np.fromfile(self.background_path, dtype=np.uint8), 1)
            background = cv2.resize(background,
                                    (int(r * 2), int(r * 2)))
            background = (background * brightness).astype(np.uint8)

            offset_x = int((width - r * 2) / 2)
            offset_y = int((height - r * 2) / 2)

            background_np = paste_image(background_np, background,
                                        offset_x, offset_y)
        cv2.circle(background_np, (width // 2, height // 2),
                   int(r), (255, 255, 255),
                   int(thickness),
                   lineType=cv2.LINE_AA)
        return cv2.cvtColor(background_np, cv2.COLOR_BGR2RGB)

    def _get_video_info(self,
                        height,
                        width,
                        output_height_want: int | None = None):
        aspect_ratio = 16 / 9

        real_width = width
        real_height = height
        if self.auto_crop:
            video_ratio = width / height
            if video_ratio < aspect_ratio:
                real_height = width / aspect_ratio
            elif video_ratio > aspect_ratio:
                real_width = height * aspect_ratio

        max_size = ceil_even(math.sqrt(real_width**2 +
                                       real_height**2))
        # ciricle radius is from https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer
        circle_radius = (1.5575 * real_height) // 2
        circle_thickness = max(real_height // 120, 1)

        real_height = ceil_even(real_height)
        real_width = ceil_even(real_width)

        if self.circle_crop:

            alpha = np.zeros((real_height, real_width),
                             dtype=np.uint8)
            alpha = cv2.circle(alpha,
                               (real_width // 2, real_height // 2),
                               real_width // 2, (255, ),
                               thickness=-1,
                               lineType=cv2.LINE_AA)
            #print("2", time.time() - t)
        else:
            alpha = np.full((real_height, real_width),
                            255,
                            dtype=np.uint8)

        if self.display_all:
            video_a = ceil_even(
                real_width if self.circle_crop else max_size)

            background = self.generate_background(
                video_a, video_a, circle_radius, circle_thickness)
            if output_height_want is not None:
                resize_ratio = video_a / output_height_want
        else:
            video_a = None
            background = self.generate_background(
                real_width, real_height, circle_radius,
                circle_thickness)
            if output_height_want is not None:
                resize_ratio = real_height / output_height_want

        if output_height_want is not None:
            if self.display_all:
                video_a = output_height_want
            else:
                real_height = output_height_want
                real_width /= resize_ratio
            circle_radius /= resize_ratio
            circle_thickness /= resize_ratio
        return PaintMsg(real_height=ceil_even(real_height),
                        real_width=ceil_even(real_width),
                        circle_radius=circle_radius,
                        circle_thickness=circle_thickness,
                        background=background,
                        video_a=video_a,
                        image_alpha=alpha)

    def process_frame(self, frame: np.ndarray, angle: float):
        """

        Args:
            frame (av.VideoFrame): 帧
            height (int): 输出帧高度
            width (int): 输出帧宽度
        """
        # 自动裁切
        t = time.time()
        height, width = frame.shape[:2]
        if self.auto_crop:
            if self.paint_msg.real_height != height:
                offset = (height - self.paint_msg.real_height) // 2
                frame = frame[offset:-offset, :, :]
                height = self.paint_msg.real_height
            elif self.paint_msg.real_width != width:
                offset = (width - self.paint_msg.real_width) // 2
                frame = frame[:, offset:-offset, :]
                width = self.paint_msg.real_width
        #print("1", time.time() - t)
        # 绘制圆形 alpha 通道

        #frame = np.concatenate(
        #    (frame, np.expand_dims(alpha, axis=-1)), axis=2)
        #frame = np.dstack(
        #    (frame, self.paint_msg.image_alpha[..., np.newaxis]))
        frame[:, :, 3] = self.paint_msg.image_alpha
        #print("3", time.time() - t)
        # 如果全部显示
        if self.display_all:
            frame_ = np.zeros(
                (self.paint_msg.video_a, self.paint_msg.video_a, 4),
                dtype=np.uint8)
            offset_x = (self.paint_msg.video_a - width) // 2
            offset_y = (self.paint_msg.video_a - height) // 2
            offset_x = slice(offset_x,
                             -offset_x) if offset_x else slice(
                                 None, None)
            offset_y = slice(offset_y,
                             -offset_y) if offset_y else slice(
                                 None, None)
            frame_[offset_y, offset_x, :] = frame
        else:
            frame_ = frame

    # print("4", time.time() - t)
    # 对扩展帧进行旋转
        M = cv2.getRotationMatrix2D(
            (frame_.shape[1] // 2, frame_.shape[0] // 2), angle, 1)
        rotated_frame = cv2.warpAffine(
            frame_,
            M,
            (frame_.shape[1], frame_.shape[0]),
        )
        #print("5", time.time() - t)
        #background = paint_msg.background.copy()[:, :, :3]
        #rotated_frame, mask = rotated_frame[:, :, :
        #                                    3], rotated_frame[:, :, 3]
        """
        mask3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255
        #print(time.time() - t)
        _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        combine_frame = background.copy()
        combine_frame[mask == 255] = rotated_frame[mask == 255]
        #print("3",time.time()-t)
        translucent = (mask != 255) & (mask != 0)
        combine_frame[translucent] = (
            rotated_frame[translucent] * mask3[translucent] +
            background[translucent] * (1 - mask3[translucent]))"""
        return rotated_frame  #combine_frame

    def process_video(self, output_writer: ffmpeg.FFMpegWriter,
                      frame_count: int):
        with Progress(
                TextColumn(
                    "[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(), TimeElapsedColumn(),
                TimeRemainingColumn(), FPSColumn()) as progress:
            #先给稳定器投喂点数据
            wakeup_elems = []
            for _ in range(self.rotation_method.wake_up_num):
                wakeup_elems.append(self.read_frame_queue.get())
                self.read_frame_queue.task_done()
            self.rotation_method.wake_up(wakeup_elems)
            angle_deque = deque(
                wakeup_elems, maxlen=self.rotation_method.window_size)
            task = progress.add_task("Rendering", total=frame_count)
            while True:
                f = self.read_frame_queue.get()
                if f is None:
                    break
                angle_deque.append(f)
                angle = self.rotation_method.update(f)
                a = self.process_frame(
                    angle_deque[self.rotation_method.wake_up_num],
                    angle)
                output_writer.queue.put(a)
                progress.advance(task)
                self.read_frame_queue.task_done()
            for f in range(self.rotation_method.wake_up_num):
                output_writer.queue.put(
                    self.process_frame(angle_deque.popleft(),
                                       self.rotation_method.update()))
                progress.advance(task)
            output_writer.queue.put(None)

    def _read_frame(self, reader: ffmpeg.FFMpegReader):
        for i in reader.read():
            if self.event.is_set():
                raise RuntimeError
            self.read_frame_queue.put(i)
        self.read_frame_queue.put(None)

    def run(self, input_video: str | os.PathLike,
            output_video: str | os.PathLike):
        with self.con.status("[1/3]Loading Video...") as status:
            input_reader = ffmpeg.FFMpegReader(input_video)
            self.paint_msg = self._get_video_info(
                input_reader.info["height"],
                input_reader.info["width"], self.height)
            background_BGR = cv2.cvtColor(self.paint_msg.background,
                                          cv2.COLOR_RGB2BGR)
            # 又是一个支持中文路径小技巧
            bg_temp_path = Path("temp.png")
            cv2.imencode('.png',
                         background_BGR)[1].tofile(bg_temp_path)
            fps_output = (input_reader.info["fps"]
                          if input_reader.hope_fps is None else
                          input_reader.hope_fps)

            if self.display_all:
                width, height = self.paint_msg.video_a, self.paint_msg.video_a
            else:
                width, height = self.paint_msg.real_width, self.paint_msg.real_height
            output_writer = ffmpeg.FFMpegWriter(
                output_video,
                width=width,
                height=height,
                fps=fps_output,
                codec="hevc_nvenc",
                background_image=bg_temp_path)
            status.update("[1/3]Loading Video... Complete")
        frame_count = int(input_reader.info["duration"] * fps_output)
        read_thread = threading.Thread(target=self._read_frame,
                                       args=(input_reader, ))
        write_thread = threading.Thread(target=output_writer.write)
        try:
            read_thread.start()
            write_thread.start()

            # 处理视频帧
            self.process_video(output_writer, frame_count)
        except:
            self.event.set()
            read_thread.join()
            output_writer.queue.put(None)
            return
        finally:
            write_thread.join()
        # 删了临时文件
        bg_temp_path.unlink()
        with self.con.status("[3/3]Coping audio") as status:
            ffmpeg.audio_copy(input_video, output_video)


if __name__ == "__main__":
    a = Rotaeno(
        background_path="Songs_today-is-not-tomorrow.png",
        circle_crop=True,
        #auto_crop=False,
        display_all=True,
        window_size=5)

    a.run("test.mp4", "test_a.mp4")
