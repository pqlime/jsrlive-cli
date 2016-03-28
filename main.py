#!/usr/bin/env python3

# dependencies: beautifulsoup4, requests, pyaudio, pydub

# nerd notes

# helpful links:
# messages = http://jetsetradio.live/chat/messages.xml
# listeners = http://jetsetradio.live/counter/listeners.xml or http://jetsetradio.live/counter/counter.php (2nd faster)
# djpk = http://jetsetradio.live/messages/messages.xml
# song list = http://jetsetradio.live/audioplayer/audio/~list.js

# posting = http://jetsetradio.live/chat/save.php (form data = chatmessage, username, chatpassword="false")


# printing:

# sys.stdout.write(text)
# sys.stdout.flush()

import bs4
import curses
from _curses import error as curses_error
import locale
# import pyaudio
# import pydub
import re
import requests
import threading
import time

stdscr = curses.initscr()

curses.noecho()
curses.cbreak()
curses.resizeterm(24, 80)
curses.curs_set(0)
# if curses.has_colors():
curses.start_color()
stdscr.keypad(True)
stdscr.nodelay(1)

# ===========CONFIG=========== #

broadcaster_names = {
    'djprofessork': 'DJ Professor K',
    'noisetanks': 'Noise Tanks',
    'seaman': 'Seaman',
}

curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)

# ============================ #

# sorry for this giant mess vvvv
login_text = '\n\n\n\n/=============================================================================\\\n|                ____. ___________________.____    .__                        |\n|               |    |/   _____/\\______   \\    |   |__|__  __ ____            |\n|               |    |\\_____  \\  |       _/    |   |  \\  \\/ // __ \\           |\n|           /\\__|    |/        \\ |    |   \\    |___|  |\\   /\\  ___/           |\n|           \\________/_______  / |____|_  /_______ \\__| \\_/  \\___  >          |\n|                           \\/         \\/        \\/             \\/            |\n>=============================================================================<\n|                           Please enter a username.                          |\n|           (Try not to be offensive, be respectful to other GGs!)            |\n|                                                                             |\n|        [>                                                          ]        |\n|        [>                                                          ]        |\n|             Note: Password not necessary if you do not use one!             |\n|       I do not know how the password works, if you have one use one.        |\n\\=============================================================================/\n\n'
chat_text = '\n/==[Jet Set Radio Live]=====================================[0000 listeners]==\\n[ Currently Playing | UNIMPLEMENTED YET!!!!!! |   [                    ] 0:00 ]\n===============================================================================\n|__________________________[Chat]__________________________|_[COMMANDS  LIST]_|\n|                                                          | help <CMD>       |\n|                                                          | setvolume <VOL>  |\n|                                                          | playmusic <TRUE> |\n|                                                          | skipsong         |\n|                                                          |                  |\n|                                                          |                  |\n|                                                          |                  |\n|                                                          |                  |\n|                                                          |                  |\n|                                                          | <UNIMPLEMENTED!> |\n|                                                          >==================<\n|                                                          | Command prefix ! |\n|                                                          | (example: !help) |\n|==========================================================V==================|\n|>                                                                            |\n>=============================================================================<\n[BCST:                                                                        ]\n\=============================================================================/\n'
# sorry for this giant mess ^^^^

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()
# pa = pyaudio.PyAudio()


def write(line, x, y, effect=0):
    if line != '':
        try:
            stdscr.addstr(x, y, str.encode(line, code), effect)
        except curses_error:
            pass


def rtnl(text):  # remove tab and newline
    return text.replace('\t', '    ').replace('\n', '')


def get_key_from_wch(wch):
    if wch == -1:
        return ''
    elif isinstance(wch, int):
        if curses.keyname(wch):
            return curses.keyname(wch).decode('utf-8')
        else:
            return chr(wch)
    elif isinstance(wch, str):
        if wch == '\x0A':
            return 'KEY_ENTER'
        return wch


