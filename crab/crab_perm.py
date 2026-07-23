#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""螃蟹授权登记：读 hook 的 stdin(JSON)，按 session_id 建/删登记文件。

翻译官(crab_bridge.py)扫描 ~/.crab-pending/：有文件=有窗口在等授权→举灯泡；空了→放下。

用法(在 hook 里)：
  crab_perm.py add    # PermissionRequest：登记"我这个会话在等授权"
  crab_perm.py clear  # PostToolUse/PermissionDenied/Stop/SessionEnd：撤销登记
"""
import sys, os, json

PENDING_DIR = os.path.expanduser('~/.crab-pending')

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    sid = data.get('session_id')
    if not sid:
        return
    os.makedirs(PENDING_DIR, exist_ok=True)
    path = os.path.join(PENDING_DIR, sid)
    if action == 'add':
        try:
            open(path, 'w').close()   # 建空文件登记
        except OSError:
            pass
    elif action == 'clear':
        try:
            os.remove(path)           # 撤销登记
        except OSError:
            pass                      # 本来就没有，忽略

if __name__ == '__main__':
    main()
