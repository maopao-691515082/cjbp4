#qpy:kivy

import sys
import os
import random
import time
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.graphics import Color, Rectangle

def _assert(e):
    if not e:
        raise Exception("Bug")

class ScorePad(Label):
    def refresh(self):
        self.text = "%d\n%d" % (game.player_n.score + game.player_s.score, game.player_e.score + game.player_w.score)

class OkButton(Button):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if game.turn.end():
                _assert(len(set([len(player.pk_list) for player in game.player_list])) == 1)
                if len(game.player_s.pk_list) == 0:
                    game.start_game()
                else:
                    game.start_turn()
                return True
            if game.is_my_turn():
                game.on_my_turn_play()
                return True

poker_width = None
poker_height = None

class Poker(Image):

    def __init__(self, idx, name, **kwarg):
        Image.__init__(self, **kwarg)
        self.size = poker_width, poker_height
        self.allow_stretch = True
        self.keep_ratio = False

        self.idx = idx
        self.type = -1 if idx < 48 else (idx - 48) / 20
        self.name = name
        self.selected = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not game.turn.end() and game.is_my_turn() and game.in_my_pk_list(self):
            if self.selected:
                self.deselect()
            else:
                self.select()
            return True

    def select(self):
        _assert(not self.selected)
        x, y = self.pos
        game.on_pk_selected(self)
        self.pos = x, y + 20
        self.selected = True

    def deselect(self):
        _assert(self.selected)
        x, y = self.pos
        self.pos = x, y - 20
        self.selected = False

class Player:
    def __init__(self, name):
        if name == "n":
            self.played_pk_list_pos = game.width / 2 - poker_width * 3 / 4, game.height - 20 - poker_height
        elif name == "s":
            self.played_pk_list_pos = game.width / 2 - poker_width * 3 / 4, 20 + poker_height + 30
        elif name == "w":
            self.played_pk_list_pos = 20, 20 + poker_height + 10 + (game.height - 20 - poker_height - 10) / 2 - poker_height / 2
        else:
            _assert(name == "e")
            self.played_pk_list_pos = (game.width - 20 - poker_width * 3 / 2,
                                       20 + poker_height + 10 + (game.height - 20 - poker_height - 10) / 2 - poker_height / 2)
        self.score = 0
        self.next = None
        self.buddy = None
        self.pk_list = []

    def show_played_pk_list(self, pk_list):
        _assert(len(pk_list) in (1, 2))
        game.thinking_pad.pos = game.width, game.height
        x, y = self.played_pk_list_pos
        for i, pk in enumerate(pk_list):
            pk.pos = x + i * poker_width / 2, y
        new_pk_list = []
        for pk in self.pk_list:
            for pk_to_del in pk_list:
                if pk is pk_to_del:
                    break
            else:
                new_pk_list.append(pk)
        _assert(len(new_pk_list) + len(pk_list) == len(self.pk_list))
        self.pk_list[:] = new_pk_list

    def show_thinking_pad(self):
        game.thinking_pad.pos = self.played_pk_list_pos

def get_possible_play(base_type, num, pk_list):
    if base_type is None:
        _assert(num is None)
        possible_play = [(pk,) for pk in pk_list]
        for i in xrange(1, len(pk_list)):
            a = pk_list[i - 1]
            b = pk_list[i]
            _assert(a.idx < b.idx)
            if a.name == b.name:
                possible_play.append((a, b))
        return possible_play

    _assert(len(pk_list) >= num)
    base_type_pk_list = [pk for pk in pk_list if pk.type == base_type]

    if num == 1:
        if base_type_pk_list:
            return [(pk,) for pk in base_type_pk_list]
        return [(pk,) for pk in pk_list]

    _assert(num == 2)
    possible_play = []

    if len(base_type_pk_list) > 1:
        if base_type == -1:
            for i in xrange(1, len(base_type_pk_list)):
                a = base_type_pk_list[i - 1]
                b = base_type_pk_list[i]
                _assert(a.idx < b.idx)
                if a.name == b.name:
                    possible_play.append((a, b))
            if possible_play:
                return possible_play
            if base_type_pk_list[1].idx < 28:
                return [(base_type_pk_list[0], base_type_pk_list[1])]
            if base_type_pk_list[0].idx < 28:
                for pk in base_type_pk_list[1 :]:
                    possible_play.append((base_type_pk_list[0], pk))
                return possible_play
        for i in xrange(len(base_type_pk_list)):
            for j in xrange(i + 1, len(base_type_pk_list)):
                possible_play.append((base_type_pk_list[i], base_type_pk_list[j]))
        return possible_play

    if len(base_type_pk_list) == 1:
        base_type_pk = base_type_pk_list[0]
        for pk in pk_list:
            if pk is base_type_pk:
                continue
            if pk.idx < base_type_pk.idx:
                possible_play.append((pk, base_type_pk))
            else:
                possible_play.append((base_type_pk, pk))
        return possible_play

    for i in xrange(len(pk_list)):
        for j in xrange(i + 1, len(pk_list)):
            possible_play.append((pk_list[i], pk_list[j]))
    return possible_play

