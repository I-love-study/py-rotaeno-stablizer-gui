import argparse
from pathlib import Path

from rotaeno_stablizer import Rotaeno

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o",
                        "--output-video",
                        type=str,
                        default=None)
    parser.add_argument("--rotation-version",
                        type=int,
                        default=2,
                        help="直播模式版本，默认为2（V2）")
    parser.add_argument("-bg",
                        "--background-path",
                        type=str,
                        help="歌曲封面照片路径")
    parser.add_argument("--no-auto_crop",
                        action="store_true",
                        help="不将原视频裁切（不是拉伸）到16:9")
    parser.add_argument("--no-circle-crop",
                        action="store_true",
                        help="不使用圆形切环")
    parser.add_argument("--no-display-all",
                        action="store_true",
                        help="不输出正方形版本")
    parser.add_argument("--height",
                        type=int,
                        help="输出视频高度，默认不选")
    parser.add_argument("--window-size",
                        type=int,
                        default=3,
                        help="平滑参数（参数越高越平滑）默认为3")
    parser.add_argument("input_video", type=str)
    args = parser.parse_args()
    print(args)
    rotaeno = Rotaeno(rotation_version=args.rotation_version,
                      circle_crop=not args.no_circle_crop,
                      auto_crop=not args.no_auto_crop,
                      display_all=not args.no_display_all,
                      background_path=args.background_path,
                      height=args.height,
                      spectrogram_circle=False,
                      window_size=args.window_size)
    input_video = Path(args.input_video)
    rotaeno.process_video(
        input_video,
        input_video.with_stem(input_video.stem + "_out")
        if args.output_video is None else args.output_video)
