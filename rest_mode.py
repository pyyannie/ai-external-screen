#!/usr/bin/env python3
import time, json, glob, random, urllib.request, os, datetime

QUOTES = [
    "Nobody can bring|you peace but|yourself.",
    "Nothing will work|unless you do.",
    "You save yourself|or you remain|unsaved.",
    "Once determined to|help themselves,|nothing stops them.",
    "Trust thyself:|every heart vibrates|to that iron string.",
    "Trust yourself,|you'll know|how to live.",
    "To be yourself|in a world that|tries to change you|is the greatest act.",
    "The strongest man|is he who|stands alone.",
    "You complete yourself.|No one can|complete you.",
    "Nobody will save you.|You've got to|save yourself.",
    "When I accept myself|just as I am,|then I can change.",
    "What a man|can be,|he must be.",
    "Plan to be less|than you are capable|you'll be unhappy.",
    "Most people fear|freedom because it|means responsibility.",
    "The good life is|a process, not|a state of being.",
    "Be the change|you wish to see|in the world.",
    "Life: not holding|good cards, but|playing them well.",
    "Success not final.|Failure not fatal.|Courage to continue.",
    "Our limit tomorrow|is our doubts|of today.",
    "You get what|you work for,|not what you wish.",
    "About life,|three words:|It goes on.",
    "Choices show who|we truly are,|more than abilities.",
    "A person with a why|can bear almost|any how.",
    "Life hurts you,|but those wounds|become your strength.",
    "A man can be|destroyed but|not defeated.",
    "No dependence sure|but dependence|on one's self.",
    "The best lightning|rod is|your own spine.",
    "What I must do|concerns me,|not what others think.",
    "Before saving anyone|you must first|save yourself.",
    "No positive life|with a|negative mind.",
    "God helps those|who help|themselves.",
    "Move the world?|First move|yourself.",
    "Freedom is what we|do with what|is done to us.",
    "Be the heroine|of your life,|not the victim.",
    "Pursue happiness:|you have to|catch it yourself.",
    "Power over your mind,|not outside events.|Find your strength.",
    "No one makes you|feel inferior without|your consent.",
    "Life isn't finding|yourself. It is|creating yourself.",
    "Invest in yourself;|it pays the|best interest.",
    "The more solitary,|the more I|respect myself.",
    "Every path but|your own is|the path of fate.",
    "Never put your key|to happiness in|someone else's pocket.",
    "Want it done well?|Do it|yourself.",
    "The worst: rely|on others and|whine over suffering.",
    "We are our own|devil, making this|world our hell.",
    "If you don't believe|in yourself,|no one else will.",
    "You are your refuge.|Only you can|save yourself.",
    "No one is coming.|This life is|100% your job.",
    "A book inspires,|teacher guides,|only you save you.",
    "Want respect? Prove|you can survive|without anyone.",
    "It's your job to|make things happen|for yourself.",
    "Your life is as|wonderful as you|choose to make it.",
    "Put your mask on|first before|helping others.",
    "No one can|stop you|but yourself.",
    "You steer yourself|any direction|you choose.",
    "Self-care is how|you take your|power back.",
    "Compassion without|yourself is|incomplete.",
    "Waiting for happiness|wastes time.|Create your own.",
    "A man must be|a nonconformist.",
    "In the end, only|you can rely|on yourself.",
]

def is_claude_busy():
    try:
        with open(os.path.expanduser('~/.clawd-state')) as f:
            state = f.read().strip()
        return state in ('thinking', 'typing', 'notification')
    except:
        return False

def find_port():
    candidates = (
        glob.glob('/dev/cu.usbmodem*') +
        glob.glob('/dev/cu.wchusbserial*') +
        glob.glob('/dev/cu.usbserial*')
    )
    return candidates[0] if candidates else None

def send(port_path, event):
    try:
        import serial
        ser = serial.Serial(port_path, 115200, timeout=2)
        time.sleep(0.3)
        ser.write((json.dumps({'hook_event_name': event}) + '\n').encode())
        ser.close()
    except Exception as e:
        print(f"串口发送失败: {e}")

def get_datetime():
    now = datetime.datetime.now()
    return (
        now.strftime("%H"),
        now.strftime("%M"),
        now.strftime("%S"),
        now.strftime("%m-%d"),
        now.strftime("%a").upper(),
    )

def get_weather():
    try:
        url = 'https://wttr.in/Singapore?format=j1'
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        cur = data['current_condition'][0]
        temp = cur['temp_C']
        feels = cur['FeelsLikeC']
        humidity = cur['humidity']
        desc = cur['weatherDesc'][0]['value']
        try:
            uv = cur.get('uvIndex', 'N/A')
            uv_str = f"UV:{uv}"
        except:
            uv_str = "UV:N/A"
        words = desc.split()
        line1, line2 = '', ''
        for w in words:
            if len(line1) + len(w) + 1 <= 18:
                line1 = (line1 + ' ' + w).strip()
            else:
                line2 = (line2 + ' ' + w).strip()
        lines = ['SG Weather', f"{temp}C Feel:{feels}C", f"Hum:{humidity}% {uv_str}"]
        if line1: lines.append(line1)
        if line2: lines.append(line2[:20])
        return lines
    except Exception as e:
        print(f"天气获取失败: {e}")
        return ['SG Weather', 'No data']

def main():
    print("等待 15 秒空闲后进入休息模式...")
    time.sleep(15)

    port = find_port()
    if not port:
        print("找不到 ESP32 串口")
        return
    print(f"找到串口: {port}")

    quotes = QUOTES.copy()
    random.shuffle(quotes)
    qi = 0
    mode = 0  # 0=时间 1=天气 2=名言
    weather_lines = get_weather()
    weather_refresh = time.time()

    while True:
        if is_claude_busy():
            print("Claude 工作中，跳过")
            time.sleep(11)
            continue

        if mode == 0:
            h, m, s, date, day = get_datetime()
            send(port, f'REST:CLOCK|{h}|{m}|{s}|{date}|{day}')
            print(f"时间: {h}:{m}:{s} {date} {day}")
        elif mode == 1:
            if time.time() - weather_refresh > 600:
                weather_lines = get_weather()
                weather_refresh = time.time()
            send(port, f'REST:{"|".join(weather_lines)}')
            print(f"天气: {weather_lines}")
        else:
            q = quotes[qi % len(quotes)]
            qi += 1
            if qi % len(quotes) == 0:
                random.shuffle(quotes)
            send(port, f'REST:{q}')
            print(f"名言: {q}")

        mode = (mode + 1) % 3
        time.sleep(11)

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
