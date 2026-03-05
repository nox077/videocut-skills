#!/usr/bin/env python3
"""
Videocut - AI 口播视频剪辑工具
完全自动化版本 - 无需对话介入
"""

import argparse
import json
import os
import re
import subprocess
import sys
import requests
from pathlib import Path
from typing import Optional, List, Dict

# ============ 配置区域 ============
# 设置你的 MiniMax API Key
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
# 或直接在这里填写 API Key
# MINIMAX_API_KEY = "your-api-key-here"

MINIMAX_BASE_URL = "https://api.minimax.io/v1"

WHISPER_SCRIPT = os.path.expanduser("~/.openclaw/workspace/skills/local-whisper/scripts/transcribe.py")
WHISPER_VENV = os.path.expanduser("~/.openclaw/workspace/skills/local-whisper/.venv/bin/python")

# 工作目录
WORK_DIR = os.path.expanduser("~/work/cut-task")
# ============ 配置结束 ============


def log(msg: str):
    """打印日志"""
    print(f"📌 {msg}")


def error(msg: str):
    """打印错误"""
    print(f"❌ {msg}", file=sys.stderr)


def call_minimax(prompt: str, system_prompt: str = None) -> Optional[str]:
    """调用 MiniMax API"""
    if not MINIMAX_API_KEY:
        error("未设置 MiniMax API Key！")
        error("请设置环境变量 MINIMAX_API_KEY 或在脚本中填写")
        return None
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "MiniMax-M2.5",
        "messages": messages,
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            error(f"API 错误: {response.status_code} {response.text}")
            return None
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
        
    except Exception as e:
        error(f"调用失败: {e}")
        return None


def extract_audio(video_path: str, output_path: str = None) -> str:
    """提取视频音频"""
    if output_path is None:
        output_path = Path(video_path).with_suffix(".mp3")
    
    log(f"提取音频: {video_path} -> {output_path}")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        "-y", output_path
    ]
    subprocess.run(cmd, check=True)
    return str(output_path)


def transcribe(audio_path: str, output_path: str = None) -> dict:
    """用 local-whisper 转录音频"""
    if output_path is None:
        output_path = Path(audio_path).with_suffix(".json")
    
    log(f"转录音频: {audio_path}")
    cmd = [
        WHISPER_VENV, WHISPER_SCRIPT,
        audio_path, "--model", "base", "--timestamps", "--json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    # 处理可能的额外输出
    content = result.stdout
    idx = content.find('{')
    if idx >= 0:
        transcript = json.loads(content[idx:])
    else:
        raise ValueError("无法解析转录结果")
    
    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    
    log(f"转录完成: {output_path}")
    return transcript


def ai_audit(transcript: dict) -> List[Dict]:
    """AI 审核 - 调用 MiniMax"""
    log("🔍 调用 MiniMax AI 审核...")
    
    # 准备转录文本
    segments = transcript.get("segments", [])
    
    transcript_text = ""
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        transcript_text += f"[{start:.2f}s - {end:.2f}s] {text}\n"
    
    system_prompt = """你是一个专业的视频剪辑助手，擅长分析口播视频的转录文本，识别需要删除的内容。
你必须返回有效的 JSON 格式。"""
    
    user_prompt = f"""请分析以下口播视频转录文本，识别需要删除的问题内容。

要求：
1. 重复说的话（连续或间隔不远重复说同一内容）
2. 说错后纠正的内容（比如开头说错了，后面重新说）
3. 明显的卡顿、长时间的停顿（超过0.5秒）
4. 口语中不必要的重复词（比如"那个那个"）

注意：
- 保留正常的过渡语、口语化表达
- 只标记确实需要删除的内容
- 返回时按时间顺序排序

转录文本：
{transcript_text}

请返回以下 JSON 格式：
{{
    "issues": [
        {{"start": 起始秒, "end": 结束秒, "reason": "问题原因"}}
    ],
    "summary": "简要总结"
}}

只返回 JSON，不要其他内容。"""
    
    result = call_minimax(user_prompt, system_prompt)
    
    if not result:
        error("AI 审核失败，使用基础规则")
        return basic_audit(transcript)
    
    # 解析 JSON
    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            ai_result = json.loads(json_match.group())
        else:
            ai_result = json.loads(result)
        
        issues = ai_result.get("issues", [])
        log(f"✅ AI 审核完成，发现 {len(issues)} 个问题")
        return issues
        
    except Exception as e:
        error(f"解析失败: {e}，使用基础规则")
        return basic_audit(transcript)


def basic_audit(transcript: dict) -> List[Dict]:
    """基础规则审核（备用）"""
    log("📋 使用基础规则审核...")
    
    segments = transcript.get("segments", [])
    issues = []
    
    # 检测长间隙
    for i in range(len(segments) - 1):
        current_end = segments[i]["end"]
        next_start = segments[i + 1]["start"]
        gap = next_start - current_end
        if gap > 0.5:
            issues.append({
                "start": current_end,
                "end": next_start,
                "reason": f"长间隙 ({gap:.2f}s)"
            })
    
    return issues


def cut_video(video_path: str, issues: List[Dict], output_path: str = None) -> str:
    """根据问题列表剪辑视频"""
    if output_path is None:
        output_path = Path(video_path).stem + "_cut.mp4"
    
    if not issues:
        log("没有问题需要处理")
        return video_path
    
    # 生成删除范围
    delete_ranges = []
    for issue in issues:
        start = float(issue.get("start", 0))
        end = float(issue.get("end", 0))
        if start < end:
            delete_ranges.append((start, end))
    
    if not delete_ranges:
        return video_path
    
    # 合并重叠
    delete_ranges.sort()
    merged = []
    for start, end in delete_ranges:
        if merged and start <= merged[-1][1] + 0.5:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    delete_ranges = merged
    
    # 获取视频时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True
    )
    total_duration = float(result.stdout.strip())
    
    # 生成分片
    parts = []
    last_end = 0
    for start, end in delete_ranges:
        if last_end < start:
            parts.append((last_end, start))
        last_end = end
    if last_end < total_duration:
        parts.append((last_end, total_duration))
    
    log(f"保留时间段: {parts}")
    
    # 分片
    part_files = []
    for i, (start, end) in enumerate(parts):
        part_file = f"/tmp/videocut_part_{i}.mp4"
        cmd = ["ffmpeg", "-i", video_path, "-ss", str(start), "-t", str(end - start), 
               "-c:v", "libx264", "-c:a", "aac", "-y", part_file]
        subprocess.run(cmd, check=True)
        part_files.append(part_file)
    
    # 合并
    with open("/tmp/videocut_concat.txt", "w") as f:
        for pf in part_files:
            f.write(f"file '{pf}'\n")
    
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", "/tmp/videocut_concat.txt",
        "-c", "copy", "-y", output_path
    ]
    subprocess.run(cmd, check=True)
    
    # 清理
    for pf in part_files:
        os.remove(pf)
    os.remove("/tmp/videocut_concat.txt")
    
    return output_path


