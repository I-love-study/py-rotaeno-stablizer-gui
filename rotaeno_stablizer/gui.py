from functools import wraps
from importlib import resources
from pathlib import Path
from tkinter.filedialog import askopenfilename
from typing import Callable
from webbrowser import open as webopen

from PIL import Image

try:
    from CTkMenuBar import CTkMenuBar
    from CTkMessagebox import CTkMessagebox
    from CTkTable import CTkTable
    from customtkinter import (
        BooleanVar,
        CTk,
        CTkButton,
        CTkCheckBox,
        CTkEntry,
        CTkFont,
        CTkFrame,
        CTkImage,
        CTkLabel,
        CTkProgressBar,
        CTkScrollableFrame,
        CTkToplevel,
        IntVar,
        StringVar,
        ThemeManager,
    )
    from PIL import ImageTk
except ImportError as e:
    raise ImportError("Cannot import customtkinter, fix it by using `pip install rotaeno_stablizer[gui]`") from e

from . import Rotaeno
from .config import config_data
from .ffmpeg import FFMpegHWTest

video_type = [("Video", ".mp4 .m4v .avi .mov .flv .mkv"), ("mp4 video", ".mp4 .m4v"),
              ('avi', '.avi'), ("Mov video", ".mov"),
              ('Any other that ffmpeg support', '*')]
image_type = [("Image", ".jpg .jpeg .png .bmp .tiff .gif"), ("JPG", ".jpg .jpeg"),
              ('PNG', '.png'), ('其他乱七八糟类型的图片', '*')]


def create_logos():
    with resources.files("rotaeno_stablizer").joinpath("rotaeno_logo_black.png").open("rb") as f:
        logo_black = Image.open(f).copy()
    logo_white = Image.new("RGBA", logo_black.size)
    logo_white.putdata([(255, 255, 255, pixel[3]) if pixel[:3] == (0, 0, 0) else pixel
                        for pixel in logo_black.getdata()])
    return logo_black, logo_white

logo_black, logo_white = create_logos()

def raise_messagebox(master=None, icon="warning"):

    def decorator(func: Callable[..., None]):

        @wraps(func)
        def wrapper(*args, **kw):
            try:
                func(*args, **kw)
            except Exception as e:
                CTkMessagebox(master,
                              title=e.__class__.__name__,
                              message=str(e),
                              icon=icon)

        return wrapper

    return decorator


