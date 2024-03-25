# PY ROTAENO Stablizer GUI

Rotaeno 录屏稳定

Still in WIP

## 特点

1. 使用 ffmpeg 作为视频编解码器，可以选择多个编码器选择（包括显卡编码）
2. 使用 PIPE 作连接，temp不会过大
3. 采用平滑曲线，让输出更加稳定

## TO-DO-LIST

- [x] 帧处理
- [x] SMA 平滑曲线
- [x] 视频处理
- [ ] 多线程处理
- [ ] 命令行调用
- [ ] GUI 界面

## 安装

### 直接下载

WIP

### 命令行

:::warning
请确保你安装了 `Git` 和 `python`，且将其放置在环境变量中
:::

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
