"""Dialogue parsing is independent of API, inference and persistence."""

import re


def parse_dialogue(text):
    result = []
    errors = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("(", "（")):
            continue
        match = re.fullmatch(r"\[([^\]]+)\]\s*(.+)", line)
        if not match or not match[1].strip() or not match[2].strip():
            errors.append(number)
        else:
            result.append({"speaker": match[1].strip(), "text": match[2].strip()})
    if errors:
        raise ValueError(
            f"第 {', '.join(map(str, errors))} 行格式无效，请使用 [角色名] 文本"
        )
    if not result:
        raise ValueError("没有有效对话")
    return result
