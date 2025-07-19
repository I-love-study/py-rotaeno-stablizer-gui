import sys
from pathlib import Path

if sys.version_info >= (3,11):
    import tomllib
else:
    import rtoml as tomllib

default_toml = """[video]
rotation_version = 2 # 直播模式版本
auto_crop = true # 是否裁剪到16:9
circle_crop = true # 是否圆形裁剪
display_all = true # 是否显示全部
background_need = true # 是否需要背景
window_size = 3 # 平滑参数
height = 0 # 输出视频高度（0 为自动判断）
video_output = true # 是否输出视频
mask_output = false # 是否输出掩码
cmd_output = false # 是否输出 ffmpeg 命令 与旋转信息

[codec] # 编码器
encoder = ""
bitrate = "8000k" # 8 Mbps
decoder = ""

[other]
ask_for_config = true # 在直接运行时，是否询问、
ask_for_output = false # 是否需要询问输出文件
loglevel = "info" # 日志等级
default_gui = true # （无参数情况下）启用 GUI 界面
show_warning = true # 展示非官方警告"""

config_path = Path("config.toml")
config_data = tomllib.loads(
    config_path.read_text(encoding="UTF-8") \
    if config_path.exists() else default_toml)
