#!/usr/bin/env python3
"""给 Claude-外接屏幕2.0 螃蟹板发状态名。
用法: python3 crab_send.py notification
打开串口时禁用 DTR/RTS，尽量避免 ESP32-C3 复位（屏幕不闪）。
"""
import sys, glob, time

def find_port():
    c = (glob.glob('/dev/cu.usbmodem*') +
         glob.glob('/dev/cu.wchusbserial*') +
         glob.glob('/dev/cu.usbserial*'))
    return c[0] if c else None

def main():
    state = sys.argv[1] if len(sys.argv) > 1 else 'idle'
    port = find_port()
    if not port:
        print('找不到串口'); return
    import serial
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.dtr = False       # 禁用复位信号
    s.rts = False
    s.open()
    s.write((state + '\r\n').encode())
    s.flush()
    time.sleep(0.05)
    s.close()
    print(f'已发送: {state} -> {port}')

if __name__ == '__main__':
    main()
