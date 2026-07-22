from machine import Pin, SPI
import time

SCK, MOSI, CS, DC, RST, BL = 4, 6, 7, 1, 0, 5
bl  = Pin(BL,  Pin.OUT); bl.value(1)
cs  = Pin(CS,  Pin.OUT, value=1)
dc  = Pin(DC,  Pin.OUT, value=0)
rst = Pin(RST, Pin.OUT, value=1)
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI))

def wr_cmd(c):
    dc.value(0); cs.value(0); spi.write(bytes([c])); cs.value(1)
def wr_data(d):
    dc.value(1); cs.value(0); spi.write(d); cs.value(1)

rst.value(1); time.sleep_ms(50); rst.value(0); time.sleep_ms(50); rst.value(1); time.sleep_ms(150)
wr_cmd(0x01); time.sleep_ms(150)
wr_cmd(0x11); time.sleep_ms(150)
wr_cmd(0x3A); wr_data(b'\x55')
wr_cmd(0x36); wr_data(b'\x00')
wr_cmd(0x21); wr_cmd(0x13); wr_cmd(0x29); time.sleep_ms(50)   # 反显=正确颜色

WIDTH = HEIGHT = 240

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

def blit_rle(data, size, ox, oy):
    """在 (ox,oy) 处解压并画一帧 size×size 的 RLE 图。"""
    set_window(ox, oy, ox + size - 1, oy + size - 1)
    dc.value(1); cs.value(0)
    i = 0; L = len(data); CH = 2048
    while i < L:
        cnt = (data[i] << 8) | data[i + 1]
        px = data[i + 2:i + 4]
        i += 4
        while cnt > 0:
            m = cnt if cnt < CH else CH
            spi.write(px * m)
            cnt -= m
    cs.value(1)

def load_frame(fname, k):
    """读取 CRAB 文件的第 k 帧 RLE 数据，返回 (data, size, ox, oy)。"""
    f = open(fname, 'rb')
    hdr = f.read(8)
    size = (hdr[4] << 8) | hdr[5]
    nfr = hdr[6]
    lens = []
    for _ in range(nfr):
        b = f.read(4)
        lens.append((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3])
    body = 8 + 4 * nfr
    off = body + sum(lens[:k])
    f.seek(off)
    data = f.read(lens[k])
    f.close()
    ox = (WIDTH - size) // 2
    oy = (HEIGHT - size) // 2
    return data, size, ox, oy

fill(0x1083)
data, size, ox, oy = load_frame('idle.bin', 6)
blit_rle(data, size, ox, oy)
print("已显示静止螃蟹(RLE)，可以拍照了 size=", size)
