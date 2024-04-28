"""Still in WIP"""
import datetime
import pathlib
from queue import Queue
from threading import Thread
from tkinter.filedialog import askopenfilename
import ttkbootstrap as ttk

from ttkbootstrap.constants import *
from ttkbootstrap import utility

from .ffmpeg import FFMpegReader


class Gui(ttk.Frame):

    queue = Queue()
    searching = False

    def __init__(self, master):
        ttk.font.nametofont("TkDefaultFont").configure(
            family="Consolas", size=10)
        super().__init__(master, padding=15)
        self.pack(fill=BOTH, expand=YES)

        # application variables
        self.path_var = ttk.StringVar(value="")
        self.background_var = ttk.StringVar(value="")
        self.video_info_var = ttk.StringVar(value="Video Info")

        self.config_lf = ttk.Frame(self)
        # header and labelframe option container
        option_text = "  请输入设置  "
        self.path_lf = ttk.Labelframe(self.config_lf,
                                      text=option_text,
                                      padding=15)
        self.path_lf.grid(row=0,
                          column=1,
                          sticky=NSEW,
                          padx=10,
                          rowspan=2)

        self.video_info_lf = ttk.LabelFrame(self.config_lf,
                                            text="视频信息",
                                            padding=15)
        ttk.Label(self.video_info_lf,
                  textvariable=self.video_info_var,
                  font=("Consolas", 10)).pack()

        self.video_info_lf.grid(row=0,
                                column=2,
                                sticky=NSEW,
                                padx=10,
                                rowspan=2)
        self.encoder_lf = ttk.LabelFrame(self.config_lf,
                                         text="Encoder Info",
                                         padding=15)
        self.encoder_lf.grid(row=1, column=0)

        self.option_lf = ttk.Labelframe(self.config_lf,
                                        text=option_text,
                                        padding=15)
        self.option_lf.grid(row=0, column=0)

        self.create_file_row()
        #self.create_option()
        #self.create_term_row()
        self.create_type_row()
        self.create_encoder()
        #self.create_results_view()
        self.config_lf.pack()
        self.progressbar = ttk.Progressbar(master=self,
                                           mode=INDETERMINATE,
                                           bootstyle=(STRIPED,
                                                      SUCCESS))
        self.progressbar.pack(fill=X, expand=YES, pady=10)

    def create_file_row(self):
        """Add path row to labelframe"""
        path_row = ttk.Frame(self.path_lf)
        path_row.pack(fill=X, expand=YES, pady=15)
        path_lbl = ttk.Label(path_row, text="Input Video", width=10)
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
        path_lbl = ttk.Label(path_row, text="Background", width=10)
        path_lbl.pack(side=LEFT, padx=(15, 0))
        path_ent = ttk.Entry(path_row,
                             textvariable=self.background_var)
        path_ent.pack(side=LEFT, fill=X, expand=YES, padx=5)
        browse_btn = ttk.Button(master=path_row,
                                text="Browse",
                                command=self.on_browse_image,
                                width=8)
        browse_btn.pack(side=LEFT, padx=5)

        path_row = ttk.Frame(self.path_lf)
        path_row.pack(fill=X, expand=YES, pady=15)
        path_lbl = ttk.Label(path_row, text="Output Video Height")
        path_lbl.pack(side=LEFT, padx=5)
        path_ent = ttk.Entry(path_row,
                             textvariable=self.path_var,
                             width=8)
        path_ent.pack(side=LEFT, fill=X, padx=5)
        op3 = ttk.Label(path_row, text='Window Size')
        op3.pack(side=LEFT, pady=5, padx=5, anchor="w")
        op3 = ttk.Entry(path_row, show="3", width=8)
        op3.pack(side=LEFT, pady=5, anchor="w")

    def create_type_row(self):
        """Add type row to labelframe"""
        type_row = ttk.Frame(self.option_lf, )
        type_row.pack(fill=X, expand=YES)
        op1 = ttk.Checkbutton(type_row, text='Circle Crop')
        op1.pack(side=TOP, pady=5, anchor="w")
        op2 = ttk.Checkbutton(type_row, text='Auto Crop')
        op2.pack(side=TOP, pady=5, anchor="w")
        op3 = ttk.Checkbutton(type_row, text='Display All')
        op3.pack(side=TOP, pady=5, anchor="w")
        op3 = ttk.Checkbutton(type_row, text='Using V2 Rotate')
        op3.pack(side=TOP, pady=5, anchor="w")

    def create_encoder(self):
        type_row = ttk.Frame(self.encoder_lf)
        type_row.pack(fill=X, expand=YES)
        op3 = ttk.Label(type_row, text='Encoder', width=8)
        op3.pack(side=LEFT, pady=5, padx=5, anchor="w")
        op3 = ttk.Entry(type_row, show="s", width=8)
        op3.pack(side=LEFT, pady=5, anchor="w")

        type_row = ttk.Frame(self.encoder_lf)
        type_row.pack(fill=X, expand=YES)
        op3 = ttk.Label(type_row, text='Bitrate', width=8)
        op3.pack(side=LEFT, pady=5, padx=5, anchor="w")
        op3 = ttk.Entry(type_row, show="s", width=8)
        op3.pack(side=LEFT, pady=5, anchor="w")

    def on_browse_video(self):
        """Callback for directory browse"""
        filepath = askopenfilename(
            title="请选择输入视频",
            defaultextension=".jpg",
            filetypes=[("Video", ".mp4 .m4v .avi .mov .flv .mkv"),
                       ("mp4 video", ".mp4 .m4v"), ('avi', '.avi'),
                       ("Mov video", ".mov"),
                       ('Any other that ffmpeg support', '*')])
        if filepath:
            self.path_var.set(filepath)
        reader = FFMpegReader(filepath)
        key_len = max(map(len, reader.info))
        self.video_info_var.set(
            "\n".join(f"{k:{key_len}}:" +
                      str(round(v, 4) if isinstance(v, float) else v)
                      for k, v in reader.info.items()))

    def on_browse_image(self):
        """Callback for directory browse"""
        filepath = askopenfilename(
            title="请选择输入图片",
            defaultextension=".jpg",
            filetypes=[("图片", ".jpg .jpeg .png .bmp .tiff .gif"),
                       ("JPG图片", ".jpg .jpeg"), ('PNG图片', '.png'),
                       ('其他乱七八糟类型的图片', '*')])
        if filepath:
            self.background_var.set(filepath)


if __name__ == '__main__':

    app = ttk.Window("Rotaeno Stablizer", "darkly")
    Gui(app)
    app.mainloop()
