from rich.progress import ProgressColumn, Task
from rich.text import Text
from rich import get_console
import numpy as np
import sys


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

    if foreground_image.shape[2] != 4:
        dep = slice(0, 2)
    else:
        dep = slice(None, None)

    # 粘贴前景图像到背景图像上
    background_image[
        offset_y_start:offset_y_end,
        offset_x_start:offset_x_end, dep] = foreground_image[
            offset_y_fore_start:offset_y_fore_end,
            offset_x_fore_start:offset_x_fore_end, dep]
    return background_image


if sys.platform == "win32":
    from msvcrt import getch as msvc_getch
    def getch() -> str:
        return msvc_getch().decode(errors="replace")
else:

    def getch() -> str:
        import sys
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def ask_confirm(text: str, default=True) -> bool:
    while True:
        console = get_console()
        options = "([y]/n)" if default else "(y/[n])"
        console.print(Text(text),
                    Text(options, style="prompt.choices"),
                    Text(": "),
                    end="")
        get = getch().lower()
        print(["n", "y"][default] if get in "\r\n" else get)
        if get in "\r\n":
            return default
        elif get == "y":
            return True
        elif get == "n":
            return False
        console.print("[prompt.invalid]Please enter Y or N")

    
