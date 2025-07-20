import itertools
import json
import logging
import re
import subprocess
import uuid
from contextlib import contextmanager
from dataclasses import InitVar, dataclass, field
from multiprocessing.pool import ThreadPool
from os import PathLike
from pathlib import Path
from shutil import which
from subprocess import PIPE, STDOUT

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
    # Use FFMpeg Under path first
    if Path("./ffmpeg.exe").exists():
        return "./ffmpeg.exe"
    elif which("ffmpeg"):
        return "ffmpeg"

    Warning("Couldn't find ffmpeg, maybe it'll not work")
    return "ffmpeg"


def get_ffprobe():
    """获取本机拥有的编解码器"""
    if Path("./ffprobe.exe").exists():
        return "./ffprobe.exe"
    elif which("ffprobe"):
        return "ffprobe"

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
            get_ffmpeg(), "-y", "-i", audio_from, "-i", audio_temp, "-map", "0:a",
            "-map", "1:v", "-c", "copy", audio_to
        ],
                                stderr=PIPE)
        _, stderr = pipe.communicate()
    except Exception as e:
        if stderr is None:
            raise e
        raise OSError(stderr) from e

    # 不用 finally，好不容易出来的视频，炸了就先别删
    audio_temp.unlink()


@dataclass
class VideoInfo:
    video_path_m: InitVar[str | PathLike]
    video_path: Path = field(init=False)
    fps: float = field(init=False)
    height: int = field(init=False)
    width: int = field(init=False)
    duration: float = field(init=False)
    codec: str = field(init=False)
    size: tuple[int, int] = field(init=False)

    def __post_init__(self, video_path_m):
        self.video_path = Path(video_path_m)
        commands = [
            get_ffprobe(), "-v", "quiet", "-print_format", "json", "-show_streams",
            self.video_path
        ]
        pipe = subprocess.Popen(commands, stdout=PIPE, stderr=PIPE)
        info = json.loads(pipe.communicate()[0])
        try:
            video_info = next(stream for stream in info["streams"]
                              if stream["codec_type"] == "video")
        except StopIteration:
            raise ValueError("Cannot found video infomation in Stream.")

        video_fps = float(video_info["nb_frames"]) / float(video_info["duration"])
        height, width = video_info["height"], video_info["width"]
        codec_name = video_info["codec_name"]
        if ("side_data_list" in video_info
                and video_info["side_data_list"][0]["rotation"] % 360 in [90, 270]):
            height, width = width, height
        duration = float(video_info["duration"])

        self.fps = video_fps
        self.height = height
        self.width = width
        self.duration = duration
        self.codec = codec_name
        self.size = (width, height)


class FFMpegProgress:

    def __init__(self, cmd: list) -> None:
        self.cmd = cmd

    def process(self):
        commands = self.cmd[0:1] + [
            "-progress", "-", "-nostats", "-stats_period", "0.1"
        ] + self.cmd[1:]
        pipe = subprocess.Popen(commands,
                                stdin=PIPE,
                                stdout=PIPE,
                                stderr=STDOUT,
                                universal_newlines=False)

        stderr = ""
        while True:
            assert pipe.stdout is not None

            line = (pipe.stdout.readline().decode("utf-8", errors="replace").strip())
            stderr += line
            if line == "" and pipe.poll() is not None:
                break

            if line.startswith("frame=") and line[6:].isdigit():
                yield int(line[6:])

        if pipe.returncode != 0:
            raise RuntimeError(f"Error running command {self.cmd}: {stderr}")


class FFMpegHWTest:

    def __init__(self) -> None:
        ...

    def get_available_codecs(self, codec: str) -> tuple[list[str], list[str]]:
        commands = [get_ffmpeg(), "-codecs"]
        encoder_pattern = r'\((encoders:[^\)]+)\)'
        decoder_pattern = r'\((decoders:[^\)]+)\)'
        with subprocess.Popen(commands, stdout=PIPE, stderr=PIPE) as popen:
            assert popen.stdout
            try:
                l = next(li[8:] for line in popen.stdout.readlines() if codec +
                         " " == (li := line.decode("UTF-8"))[8:9 + len(codec)])
            except StopIteration:
                raise FFMpegError(f"Cannot fount codecs in ffmpeg: {codec}")
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
            get_ffmpeg(), "-f", "lavfi", "-i", "nullsrc", "-c:v", encoder, "-frames:v",
            "1", filename, "-y"
        ]
        subprocess.run(commands, stdout=PIPE, stderr=PIPE)
        yield filename
        filename.unlink()

    def test_encoder(self, encoder: str):
        commands = [
            get_ffmpeg(), "-f", "lavfi", "-i", "nullsrc", "-c:v", encoder, "-frames:v",
            "1", "-f", "null", "-"
        ]
        proc = subprocess.run(commands, stdout=PIPE, stderr=PIPE)

        return not proc.returncode

    def test_decoder(self, decoder: str, path):
        commands = [
            get_ffmpeg(), "-c:v", decoder, "-i", path, "-frames:v", "1", "-f", "null",
            "-"
        ]
        proc = subprocess.run(commands, stdout=PIPE, stderr=PIPE)

        return not proc.returncode

    def test_encoders(self, encoders: list[str]):
        with ThreadPool() as pool:
            available_encoders = [
                encoder for encoder, available in zip(
                    encoders, pool.map(self.test_encoder, encoders)) if available
            ]
        return available_encoders

    def test_decoders(self, decoders: list[str], source_encoder: str):
        with (self.generate_decoder_video(source_encoder) as file, ThreadPool() as
              pool):
            available_decoders = [
                decoder for decoder, available in zip(
                    decoders,
                    pool.starmap(self.test_decoder, zip(decoders, itertools.repeat(
                        file)))) if available
            ]
        return available_decoders

    def priority_sort(self, coders: list):
        priority = {"_cuvid": 4, "_nvenc": 4, "_qsv": 3, "_vaapi": 2}

        def key(x):
            for k, v in priority.items():
                if k in x:
                    return v
            return 0

        return coders.sort(key=key, reverse=True)

    def run(self, codec: str):
        encoders, decoders = self.get_available_codecs(codec)

        available_encoders = self.test_encoders(encoders)
        available_decoders = self.test_decoders(decoders, available_encoders[0])
        self.priority_sort(available_encoders)
        self.priority_sort(available_decoders)
        return available_encoders, available_decoders


if __name__ == "__main__":
    from rich.logging import RichHandler
    logging.basicConfig(level="INFO",
                        format="%(message)s",
                        datefmt="[%X]",
                        handlers=[RichHandler(rich_tracebacks=True)])
    logging.getLogger("rich").setLevel("DEBUG")
    import time
    t = time.time()
    print(FFMpegHWTest().run("hevc"))
    #print(VideoInfo(r"E:\Code\py-rotaeno-stablizer-gui\test\test_full.mp4"))
    print(time.time() - t)
