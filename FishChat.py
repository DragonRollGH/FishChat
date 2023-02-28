import argparse
import threading
from time import localtime, sleep, strftime, time
import sys
import os

# from plyer import notification
from notifypy import Notify
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout

from HChat import HChat
import FishGame

logl = 1

def logl_set(l):
    global logl
    logl = l

def logl_get():
    global logl
    return logl

notifyer = Notify()
notifyer.application_name = "Windows 通知中心"
notifyer.title = "New Update"
notifyer.message = ""
notifyer.icon = ""

notify_flag = 1
notify_amnt = 0

def notify_set(tmo):
    global notify_flag, notify_amnt
    notify_flag = tmo
    notify_amnt = 0

def notify_clr():
    global notify_flag, notify_amnt
    notify_flag = 1
    notify_amnt = 0

def notify(message = "New Update"):
    notifyer.title = message
    notifyer.send(block = False)

# Parse argument
parser = argparse.ArgumentParser()
parser.add_argument("-c", help="channel", default="dragonroll")
parser.add_argument("-n", help="nickname", default="default")
args = parser.parse_args()


# HChat
hchat = HChat(args.c, args.n)
FP_RECORDS_DIR = f"records_{args.c}"
if not os.path.exists(FP_RECORDS_DIR):
    os.mkdir(FP_RECORDS_DIR)

# FishGame
fgh = FishGame.init()

# Prompt_toolkit
input_buffer = Buffer()
print_buffer = Buffer()

input_window = Window(BufferControl(buffer=input_buffer), height=1, wrap_lines=True)
print_window = Window(BufferControl(buffer=print_buffer), wrap_lines=True)

root = HSplit([
    print_window,
    Window(height=1, char="-", style="class:line"),
    input_window,
])

# Print on print_buffer
def printf(usr, msg):
    t = strftime("%H:%M", localtime())
    title = "\n{:s}|{:>3s}: ".format(t, usr)
    if '\n' in msg:
        msg = msg.replace('\n', '\n'.ljust(len(title)))
    print_buffer.text += title + msg
    print_buffer.cursor_position = len(print_buffer.text)

kb = KeyBindings()

# Ctrl+D: change focus between input window and print window
@kb.add("c-d", eager=True)
def _(e):
    notify_clr()
    application.layout.focus_next()

# Press Q in print window will quit the program
@kb.add("q", eager=True, filter=has_focus(print_buffer))
@kb.add("Q", eager=True, filter=has_focus(print_buffer))
def _(e):
    notify_set(0)
    e.app.exit()

# Press U in print window will get online users
@kb.add("u", eager=True, filter=has_focus(print_buffer))
@kb.add("U", eager=True, filter=has_focus(print_buffer))
def _(e):
    hchat.get_usrs()

# Press R in print window will reconnect
@kb.add("r", eager=True, filter=has_focus(print_buffer))
@kb.add("R", eager=True, filter=has_focus(print_buffer))
def _(e):
    hchat.offline()

# Press TAB in print window will quote
@kb.add("c-i", eager=True, filter=has_focus(print_buffer))
def _(e):
    idx = print_buffer.cursor_position
    msg = print_buffer.text
    if len(input_buffer.text) != 0:
        input_buffer.text += '\n'
    input_buffer.text += msg.split('\n')[msg[:idx].count('\n')]
    input_buffer.cursor_position = len(msg)

# Press shift+↑ in input window will scroll up print window
@kb.add("s-up", eager=True, filter=has_focus(input_buffer))
def _(e):
    print_window._scroll_up()

# Press shift+↓ in input window will scroll down print window
@kb.add("s-down", eager=True, filter=has_focus(input_buffer))
def _(e):
    print_window._scroll_down()

# Press TAB in input window will \n
@kb.add("c-i", eager=True, filter=has_focus(input_buffer))
def _(e):
    idx = input_buffer.cursor_position
    msg = input_buffer.text
    msg = msg[:idx] + '\n' + msg[idx:]
    input_buffer.text = msg
    input_buffer.cursor_position = len(msg)

