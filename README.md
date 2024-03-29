# PY ROTAENO Stablizer GUI

Rotaeno 录屏稳定

Still in WIP

## 特点

1. 使用 ffmpeg 作为视频编解码器，可以选择多个编码器选择（包括显卡编码）
2. 使用 PIPE 作连接，几乎不会出现中间变量
3. 采用平滑曲线，让输出更加稳定

## 效果展示

在这里以 [今天不是明天](https://www.bilibili.com/video/BV1pi4y1B7oz) （作曲 [PIKASONIC](https://space.bilibili.com/262995951) feat. [兰音Reine](https://space.bilibili.com/698029620)）为例

> [!TIP]
> 封面图像可以从 [Rotaeno 中文维基](https://wiki.rotaeno.cn/) 获取

|       操作       |          语法           |                                 效果                                  |
| :--------------: | :---------------------: | :-------------------------------------------------------------------: |
|     默认效果     |            -            |         <details>![normal](docs_image/normal.avif)</details>          |
|   添加音乐封面   | -bg / --background-path | <details>![with_background](docs_image/with_backgrond.avif)</details> |
|  不进行自动裁切  |     --no-auto-crop      |   <details>![no_auto_crop](docs_image/no_auto_crop.avif)<\details>    |
|  不进行圆形裁切  |    --no-circle-crop     | <details>![no_circle_crop](docs_image/no_circle_crop.avif)<\details>  |
| 不输出正方形版本 |    --no-display-all     | <details>![no_display_all](docs_image/no_display_all.avif)<\details>  |

## TO-DO-LIST

- [x] 帧处理
- [x] SMA 平滑曲线
- [x] 视频处理
- [ ] 编码器详细设置
- [ ] 多线程处理
- [ ] 环状频谱图
- [x] 命令行调用
- [ ] GUI 界面

## 安装

### 直接下载

> [!IMPORTANT]
> 因为 `libx264`、`libx265` 要求 GPL-3.0 协议，而本仓库为 LGPL-3.0
> 所以 Release 中的 `with-ffmpeg` 将使用 LGPL-3.0 协议的 `ffmpeg`

从 Github Action 下载最新版本

### 命令行

> [!IMPORTANT]
> 请确保你安装了 `Git`, `python` 和 `ffmpeg`，且将其放置在环境变量中

```bash
git clone https://github.com/I-love-study/py-rotaeno-stablizer-gui.git
cd py-rotaeno-stablizer-gui
pip install -r requirements.txt
```

## 使用方法

要求先要启动 v2 直播录像

### 命令行办法(暂时无法使用)

```bash
python main.py input.mp4
```

### 半 GUI 办法

WIP

### GUI 办法

WIP

## 相关项目

[Lawrenceeeeeeee/python_rotaeno_stabilizer](https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer)

[linnaea/obs-rotaeno-stablizer](https://github.com/linnaea/obs-rotaeno-stablizer)
