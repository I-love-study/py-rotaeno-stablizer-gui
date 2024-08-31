import sys
import urllib.request
from os import PathLike

import numpy as np
from rich import get_console
from rich.progress import ProgressColumn, Task
from rich.text import Text
import skia


class FPSColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("FPS: ?", style="progress.data.speed")
        return Text(f"FPS: {int(speed)}", style="progress.data.speed")

def get_skia_picture(background: str | PathLike | None) -> skia.Image | None:
    if background is None:
        return
    if isinstance(background,
                    str) and background.startswith("http"):
        with urllib.request.urlopen(background) as f:
            r = f.read()
        return skia.Image.MakeFromEncoded(r)
    return skia.Image.open(background)

    
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