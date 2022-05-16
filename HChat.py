import json
import threading
from time import sleep, time

try:
    import websocket
    getattr(websocket, 'create_connection')
except AttributeError:
    print("Error: you must uninstall websocket to use websocket-client due to naming conflicts")
except ImportError:
    print("You must have websocket-client installed to use tchat")
    exit(1)

class HChat:
    def __init__(self, channel, nick):
        """Connects to a channel on https://hack.chat."""
        self.channel = channel
        self.nicks = [nick]
        for i in range(2,10):
            self.nicks.append(self.nicks[0] + str(i))
        self.nicki = 0
        self.usrs = []
        self.on_chat = self._default_callback
        self.on_set = self._default_callback
        self.on_add = self._default_callback
        self.on_remove = self._default_callback
        self.on_warn = self._default_callback
        self.url = "wss://hack.chat/chat-ws"
        self.ws = websocket.WebSocket()
        self.thread = threading.Thread(target=self.recv_thread)
        self.thread.daemon = 1
        self.online = 0
        self.time = time()

    def run(self):
        self.thread.start()

    def stop(self):
        self.ws.close()
        exit(0)

    def get_usrs(self):
        self.on_set(self.usrs)

    def get_nick(self):
        return self.nicks[self.nicki]

    def send_message(self, msg):
        """Sends a message on the channel."""
        if self.ws.connected and self.online:
            self._send_packet({"cmd": "chat", "text": msg})


    def _default_callback(self, *args):
        print(*args)

    def _ensure_connection(self):
        """ Ensure connection is success. """
        if not self.ws.connected:
            self.online = 0
            try:
                # Connect
                self.on_warn("Connecting to Server...")
                self.ws.connect(self.url)
            except Exception as e:
                print("[Error] Can't connect to the server! ")
                exit(0)
            # Use the origin nick
            self.nicki = 0
            while True:
                try:
                    # Login
                    self.on_warn("Try to login as "+self.get_nick())
                    self._send_packet({"cmd": "join", "channel": self.channel, "nick": self.get_nick()})
                    res = json.loads(self.ws.recv())
                    sleep(1)
                    if not res:
                        continue
                    if res["cmd"] == "warn" and "taken" in res["text"]:
                        # Nick is taken
                        self.nicki += 1
                        continue
                    elif res["cmd"] == "warn" and "blocked" in res["text"]:
                        # Try too fast
                        self.on_warn("Try too frequently, wait for 10 sec. ")
                        sleep(10)
                        continue
                    elif res["cmd"] == "onlineSet":
                        # Login success
                        self.online = 1
                        self.on_warn("Successfully login! ")
                        self.usrs = res["nicks"]
                        self.on_set(res["nicks"])
                        break
                except Exception as e:
                    print("[Error] Can't login to the server! ")
                    exit(0)
                

    def _send_ping(self):
        self._ensure_connection()
        if (time() - self.time) > 60:
            self.time = time()
            try:
                self._send_packet({"cmd": "ping"})
            except Exception as e:
                self._ensure_connection()

    def _send_packet(self, packet):
        """Sends <packet> (<dict>) to https://hack.chat."""
        encoded = json.dumps(packet)
        self.ws.send(encoded)

    def recv_thread(self):
        while True:
            self._send_ping()
            try:
                res = json.loads(self.ws.recv())
                # print(res)
                if not res["cmd"]:
                    continue
                if res["cmd"] == "chat":
                    self.on_chat(res["nick"], res["text"])
                    if 'kick' in res["text"] and self.get_nick() in res["text"]:
                        self.send_message("WTF")
                        self.stop()
                elif res["cmd"] == "onlineAdd":
                    self.usrs.append(res["nick"])
                    self.on_add(res["nick"])
                elif res["cmd"] == "onlineRemove":
                    self.usrs.remove(res["nick"])
                    self.on_remove(res["nick"])
                elif res["cmd"] == "warn":
                    if "blocked" in res["text"]:
                        self.on_warn("Send too fast, wait for 10 sec.")
                        self.online = 0
                        sleep(10)
                        self.online = 1
                        self.on_warn("Try again now.")
                    else:
                        self.on_warn(res["text"])
            except Exception as e:
                pass
            sleep(500/1000)