def process_task(source_dir: str):
    """处理一个任务"""
    source_path = Path(source_dir)
    
    # 找视频文件
    video_files = list(source_path.glob("*.mp4"))
    if not video_files:
        error(f"在 {source_dir} 中找不到视频文件")
        return
    
    video_path = str(video_files[0])
    task_name = source_path.name
    
    # 生成 result 目录
    result_dir = source_path.parent / f"result-{task_name.split('-')[1]}"
    result_dir.mkdir(exist_ok=True)
    
    log(f"\n{'='*50}")
    log(f"处理任务: {task_name}")
    log(f"{'='*50}")
    
    # 1. 提取音频
    audio_path = str(source_path / "audio.mp3")
    if not os.path.exists(audio_path):
        extract_audio(video_path, audio_path)
    
    # 2. 转录
    transcript_path = str(source_path / "transcript.json")
    if not os.path.exists(transcript_path):
        transcribe(audio_path, transcript_path)
    
    # 3. 读取转录
    with open(transcript_path, encoding="utf-8") as f:
        content = f.read()
        idx = content.find('{')
        if idx >= 0:
            transcript = json.loads(content[idx:])
        else:
            error("无法读取转录文件")
            return
    
    # 4. AI 审核
    issues = ai_audit(transcript)
    
    # 显示问题
    log("\n发现问题:")
    for i, issue in enumerate(issues, 1):
        log(f"  {i}. {issue['start']:.2f}s - {issue['end']:.2f}s: {issue['reason']}")
    
    # 5. 剪辑
    output_path = str(result_dir / "output.mp4")
    cut_video(video_path, issues, output_path)
    
    # 6. 保存审核结果
    audit_result = {
        "task": task_name,
        "source": video_path,
        "output": output_path,
        "issues": issues
    }
    with open(result_dir / "audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_result, f, ensure_ascii=False, indent=2)
    
    log(f"\n✅ 完成！结果保存到: {output_path}")
    
    # 显示时长变化
    orig = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True
    )
    cut = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True, check=True
    )
    orig_dur = float(orig.stdout.strip())
    cut_dur = float(cut.stdout.strip())
    log(f"📹 时长: {orig_dur:.1f}s → {cut_dur:.1f}s (删除 {orig_dur - cut_dur:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="Videocut - AI 口播视频剪辑")
    parser.add_argument("--task", help="任务目录，如 source-001")
    parser.add_argument("--all", action="store_true", help="处理所有任务")
    parser.add_argument("--api-key", help="MiniMax API Key")
    
    args = parser.parse_args()
    
    # 设置 API Key
    global MINIMAX_API_KEY
    if args.api_key:
        MINIMAX_API_KEY = args.api_key
    
    if not MINIMAX_API_KEY:
        error("请设置 MiniMax API Key:")
        error("  export MINIMAX_API_KEY='your-key'")
        error("  或使用 --api-key 参数")
        sys.exit(1)
    
    work_dir = Path(WORK_DIR)
    
    if args.all:
        # 处理所有任务
        for source_dir in sorted(work_dir.glob("source-*")):
            result_name = f"result-{source_dir.name.split('-')[1]}"
            if not (work_dir / result_name).exists():
                process_task(str(source_dir))
    elif args.task:
        # 处理指定任务
        source_dir = work_dir / args.task
        if not source_dir.exists():
            error(f"任务目录不存在: {source_dir}")
            sys.exit(1)
        process_task(str(source_dir))
    else:
        # 列出可用任务
        print("可用任务:")
        for source_dir in sorted(work_dir.glob("source-*")):
            result_name = f"result-{source_dir.name.split('-')[1]}"
            status = "✅" if (work_dir / result_name).exists() else "⏳"
            print(f"  {status} {source_dir.name}")


if __name__ == "__main__":
    main()
