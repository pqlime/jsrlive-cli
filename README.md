Jet Set Radio Live (jetsetradio.live) CLI Chat Application
=

Python library dependencies
-
Unfortunately I can't be arsed to write some socket code to fetch http pages
nor can I give enough of a fuck to write my own XML parser, so you're going
to need to get BeautifulSoup4 and requests. These both can be installed via
pip. The optional dependencies will eventually be included because I'll be
incorporating the music from the website version into the CLI app. Unicurses
is required because the curses library only works under Linux, and I don't
want to leave any funk soul brothers out of the fun, do I?

(Both the code in this program and the libraries are for Python 3)

Dependencies:
 * BeautifulSoup4
 * requests
 * pyAudio
 * Unicurses*

*If you are using Windows, you will have to also install curses via www.lfd.uci.edu/~gohlke/pythonlibs/#curses

How to install dependencies:
 * on Windows: ```python.exe -m pip install [LIBRARY_NAME]```
 * on Linux: ```pip3 install [LIBRARY_NAME]```
 * on OS X: ```i don't fucking know-- good luck and have fun reworking everything in the code for os x```

Running the program
-
Once all dependencies are installed, run main.py. If errors persist, it'll tell you. If a fatal error occurs, it'll create an `errorlog.txt` in the working directory: send that to my personal e-mail @ pqlime (at) gmail.com

Disclaimer
-
If this program causes the Rokkaku to come  after you or for your computer to catch  on fire, that's not my problem.

License
-
This program & it's source code are both under the Do What The Fuck You Want To
Public License. You can use both this and its source code as well as modify whatever
you'd like. 
