import json
import logging
import queue
import re
import subprocess
from os import PathLike
from pathlib import Path
from shutil import which

import numpy as np

log = logging.getLogger()


class FFMpegError(Exception):
    ...


def get_ffmpeg():
    """获取本机拥有的编解码器"""
    if which("ffmpeg"):
        return "ffmpeg"
    elif Path("ffmpeg/ffmpeg.exe").exists():
        return "ffmpeg/ffmpeg.exe"

    Warning("Couldn't find ffmpeg, maybe it'll not work")
    return "ffmpeg"


def get_ffprobe():
    """获取本机拥有的编解码器"""
    if which("ffprobe"):
        return "ffprobe"
    elif Path("ffmpeg/ffprobe.exe").exists():
        return "ffmpeg/ffprobe.exe"

    Warning("Couldn't find ffprobe, maybe it'll not work")
    return "ffprobe"


def audio_copy(audio_from: str | PathLike, audio_to: str | PathLike):
    audio_from = Path(audio_from)
    audio_to = Path(audio_to)
    audio_temp = audio_to.with_stem(audio_to.stem + "_video")
    audio_to.rename(audio_temp)
    stderr = None
    try:
        pipe = subprocess.Popen([
            get_ffmpeg(), "-y", "-i", audio_from, "-i", audio_temp,
            "-map", "0:a", "-map", "1:v", "-c", "copy", audio_to
        ],
                                stderr=subprocess.PIPE)
        _, stderr = pipe.communicate()
    except Exception as e:
        if stderr is None:
            raise e
        raise OSError(stderr) from e

    # 不用 finally，好不容易出来的视频，炸了就先别删
    audio_temp.unlink()


class FFMpegReader:

    def __init__(self,
                 input_name: str | PathLike,
                 fps: int | None = None) -> None:
        self.input_file = Path(input_name)
        self.is_vfr = self.vfr_check()
        self.info = self.get_info()
        common_fps = [30, 60, 75, 90, 120, 144, 180, 240]
        self.hope_fps = min(common_fps,
                            key=lambda x: abs(x - self.info["fps"])
                            ) if fps is None and self.is_vfr else fps
        self.queue = queue.Queue(5)

    def get_info(self):
        commands = [
            get_ffprobe(), "-v", "quiet", "-print_format", "json",
            "-show_streams", self.input_file
        ]
        pipe = subprocess.Popen(commands,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        info = json.loads(pipe.communicate()[0])
        try:
            video_info = next(stream for stream in info["streams"]
                              if stream["codec_type"] == "video")
        except StopIteration:
            raise ValueError(
                "Cannot found video infomation in Stream.")
        video_fps = float(video_info["nb_frames"]) / float(
            video_info["duration"])
        height, width = video_info["height"], video_info["width"]
        if ("side_data_list" in video_info
                and video_info["side_data_list"][0]["rotation"] % 360
                in [90, 270]):
            height, width = width, height
        duration = float(video_info["duration"])
        return {
            "fps": video_fps,
            "height": height,
            "width": width,
            "duration": duration
        }

    def vfr_check(self):
        commands = [
            get_ffmpeg(), "-i", self.input_file, "-vf", "vfrdet",
            "-an", "-f", "null", "-"
        ]
        pipe = subprocess.Popen(commands, stderr=subprocess.PIPE)
        vfr_str = pipe.communicate()[1].splitlines()[-1].decode()
        pattern = r'VFR:(\d+\.\d+)'
        match = re.search(pattern, vfr_str)
        assert match is not None
        target_number = match.group(1)
        return float(target_number)

    def start(self, resize: tuple[int, int] | None = None):
        commands = [
            get_ffmpeg(), "-loglevel", "error", "-i", self.input_file
        ]
        if self.hope_fps is not None:
            commands += ["-vf", "fps=" + str(self.hope_fps)]
        if resize is not None:
            commands += ["-s", f"{resize[0]}x{resize[1]}"]
            width = resize[0]
            height = resize[1]
        else:
            width = self.info["width"]
            height = self.info["height"]
        commands += ["-f", "rawvideo", "-pix_fmt", "rgba", "pipe:"]
        log.debug("Reader Commands: [bold green]" +
                  " ".join(map(str, commands)),
                  extra={"markup": True})
        frame_size = width * height * 4
        pipe = subprocess.Popen(commands,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                bufsize=frame_size + 1)
        return pipe, height, width

    def __iter__(self):
        while True:
            q = self.queue.get()
            if q is None:
                return
            yield q
            self.queue.task_done()
            

    def read(self):
        pipe, height, width = self.start()
        frame_size = height * width * 4
        stdout = pipe.stdout
        assert stdout is not None
        while pipe.poll() is None:
            frame_raw = stdout.read(frame_size)
            frame = np.frombuffer(frame_raw, dtype=np.uint8)
            if frame.size == 0: break
            self.queue.put(frame.reshape((height, width, 4)).copy())
            stdout.flush()
        self.queue.put(None)
        pipe.wait()


class FFMpegWriter:

    def __init__(
            self,
            output_video: str | PathLike,
            width: int,
            height: int,
            fps: float,
            pix_fmt: str = "yuv420p",
            codec: str = "libx265",
            bitrate: str = "8M",
            background_image: str | PathLike | None = None) -> None:
        self.output_video = output_video
        self.height = height
        self.width = width
        self.fps = fps
        self.pix_fmt = pix_fmt
        self.codec = codec
        self.background_image = background_image
        self.bitrate = bitrate
        self.pipe = None
        self.queue = queue.Queue(5)

    def start(self):
        commands = [get_ffmpeg(), "-y", "-loglevel", "warning"]
        if self.background_image is not None:
            commands += ["-i", self.background_image]
        commands += [
            "-f", "rawvideo", "-r",
            str(self.fps), "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgba", "-i", "pipe:"
        ]
        if self.background_image is not None:
            commands += [
                "-filter_complex",
                "[0:v][1:v]overlay=0:H-h:format=rgb[v]", "-map", "[v]"
            ]
        commands += [
            "-r",
            str(self.fps), "-c:v", self.codec, "-pix_fmt",
            self.pix_fmt, "-b:v", self.bitrate, self.output_video
        ]
        log.debug("Writer Commands: [bold green]" +
                  " ".join(map(str, commands)),
                  extra={"markup": True})
        self.pipe = subprocess.Popen(
            commands,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=self.height * self.width * 4 + 1)
        return self

    def write(self):
        self.start()
        assert self.pipe
        assert self.pipe.stdin
        with self.pipe:
            while True:
                frame = self.queue.get()
                if frame is None:
                    self.queue.task_done()
                    break
                assert frame.shape == (self.height, self.width, 4)
                try:
                    self.pipe.stdin.write(frame)
                except BrokenPipeError as e:
                    assert self.pipe.stderr
                    line = self.pipe.stderr.read().decode(encoding="UTF-8").splitlines()
                    raise FFMpegError("\n".join(line)) from e
                self.queue.task_done()

if __name__ == "__main__":
    a = FFMpegReader("test.mp4")
