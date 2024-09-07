import sys
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory

import skia
from rich import print as rprint
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .background import PaintMsg
from .ffmpeg import FFMpegHWTest, FFMpegProgress, VideoInfo, get_ffmpeg
from .log import log
from .rotation_calc import RotationCalc
from .utils import FPSColumn, ask_confirm

if sys.version_info < (3, 11):
    raise ImportError(
        "RotaenoStablizer requires Python 3.11 or higher. "
        f"Now you are on Python {sys.version}")


class Rotaeno:

    def __init__(self,
                 rotation_version: int = 2,
                 fps: float | None = None,
                 circle_crop: bool = True,
                 auto_crop: bool = True,
                 display_all: bool = True,
                 height: int | None = None,
                 background: str | PathLike | None = None):
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

    def generate_ffmpeg_cmd(self,
                            input_video: str | PathLike,
                            output_video: str | PathLike,
                            background: str | PathLike,
                            alpha: str | PathLike,
                            input_video_info: VideoInfo,
                            paint_msg: PaintMsg,
                            sendcmd_path: str | PathLike,
                            bitrate: str | None = None,
                            encoder: str | None = None,
                            decoder: str | None = None):
        commands = [get_ffmpeg()]
        if decoder is not None:
            commands += ["-c:v", decoder]
        commands += ["-i", input_video, "-i", alpha, "-i", background]
        sendcmd_path = Path(sendcmd_path).as_posix().replace(
            ":", r"\:")

        video_process = "[0:v]"
        if self.fps:
            video_process += f"fps={self.fps},"
        if paint_msg.video_resize != input_video_info.size:
            video_process += (
                "scale="
                f"{paint_msg.video_resize[0]}:{paint_msg.video_resize[1]},"
            )
        if paint_msg.video_crop != paint_msg.video_resize:
            video_process += (
                "crop="
                f"{paint_msg.video_crop[0]}:{paint_msg.video_crop[1]},"
            )
        video_process = video_process[:-1]
        video_process += "[padded];"
        video_process += "[padded][1:v]alphamerge[masked];"

        video_process += f"[masked]sendcmd=f='{sendcmd_path}'"
        video_process += f",rotate=c=black@0:ow={paint_msg.video_crop[0]}:oh=ow[rotated];"
        video_process += "[2:v][rotated]overlay[output]"

        commands += ["-filter_complex", video_process]
        commands += ["-map", "[output]", "-map", "0:a"]
        if self.fps:
            commands += [
                "-r",
                str(self.fps if self.
                    fps is not None else input_video_info.fps)
            ]
        if encoder is not None:
            commands += ["-c:v", encoder]
        if bitrate is not None:
            commands += ["-b:v", bitrate]

        commands += ["-c:a", "copy", output_video, "-y"]

        return commands

    def run(self,
            input_video: str | PathLike,
            output_video: str | PathLike,
            using_hardware_acc: bool = True,
            decoder: str | None = None,
            encoder: str | None = None,
            bitrate: str | None = None):

        if (output_video := Path(output_video)).exists():
            rprint(f"输出文件已存在：{output_video}")
            if not ask_confirm("是否覆盖"):
                return

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(), TaskProgressColumn(), FPSColumn(),
            TimeRemainingColumn(elapsed_when_finished=True))

        task1 = progress.add_task("[1/3] Preprocessing...", total=1)
        task2 = progress.add_task("[2/3] Create Rotation Command")
        task3 = progress.add_task("[3/3] Running Rotaion")
        with TemporaryDirectory(dir=".") as temp_dir_str, progress:
            temp_dir = Path(temp_dir_str)
            log.debug(f"Create temp dir: {temp_dir}")

            # Get Video Info
            input_video_info = VideoInfo(input_video)
            if self.fps is None:
                common_fps = [
                    24, 25, 29.97, 30, 48, 50, 59.94, 60, 120, 144,
                    180, 240
                ]
                if input_video_info.fps not in common_fps:
                    self.fps = min(
                        common_fps,
                        key=lambda x: abs(x - input_video_info.fps))
                    log.info(
                        f"Unusual fps ({input_video_info.fps}), maybe it's vfr video. Turn output video fps as {self.fps}"
                    )
                else:
                    self.fps = input_video_info.fps

            paint_msg = PaintMsg.from_video_info(
                input_video_info.height, input_video_info.width,
                self.height, self.background, self.circle_crop,
                self.auto_crop, self.display_all)

            paint_msg.background.save(
                str(temp_dir / "background.png"), skia.kPNG)
            paint_msg.image_alpha.save(
                str(temp_dir / "image_alpha.png"), skia.kPNG)

            # About coder
            if (using_hardware_acc
                    and (encoder is None or decoder is None)):
                support_encoder, support_decoder = (
                    FFMpegHWTest().run(input_video_info.codec))
                if encoder is None:
                    encoder = support_encoder[0]
                if decoder is None:
                    decoder = support_decoder[0]

            progress.advance(task1)

            # Write Rotation
            rotation_calc = RotationCalc(self.rotation_version)
            total_frame = int(input_video_info.duration * self.fps)
            rotation_cmd = [
                line
                for line in progress.track(rotation_calc.export_cmd(
                    input_video, self.fps, decoder),
                                           task_id=task2,
                                           total=total_frame)
            ]

            # total_frame is not truth frame, So updated as completed
            progress.update(task2, completed=total_frame)
            total_frame = len(rotation_cmd)
            (temp_dir / "rotation.ffmpeg.cmd").write_text(
                "\n".join(rotation_cmd))

            ffmpeg_cmd = self.generate_ffmpeg_cmd(
                input_video=input_video,
                output_video=output_video,
                background=temp_dir / "background.png",
                alpha=temp_dir / "image_alpha.png",
                input_video_info=input_video_info,
                paint_msg=paint_msg,
                sendcmd_path=temp_dir / "rotation.ffmpeg.cmd",
                bitrate=bitrate,
                encoder=encoder,
                decoder=decoder)

            log.debug("Running Commands: [bold green]" +
                      escape(" ".join(map(str, ffmpeg_cmd))),
                      extra={"markup": True})

            ff = FFMpegProgress(ffmpeg_cmd)
            progress.update(task3, total=total_frame)
            for p in ff.process():
                progress.update(task3, completed=p)
            progress.update(task3, completed=total_frame)
            log.info("Task Finish")


if __name__ == "__main__":
    a = Rotaeno(
        background=
        r"E:\Code\py-rotaeno-stablizer-gui\test\Songs_today-is-not-tomorrow.png",
    )
    a.run(r"E:\Code\py-rotaeno-stablizer-gui\test\test_5s.mp4",
          r"E:\Code\py-rotaeno-stablizer-gui\test\test_5s_.mp4",
          bitrate="8000K")
