import itertools
import json
import logging
import re
import subprocess
import uuid
from contextlib import contextmanager
from functools import cached_property
from multiprocessing.pool import ThreadPool
from os import PathLike
from pathlib import Path
from queue import Queue
from shutil import which
from subprocess import PIPE

import numpy as np
from rich.markup import escape

log = logging.getLogger("rich")


class FFMpegError(Exception):
    ...


def gpu_perfer_order(coders: list[str]):
    ret = []
    for coder in coders:
        for gpu_fix in ["nvenc", "vaapi", "qsv"]:
            if gpu_fix in coder:
                ret.append(coder)
                break
    ret += [c for c in coders if c not in ret]
    return ret


def get_ffmpeg():
    """获取本机拥有的编解码器"""
    if which("ffmpeg"):
        return "ffmpeg"
    elif Path("ffmpeg/bin/ffmpeg.exe").exists():
        return "ffmpeg/bin/ffmpeg.exe"

    Warning("Couldn't find ffmpeg, maybe it'll not work")
    return "ffmpeg"


def get_ffprobe():
    """获取本机拥有的编解码器"""
    if which("ffprobe"):
        return "ffprobe"
    elif Path("ffmpeg/bin/ffprobe.exe").exists():
        return "ffmpeg/bin/ffprobe.exe"

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
                                stderr=PIPE)
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
                 fps: float | None = None,
                 decoder: str | None = None) -> None:
        self.input_file = Path(input_name)
        self.info = self.get_info()
        self.fps = fps
        self.queue = Queue(5)
        self.resize: tuple[int, int] | None = None
        self.decoder = decoder

    @cached_property
    def is_vfr(self):
        return self.vfr_check()

    @cached_property
    def hope_fps(self):
        common_fps = [30, 60, 75, 90, 120, 144, 180, 240]
        hope_fps = (min(common_fps,
                    key=lambda x: abs(x - self.info["fps"]))
                if self.fps is None and self.is_vfr else self.fps)
        log.debug(f"Output Video fps: {hope_fps}")
        return hope_fps

    def get_info(self):
        commands = [
            get_ffprobe(), "-v", "quiet", "-print_format", "json",
            "-show_streams", self.input_file
        ]
        pipe = subprocess.Popen(commands, stdout=PIPE, stderr=PIPE)
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
        codec_name = video_info["codec_name"]
        if ("side_data_list" in video_info
                and video_info["side_data_list"][0]["rotation"] % 360
                in [90, 270]):
            height, width = width, height

        log.debug(f"Video coder: {codec_name}")
        log.debug(f"Video Width: {width}, Height: {height}")
        duration = float(video_info["duration"])
        log.debug(f"Video duration: {duration:.2f}s")
        log.debug(f"Video fps: {video_fps:.2f}")
        return {
            "fps": video_fps,
            "height": height,
            "width": width,
            "duration": duration,
            "codec_name": codec_name
        }

    def vfr_check(self):
        commands = [
            get_ffmpeg(), "-i", self.input_file, "-vf", "vfrdet",
            "-an", "-f", "null", "-"
        ]
        pipe = subprocess.Popen(commands, stderr=PIPE)
        vfr_str = pipe.communicate()[1].decode()
        pattern = r'VFR:(\d+\.\d+)'
        match = re.search(pattern, vfr_str)
        assert match is not None
        target_number = float(match.group(1))
        log.debug(f"VFR have {target_number:.2f}")
        return target_number

    def start(self):
        commands = [get_ffmpeg(), "-loglevel", "error"]
        if self.decoder is not None:
            commands += ["-c:v", self.decoder]
        commands += ["-i", self.input_file]
        ("-filter_complex "
         "[0:v]fps=60[original];"
         "[original]scale=-1:720, crop=1280:720[cropd]"
         "[original]crop=10:10:0:0[top_left];"
         "[original]crop=10:10:iw-10:0[top_right];"
         "[original]crop=10:10:0:ih-10[bottom_left];"
         "[original]crop=10:10:iw-10:ih-10[bottom_right];"
         "[top_left][top_right]hstack[top];"
         "[bottom_left][bottom_right]hstack[bottom];"
         "[top][bottom]vstack[rotation];"
         "")
        if self.hope_fps is not None:
            commands += ["-vf", "fps=" + str(self.hope_fps)]
        if self.resize is not None:
            commands += ["-s", f"{self.resize[0]}x{self.resize[1]}"]
            width = self.resize[0]
            height = self.resize[1]
        else:
            width = self.info["width"]
            height = self.info["height"]
        commands += ["-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"]
        log.debug("Reader Commands: [bold green]" +
                  escape(" ".join(map(str, commands))),
                  extra={"markup": True})
        frame_size = width * height * 3
        pipe = subprocess.Popen(commands,
                                stdout=PIPE,
                                stderr=PIPE,
                                bufsize=frame_size + 1)
        return pipe, height, width

    def read(self):
        while True:
            q = self.queue.get()
            if q is None:
                return
            yield q
            self.queue.task_done()

    def start_process(self):
        pipe, height, width = self.start()
        frame_size = height * width * 3
        stdout = pipe.stdout
        assert stdout is not None
        while pipe.poll() is None:
            frame_raw = stdout.read(frame_size)
            frame = np.frombuffer(frame_raw, dtype=np.uint8)
            if frame.size == 0: break
            #frame_rgba = np.empty((height, width, 4), np.uint8)
            #frame_rgba[:,:,:3] = frame.reshape((height, width, 3))
            #tag = frame.reshape(frame_rgba)
            #self.queue.put(frame_rgba)
            self.queue.put(frame.reshape((height, width, 3)))
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
            encoder: str | None = None,
            bitrate: str | None = None,
            background_image: str | PathLike | None = None) -> None:
        self.output_video = output_video
        self.height = height
        self.width = width
        self.fps = fps
        self.pix_fmt = pix_fmt
        self.background_image = background_image
        self.bitrate = bitrate
        self.pipe = None
        self.queue = Queue(5)
        self.encoder = encoder

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
                f"[0:v][1:v]overlay=format=yuv420[v]", "-map", "[v]"
            ]
        if self.encoder is not None:
            commands += ["-c:v", self.encoder]
        commands += ["-r", str(self.fps), "-pix_fmt", self.pix_fmt]
        if self.bitrate is not None:
            commands += ["-b:v", self.bitrate]
        commands += [self.output_video]

        log.debug("Writer Commands: [bold green]" +
                  escape(" ".join(map(str, commands))),
                  extra={"markup": True})
        self.pipe = subprocess.Popen(
            commands,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            bufsize=self.height * self.width * 4 + 1)
        return self

    def start_process(self):
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
                except (OSError, BrokenPipeError) as e:
                    assert self.pipe.stderr
                    line = self.pipe.stderr.read().decode(
                        encoding="UTF-8").splitlines()
                    raise FFMpegError("\n".join(line)) from e
                self.queue.task_done()


