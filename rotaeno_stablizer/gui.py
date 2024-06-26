"""Still in WIP"""
import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from tkinter.filedialog import askopenfilename
import traceback
import ttkbootstrap as ttk

from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import tomllib

from .ffmpeg import FFMpegHWTest, FFMpegReader
from . import Rotaeno


class Gui(ttk.Frame):

    queue = Queue()
    searching = False

    def __init__(self, master):
        #ttk.font.nametofont("TkDefaultFont").configure(
        #    family="Consolas", size=10)
        ttk.font.nametofont("TkDefaultFont").configure(
            family="Source Han Sans HC", size=10, weight=NORMAL)

        super().__init__(master, padding=15)
        self.config = tomllib.loads(
            Path("config.toml").read_text(encoding="UTF-8"))
        self.pack(fill=BOTH, expand=YES)

        # application variables
        self.path_var = ttk.StringVar(value="")
        self.out_path_var = ttk.StringVar(value="")

        self.video_info_var = ttk.StringVar(value="Video Info")

        self.config_lf = ttk.Frame(self)

        self.coder_frame = ttk.Frame(self.config_lf)
        self.coder_frame.grid(row=0, column=0)

        self.args_frame = ttk.Frame(self.config_lf)
        self.path_lf = ttk.Labelframe(self.args_frame,
                                      text="  路径  ",
                                      padding=15)
        self.path_lf.pack(fill=BOTH, expand=YES)
        self.option_lf = ttk.Labelframe(self.args_frame,
                                        text=" 选项 ",
                                        padding=15)
        self.option_lf.pack(fill=BOTH, expand=YES)

        self.video_info_lf = ttk.LabelFrame(self.config_lf,
                                            text="视频信息",
                                            padding=15)
        ttk.Label(self.video_info_lf,
                  textvariable=self.video_info_var,
                  font=("Consolas", 10)).pack()
        self.video_info_lf.grid(row=0, column=2, sticky=NSEW)

        self.args_frame.grid(row=0, column=1, padx=10)
        self.all_vars = {}
        self.encoder_vars = {}
        self.create_file_row()
        self.create_option_row()
        self.create_encoder()
        self.config_lf.pack()

        self.progressbar = ttk.Progressbar(master=self,
                                           mode=DETERMINATE,
                                           bootstyle=SUCCESS)
        self.progressbar.pack(fill=X, expand=YES, pady=10)
        self.run_button = ttk.Button(self,
                                     text="Run",
                                     command=self.running)
        self.run_button.pack(side=RIGHT, pady=(10, 0))

    def create_file_row(self):
        """Add path row to labelframe"""
        path_row = ttk.Frame(self.path_lf)
        path_row.pack(fill=X, expand=YES)
        path_lbl = ttk.Label(path_row, text="Input Video", width=11)
        path_lbl.pack(side=LEFT, padx=(15, 0))
        path_ent = ttk.Entry(path_row, textvariable=self.path_var)
        path_ent.pack(side=LEFT, fill=X, expand=YES, padx=5)
        browse_btn = ttk.Button(master=path_row,
                                text="Browse",
                                command=self.on_browse_video,
                                width=8)
        browse_btn.pack(side=LEFT, padx=5)

        path_row = ttk.Frame(self.path_lf)
        path_row.pack(fill=X, expand=YES, pady=15)
        path_lbl = ttk.Label(path_row, text="Output Video", width=11)
        path_lbl.pack(side=LEFT, padx=(15, 0))
        path_ent = ttk.Entry(path_row, textvariable=self.out_path_var)
        path_ent.pack(side=LEFT, fill=X, expand=YES, padx=5)
        browse_btn = ttk.Button(master=path_row,
                                text="Browse",
                                command=self.on_browse_out_video,
                                width=8)
        browse_btn.pack(side=LEFT, padx=5)

        path_row = ttk.Frame(self.path_lf)
        path_row.pack(fill=X, expand=YES)
        path_lbl = ttk.Label(path_row, text="Background", width=11)
        path_lbl.pack(side=LEFT, padx=(15, 0))
        self.all_vars["background"] = ttk.StringVar()
        path_ent = ttk.Entry(path_row,
                             textvariable=self.all_vars["background"])
        path_ent.pack(side=LEFT, fill=X, expand=YES, padx=5)
        browse_btn = ttk.Button(master=path_row,
                                text="Browse",
                                command=self.on_browse_image,
                                width=8)
        browse_btn.pack(side=LEFT, padx=5)

    def create_option_row(self):
        entry_frame = ttk.Frame(self.option_lf)
        path_lbl = ttk.Label(entry_frame, text="Output Video Height")
        path_lbl.grid(row=0, column=0)
        self.all_vars["height"] = ttk.IntVar(
            value=self.config["video"]["height"])
        path_ent = ttk.Entry(entry_frame,
                             textvariable=self.all_vars["height"],
                             width=8)
        path_ent.grid(row=0, column=1, padx=5)

        op3 = ttk.Label(entry_frame, text='Window Size')
        op3.grid(row=1, column=0)
        self.all_vars["window_size"] = ttk.IntVar(
            value=self.config["video"]["window_size"])
        op3 = ttk.Entry(entry_frame,
                        textvariable=self.all_vars["window_size"],
                        width=8)
        op3.grid(row=1, column=1, pady=10)

        op3 = ttk.Label(entry_frame, text='Rotate Version')
        op3.grid(row=2, column=0)
        self.all_vars["rotation_version"] = ttk.IntVar(
            value=self.config["video"]["rotation_version"])
        op3 = ttk.Entry(
            entry_frame,
            textvariable=self.all_vars["rotation_version"],
            width=8)
        op3.grid(row=2, column=1)

        check_frame = ttk.Frame(self.option_lf)
        bool_var = ["auto_crop", "circle_crop", "display_all"]
        for i, name in enumerate(bool_var):
            var = ttk.BooleanVar(value=self.config["video"][name])
            button = ttk.Checkbutton(check_frame,
                                     text=name,
                                     state=ACTIVE,
                                     variable=var)
            self.all_vars[name] = var
            button.grid(row=i, column=2, pady=10, sticky=W)

        entry_frame.pack(fill=X,
                         expand=YES,
                         pady=15,
                         padx=(0, 10),
                         side=LEFT)
        check_frame.pack(fill=X, expand=YES, pady=15)

    def create_encoder(self):
        self.encoder_lf = ttk.LabelFrame(self.coder_frame,
                                         text="Encoder Info",
                                         padding=15)
        self.encoder_lf.pack(fill=X, expand=YES)

        type_row = ttk.Frame(self.encoder_lf)
        type_row.pack(fill=X, expand=YES)
        ttk.Label(type_row, text='Encoder', width=8).pack(side=LEFT,
                                                          pady=5,
                                                          padx=5,
                                                          anchor="w")
        self.encoder_vars["codec"] = ttk.StringVar(
            value=self.config["encode"]["codec"])
        ttk.Entry(type_row,
                  textvariable=self.encoder_vars["codec"],
                  width=10).pack(side=LEFT, pady=5, anchor="w")

        type_row = ttk.Frame(self.encoder_lf)
        type_row.pack(fill=X, expand=YES)
        ttk.Label(type_row, text='Bitrate', width=8).pack(side=LEFT,
                                                          pady=5,
                                                          padx=5,
                                                          anchor="w")
        self.encoder_vars["bitrate"] = ttk.StringVar(
            value=self.config["encode"]["bitrate"])
        ttk.Entry(type_row,
                  textvariable=self.encoder_vars["bitrate"],
                  width=10).pack(side=LEFT, pady=5, anchor="w")

        type_row = ttk.Frame(self.encoder_lf)
        type_row.pack(fill=X, expand=YES)
        ttk.Label(type_row, text='FPS', width=8).pack(side=LEFT,
                                                      pady=5,
                                                      padx=5,
                                                      anchor="w")
        self.encoder_vars["fps"] = ttk.DoubleVar(value=0)
        ttk.Entry(type_row,
                  textvariable=self.encoder_vars["fps"],
                  width=10).pack(side=LEFT, pady=5, anchor="w")

        self.coder_check_lf = ttk.LabelFrame(self.coder_frame,
                                             text="Codec check",
                                             padding=15)
        self.codec_entry = ttk.Entry(self.coder_check_lf, width=10)
        self.codec_entry.grid(row=0, column=0)
        self.codec_button = ttk.Button(self.coder_check_lf,
                                       text="Check",
                                       command=self.get_codec_config)
        self.codec_button.grid(row=0, column=1)
        self.codec_list = ttk.Treeview(self.coder_check_lf,
                                       height=4,
                                       show='headings')
        self.codec_list.configure(columns=("Type", "Codec_name"))
        self.codec_list.heading("Type", text="Type")
        self.codec_list.heading("Codec_name", text="Codec Name")
        self.codec_list.column('Type', width=90, anchor=CENTER)
        self.codec_list.column('Codec_name', width=150, anchor=CENTER)
        self.codec_list.grid(row=1,
                             column=0,
                             columnspan=2,
                             pady=(10, 0))
        self.coder_check_lf.pack(fill=X, expand=YES)

    def get_codec_config(self):
        codec = self.codec_entry.get()
        if codec == "":
            Messagebox.show_warning("codec 输入为空")
            return

        encoders, decoders = FFMpegHWTest().run(codec)

        for child in self.codec_list.get_children():
            self.codec_list.delete(child)

        for encoder in encoders:
            self.codec_list.insert("",
                                   END,
                                   values=("Encoder", encoder))
        for decoder in decoders:
            self.codec_list.insert("",
                                   END,
                                   values=("Decoder", decoder))

    def on_browse_video(self):
        """Callback for directory browse"""
        filepath = askopenfilename(
            title="请选择输入视频",
            defaultextension=".mp4",
            filetypes=[("Video", ".mp4 .m4v .avi .mov .flv .mkv"),
                       ("mp4 video", ".mp4 .m4v"), ('avi', '.avi'),
                       ("Mov video", ".mov"),
                       ('Any other that ffmpeg support', '*')])
        if not filepath:
            return
        filepath = Path(filepath)
        self.path_var.set(str(filepath))
        self.out_path_var.set(
            str(filepath.parent / self.config["other"]
                ["default_output_filename"].format(filepath.stem)) +
            ".mp4")
        self.reader = FFMpegReader(filepath)
        key_len = max(map(len, self.reader.info))
        self.video_info_var.set(
            "\n".join(f"{k:{key_len}}:" +
                      str(round(v, 4) if isinstance(v, float) else v)
                      for k, v in self.reader.info.items()))

    def on_browse_out_video(self):
        """Callback for directory browse"""
        p = Path(self.out_path_var.get())
        filepath = askopenfilename(
            title="请选择输入视频",
            defaultextension=".mp4",
            initialdir=p.parent,
            initialfile=p.name,
            filetypes=[("Video", ".mp4 .m4v .avi .mov .flv .mkv"),
                       ("mp4 video", ".mp4 .m4v"), ('avi', '.avi'),
                       ("Mov video", ".mov"),
                       ('Any other that ffmpeg support', '*')])
        if not filepath:
            return
        filepath = Path(filepath)
        self.out_path_var.set(str(filepath))

    def on_browse_image(self):
        """Callback for directory browse"""
        filepath = askopenfilename(
            title="请选择输入图片",
            defaultextension=".jpg",
            filetypes=[("图片", ".jpg .jpeg .png .bmp .tiff .gif"),
                       ("JPG图片", ".jpg .jpeg"), ('PNG图片', '.png'),
                       ('其他乱七八糟类型的图片', '*')])
        if filepath:
            self.all_vars["background"].set(filepath)

    def running(self):
        arg_dict = {
            key: value.get()
            for key, value in self.all_vars.items()
        }
        if arg_dict["background"] == "":
            arg_dict["background"] = None
        rotaeno = Rotaeno(**arg_dict)
        encoder_arg = {
            key: value.get()
            for key, value in self.encoder_vars.items()
        }

        import threading
        exception_args = None

        event = threading.Event()

        def check_event():
            if not event.is_set():
                self.master.after(100, check_event)
                return
            if exception_args is not None:
                err = traceback.format_exception(
                    exception_args.exc_type,
                    exception_args.exc_value,
                    exception_args.exc_traceback,
                    limit=2)
                Messagebox.show_error(
                    "".join(err),
                    (f"{exception_args.exc_type.__name__}: "
                     f"{exception_args.exc_value}"))
            else:
                Messagebox.show_info("Process Success")
            exit()

        def run_stablizer():
            nonlocal exception_args
            r = rotaeno.run_gui(self.reader,
                                self.out_path_var.get(),
                                **encoder_arg,
                                progressbar=self.progressbar)
            if not r[0]:
                exception_args = r[1]
            event.set()

        thread = threading.Thread(target=run_stablizer, daemon=True)
        thread.start()
        self.master.after(100, check_event)


if __name__ == '__main__':
    import logging
    from rich.logging import RichHandler
    logging.basicConfig(level="INFO",
                        format="%(message)s",
                        datefmt="[%X]",
                        handlers=[RichHandler(rich_tracebacks=True)])
    logging.getLogger("rich").setLevel("DEBUG")
    p = Path(__file__).parent / "logo.png"
    app = ttk.Window("Rotaeno Stablizer", "darkly", p)
    Gui(app)
    app.mainloop()
