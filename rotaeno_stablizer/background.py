import math
from dataclasses import dataclass, field
from os import PathLike

from PIL import Image, ImageDraw, ImageEnhance

from .utils import get_picture


def ceil_even(num: tuple[float, float]) -> tuple[int, int]:
    def ceil_single(n):
        return math.ceil(n / 2) * 2
    return (ceil_single(num[0]), ceil_single(num[1]))


@dataclass
class PaintMsg:
    video_resize: tuple[int, int]
    video_crop: tuple[int, int]
    output_size: tuple[int, int]
    circle_radius: float
    circle_thickness: float
    resize_ratio: float
    cover: Image.Image | None
    background: Image.Image = field(init=False)
    image_alpha: Image.Image

    def __post_init__(self):
        self.background = self.generate_background()

    def generate_background(self):
        width, height = self.output_size
        r = self.circle_radius
        thickness = self.circle_thickness

        brightness = 0.2

        image = Image.new("RGB", (width, height))
        convert_x = int((width - r * 2) / 2)
        convert_y = int((height - r * 2) / 2)
        if self.cover is not None:
            cover_resized = self.cover.resize((int(r * 2), int(r * 2)))
            cover_resized = ImageEnhance.Brightness(cover_resized).enhance(brightness)
            image.paste(cover_resized, (convert_x, convert_y))

        circle_image = Image.new("RGBA", (width * 2, height * 2))
        ImageDraw.Draw(circle_image).circle((width, height),
                                            r * 2,
                                            outline="white",
                                            width=int(thickness * 2))
        circle_image = circle_image.resize((width, height))
        image.paste(circle_image, mask=circle_image)

        # 返回绘制结果
        return image

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
                video_crop = (width / resize_ratio, output_height_want)
            video_resize = (width / resize_ratio, height / resize_ratio)
        else:
            resize_ratio = 1
            video_resize = (width, height)

        # ciricle radius is from https://github.com/Lawrenceeeeeeee/python_rotaeno_stabilizer
        circle_radius = (1.565 * video_crop[1]) // 2
        circle_thickness = max(video_crop[1] // 120, 1)

        if display_all:
            output_size = (video_a, video_a)
        elif circle_crop:
            output_size = video_crop
        else:
            output_size = (math.sqrt(video_crop[0]**2 + video_crop[1]**2),
                           video_crop[1])

        video_resize = ceil_even(video_resize)
        video_crop = ceil_even(video_crop)
        output_size = ceil_even(output_size)

        alpha_image = Image.new("L", (video_crop[0] * 2, video_crop[1] * 2))
        ImageDraw.Draw(alpha_image).circle(video_crop, video_crop[0], "white")
        alpha_image = alpha_image.resize(video_crop)

        return cls(video_resize=video_resize,
                   video_crop=video_crop,
                   output_size=output_size,
                   circle_radius=circle_radius,
                   circle_thickness=circle_thickness,
                   resize_ratio=resize_ratio,
                   cover=get_picture(cover),
                   image_alpha=alpha_image)


if __name__ == "__main__":
    a = PaintMsg.from_video_info(
        1920,
        1920,
        cover=r"E:\Code\py-rotaeno-stablizer-gui\test\Songs_today-is-not-tomorrow.png")
    a.background.save("test.jpg")
