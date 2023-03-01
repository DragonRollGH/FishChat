import json
import threading
from time import localtime, strftime, sleep, time

try:
    import websocket
    getattr(websocket, 'create_connection')
except AttributeError:
    print("Error: you must uninstall websocket to use websocket-client due to naming conflicts")
except ImportError:
    print("You must have websocket-client installed to use tchat")
    exit(1)

from websocket._exceptions import WebSocketTimeoutException

OFFLINE_THRESHOLD = 45
PING_INTERVAL = 20
PING_DIVIDER = 4 # 3

class HChat:
    def __init__(self, channel, nick):
        """Connects to a channel on https://hack.chat."""
        self.url = "wss://hack.chat/chat-ws" if channel != "offline" else ""
        self.channel = channel
        self.nicks = [nick]
        for i in range(2,10):
            self.nicks.append(self.nicks[0] + str(i))
        self.nicki = 0
        self.usrs = {}
        self.ws = websocket.WebSocket()
        self.revc_thread = threading.Thread(target=self._recv_thread, daemon=1)
        self.ping_thread = threading.Thread(target=self._ping_thread, daemon=1)
        self.online = 0
        self.last_ping = 0
        self.alone = 0
        self.offline_threshold = OFFLINE_THRESHOLD
        self.ping_interval = PING_INTERVAL
        self.ping_divider = PING_DIVIDER
        self.ping_divider_i = 0
        self.on_chat = self._default_callback
        self.on_set = self._default_callback
        self.on_add = self._default_callback
        self.on_remove = self._default_callback
        self.on_debug = self._none_callback
        self.on_info = self._default_callback
        self.on_warn = self._default_callback
        self.on_error = self._default_callback
        self.on_critical = self.stop

    def run(self):
        self.revc_thread.start()
        self.ping_thread.start()

    def offline(self):
        self.online = 0
        self.alone = 0
        self.ws.abort()     # abort recv to daemon connection immediately

    def be_alone(self):
        if self.alone != 1:
            self.alone = 1
            self.on_info("You are alone.")

    def be_group(self):
        if self.alone != 0:
            self.alone = 0
            self.on_info("You are group.")

    def stop(self, msg):
        self._default_callback(msg)
        self.online = 0
        self.ws.close()
        print("[ERROR] EXIT")
        # exit()

    def get_usrs(self):
        self.on_set(self.usrs)

    def get_nick(self):
        return self.nicks[self.nicki]

    def send_message(self, msg):
        """Sends a message on the channel."""
        if self.online:
            self._send_packet({"cmd": "chat", "text": msg})
        else:
            self.on_warn("[WARN] You are offline.")

    def _default_callback(self, *args):
        print(strftime("%H:%M:%S|", localtime()),end="")
        print(*args)

    def _none_callback(self, *args):
        pass

    def _send_packet(self, packet):
        """Sends <packet> (<dict>) to https://hack.chat."""
        if self.ws.connected:
            encoded = json.dumps(packet)
            try:
                self.ws.send(encoded)
                self.last_ping = time()
                # self.on_debug(encoded)
            except Exception as e:
                self.on_warn(str(e.__class__)+str(e))
                self.on_warn("[WARN] Send Exception.")
                self.offline()

    def _daemon_connection(self):
        if not self.online or not self.ws.connected:
            self.on_error("[Error] Reconnecting...")
            self.offline()
            self.ws.close()
            self._connect()

    def _connect(self):
        """ Connect to server. """
        while not self.ws.connected:
            try:
                self.on_info("Connecting to Server...")
                self.online = 0
                self.ws.connect(self.url, timeout=20)   # Connect timeout
                self.ws.settimeout(10)                  # Recv timeout
                websocket._socket.setdefaulttimeout(10)
                self._login()
            except Exception as e:
                self.on_warn(str(e.__class__)+str(e))
                self.on_warn("[WARN] Connect Exception.")
                sleep(5)

    def _login(self):
        """ Send join packet after establish connection. """
        # Use the origin nick
        self.nicki = 0
        retry = 0
        while not self.online:
            self.on_debug("Try to login as "+self.get_nick())
            self._send_packet({"cmd": "join", "channel": self.channel, "nick": self.get_nick()})
            sleep(1)
            res = 0
            while not res:
                try:
                    res = json.loads(self.ws.recv())
                except Exception:
                    # keep recv
                    pass
            if res["cmd"] == "warn":
                if "taken" in res["text"]:
                    # Nick is taken
                    self.nicki += 1
                    sleep(2)
                elif "blocked" in res["text"] or "Wait" in res["text"]:
                    # Try too fast
                    t = 20 + 20*(retry+1)
                    self.on_warn("[WARN] Try too frequently, wait for %d sec. "%(t))
                    sleep(t)
                    retry += 1
            elif res["cmd"] == "onlineSet":
                # Login success
                self.online = 1
                sleep(1)
                self.last_ping = 0
                self.on_debug("Successfully login! ")
                # for u in res["nicks"]:
                #     self.usrs[u] = time()
                self.on_set(res["nicks"])

    def _recv_thread(self):
        while True:
            self._daemon_connection()
            res = 0
            try:
                res = json.loads(self.ws.recv())
            except WebSocketTimeoutException:
                # no idea with connection status, ping immediately
                self.last_ping = 0
                pass
            except Exception as e:
                self.on_warn(str(e.__class__)+str(e))
                self.on_warn("[WARN] Recv Exception.")
                self.offline()
            self.on_debug(res)
            if not res:
                continue
            if res["cmd"] == "chat":
                if not self.usrs.get(res["nick"]):
                    self.on_add(res["nick"])
                self.usrs[res["nick"]] = time()
                if res["text"] != "ping":
                    self.on_chat(res["nick"], res["text"])
                if 'kick ' in res["text"] and (self.get_nick() == res["text"].strip("kick ")):
                    self.send_message("WTF")
                    self.on_critical("[CRITICAL] You are kicked. ")
            elif res["cmd"] == "onlineAdd":
                self.last_ping = 0
            #     self.usrs[res["nick"]] = time()
            #     self.on_add(res["nick"])
            # elif res["cmd"] == "onlineRemove":
            #     if self.usrs.get(res["nick"]):
            #         self.usrs.pop(res["nick"])
            #         self.on_remove(res["nick"])
            elif res["cmd"] == "warn":
                if "blocked" in res["text"]:
                    self.on_error("[ERROR] Send too fast, wait for 10 sec.")
                    self.online = 0
                    sleep(10)
                    self.online = 1
                    self.on_info("Try again now.")
                else:
                    self.on_error(res["text"])
            pop_list = []
            for u, p in self.usrs.items():
                if (time() - p) > self.offline_threshold:
                    pop_list.append(u)
            for u in pop_list:
                self.usrs.pop(u)
                self.on_remove(u)
            for u in self.usrs.keys():
                if u not in self.nicks:
                    self.be_group()
                    break
            else:
                self.be_alone()
            sleep(500/1000)

    def _ping_thread(self):
        while True:
            if (time() - self.last_ping) > self.ping_interval:
                if self.online:
                    if self.ping_divider_i > self.ping_divider:
                        self.ping_divider_i = 0
                        self._send_packet({"cmd": "ping"})
                    self.send_message("ping")
                    self.ping_divider_i += 1
                    self.last_ping = time()
            sleep(1)

if __name__ == "__main__":
    h = HChat("hackchat", "HChat_py")
    h.run()
    while True:
        h.send_message(input('>'))
