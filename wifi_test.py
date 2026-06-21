import network, time
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
time.sleep(2)
wlan.active(True)
time.sleep(1)
wlan.disconnect()
time.sleep(1)
nets = wlan.scan()
print("Found", len(nets), "networks:")
for n in nets:
    print(" ", n[0])
wlan.connect("YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD")
for i in range(30):
    s = wlan.status()
    print(i, "status:", s, "connected:", wlan.isconnected())
    if wlan.isconnected():
        print("Success! IP:", wlan.ifconfig()[0])
        break
    time.sleep(1)
