import argparse
import logging
from pathlib import Path

from rich import print as rprint
from rich_argparse import RichHelpFormatter

from rotaeno_stablizer import Rotaeno

from .config import config_data

from .cli import ui as cli
from .gui import main as gui


class ArgumentDefaultsHelpFormatter(RichHelpFormatter):

    def _get_help_string(self, action):
        help = action.help
        if help is None:
            help = ''

        if '%(default)' not in help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += '[argparse.args] (默认为 %(default)s)[/argparse.args]'
        return help


if __name__ == "__main__":

    from rich import get_console
    console = get_console()

    rprint(
        "PY Rotaeno Stablizer: [link]https://github.com/I-love-study/py-rotaeno-stablizer-gui[/link]\n"
    )

    parser = argparse.ArgumentParser(description='Rotaeno',
                                     formatter_class=ArgumentDefaultsHelpFormatter,
                                     add_help=False)
    parser.add_argument('-h', '--help', help='帮助', action='store_true')

    parser.add_argument("-o", "--output-video", type=str, default=None)

    parser.add_argument("--video-output",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["video_output"],
                        help="输出视频"
    )
    parser.add_argument("--rotation-version", type=int, default=2, help="直播模式版本")
    parser.add_argument("-bg", "--background", type=str, help="歌曲封面照片路径")
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
    parser.add_argument("--encoder",
                        type=str,
                        default=config_data["codec"]["encoder"],
                        help="输出视频所使用的编码器")
    parser.add_argument("--decoder",
                        type=str,
                        default=config_data["codec"]["decoder"],
                        help="输出视频所使用的编码器")
    parser.add_argument("-b",
                        "--bitrate",
                        type=str,
                        default=config_data["codec"]["bitrate"],
                        help="输出视频码率（不包含音频）")
    parser.add_argument("--loglevel",
                        type=str,
                        default=config_data["other"]["loglevel"],
                        help="日志等级")

    parser.add_argument("--mask-output",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["mask_output"],
                        help="输出掩码"
    )
    parser.add_argument("--mask-path",
                        type=str,
                        default=None,
                        help="掩码视频路径，默认为输出文件 + '_mask'，如果已填写，默认输出"
    )
    parser.add_argument("--cmd-output",
                        action=argparse.BooleanOptionalAction,
                        default=config_data["video"]["cmd_output"],
                        help="输出 ffmpeg 命令，以及对应的旋转信息，如果已填写，默认输出"
    )
    parser.add_argument("--cmd-path",
                        type=str,
                        default=None,
                        help="输出旋转路径，默认为输出文件 + '_rotate.cmd'"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cli",
                       action="store_true",
                       default=not config_data["other"]["default_gui"],
                       help="使用 cli 界面")
    group.add_argument("--gui",
                       action="store_true",
                       default=config_data["other"]["default_gui"],
                       help="使用 cli 界面")
    parser.add_argument("--show-warning",
                        action=argparse.BooleanOptionalAction,
                       default=config_data["other"]["show_warning"],
                       help="是否展示非官方警告")
    parser.add_argument("input_video", type=str, default=None, nargs='?')
    args = parser.parse_args()
    if args.help:
        parser.print_help()
    elif args.input_video is None:
        # TODO: auto downgrade to cli when no have display
        if args.cli:
            cli()
        else:
            gui(args)
    else:
        input_video = Path(args.input_video)

        if args.output_video is not None:
            output_video = Path(args.output_video)
        elif not args.cmd_output:
            cmd_path = None
        else:
            cmd_path = (
                input_video.with_stem(f"{input_video.stem}_out"))

        if args.cmd_path is not None:
            cmd_path = Path(args.cmd_path)
        elif not args.cmd_output:
            cmd_path = None
        else:
            cmd_path = (
                input_video.with_stem(f"{input_video.stem}_rotate").with_suffix(".cmd"))

        if args.mask_path is not None:
            mask_path = Path(args.mask_path)
        elif not args.mask_output:
            mask_path = None
        else:
            mask_path = input_video.with_stem(f"{input_video.stem}_mask")

        logging.getLogger("rich").setLevel(args.loglevel.upper())
        rotaeno = Rotaeno(rotation_version=args.rotation_version,
                          circle_crop=args.circle_crop,
                          auto_crop=args.auto_crop,
                          display_all=args.display_all,
                          background=args.background,
                          height=args.height)

        rotaeno.run(input_video=input_video,
                    output_video=output_video,
                    output_mask=mask_path,
                    output_cmd=cmd_path,
                    encoder=args.encoder if args.encoder else None,
                    decoder=args.decoder if args.encoder else None,
                    bitrate=args.bitrate,
                    )
