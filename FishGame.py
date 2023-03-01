import time
import pickle
import os
import json


TUI_N = "."
TUI_O = "O"
TUI_X = "X"
GMR_N = 0
GMR_O = 1
GMR_X = 2
KDA_W = "win"
KDA_D = "draw"
KDA_L = "lose"
KDA_T = "total"

ERR_NO_ERROR             = 0
ERR_OUT_OF_INDEX         = "Position out of index"
ERR_WRONG_GMR            = "It's not your turn"
ERR_CONFLIC_INDEX        = "Position conflict"
ERR_WRONG_TURN           = "It's not your turn"
ERR_INVALID_ARG          = "Unknown command"
ERR_NO_FISHGAME          = "No game"
ERR_NOT_END              = "Game not end"
ERR_ECHO_REMINDER        = "Sent reminder"
ERR_ECHO_END             = "End the game"
ERR_GAME_FINISHED        = "Game Finished"

HELP = """FishGame manual:
fg                  查看当前棋盘
fg ?                再次发送当前棋盘给对手，以防对手没看见/没收到
fg new W H S        新建一个W宽，H高的棋盘，连续S子胜利
                    缺省值为 9 9 5
fg X Y              在第X列，第Y行落子
fg end              终止本轮对局
fg kda              查看并向对方发送自己的战绩"""

FP_FG_DIR = "FishGame"
FP_FG_KDA = f"{FP_FG_DIR}/kda.json"
FP_FGH_AUTOSAVE = f"{FP_FG_DIR}/fgh_autosave.pkl"

class FishGame:
    def __init__(self, w:int=9, h:int=9, s:int=5, id:str=None):
        t = time.localtime()
        self.id = id if id != None else f"{t.tm_mon:0>2}{t.tm_mday:0>2}{t.tm_hour:0>2}{t.tm_min:0>2}"
        self.table_w = w
        self.table_h = h
        self.table_s = s if min(w, h) > s else min(w, h)
        self.battles = [ [ 0 for i in range(self.table_w) ] for j in range(self.table_h) ]
        self.turn_gmr = GMR_N
        self.step = 0
        self.gmr = GMR_N
        self.last_ij = [-1, -1]
        self.winner = GMR_N
        # print(f"ID: {self.id} | {self.table_w}x{self.table_h} | {self.table_s} to win")

    def render(self) -> str:
        table = ""

        for j in range(self.table_h + 1):
            for i in range(self.table_w + 1):
                if i == 0 and j == 0:
                    table += "   "
                    continue
                elif i == 0:
                    table += f"{j:>2} "
                    continue
                elif j == 0:
                    table += f"{i%10} "
                    continue

                if self.battles[i-1][j-1] == GMR_O:
                    table += TUI_O
                elif self.battles[i-1][j-1] == GMR_X:
                    table += TUI_X
                else:
                    table += TUI_N
                if i == self.last_ij[0] and j-1 == self.last_ij[1]:
                    table += "("
                elif i-1 == self.last_ij[0] and j-1 == self.last_ij[1]:
                    table += ")"
                else:
                    table += " "

            if j == self.table_h - 1:
                table += f" You're {TUI_O if self.gmr == GMR_O else TUI_X}"
            if j != self.table_h:
                table += "\n"

        if self.winner == GMR_N:
            if self.turn_gmr == self.gmr:
                table += " Waiting..."
            else:
                table += " Your turn"
        else:
            table += " Game Finished!\n"
            if self.winner == self.gmr:
                table += " You Win! "
            else:
                table += " You lose."
        return table

    def run(self, i, j, gmr=GMR_N):
        i -= 1
        j -= 1
        if gmr == GMR_N:
            gmr = GMR_O if self.turn_gmr == GMR_X else GMR_X

        if self.winner != GMR_N:
            return ERR_GAME_FINISHED
        if self.turn_gmr != GMR_N and self.turn_gmr == gmr:
            return ERR_WRONG_TURN
        if i >= self.table_w or j >= self.table_h:
            return ERR_OUT_OF_INDEX
        if self.battles[i][j] != GMR_N:
            return ERR_CONFLIC_INDEX

        self.battles[i][j] = gmr
        self.turn_gmr = gmr
        self.last_ij[0] = i
        self.last_ij[1] = j

        self.win_check()
        return ERR_NO_ERROR

    def win_check(self):
        for way_i, way_j in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            checked = 0
            for idx in range(-1*(self.table_s - 1), self.table_s):
                check_i = self.last_ij[0] + (way_i * idx)
                check_j = self.last_ij[1] + (way_j * idx)
                if check_i < 0 or check_i >= self.table_w:
                    checked = 0
                    continue
                if check_j < 0 or check_j >= self.table_h:
                    checked = 0
                    continue

                if self.battles[check_i][check_j] != self.turn_gmr:
                    checked = 0
                    continue
                else:
                    checked += 1
                if checked >= self.table_s:
                    self.winner = self.turn_gmr
                    record_kda(KDA_W if self.winner == self.gmr else KDA_L)
                    return True
        return False