class Turn:
    def __init__(self, start_player, is_simulation = False):
        self.start_player = start_player
        self.l = []
        self.is_simulation = is_simulation

    def __del__(self):
        _assert(self.end())
        if not self.is_simulation:
            for pk_list in self.l:
                for pk in pk_list:
                    pk.pos = game.width, game.height

    def end(self):
        _assert(len(self.l) <= 4)
        return len(self.l) == 4

    def get_base_type_num(self):
        if not self.l:
            return None, None
        base = self.l[0]
        _assert(len(base) in (1, 2))
        if len(base) == 2:
            a, b = base
            _assert(a.name == b.name and a.type == b.type)
        else:
            a, = base
        return a.type, len(base)

    def add(self, pk_list, curr_player = None):
        if curr_player is None:
            curr_player = game.curr_player
        _assert(len(self.l) < 4)
        base_type, num = self.get_base_type_num()
        possible_play = get_possible_play(base_type, num, curr_player.pk_list)
        _assert(possible_play)
        for possible_pk_list in possible_play:
            if len(pk_list) == len(possible_pk_list) == 1 and pk_list[0] is possible_pk_list[0]:
                self.l.append(pk_list)
                return True
            if len(pk_list) == len(possible_pk_list) == 2:
                a, b = pk_list
                c, d = possible_pk_list
                _assert(a.idx < b.idx and c.idx < d.idx)
                if a is c and b is d:
                    self.l.append(pk_list)
                    return True

    def get_winner(self):
        _assert(self.end())
        base_type, num = self.get_base_type_num()
        _assert(base_type is not None and num is not None)

        win_idx = 0
        if num == 1:
            win_pk, = self.l[0]
            for i in xrange(1, len(self.l)):
                pk, = self.l[i]
                if pk.type == win_pk.type:
                    if pk.idx < win_pk.idx and pk.name != win_pk.name:
                        if pk.name[1] == win_pk.name[1] and pk.name[1] in "235" and pk.name[0] != "s" and win_pk.name[0] != "s":
                            _assert(win_pk.name[1] in "235")
                            _assert(pk.name[0] in "hcd" and win_pk.name[0] in "hcd")
                        else:
                            win_idx = i
                            win_pk = pk
                else:
                    if pk.type == -1:
                        win_idx = i
                        win_pk = pk
        else:
            _assert(num == 2)
            win_a, win_b = self.l[0]
            _assert(win_a.name == win_b.name and win_a.type == win_b.type)
            for i in xrange(1, len(self.l)):
                a, b = self.l[i]
                if a.name == b.name:
                    _assert(a.type == b.type)
                    if a.type == win_a.type:
                        if a.idx < win_a.idx:
                            _assert(a.name != win_a.name)
                            if a.name[1] == win_a.name[1] and a.name[1] in "235" and a.name[0] != "s" and win_a.name[0] != "s":
                                _assert(win_a.name[1] in "235")
                                _assert(a.name[0] in "hcd" and win_a.name[0] in "hcd")
                            else:
                                win_idx = i
                                win_a, win_b = a, b
                    else:
                        if a.type == -1:
                            win_idx = i
                            win_a, win_b = a, b

        winner = self.start_player
        for i in xrange(win_idx):
            winner = winner.next
        return winner

    def get_score(self):
        _assert(self.end())
        base_type, num = self.get_base_type_num()
        _assert(base_type is not None and num is not None)

        score = 0
        for pk_list in self.l:
            for pk in pk_list:
                _assert(len(pk.name) == 2)
                score += {"5" : 5, "t" : 10, "k" : 10}.get(pk.name[1], 0)
        if not self.is_simulation:
            _assert(len(set([len(player.pk_list) for player in game.player_list])) == 1)
            if len(game.player_s.pk_list) == 0:
                score *= num * 2
        return score

    def finish(self):
        _assert(not self.is_simulation)
        _assert(self.end())

        winner = self.get_winner()
        score = self.get_score()

        winner.score += score
        return winner

    def copy(self):
        turn = Turn(self.start_player, True)
        turn.l = self.l[:]
        return turn

    def get_player_idx(self, player):
        p = self.start_player
        for i in xrange(4):
            if p is player:
                return i
            p = p.next
        else:
            _assert(False)

