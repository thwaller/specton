# specton
Specton Audio Analyser

Graphical frontend for various audio scanners (mediainfo, mp3guessenc etc)  
Cross platform (Windows/Linux/Mac OS X)

Requires Python 3, PyQt5, matplotlib

Windows: The easiest way to satisfy these requirements is to install [WinPython](http://winpython.github.io/#releases). Be sure to choose an installer with PyQt5 included (These have 'Qt5' in the filename)

Debian/Ubuntu: sudo apt-get install python3-pyqt5 python3-matplotlib mediainfo  
Optional but recommended: sudo apt-get install libav-tools sox libsox-fmt-mp3  
mp3guessenc (for mp3 encoder detection): https://sourceforge.net/projects/mp3guessenc/  
aucdtect (for lossless transcode detection): http://true-audio.com/ftp/  

FUQ:  
Q: I get an error "ValueError: Unrecognized backend string "qt5agg""  
A: Most likely your matplotlib library is too old. Upgrade with Pip or from the [website](http://matplotlib.org/)  

This product uses [MediaInfo](http://mediaarea.net/MediaInfo) library, Copyright (c) 2002-2014 MediaArea.net SARL.

Uses IcoMoon Free Pack icons (https://icomoon.io/)