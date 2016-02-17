#!/usr/bin/env python3

#    Specton Audio Analyser
#    Copyright (C) 2016 D. Bird <somesortoferror@gmail.com>
#    https://github.com/somesortoferror/specton

version = 0.11

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QAction, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5 import uic
from PyQt5.QtCore import QByteArray
import os.path
from os import walk
import fnmatch, re
import configparser
import subprocess
from multiprocessing import Pool, Process
import time
import queue
import io

if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,sys.stdout.encoding,'backslashreplace') # fix for printing utf8 strings on windows

if __name__ == '__main__':
    main_q = queue.Queue()

if __name__ == '__main__':
    form_class = uic.loadUiType("specton.ui")[0]                 # Load the UI

    config = configparser.ConfigParser(allow_no_value = True)
    config.read('specton.ini') # Load config file

    try:
        options = config['Options']
    except:
        config['Options'] = {}
        options = config['Options']
    
    debug_enabled = options.getboolean('Debug', False)
    stop_tasks = False

def findGuessEncBin():
    if os.name == 'nt':
        bin = 'scanners/mp3guessenc.exe'
    elif os.name == 'posix':
        bin = '/usr/bin/mp3guessenc'
    else:
        bin = ''
        
    return bin

def findMediaInfoBin():
    if os.name == 'nt':
        bin = 'scanners/MediaInfo.exe'
    elif os.name == 'posix':
        bin = '/usr/bin/mediainfo'
    else:
        bin = ''
        
    return bin

        
def scanner_Thread(row,filenameStr,binary,options,debug_enabled):
# run scanner on filenameStr as separate process
# and return output as string
    if debug_enabled:
        print("DEBUG: thread started for row {}, file: {}".format(row,filenameStr))
    try:
        output = subprocess.check_output([binary,options,filenameStr])
        output_str = output.decode(sys.stdout.encoding)
    except:
        output_str = "Error"
    return (row,output_str,filenameStr)

if __name__ == '__main__':
    TableHeaders = ["Folder","Filename","Length","Bitrate","Filesize","Encoder"]
    task_count = 0