def evaluate(turn, curr_player, my_play):
    base_type, num = turn.get_base_type_num()
    winner = turn.get_winner()
    me_win = winner is curr_player
    team_win = me_win or winner is curr_player.buddy
    score = turn.get_score()
    if base_type == -1:
        score -= 3
    if not team_win:
        score = -score
    _assert(len(my_play) in (1, 2) and len(my_play) == num)
    if len(my_play) == 1 or my_play[0].name != my_play[1].name:
        for play_pk in my_play:
            count = 0
            for pk in curr_player.pk_list:
                if play_pk.name == pk.name:
                    count += 1
            if count > 1:
                score -= 5
    is_pair = len(my_play) == 2 and my_play[0].name != my_play[1].name
    master_pair = is_pair and base_type == -1
    lose_pair = is_pair and (not team_win or (not me_win and turn.get_player_idx(curr_player) > 1))
    value = 0
    for pk in my_play:
        if pk.type != -1:
            value += (pk.idx - 48) % 20 + 48
        else:
            value += pk.idx
    return score, 0 if lose_pair else 1, 0 if master_pair else 1, 1 if is_pair else 0, value, 1 if team_win else 0, random.random() 

def simulate_turn(turn):
    if turn.end():
        return
    turn_progress = len(turn.l)
    curr_player = turn.start_player
    for i in xrange(turn_progress):
        curr_player = curr_player.next
    base_type, num = turn.get_base_type_num()
    possible_play = get_possible_play(base_type, num, curr_player.pk_list)
    _assert(possible_play)
    random.shuffle(possible_play)
    best_evaluation = None
    best_pk_list = None
    for pk_list in possible_play:
        _assert(turn.add(pk_list, curr_player))
        simulate_turn(turn)
        evaluation = evaluate(turn, curr_player, pk_list)
        if best_evaluation is None or best_evaluation < evaluation:
            best_evaluation = evaluation
            best_pk_list = pk_list
        turn.l[:] = turn.l[: turn_progress]
        if time.time() - ai_start_time > 10:
            break
    _assert(best_evaluation is not None and best_pk_list is not None)
    _assert(turn.add(best_pk_list, curr_player))
    simulate_turn(turn)

ai_start_time = None
def ai_choice():
    global ai_start_time
    ai_start_time = time.time()
    turn = game.turn.copy()
    simulate_turn(turn)
    return turn.l[len(game.turn.l)]

