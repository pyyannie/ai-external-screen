#!/usr/bin/env python3
"""把 Clawd 的 GIF 转成 ESP32 能读的 RGB565 二进制帧文件。
每个状态输出一个 .bin：N 帧连续排列，每帧 SIZE*SIZE 像素，每像素 2 字节(大端 RGB565)。
自动裁剪到螃蟹轮廓，让它撑满画面。
"""
import sys, os
from PIL import Image, ImageEnhance

SIZE = 237                 # 精灵图边长（1.3倍，接近满屏）
FRAMES = 8                 # 每个状态抽多少帧（8帧省空间且流畅）
BG = (16, 16, 24)          # 深色背景
SAT = 1.8                  # 饱和度增强（只加在螃蟹身上，背景不动）
ROTATE = True              # True = 顺时针90度（装壳方向）
# 所有状态统一的固定取景框(原图302x300坐标)：螃蟹在下部，上方留头顶空间给气泡/特效
CROP_BOX = (51, 96, 251, 296)   # 下移20px：螃蟹往上挪+脚下留白离开底边

GIF_DIR = "/Users/anniepeng/claude_lamp/crab/gifs"
OUT_DIR = "/Users/anniepeng/claude_lamp/crab/bin"


def to_rgb565_be(img):
    px = img.load()
    w, h = img.size
    out = bytearray(w * h * 2)
    i = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            out[i] = v >> 8
            out[i + 1] = v & 0xFF
            i += 2
    return bytes(out)


def rle_encode(fb):
    """行程编码：连续相同像素压成 (count2字节, 像素2字节)。纯色背景压缩率极高。"""
    out = bytearray()
    i = 0
    L = len(fb)
    while i < L:
        px = fb[i:i + 2]
        c = 1
        while i + 2 * c < L and fb[i + 2 * c:i + 2 * c + 2] == px and c < 65535:
            c += 1
        out += bytes([c >> 8, c & 0xff])
        out += px
        i += 2 * c
    return bytes(out)


def coalesce(im):
    """逐帧取完整画面（Clawd 的 GIF 每帧本身就是完整帧，不能累加否则跳动会留重影）。"""
    n = getattr(im, "n_frames", 1)
    frames = []
    for i in range(n):
        im.seek(i)
        frames.append(im.convert("RGBA").copy())
    return frames


def union_bbox(frames):
    """所有帧不透明区域的并集包围盒（保证动画不被裁掉）。"""
    box = None
    for f in frames:
        bb = f.split()[3].getbbox()
        if bb:
            box = bb if box is None else (
                min(box[0], bb[0]), min(box[1], bb[1]),
                max(box[2], bb[2]), max(box[3], bb[3]))
    return box


def square_crop(box, w, h):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    half = max(x1 - x0, y1 - y0) / 2 * PAD
    return (max(0, int(cx - half)), max(0, int(cy - half)),
            min(w, int(cx + half)), min(h, int(cy + half)))


def convert(state):
    path = os.path.join(GIF_DIR, f"clawd-{state}.gif")
    im = Image.open(path)
    frames = coalesce(im)
    n = len(frames)
    idx = [round(k * (n - 1) / (FRAMES - 1)) for k in range(FRAMES)]
    rle_frames = []
    for k in idx:
        f = frames[k].crop(CROP_BOX)
        # 饱和度只加在螃蟹上（保留透明度），背景不受影响
        if SAT != 1.0:
            rgb = ImageEnhance.Color(f.convert("RGB")).enhance(SAT)
            f = Image.merge("RGBA", (*rgb.split(), f.split()[3]))
        bg = Image.new("RGBA", f.size, BG + (255,))
        comp = Image.alpha_composite(bg, f).convert("RGB")
        comp = comp.resize((SIZE, SIZE), Image.LANCZOS)
        if ROTATE:
            comp = comp.transpose(Image.ROTATE_90)   # 顺时针90 + 上下颠倒180 = ROTATE_90
        rle_frames.append(rle_encode(to_rgb565_be(comp)))
    # 文件格式: 'CRAB' + SIZE(2) + FRAMES(1) + 保留(1) + 每帧长度(4 x FRAMES) + RLE数据
    header = bytearray(b'CRAB')
    header += bytes([SIZE >> 8, SIZE & 0xff, FRAMES, 0])
    for r in rle_frames:
        L = len(r)
        header += bytes([L >> 24 & 0xff, L >> 16 & 0xff, L >> 8 & 0xff, L & 0xff])
    body = b''.join(rle_frames)
    outpath = os.path.join(OUT_DIR, f"{state}.bin")
    with open(outpath, "wb") as fp:
        fp.write(header)
        fp.write(body)
    total = len(header) + len(body)
    raw = SIZE * SIZE * 2 * FRAMES
    print(f"{state:10s} -> {os.path.basename(outpath)}  "
          f"{FRAMES}帧 x {SIZE}x{SIZE}  RLE {total} 字节 ({total/1024:.0f} KB, "
          f"压到原始的 {total/raw*100:.0f}%)")


if __name__ == "__main__":
    states = sys.argv[1:] or ["idle"]
    for s in states:
        convert(s)