class FFMpegHWTest:

    def __init__(self) -> None:
        ...

    def get_available_codecs(
            self, codec: str) -> tuple[list[str], list[str]]:
        commands = [get_ffmpeg(), "-codecs"]
        encoder_pattern = r'\((encoders:[^\)]+)\)'
        decoder_pattern = r'\((decoders:[^\)]+)\)'
        with subprocess.Popen(commands, stdout=PIPE,
                              stderr=PIPE) as popen:
            assert popen.stdout
            try:
                l = next(
                    l[8:] for line in popen.stdout.readlines()
                    if codec +
                    " " == (l := line.decode("UTF-8"))[8:9 +
                                                       len(codec)])
            except StopIteration:
                raise FFMpegError(
                    f"Cannot fount codecs in ffmpeg: {codec}")
            encoder_searcher = re.search(encoder_pattern, l)
            assert encoder_searcher is not None
            encoders = encoder_searcher.group(1).split()[1:]
            decoder_searcher = re.search(decoder_pattern, l)
            assert decoder_searcher is not None
            decoders = decoder_searcher.group(1).split()[1:]
        return encoders, decoders

    @contextmanager
    def generate_decoder_video(self, encoder):
        filename = Path(f"temp_{uuid.uuid4()}.mp4")
        commands = [
            get_ffmpeg(), "-f", "lavfi", "-i", "nullsrc", "-c:v",
            encoder, "-frames:v", "1", filename, "-y"
        ]
        subprocess.run(commands, stdout=PIPE, stderr=PIPE)
        yield filename
        filename.unlink()

    def test_encoder(self, encoder: str):
        commands = [
            get_ffmpeg(), "-f", "lavfi", "-i", "nullsrc", "-c:v",
            encoder, "-frames:v", "1", "-f", "null", "-"
        ]
        proc = subprocess.run(commands, stdout=PIPE, stderr=PIPE)

        return not proc.returncode

    def test_decoder(self, decoder: str, path):
        commands = [
            get_ffmpeg(), "-c:v", decoder, "-i", path, "-frames:v",
            "1", "-f", "null", "-"
        ]
        proc = subprocess.run(commands, stdout=PIPE, stderr=PIPE)

        return not proc.returncode

    def test_encoders(self, encoders: list[str]):
        with ThreadPool() as pool:
            available_encoders = [
                encoder for encoder, available in zip(
                    encoders, pool.map(self.test_encoder, encoders))
                if available
            ]
        return available_encoders

    def test_decoders(self, decoders: list[str]):
        with (self.generate_decoder_video("libx265") as
              file, ThreadPool() as pool):
            available_decoders = [
                decoder for decoder, available in zip(
                    decoders,
                    pool.starmap(
                        self.test_decoder,
                        zip(decoders, itertools.repeat(file))))
                if available
            ]
        return available_decoders

    @classmethod
    def get_encoders(cls, codec: str) -> list[str]:
        cls_ = cls()
        encoders, _ = cls_.get_available_codecs(codec)
        return cls_.test_encoders(encoders)

    @classmethod
    def get_decoders(cls, codec: str) -> list[str]:
        cls_ = cls()
        _, decoders = cls_.get_available_codecs(codec)
        return cls_.test_decoders(decoders)

    def run(self, codec: str):
        encoders, decoders = self.get_available_codecs(codec)
        available_encoders = self.test_encoders(encoders)
        available_decoders = self.test_decoders(decoders)
        return available_encoders, available_decoders


if __name__ == "__main__":
    from rich.logging import RichHandler
    logging.basicConfig(level="INFO",
                        format="%(message)s",
                        datefmt="[%X]",
                        handlers=[RichHandler(rich_tracebacks=True)])
    logging.getLogger("rich").setLevel("DEBUG")

    f = FFMpegReader(r"test/test_5s.mp4")
