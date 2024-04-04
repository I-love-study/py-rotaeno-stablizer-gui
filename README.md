# PY ROTAENO Stablizer GUI

Rotaeno 录屏稳定

Still in WIP

## 特点

1. 使用 ffmpeg 作为视频编解码器，可以选择多个编码器选择（包括显卡编码）
2. 使用 PIPE 作连接，几乎不会出现中间变量
3. 采用平滑曲线，让输出更加稳定

## 效果展示

在这里以 [今天不是明天](https://www.bilibili.com/video/BV1pi4y1B7oz)
（作曲 [PIKASONIC](https://space.bilibili.com/262995951) feat. [兰音Reine](https://space.bilibili.com/698029620)）为例

> [!TIP]
> 封面图像可以从 [Rotaeno 中文维基](https://wiki.rotaeno.cn/) 获取

> [!IMPORTANT]
> 因为图片采用了 AVIF 格式，可能部分浏览器无法显示

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
- [ ] 配置文件
- [ ] 多线程处理
- [ ] 环状频谱图
- [x] 命令行调用
- [ ] GUI 界面

## 安装

### 直接下载

> [!IMPORTANT]
> 因为 `libx264`、`libx265` 要求 GPL-3.0 协议，而本仓库为 LGPL-3.0  
> 所以 Release 中的 `with-ffmpeg` 将使用 LGPL-3.0 协议的 `ffmpeg`  
> （即不包括 `libx264`, `libx265`）

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

### 命令行办法(推荐)

```bash
./rotaeno_stablizer [options] input_video.mp4 ouput_video.mp4
python -m rotaeno_stablizer [options] input_video.mp4 ouput_video.mp4
```

或者直接双击，将会得到以下文字

<style>
.r1 {color: #808000; text-decoration-color: #808000; font-weight: bold}
.r2 {color: #800080; text-decoration-color: #800080; font-weight: bold}
.r3 {color: #008080; text-decoration-color: #008080; font-weight: bold}
</style>
<pre style="font-family:Menlo,'DejaVu Sans Mono',consolas,sans-serif, monospace; background-color:#171b22">
<code style="font-family:inherit; background-color:#171b22">请输入原始文件:
输出文件： <span class="r1">test_out.mp4</span>
请选择直播模式版本 <span class="r2">[1/2]</span> <span class="r3">(2)</span>:
是否自动裁切成16:9 <span class="r2">([y]/n)</span> :
是否使用圆形切环 <span class="r2">([y]/n)</span> :
是否输出正方形版本 <span class="r2">([y]/n)</span> :
是否自动裁切成16:9 <span class="r2">([y]/n)</span> :
是否需要背景图片 <span class="r2">([y]/n)</span> :
请输入背景图片路径: 请输入平滑参数： <span class="r3">(3)</span>:
请输入输出视频高度（0 为系统自动选择） <span class="r3">(0)</span>:
请选择输出视频编码器 <span class="r3">(hevc_nvenc)</span>:
请选择输出视频比特率 <span class="r3">(8m)</span>: </code></pre>

### 半 GUI 办法

直接双击即可

### GUI 办法

WIP

## Help Usage

<style>
.r1 {color: #0000ff; text-decoration-color: #0000ff; text-decoration: underline}
.r2 {color: #ff8700; text-decoration-color: #ff8700}
.r3 {color: #808080; text-decoration-color: #808080}
.r4 {color: #008080; text-decoration-color: #008080}
.r5 {color: #00af87; text-decoration-color: #00af87}
.r6 {color: #ffffff; text-decoration-color: #ffffff}
.r7 {color: #008080; text-decoration-color: #008080; font-style: italic}
</style>
<pre style="font-family:Menlo,'DejaVu Sans Mono',consolas,sans-serif, monospace; background-color:#171b22">
<code style="font-family:inherit; background-color:#171b22">PY Rotaeno Stablizer: <span class="r1">https://github.com/I-love-study/py-rotaeno-stablizer-gui</span>

<span class="r2">Usage:</span> <span class="r3">__main__.py</span> [<span class="r4">-h</span>] [<span class="r4">-o</span> <span class="r5">OUTPUT_VIDEO</span>] [<span class="r4">--rotation-version</span> <span class="r5">ROTATION_VERSION</span>] [<span class="r4">-bg</span> <span class="r5">BACKGROUND</span>] [<span class="r4">--auto-crop</span> | <span class="r4">--no-auto-crop</span>] [<span class="r4">--circle-crop</span> | <span class="r4">--no-circle-crop</span>]
                   [<span class="r4">--display-all</span> | <span class="r4">--no-display-all</span>] [<span class="r4">--height</span> <span class="r5">HEIGHT</span>] [<span class="r4">--window-size</span> <span class="r5">WINDOW_SIZE</span>] [<span class="r4">-c</span> <span class="r5">CODEC</span>] [<span class="r4">-b</span> <span class="r5">BITRATE</span>]
                   [<span class="r4">input_video</span>]

<span class="r6">Rotaeno</span>

<span class="r2">Positional Arguments:</span>
  <span class="r4">input_video</span>

<span class="r2">Options:</span>
  <span class="r4">-h</span>, <span class="r4">--help</span>            <span class="r6">帮助</span><span class="r4"> (默认为 </span><span class="r7">False</span><span class="r4">)</span>
  <span class="r4">-o</span>, <span class="r4">--output-video</span> <span class="r5">OUTPUT_VIDEO</span>
  <span class="r4">--rotation-version</span> <span class="r5">ROTATION_VERSION</span>
                        <span class="r6">直播模式版本</span><span class="r4"> (默认为 </span><span class="r7">2</span><span class="r4">)</span>
  <span class="r4">-bg</span>, <span class="r4">--background</span> <span class="r5">BACKGROUND</span>
                        <span class="r6">歌曲封面照片路径</span><span class="r4"> (默认为 </span><span class="r7">None</span><span class="r4">)</span>
  <span class="r4">--auto-crop</span>, <span class="r4">--no-auto-crop</span>
                        <span class="r6">将原视频裁切（不是拉伸）到16:9</span><span class="r4"> (默认为 </span><span class="r7">True</span><span class="r4">)</span>
  <span class="r4">--circle-crop</span>, <span class="r4">--no-circle-crop</span>
                        <span class="r6">使用圆形切环</span><span class="r4"> (默认为 </span><span class="r7">True</span><span class="r4">)</span>
  <span class="r4">--display-all</span>, <span class="r4">--no-display-all</span>
                        <span class="r6">输出正方形版本</span><span class="r4"> (默认为 </span><span class="r7">True</span><span class="r4">)</span>
  <span class="r4">--height</span> <span class="r5">HEIGHT</span>       <span class="r6">输出视频高度</span><span class="r4"> (默认为 </span><span class="r7">0</span><span class="r4">)</span>
  <span class="r4">--window-size</span> <span class="r5">WINDOW_SIZE</span>
                        <span class="r6">平滑参数（参数越高越平滑）</span><span class="r4"> (默认为 </span><span class="r7">3</span><span class="r4">)</span>
  <span class="r4">-c</span>, <span class="r4">--codec</span> <span class="r5">CODEC</span>     <span class="r6">输出视频所使用的编码器</span><span class="r4"> (默认为 </span><span class="r7">hevc_nvenc</span><span class="r4">)</span>
  <span class="r4">-b</span>, <span class="r4">--bitrate</span> <span class="r5">BITRATE</span>
                        <span class="r6">输出视频码率（不包含音频）</span><span class="r4"> (默认为 </span><span class="r7">8m</span><span class="r4">)</span>
</code></pre>

## 相关项目

[Lawrenceeeeeeee/python_rotaeno_stabilizer](https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer)

[linnaea/obs-rotaeno-stablizer](https://github.com/linnaea/obs-rotaeno-stablizer)
