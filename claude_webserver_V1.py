# 初始版本
import usocket as socket # type: ignore
import utime  # type: ignore
import ujson # type: ignore
from machine import Pin, SPI # type: ignore
from claude_st7735 import ST7735, BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA

class ClaudeAction:
    """
    整合ClaudeCodeDoll的所有动作控制
    """
    def __init__(self):
        """
        初始化ClaudeCodeDoll动作控制
        """
        self.spi = SPI(1, baudrate=4_000_000, polarity=0, phase=0, sck=Pin(4), mosi=Pin(6))
        self.lcd = ST7735(self.spi, rst=Pin(0, Pin.OUT), dc=Pin(1, Pin.OUT), cs=Pin(7, Pin.OUT))
        self.lcd.set_rot(1)  # 横屏 160x128
        self._thinking = False
        self._tick_n = 0
        self.lcd.fill(BLACK)
        self.lcd.center("HI", 48, GREEN, None, 4)

    def _show_clock(self, h, m, s, date, day):
        self.lcd.fill(BLACK)
        # HH:MM sz=3 青色从左边开始（5字符×24px=120px）
        hm = f"{h}:{m}"
        self.lcd.text(hm, 0, 20, CYAN, None, 3)
        # SS sz=2 白色紧贴右边（x=122）
        self.lcd.text(s, 122, 36, WHITE, None, 2)
        # 日期 + 星期 sz=2 绿色居中
        label = f"{date} {day}"
        x = (self.lcd.w - len(label) * 16) // 2
        self.lcd.text(label, max(0, x), 76, GREEN, None, 2)

    def _show_lines(self, lines, color=None):
        ORANGE = 0x037F
        if color is None:
            color = WHITE
        elif color == 'orange':
            color = ORANGE
        elif color == 'cyan':
            color = CYAN
        elif color == 'green':
            color = GREEN
        self.lcd.fill(BLACK)
        n = min(len(lines), 10)
        y = max(2, (128 - n * 12) // 2)
        for line in lines[:10]:
            x = max(0, (160 - len(line) * 8) // 2)
            self.lcd.text(line, x, y, color)
            y += 12

    def _draw_smiley(self):
        ORANGE = 0x037F
        self.lcd.fill(BLACK)
        # 天线（横屏 160x128，脸居中 x=40~120）
        self.lcd.rect(78, 6, 4, 8, ORANGE)
        self.lcd.rect(73, 4, 14, 5, ORANGE)
        # 脑袋
        self.lcd.rect(40, 14, 80, 65, ORANGE)
        # 左眼
        self.lcd.rect(53, 26, 14, 14, WHITE)
        self.lcd.rect(58, 31, 5, 5, BLACK)
        # 右眼
        self.lcd.rect(93, 26, 14, 14, WHITE)
        self.lcd.rect(98, 31, 5, 5, BLACK)
        # 嘴（U形）
        self.lcd.rect(62, 50, 3, 18, BLACK)
        self.lcd.rect(95, 50, 3, 18, BLACK)
        self.lcd.rect(62, 66, 36, 3, BLACK)
        # DONE
        self.lcd.center("DONE", 88, ORANGE, None, 2)

    def tick(self):
        ORANGE = 0x037F
        if self._tick_n < 0:
            self._tick_n += 1
            return
        self._tick_n = (self._tick_n % 3) + 1
        self.lcd.fill(BLACK)
        dots = "o" * self._tick_n
        self.lcd.center(dots, 52, ORANGE, None, 3)

    def _handle(self, event: str):
        ORANGE = 0x037F
        print(f'执行指令: {event}')
        self._thinking = False
        if event == 'UserPromptSubmit':
            self._thinking = True
            self._tick_n = -2  # 延迟2个 tick（约1.2秒）再开始动画
            self.lcd.fill(BLACK)
            self.lcd.center("COPY!", 52, GREEN, None, 3)
        elif event == 'Stop' or event == 'Notification':
            self._draw_smiley()
        elif event == 'PermissionRequest':
            self.lcd.fill(BLACK)
            self.lcd.center("ASK!", 48, MAGENTA, None, 4)
        elif event in ('Read', 'Glob', 'Grep'):
            self.lcd.fill(BLACK)
            self.lcd.center("READ", 52, CYAN, None, 3)
        elif event in ('Edit', 'Write'):
            self.lcd.fill(BLACK)
            self.lcd.center("EDIT", 52, YELLOW, None, 3)
        elif event == 'Bash':
            self.lcd.fill(BLACK)
            self.lcd.center("BASH", 52, RED, None, 3)
        elif event.startswith('REST:'):
            payload = event[5:]
            parts = payload.split('|')
            if len(parts) >= 5 and parts[0] == 'CLOCK':
                self._show_clock(parts[1], parts[2], parts[3], parts[4], parts[5] if len(parts) > 5 else '')
            else:
                color = 'orange' if parts and parts[0].startswith('SG') else None
                self._show_lines(parts, color)
        else:
            self.lcd.fill(BLACK)
            self.lcd.center(event[:6], 56, WHITE, None, 2)

def safe_decode(data):
    """安全解码字节为字符串，兼容 MicroPython"""
    try:
        return data.decode('utf-8')
    except (UnicodeError, TypeError):
        # 逐字节尝试，忽略无效字符
        result = ''
        for b in data:
            if b < 128:
                result += chr(b)
            else:
                result += '?'
        return result

def parse_request(request):
    """解析 HTTP 请求为统一的 JSON 结构"""
    try:
        import ujson as json # type: ignore
    except ImportError:
        import json

    result = {
        'method': '',
        'path': '',
        'query': '',
        'headers': {},
        'body': None
    }

    lines = request.split('\r\n')
    if not lines:
        return result

    # 解析请求行
    first_line = lines[0].split(' ')
    if len(first_line) >= 2:
        result['method'] = first_line[0]
        result['path'] = first_line[1]
        # 解析 query string
        if '?' in result['path']:
            path_parts = result['path'].split('?', 1)
            result['path'] = path_parts[0]
            result['query'] = path_parts[1]

    # 解析请求头
    body_start = 0
    for i, line in enumerate(lines[1:], 1):
        if line == '':
            body_start = i + 1
            break
        if ': ' in line:
            key, value = line.split(': ', 1)
            result['headers'][key] = value

    # 解析请求体
    if body_start > 0 and body_start < len(lines):
        body_str = '\r\n'.join(lines[body_start:])
        if body_str:
            try:
                result['body'] = json.loads(body_str)
            except:
                result['body'] = body_str

    return result


def make_json_response(data):
    """构建 JSON 响应"""
    try:
        import ujson as json # type: ignore
    except ImportError:
        import json
    body = json.dumps(data)
    return f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}'


def main():
    claudeaction = ClaudeAction()
    import network # type: ignore
    wlan = network.WLAN(network.STA_IF)
    ip = wlan.ifconfig()[0]
    claudeaction.lcd.fill(BLACK)
    parts = ip.split('.')
    claudeaction.lcd.center(parts[0]+'.'+parts[1], 30, CYAN, None, 2)
    claudeaction.lcd.center(parts[2]+'.'+parts[3], 75, WHITE, None, 3)
    s = socket.socket()  # type: ignore
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # type: ignore
    s.bind(socket.getaddrinfo('0.0.0.0', 80)[0][-1])  # type: ignore
    s.listen(5)

    print('服务器已启动！')

    while True:
        cl, client_addr = s.accept()  # type: ignore
        cl.settimeout(10.0)
        try:
            # 先读取请求头，找到 Content-Length
            header_data = b''
            while True:
                chunk = cl.recv(1024)
                if not chunk:
                    cl.close()
                    break
                header_data += chunk
                # 检测请求头结束（\r\n\r\n）
                if b'\r\n\r\n' in header_data:
                    break

            header_str = safe_decode(header_data)
            # 提取 Content-Length
            content_length = 0
            for line in header_str.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    try:
                        content_length = int(line.split(':', 1)[1].strip())
                    except:
                        pass
                    break

            # 计算请求头占用的字节数
            header_end_pos = header_data.find(b'\r\n\r\n')
            body_received = len(header_data) - header_end_pos - 4 if header_end_pos != -1 else len(header_data)

            # 继续读取直到获得完整的 Content-Length 数据
            while body_received < content_length:
                chunk = cl.recv(min(1024, content_length - body_received))
                if not chunk:
                    break
                header_data += chunk
                body_received += len(chunk)

            request_str = safe_decode(header_data)
            req = parse_request(request_str)


            # 只处理 /claude 路径
            if req['path'].startswith('/claude'):
                hook_event_name = ''
                if 'body' in req and req['body'] is not None:
                    body = req['body']
                    # parse_request 已经尝试过 JSON 解析，body 可能是 dict 或 str
                    if isinstance(body, dict):
                        hook_event_name = body.get('hook_event_name', '')
                    elif isinstance(body, str):
                        # str 说明 JSON 解析失败（非截断情况下可能是非法 JSON）
                        try:
                            hook_event_name = ujson.loads(body).get('hook_event_name', '')
                        except Exception as e:
                            print('JSON parse error:', e)
                            print('body:', body)
                    elif isinstance(body, bytes):
                        try:
                            hook_event_name = ujson.loads(body.decode('utf-8')).get('hook_event_name', '')
                        except Exception as e:
                            print('JSON parse error:', e)
                
                result = claudeaction._handle(hook_event_name)
                response = make_json_response({
                    'status': 'ok',
                    'hook_event_name': hook_event_name,
                    'result': result
                })
            else:
                # 其他路径返回 404
                response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 9\r\n\r\nNot Found'

            cl.sendall(response.encode('utf-8'))

        except OSError as e:
            print(f'请求处理错误: {e}')
        except MemoryError:
            try:
                import gc
                gc.collect()
            except:
                pass
        finally:
            try:
                cl.close()
            except OSError:
                pass

if __name__ == '__main__':
    main()
