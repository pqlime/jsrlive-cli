#!/usr/bin/env python3

"""
This program is free software. It comes without any warranty, to
     * the extent permitted by applicable law. You can redistribute it
     * and/or modify it under the terms of the Do What The Fuck You Want
     * To Public License, Version 2, as published by Sam Hocevar. See
     * http://www.wtfpl.net/ for more details.
"""

import bs4
import unicurses
from _curses import error as curses_error
import locale
import os
import re
import requests
import sys
import threading
import time


# Screen config

stdscr = unicurses.initscr()  # initiates the unicurses module & returns a writable screen obj

unicurses.noecho()  # disables echoing of user input
unicurses.cbreak()  # characters are read one-by-one
unicurses.curs_set(0)  # Hide the cursor from view by the user
unicurses.start_color()  # enables color in terminal

stdscr.keypad(True)  # returns special keys like PAGE_UP, etc.
stdscr.nodelay(False)  # enables input blocking to keep CPU down

locale.setlocale(locale.LC_ALL, '')
encoding = locale.getpreferredencoding()  # get the preferred system encoding for unicode support


# Settings

broadcaster_names = {  # Broadcaster names for the 'BCST' bar
    'djprofessork': 'DJ Professor K',
    'noisetanks': 'Noise Tanks',
    'seaman': 'Seaman'
}

unicurses.init_pair(1, unicurses.COLOR_BLUE, unicurses.COLOR_BLACK)  # default user color pair
unicurses.init_pair(2, unicurses.COLOR_CYAN, unicurses.COLOR_BLACK)  # registered user color pair
unicurses.init_pair(3, unicurses.COLOR_YELLOW, unicurses.COLOR_BLACK)  # DJPK color pair

default_color = unicurses.color_pair(1) | unicurses.A_BOLD  # default user color
registered_color = unicurses.color_pair(2) | unicurses.A_BOLD  # registered user color
djpk_color = unicurses.color_pair(3) | unicurses.A_BOLD  # DJPK color

login_text = open('./screens/login.txt', 'r').read()  # login text loaded from file
chat_text = open('./screens/chat.txt', 'r').read()  # chat text loaded from file


# Core functions and classes

def write(line, x, y, effect=0):
    """
    Function to write text to coordinates (x, y) with optional effect

    Args:
        line (str): Line to write to coordinates (x, y)
        x (int): X position to write text to
        y (int): Y position to write text to
        effect (int): Curses effect to apply to the text given (A_BLINK, etc.)

    Notes:
        We put stdscr.addstr into a variable to check that it doesn't return
            uniunicurses.ERR. If it does, we can throw an
    """
    try:
        stdscr.addstr(y, x, line, effect)
    except TypeError:
        stdscr.addstr(y, x, line, effect)  # error with win32; addstr requires a str and not byte
    except curses_error:
        pass


def get_key():
    """
    Function to retrieve a character (code) given user input.
    Non-blocking mode available if stdscr.nodelay(False) is called.
    """

    try:  # Catch non-blocking errors when attempting to fetch character
        if sys.platform == 'win32':
            wch = unicurses.wgetkey(stdscr)  # wgetkey is for windows support
        else:
            wch = stdscr.get_wch()  # get_wch is for linux ( and os x?)
    except curses_error:  # No input error --> return ''; only happens if blocking off
        return ''
    if isinstance(wch, int):  # if the keycode is a byte, it'll return an int which needs to be converted
        if unicurses.keyname(wch):  # check for a valid key descriptor
            return unicurses.keyname(wch).decode('utf-8')
        else:  # if no valid key descriptor is available, try using the character in the next area
            wch = chr(wch)
    if isinstance(wch, str):  # already a string; check if KEY_ENTER or KEY_TAB as they are unparsed by keyname(wch)
        if wch == '\n':  # newline = KEY_ENTER
            return 'KEY_ENTER'
        elif wch == '\t':  # tab = KEY_TAB
            return 'KEY_TAB'
        elif wch == '\b':  # bs = KEY_BACKSPACE
            return 'KEY_BACKSPACE'
        else:  # properly formatted, we can return this safely
            return wch


