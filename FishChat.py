import argparse
import threading
from time import localtime, sleep, strftime, time

from plyer import notification
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout

from HChat import HChat

notify_flag = 1

# Parse argument
parser = argparse.ArgumentParser()
parser.add_argument("-c", required=True, help="channel")
parser.add_argument("-n", required=True, help="nickname")
args = parser.parse_args()

# HChat
hchat = HChat(args.c, args.n)

# Prompt_toolkit
input_buffer = Buffer()
print_buffer = Buffer()

input_window = Window(BufferControl(buffer=input_buffer), height=1)
print_window = Window(BufferControl(buffer=print_buffer))

root = HSplit([
    print_window,
    Window(height=1, char="-", style="class:line"),
    input_window,
])

kb = KeyBindings()

# Ctrl+D: change focus between input window and print window
@kb.add("c-d", eager=True)
def _(e):
    global notify_flag
    notify_flag = 1
    application.layout.focus_next()

# Press Q in print window will quit the program
@kb.add("q", eager=True, filter=has_focus(print_buffer))
def _(e):
    global notify_flag
    notify_flag = 0
    e.app.exit()

# Press U in print window will get online users
@kb.add("u", eager=True, filter=has_focus(print_buffer))
def _(e):
    hchat.get_usrs()


# Input control
def input_buffer_changed(_):
    if input_buffer.cursor_position == 0:
        return
    global notify_flag
    notify_flag = 1
    if input_buffer.text[input_buffer.cursor_position-1] == '\n':
        hchat.send_message(input_buffer.text[0:-1])
        input_buffer.text = ''
input_buffer.on_text_changed += input_buffer_changed

# Print on print_buffer
def printf(usr, msg):
    t = strftime("%H:%M", localtime())
    print_buffer.text += "\n{:s}|{:>3s}: {:s}".format(t, usr, msg)
    print_buffer.cursor_position = len(print_buffer.text)

def on_chat(usr, msg):
    t = strftime("%H:%M", localtime())
    d = strftime("%Y%m%d", localtime())
    try:
        with open("%s-%s.csv"%(args.c, d), "a") as f:
            f.write("%s,%s,%s\n"%(t, usr, msg))
    except Exception as e:
        pass
    if usr != hchat.get_nick():
        global notify_flag
        notify_flag = time()
    printf(usr, msg)
hchat.on_chat = on_chat

def on_set(usrs):
    printf("#", "Online: "+", ".join(usrs))
hchat.on_set = on_set

def on_add(usr):
    printf("#", usr+" joined.")
hchat.on_add = on_add

def on_remove(usr):
    printf("#", usr+" left.")
hchat.on_remove = on_remove

def on_warn(msg):
    printf("#", msg)
hchat.on_warn = on_warn

application = Application(
    layout=Layout(root, focused_element=input_window),
    key_bindings=kb,
    full_screen=True,
)

# Notify if not reply after receive msg 10s
def thread_notify():
    global notify_flag
    while notify_flag:
        if notify_flag != 1 and (time() - notify_flag) > 10:
            notification.notify(message='New update! ', toast=True)
            notify_flag = 1
        sleep(0.5)
thread = threading.Thread(target=thread_notify)
thread.daemon = 1

thread.start()
hchat.run()
application.run()