if __name__ == '__main__':
    guessenc_encoder_regex = re.compile(r"^Maybe this file is encoded by (.*)",re.MULTILINE)
    guessenc_encoder_string_regex = re.compile(r"^Encoder string \: (.*)",re.MULTILINE)
    guessenc_bitrate_regex = re.compile(r"Data rate.*\: (.*)",re.MULTILINE)
    guessenc_length_regex = re.compile(r"Length.*\: ([\d\:\.]*)",re.MULTILINE)
    guessenc_filesize_regex = re.compile(r"Detected .*?\n  File size.*?\: (\d* bytes)",re.MULTILINE)
    mediainfo_format_regex = re.compile(r"^Audio.*?Format.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_encoder_regex = re.compile(r"^Writing library.*\: (.*)",re.MULTILINE)
    mediainfo_length_regex = re.compile(r"^Audio.*?Duration.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_bitrate_regex = re.compile(r"^Bit rate.*\: ([\d\. ]* [MK]bps)",re.MULTILINE)
    mediainfo_filesize_regex = re.compile(r"^File size.*\: (.* .iB|.* Bytes)",re.MULTILINE)

def doMP3Checks(mp3guessenc_output):
# do some MP3 quality checks here
    return True
    
def parse_mp3guessenc_output(mp3guessenc_output):
# parse mp3guessenc output using regex
# return parsed variables as a dictionary
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""

    search = guessenc_encoder_regex.search(mp3guessenc_output)
    if search is not None:
        encoder=search.group(1)
    search = guessenc_encoder_string_regex.search(mp3guessenc_output)
    if search is not None:
        encoder_string=search.group(1)
    search = guessenc_bitrate_regex.search(mp3guessenc_output)
    if search is not None:
        bitrate=search.group(1)
    search = guessenc_length_regex.search(mp3guessenc_output)
    if search is not None:
        length=search.group(1)
    search = guessenc_filesize_regex.search(mp3guessenc_output)
    if search is not None:
        filesize=search.group(1)

    checks_ok = doMP3Checks(mp3guessenc_output)
        
    return {'encoder':encoder, 'audio_format':'MP3', 'bitrate':bitrate ,'encoder_string':encoder_string, 'length':length, 'filesize':filesize, 'checks_ok':checks_ok, 'error':False }

def parse_mediainfo_output(mediainfo_output):
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""
    audio_format="Unknown"
    checks_ok = False

    search = mediainfo_encoder_regex.search(mediainfo_output)
    if search is not None:
        encoder=search.group(1)

    search = mediainfo_format_regex.search(mediainfo_output)
    if search is not None:
        audio_format=search.group(1)

    search = mediainfo_length_regex.search(mediainfo_output)
    if search is not None:
        length=search.group(1)

    search = mediainfo_bitrate_regex.search(mediainfo_output)
    if search is not None:
        bitrate=search.group(1)

    search = mediainfo_filesize_regex.search(mediainfo_output)
    if search is not None:
        filesize=search.group(1)

    return {'encoder':encoder, 'audio_format':audio_format, 'bitrate':bitrate ,'encoder_string':encoder_string, 'length':length, 'filesize':filesize, 'checks_ok':checks_ok, 'error':False }
    
    
def scanner_Finished(fileinfo):
# callback function
# runs after scanner process has completed
    i = fileinfo[0]
    scanner_output = fileinfo[1]
    filenameStr = fileinfo[2]
    global task_count
    task_count -= 1

    if not (scanner_output == "Error"):
        if fnmatch.fnmatch(filenameStr, "*.mp3"):
            song_info = parse_mp3guessenc_output(scanner_output)
        elif fnmatch.fnmatch(filenameStr, "*.flac"):
            song_info = parse_mediainfo_output(scanner_output)
        else: # default to mediainfo... 
            song_info = parse_mediainfo_output(scanner_output)

        if debug_enabled:
            print("DEBUG: thread finished - row {}, result: {}, task count={}".format(i,song_info['encoder'],task_count))
    
        main_q.put((i,song_info,scanner_output))
    else:
        main_q.put((i,{'error':True},scanner_output))
        if debug_enabled:
            print("DEBUG: thread finished with error - row {}, result: {}, task count={}".format(i,scanner_output,task_count))

def headerIndexByName(table,headerName):
    index = -1
    for i in range(0, table.columnCount()):
        headerItem = table.horizontalHeaderItem(i)
        if headerItem.text() == headerName:
            index = i
    return index


class Main(QMainWindow):
    def __init__(self):
        super(Main, self).__init__()

        # build ui
        self.ui = form_class()
        self.ui.setupUi(self)

        self.ui.actionExit.triggered.connect(sys.exit)
        self.ui.actionScan_Files.triggered.connect(self.scan_Files)
        self.ui.actionFolder_Select.triggered.connect(self.select_Folder)
        self.ui.actionClear_Filelist.triggered.connect(self.clear_List)
        self.ui.actionStop.triggered.connect(self.cancel_Tasks)
            
        fileMenu = self.ui.menubar.addMenu('&File')
        fileMenu.addAction(self.ui.actionFolder_Select)
        fileMenu.addAction(self.ui.actionExit)
        helpMenu = self.ui.menubar.addMenu('&Help')
        helpMenu.addAction(self.ui.actionAbout)

        self.ui.tableWidget.setColumnCount(len(TableHeaders))
        self.ui.tableWidget.setHorizontalHeaderLabels(TableHeaders)
        self.ui.tableWidget.horizontalHeader().resizeSection(headerIndexByName(self.ui.tableWidget,"Filename"),300)
        self.ui.tableWidget.horizontalHeader().setSectionsMovable(True)
        
        playFileAction = QAction("Play File",None)
        playFileAction.triggered.connect(self.contextPlayFile)
        self.ui.tableWidget.addAction(playFileAction)

        browseFolderAction = QAction("Browse Folder",None)
        browseFolderAction.triggered.connect(self.contextBrowseFolder)
        self.ui.tableWidget.addAction(browseFolderAction)
        
        windowStateStr = options.get('windowState')
        windowGeometryStr = options.get('windowGeometry')
        if windowStateStr is not None:
            windowState = QByteArray.fromBase64(QByteArray().append(windowStateStr))
            self.restoreState(windowState)
        if windowGeometryStr is not None:
            windowGeometry = QByteArray.fromBase64(QByteArray().append(windowGeometryStr))
            self.restoreGeometry(windowGeometry)

            
    def closeEvent(self,event):
        windowState = self.saveState()
        windowGeometry = self.saveGeometry()
        config['Options']['windowState'] = str(windowState.toBase64())
        config['Options']['windowGeometry'] = str(windowGeometry.toBase64())
        with open('specton.ini', 'w') as configfile:
            config.write(configfile)            
        event.accept()        
    
    def contextPlayFile(self):
        pass

    def contextBrowseFolder(self):
        pass
    
    def select_Folder(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory to Scan", os.path.expanduser("~")))
        
        filemask = options.get('FilemaskRegEx')
        if filemask == None:
            filemask = "\.mp3$|\.flac$|\.mpc$|\.ogg$|\.wav$|\.m4a$|\.aac$|\.ac3$|\.ra$|\.au$"
        filemask_regex = re.compile(filemask,re.IGNORECASE)

        followsymlinks = options.getboolean('FollowSymlinks')
        if followsymlinks == None:
            followsymlinks = False
        recursedirectories = options.getboolean('RecurseDirectories')
        if recursedirectories == None:
            recursedirectories = False

        self.ui.tableWidget.setUpdatesEnabled(False)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(0)
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        
        # walk through directory chosen by user
        # and add filenames to treeview
        for root, dirs, files in os.walk(directory, True, None, followsymlinks):
            for name in files:
                if filemask_regex.search(name) is not None:
                    i = self.ui.tableWidget.rowCount()
                    self.ui.tableWidget.insertRow(i)
                    filenameItem = QTableWidgetItem(name)
                    filenameStr = os.path.join(root, name)
                    filenameItem.setToolTip(filenameStr)
                    filenameItem.setData(33, filenameStr)
                    codecItem = QTableWidgetItem("Not scanned")
                    folderItem = QTableWidgetItem(os.path.basename(root))
                    folderItem.setToolTip(root)
                    bitrateItem = QTableWidgetItem("")
                    lengthItem = QTableWidgetItem("")
                    filesizeItem = QTableWidgetItem("")
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Filename"), filenameItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Folder"), folderItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Encoder"), codecItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Bitrate"), bitrateItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Length"), lengthItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Filesize"), filesizeItem)

                    self.statusBar().showMessage("Scanning for files: {} found".format(i))
                    
                    QApplication.processEvents()

        self.ui.tableWidget.setUpdatesEnabled(True)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        self.statusBar().showMessage('Ready')
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
                    
    def cancel_Tasks(self):
        if task_count > 0: # tasks are running
            global stop_tasks
            stop_tasks = True
    
    def scan_Files(self):
    # loop through table and queue scanner processes for all files
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
        
        numproc = options.getint('processes') # number of scanner processes to run, default = # of cpus
        pool = Pool(processes=numproc)
        
        self.ui.tableWidget.setSortingEnabled(False) # prevent row numbers changing
        self.ui.tableWidget.setUpdatesEnabled(True)
        
        mp3guessencbin = options.get('mp3guessencbin') # path to mp3guessenc binary
        if mp3guessencbin == None:
            mp3guessencbin = findGuessEncBin()
        if (mp3guessencbin == "") or (not os.path.exists(mp3guessencbin)):
            mp3guessencbin = ""

        mediainfo_bin = options.get('mediainfo_bin') # path to mediainfo binary
        if mediainfo_bin == None:
            mediainfo_bin = findMediaInfoBin()
        if (mediainfo_bin == "") or (not os.path.exists(mediainfo_bin)):
            mediainfo_bin = ""

        global task_count
        task_count = 0 # tasks remaining

        for i in range(0,self.ui.tableWidget.rowCount()):
            filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
            filenameStr = filenameItem.data(33) # filename
            fileScanned = filenameItem.data(32) # boolean, true if file already scanned
            
            if not fileScanned:
