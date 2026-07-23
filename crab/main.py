from machine import Pin, SPI
import time, sys, select, micropython

# ==== 引脚 ====
SCK, MOSI, CS, DC, RST, BL = 4, 6, 7, 1, 0, 5
bl  = Pin(BL,  Pin.OUT); bl.value(1)
cs  = Pin(CS,  Pin.OUT, value=1)
dc  = Pin(DC,  Pin.OUT, value=0)
rst = Pin(RST, Pin.OUT, value=1)
spi = SPI(1, baudrate=40000000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI))

def wr_cmd(c):
    dc.value(0); cs.value(0); spi.write(bytes([c])); cs.value(1)
def wr_data(d):
    dc.value(1); cs.value(0); spi.write(d); cs.value(1)

# ==== 初始化 ST7789 ====
rst.value(1); time.sleep_ms(50); rst.value(0); time.sleep_ms(50); rst.value(1); time.sleep_ms(150)
wr_cmd(0x01); time.sleep_ms(150)
wr_cmd(0x11); time.sleep_ms(150)
wr_cmd(0x3A); wr_data(b'\x55')
wr_cmd(0x36); wr_data(b'\x00')
wr_cmd(0x21); wr_cmd(0x13); wr_cmd(0x29); time.sleep_ms(50)

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
    set_window(ox, oy, ox + size - 1, oy + size - 1)
    dc.value(1); cs.value(0)
    i = 0; L = len(data); CH = 2048
    while i < L:
        cnt = (data[i] << 8) | data[i + 1]
        px = bytes(data[i + 2:i + 4])
        i += 4
        while cnt > 0:
            m = cnt if cnt < CH else CH
            spi.write(px * m)
            cnt -= m
    cs.value(1)

# ==== 打开某状态文件，只读帧索引，不把帧读进内存(省RAM) ====
def load_state(state):
    try:
        f = open(state + '.bin', 'rb')
    except OSError:
        return None
    hdr = f.read(8)
    size = (hdr[4] << 8) | hdr[5]
    nfr = hdr[6]
    lens = []
    for _ in range(nfr):
        b = f.read(4)
        lens.append((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3])
    base = 8 + 4 * nfr
    offsets = []
    acc = base
    for L in lens:
        offsets.append(acc); acc += L
    ox = (WIDTH - size) // 2
    oy = (HEIGHT - size) // 2
    return {'f': f, 'size': size, 'ox': ox, 'oy': oy,
            'lens': lens, 'offsets': offsets, 'nfr': nfr}

import gc, array
gc.collect()
_rle = bytearray(42000)     # 读单帧RLE的临时缓冲
_out = bytearray(16384)     # 输出分块缓冲(viper填满就刷,省RAM)
_st  = array.array('i', [0, 0, 0, 0])   # viper解压状态: [srcIdx, 剩余run, hi, lo]

@micropython.viper
def _expand(src, srclen: int, dst, cap: int, st) -> int:
    s = ptr8(src); d = ptr8(dst); sp = ptr32(st)
    i = int(sp[0]); rem = int(sp[1]); hi = int(sp[2]); lo = int(sp[3])
    o = 0
    while o < cap:
        if rem == 0:
            if i >= srclen:
                break
            rem = (s[i] << 8) | s[i + 1]
            hi = s[i + 2]; lo = s[i + 3]
            i += 4
        d[o] = hi; d[o + 1] = lo
        o += 2; rem -= 1
    sp[0] = i; sp[1] = rem; sp[2] = hi; sp[3] = lo
    return o

def draw_frame(st, k):
    L = st['lens'][k]
    st['f'].seek(st['offsets'][k])
    mv = memoryview(_rle)[:L]
    st['f'].readinto(mv)
    size = st['size']
    set_window(st['ox'], st['oy'], st['ox'] + size - 1, st['oy'] + size - 1)
    dc.value(1); cs.value(0)
    _st[0] = 0; _st[1] = 0; _st[2] = 0; _st[3] = 0
    ov = memoryview(_out)
    while True:
        n = int(_expand(_rle, L, _out, 16384, _st))
        if n == 0:
            break
        spi.write(ov[:n])
    cs.value(1)

STATES = ('idle', 'thinking', 'typing', 'error', 'happy', 'sleeping', 'notification',
          'building', 'sweeping', 'juggling', 'groove')

# 串口非阻塞读取
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
def read_cmd():
    cmd = None
    while poll.poll(0):
        line = sys.stdin.readline()
        if line:
            s = line.strip()
            if s:            # 跳过 \r\n 拆出来的空行，保留最后一个非空指令
                cmd = s
    return cmd

fill(0x1083)
cur = 'idle'
data = load_state(cur)
last_input = time.ticks_ms()
SLEEP_AFTER = 60000    # idle 真空闲 60秒→睡
STUCK_AFTER = 180000   # 任何忙碌态卡满3分钟无更新→判定卡死(如API断线),兜底睡

def run():
    global cur, data, last_input
    print("螃蟹启动！默认 idle。串口发状态名切换:", STATES)
    fi = 0
    happy_until = 0
    while True:
        cmd = read_cmd()
        if cmd:
            if cmd in STATES and cmd != cur:
                cur = cmd
                d = load_state(cur)
                if d:
                    if data: data['f'].close()
                    data = d; fi = 0
                if cur == 'happy':
                    happy_until = time.ticks_add(time.ticks_ms(), 4000)  # 开心演4秒
            last_input = time.ticks_ms()
        # happy 演完自动回 idle
        if cur == 'happy' and time.ticks_diff(time.ticks_ms(), happy_until) > 0:
            cur = 'idle'; d = load_state(cur)
            if d:
                if data: data['f'].close()
                data = d; fi = 0
        # idle 空闲60秒→睡；其他忙碌态卡满3分钟无更新→判定卡死(API断线等)兜底睡
        idle_timeout = cur == 'idle' and time.ticks_diff(time.ticks_ms(), last_input) > SLEEP_AFTER
        stuck_timeout = cur != 'sleeping' and time.ticks_diff(time.ticks_ms(), last_input) > STUCK_AFTER
        if idle_timeout or stuck_timeout:
            cur = 'sleeping'; d = load_state(cur)
            if d:
                if data: data['f'].close()
                data = d; fi = 0
        if data:
            draw_frame(data, fi % data['nfr'])
            fi += 1
        time.sleep_ms(90)

if __name__ == '__main__':
    run()

