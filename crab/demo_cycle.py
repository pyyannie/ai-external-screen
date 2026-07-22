import time
import main as M   # 复用 main.py 的驱动和函数（会先初始化屏幕）

M.fill(0x1083)
for state in M.STATES:
    d = M.load_state(state)
    print("演示:", state)
    if not d:
        print("  缺文件"); continue
    t0 = time.ticks_ms()
    fi = 0
    while time.ticks_diff(time.ticks_ms(), t0) < 2500:
        M.draw_frame(d, fi % d['nfr'])
        fi += 1
        time.sleep_ms(90)
    d['f'].close()
print("巡演结束")
