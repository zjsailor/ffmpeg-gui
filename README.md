# FFmpeg GUI 工具

基于 FFmpeg 的图形化多媒体处理工具，提供直观的GUI界面进行音视频操作。

## 功能特性

### 🔄 格式转换
- 支持 mp4, avi, mov, mkv, wmv, flv, webm, mp3, wav, aac, flac, m4a 等格式互转
- 视频编码：H.264, H.265, MPEG4, VP9, AV1
- 音频编码：AAC, MP3, FLAC, PCM
- 质量预设：原始/高/中/低/自定义CRF

### 📝 字幕添加
- 支持 srt, ass, ssa, vtt 字幕格式
- 硬字幕（烧录）/ 软字幕（封装）
- 字幕样式自定义：字体、大小、颜色、位置、边框
- 字幕延迟调整

### 📦 视频压缩
- 分辨率预设：1080P, 720P, 480P, 360P
- 编码器：H.264 (libx264) / H.265 (libx265)
- CRF质量控制（0-51）
- 帧率调整

### ⚡ 视频加速
- 倍率：1.25X, 1.5X, 2X, 2.5X, 3X, 4X 或自定义
- 音频处理：保持原速 / 同步加速 / 移除音频

### 🎵 音轨管理
- **提取音频**：从视频中提取为 mp3/wav/aac/flac
- **移除音轨**：生成静音视频
- **添加背景音乐**：
  - 支持多个背景音乐文件
  - 独立音量控制（dB调节）
  - 循环次数设置
  - 开始/截止时间控制

### 🔗 视频合并
- 多文件按顺序合并
- 统一输出格式、分辨率、帧率
- 填充方式：黑边/模糊/拉伸

### ✂️ 视频切割
- 精确时间段截取
- 支持 HH:MM:SS.ms 格式
- 精确模式（逐帧）可选

## 界面预览

- 现代化 UI 风格 (ttkbootstrap)
- 左右分栏布局
- 支持文件拖拽
- 队列式任务处理
- 实时进度显示

## 下载安装

1. 下载 [最新版本](https://github.com/zjsailor/ffmpeg-gui/releases/latest)
2. 解压后运行 `FFmpegGUI.exe`
3. 首次使用需要设置 FFmpeg 路径（可从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载）

## 使用方法

1. 点击"添加文件"或拖拽文件到左侧列表
2. 在右侧选择功能标签页
3. 设置输出参数
4. 点击"开始处理"

## 系统要求

- Windows 10/11
- 需要安装 [FFmpeg](https://ffmpeg.org/download.html)

## 开发信息

- **版本**：1.0
- **作者**：洪旭涛
- **联系方式**：hxt@uoes.edu.kg
- **技术栈**：Python + ttkbootstrap + FFmpeg

## 许可证

MIT License
