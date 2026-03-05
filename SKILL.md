# videocut - AI 口播视频剪辑 Skill

基于 videocut-skills 架构，专为口播视频设计

## 功能（完整流程）

1. **提取音频** - FFmpeg
2. **转录** - local-whisper
3. **AI 纠错** - 纠正识别错误（保持字数和时间）
4. **AI 审核** - 检测重复句、静音段等
5. **精确剪辑** - FFmpeg filter_complex + crossfade
6. **生成字幕** - 从纠错后转录生成 SRT
7. **烧录字幕** - 文字叠加在屏幕上，支持自定义样式

## 使用方法

### 告诉 AI

> 帮我剪辑 source-001

AI 自动完成全部流程！

## 目录结构

```
~/work/cut-task/
├── source-001/           # 素材（只读）
│   └── source.mp4
└── result-001/           # 结果
    ├── audio.mp3           # 提取的音频
    ├── transcript.json     # 原转录
    ├── transcript_fixed.json # 纠错后转录
    ├── subtitles.srt       # 字幕文件
    ├── audit.json        # 审核+纠错记录
    ├── output.mp4         # 剪辑后视频
    └── output_subtitled.mp4  # 带字幕的视频
```

## AI 纠错

自动纠正转录错误：

| 错误类型 | 示例 | 纠正 |
|----------|------|------|
| 同音字 | 经讯 | 资讯 |
| 识别错误 | 性败于七的 | 失信人员的 |
| 口误 | 后悔悠 | 后悔啊 |

**保持字数和时间不变！**

## AI 审核规则

### 检测类型

| # | 类型 | 处理 |
|---|------|------|
| 1 | **静音 >1s** | 建议删除 |
| 2 | **残句** | 删整句 |
| 3 | **重复句** | 删短的（含开头+中间重复） |
| 4 | **句内重复** | 删 A+中间 |
| 5 | **语气词** | 标记 |

### 核心原则

**删前保后** — 后说的更完整

### 排除：列表序号

"一、"、"二、"、"第一点" 等不是重复

## 字幕样式

烧录使用 ffmpeg-full：

| 参数 | 默认值 |
|------|--------|
| 字号 | 24 |
| 颜色 | 白色 |
| 背景 | 半透明黑 |
| 描边 | 2 |
| 边距 | 20 |

### 自定义样式

```bash
--size 28 --color FFFF00 --bg 000000 --outline 2 --margin 30
```

## 依赖

- FFmpeg (需 ffmpeg-full)
- local-whisper
- MiniMax (通过 OpenClaw)

## 安装

```bash
# 安装 ffmpeg-full (带 libass)
brew install ffmpeg-full
```