class TextInput:
    def __init__(self, char_limit=0):
        self.__value = u''
        self.__cursor_pos = 0
        self.__char_limit = char_limit

    def update(self, char):
        if (self.__char_limit and len(self.__value) < self.__char_limit) or not self.__char_limit:
            if len(char) == 1:
                self.__value = self.__value[:self.__cursor_pos] + char + self.__value[self.__cursor_pos:]
                self.__cursor_pos += 1
        if char == 'KEY_LEFT':
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif char == 'KEY_RIGHT':
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos + 1)
        elif char == 'KEY_HOME':
            self.__cursor_pos = 0
        elif char == 'KEY_END':
            self.__cursor_pos = len(self.__value)
        elif char == 'KEY_DC':
            self.__value = self.__value[:self.__cursor_pos] + self.__value[self.__cursor_pos + 1:]
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos)
        elif char == 'KEY_BACKSPACE':
            self.__value = self.__value[:max(0, self.__cursor_pos - 1)] + self.__value[self.__cursor_pos:]
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif char == 'KEY_ENTER':
            return
        if self.__char_limit > 0:
            self.__value = self.__value[:self.__char_limit]

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_value):
        assert isinstance(new_value, str)
        self.__value = new_value
        self.__cursor_pos = len(new_value)

    def write(self, x=0, y=0, active=False, password=False):
        to_write = (password and '*' * len(self.__value) or self.__value)
        if not active:  # me_irl
            write(to_write, x, y)
        else:
            if len(self.__value) == 0:
                write(' ', x, y, curses.A_REVERSE)
            else:
                to_write = to_write.encode(code)
                cpos = max(0, self.__cursor_pos - 1)

                stdscr.addnstr(x, y, to_write, cpos + 1)
                stdscr.addnstr(x, y + cpos, chr(to_write[cpos]), 1, curses.A_REVERSE)
                stdscr.addstr(x, y + cpos + 1, to_write[cpos + 1:])


# ===============AUDIO CODE============== #

current_song = None
music_enabled = True


# def audio_callback(in_data, frame_count, time_info, status):
#     if current_song:
#         data = in_data
#     else:
#         data = in_data
#     return data, pyaudio.paContinue


# ===============MAIN CODE=============== #


def login():
    current_field = 0  # user_field = 0, password_field = 1
    enter_username_warning = False
    user_field = TextInput(char_limit=18)
    password_field = TextInput(char_limit=40)

    while True:
        try:
            char = get_key_from_wch(stdscr.get_wch())
        except curses_error:
            char = ''

        if char == 'KEY_UP' or char == 'KEY_DOWN' or char == '\t':
            current_field = abs(current_field - 1)
        elif char == 'KEY_ENTER':
            if user_field.value.replace(' ', '') != '':
                break
            else:
                enter_username_warning = True
        else:
            if current_field == 0:
                user_field.update(char)
            elif current_field == 1:
                password_field.update(char)

        write(login_text, 0, 0)
        user_field.write(15, 11, not current_field)
        password_field.write(16, 11, current_field, True)
        if enter_username_warning:
            write('    You must enter a username!    ', 12, 23)

        stdscr.refresh()

    return user_field.value, password_field.value


