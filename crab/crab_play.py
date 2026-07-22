from machine import Pin, SPI
import time

# ==== 引脚（和你的接线一致）====
SCK, MOSI, CS, DC, RST, BL = 4, 6, 7, 1, 0, 5
bl  = Pin(BL,  Pin.OUT); bl.value(1)
cs  = Pin(CS,  Pin.OUT, value=1)
dc  = Pin(DC,  Pin.OUT, value=0)
rst = Pin(RST, Pin.OUT, value=1)
spi = SPI(1, baudrate=10000000, polarity=0, phase=0,
          sck=Pin(SCK), mosi=Pin(MOSI))

def wr_cmd(c):
    dc.value(0); cs.value(0); spi.write(bytes([c])); cs.value(1)

def wr_data(d):
    dc.value(1); cs.value(0); spi.write(d); cs.value(1)

# ==== 初始化 ST7789 ====
rst.value(1); time.sleep_ms(50)
rst.value(0); time.sleep_ms(50)
rst.value(1); time.sleep_ms(150)
wr_cmd(0x01); time.sleep_ms(150)
wr_cmd(0x11); time.sleep_ms(150)
wr_cmd(0x3A); wr_data(b'\x55')
wr_cmd(0x36); wr_data(b'\x00')
wr_cmd(0x21)
wr_cmd(0x13)
wr_cmd(0x29); time.sleep_ms(50)

WIDTH = HEIGHT = 240
SIZE = 200                      # 螃蟹精灵图边长（留边框）
OX = (WIDTH - SIZE) // 2        # 居中偏移
OY = (HEIGHT - SIZE) // 2

def set_window(x0, y0, x1, y1):
    wr_cmd(0x2A); wr_data(bytes([x0 >> 8, x0 & 0xff, x1 >> 8, x1 & 0xff]))
    wr_cmd(0x2B); wr_data(bytes([y0 >> 8, y0 & 0xff, y1 >> 8, y1 & 0xff]))
    wr_cmd(0x2C)

def fill(color):
    set_window(0, 0, WIDTH - 1, HEIGHT - 1)
    line = bytes([color >> 8, color & 0xff]) * WIDTH
    dc.value(1); cs.value(0)
    for _ in range(HEIGHT):
        spi.write(line)
    cs.value(1)

# 先铺一次深色背景（和图里的背景一致，边框才不突兀）
fill(0x1083)   # RGB565 of (16,16,24)

# ==== 播放 idle 动画 ====
FRAME_BYTES = SIZE * SIZE * 2   # 28800
NFRAMES = 12
buf = bytearray(FRAME_BYTES)

f = open('idle.bin', 'rb')
print("开始播放 idle 动画，Ctrl-C 或点 STOP 停止")
try:
    while True:
        for i in range(NFRAMES):
            f.seek(i * FRAME_BYTES)
            f.readinto(buf)
            set_window(OX, OY, OX + SIZE - 1, OY + SIZE - 1)
            dc.value(1); cs.value(0)
            spi.write(buf)
            cs.value(1)
            time.sleep_ms(70)
finally:
    f.close()
