#!/usr/bin/env python3

"""
This program is free software. It comes without any warranty, to
     * the extent permitted by applicable law. You can redistribute it
     * and/or modify it under the terms of the Do What The Fuck You Want
     * To Public License, Version 2, as published by Sam Hocevar. See
     * http://www.wtfpl.net/ for more details.
"""

import bs4
from _curses import error as curses_error
import locale
import os
import pyaudio
import random
import re
import requests
import struct
import sys
import threading
import time
import unicurses
import wave


os.chdir(os.path.dirname(os.path.realpath(__file__)))  # Changes working directory to the script's parent directory


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

if sys.platform == 'win32':  # Windows: set codepage to 65001 for unicode support
    os.system('chcp 65001')

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
    """
    try:
        stdscr.addstr(y, x, line, effect)  # Add the given line to coordinates (x, y) with effect 'effect'
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
        else:  # if no valid key descriptor is available, try using the character in the next conditional
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

    def update(self, key):
        """
        Adds a character/string to this class's value

        Args:
            key (str): Character/string to write to this class
        """
        if (not self.__char_limit or (self.__char_limit > 0 and len(self.__value) < self.__char_limit)) and \
           len(key) == 1:
            # If there is not a character limit OR there are less characters than the character limit,
            #   and there is only one character within the char string, add the character to the input
            self.__value = self.__value[:self.__cursor_pos] + key + self.__value[self.__cursor_pos:]
            self.__cursor_pos += 1
        if key == 'KEY_LEFT':  # If left arrow, move cursor pos left 1
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif key == 'KEY_RIGHT':  # If right arrow, move cursor pos right 1
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos + 1)
        elif key == 'KEY_HOME':  # If home key, move cursor to the beginning
            self.__cursor_pos = 0
        elif key == 'KEY_END':  # If end key, move cursor to the end
            self.__cursor_pos = len(self.__value)
        elif key == 'KEY_DC':  # If delete key, delete a character in front of the cursor
            self.__value = self.__value[:self.__cursor_pos] + self.__value[self.__cursor_pos + 1:]
            self.__cursor_pos = min(len(self.__value), self.__cursor_pos)
        elif key == 'KEY_BACKSPACE':  # If the backspace key, remove the character the cursor is on
            self.__value = self.__value[:max(0, self.__cursor_pos - 1)] + self.__value[self.__cursor_pos:]
            self.__cursor_pos = max(0, self.__cursor_pos - 1)
        elif key == 'KEY_ENTER':  # If the key is the enter key, do nothing and return
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


# Tracklist fetching code

songs = []  # The master list of songs: Format is [song name, song url]

song_list_data = requests.request('GET', 'http://jetsetradio.live/audioplayer/audio/~list.js').content
song_name_matches = re.findall(b'"(.*)";', song_list_data)  # Since the list is for a JS exec(), we need to parse it

for song_name in song_name_matches:  # Loop through all matches within the song list
    song_url = 'http://jetsetradio.live/audioplayer/audio/%s.mp3' % song_name.decode('utf-8')  # Format names into URLs
    songs.append([song_name.decode('utf-8'), song_url])  # Add the newly formatted song into the internal song list

del song_list_data  # Delete unused variables
del song_name_matches


# Audio playback code

playback_progress = 0  # 0 -> 1; How much audio has been played (for the status bar)
current_song = 'Loading...'  # The song currently playing
volume = 5  # The volume to play music at; goes from 0 to 9


def download_mp3_to_wav(url):
    """
    This function downloads a file given url 'url' and converts it into a wav
    for playback using pyAudio

    Args:
        url (str): The URL to download the file from
    """
    
    try:  # We want to remove the old temp.wav file (Windows can't remove immediately because it's still in use by us)
        os.remove('./temp.wav')
    except OSError:  # It's still in use??? (This should never happen)
        pass

    try:
        song_download = requests.request('GET', url).content  # Fetch the song data from the website
    except requests.ConnectionError:  # Return nothing and delete the tempfile if the song doesn't properly load
        os.remove('./temp.mp3')
        return

    temp = open('./temp.mp3', 'wb')  # Create a temporary file to load into ffmpeg
    temp.write(song_download)  # Write the song data to the temp file
    temp.close()  # Close the file and save it

    os.system('ffmpeg -loglevel panic -i %s -acodec pcm_u8 -ar 44100 temp.wav' % temp.name)  # Converts mp3 to wav
    while not os.path.exists('./temp.wav'):  # Wait for the new wav file to exist just in case
        time.sleep(1)
    os.remove(temp.name)  # Remove the mp3 temp file
    
    new_wave = wave.open('./temp.wav')  # Load the wav file

    return new_wave


def play_song(name, url):
    """
    Function that plays a song in a new thread

    Args:
        name (str): Name to display
        url (str): URL to fetch the mp3 from
    """
    global current_song
    global playback_progress

    current_song = 'Loading...'  # Set the song name to 'Loading...' to notify the user
    playback_progress = 0

    wav = download_mp3_to_wav(url)  # Download the mp3 file as a wav from jetsetradio.live
    if not wav:  # If there's no wav returned, don't play it
        return

    current_song = name  # Set the song name to the new song

    pa = pyaudio.PyAudio()  # Main class of pyAudio; contains the open() function we need for an audio stream

    # Opens an audio stream on the default output device.
    # Explained: We're using 1/2th the framerate because we're going from Int16 to Float32; this change
    # requires us to get twice the amount of data, hence leaving us with twice the amount of bytes.
    # We convert from Int16 to Float32 to prevent byte overflow, which results in garbled (and scary) static.
    audio_stream = pa.open(wav.getframerate() // 2, wav.getnchannels(), pyaudio.paFloat32, output=True)
    audio_stream.start_stream()

    buffer_size = audio_stream._frames_per_buffer  # The amount of int16's to read per frame

    while True:
        data = wav.readframes(buffer_size * 2)  # Read data from wav
        if isinstance(data, str):  # Check typing to prevent errors
            data = data.encode('utf-8')

        # Take each byte, divide by 0x7FFF to get a float, and then multiply that by the volume constant
        data = struct.pack('f' * (len(data) // 2), *list(map(lambda b: b / 65535 * (volume / 9),
                           struct.unpack('H' * (len(data) // 2), data))))
        playback_progress = wav.tell() / wav.getnframes()  # Set percent of song played
        audio_stream.write(data)  # Write raw data to speakers

        if len(data) // 2 < buffer_size:  # If we're out of data, exit the loop
            break
        if current_song != name:  # If the song changed halfway through, stop the stream
            break

    audio_stream.stop_stream()

    del audio_stream  # Cleanup unused variables
    del pa
    del wav


# Main code

error_msg = ''  # If it's a thread exception, it'll write it to here
has_exception = False  # Will be set to true if an exception occurs, in which the user will be notified why this crashed


def register_exception():
    """
    Sets has_exception to True and the error_msg to the traceback
    """
    import traceback

    global error_msg
    global has_exception

    error_msg = traceback.format_exc()
    has_exception = True


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
    song_marquee_text = u''  # The marquee to be displayed at the top of the screen

    def draw():
        """
        Function that draws everything to the screen in one fell swoop.

        Notes:
            This used to be built in to the write thread, but since the write
            thread has been throttled to keep CPU and I/O low, we need to have
            this at the top so we can call it from both the text input loop as
            well as the write thread.
        """

        stdscr.clear()  # Clear the window

        write(chat_text, 0, 0)  # Write the base of the chat window
        write(marquee_text, 6, 21)  # Write the marquee text to the window
        write(song_marquee_text, 21, 2)  # Write the song marquee text to the window
        write(str(volume), 51, 2)  # Write the current volume to the window
        write(str(listeners).zfill(4), 61, 1)  # Write the amount of listeners to the window
        write('#' * int(20 * playback_progress), 56, 2)  # Write the percentage of the song completed
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

    def marquee_thread():
        """
        Constantly fetches and updates the marquee at the bottom of the window
        """
        global has_exception
        global marquee_text
        global song_marquee_text

        def fetch_broadcast_message():
                """
                Fetches the broadcast messsage to be marquee'd at the bottom of the screen
                """
                try:
                    data = requests.request('GET', 'http://jetsetradio.live/messages/messages.xml').content  # Get data
                    bs = bs4.BeautifulSoup(data, 'html.parser')  # Parse XML data retrieved from the URL

                    msg = bs.find('message').text  # Parse the broadcast message out of the XML data
                    broadcaster_name = bs.find('avatar').text  # Get the broadcaster's name

                    if broadcaster_name in broadcaster_names:  # Check that there's name for the broadcaster avatar id
                        msg = broadcaster_names[broadcaster_name] + ': ' + msg  # Replace the id with a name

                    return ' ' * 72 + msg  # Append 72 blank spaces to make it truly act like a marquee
                except requests.ConnectionError:  # If there is an issue retrieving the message, use a blank string
                    return ' ' * 72

        broadcast_message = fetch_broadcast_message()  # The message to be marquee'd at the bottom of the screen
        marquee_offset = 0  # The offset of which the marquee text is currently at

        last_song_name = ''  # The last song name played
        song_marquee = ' ' * 24 + 'Loading...'  # The song name to be marquee'd at the top of the screen
        song_marquee_offset = 0  # The offset of which the SONG marquee text is currently at

        try:
            while True:
                marquee_offset = (marquee_offset + 1) % len(broadcast_message)  # Set the marquee over by 1
                marquee_text = broadcast_message[marquee_offset:marquee_offset + 72]  # Offset marquee text

                song_marquee_offset = (song_marquee_offset + 1) % len(song_marquee)  # Set the song marquee over by 1
                song_marquee_text = song_marquee[song_marquee_offset:song_marquee_offset + 24]  # Offset marquee text

                if marquee_offset == 0:  # If the marquee is fully read, check if the server has a new one readied
                    broadcast_message = fetch_broadcast_message()

                if last_song_name != current_song:  # Check to make sure the song name marquee is still valid
                    song_marquee_offset = 0  # Set the offset to 0
                    song_marquee = ' ' * 24 + current_song  # Set the current marquee to be the new song
                    last_song_name = current_song  # ...and set the last song as the new one

                time.sleep(0.1)
                if has_exception:
                    break
        except:
            register_exception()

    def listener_thread():
        """
        Updates the listener count at the top right of the window
        """
        global listeners

        try:
            while True:
                try:
                    # Retrieve the listener XML page
                    data = requests.request('GET', 'http://jetsetradio.live/counter/listeners.xml').content
                    listeners = data.count(b'<user>')  # The amount of listeners = <user> tags, so we can use count()
                except requests.ConnectionError:  # Don't do anything when errors occur so as not to reset the counter
                    pass

                time.sleep(1)
                if has_exception:
                    break
        except:
            register_exception()

    def chat_thread():
        """
        Constantly retrieves chat messages from jetsetradio.live and places them into chat_messages
        """
        global chat_messages

        try:
            while True:
                try:
                    new_messages = []  # The new messages to replace the old ones with

                    data = requests.request('GET', 'http://jetsetradio.live/chat/messages.xml').content  # Retrieve data
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
                            message_data = {'user': None, 'msg': chunk}  # Create dict to insert into chat_messages

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
        except:
            register_exception()

    def song_thread():
        """
        Constantly updates the current song / plays it back
        """
        global current_song
        global has_exception
        global playback_progress

        try:
            while True:
                time.sleep(1)
                next_song = songs[random.randrange(len(songs))]  # Get a random song from the list
                play_song(*next_song)  # Play back said song (format [song name, song url])

                if has_exception:
                    break
        except:
            register_exception()

    def write_thread():
        """
        Writes the contents of the chat window to the terminal constantly
        """
        global has_exception

        try:
            while True:
                draw()

                time.sleep(0.1)
                if has_exception:
                    break
        except:
            register_exception()

    # Create threads
    thread_1 = threading.Thread(target=marquee_thread, daemon=True)
    thread_2 = threading.Thread(target=listener_thread, daemon=True)
    thread_3 = threading.Thread(target=chat_thread, daemon=True)
    thread_4 = threading.Thread(target=song_thread, daemon=True)
    thread_5 = threading.Thread(target=write_thread, daemon=True)

    # Run threads
    thread_1.start()
    thread_2.start()
    thread_3.start()
    thread_4.start()
    thread_5.start()

    # Input loop; not a thread so that the program will run properly

    def parse_commands(msg):
        """
        Parses commands sent by the user

        Args:
            msg (str): The command string to execute
        """

        command = msg.split(' ')[0].lower()  # Get the command
        command_args = msg.split(' ')[1:]  # Get all the args along with the command name

        if command == 'exit':  # Quit the app
            current_song = 'None'  # Stop song
            stdscr.clear()  # Clear screen before exit
            stdscr.refresh()  # Refresh to load cleared screen
            
            time.sleep(0.2)  # Give time for song to stop

            try:
                os.remove('./temp.wav')  # Try to delete tempfile
            except OSError:
                pass
                
            unicurses.endwin()  # Reset terminal back to original state
            sys.exit()  # Exit the application
        elif command == 'setvolume':  # Volume change command
            try:  # Try and parse the argument as a volume and then set said volume
                global volume

                volume = max(0, min(9, int(command_args[0])))  # Clamp between 0 and 9
            except (TypeError, IndexError):
                pass
        elif command == 'skipsong':  # Skip the current song
            global current_song

            current_song = 'Loading...'  # Since the playback code stops if the current_song's changed, this works

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
            elif char == 'KEY_TAB':  # Replace tabs with 4 spaces to prevent input glitches
                for i in range(4):
                    chat_input.update(' ')
            else:  # Standard character; add to the current input
                chat_input.update(char)

            draw()  # Draw the text input instantly
        except curses_error:  # Prevent crashes simply because of input glitches
            pass

        if has_exception:
            break

except KeyboardInterrupt:  # CTRL+C
    pass
except SystemExit:  # /exit
    pass
except:  # unexpected shutdown
    register_exception()

if has_exception:  # If an exception occurs, print how to get help debugging the client

    current_song = 'None'  # Stop the current song

    logfile = open('./errorlog.txt', 'w')  # Create errorlog.txt in the working directory to write the exception to
    logfile.write(error_msg)  # Writes the exception traceback to the file...
    logfile.close()  # ...and then closes it, saving it

    stdscr.clear()  # Clear the screen to print the error message

    unicurses.beep()  # Attempt to make a beep; may not be possible on Linux without the pcspkr driver loaded

    # Write a message stating how to get help with debugging for those who aren't programmers
    write('Fatal error occured: please send errorlog.txt to bb via pqlime@gmail.com', 0, 0)
    write('Press any key to exit.', 0, 1)
    stdscr.refresh()

    get_key()  # Wait for key
    os.remove('./temp.wav')  # Remove the temporary song file

unicurses.endwin()  # Returns the terminal to it's original state
