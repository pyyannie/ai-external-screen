#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse 分派：按 Claude 正在调用的工具名，给螃蟹屏写不同的动画状态。

读 hook 的 stdin(JSON) 取 tool_name，写到 ~/.crab-state，翻译官再发给板子。
映射：
  Edit/Write/... → building(搬砖)   Bash → sweeping(扫地)
  Read/Grep/Glob → juggling(杂耍)   WebFetch/WebSearch → groove(戴耳机)
  其他 → typing(原样)
"""
import sys, os, json

STATE_FILE = os.path.expanduser('~/.crab-state')

TOOL_MAP = {
    'Edit': 'building', 'Write': 'building', 'MultiEdit': 'building',
    'NotebookEdit': 'building',
    'Bash': 'sweeping',
    'Read': 'juggling', 'Grep': 'juggling', 'Glob': 'juggling',
    'WebFetch': 'groove', 'WebSearch': 'groove',
}

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    tool = data.get('tool_name', '')
    state = TOOL_MAP.get(tool, 'typing')   # 未映射的工具默认 typing
    try:
        with open(STATE_FILE, 'w') as f:
            f.write(state)
    except OSError:
        pass

if __name__ == '__main__':
    main()
