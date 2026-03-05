#!/usr/bin/env python3
"""
烧录字幕到视频
支持自定义字体样式
"""

import subprocess
import os

def burn_subtitles(video_path: str, srt_path: str, output_path: str = None,
                   font_size: int = 24, color: str = "FFFFFF", 
                   bg_color: str = "000000", outline: int = 2, margin: int = 20):
    """烧录字幕到视频"""
    
    if output_path is None:
        output_path = video_path.replace(".mp4", "_subtitled.mp4")
    
    # ffmpeg-full 路径
    ffmpeg = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    
    # 如果不存在，尝试默认 ffmpeg
    if not os.path.exists(ffmpeg):
        ffmpeg = "ffmpeg"
    
    # 颜色格式
    primary_color = f"&H{color}"
    back_color = f"&H{bg_color}80"  # 80 = 50% 透明度
    
    # 构建命令
    cmd = [
        ffmpeg, "-y", "-i", video_path,
        "-vf", f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour={primary_color},BackColour={back_color},Outline={outline},MarginV={margin}'",
        "-c:a", "copy",
        output_path
    ]
    
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return None
    
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="烧录字幕")
    parser.add_argument("video", help="视频文件")
    parser.add_argument("srt", help="SRT字幕文件")
    parser.add_argument("--output", "-o", help="输出文件")
    parser.add_argument("--size", "-s", type=int, default=24, help="字号")
    parser.add_argument("--color", "-c", default="FFFFFF", help="颜色(hex)")
    parser.add_argument("--bg", "-b", default="000000", help="背景颜色(hex)")
    parser.add_argument("--outline", type=int, default=2, help="描边宽度")
    parser.add_argument("--margin", type=int, default=20, help="底部边距")
    
    args = parser.parse_args()
    
    result = burn_subtitles(
        args.video, args.srt, args.output,
        args.size, args.color, args.bg, args.outline, args.margin
    )
    
    if result:
        print(f"✅ 完成: {result}")
