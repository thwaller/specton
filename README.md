# specton
Specton Audio Analyser

Graphical frontend for various audio scanners (mediainfo, mp3guessenc etc)  
Cross platform (Windows/Linux/Mac OS X)

Requires Python 3, PyQt5, requests

Windows: The easiest way to satisfy these requirements is to install [WinPython](http://winpython.github.io/#releases). Be sure to choose an installer with PyQt5 included (These have 'Qt5' in the filename)

Debian/Ubuntu: sudo apt-get install python3-pyqt5 mediainfo python3-requests  
Optional but recommended: sudo apt-get install libav-tools sox libsox-fmt-mp3 gnuplot  
mp3guessenc (for mp3 encoder detection): https://sourceforge.net/projects/mp3guessenc/  
aucdtect (for lossless transcode detection): http://true-audio.com/ftp/  

This product uses [MediaInfo](http://mediaarea.net/MediaInfo) library, Copyright (c) 2002-2014 MediaArea.net SARL.

Uses IcoMoon Free Pack icons (https://icomoon.io/)