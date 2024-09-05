import math
from dataclasses import dataclass, field
from os import PathLike

import skia

from .utils import get_skia_picture


def ceil_even(num: tuple[float, float]) -> tuple[int, int]:
    ceil_single = lambda n: math.ceil(n / 2) * 2
    return (ceil_single(num[0]), ceil_single(num[1]))


@dataclass
class PaintMsg:
    video_resize: tuple[int, int]
    video_crop: tuple[int, int]
    output_size: tuple[int, int]
    circle_radius: float
    circle_thickness: float
    resize_ratio: float
    cover: skia.Image | None
    background: skia.Image = field(init=False)
    image_alpha: skia.Image

    def __post_init__(self):
        self.background = self.generate_background()

    def generate_background(self):
        width, height = self.output_size
        r = self.circle_radius
        thickness = self.circle_thickness

        brightness = 0.2
        surface = skia.Surface(width, height)
        with surface as canvas:
            canvas.clear(skia.ColorBLACK)
            if self.cover is not None:
                # 调整背景图像大小
                cover_resized = self.cover.resize(
                    int(r * 2), int(r * 2))

                # 创建亮度过滤器
                brightness_filter = skia.ColorFilters.Matrix([
                    brightness, 0, 0, 0, 0, 0, brightness, 0, 0, 0, 0,
                    0, brightness, 0, 0, 0, 0, 0, 1, 0
                ])
                paint = skia.Paint(ColorFilter=brightness_filter)

                # 将背景图像居中
                canvas.save()
                canvas.translate((width - r * 2) / 2,
                                 (height - r * 2) / 2)

                # 绘制调整后的背景图像
                canvas.drawImage(cover_resized, 0, 0, paint=paint)
                canvas.restore()

            # 绘制圆
            paint = skia.Paint(Color=skia.ColorWHITE,
                               Style=skia.Paint.kStroke_Style,
                               StrokeWidth=thickness,
                               AntiAlias=True)
            canvas.drawCircle(width // 2, height // 2, r, paint)

        # 返回绘制结果
        return surface.makeImageSnapshot()

    @classmethod
    def from_video_info(cls,
                        height: int,
                        width: int,
                        output_height_want: int | None = None,
                        cover: str | PathLike | None = None,
                        circle_crop: bool = False,
                        auto_crop: bool = True,
                        display_all: bool = True):
        aspect_ratio = 16 / 9

        # ciricle radius is from https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer

        if auto_crop:
            video_ratio = width / height
            if math.isclose(video_ratio, aspect_ratio, rel_tol=1e-03):
                video_crop = (width, height)
            elif video_ratio < aspect_ratio:
                video_crop = (width, width / aspect_ratio)
            else:  #if video_ratio > aspect_ratio
                video_crop = (height * aspect_ratio, height)
        else:
            video_crop = (width, height)

        if display_all:
            video_a = (math.sqrt(video_crop[0]**2 + video_crop[1]**2)
                       if not circle_crop else video_crop[0])

        if output_height_want is not None:
            if display_all:
                resize_ratio = video_a / output_height_want
                video_a = output_height_want
                video_crop = (video_crop[0] / resize_ratio,
                              video_crop[1] / resize_ratio)
            else:
                resize_ratio = video_crop[1] / output_height_want
                video_crop = (width / resize_ratio,
                              output_height_want)
            video_resize = (width / resize_ratio,
                            height / resize_ratio)
        else:
            resize_ratio = 1
            video_resize = (width, height)

        circle_radius = (1.5575 * video_crop[1]) // 2
        circle_thickness = max(video_crop[1] // 120, 1)

        if display_all:
            output_size = (video_a, video_a)
        elif circle_crop:
            output_size = video_crop
        else:
            output_size = (math.sqrt(video_crop[0]**2 +
                                     video_crop[1]**2), video_crop[1])

        video_resize = ceil_even(video_resize)
        video_crop = ceil_even(video_crop)
        output_size = ceil_even(output_size)
        image_info = skia.ImageInfo.Make(*video_crop, skia.ColorType.kGray_8_ColorType, skia.AlphaType.kOpaque_AlphaType)
        surface = skia.Surface.MakeRaster(image_info)
        #surface = skia.Surface(*video_crop)
        with surface as canvas:
            if circle_crop:  # 创建绘制圆形的 Paint 对象
                paint = skia.Paint(
                    Color=skia.ColorWHITE,  # 圆形的颜色
                    Style=skia.Paint.kFill_Style,  # 填充圆形
                    AntiAlias=True)

                x, y = video_crop
                x //= 2
                y //= 2
                # 绘制圆形
                canvas.drawCircle(x, y, x, paint)
                #print("2", time.time() - t)
            else:
                canvas.clear(skia.ColorWHITE)

        return cls(video_resize=video_resize,
                   video_crop=video_crop,
                   output_size=output_size,
                   circle_radius=circle_radius,
                   circle_thickness=circle_thickness,
                   resize_ratio=resize_ratio,
                   cover=get_skia_picture(cover),
                   image_alpha=surface.makeImageSnapshot())


if __name__ == "__main__":
    a = PaintMsg.from_video_info(
        1920,
        1920,
        cover=
        r"E:\Code\py-rotaeno-stablizer-gui\test\Songs_today-is-not-tomorrow.png"
    )
    print(a)
