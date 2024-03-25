from rich.progress import ProgressColumn, Task
from rich.text import Text
import numpy as np


class FPSColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("FPS: ?", style="progress.data.speed")
        return Text(f"FPS: {int(speed)}", style="progress.data.speed")


def paste_image(background_image: np.ndarray,
                foreground_image: np.ndarray, offset_x: int,
                offset_y: int):
    # 确定前景图像在背景图像上的位置
    
    # 计算粘贴的区域
    if offset_x < 0:
        offset_x_start = None
        offset_x_end = None
    else:
        offset_x_start = offset_x
        offset_x_end = -offset_x
    if offset_y < 0:
        offset_y_start = None
        offset_y_end = None
    else:
        offset_y_start = offset_y
        offset_y_end = -offset_y

    # 计算前景图像在背景图像上的位置
    if offset_x > 0:
        offset_x_fore_start = None
        offset_x_fore_end = None
    else:
        offset_x_fore_start = -offset_x
        offset_x_fore_end = offset_x
    if offset_y > 0:
        offset_y_fore_start = None
        offset_y_fore_end = None
    else:
        offset_y_fore_start = -offset_y
        offset_y_fore_end = offset_y

    # 粘贴前景图像到背景图像上
    background_image[
        offset_y_start:offset_y_end,
        offset_x_start:offset_x_end, :] = foreground_image[
            offset_y_fore_start:offset_y_fore_end,
            offset_x_fore_start:offset_x_fore_end, :]
    return background_image
