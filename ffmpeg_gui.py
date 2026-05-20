import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime

# ==================== 常量 ====================
APP_NAME = "FFmpeg GUI 工具"
APP_VERSION = "1.0"
APP_AUTHOR = "洪旭涛"
APP_EMAIL = "hxt@uoes.edu.kg"

SUPPORTED_VIDEO = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts']
SUPPORTED_AUDIO = ['.mp3', '.wav', '.wma', '.aac', '.flac', '.m4a', '.ogg', '.opus']
SUPPORTED_SUBTITLE = ['.srt', '.ass', '.ssa', '.vtt']
SUPPORTED_ALL = SUPPORTED_VIDEO + SUPPORTED_AUDIO

OUTPUT_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v', 'mpg', 'mpeg', 'ts']
OUTPUT_AUDIO_FORMATS = ['mp3', 'wav', 'aac', 'flac', 'm4a', 'wma', 'ogg', 'opus']

VIDEO_CODECS = ['H.264 (libx264)', 'H.265 (libx265)', 'MPEG4', 'VP9', 'AV1', 'Copy (不重新编码)']
AUDIO_CODECS = ['AAC', 'MP3 (libmp3lame)', 'FLAC', 'PCM (pcm_s16le)', 'Copy (不重新编码)']

QUALITY_PRESETS = ['原始质量', '高质量 (CRF 18)', '中等质量 (CRF 23)', '低质量 (CRF 28)', '极低质量 (CRF 35)', '自定义']

SPEED_PRESETS = ['1.25X', '1.5X', '2X', '2.5X', '3X', '4X', '自定义']

RESOLUTION_PRESETS = ['原始分辨率', '1920x1080 (1080P)', '1280x720 (720P)', '854x480 (480P)', '640x360 (360P)', '自定义']


def get_config_path():
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "ffmpeg_gui_config.json"


def load_config():
    path = get_config_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"ffmpeg_path": "", "output_dir": "", "theme": "cosmo"}


