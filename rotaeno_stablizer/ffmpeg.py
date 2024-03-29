from os import PathLike
import queue
import subprocess
from pathlib import Path
import json
import re
import logging
import numpy as np

log = logging.getLogger()


def get_ffmpeg_path() -> str:
    return "ffmpeg"


def get_ffprobe_path() -> str:
    return "ffprobe"


def audio_copy(audio_from, audio_to):
    print([
        get_ffmpeg_path(), "-y", "-i", audio_from, "-i", audio_to,
        "-map", "0:a", "-map", "1:v", "-c", "copy", audio_to
    ])
    try:
        pipe = subprocess.Popen([
            get_ffmpeg_path(), "-y", "-i", audio_from, "-i", audio_to,
            "-map", "0:a", "-map", "1:v", "-c", "copy", audio_to
        ],
                                stderr=subprocess.PIPE)
        _, stderr = pipe.communicate()
    except:
        raise OSError(stderr)


class FFMpegReader:

    def __init__(self,
                 input_name: str | PathLike,
                 fps: int | None = None) -> None:
        self.input_file = Path(input_name)
        #self.is_vfr = self.vfr_check()
        self.is_vfr = True
        self.info = self.get_info()
        common_fps = [30, 60, 75, 90, 120, 144, 180, 240]
        self.hope_fps = min(common_fps,
                            key=lambda x: abs(x - self.info["fps"])
                            ) if fps is None and self.is_vfr else fps
        self.queue = queue.Queue

    def get_info(self):
        commands = [
            get_ffprobe_path(), "-v", "quiet", "-print_format",
            "json", "-show_streams", self.input_file
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
            get_ffmpeg_path(), "-i", self.input_file, "-vf", "vfrdet",
            "-an", "-f", "null", "-"
        ]
        pipe = subprocess.Popen(commands, stderr=subprocess.PIPE)
        vfr_str = pipe.communicate()[1].splitlines()[-1].decode()
        pattern = r'VFR:(\d+\.\d+)'
        match = re.search(pattern, vfr_str)
        assert match is not None
        target_number = match.group(1)
        return float(target_number)

    def read(self, resize: tuple[int, int] | None = None):
        commands = [
            get_ffmpeg_path(), "-loglevel", "error", "-i",
            self.input_file
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

        stdout = pipe.stdout
        assert stdout is not None
        while pipe.poll() is None:
            frame_raw = stdout.read(frame_size)
            frame = np.frombuffer(frame_raw, dtype=np.uint8)
            if frame.size == 0: break
            yield frame.reshape((height, width, 4)).copy()
            stdout.flush()
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
            background_image: str | PathLike | None = None
    ) -> None:
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
        commands = [get_ffmpeg_path(), "-y", "-loglevel", "warning"]
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
        while True:
            frame = self.queue.get()
            if frame is None:
                self.pipe.stdin.close()
                self.pipe.wait()
                self.queue.task_done()
                break
            assert frame.shape == (self.height, self.width, 4)
            self.pipe.stdin.write(frame)
            self.queue.task_done()

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.pipe
        assert self.pipe.stdin
        self.pipe.stdin.close()
        self.pipe.wait()


if __name__ == "__main__":
    a = FFMpegReader("test.mp4")
