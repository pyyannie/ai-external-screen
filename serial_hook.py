#!/usr/bin/env python3
import sys
import json
import glob
import time

def find_port():
    candidates = (
        glob.glob('/dev/cu.usbmodem*') +
        glob.glob('/dev/cu.wchusbserial*') +
        glob.glob('/dev/cu.usbserial*')
    )
    return candidates[0] if candidates else None

def main():
    try:
        data = json.loads(sys.stdin.read())
        event = data.get('hook_event_name', '')
        tool_name = data.get('tool_name', '')
    except Exception:
        event = ''
        tool_name = ''

    if event == 'PreToolUse' and tool_name:
        send_event = tool_name
    else:
        send_event = event

    if not send_event:
        sys.exit(0)

    port = find_port()
    if not port:
        sys.exit(0)

    try:
        import serial
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(0.5)
        payload = json.dumps({'hook_event_name': send_event}) + '\n'
        ser.write(payload.encode())
        ser.close()
    except Exception:
        pass

if __name__ == '__main__':
    main()
