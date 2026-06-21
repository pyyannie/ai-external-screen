import sys
import ujson # type: ignore
import micropython # type: ignore
from machine import Timer # type: ignore
import claude_webserver_V1 as server # type: ignore

action = server.ClaudeAction()

def _do_tick(_):
    action.tick()

def _timer_cb(t):
    if action._thinking:
        try:
            micropython.schedule(_do_tick, None)
        except:
            pass

timer = Timer(0)
timer.init(period=600, mode=Timer.PERIODIC, callback=_timer_cb)

while True:
    line = sys.stdin.readline().strip()
    if line:
        try:
            data = ujson.loads(line)
            event = data.get('hook_event_name', '')
            action._handle(event)
            sys.stdout.write('OK\n')
        except:
            pass