class Cjbp4Game(Widget):
    def init(self):
        global poker_width, poker_height
        poker_width = game.width / 10
        poker_height = game.width / 7

        with self.canvas:
            Color(rgb = [0.0, 0.3, 0.0])
            Rectangle(size = self.size)

        score_pad_hint = Label(text = "NS\nEW")
        score_pad_hint.size = self.width / 16, self.height / 7
        score_pad_hint.bold = True
        score_pad_hint.font_size = 30
        score_pad_hint.color = [1, 1, 1, 1]
        score_pad_hint.pos = 0, self.height - score_pad_hint.height
        self.add_widget(score_pad_hint)

        self.score_pad = ScorePad()
        self.score_pad.size = score_pad_hint.size
        self.score_pad.bold = True
        self.score_pad.font_size = 30
        self.score_pad.color = score_pad_hint.color
        self.score_pad.pos = score_pad_hint.pos[0] + score_pad_hint.width, score_pad_hint.pos[1]
        self.add_widget(self.score_pad)

        self.player_list = []
        for name in "nsew":
            player = Player(name)
            setattr(self, "player_" + name, player)
            self.player_list.append(player)
        self.player_n.next = self.player_w
        self.player_w.next = self.player_s
        self.player_s.next = self.player_e
        self.player_e.next = self.player_n
        self.player_n.buddy = self.player_s
        self.player_s.buddy = self.player_n
        self.player_w.buddy = self.player_e
        self.player_e.buddy = self.player_w

        self.score_pad.refresh()

        self.pk_list = []
        pk_seq = (["s5"] + [c + "j" for c in "rb"] + [c + "5" for c in "hcd"] + [c + n for n in "32" for c in "shcd"] +
                  [c + n for c in "shcd" for n in "akqjt98764"])
        for i, pk_name in enumerate(pk_seq):
            for j in xrange(2):
                pk = Poker(i * 2 + j, pk_name, source = os.path.join("image", "%s.bmp" % pk_name))
                self.add_widget(pk)
                self.pk_list.append(pk)

        self.ok_button = OkButton(text = "OK", font_size = 30)
        self.ok_button.size = self.width / 16, self.width / 32
        self.ok_button.pos = self.width - self.ok_button.width * 2, 20 + poker_height + 30
        self.add_widget(self.ok_button)

        self.thinking_pad = Label(text = "THINKING")
        self.thinking_pad.size = poker_width * 3 / 2, 50
        self.thinking_pad.bold = True
        self.thinking_pad.font_size = 20
        self.thinking_pad.color = [1, 1, 1, 1]
        self.thinking_pad.pos = self.width, self.height
        self.add_widget(self.thinking_pad)

        self.turn = None
        self.start_game()

    def start_game(self):
        for pk in self.pk_list:
            pk.pos = self.width, self.height
            pk.selected = False
        pk_list = self.pk_list[:]
        random.shuffle(pk_list)
        for i, player in enumerate(self.player_list):
            player.pk_list = pk_list[i :: 4]
            player.pk_list.sort(key = lambda pk : pk.idx)
        self.show_my_pk_list()
        self.curr_player = self.player_s if self.turn is None else self.turn.get_winner()
        self.start_turn()

    def start_turn(self):
        self.turn = Turn(self.curr_player)
        self.continue_turn()

    def _continue_turn_callback(self, dt):
        self.continue_turn(from_callback = True)

    def continue_turn(self, from_callback = False):
        while not self.turn.end():
            self.curr_player.show_thinking_pad()
            if self.is_my_turn():
                base_type, num = self.turn.get_base_type_num()
                possible_play = get_possible_play(base_type, num, self.curr_player.pk_list)
                _assert(possible_play)
                if len(possible_play) == 1:
                    for pk in possible_play[0]:
                        pk.select()
                return
            if not from_callback:
                Clock.schedule_once(self._continue_turn_callback)
                return
            from_callback = False
            pk_list = ai_choice()
            _assert(self.turn.add(pk_list))
            self.curr_player.show_played_pk_list(pk_list)
            self.curr_player = self.curr_player.next
        else:
            self.end_turn()

    def end_turn(self):
        _assert(self.turn.end())
        self.curr_player = self.turn.finish()
        self.score_pad.refresh()

    def show_my_pk_list(self):
        count = len(self.player_s.pk_list)
        if count == 0:
            return
        _assert(count > 0)
        distance = 0 if count == 1 else (self.width - poker_width * 2) / (count - 1)
        if distance > poker_width / 2:
            distance = poker_width / 2
        total_width = distance * (count - 1) + poker_width
        space_width = (self.width - total_width) / 2
        for i, pk in enumerate(self.player_s.pk_list):
            if pk.selected:
                pk.deselect()
            pk.pos = space_width + i * distance, 20

    def is_my_turn(self):
        return self.curr_player is self.player_s

    def in_my_pk_list(self, pk_to_find):
        for pk in self.player_s.pk_list:
            if id(pk) == id(pk_to_find):
                return True
        return False

    def selected_pk_count(self):
        count = 0
        for pk in self.player_s.pk_list:
            if pk.selected:
                count += 1
        return count

    def on_pk_selected(self, pk_to_select):
        if self.selected_pk_count() > 1:
            for pk in self.player_s.pk_list:
                if pk.selected:
                    pk.deselect()

    def on_my_turn_play(self):
        _assert(self.is_my_turn())
        pk_list = [pk for pk in self.player_s.pk_list if pk.selected]
        if self.turn.add(pk_list):
            self.player_s.show_played_pk_list(pk_list)
            self.show_my_pk_list()
            self.curr_player = self.curr_player.next
            self.continue_turn()
        else:
            self.show_my_pk_list()

game = None

class Cjbp4App(App):
    def build(self):
        global game
        game = Cjbp4Game()
        return game

    def on_start(self):
        game.init()

    def on_pause(self):
        return True

if __name__ == '__main__':
    prog_dir = os.path.dirname(sys.argv[0])
    if prog_dir:
        os.chdir(prog_dir)
    app = Cjbp4App()
    app.run()
