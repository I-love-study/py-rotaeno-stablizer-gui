import sys
if sys.platform == "win32":
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
try:
    from tkinter.filedialog import askopenfilename
    use_tkinter = True
except ModuleNotFoundError:
    use_tkinter = False

"""Still in WIP"""