#                codecItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Encoder"))
#                codecItem.setText("Scanning...")
            
                if debug_enabled:
                    print("DEBUG: About to run process for file {}".format(filenameStr))

                if fnmatch.fnmatch(filenameStr, "*.mp3") and not mp3guessencbin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mp3guessencbin,"-e",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"-",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                elif not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"-",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                
            QApplication.processEvents()
            
        pool.close()

        task_total = self.ui.tableWidget.rowCount()

        def update_Table(row,song_info,scanner_output):
        # update table with info from scanner
            error_status = song_info['error']
            if not error_status:
                filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
                filenameItem.setData(32, True)
                codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
                encoder_string = song_info['encoder_string']
                encoder = song_info['encoder']
                audio_format = song_info['audio_format']
                if not encoder_string == "":
                    codecItem.setText("{} ({})".format(audio_format,encoder_string))
                else:
                    if encoder == "":
                        codecItem.setText("{}".format(audio_format))
                    else:
                        codecItem.setText("{} ({})".format(audio_format,encoder))
                
                codecItem.setToolTip(scanner_output)
                bitrateItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Bitrate"))
                bitrateItem.setText(song_info['bitrate'])
                lengthItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Length"))
                lengthItem.setText(song_info['length'])
                filesizeItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filesize"))
                filesizeItem.setText(song_info['filesize'])
            else:
                codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
                codecItem.setText("error scanning file")
                codecItem.setToolTip(scanner_output)
            
            QApplication.processEvents()

        self.statusBar().showMessage('Scanning files...')

        global stop_tasks
        while (task_count > 0) and (not stop_tasks):
            tasks_done = task_total - task_count
            self.ui.progressBar.setValue(round((tasks_done/task_total)*100))
            QApplication.processEvents()
            time.sleep(0.025)

            if not main_q.empty():
            # scanner processes add results to main_q when finished
                q_info = main_q.get(False,5)
                row = q_info[0]
                song_info = q_info[1]
                scanner_output = q_info[2]
                update_Table(row,song_info,scanner_output)
                        
        if debug_enabled:
            print("DEBUG: all threads finished, task count={}".format(task_count))

        if stop_tasks:
            pool.terminate()
            stop_tasks = False
        
        while not main_q.empty():
        # keep going until results queue is empty
            q_info = main_q.get(False,5)
            row = q_info[0]
            song_info = q_info[1]
            scanner_output = q_info[2]
            update_Table(row,song_info,scanner_output)
                           
        self.ui.progressBar.setValue(100)
        self.statusBar().showMessage('Done')
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
        self.ui.actionFolder_Select.setEnabled(True)
        self.ui.tableWidget.setSortingEnabled(True)
            
    def clear_List(self):
        self.ui.progressBar.setValue(0)
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def about_Dlg(self):
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
