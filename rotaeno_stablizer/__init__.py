import sys
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory

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

if sys.version_info < (3, 10):
    raise ImportError("RotaenoStablizer requires Python 3.10 or higher. "
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
        """__init__，用于创建实例，需传入输出视频的部分信息

        Args:
            rotation_version (int, optional): 使用串流版本. Defaults to 2.
            fps (int, optional): 帧率，None 则表示使用原帧率
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
                            decoder: str | None = None,
                            mask_output : bool = True):
        commands = [get_ffmpeg()]

        if not mask_output:
            if decoder is not None:
                commands += ["-c:v", decoder]
            commands += ["-i", input_video]

        commands += ["-i", alpha, "-i", background]
        sendcmd_path = Path(sendcmd_path).as_posix().replace(":", r"\:")

        video_process = ""
        if not mask_output:
            video_process += "[0:v]"
            if self.fps:
                video_process += f"fps={self.fps},"
            if paint_msg.video_resize != input_video_info.size:
                video_process += (
                    "scale="
                    f"{paint_msg.video_resize[0]}:{paint_msg.video_resize[1]},")
            if paint_msg.video_crop != paint_msg.video_resize:
                video_process += ("crop="
                                f"{paint_msg.video_crop[0]}:{paint_msg.video_crop[1]},")
            video_process = video_process[:-1]
            video_process += "[padded];"
            video_process += "[padded][1:v]alphamerge[masked];"
        else:
            video_process += f"[0:v]format=rgba,loop=loop=-1:size=1:start=0,trim=duration={input_video_info.duration}[masked];"

        video_process += (f"[masked]sendcmd=f='{sendcmd_path}'"
                          f",rotate=c=black@0:ow={paint_msg.video_crop[0]}:oh=ow[rotated];")

        if not mask_output:
            video_process += "[2:v][rotated]overlay[output]"

        commands += ["-filter_complex", video_process]
        commands += ["-map", "[rotated]" if mask_output else "[output]"]

        if not mask_output:
            commands += ["-map", "0:a"]

        if self.fps:
            commands += [
                "-r",
                str(self.fps if self.fps is not None else input_video_info.fps)
            ]
        if encoder is not None:
            commands += ["-c:v", encoder]
        if bitrate is not None:
            commands += ["-b:v", bitrate]

        if not mask_output:
            commands += ["-c:a", "copy"]

        commands += [output_video, "-y"]

        return commands

    def infomation_get(
        self,
        input_video: str | PathLike,
        temp_dir: Path,
        using_hardware_acc: bool = True,
        decoder: str | None = None,
        encoder: str | None = None,
    ):

        # Get Video Info
        input_video_info = VideoInfo(input_video)
        if self.fps is None:
            common_fps = [24, 25, 29.97, 30, 48, 50, 59.94, 60, 120, 144, 180, 240]
            if input_video_info.fps not in common_fps:
                self.fps = min(common_fps,
                               key=lambda x: abs(x - input_video_info.fps))
                log.info(
                    f"Unusual fps ({input_video_info.fps}), maybe it's vfr video. Turn output video fps as {self.fps}"
                )
            else:
                self.fps = input_video_info.fps

        paint_msg = PaintMsg.from_video_info(input_video_info.height,
                                             input_video_info.width, self.height,
                                             self.background, self.circle_crop,
                                             self.auto_crop, self.display_all)

        paint_msg.background.save(str(temp_dir / "background.png"))
        paint_msg.image_alpha.save(str(temp_dir / "image_alpha.png"))

        # About coder
        if (using_hardware_acc and (encoder is None or decoder is None)):
            support_encoder, support_decoder = (FFMpegHWTest().run(
                input_video_info.codec))
            if encoder is None:
                encoder = support_encoder[0]
            if decoder is None:
                decoder = support_decoder[0]

        return input_video_info, paint_msg, encoder, decoder

    def run(self,
            input_video: str | PathLike,
            output_video: str | PathLike | None = None,
            output_cmd: str | PathLike | None = None,
            output_mask: str | PathLike | None = None,
            using_hardware_acc: bool = True,
            decoder: str | None = None,
            encoder: str | None = None,
            bitrate: str | None = None,
            ensure_rewrite: bool = False):

        input_video = Path(input_video)
        if output_video is not None:
            output_video = Path(output_video)

        if not ensure_rewrite:
            checklist = [output_video, output_cmd, output_mask]
            existlist = [c for c in checklist if c is not None and c.exists()]
            if existlist:
                rprint(f"输出文件已存在：{', '.join(map(str, existlist))}")
                if not ask_confirm("是否覆盖"):
                    return

        progress = Progress(SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            BarColumn(), TaskProgressColumn(), FPSColumn(),
                            TimeRemainingColumn(elapsed_when_finished=True))


        task1 = progress.add_task("Preprocessing...", total=1)
        task2 = progress.add_task("Create Rotation Command")
        if output_video is not None:
            task_video = progress.add_task("Running Video Generate")
            output_video = Path(output_video)
        if output_mask is not None:
            task_mask = progress.add_task("Running Mask Generate")
            output_mask = Path(output_mask)
        if output_cmd is not None:
            output_cmd = Path(output_cmd)

        with TemporaryDirectory(dir=".") as temp_dir_str, progress:
            temp_dir = Path(temp_dir_str)
            log.debug(f"Create temp dir: {temp_dir}")

            input_video_info, paint_msg, encoder, decoder = self.infomation_get(
                input_video, temp_dir, using_hardware_acc, decoder, encoder)
            progress.advance(task1)

            # Write Rotation
            assert self.fps is not None
            rotation_calc = RotationCalc(self.rotation_version)
            total_frame = int(input_video_info.duration * self.fps)
            rotation_cmd = [
                line for line in progress.track(rotation_calc.export_cmd(
                    input_video, self.fps, decoder),
                                                task_id=task2,
                                                total=total_frame)
            ]

            # total_frame is not truth frame, So updated as completed
            progress.update(task2, completed=total_frame)
            total_frame = len(rotation_cmd)
            rotate_data_path = (output_cmd if output_cmd is not None else temp_dir /
                                "rotation.ffmpeg.cmd")
            rotate_data_path.write_text("\n".join(rotation_cmd))

            ffmpeg_cmd = self.generate_ffmpeg_cmd(
                input_video=input_video,
                output_video=(output_video if output_video is not None else
                              input_video.with_stem(input_video.stem + "_out")),
                background=temp_dir / "background.png",
                alpha=temp_dir / "image_alpha.png",
                input_video_info=input_video_info,
                paint_msg=paint_msg,
                sendcmd_path=rotate_data_path,
                bitrate=bitrate,
                encoder=encoder,
                decoder=decoder,
                mask_output=False)

            if output_cmd is not None:
                log.debug(f"Rotated data saved in {rotate_data_path.absolute()}")
                log.info("Commands: [bold green]" +
                        escape(" ".join(map(str, ffmpeg_cmd))),
                        extra={"markup": True})

            if output_video is not None:
                log.debug("Running Commands: [bold green]" +
                        escape(" ".join(map(str, ffmpeg_cmd))),
                        extra={"markup": True})

                ff = FFMpegProgress(ffmpeg_cmd)
                progress.update(task_video, total=total_frame)
                for p in ff.process():
                    progress.update(task_video, completed=p)
                progress.update(task_video, completed=total_frame)

            if output_mask is not None:
                ffmpeg_cmd = self.generate_ffmpeg_cmd(
                    input_video=input_video,
                    output_video=output_mask,
                    background=temp_dir / "background.png",
                    alpha=temp_dir / "image_alpha.png",
                    input_video_info=input_video_info,
                    paint_msg=paint_msg,
                    sendcmd_path=rotate_data_path,
                    bitrate=bitrate,
                    encoder=encoder,
                    decoder=decoder,
                    mask_output=True)

                log.debug("Running Commands: [bold green]" +
                        escape(" ".join(map(str, ffmpeg_cmd))),
                        extra={"markup": True})

                ff = FFMpegProgress(ffmpeg_cmd)
                progress.update(task_mask, total=total_frame)
                for p in ff.process():
                    progress.update(task_mask, completed=p)
                progress.update(task_mask, completed=total_frame)

            log.info("Task Finish")

if __name__ == "__main__":
    a = Rotaeno(
        background=
        r"E:\Code\py-rotaeno-stablizer-gui\test\Songs_today-is-not-tomorrow.png", )
    a.run(r"E:\Code\py-rotaeno-stablizer-gui\test\test_5s.mp4",
          r"E:\Code\py-rotaeno-stablizer-gui\test\test_5s_.mp4",
          bitrate="8000K")
