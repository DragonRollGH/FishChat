import json
import threading
from time import sleep

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
        self.running = 1

    def run(self):
        self.thread.start()

    def stop(self):
        self.running = 0
        self.ws.close()
        print("delete")

    def get_usrs(self):
        self.on_set(self.usrs)

    def get_nick(self):
        return self.nicks[self.nicki]

    def send_message(self, msg):
        """Sends a message on the channel."""
        if self.ws.connected:
            self._send_packet({"cmd": "chat", "text": msg})

    def _default_callback(self, *args):
        print(*args)

    def _ensure_connection(self):
        """ Ensure connection is success. """
        if not self.ws.connected and self.running:
            try:
                # Connect
                self.ws.connect(self.url)
            except Exception as e:
                print("[Error] Can't connect to the server! ")
                exit(0)
            # Use the origin nick
            self.nicki = 0
            while True:
                try:
                    # Login
                    self._send_packet({"cmd": "join", "channel": self.channel, "nick": self.nicks[self.nicki]})
                    res = json.loads(self.ws.recv())
                    if not res:
                        continue
                    if res["cmd"] == "warn" and "taken" in res["text"]:
                        # Nick is taken
                        self.nicki += 1
                        continue
                    elif res["cmd"] == "warn" and "blocked" in res["text"]:
                        # Already login or send too fast
                        sleep(5)
                        break
                    elif res["cmd"] == "onlineSet":
                        # Login success
                        self.usrs = res["nicks"]
                        self.on_set(res["nicks"])

                        break
                except Exception as e:
                    print("[Error] Can't login to the server! ")
                    exit(0)

    def _send_ping(self):
        self._ensure_connection()
        try:
            self._send_packet({"cmd": "ping"})
        except Exception as e:
            self._ensure_connection()

    def _send_packet(self, packet):
        """Sends <packet> (<dict>) to https://hack.chat."""
        encoded = json.dumps(packet)
        self.ws.send(encoded)

    def recv_thread(self):
        while self.running:
            self._send_ping()
            try:
                res = json.loads(self.ws.recv())
                # print(res)
                if not res["cmd"]:
                    continue
                if res["cmd"] == "chat":
                    self.on_chat(res["nick"], res["text"])
                    if 'die' in res["text"]:
                        self.send_message("WTF")
                        self.ws.close()
                        pass
                elif res["cmd"] == "onlineAdd":
                    self.usrs.append(res["nick"])
                    self.on_add(res["nick"])
                elif res["cmd"] == "onlineRemove":
                    self.usrs.remove(res["nick"])
                    self.on_remove(res["nick"])
                elif res["cmd"] == "warn":
                    self.on_warn(res["text"])
                    if "blocked" in res["text"]:
                        sleep(5)
            except Exception as e:
                pass
            sleep(500/1000)
