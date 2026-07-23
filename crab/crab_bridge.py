#!/usr/bin/env python3
"""Claude-外接屏幕2.0 常驻翻译官。
端口只开一次(只让板子复位这一次)，之后常开；监视 ~/.crab-state 文件，
内容变了就把状态名发给螃蟹板。hook 只需 echo 状态名到该文件，瞬间完成、不碰串口。
"""
import os, glob, time, sys

STATE_FILE = os.path.expanduser('~/.crab-state')
PENDING_DIR = os.path.expanduser('~/.crab-pending')
STALE_SEC = 600   # 登记文件超过10分钟视为残留(窗口崩溃没清)，忽略，防灯泡永久举着
VALID = {'idle', 'thinking', 'typing', 'error', 'happy', 'sleeping', 'notification',
         'building', 'sweeping', 'juggling', 'groove'}

def find_port():
    c = (glob.glob('/dev/cu.usbmodem*') +
         glob.glob('/dev/cu.wchusbserial*') +
         glob.glob('/dev/cu.usbserial*'))
    return c[0] if c else None

def open_port():
    import serial
    port = find_port()
    if not port:
        return None
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.dtr = False
    s.rts = False
    s.open()
    time.sleep(2.0)   # 等板子这一次复位后重新起来
    return s

def read_state():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip()
    except OSError:
        return None

def any_pending():
    """有任何未过期的授权登记 → 返回 True(该举灯泡)。顺手清理残留的旧登记。"""
    try:
        names = os.listdir(PENDING_DIR)
    except OSError:
        return False
    now = time.time()
    alive = False
    for n in names:
        p = os.path.join(PENDING_DIR, n)
        try:
            age = now - os.path.getmtime(p)
        except OSError:
            continue
        if age > STALE_SEC:
            try: os.remove(p)          # 残留登记(窗口崩了没清)，删掉
            except OSError: pass
        else:
            alive = True
    return alive

def main():
    ser = open_port()
    if not ser:
        print('找不到串口，退出'); return
    print('翻译官已启动，监视', STATE_FILE, '+', PENDING_DIR)
    last = None
    while True:
        # 授权优先：只要有窗口在等授权就举灯泡，全部处理完立刻回到正常状态
        if any_pending():
            st = 'notification'
        else:
            st = read_state()
            if st == 'notification':
                st = 'idle'   # 没人在等授权了，别再显示旧的灯泡状态
        if st and st != last and st in VALID:
            try:
                ser.write((st + '\r\n').encode())
                ser.flush()
                print('->', st)
                last = st
            except Exception as e:
                # 端口断了(拔线等)，尝试重开
                print('端口异常，重连中:', e)
                try: ser.close()
                except: pass
                time.sleep(2)
                ser = open_port()
                if not ser:
                    time.sleep(3)
        time.sleep(0.15)

if __name__ == '__main__':
    main()
