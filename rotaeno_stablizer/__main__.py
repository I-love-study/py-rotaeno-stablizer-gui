import argparse
import logging
import tomllib
from pathlib import Path

from rich import print as rprint
from rich_argparse import RichHelpFormatter

from rotaeno_stablizer import Rotaeno


class ArgumentDefaultsHelpFormatter(RichHelpFormatter):

    def _get_help_string(self, action):
        help = action.help
        if help is None:
            help = ''

        if '%(default)' not in help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [
                    argparse.OPTIONAL, argparse.ZERO_OR_MORE
                ]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += '[argparse.args] (默认为 %(default)s)[/argparse.args]'
        return help


def ui(config_data):
    from os import getcwd

    from rich.prompt import IntPrompt, Prompt

    from .utils import ask_confirm

    input_file = Path(Prompt.ask("请输入原始文件"))
    if config_data['other']['ask_for_output']:
        output_file = Path(Prompt.ask("请输入原始文件"))
    else:
        output_file = input_file.with_stem(
            config_data['other']['default_output_filename'].format(
                input_file.stem))
        rprint("输出文件：", f"[bold yellow]{output_file}")

    config_data["video"]["rotation_version"] = IntPrompt.ask(
        "请选择直播模式版本",
        choices=["1", "2"],
        default=config_data["video"]["rotation_version"])
    config_data["video"]["auto_crop"] = ask_confirm(
        "是否自动裁切成16:9", default=config_data["video"]["auto_crop"])
    config_data["video"]["circle_crop"] = ask_confirm(
        "是否使用圆形切环", default=config_data["video"]["circle_crop"])
    config_data["video"]["display_all"] = ask_confirm(
        "是否输出正方形版本", default=config_data["video"]["display_all"])
    config_data["video"]["auto_crop"] = ask_confirm(
        "是否自动裁切成16:9", default=config_data["video"]["auto_crop"])
    config_data["video"]["background_need"] = ask_confirm(
        "是否需要背景图片", default=config_data["video"]["background_need"])
    if config_data["video"]["background_need"]:
        config_data["video"]["background"] = Prompt.ask("请输入背景图片路径")
    else:
        config_data["video"]["background"] = None
    config_data["video"]["window_size"] = IntPrompt.ask(
        "请输入平滑参数：", default=config_data["video"]["window_size"])
    config_data["video"]["height"] = IntPrompt.ask(
        "请输入输出视频高度（0 为系统自动选择）",
        default=config_data["video"]["height"])

    config_data["encode"]["codec"] = Prompt.ask(
        "请选择输出视频编码器", default=config_data["encode"]["codec"])
    config_data["encode"]["bitrate"] = Prompt.ask(
        "请选择输出视频比特率", default=config_data["encode"]["bitrate"])

    rotaeno = Rotaeno(
        rotation_version=config_data["video"]["rotation_version"],
        circle_crop=config_data["video"]["circle_crop"],
        auto_crop=config_data["video"]["auto_crop"],
        display_all=config_data["video"]["display_all"],
        background=config_data["video"]["background"],
        height=config_data["video"]["height"],
        spectrogram_circle=False,
        window_size=config_data["video"]["window_size"])
    rotaeno.run(input_file, output_file,
                config_data["encode"]["codec"],
                config_data["encode"]["bitrate"])


if __name__ == "__main__":

    from rich import get_console
    console = get_console()
    console.record = True

    rprint(
        "PY Rotaeno Stablizer: [link]https://github.com/I-love-study/py-rotaeno-stablizer-gui[/link]\n"
    )
    config_path = Path("config.toml")
    config_data = tomllib.loads(
        config_path.read_text(encoding="UTF-8"))
    parser = argparse.ArgumentParser(
        description='Rotaeno',
        formatter_class=ArgumentDefaultsHelpFormatter,
        add_help=False)
    parser.add_argument('-h',
                        '--help',
                        help='帮助',
                        action='store_true')
    parser.add_argument("-o",
                        "--output-video",
                        type=str,
                        default=None)
    parser.add_argument("--rotation-version",
                        type=int,
                        default=2,
                        help=f"直播模式版本")
    parser.add_argument("-bg",
                        "--background",
                        type=str,
                        help="歌曲封面照片路径")
    parser.add_argument("--auto-crop",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["auto_crop"],
                        help="将原视频裁切（不是拉伸）到16:9")
    parser.add_argument("--circle-crop",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["circle_crop"],
                        help="使用圆形切环")
    parser.add_argument("--display-all",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["display_all"],
                        help="输出正方形版本")
    parser.add_argument("--height",
                        type=int,
                        default=config_data["video"]["height"],
                        help="输出视频高度")
    parser.add_argument("--window-size",
                        type=int,
                        default=config_data["video"]["window_size"],
                        help="平滑参数（参数越高越平滑）")
    parser.add_argument("-c",
                        "--codec",
                        type=str,
                        default=config_data["encode"]["codec"],
                        help="输出视频所使用的编码器")
    parser.add_argument("-b",
                        "--bitrate",
                        type=str,
                        default=config_data["encode"]["bitrate"],
                        help="输出视频码率（不包含音频）")
    parser.add_argument("--loglevel",
                        type=str,
                        default=config_data["other"]["loglevel"],
                        help="输出视频码率（不包含音频）")
    parser.add_argument("input_video",
                        type=str,
                        default=None,
                        nargs='?')
    args = parser.parse_args()
    if args.help:
        parser.print_help()
        exit()
    if args.input_video is None:
        ui(config_data)
    else:
        logging.getLogger("rich").setLevel(args.loglevel.upper())
        rotaeno = Rotaeno(rotation_version=args.rotation_version,
                          circle_crop=args.circle_crop,
                          auto_crop=args.auto_crop,
                          display_all=args.display_all,
                          background=args.background,
                          height=args.height,
                          spectrogram_circle=False,
                          window_size=args.window_size)

        input_video = Path(args.input_video)
        rotaeno.run(
            input_video,
            input_video.with_stem(input_video.stem + "_out")
            if args.output_video is None else args.output_video,
            args.codec, args.bitrate)
