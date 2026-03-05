#!/usr/bin/env python3
"""
Videocut 精确剪辑脚本
基于 videocut-skills 的 cut_video.sh
使用 FFmpeg filter_complex + crossfade
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def get_duration(video_path: str) -> float:
    """获取视频时长"""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())

def cut_video(input_path: str, delete_ranges: list, output_path: str, 
              buffer_ms: int = 50, crossfade_ms: int = 30) -> bool:
    """
    精确剪辑视频
    
    Args:
        input_path: 输入视频
        delete_ranges: 删除时间段列表 [(start, end), ...]
        output_path: 输出视频
        buffer_ms: 删除范围前后扩展毫秒数
        crossfade_ms: 音频 crossfade 毫秒数
    """
    if not delete_ranges:
        print("没有需要删除的内容，复制原文件")
        subprocess.run(["cp", input_path, output_path], check=True)
        return True
    
    duration = get_duration(input_path)
    buffer_sec = buffer_ms / 1000
    crossfade_sec = crossfade_ms / 1000
    
    # 扩展删除范围
    expanded = []
    for start, end in delete_ranges:
        expanded.append((
            max(0, start - buffer_sec),
            min(duration, end + buffer_sec)
        ))
    
    # 合并重叠
    expanded.sort()
    merged = []
    for start, end in expanded:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    # 计算保留片段
    keep_segments = []
    cursor = 0
    for start, end in merged:
        if start > cursor:
            keep_segments.append((cursor, start))
        cursor = end
    if cursor < duration:
        keep_segments.append((cursor, duration))
    
    print(f"保留片段数: {len(keep_segments)}")
    print(f"删除片段数: {len(merged)}")
    
    deleted_time = sum(e - s for s, e in merged)
    print(f"删除总时长: {deleted_time:.2f}s")
    
    if not keep_segments:
        print("错误：没有保留片段")
        return False
    
    # 生成 FFmpeg filter_complex
    filters = []
    v_concat = ""
    a_labels = []
    
    for i, (start, end) in enumerate(keep_segments):
        filters.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]")
        filters.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]")
        v_concat += f"[v{i}]"
        a_labels.append(f"a{i}")
    
    # 视频 concat
    filters.append(f"{v_concat}concat=n={len(keep_segments)}:v=1:a=0[outv]")
    
    # 音频 crossfade
    if len(keep_segments) == 1:
        filters.append("[a0]anull[outa]")
    else:
        current = "a0"
        for i in range(1, len(keep_segments)):
            next_label = f"a{i}"
            out_label = "outa" if i == len(keep_segments) - 1 else f"amid{i}"
            filters.append(f"[{current}][{next_label}]acrossfade=d={crossfade_sec:.3f}:c1=tri:c2=tri[{out_label}]")
            current = out_label
    
    filter_complex = ";".join(filters)
    
    # 执行 FFmpeg
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    
    print(f"\n执行 FFmpeg 剪辑...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Videocut 精确剪辑")
    parser.add_argument("input", help="输入视频")
    parser.add_argument("--delete", "-d", required=True, help="删除时间段 JSON 文件或字符串")
    parser.add_argument("--output", "-o", help="输出视频")
    parser.add_argument("--buffer", "-b", type=int, default=50, help="删除范围前后扩展毫秒数")
    parser.add_argument("--crossfade", "-c", type=int, default=30, help="音频 crossfade 毫秒数")
    
    args = parser.parse_args()
    
    # 解析删除范围
    if args.delete.endswith(".json"):
        with open(args.delete) as f:
            data = json.load(f)
            delete_ranges = [(i["start"], i["end"]) for i in data]
    else:
        delete_ranges = []
        for part in args.delete.split(","):
            start, end = map(float, part.split("-"))
            delete_ranges.append((start, end))
    
    output = args.output or Path(args.input).stem + "_cut.mp4"
    
    success = cut_video(args.input, delete_ranges, output, args.buffer, args.crossfade)
    
    if success:
        print(f"\n✅ 完成: {output}")
        new_dur = get_duration(output)
        print(f"📹 新时长: {new_dur:.1f}s")

if __name__ == "__main__":
    main()