class TextInput(object):
    def __init__(self, char_limit):
        """
        Text input class for user interaction. Updated manually.

        Args:
            char_limit (int): Max amount of characters that can be written by the user
        """

        self.__value = u''  # Text value of this class
        self.__cursor_pos = 0  # When using write(), it displays the text along with a user cursor.
        self.__char_limit = char_limit  # Max amount of characters writable

    def update(self, char):
        """
        Adds a character/string to this class's value

        Args:
            char (str): Character/string to write to this class
        """
        if (not self.__char_limit or (self.__char_limit > 0 and len(self.__value) < self.__char_limit)) and \
           len(char) == 1:
            # If there is not a character limit OR there are less characters than the character limit,
            #   and there is only one character within the char string, add the character to the input
            self.__value = self.__value[:self.__cursor_pos] + char + self.__value[self.__cursor_pos:]
            self.__cursor_pos += 1
        if char == 'KEY_LEFT':  # If left arrow, move cursor pos left 1
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif char == 'KEY_RIGHT':  # If right arrow, move cursor pos right 1
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos + 1)
        elif char == 'KEY_HOME':  # If home key, move cursor to the beginning
            self.__cursor_pos = 0
        elif char == 'KEY_END':  # If end key, move cursor to the end
            self.__cursor_pos = len(self.__value)
        elif char == 'KEY_DC':  # If delete key, delete a character in front of the cursor
            self.__value = self.__value[:self.__cursor_pos] + self.__value[self.__cursor_pos + 1:]
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos)
        elif char == 'KEY_BACKSPACE':  # If the backspace key, remove the character the cursor is on
            self.__value = self.__value[:max(0, self.__cursor_pos - 1)] + self.__value[self.__cursor_pos:]
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif char == 'KEY_ENTER':  # If the key is the enter key, do nothing and return
            return
        if self.__char_limit > 0:  # If there is a character limit in place, truncate the current input to stay in it
            self.__value = self.__value[:self.__char_limit]

    @property
    def value(self):  # Value property for external reading
        return self.__value

    @value.setter
    def value(self, new_value):  # Value property setter for external writing
        assert isinstance(new_value, str)
        self.__value = new_value
        self.__cursor_pos = len(new_value)

    def write(self, x=0, y=0, active=False, is_password=False):
        """
        Function to write this class's input to coordinates (x, y)

        Args:
            x (int): X position to write text to
            y (int): Y position to write text to
            active (bool): Whether or not to render the cursor along with the text
            is_password (bool): Whether or not to render all the text as asterisks
        """

        to_write = (is_password and '*' * len(self.__value) or self.__value)  # replace text with *'s if password
        if not active:  # me_irl
            write(to_write, x, y)  # Write using the default function
        else:  # Text input is active, so cursor needs to be rendered
            if len(self.__value) == 0:  # If there is no text, just render the cursor
                write(' ', x, y, unicurses.A_REVERSE)
            else:  # If there is text, render the text alongside the cursor
                # to_write = to_write.encode(encoding)  # Encode to be unicode-safe

                cpos = max(0, self.__cursor_pos - 1)  # Calculate the proper position in the text to render w/ cursor

                stdscr.addnstr(y, x, to_write, cpos + 1)  # Write the text before the cursor
                stdscr.addnstr(y, x + cpos, to_write[cpos], 1, unicurses.A_REVERSE)  # Write the cursor character
                stdscr.addstr(y, x + cpos + 1, to_write[cpos + 1:])  # Write all text after the cursor mark


# Audio code

# todo: audio code


# Main code

has_exception = False  # Will be set to true if an exception occurs, in which the user will be notified why this crashed
threads = []