class PathFrame(CTkFrame):
    """Path Chooser"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        inner = CTkFrame(self, fg_color="transparent")
        inner.pack(padx=10, pady=0, fill="none", expand=True)

        self.input_video_ = StringVar()
        self.cover_ = StringVar()
        self.output_video_ = StringVar()
        self.output_mask_video_ = StringVar()
        self.output_cmd_data_ = StringVar()
        self.need_output_video_ = BooleanVar()
        self.need_output_mask_video_ = BooleanVar()
        self.need_output_cmd_data_ = BooleanVar()
        self.force_rewrite_ = BooleanVar()

        def input_wrapper():
            filepath = askopenfilename(title="请选择输入视频",
                                       defaultextension=".mp4",
                                       filetypes=video_type)
            filepath = Path(filepath)
            self.input_video_.set(str(filepath))
            self.ctk_input._entry.xview_moveto(1)
            self.output_video_.set(str(filepath.with_stem(filepath.stem + "_out")))
            self.ctk_output._entry.xview_moveto(1)
            self.output_mask_video_.set(
                str(filepath.with_stem(filepath.stem.removesuffix("_out") + "_mask")))
            self.ctk_mask._entry.xview_moveto(1)
            self.output_cmd_data_.set(
                str(
                    filepath.with_stem(filepath.stem.removesuffix("_out") +
                                       "_rotate").with_suffix(".cmd")))
            self.ctk_data._entry.xview_moveto(1)

        def cover_wrapper():
            filepath = askopenfilename(title="请选择输入图像",
                                       defaultextension=".jpg",
                                       filetypes=image_type)
            self.cover_.set(filepath)

        def output_wrapper():
            p = Path(self.output_mask_video_.get())
            filepath = askopenfilename(title="请选择输出掩码视频",
                                       defaultextension=".mp4",
                                       initialdir=p.parent,
                                       initialfile=p.name,
                                       filetypes=video_type)
            self.output_video_.set(filepath)

        def output_mask_wrapper():
            p = Path(self.output_video)
            filepath = askopenfilename(title="请选择输出视频",
                                       defaultextension=".mp4",
                                       initialdir=p.parent,
                                       initialfile=p.name,
                                       filetypes=video_type)
            filepath = Path(filepath)
            self.output_video_.set(str(filepath))

        def output_cmd_wrapper():
            p = Path(self.output_video)
            filepath = askopenfilename(title="请选择输出 Rotaeno 数据",
                                       defaultextension=".cmd",
                                       initialdir=p.parent,
                                       initialfile=p.name,
                                       filetypes=[("FFmpeg Cmd Output", "*")])
            filepath = Path(filepath)
            self.output_cmd_data_.set(str(filepath))

        inner.grid_columnconfigure(list(range(3)), pad=15)
        inner.grid_rowconfigure(list(range(6)), pad=15)
        inner.grid_rowconfigure(6, pad=0)

        CTkLabel(inner, text="Input Video").grid(row=0, column=1, sticky="W")
        self.ctk_input = CTkEntry(inner, width=200, textvariable=self.input_video_)
        self.ctk_input.grid(row=0, column=2)
        CTkButton(inner, width=50, text="Select", command=input_wrapper).grid(row=0,
                                                                              column=3)

        CTkLabel(inner, text="Cover").grid(row=1, column=1, sticky="W")
        CTkEntry(inner, width=200, textvariable=self.cover_).grid(row=1, column=2)
        CTkButton(inner, width=50, text="Select", command=cover_wrapper).grid(row=1,
                                                                              column=3)


        p = CTkProgressBar(master=inner, height=5, width=350)
        p.set(1)
        p.grid(row=2, column=0, columnspan=4)

        CTkCheckBox(inner, text="Output Video",
                    variable=self.need_output_video_).grid(row=3, column=1, sticky="W")
        self.ctk_output = CTkEntry(inner, width=200, textvariable=self.output_video_)
        self.ctk_output.grid(row=3, column=2)
        CTkButton(inner, width=50, text="Select", command=output_wrapper).grid(row=3,
                                                                               column=3)

        CTkCheckBox(inner, text="Mask Video",
                    variable=self.need_output_mask_video_).grid(row=4,
                                                                column=1,
                                                                sticky="W")
        self.ctk_mask = CTkEntry(inner, width=200, textvariable=self.output_mask_video_)
        self.ctk_mask.grid(row=4, column=2)
        CTkButton(inner, width=50, text="Select",
                  command=output_mask_wrapper).grid(row=4, column=3)

        CTkCheckBox(inner, text="Rotated Data",
                    variable=self.need_output_cmd_data_).grid(row=5,
                                                              column=1,
                                                              sticky="W")
        self.ctk_data = CTkEntry(inner, width=200, textvariable=self.output_cmd_data_)
        self.ctk_data.grid(row=5, column=2)
        CTkButton(inner, width=50, text="Select",
                  command=output_cmd_wrapper).grid(row=5, column=3)

        down_inner = CTkFrame(self, fg_color="transparent")
        down_inner.pack(padx=10, pady=10, fill="x", expand=True)
        self.start_button = CTkButton(down_inner, text="Start")
        self.start_button.pack(side="right")
        CTkCheckBox(down_inner, text="Force rewrite", variable=self.force_rewrite_).pack(side="left")


    @property
    def input_video(self):
        return self.input_video_.get()

    @property
    def output_video(self):
        return self.output_video_.get()

    @property
    def need_output_video(self):
        return self.need_output_video_.get()

    @property
    def mask_video(self):
        return self.output_mask_video_.get()

    @property
    def need_mask_video(self):
        return self.need_output_mask_video_.get()

    @property
    def output_cmd_data(self):
        return self.output_cmd_data_.get()

    @property
    def need_output_cmd_data(self):
        return self.need_output_cmd_data_.get()

    @property
    def force_rewrite(self):
        return self.force_rewrite_.get()

    @property
    def cover(self):
        return self.cover_.get()

class CodecFrame(CTkFrame):
    """Codec"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        width = 250
        image_title = CTkImage(light_image=logo_black,
                               dark_image=logo_white,
                               size=(width, width * 168 // 523))
        image_label = CTkLabel(self, image=image_title, text="")  # display image with a CTkLabel
        image_label.pack(padx=5, pady=5, fill="none", expand=True)

        inner = CTkFrame(self, fg_color="transparent")
        inner.pack(padx=10, pady=10, fill="none")

        self.encoder_ = StringVar(value=config_data["codec"]["encoder"])
        self.decoder_ = StringVar(value=config_data["codec"]["decoder"])
        self.bitrate_ = StringVar(value=config_data["codec"]["bitrate"])
        self.fps_ = StringVar()
        self.height_ = IntVar(value=config_data["video"]["height"])
        self.rotation_version_ = IntVar(value=config_data["video"]["rotation_version"])

        inner.grid_columnconfigure(list(range(3)), pad=15)
        inner.grid_rowconfigure(list(range(6)), pad=15)

        CTkLabel(inner, text="Decoder").grid(row=0, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.encoder_).grid(row=0, column=1)

        CTkLabel(inner, text="Encoder").grid(row=1, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.decoder_).grid(row=1, column=1)

        CTkLabel(inner, text="Bitrate").grid(row=2, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.bitrate_).grid(row=2, column=1)

        CTkLabel(inner, text="FPS").grid(row=3, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.fps_).grid(row=3, column=1)

        CTkLabel(inner, text="Output video height").grid(row=4, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.height_).grid(row=4, column=1)

        CTkLabel(inner, text="Rotaeno version").grid(row=5, column=0, sticky="W")
        CTkEntry(inner, width=100, textvariable=self.rotation_version_).grid(row=5,
                                                                             column=1)

    @property
    def encoder(self):
        return self.encoder_.get()

    @property
    def decoder(self):
        return self.decoder_.get()

    @property
    def bitrate(self):
        return self.bitrate_.get()

    @property
    def fps(self):
        return self.fps_.get()

    @property
    def height(self):
        return self.height_.get()

    @property
    def rotation_version(self):
        return self.rotation_version_.get()

class OptionFrame(CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        inner = CTkFrame(self, fg_color="transparent")
        inner.pack(padx=10, pady=10, fill="none", expand=True)

        self.auto_crop_ = BooleanVar(value=config_data["video"]["auto_crop"])
        self.circle_crop_ = BooleanVar(value=config_data["video"]["circle_crop"])
        self.display_all_ = BooleanVar(value=config_data["video"]["display_all"])
        self.auto_crop_ = BooleanVar(value=config_data["video"]["auto_crop"])


        inner.grid_columnconfigure(list(range(4)), pad=15)

        CTkCheckBox(inner, text="Auto crop", variable=self.auto_crop_).grid(row=0,
                                                                            column=0)
        CTkCheckBox(inner, text="Circle crop",
                    variable=self.circle_crop_).grid(row=0, column=1)
        CTkCheckBox(inner, text="Display all",
                    variable=self.display_all_).grid(row=0, column=2)


    @property
    def auto_crop(self):
        return self.auto_crop_.get()

    @property
    def circle_crop(self):
        return self.circle_crop_.get()

    @property
    def display_all(self):
        return self.display_all_.get()

class HWTestFrame(CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        inner = CTkFrame(self, fg_color="transparent")
        inner.pack(padx=5, pady=5, fill="none", expand=True)

        inner.grid_columnconfigure(list(range(3)), pad=15)
        inner.grid_rowconfigure(list(range(3)), pad=15)

        self.codec = StringVar()
        CTkLabel(inner, text="Codec").grid(row=0, column=0, sticky="W")
        entry = CTkEntry(inner, width=100, textvariable=self.codec)
        entry.grid(row=0, column=1)
        entry.bind("<Return>", self.update_table)
        CTkButton(inner, width=50, text="Select",
                  command=self.update_table).grid(row=0, column=2)
        table_frame = CTkScrollableFrame(inner, height=250)
        self.table = CTkTable(table_frame,
                              corner_radius=0,
                              column=2,
                              row=9,
                              border_width=2,
                              width=50,
                              values=[["Codec", "Type"]])
        self.table.pack(fill="both")
        table_frame.grid(row=1, columnspan=3)

    def update_table(self, entry_event=None) -> None:
        codec = self.codec.get()
        try:
            encoders, decoders = FFMpegHWTest().run(codec)
        except Exception as e:
            CTkMessagebox(title="Error", message=str(e), icon="cancel")
            return
        self.table.delete_rows(range(1, self.table.rows))

        for i in encoders:
            self.table.add_row([i, "Encoder"])
        for i in decoders:
            self.table.add_row([i, "Decoder"])


class AboutWindow(CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About the Project")
        with resources.files("rotaeno_stablizer").joinpath("logo.png").open("rb") as f:
            logo_image = Image.open(f).copy()
            icon = ImageTk.PhotoImage(logo_image)
        self.wm_iconbitmap()
        self.iconphoto(True, icon)

        self.geometry("550x240")
        self.resizable(False, False)
        self.grab_set()

        top_frame = CTkFrame(self, fg_color="transparent")
        top_frame.pack(padx=20, pady=(20, 10), fill="x")

        icon_img = CTkImage(logo_image, size=(64, 64))
        icon_label = CTkLabel(top_frame, image=icon_img, text="")
        icon_label.grid(row=0, column=0, padx=(0, 20), sticky="w")

        right_frame = CTkFrame(top_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="w")

        logo_img = CTkImage(light_image=logo_black,
                            dark_image=logo_white,
                            size=(120, 40))
        logo_label = CTkLabel(right_frame, image=logo_img, text="")
        logo_label.grid(row=0, column=0, padx=(0, 10))

        title_label = CTkLabel(right_frame, text="Stablizer", font=CTkFont(size=30, weight="bold"))
        title_label.grid(row=0, column=1, sticky="w")

        info_frame = CTkFrame(self, fg_color="transparent")
        info_frame.pack(padx=20, pady=5, anchor="w")

        CTkLabel(info_frame, text="作者：ILStudy").pack(anchor="w", pady=2)
        site = CTkLabel(info_frame, text="项目地址：https://github.com/I-love-study/py-rotaeno-stablizer-gui")
        assert site is not None
        site._label.bind("<Button-1>", lambda event: webopen("https://github.com/I-love-study/py-rotaeno-stablizer-gui"))
        site._label.bind("<Enter>", lambda event: site.configure(font=CTkFont(underline=True), cursor="hand2"))
        site._label.bind("<Leave>", lambda event: site.configure(font=CTkFont(underline=False), cursor="arrow"))
        site.pack(anchor="w", pady=2)

        CTkButton(self, text="关闭", command=self.destroy).pack(pady=(10, 20))

class App(CTk):

    def __init__(self):
        super().__init__()

        # Title & Icon
        self.title("Rotaeno Stablizer")
        with resources.files("rotaeno_stablizer").joinpath("logo.png").open("rb") as f:
            icon = ImageTk.PhotoImage(Image.open(f).copy())
        self.wm_iconbitmap()
        self.iconphoto(True, icon)

        self.start_run = False

        menu = CTkMenuBar(master=self, bg_color="transparent")
        menu.add_cascade("About project", self.show_about_us)
        menu.grid(columnspan=3, sticky="we")

        # Build frame
        self.codec_frame = CodecFrame(self, border_width=2)
        self.hw_frame = HWTestFrame(self, border_width=2)
        self.path_frame = PathFrame(self, border_width=2)
        self.option_frame = OptionFrame(self, border_width=2)
        self.start_button = self.path_frame.start_button
        self.start_button.configure(command=self.start)
        self.build()

    def build(self):
        self.codec_frame.grid(row=1, column=0, rowspan=2, padx=5, pady=5, sticky="nsew")
        self.path_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.hw_frame.grid(row=1, column=2, rowspan=2, padx=5, pady=5, sticky="nsew")
        self.option_frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

    def show_about_us(self):
        AboutWindow(self)

    @raise_messagebox()
    def start(self):
        out_path = Path(self.path_frame.output_video)
        if out_path.exists() and not self.path_frame.force_rewrite:
            msg = CTkMessagebox(title="输出路径已存在\n是否覆盖",
                                icon="question",
                                option_1="Yes",
                                option_2="False")
            if msg.get() == "False":
                return
        self.start_run = True
        self.destroy()

def main():
    app = App()
    ThemeManager.theme["CTkFont"] = CTkFont("Sarasa UI SC", 15)
    result = CTkMessagebox(None,
                           title="注意",
                           message="这并不是官方制作的视频稳定器。如有问题，请及时反馈。",
                           icon="warning",
                           option_1="不是？我不用了！",
                           option_2="我已知晓").get()
    if result == "我已知晓":
        app.mainloop()
    else:
        app.destroy()

    if not app.start_run:
        exit()

    circle_crop = app.option_frame.circle_crop
    auto_crop = app.option_frame.auto_crop
    display_all = app.option_frame.display_all

    rotation_version = app.codec_frame.rotation_version
    height = app.codec_frame.height
    encoder = app.codec_frame.encoder
    decoder = app.codec_frame.decoder
    bitrate = app.codec_frame.bitrate

    background = app.path_frame.cover
    input_video = app.path_frame.input_video
    need_output_video = app.path_frame.need_output_video
    need_output_mask = app.path_frame.need_mask_video
    need_output_cmd_data = app.path_frame.need_output_cmd_data
    output_video = app.path_frame.output_video if need_output_video else None
    output_mask = app.path_frame.mask_video if need_output_mask else None
    output_cmd = app.path_frame.output_cmd_data if need_output_cmd_data else None
    import logging
    logging.getLogger("rich").setLevel("DEBUG")
    rotaeno = Rotaeno(rotation_version=rotation_version,
                      circle_crop=circle_crop,
                      auto_crop=auto_crop,
                      display_all=display_all,
                      background=background if background else None,
                      height=height)

    input_video = Path(input_video)
    rotaeno.run(input_video=input_video,
                output_video=input_video.with_stem(input_video.stem + "_out")
                if output_video is None else output_video,
                encoder=encoder if encoder else None,
                decoder=decoder if decoder else None,
                bitrate=bitrate if decoder else None,
                ensure_rewrite=True,
                output_mask=output_mask,
                output_cmd=output_cmd,
            )


if __name__ == "__main__":
    main()