class FishGameHandler:
    def __init__(self) -> None:
        self.fg = None
        self.last_time = 0
        self.last_arg = ""

    def test(self, arg):
        ret = self.parse(arg)
        print(ret[0])
        print(ret[1])

    def isfishgame(self, arg:str):
        if arg.startswith("\\fg ") or arg.startswith("fg ") or arg == "fg":
            return True
        return False

    def parse(self, arg:str):
        args = arg.split()
        if arg.startswith("\\fg "):
            t = int(args[1])
            if t < self.last_time: # reply fail
                return "", self.last_arg # cannot usr fmt_ret
            elif t == self.last_time: # not reply yet
                return self.fmt_ret(self.fg.render())
            else:
                self.last_time = t
                return self.run(" ".join(args[2:]), False)
        elif arg.startswith("fg "):
            return self.run(" ".join(args[1:]))
        elif arg == "fg":
            if not self.fg:
                return self.fmt_ret(ERR_NO_FISHGAME)
            return self.fmt_ret(self.fg.render())
        else:
            return self.fmt_ret(ERR_INVALID_ARG)

    def run(self, arg:str, host=True):
        args = arg.split()
        if len(args) == 0: # no arg
            return self.fmt_ret(ERR_INVALID_ARG) # no arg

        if args[0] in ["?", "？"]:
            if not self.fg:
                return self.fmt_ret(ERR_NO_FISHGAME)
            return ERR_ECHO_REMINDER, self.last_arg # cannot usr fmt_ret

        elif args[0] in ["end"]:
            self.fg = None
            record_kda(KDA_D)
            return self.fmt_ret(ERR_ECHO_END, args[0] if host else "")

        elif args[0] in ["kda"]:
            return "", print_kda() # do not use fmt_ret

        elif args[0] in ["help"]:
            return self.fmt_ret(HELP)

        elif len(args) == 2 and args[0].isdecimal() and args[1].isdecimal():
            if not self.fg:
                return self.fmt_ret(ERR_NO_FISHGAME)
            gmr = self.fg.gmr if host else (GMR_X if self.fg.gmr == GMR_O else GMR_O)
            ret = self.fg.run(int(args[0]), int(args[1]), gmr)
            if ret == ERR_NO_ERROR:
                return self.fmt_ret(self.fg.render(), arg if host else "")
            else:
                return self.fmt_ret(ret)

        elif self.param_check(args, ["new"], [1, 1, 1, 0], 0, 4):
            if host and self.fg != None and self.fg.winner == GMR_N:
                return self.fmt_ret(ERR_NOT_END)
            self.fg = FishGame(*args)
            self.fg.gmr = GMR_X if host else GMR_O
            self.fg.turn_gmr = GMR_X
            sendbuf = f"new {self.fg.table_w} {self.fg.table_h} {self.fg.table_s} {self.fg.id}"
            return self.fmt_ret(self.fg.render(), sendbuf if host else "")

        else:
            return self.fmt_ret(ERR_INVALID_ARG)

    def fmt_ret(self, printbuf, sendbuf = ""):
        if sendbuf != "":
            self.last_time = time.time()
            self.last_arg = f"\\fg {round(self.last_time)} {sendbuf}"
        self.autosave()
        return str(printbuf), self.last_arg if sendbuf != "" else sendbuf

    def param_check(self, args:list, fns:list, decimals:list, min_p:int, max_p:int):
        if args[0] not in fns:
            return False
        args.pop(0)
        if len(args) < min_p or len(args) > max_p:
            return False
        for i in range(len(args)):
            if not decimals[i]:
                continue
            if not args[i].isdecimal():
                return False
            else:
                args[i] = int(args[i])
        return True

    def autosave(self):
        pickle.dump(self, open(FP_FGH_AUTOSAVE, "wb"))

    def del_autosave(self):
        if os.path.exists(FP_FGH_AUTOSAVE):
            os.remove(FP_FGH_AUTOSAVE)

    def save(self):
        pass

    def load(self):
        pass


def record_kda(result: str):
    kda = {
        KDA_W: 0,
        KDA_D: 0,
        KDA_L: 0,
        KDA_T: 0,
    }
    if os.path.exists(FP_FG_KDA):
        with open(FP_FG_KDA, "r", encoding="utf-8") as f:
            kda = json.load(f)

    kda[result] += 1
    kda[KDA_T] += 1

    with open(FP_FG_KDA, "w", encoding="utf-8") as f:
        json.dump(kda, f, ensure_ascii=False, indent=2)


def print_kda():
    if os.path.exists(FP_FG_KDA):
        with open(FP_FG_KDA, "r", encoding="utf-8") as f:
            kda = json.load(f)
        return f"win ratio: {100*kda[KDA_W]/kda[KDA_T]:.2f} {kda[KDA_W]}/{kda[KDA_D]}/{kda[KDA_L]}"
    else:
        return "no kda records"


def init():
    if os.path.exists(FP_FGH_AUTOSAVE):
        return pickle.load(open(FP_FGH_AUTOSAVE, "rb"))
    else:
        if not os.path.exists(FP_FG_DIR):
            os.mkdir(FP_FG_DIR)
        return FishGameHandler()
