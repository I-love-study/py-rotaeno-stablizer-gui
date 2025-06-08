# 旋转指令

Rotate Data 的指令由下面的参数组成：

```bash
[开始时间(s)]-[结束时间(s)] rotate angle [旋转(弧度制)];
```

例如：

```bash
0-0.016666666666666666 rotate angle 6.264777537724958;
```

如果你是**FFMpeg 高手**，或者认为该程序提供的参数不足以支撑你的创作，那么就可以通过导出该 Rotate Data 来创建你自己的 FFMpeg 指令，并运行。在下面，我们将会提供程序导出时提供的 FFMpeg 指令：

```bash
ffmpeg -i input_video.mp4 -i image_alpha.png -i background.png -filter_complex "[0:v]fps=60,crop=1920:1080[padded];[padded][1:v]alphamerge[masked];[masked]sendcmd=f='rotation.ffmpeg.cmd',rotate=c=black@0:ow=1920:oh=ow[rotated];[2:v][rotated]overlay[output]" -map "[output]" -map 0:a -r 60 -c:v hevc_nvenc -b:v 8000k -c:a copy output.mp4
```
