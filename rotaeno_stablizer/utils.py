import sys
import urllib.request
from os import PathLike, fspath
import os.path

from PIL import Image
from rich import get_console
from rich.progress import ProgressColumn, Task
from rich.text import Text



class FPSColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("FPS:   ?", style="progress.data.speed")
        return Text(f"FPS:{speed:>4.0f}", style="progress.data.speed")


def get_picture(background: str | PathLike | None) -> Image.Image | None:
    if background is None:
        return

    input_str = fspath(background)

    # 判断是网址还是本地路径，并加载图片
    if input_str.startswith(("http://", "https://")):
        with urllib.request.urlopen(input_str) as r:
            image = Image.open(r)
    elif os.path.isfile(input_str):
        image = Image.open(input_str)
    else:
        raise ValueError("Unknown input")

    return image


if sys.platform == "win32":
    from msvcrt import getch as msvc_getch

    def getch() -> str:
        return msvc_getch().decode(errors="replace")
else:

    def getch() -> str:
        import sys
        import termios
        import tty
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