def save_config(config):
    try:
        with open(get_config_path(), 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{m:02d}:{s:02d}.{ms:03d}"


def parse_time(time_str):
    time_str = time_str.strip()
    parts = time_str.replace(',', '.').split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


# ==================== 主应用 ====================
class FFmpegGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.config = load_config()
        self.files = []
        self.is_processing = False
        self.current_process = None

        self._build_ui()
        self._detect_ffmpeg()

    def _build_ui(self):
        self._build_menu()
        self._build_main_layout()
        self._build_status_bar()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="添加文件", command=self._add_files, accelerator="Ctrl+O")
        file_menu.add_command(label="添加文件夹", command=self._add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="清空列表", command=self._clear_files)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

        self.root.bind('<Control-o>', lambda e: self._add_files())

    def _build_main_layout(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        paned = ttk.Panedwindow(main_frame, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True)

        left_frame = self._build_left_panel()
        right_frame = self._build_right_panel()

        paned.add(left_frame, weight=35)
        paned.add(right_frame, weight=65)

    def _build_left_panel(self):
        frame = ttk.Labelframe(text=" 📁 任务列表 ", padding=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, pady=(0, 5))
        ttk.Button(btn_frame, text="➕ 添加文件", command=self._add_files, bootstyle="success").pack(side=LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="📂 添加文件夹", command=self._add_folder, bootstyle="info").pack(side=LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="🗑️ 清空", command=self._clear_files, bootstyle="danger-outline").pack(side=RIGHT)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=BOTH, expand=True)

        self.file_tree = ttk.Treeview(tree_frame, columns=("name", "size", "type"), show="headings", height=15)
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        self.file_tree.heading("type", text="类型")
        self.file_tree.column("name", width=180)
        self.file_tree.column("size", width=70, anchor=E)
        self.file_tree.column("type", width=60, anchor=CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        self.file_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.file_tree.bind('<Delete>', lambda e: self._remove_selected())
        self.file_tree.bind('<Double-1>', lambda e: self._remove_selected())

        remove_btn = ttk.Button(frame, text="❌ 移除选中", command=self._remove_selected, bootstyle="danger-outline")
        remove_btn.pack(fill=X, pady=(5, 0))

        self._setup_drag_drop()
        return frame

    def _setup_drag_drop(self):
        try:
            self.root.drop_target_register(DND_DROP)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        data = event.data
        if data:
            paths = self.root.tk.splitlist(data)
            for path in paths:
                self._add_file(path)

    def _build_right_panel(self):
        frame = ttk.Frame()

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=(0, 5))

        self._build_convert_tab()
        self._build_subtitle_tab()
        self._build_compress_tab()
        self._build_speed_tab()
        self._build_audio_tab()
        self._build_merge_tab()
        self._build_cut_tab()

        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill=X)

        self.process_btn = ttk.Button(bottom_frame, text="▶ 开始处理", command=self._start_processing, bootstyle="success", width=15)
        self.process_btn.pack(side=LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(bottom_frame, text="⏹ 停止", command=self._stop_processing, bootstyle="danger", state=DISABLED, width=10)
        self.stop_btn.pack(side=LEFT, padx=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100, bootstyle="success-striped")
        self.progress_bar.pack(side=LEFT, fill=X, expand=True, padx=(10, 0))

        return frame

    def _build_convert_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" 🔄 格式转换 ")

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="输出格式:", width=12).pack(side=LEFT)
        self.convert_format = ttk.Combobox(row1, values=OUTPUT_VIDEO_FORMATS + OUTPUT_AUDIO_FORMATS, state="readonly", width=20)
        self.convert_format.set("mp4")
        self.convert_format.pack(side=LEFT, padx=5)

        ttk.Label(row1, text="视频编码:", width=12).pack(side=LEFT, padx=(20, 0))
        self.convert_vcodec = ttk.Combobox(row1, values=VIDEO_CODECS, state="readonly", width=22)
        self.convert_vcodec.set("H.264 (libx264)")
        self.convert_vcodec.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="音频编码:", width=12).pack(side=LEFT)
        self.convert_acodec = ttk.Combobox(row2, values=AUDIO_CODECS, state="readonly", width=20)
        self.convert_acodec.set("AAC")
        self.convert_acodec.pack(side=LEFT, padx=5)

        ttk.Label(row2, text="质量预设:", width=12).pack(side=LEFT, padx=(20, 0))
        self.convert_quality = ttk.Combobox(row2, values=QUALITY_PRESETS, state="readonly", width=22)
        self.convert_quality.set("中等质量 (CRF 23)")
        self.convert_quality.pack(side=LEFT, padx=5)

        row3 = ttk.Frame(tab)
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="自定义CRF:", width=12).pack(side=LEFT)
        self.convert_crf = ttk.Spinbox(row3, from_=0, to=51, width=8, increment=1)
        self.convert_crf.set("23")
        self.convert_crf.pack(side=LEFT, padx=5)
        ttk.Label(row3, text="(0=最佳, 51=最差)", foreground="gray").pack(side=LEFT, padx=5)

        row4 = ttk.Frame(tab)
        row4.pack(fill=X, pady=5)
        ttk.Label(row4, text="自定义比特率:", width=12).pack(side=LEFT)
        self.convert_bitrate = ttk.Entry(row4, width=12)
        self.convert_bitrate.insert(0, "2000k")
        self.convert_bitrate.pack(side=LEFT, padx=5)
        ttk.Label(row4, text="例: 2000k, 5M", foreground="gray").pack(side=LEFT, padx=5)

        self.convert_same_folder = ttk.BooleanVar(value=True)
        ttk.Checkbutton(tab, text="输出到源文件同目录", variable=self.convert_same_folder).pack(anchor=W, pady=10)

    def _build_subtitle_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" 📝 字幕 ")

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="字幕文件:", width=12).pack(side=LEFT)
        self.subtitle_path = ttk.Entry(row1, width=40)
        self.subtitle_path.pack(side=LEFT, padx=5, fill=X, expand=True)
        ttk.Button(row1, text="浏览", command=self._browse_subtitle, width=8).pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="字幕模式:", width=12).pack(side=LEFT)
        self.subtitle_mode = ttk.Combobox(row2, values=["硬字幕 (烧录到视频)", "软字幕 (封装到容器)"], state="readonly", width=25)
        self.subtitle_mode.set("硬字幕 (烧录到视频)")
        self.subtitle_mode.pack(side=LEFT, padx=5)

        row3 = ttk.Frame(tab)
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="字幕延迟:", width=12).pack(side=LEFT)
        self.subtitle_delay = ttk.Spinbox(row3, from_=-10000, to=10000, width=10, increment=100)
        self.subtitle_delay.set("0")
        self.subtitle_delay.pack(side=LEFT, padx=5)
        ttk.Label(row3, text="毫秒 (正数延后, 负数提前)", foreground="gray").pack(side=LEFT, padx=5)

        style_frame = ttk.Labelframe(tab, text="字幕样式", padding=10)
        style_frame.pack(fill=X, pady=10)

        s1 = ttk.Frame(style_frame)
        s1.pack(fill=X, pady=2)
        ttk.Label(s1, text="字体大小:", width=12).pack(side=LEFT)
        self.sub_fontsize = ttk.Spinbox(s1, from_=8, to=72, width=6, increment=2)
        self.sub_fontsize.set("24")
        self.sub_fontsize.pack(side=LEFT, padx=5)

        ttk.Label(s1, text="字体颜色:", width=12).pack(side=LEFT, padx=(20, 0))
        self.sub_color = ttk.Combobox(s1, values=["白色", "黄色", "红色", "蓝色", "绿色", "黑色"], state="readonly", width=10)
        self.sub_color.set("白色")
        self.sub_color.pack(side=LEFT, padx=5)

        s2 = ttk.Frame(style_frame)
        s2.pack(fill=X, pady=2)
        ttk.Label(s2, text="字幕位置:", width=12).pack(side=LEFT)
        self.sub_position = ttk.Combobox(s2, values=["底部", "顶部", "居中"], state="readonly", width=10)
        self.sub_position.set("底部")
        self.sub_position.pack(side=LEFT, padx=5)

        ttk.Label(s2, text="边框粗细:", width=12).pack(side=LEFT, padx=(20, 0))
        self.sub_border = ttk.Spinbox(s2, from_=0, to=5, width=6)
        self.sub_border.set("2")
        self.sub_border.pack(side=LEFT, padx=5)

    def _build_compress_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" 📦 压缩 ")

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="分辨率:", width=12).pack(side=LEFT)
        self.compress_resolution = ttk.Combobox(row1, values=RESOLUTION_PRESETS, state="readonly", width=25)
        self.compress_resolution.set("原始分辨率")
        self.compress_resolution.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="编码器:", width=12).pack(side=LEFT)
        self.compress_codec = ttk.Combobox(row2, values=["H.264 (libx264)", "H.265 (libx265)"], state="readonly", width=25)
        self.compress_codec.set("H.264 (libx264)")
        self.compress_codec.pack(side=LEFT, padx=5)

        row3 = ttk.Frame(tab)
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="质量CRF:", width=12).pack(side=LEFT)
        self.compress_crf = ttk.Spinbox(row3, from_=0, to=51, width=8, increment=1)
        self.compress_crf.set("28")
        self.compress_crf.pack(side=LEFT, padx=5)
        ttk.Label(row3, text="(推荐23-28, 数值越大压缩越狠)", foreground="gray").pack(side=LEFT, padx=5)

        row4 = ttk.Frame(tab)
        row4.pack(fill=X, pady=5)
        ttk.Label(row4, text="预设方案:", width=12).pack(side=LEFT)
        self.compress_preset = ttk.Combobox(row4, values=["高质量", "中等质量", "小文件优先"], state="readonly", width=25)
        self.compress_preset.set("中等质量")
        self.compress_preset.pack(side=LEFT, padx=5)

        row5 = ttk.Frame(tab)
        row5.pack(fill=X, pady=5)
        ttk.Label(row5, text="帧率:", width=12).pack(side=LEFT)
        self.compress_fps = ttk.Combobox(row5, values=["保持原始", "60", "30", "25", "24", "15"], state="readonly", width=15)
        self.compress_fps.set("保持原始")
        self.compress_fps.pack(side=LEFT, padx=5)

    def _build_speed_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" ⚡ 加速 ")

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="加速倍率:", width=12).pack(side=LEFT)
        self.speed_ratio = ttk.Combobox(row1, values=SPEED_PRESETS, state="readonly", width=15)
        self.speed_ratio.set("2X")
        self.speed_ratio.pack(side=LEFT, padx=5)

        ttk.Label(row1, text="自定义倍率:", width=12).pack(side=LEFT, padx=(20, 0))
        self.speed_custom = ttk.Spinbox(row1, from_=1.0, to=10.0, width=8, increment=0.25, format="%.2f")
        self.speed_custom.set("2.00")
        self.speed_custom.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="音频处理:", width=12).pack(side=LEFT)
        self.speed_audio = ttk.Combobox(row2, values=["保持原速（不变调）", "同步加速（变调）", "移除音频"], state="readonly", width=25)
        self.speed_audio.set("保持原速（不变调）")
        self.speed_audio.pack(side=LEFT, padx=5)

        info_frame = ttk.Labelframe(tab, text="说明", padding=10)
        info_frame.pack(fill=X, pady=10)
        ttk.Label(info_frame, text="• 2X = 原时长的一半\n• 保持原速：音频时长不变\n• 同步加速：音频会变尖锐\n• 移除音频：完全去掉音轨",
                  foreground="gray", justify=LEFT).pack(anchor=W)

    def _build_audio_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" 🎵 音轨 ")

        self.audio_mode = tk.StringVar(value="extract")

        mode_frame = ttk.Frame(tab)
        mode_frame.pack(fill=X, pady=5)
        ttk.Radiobutton(mode_frame, text="提取音频", variable=self.audio_mode, value="extract", command=self._toggle_audio_mode).pack(side=LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="移除音频", variable=self.audio_mode, value="remove", command=self._toggle_audio_mode).pack(side=LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="添加背景音乐", variable=self.audio_mode, value="add", command=self._toggle_audio_mode).pack(side=LEFT, padx=10)

        self.audio_extract_frame = ttk.Labelframe(tab, text="提取音频设置", padding=10)
        self.audio_extract_frame.pack(fill=X, pady=5)

        r1 = ttk.Frame(self.audio_extract_frame)
        r1.pack(fill=X, pady=2)
        ttk.Label(r1, text="输出格式:", width=12).pack(side=LEFT)
        self.audio_extract_fmt = ttk.Combobox(r1, values=["mp3", "wav", "aac", "flac", "m4a"], state="readonly", width=15)
        self.audio_extract_fmt.set("mp3")
        self.audio_extract_fmt.pack(side=LEFT, padx=5)
        ttk.Label(r1, text="比特率:", width=8).pack(side=LEFT, padx=(20, 0))
        self.audio_extract_bitrate = ttk.Combobox(r1, values=["128k", "192k", "256k", "320k"], state="readonly", width=10)
        self.audio_extract_bitrate.set("192k")
        self.audio_extract_bitrate.pack(side=LEFT, padx=5)

        self.audio_add_frame = ttk.Labelframe(tab, text="背景音乐设置", padding=10)

        self.bgm_list_var = tk.StringVar(value="")
        self.bgm_files = []

        bgm_top = ttk.Frame(self.audio_add_frame)
        bgm_top.pack(fill=X, pady=(0, 5))
        ttk.Button(bgm_top, text="➕ 添加音乐", command=self._add_bgm, bootstyle="success-outline").pack(side=LEFT)
        ttk.Button(bgm_top, text="🗑️ 移除选中", command=self._remove_bgm, bootstyle="danger-outline").pack(side=LEFT, padx=5)

        bgm_list_frame = ttk.Frame(self.audio_add_frame)
        bgm_list_frame.pack(fill=X, pady=5)
        self.bgm_listbox = tk.Listbox(bgm_list_frame, height=4, selectmode=SINGLE)
        self.bgm_listbox.pack(fill=X)

        settings_frame = ttk.Frame(self.audio_add_frame)
        settings_frame.pack(fill=X, pady=5)

        sf1 = ttk.Frame(settings_frame)
        sf1.pack(fill=X, pady=2)
        ttk.Label(sf1, text="主音量:", width=10).pack(side=LEFT)
        self.bgm_main_vol = ttk.Spinbox(sf1, from_=-30, to=10, width=8, increment=1)
        self.bgm_main_vol.set("0")
        self.bgm_main_vol.pack(side=LEFT, padx=5)
        ttk.Label(sf1, text="dB", foreground="gray").pack(side=LEFT)
        ttk.Label(sf1, text="背景音量:", width=10).pack(side=LEFT, padx=(20, 0))
        self.bgm_bg_vol = ttk.Spinbox(sf1, from_=-30, to=10, width=8, increment=1)
        self.bgm_bg_vol.set("-3")
        self.bgm_bg_vol.pack(side=LEFT, padx=5)
        ttk.Label(sf1, text="dB", foreground="gray").pack(side=LEFT)

        sf2 = ttk.Frame(settings_frame)
        sf2.pack(fill=X, pady=2)
        ttk.Label(sf2, text="循环次数:", width=10).pack(side=LEFT)
        self.bgm_loop = ttk.Spinbox(sf2, from_=-1, to=100, width=8, increment=1)
        self.bgm_loop.set("-1")
        self.bgm_loop.pack(side=LEFT, padx=5)
        ttk.Label(sf2, text="(-1=无限循环)", foreground="gray").pack(side=LEFT)
        ttk.Label(sf2, text="开始时间:", width=10).pack(side=LEFT, padx=(20, 0))
        self.bgm_start = ttk.Entry(sf2, width=10)
        self.bgm_start.insert(0, "0")
        self.bgm_start.pack(side=LEFT, padx=5)
        ttk.Label(sf2, text="秒", foreground="gray").pack(side=LEFT)

        sf3 = ttk.Frame(settings_frame)
        sf3.pack(fill=X, pady=2)
        ttk.Label(sf3, text="截止时间:", width=10).pack(side=LEFT)
        self.bgm_end = ttk.Entry(sf3, width=10)
        self.bgm_end.insert(0, "0")
        self.bgm_end.pack(side=LEFT, padx=5)
        ttk.Label(sf3, text="秒 (0=到视频结束)", foreground="gray").pack(side=LEFT)

        self._toggle_audio_mode()

    def _toggle_audio_mode(self):
        mode = self.audio_mode.get()
        if mode == "extract":
            self.audio_extract_frame.pack(fill=X, pady=5)
            self.audio_add_frame.pack_forget()
        elif mode == "add":
            self.audio_extract_frame.pack_forget()
            self.audio_add_frame.pack(fill=X, pady=5)
        else:
            self.audio_extract_frame.pack_forget()
            self.audio_add_frame.pack_forget()

    def _add_bgm(self):
        files = filedialog.askopenfilenames(title="选择背景音乐", filetypes=[("音频文件", "*.mp3 *.wav *.aac *.flac *.m4a *.wma")])
        for f in files:
            if f not in self.bgm_files:
                self.bgm_files.append(f)
                self.bgm_listbox.insert(END, os.path.basename(f))

    def _remove_bgm(self):
        sel = self.bgm_listbox.curselection()
        if sel:
            idx = sel[0]
            self.bgm_listbox.delete(idx)
            self.bgm_files.pop(idx)

    def _build_merge_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" 🔗 合并 ")

        info = ttk.Label(tab, text="合并功能说明：将任务列表中的多个视频/音频文件按顺序合并为一个文件。", foreground="gray")
        info.pack(anchor=W, pady=(0, 10))

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="输出格式:", width=12).pack(side=LEFT)
        self.merge_format = ttk.Combobox(row1, values=OUTPUT_VIDEO_FORMATS, state="readonly", width=15)
        self.merge_format.set("mp4")
        self.merge_format.pack(side=LEFT, padx=5)

        ttk.Label(row1, text="分辨率:", width=8).pack(side=LEFT, padx=(20, 0))
        self.merge_resolution = ttk.Combobox(row1, values=RESOLUTION_PRESETS, state="readonly", width=20)
        self.merge_resolution.set("保持原始")
        self.merge_resolution.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="帧率:", width=12).pack(side=LEFT)
        self.merge_fps = ttk.Combobox(row2, values=["保持原始", "60", "30", "25", "24"], state="readonly", width=15)
        self.merge_fps.set("保持原始")
        self.merge_fps.pack(side=LEFT, padx=5)

        ttk.Label(row2, text="填充方式:", width=8).pack(side=LEFT, padx=(20, 0))
        self.merge_pad = ttk.Combobox(row2, values=["黑边填充", "模糊填充", "拉伸填充"], state="readonly", width=15)
        self.merge_pad.set("黑边填充")
        self.merge_pad.pack(side=LEFT, padx=5)

        tip = ttk.Labelframe(tab, text="操作提示", padding=10)
        tip.pack(fill=X, pady=10)
        ttk.Label(tip, text="1. 在左侧任务列表中添加要合并的文件\n2. 通过上移/下移调整顺序\n3. 选择输出参数后点击开始处理",
                  foreground="gray", justify=LEFT).pack(anchor=W)

    def _build_cut_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text=" ✂️ 切割 ")

        row1 = ttk.Frame(tab)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="开始时间:", width=12).pack(side=LEFT)
        self.cut_start = ttk.Entry(row1, width=15)
        self.cut_start.insert(0, "00:00:00.000")
        self.cut_start.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="格式: HH:MM:SS 或 秒数", foreground="gray").pack(side=LEFT, padx=5)

        row2 = ttk.Frame(tab)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="结束时间:", width=12).pack(side=LEFT)
        self.cut_end = ttk.Entry(row2, width=15)
        self.cut_end.insert(0, "00:00:00.000")
        self.cut_end.pack(side=LEFT, padx=5)
        ttk.Label(row2, text="格式: HH:MM:SS 或 秒数 (留空=到结尾)", foreground="gray").pack(side=LEFT, padx=5)

        row3 = ttk.Frame(tab)
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="持续时间:", width=12).pack(side=LEFT)
        self.cut_duration = ttk.Label(row3, text="--:--:--", foreground="blue")
        self.cut_duration.pack(side=LEFT, padx=5)

        row4 = ttk.Frame(tab)
        row4.pack(fill=X, pady=5)
        self.cut_keyframe = ttk.BooleanVar(value=False)
        ttk.Checkbutton(row4, text="精确模式（逐帧，较慢但更准确）", variable=self.cut_keyframe).pack(side=LEFT)

        self.cut_start.bind('<KeyRelease>', self._update_cut_duration)
        self.cut_end.bind('<KeyRelease>', self._update_cut_duration)

    def _update_cut_duration(self, event=None):
        try:
            start = parse_time(self.cut_start.get()) if self.cut_start.get().strip() else 0
            end = parse_time(self.cut_end.get()) if self.cut_end.get().strip() else 0
            if end > start:
                dur = end - start
                self.cut_duration.config(text=format_time(dur))
            else:
                self.cut_duration.config(text="--:--:--")
        except Exception:
            self.cut_duration.config(text="格式错误")

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root, padding=(10, 5))
        status_frame.pack(fill=X, side=BOTTOM)

        ttk.Label(status_frame, text="FFmpeg:", width=8).pack(side=LEFT)
        self.ffmpeg_path_var = tk.StringVar(value=self.config.get("ffmpeg_path", ""))
        self.ffmpeg_entry = ttk.Entry(status_frame, textvariable=self.ffmpeg_path_var, width=40)
        self.ffmpeg_entry.pack(side=LEFT, padx=5)
        ttk.Button(status_frame, text="浏览", command=self._browse_ffmpeg, width=6).pack(side=LEFT)
        ttk.Button(status_frame, text="下载", command=self._open_download, width=6, bootstyle="info-outline").pack(side=LEFT, padx=5)

        ttk.Separator(status_frame, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)

        ttk.Label(status_frame, text="输出目录:", width=9).pack(side=LEFT)
        self.output_dir_var = tk.StringVar(value=self.config.get("output_dir", ""))
        ttk.Entry(status_frame, textvariable=self.output_dir_var, width=30).pack(side=LEFT, padx=5)
        ttk.Button(status_frame, text="浏览", command=self._browse_output_dir, width=6).pack(side=LEFT)

        ttk.Separator(status_frame, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="green").pack(side=LEFT, padx=5)

    def _detect_ffmpeg(self):
        path = self.ffmpeg_path_var.get()
        if path and os.path.isfile(path):
            self.status_var.set("✅ FFmpeg 已就绪")
            return

        for p in ["ffmpeg.exe", "C:\\ffmpeg\\bin\\ffmpeg.exe", "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"]:
            try:
                result = subprocess.run([p, "-version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.ffmpeg_path_var.set(p)
                    self.config["ffmpeg_path"] = p
                    save_config(self.config)
                    self.status_var.set("✅ FFmpeg 已就绪")
                    return
            except Exception:
                continue

        self.status_var.set("⚠️ 未检测到 FFmpeg，请设置路径")

    # ==================== 文件操作 ====================
    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="选择媒体文件",
            filetypes=[("媒体文件", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.mp3 *.wav *.aac *.flac *.m4a *.wma *.srt *.ass *.vtt"),
                       ("所有文件", "*.*")]
        )
        for f in files:
            self._add_file(f)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            for f in os.listdir(folder):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_ALL:
                    self._add_file(os.path.join(folder, f))

    def _add_file(self, filepath):
        if not os.path.isfile(filepath):
            return
        for item in self.files:
            if item["path"] == filepath:
                return

        name = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        ext = os.path.splitext(name)[1].lower()

        size_str = f"{size / 1024 / 1024:.1f}MB" if size > 1024 * 1024 else f"{size / 1024:.1f}KB"

        self.file_tree.insert("", END, values=(name, size_str, ext.upper().replace('.', '')))
        self.files.append({"path": filepath, "name": name, "size": size, "ext": ext})

    def _clear_files(self):
        self.files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

    def _remove_selected(self):
        selected = self.file_tree.selection()
        for item in selected:
            values = self.file_tree.item(item, "values")
            name = values[0]
            self.files = [f for f in self.files if f["name"] != name]
            self.file_tree.delete(item)

    def _browse_subtitle(self):
        path = filedialog.askopenfilename(title="选择字幕文件", filetypes=[("字幕文件", "*.srt *.ass *.ssa *.vtt")])
        if path:
            self.subtitle_path.delete(0, END)
            self.subtitle_path.insert(0, path)

    def _browse_ffmpeg(self):
        path = filedialog.askopenfilename(title="选择 ffmpeg.exe", filetypes=[("FFmpeg", "ffmpeg.exe"), ("所有文件", "*.*")])
        if path:
            self.ffmpeg_path_var.set(path)
            self.config["ffmpeg_path"] = path
            save_config(self.config)
            self.status_var.set("✅ FFmpeg 已设置")

    def _browse_output_dir(self):
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_dir_var.set(folder)
            self.config["output_dir"] = folder
            save_config(self.config)

    def _open_download(self):
        import webbrowser
        webbrowser.open("https://ffmpeg.org/download.html")

    # ==================== 处理逻辑 ====================
    def _start_processing(self):
        if self.is_processing:
            return

        if not self.files:
            messagebox.showwarning("提示", "请先添加文件")
            return

        ffmpeg = self.ffmpeg_path_var.get()
        if not ffmpeg or not os.path.isfile(ffmpeg):
            messagebox.showerror("错误", "请先设置有效的 FFmpeg 路径")
            return

        self.is_processing = True
        self.process_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.progress_var.set(0)

        thread = threading.Thread(target=self._process_worker, daemon=True)
        thread.start()

    def _stop_processing(self):
        self.is_processing = False
        if self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass
        self.process_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.status_var.set("⏹ 已停止")

    def _process_worker(self):
        try:
            active_tab = self.notebook.index(self.notebook.select())

            if active_tab == 0:
                self._run_convert()
            elif active_tab == 1:
                self._run_subtitle()
            elif active_tab == 2:
                self._run_compress()
            elif active_tab == 3:
                self._run_speed()
            elif active_tab == 4:
                self._run_audio()
            elif active_tab == 5:
                self._run_merge()
            elif active_tab == 6:
                self._run_cut()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("处理出错", str(e)))
        finally:
            self.root.after(0, self._processing_done)

    def _processing_done(self):
        self.is_processing = False
        self.process_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.progress_var.set(100)
        self.root.after(2000, lambda: self.progress_var.set(0))

    def _get_output_path(self, input_path, ext=None):
        output_dir = self.output_dir_var.get()
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = os.path.dirname(input_path)

        base = os.path.splitext(os.path.basename(input_path))[0]
        if ext is None:
            tab = self.notebook.index(self.notebook.select())
            if tab == 0:
                ext = self.convert_format.get()
            elif tab == 2:
                ext = "mp4"
            else:
                ext = os.path.splitext(input_path)[1].replace('.', '')

        output = os.path.join(output_dir, f"{base}_output.{ext}")
        counter = 1
        while os.path.exists(output):
            output = os.path.join(output_dir, f"{base}_output_{counter}.{ext}")
            counter += 1
        return output

    def _run_ffmpeg(self, cmd):
        self.root.after(0, lambda: self.status_var.set("⏳ 处理中..."))
        self.current_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW
        )

        for line in self.current_process.stderr:
            if not self.is_processing:
                break
            time_match = re.search(r"time=(\d+):(\d+):(\d+)", line)
            if time_match:
                h, m, s = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
                total = h * 3600 + m * 60 + s
                self.root.after(0, lambda t=total: self.progress_var.set(min(t / 10, 100)))

        self.current_process.wait()
        return self.current_process.returncode

    def _run_convert(self):
        ffmpeg = self.ffmpeg_path_var.get()
        for i, file in enumerate(self.files):
            if not self.is_processing:
                break
            if file["ext"] not in SUPPORTED_ALL:
                continue

            output = self._get_output_path(file["path"])
            cmd = [ffmpeg, "-i", file["path"], "-y"]

            vcodec_text = self.convert_vcodec.get()
            if "Copy" in vcodec_text:
                cmd.extend(["-c:v", "copy"])
            else:
                cmd.extend(["-c:v", "libx264"])
                quality = self.convert_quality.get()
                if "CRF 18" in quality:
                    cmd.extend(["-crf", "18"])
                elif "CRF 23" in quality:
                    cmd.extend(["-crf", "23"])
                elif "CRF 28" in quality:
                    cmd.extend(["-crf", "28"])
                elif "CRF 35" in quality:
                    cmd.extend(["-crf", "35"])
                elif "自定义" in quality:
                    cmd.extend(["-crf", self.convert_crf.get()])

            acodec_text = self.convert_acodec.get()
            if "Copy" in acodec_text:
                cmd.extend(["-c:a", "copy"])
            elif "MP3" in acodec_text:
                cmd.extend(["-c:a", "libmp3lame"])
            elif "FLAC" in acodec_text:
                cmd.extend(["-c:a", "flac"])
            elif "PCM" in acodec_text:
                cmd.extend(["-c:a", "pcm_s16le"])
            else:
                cmd.extend(["-c:a", "aac"])

            cmd.append(output)
            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 转换: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "格式转换完成!"))

    def _run_subtitle(self):
        ffmpeg = self.ffmpeg_path_var.get()
        subtitle = self.subtitle_path.get()
        if not subtitle or not os.path.isfile(subtitle):
            self.root.after(0, lambda: messagebox.showwarning("提示", "请先选择字幕文件"))
            return

        for file in self.files:
            if not self.is_processing:
                break
            if file["ext"] not in SUPPORTED_VIDEO:
                continue

            output = self._get_output_path(file["path"])
            cmd = [ffmpeg, "-i", file["path"], "-i", subtitle, "-y"]

            if "硬字幕" in self.subtitle_mode.get():
                colors = {"白色": "white", "黄色": "yellow", "红色": "red", "蓝色": "blue", "绿色": "green", "黑色": "black"}
                positions = {"底部": 2, "顶部": 0, "居中": 5}
                color = colors.get(self.sub_color.get(), "white")
                pos = positions.get(self.sub_position.get(), 2)
                fontsize = self.sub_fontsize.get()
                border = self.sub_border.get()
                delay = int(self.subtitle_delay.get()) / 1000

                force_style = f"FontSize={fontsize},PrimaryColour=&H00{color},Alignment={pos},Outline={border}"
                cmd.extend(["-vf", f"subtitles='{subtitle}':force_style='{force_style}'"])
                if delay != 0:
                    cmd.extend(["-itsoffset", str(delay)])
            else:
                cmd.extend(["-c:s", "srt"])

            cmd.extend(["-c:v", "copy", "-c:a", "copy", output])
            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 添加字幕: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "字幕添加完成!"))

    def _run_compress(self):
        ffmpeg = self.ffmpeg_path_var.get()

        for file in self.files:
            if not self.is_processing:
                break
            if file["ext"] not in SUPPORTED_VIDEO:
                continue

            output = self._get_output_path(file["path"])
            cmd = [ffmpeg, "-i", file["path"], "-y"]

            codec = self.compress_codec.get()
            if "H.265" in codec:
                cmd.extend(["-c:v", "libx265"])
            else:
                cmd.extend(["-c:v", "libx264"])

            cmd.extend(["-crf", self.compress_crf.get()])

            res = self.compress_resolution.get()
            if "1080" in res:
                cmd.extend(["-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"])
            elif "720" in res:
                cmd.extend(["-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"])
            elif "480" in res:
                cmd.extend(["-vf", "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2"])
            elif "360" in res:
                cmd.extend(["-vf", "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2"])

            fps = self.compress_fps.get()
            if fps != "保持原始":
                cmd.extend(["-r", fps])

            cmd.extend(["-c:a", "copy", output])
            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 压缩: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "视频压缩完成!"))

    def _run_speed(self):
        ffmpeg = self.ffmpeg_path_var.get()

        ratio_text = self.speed_ratio.get()
        if "自定义" in ratio_text:
            ratio = float(self.speed_custom.get())
        else:
            ratio = float(ratio_text.replace('X', ''))

        for file in self.files:
            if not self.is_processing:
                break
            if file["ext"] not in SUPPORTED_VIDEO:
                continue

            output = self._get_output_path(file["path"])
            cmd = [ffmpeg, "-i", file["path"], "-y"]

            video_filter = f"setpts={1/ratio}*PTS"
            audio_mode = self.speed_audio.get()
            if "移除" in audio_mode:
                cmd.extend(["-an", "-vf", video_filter])
            elif "同步" in audio_mode:
                cmd.extend(["-vf", video_filter, "-af", f"atempo={ratio}"])
            else:
                cmd.extend(["-vf", video_filter])

            cmd.extend(["-c:v", "libx264", "-c:a", "aac", output])
            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 加速处理: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "加速处理完成!"))

    def _run_audio(self):
        ffmpeg = self.ffmpeg_path_var.get()
        mode = self.audio_mode.get()

        for file in self.files:
            if not self.is_processing:
                break

            if mode == "extract":
                if file["ext"] not in SUPPORTED_VIDEO:
                    continue
                output = self._get_output_path(file["path"], self.audio_extract_fmt.get())
                cmd = [ffmpeg, "-i", file["path"], "-vn", "-y"]
                fmt = self.audio_extract_fmt.get()
                if fmt == "mp3":
                    cmd.extend(["-c:a", "libmp3lame", "-b:a", self.audio_extract_bitrate.get()])
                elif fmt == "aac":
                    cmd.extend(["-c:a", "aac", "-b:a", self.audio_extract_bitrate.get()])
                elif fmt == "flac":
                    cmd.extend(["-c:a", "flac"])
                else:
                    cmd.extend(["-c:a", "copy"])
                cmd.append(output)

            elif mode == "remove":
                if file["ext"] not in SUPPORTED_VIDEO:
                    continue
                output = self._get_output_path(file["path"])
                cmd = [ffmpeg, "-i", file["path"], "-an", "-y", "-c:v", "copy", output]

            elif mode == "add":
                if file["ext"] not in SUPPORTED_VIDEO:
                    continue
                if not self.bgm_files:
                    self.root.after(0, lambda: messagebox.showwarning("提示", "请先添加背景音乐"))
                    return

                output = self._get_output_path(file["path"])
                cmd = [ffmpeg, "-i", file["path"]]
                for bgm in self.bgm_files:
                    cmd.extend(["-i", bgm])

                main_vol = int(self.bgm_main_vol.get())
                bg_vol = int(self.bgm_bg_vol.get())
                loop = int(self.bgm_loop.get())
                start = self.bgm_start.get().strip()
                end = self.bgm_end.get().strip()

                filter_parts = [f"[0:a]volume={main_vol}dB[a0]"]
                for i in range(len(self.bgm_files)):
                    loop_opt = f"-stream_loop {loop}" if loop != 0 else ""
                    filter_parts.append(f"[{i+1}:a]volume={bg_vol}dB[a{i+1}]")
                mix_inputs = "".join([f"[a{i}]" for i in range(len(self.bgm_files) + 1)])
                filter_parts.append(f"{mix_inputs}amix=inputs={len(self.bgm_files) + 1}:duration=first[aout]")
                filter_complex = ";".join(filter_parts)

                cmd.extend(["-filter_complex", filter_complex, "-map", "0:v", "-map", "[aout]", "-y", "-c:v", "copy", output])

            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 音频处理: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "音频处理完成!"))

    def _run_merge(self):
        ffmpeg = self.ffmpeg_path_var.get()

        if len(self.files) < 2:
            self.root.after(0, lambda: messagebox.showwarning("提示", "合并至少需要2个文件"))
            return

        output_fmt = self.merge_format.get()
        output = self._get_output_path(self.files[0]["path"], output_fmt)

        cmd = [ffmpeg, "-y"]
        for file in self.files:
            cmd.extend(["-i", file["path"]])

        cmd.extend(["-filter_complex"])
        filter_parts = []
        for i in range(len(self.files)):
            filter_parts.append(f"[{i}:v:0][{i}:a:0]")
        filter_complex = "".join(filter_parts) + f"concat=n={len(self.files)}:v=1:a=1[outv][outa]"
        cmd.append(filter_complex)
        cmd.extend(["-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-c:a", "aac", output])

        self.root.after(0, lambda: self.status_var.set("⏳ 合并视频中..."))
        self._run_ffmpeg(cmd)
        self.root.after(0, lambda: messagebox.showinfo("完成", "视频合并完成!"))

    def _run_cut(self):
        ffmpeg = self.ffmpeg_path_var.get()

        start_str = self.cut_start.get().strip()
        end_str = self.cut_end.get().strip()

        for file in self.files:
            if not self.is_processing:
                break

            output = self._get_output_path(file["path"])
            cmd = [ffmpeg, "-y"]

            if start_str:
                cmd.extend(["-ss", start_str])
            cmd.extend(["-i", file["path"]])
            if end_str:
                cmd.extend(["-to", end_str])

            cmd.extend(["-c", "copy", output])
            self.root.after(0, lambda n=file["name"]: self.status_var.set(f"⏳ 切割: {n}"))
            self._run_ffmpeg(cmd)

        self.root.after(0, lambda: messagebox.showinfo("完成", "视频切割完成!"))

    def _show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("关于")
        about_win.geometry("380x280")
        about_win.resizable(False, False)
        about_win.transient(self.root)
        about_win.grab_set()

        frame = ttk.Frame(about_win, padding=25)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text=f"🎬 {APP_NAME}", font=("", 16, "bold")).pack(pady=(0, 5))
        ttk.Label(frame, text=f"Version {APP_VERSION}", font=("Consolas", 11)).pack(pady=(0, 15))

        ttk.Separator(frame).pack(fill=X, pady=(0, 15))

        ttk.Label(frame, text=f"作者: {APP_AUTHOR}", font=("", 11)).pack(pady=2)
        ttk.Label(frame, text=f"联系方式: {APP_EMAIL}", font=("", 11)).pack(pady=2)
        ttk.Label(frame, text="基于 FFmpeg 的多媒体处理工具", foreground="gray").pack(pady=(15, 0))

        ttk.Button(frame, text="关闭", command=about_win.destroy, bootstyle="secondary", width=12).pack(pady=(15, 0))


# ==================== 启动 ====================
if __name__ == '__main__':
    root = ttk.Window(title=APP_NAME, themename="cosmo", size=(1100, 700), resizable=(True, True))
    app = FFmpegGUIApp(root)
    root.mainloop()