def main(username, password):
    client_input = TextInput(76)
    write(chat_text, 0, 0)

    def fetch_marquee():
        try:
            data = requests.request('GET', 'http://jetsetradio.live/messages/messages.xml').content
            bs = bs4.BeautifulSoup(data, 'lxml')

            msg = rtnl(bs.find('message').text)
            broadcaster = rtnl(bs.find('avatar').text)

            if broadcaster in broadcaster_names:
                msg = broadcaster_names[broadcaster] + ': ' + msg

            return (' ' * 72 + msg) * 2
        except requests.ConnectionError:
            return ' ' * 146

    def marquee_thread():
        dj_marquee = fetch_marquee()
        marquee_offset = 0

        last_frame = time.time()

        while True:
            time.sleep(0.05)
            delta = time.time() - last_frame
            last_frame = time.time()

            marquee_offset = (marquee_offset + delta * 10) % int(len(dj_marquee) / 2)
            marquee_offset_i = int(marquee_offset)

            input_text = dj_marquee[marquee_offset_i:marquee_offset_i + 72]
            write('[BCST:%s]' % (' ' * 72), 21, 0)
            write(input_text, 21, 6)
            if marquee_offset_i == 0:
                dj_marquee = fetch_marquee()

            stdscr.refresh()

    def listener_thread():
        while True:
            time.sleep(1)
            try:
                listeners = requests.request('GET', 'http://jetsetradio.live/counter/listeners.xml').content.decode(
                    'utf-8')
                write(str(listeners.count('<user>')).zfill(4), 1, 61)
            except requests.ConnectionError:
                pass
            stdscr.refresh()

    def chat_thread():
        while True:
            time.sleep(0.5)
            try:
                data = requests.request('GET', 'http://jetsetradio.live/chat/messages.xml').content
                bs = bs4.BeautifulSoup(data, 'lxml')

                messages = bs.findAll('message')
                messages.reverse()

                lines_written = 0
                for message in messages:
                    if lines_written == 13:
                        break
                    user = rtnl(message.find('username').get_text())
                    text = rtnl(message.find('text').get_text())

                    user_color = curses.color_pair(1)
                    if user == 'DJProfessorK':
                        user_color = curses.color_pair(2)
                    elif user.find('</font>') != -1:
                        user_color = curses.color_pair(3)

                    user_color = user_color | curses.A_BOLD
                    user = re.sub('<[^<]+?>', '', user)
                    text = re.sub('<[^<]+?>', '', text)

                    to_print = user + ': ' + text
                    chunks = [to_print[chunk:chunk + 58] for chunk in range(0, len(to_print), 58)]
                    chunks.reverse()

                    current_line = 0
                    for line in chunks:
                        write(line + ' ' * (58 - len(line)), 17 - lines_written, 1)

                        if current_line == len(chunks) - 1:
                            write(user, 17 - lines_written, 1, user_color)

                        lines_written += 1
                        current_line += 1

                        if lines_written == 13:
                            break
            except requests.ConnectionError:
                pass

            stdscr.refresh()

    thread_1 = threading.Thread(target=marquee_thread, daemon=True)
    thread_1.start()
    thread_2 = threading.Thread(target=listener_thread, daemon=True)
    thread_2.start()
    thread_3 = threading.Thread(target=chat_thread, daemon=True)
    thread_3.start()

    stdscr.nodelay(False)

    while True:
        try:
            char = get_key_from_wch(stdscr.get_wch())
            if char == 'KEY_ENTER':
                if client_input.value.replace(' ', '') != '':
                    if client_input.value[0] == '!':
                        params = client_input.value[1:].split(' ')

                    else:
                        try:
                            requests.request('POST', 'http://jetsetradio.live/chat/save.php',
                                             data={
                                                 'chatmessage': client_input.value, 'username': username,
                                                 'password': password
                                             })
                        except requests.ConnectionError:
                            pass
                    client_input.value = ''
            # elif char == 'KEY_RESIZE':
            #     curses.resizeterm(24, 80)
            #     curses.curs_set(0)
            #     write(chat_text, 0, 0)
            elif char == '\t':
                for i in range(4):
                    client_input.update(' ')
            else:
                client_input.update(char)
        except curses_error:
            pass
        write(' ' * 76, 19, 2)
        client_input.write(19, 2, True)

        stdscr.refresh()


# =============STARTUP CODE============== #


has_exception = False

# pa_stream = pa.open(rate=44100, channels=2, format=pyaudio.paInt16, output=True, stream_callback=audio_callback)
# time.sleep(1)

# noinspection PyBroadException
try:
    stdscr.clear()
    name, passwrd = login()
    stdscr.clear()
    main(name, passwrd)
except KeyboardInterrupt:
    pass
except FileExistsError as e:
    import traceback

    has_exception = True
    logfile = open('./errorlog.txt', 'w')
    logfile.write(traceback.format_exc())
    logfile.close()

# =============CLEANUP CODE============== #

curses.endwin()
if has_exception:
    curses.beep()  # might not work on linux if beep driver not loaded
    print('Fatal error occured: please send log.txt to bb via pqlime@gmail.com.')
    input()  # prevents the window from closing when run standalone
