from os import PathLike
from pathlib import Path
from uuid import uuid4

import numpy as np
import skia

from .background import PaintMsg
from .ffmpeg import VideoInfo
from .log import log
from .utils import get_skia_picture


class Rotaeno:

    def __init__(self,
                 rotation_version: int = 2,
                 fps: float | None = None,
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
        """

        self.rotation_version = rotation_version
        self.fps = fps
        self.circle_crop = circle_crop
        self.auto_crop = auto_crop
        self.display_all = display_all
        self.height = height if height != 0 else None
        self.background = background

    def run(self, input_video: str | PathLike,
            output_video: str | PathLike):
        # Get Video Info
        input_video_info = VideoInfo(input_video)
        if self.fps is None:
            common_fps = [
                24, 25, 29.97, 30, 48, 50, 59.94, 60, 120, 144, 180,
                240
            ]
            if input_video_info.fps not in common_fps:
                self.fps = min(
                    common_fps,
                    key=lambda x: abs(x - input_video_info.fps))
                log.info(
                    "Unusual fps, maybe it's vfr video. Turn output video fps as {self.fps}"
                )
            else:
                self.fps = input_video_info.fps

        # Pre
        cache_path = Path(f"cache_{uuid4()}")
        cache_path.mkdir()
        log.debug(f"Create cache path {cache_path}")

        paint_msg = PaintMsg.from_video_info(
            input_video_info.height, input_video_info.width,
            self.height, self.background, self.circle_crop,
            self.auto_crop, self.display_all)
        
        paint_msg.background.save(cache_path / "background.png", skia.kPNG)
        paint_msg.image_alpha.save(cache_path / "image_alpha.png", skia.kPNG)

        
