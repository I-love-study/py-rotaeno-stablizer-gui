from pathlib import Path

from rich import print as rprint
from rich.prompt import IntPrompt, Prompt

from . import Rotaeno
from .config import config_data
from .utils import ask_confirm


def ui():

    input_file = Path(Prompt.ask("请输入原始文件名称："))
    output_file = Prompt.ask("请给出输出文件（如不需要，请直接回车）：")
    output_file = Path(output_file) if output_file != "" else None
    output_mask = Prompt.ask("请给出输出掩码（如不需要，请直接回车）：")
    output_mask = Path(output_mask) if output_mask != "" else None
    output_cmd = Prompt.ask("请给出输出旋转信息（如不需要，请直接回车）：")
    output_cmd = Path(output_cmd) if output_cmd != "" else None

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
    config_data["video"]["background_need"] = ask_confirm(
        "是否需要背景图片", default=config_data["video"]["background_need"])
    if config_data["video"]["background_need"]:
        config_data["video"]["background"] = Prompt.ask("请输入背景图片路径")
    else:
        config_data["video"]["background"] = None
    config_data["video"]["window_size"] = IntPrompt.ask(
        "请输入平滑参数：", default=config_data["video"]["window_size"])
    config_data["video"]["height"] = IntPrompt.ask(
        "请输入输出视频高度（0 为系统自动选择）", default=config_data["video"]["height"])

    config_data["codec"]["encoder"] = Prompt.ask(
        "请选择输出视频编码器", default=config_data["codec"]["encoder"])
    config_data["codec"]["bitrate"] = Prompt.ask(
        "请选择输出视频比特率", default=config_data["codec"]["bitrate"])

    rotaeno = Rotaeno(rotation_version=config_data["video"]["rotation_version"],
                      circle_crop=config_data["video"]["circle_crop"],
                      auto_crop=config_data["video"]["auto_crop"],
                      display_all=config_data["video"]["display_all"],
                      background=config_data["video"]["background"],
                      height=config_data["video"]["height"])
    rotaeno.run(input_video=input_file,
                output_video=output_file,
                output_mask=output_mask,
                output_cmd=output_cmd,
                encoder=config_data["codec"]["encoder"],
                bitrate=config_data["codec"]["bitrate"])
