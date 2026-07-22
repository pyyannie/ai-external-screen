# 调试版：记录开机次数 + 收到的指令，判断是"没收到"还是"被复位"
from machine import Pin, SPI
import time, sys, select

def log(msg):
    try:
        with open('/rx.log', 'a') as f:
            f.write(msg + '\n')
    except:
        pass

log('BOOT ' + str(time.ticks_ms()))

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

n = 0
while True:
    if poll.poll(0):
        line = sys.stdin.readline()
        if line:
            log('RX: ' + repr(line))
    n += 1
    if n % 100 == 0:
        log('alive ' + str(n))
    time.sleep_ms(50)
