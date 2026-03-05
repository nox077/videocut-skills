#!/usr/bin/env python3
"""
转录纠错
使用 AI 纠正转录中的识别错误
"""

import json
import os
import requests
from pathlib import Path

# MiniMax 配置
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"

def call_minimax(prompt: str) -> str:
    """调用 MiniMax API"""
    if not MINIMAX_API_KEY:
        print("警告: 未设置 MINIMAX_API_KEY，跳过纠错")
        return None
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": "你是一个语音识别专家。请根据音频内容纠正转录文本中的错误。"},
        {"role": "user", "content": prompt}
    ]
    
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
            print(f"API 错误: {response.status_code}")
            return None
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"调用失败: {e}")
        return None

def correct_transcript(transcript_json: str, output_json: str = None) -> dict:
    """纠正转录错误"""
    
    # 读取转录
    with open(transcript_json, 'r', encoding='utf-8') as f:
        content = f.read()
        idx = content.find('{')
        data = json.loads(content[idx:])
    
    segments = data.get("segments", [])
    
    # 构建转录文本（带时间戳）
    transcript_text = ""
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        transcript_text += f"[{start:.2f}s - {end:.2f}s] {text}\n"
    
    # 调用 AI 纠错
    prompt = f"""请分析以下转录文本，纠正识别错误。

要求：
1. 只纠正明显的识别错误（同音字、专业术语等）
2. 保持字数不变
3. 保持时间戳不变
4. 不要改变原意

转录文本：
{transcript_text}

请返回 JSON 格式：
{{
    "corrected": [
        {{"start": 起始秒, "end": 结束秒, "text": "纠正后的文本"}}
    ]
}}

只返回 JSON。"""

    print("🔍 AI 纠错中...")
    result = call_minimax(prompt)
    
    if not result:
        print("纠错失败，使用原转录")
        return data
    
    # 解析结果
    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            corrected_data = json.loads(json_match.group())
        else:
            corrected_data = json.loads(result)
        
        # 替换文本
        corrected_segments = []
        corrections = {c["start"]: c for c in corrected_data.get("corrected", [])}
        
        for seg in segments:
            start = seg.get("start")
            if start in corrections:
                seg["text"] = corrections[start]["text"]
            corrected_segments.append(seg)
        
        data["segments"] = corrected_segments
        
        # 保存
        if output_json is None:
            output_json = Path(transcript_json).stem + "_fixed.json"
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 纠错完成: {output_json}")
        return data
        
    except Exception as e:
        print(f"解析失败: {e}")
        return data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="转录纠错")
    parser.add_argument("transcript", help="转录 JSON 文件")
    parser.add_argument("--output", "-o", help="输出文件")
    args = parser.parse_args()
    
    correct_transcript(args.transcript, args.output)