# Press Enter in input window will send message
@kb.add("c-m", eager=True, filter=has_focus(input_buffer))
def _(e):
    idx = input_buffer.cursor_position
    msg = input_buffer.text

    # null text
    if len(input_buffer.text) == 0:
        return
    notify_clr()

    # FishGame Command
    try:
        if fgh.isfishgame(msg):
            printbuf, sendbuf = fgh.parse(msg)
            if printbuf != "":
                printf("FG#", printbuf)
            if sendbuf != "":
                hchat.send_message(sendbuf)
            input_buffer.text = ''
            return
    except Exception as e:
        printf("FG#", "[ERROR] "+str(e))

    # normal msg
    hchat.send_message(msg)
    input_buffer.text = ''

def on_chat(usr, msg):
    t = strftime("%H:%M", localtime())
    d = strftime("%Y%m%d", localtime())

    # record
    try:
        with open(f"{FP_RECORDS_DIR}/{args.c}-{d}.csv", "a") as f:
            f.write("%s,%s,%s\n"%(t, usr, msg))
    except Exception as e:
        pass

    # FishGame Socket
    try:
        if fgh.isfishgame(msg):
            if usr != hchat.get_nick():
                printbuf, sendbuf = fgh.parse(msg)
                if printbuf != "":
                    printf("FG#", printbuf)
                if sendbuf != "":
                    hchat.send_message(sendbuf)
                notify_set(time()+10)
            return
    except Exception as e:
        printf("FG#", "[ERROR] "+str(e))

    # normal msg
    printf(usr, msg)
    if usr != hchat.get_nick():
        notify_set(time()+10)

    # FishCommand
    try:
        cmds = msg.split(' ')
        if cmds and len(cmds) > 2 and cmds[0] == hchat.get_nick():
            if 'logl' == cmds[1]:
                logl_set(int(cmds[2]))
                printf("#", "done")
            elif 'offline_threshold' == cmds[1]:
                hchat.offline_threshold = int(cmds[2])
                printf("#", "done")
            elif 'ping_interval' == cmds[1]:
                hchat.ping_interval = int(cmds[2])
                printf("#", "done")
            elif 'ping_divider' == cmds[1]:
                hchat.ping_divider = int(cmds[2])
                printf("#", "done")
    except:
        pass
hchat.on_chat = on_chat

def on_set(usrs):
    notify_set(100)
    printf("#", "Online: "+", ".join(usrs))
    if root.children[1].char == 'X':
        root.children[1].char = '-'
hchat.on_set = on_set

def on_add(usr):
    if hchat.get_nick() != usr:
        printf("#", usr+" joined.")
hchat.on_add = on_add

def on_remove(usr):
    printf("#", usr+" left.")
    pass
hchat.on_remove = on_remove

def on_debug(msg):
    if logl_get() >= 4:
        printf("#", msg)
hchat.on_debug = on_debug

def on_info(msg):
    if logl_get() >= 3:
        printf("#", msg)
    if ("You are alone." == msg):
        root.children[1].char = 'I'
    if ("You are group." == msg):
        root.children[1].char = '-'
        notify_set(101)
    if "Connecting to Server..." == msg:
        root.children[1].char = 'X'
    pass
hchat.on_info = on_info

def on_warn(msg):
    if logl_get() >= 2:
        printf("#", msg)
hchat.on_warn = on_warn

def on_error(msg):
    if logl_get() >= 1:
        printf("#", msg)
hchat.on_error = on_error

def on_critical(msg):
    printf("#", msg)
    # sleep(3)
    application.exit()
hchat.on_critical = on_critical

application = Application(
    layout=Layout(root, focused_element=input_window),
    key_bindings=kb,
    full_screen=True,
)

# Notify if not reply after receive msg 10s
def thread_notify():
    global notify_flag, notify_amnt
    while notify_flag:
        if notify_flag > 1000 and (time() - notify_flag) > 0:
            if os.path.exists("RunAs.bat"):
                notify(message=f'New update')
                notify_clr()
            else:
                notify(message=f'New update: v8.16.{notify_amnt}')
                notify_flag = time() + 20 + 5 * notify_amnt
                notify_amnt += 1
                if notify_amnt > 10:
                    notify_clr()
        elif notify_flag == 100:
            # notify(message='Success')
            notify_clr()
        elif notify_flag == 101:
            notify(message='Success')
            notify_clr()
        sleep(0.5)

if 'win32' == sys.platform:
    thread = threading.Thread(target=thread_notify, daemon=1)
    thread.start()

hchat.run()
application.run()
