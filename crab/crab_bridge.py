#!/usr/bin/env python3
"""Claude-外接屏幕2.0 常驻翻译官。
端口只开一次(只让板子复位这一次)，之后常开；监视 ~/.crab-state 文件，
内容变了就把状态名发给螃蟹板。hook 只需 echo 状态名到该文件，瞬间完成、不碰串口。
"""
import os, glob, time, sys

STATE_FILE = os.path.expanduser('~/.crab-state')
VALID = {'idle', 'thinking', 'typing', 'error', 'happy', 'sleeping', 'notification'}

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

def main():
    ser = open_port()
    if not ser:
        print('找不到串口，退出'); return
    print('翻译官已启动，监视', STATE_FILE)
    last = None
    while True:
        st = read_state()
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