try:  # Hold all code within a try-catch statement so that errors can be logged upon any crashes
    # Login loop

    stdscr.clear()  # Clears the screen

    username, password = '', ''  # Username and password to be sent with every chat request
    current_field = True  # Username = True, Password = False
    user_field = TextInput(18)  # Username field, 18 is the site limit
    pass_field = TextInput(40)  # Password field (never used by anyone but DJPK?)
    enter_username_warning = False  # If a blank username is given, it'll display a warning after toggling this variable

    write(login_text, 0, 0)  # Because blocking is enabled when first run, we need to draw the login screen pre-loop

    while True:  # main login loop
        char = get_key()  # Get key to input into either the username or password field

        if char == 'KEY_UP' or char == 'KEY_DOWN' or char == 'KEY_TAB':  # Switch between username and password fields?
            current_field = not current_field
        elif char == 'KEY_ENTER':  # Are we entering credentials?
            if user_field.value.replace(' ', '') == '':  # Make sure that we aren't entering a blank username
                enter_username_warning = True
            else:  # If the username isn't blank, break the loop and go to the chat loop
                username = user_field.value
                pass_field = pass_field.value
                break
        else:  # Write character to input if not a special character
            if current_field:  # Current field true = write to password field, false = write to username field
                user_field.update(char)
            else:
                pass_field.update(char)

        write(login_text, 0, 0)  # Write the base of the login window
        user_field.write(11, 15, current_field)  # Write the username input to it's respective location
        pass_field.write(11, 16, not current_field)  # Write the password input to it's respective location as well

        if enter_username_warning:
            write('    You must enter a username!    ', 23, 12)

        stdscr.refresh()

    del current_field  # Cleanup unused variables
    del user_field
    del pass_field
    del enter_username_warning

    stdscr.clear()  # Clear screen for the chat window

    # Chat loop

    chat_input = TextInput(76)  # The input box where the user types and sends messages from
    chat_messages = []  # The messages to be written with every update. Format = {'user': [username, color], 'msg':msg}
    listeners = 0  # The amount of listeners currently listening to the podcast
    marquee_text = u''  # The marquee to be displayed at the bottom of the screen

    def marquee_thread():
        """
        Constantly fetches and updates the marquee at the bottom of the window
        """
        global marquee_text

        def fetch_broadcast_message():
            """
            Fetches the broadcast messsage to be marquee'd at the bottom of the screen
            """
            try:
                data = requests.request('GET', 'http://jetsetradio.live/messages/messages.xml').content  # Get the data
                bs = bs4.BeautifulSoup(data, 'html.parser')  # Parse XML data retrieved from the URL

                msg = bs.find('message').text  # Parse the broadcast message out of the XML data
                broadcaster_name = bs.find('avatar').text  # Get the broadcaster's name

                if broadcaster_name in broadcaster_names:  # Check that there is a value for the broadcaster avatar id
                    msg = broadcaster_names[broadcaster_name] + ': ' + msg  # If there is, replace the id with a name

                return ' ' * 72 + msg  # Append 72 blank spaces to make it truly act like a marquee
            except requests.ConnectionError:  # If there is an issue retrieving the message, use a blank string
                return ' ' * 72
            except:
                global has_exception
                has_exception = True

        broadcast_message = fetch_broadcast_message()  # The message to be marquee'd at the bottom of the screen
        marquee_offset = 0  # The offset of which the marquee text is currently at

        while True:
            marquee_offset = (marquee_offset + 1) % len(broadcast_message)  # Set the marquee offset over by 1
            marquee_text = broadcast_message[marquee_offset:marquee_offset + 72]  # Offset the marquee text

            if marquee_offset == 0:  # If the marquee is fully read, check if the server has a new one readied
                broadcast_message = fetch_broadcast_message()

            time.sleep(0.1)
            if has_exception:
                break

    def listener_thread():
        """
        Updates the listener count at the top right of the window
        """
        global listeners

        while True:
            try:
                # Retrieve the listener XML page
                data = requests.request('GET', 'http://jetsetradio.live/counter/listeners.xml').content.decode('utf-8')
                listeners = data.count('<user>')  # The amount of listeners = <user> tags, so we can use count()
            except requests.ConnectionError:  # Don't do anything when errors occur so as not to reset the counter
                pass

            time.sleep(1)
            if has_exception:
                break

    def chat_thread():
        """
        Constantly retrieves chat messages from jetsetradio.live and places them into chat_messages
        """
        global chat_messages

        while True:
            try:
                new_messages = []  # The new messages to replace the old ones with

                data = requests.request('GET', 'http://jetsetradio.live/chat/messages.xml').content  # Retrieve XML data
                bs = bs4.BeautifulSoup(data, 'html.parser')  # and parse it using BeautifulSoup

                messages = bs.findAll('message')  # Get all XML tags named 'message'
                messages.reverse()  # We reverse it so that we start from the last message and go forward

                lines_parsed = 0  # Keep track of how many lines we parse so we can stop at 13
                for message in messages:
                    user = message.find('username').get_text()  # Retrieve username from message
                    msg = message.find('text').get_text()  # Retrieve actual message from message

                    user_color = default_color  # The color of the user's name
                    if user == 'DJProfessorK':  # If the user is the Professor himself, change color to yellow
                        user_color = djpk_color
                    elif user.find('</font>') != -1:  # If the user is registered, change color to cyan
                        user_color = registered_color

                    user = re.sub('<[^<]+?>', '', user)  # Remove HTML tags from username and message
                    msg = re.sub('<[^<]+?>', '', msg)

                    msg = user + ': ' + msg  # Add username + the colon to the message
                    # Create message chunks of size 58
                    chunks = [msg[chunk:chunk + 58] for chunk in range(0, len(msg), 58)]
                    chunks.reverse()  # As from before, reverse it so we go from the back to the front

                    current_line = 0  # Keep track so we can add the username if it's the correct line
                    for chunk in chunks:
                        message_data = {'user': None, 'msg': chunk}  # Create dictionary to insert into chat_messages

                        current_line += 1
                        if current_line == len(chunks):  # If the line contains the username, add it to the msg data
                            message_data['user'] = [user, user_color]

                        new_messages.append(message_data)

                        lines_parsed += 1
                        if lines_parsed == 13:  # Stop parsing messages at line 13
                            break

                    chat_messages = new_messages  # replace the old messages with the new ones
            except requests.ConnectionError:  # Don't delete messages if messages can't be retrieved
                pass

            time.sleep(0.5)

            if has_exception:
                break

    def write_thread():
        """
        Writes the contents of the chat window to the terminal constantly
        """

        while True:
            stdscr.clear()  # Clear the window

            write(chat_text, 0, 0)  # Write the base of the chat window
            write(marquee_text, 6, 21)  # Write the marquee text to the window
            write(str(listeners).zfill(4), 61, 1)  # Write the amount of listeners to the window
            chat_input.write(2, 19, True)  # Write the chatbox to the window

            current_message = 0  # Keep count of what message we're on
            for message in chat_messages:  # Format = {'user': (None | [username, color]), 'msg': msg}
                write(message['msg'], 1, 17 - current_message)  # Write the message to the screen

                if message['user'] is not None:  # If the username is in the message, write it with it's color
                    write(message['user'][0], 1, 17 - current_message, message['user'][1])

                current_message += 1
                if current_message == 13:
                    break

            stdscr.refresh()  # Refresh the window, writing contents to screen

            time.sleep(0.05)
            if has_exception:
                break

    # Create threads
    thread_1 = threading.Thread(target=marquee_thread, daemon=True)
    thread_2 = threading.Thread(target=listener_thread, daemon=True)
    thread_3 = threading.Thread(target=chat_thread, daemon=True)
    thread_4 = threading.Thread(target=write_thread, daemon=True)

    # Run threads
    thread_1.start()
    thread_2.start()
    thread_3.start()
    thread_4.start()

    # Input loop; not a thread so that the program will run properly

    def parse_commands(msg):  # todo: add user commands
        pass

    while True:
        try:
            char = get_key()  # Fetch the key to input into the chat textbox

            if char == 'KEY_ENTER':  # Send button; once pressed send the input to the server
                if chat_input.value.replace(' ', '') != '':  # Prevent sending blank messages
                    if chat_input.value[0] == '/':  # Command prefix is '/'
                        parse_commands(chat_input.value[1:])  # Parse the commands without the command prefix
                    else:
                        try:
                            requests.request('POST', 'http://jetsetradio.live/chat/save.php',  # Send message to chat
                                             data={
                                                 'chatmessage': chat_input.value, 'username': username,
                                                 'password': password
                                             })
                        except requests.ConnectionError:  # If there's an issue with sending the message, don't retry
                            pass

                    chat_input.value = ''  # Delete the previous message after sending
            elif char == 'KEY_TAB':  # Replace \t with 4 spaces to prevent input glitches
                for i in range(4):
                    chat_input.update(' ')
            else:  # Standard character; add to the current input
                chat_input.update(char)
        except curses_error:  # Prevent crashes simply because of input glitches
            pass

        if has_exception:
            break

except KeyboardInterrupt:
    pass
except BaseException as e:
    import traceback
    has_exception = True

    logfile = open('./errorlog.txt', 'w')  # Create errorlog.txt in the working directory to write the exception to
    logfile.write(traceback.format_exc())  # Writes the exception traceback to the file...
    logfile.close()  # ...and then closes it, saving it

    stdscr.clear()

    if has_exception:  # If an exception occurs, print how to get help debugging the client
        unicurses.beep()  # Attempt to make a beep; may not be possible on Linux without the pcspkr driver loaded

        # Write a message stating how to get help with debugging for those who aren't programmers
        write('Fatal error occured: please send errorlog.txt to bb via pqlime@gmail.com', 0, 0)
        write('Press any key to exit.', 0, 1)
        stdscr.refresh()

        get_key()  # Wait for key

unicurses.endwin()  # Returns the terminal to it's original state
