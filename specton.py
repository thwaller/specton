#!/usr/bin/env python3

#    Specton Audio Analyser
#    Copyright (C) 2016 D. Bird <somesortoferror@gmail.com>
#    https://github.com/somesortoferror/specton

version = 0.14

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
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QAction, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, QMenu, QLineEdit,QCheckBox,QSpinBox,QSlider,QTextEdit
from PyQt5 import uic
from PyQt5.QtCore import QByteArray, Qt, QSettings
import os.path
from os import walk
import fnmatch, re
import subprocess
from multiprocessing import Pool, Process
import time
import queue
import io
from functools import partial
import hashlib, zlib
import tempfile

dataScanned=32
dataFilenameStr=33
dataRawOutput=34

if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,sys.stdout.encoding,'backslashreplace') # fix for printing utf8 strings on windows

if __name__ == '__main__':
    main_q = queue.Queue()

if __name__ == '__main__':
    form_class = uic.loadUiType("specton.ui")[0]                 # Load the UI
    options_class = uic.loadUiType("options.ui")[0]
    fileinfo_class = uic.loadUiType("info.ui")[0]

    settings = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-settings")
    filecache = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-cache")
        
    debug_enabled = settings.value("Options/Debug", False, type=bool)
    stop_tasks = False

def findGuessEncBin():
    bin = settings.value('Paths/mp3guessenc_bin') # path to mp3guessenc binary
    if bin is None:
        if os.name == 'nt':
            bin = 'scanners/mp3guessenc.exe'
        elif os.name == 'posix':
            bin = '/usr/bin/mp3guessenc'
        else:
            bin = ''
        
    return bin

def findMediaInfoBin():
    bin = settings.value('Paths/mediainfo_bin') # path to mediainfo binary
    if bin is None:
        if os.name == 'nt':
            bin = 'scanners/MediaInfo.exe'
        elif os.name == 'posix':
            bin = '/usr/bin/mediainfo'
        else:
            bin = ''
        
    return bin

def findFlacBin():
    bin = settings.value('Paths/flac_bin')
    if bin is None:
        if os.name == 'nt':
            bin = 'scanners/flac.exe'
        elif os.name == 'posix':
            bin = '/usr/bin/flac'
        else:
            bin = ''
        
    return bin

def findauCDtectBin():
    bin = settings.value('Paths/aucdtect_bin') 
    if bin is None:
        if os.name == 'nt':
            bin = 'scanners/auCDtect.exe'
        elif os.name == 'posix':
            bin = '/usr/bin/aucdtect'
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

def aucdtect_Thread(row,filenameStr,decoder_bin,decoder_options,aucdtect_bin,aucdtect_options,debug_enabled):
    if debug_enabled:
        print("DEBUG: aucdtect thread started for row {}, file: {}".format(row,filenameStr))
    try:
        temp_file = tempfile.NamedTemporaryFile()
        temp_file_str = temp_file.name
        temp_file.close()
        decoder_output = subprocess.check_output([decoder_bin,decoder_options,filenameStr,"-o",temp_file_str],stderr=subprocess.PIPE)
        aucdtect_output = subprocess.check_output([aucdtect_bin,aucdtect_options,temp_file_str],stderr=subprocess.PIPE)
        output_str = aucdtect_output.decode(sys.stdout.encoding)
    except:
        output_str = "Error"
        
    return (row,output_str,filenameStr)

    
if __name__ == '__main__':
    TableHeaders = ["Folder","Filename","Length","Bitrate","Filesize","Encoder","Quality"]
    task_count = 0

if __name__ == '__main__':
    guessenc_encoder_regex = re.compile(r"^Maybe this file is encoded by (.*)",re.MULTILINE)
    guessenc_encoder_string_regex = re.compile(r"^Encoder string \: (.*)",re.MULTILINE)
    guessenc_bitrate_regex = re.compile(r"Data rate.*\: (.*)",re.MULTILINE)
    guessenc_length_regex = re.compile(r"Length.*\: ([\d\:\.]*)",re.MULTILINE)
    guessenc_filesize_regex = re.compile(r"Detected .*?\n  File size.*?\: (\d*) bytes",re.MULTILINE)
    guessenc_frame_hist_regex = re.compile(r"Frame histogram\n(.*?)\n\n",re.DOTALL|re.MULTILINE)
    guessenc_block_usage_regex = re.compile(r"Block usage\n(.*?)\n\s*-",re.DOTALL|re.MULTILINE)
    guessenc_mode_count_regex = re.compile(r"Mode extension.*?\n(.*?)\n\s*-",re.DOTALL|re.MULTILINE)
    mediainfo_format_regex = re.compile(r"^Audio.*?Format.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_encoder_regex = re.compile(r"^Writing library.*\: (.*)",re.MULTILINE)
    mediainfo_length_regex = re.compile(r"^Audio.*?Duration.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_bitrate_regex = re.compile(r"^Bit rate.*\: ([\d\. ]* [MK]bps)",re.MULTILINE)
    mediainfo_filesize_regex = re.compile(r"^File size.*\: (.* .iB|.* Bytes)",re.MULTILINE)
    aucdtect_regex = re.compile(r"^This track looks like (.*) with probability (\d*%)",re.MULTILINE)

def doMP3Checks(mp3guessenc_output):
# do some MP3 quality checks here
    return True
    
def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "{:3.1f} {}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:.1f} {}{}".format(num, 'Yi', suffix)
    
def parse_mp3guessenc_output(mp3guessenc_output):
# parse mp3guessenc output using regex
# return parsed variables as a dictionary
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""
    frame_hist=""
    block_usage=""
    mode_count=""

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
        filesize=format_bytes(int(search.group(1)))
    search = guessenc_frame_hist_regex.search(mp3guessenc_output)
    if search is not None:
        frame_hist=search.group(1)
    search = guessenc_block_usage_regex.search(mp3guessenc_output)
    if search is not None:
        block_usage=search.group(1)
    search = guessenc_mode_count_regex.search(mp3guessenc_output)
    if search is not None:
        mode_count=search.group(1)

    checks_ok = doMP3Checks(mp3guessenc_output)
        
    return {'encoder':encoder, 'audio_format':'MP3', 'bitrate':bitrate ,'encoder_string':encoder_string, 
            'length':length, 'filesize':filesize, 'checks_ok':checks_ok, 'error':False, 'frame_hist':frame_hist, 
            'block_usage':block_usage, 'mode_count':mode_count,'quality':None}

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

    return {'encoder':encoder, 'audio_format':audio_format, 'bitrate':bitrate ,'encoder_string':encoder_string, 
            'length':length, 'filesize':filesize, 'checks_ok':checks_ok, 'error':False, 'quality':None }

def parse_aucdtect_output(aucdtect_output):
    detection = ""
    probability = ""

    search = aucdtect_regex.search(aucdtect_output)
    if search is not None:
        detection=search.group(1)
        probability=search.group(2)

    return {'error':False,'quality':"{} {}".format(detection,probability)}
    
def md5Str(Str):
    return hashlib.md5(Str.encode('utf-8')).hexdigest()
    
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

def aucdtect_Finished(fileinfo):
# callback function
    i = fileinfo[0]
    scanner_output = fileinfo[1]
    filenameStr = fileinfo[2]
    global task_count
    task_count -= 1

    if not (scanner_output == "Error"):
        song_info = parse_aucdtect_output(scanner_output)

        if debug_enabled:
            print("DEBUG: thread finished - row {}, result: {}, task count={}".format(i,song_info['quality'],task_count))
    
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

class FileInfo(QDialog):
    def __init__(self, filenameStr,scanner_output):
        super(FileInfo,self).__init__()
        self.ui = fileinfo_class()
        self.ui.setupUi(self)
        self.setWindowTitle("Info - {}".format(os.path.basename(filenameStr)))
        textEdit_scanner = self.findChild(QTextEdit, "textEdit_scanner")
        textEdit_scanner.setPlainText(scanner_output)


class Options(QDialog):
    def __init__(self):
        super(Options,self).__init__()
        self.ui = options_class()
        self.ui.setupUi(self)
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        lineEdit_filemaskregex.setText(settings.value('Options/FilemaskRegEx',r"\.mp3$|\.flac$|\.mpc$|\.ogg$|\.wav$|\.m4a$|\.aac$|\.ac3$|\.ra$|\.au$"))
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        lineEdit_mediainfo_path.setText(findMediaInfoBin())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        lineEdit_mp3guessenc_path.setText(findGuessEncBin())
        checkBox_recursive = self.findChild(QCheckBox, "checkBox_recursive")
        checkBox_recursive.setChecked(settings.value('Options/RecurseDirectories',True, type=bool))
        checkBox_followsymlinks = self.findChild(QCheckBox, "checkBox_followsymlinks")
        checkBox_followsymlinks.setChecked(settings.value('Options/FollowSymlinks',False, type=bool))
        checkBox_cache = self.findChild(QCheckBox, "checkBox_cache")
        checkBox_cache.setChecked(settings.value('Options/UseCache',True, type=bool))
        checkBox_cacheraw = self.findChild(QCheckBox, "checkBox_cacheraw")
        checkBox_cacheraw.setChecked(settings.value('Options/CacheRawOutput',False, type=bool))
        spinBox_processes = self.findChild(QSpinBox, "spinBox_processes")
        spinBox_processes.setValue(settings.value('Options/Processes',0, type=int))
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        checkBox_debug.setChecked(settings.value("Options/Debug", False, type=bool))
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        checkBox_savewindowstate.setChecked(settings.value("Options/SaveWindowState", True, type=bool))
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        checkBox_clearfilelist.setChecked(settings.value('Options/ClearFilelist',True, type=bool))
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        checkBox_aucdtect_scan.setChecked(settings.value('Options/auCDtect_scan',False, type=bool))
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        horizontalSlider_aucdtect_mode.setValue(settings.value('Options/auCDtect_mode',8, type=int))
    
    def accept(self):
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        settings.setValue('Options/FilemaskRegEx',lineEdit_filemaskregex.text())
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        settings.setValue('Paths/mediainfo_bin',lineEdit_mediainfo_path.text())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        settings.setValue('Paths/mp3guessenc_bin',lineEdit_mp3guessenc_path.text())
        checkBox_recursive = self.findChild(QCheckBox, "checkBox_recursive")
        settings.setValue('Options/RecurseDirectories',checkBox_recursive.isChecked())
        checkBox_followsymlinks = self.findChild(QCheckBox, "checkBox_followsymlinks")
        settings.setValue('Options/FollowSymlinks',checkBox_followsymlinks.isChecked())
        checkBox_cache = self.findChild(QCheckBox, "checkBox_cache")
        settings.setValue('Options/UseCache',checkBox_cache.isChecked())
        checkBox_cacheraw = self.findChild(QCheckBox, "checkBox_cacheraw")
        settings.setValue('Options/CacheRawOutput',checkBox_cacheraw.isChecked())
        spinBox_processes = self.findChild(QSpinBox, "spinBox_processes")
        settings.setValue('Options/Processes',spinBox_processes.value())
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        settings.setValue('Options/Debug',checkBox_debug.isChecked())
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        settings.setValue('Options/SaveWindowState',checkBox_savewindowstate.isChecked())
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        settings.setValue('Options/ClearFilelist',checkBox_clearfilelist.isChecked())
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        settings.setValue('Options/auCDtect_scan',checkBox_aucdtect_scan.isChecked())
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        settings.setValue('Options/auCDtect_mode',horizontalSlider_aucdtect_mode.value())
        QDialog.accept(self)
        
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
        self.ui.actionOptions.triggered.connect(self.edit_Options)
        self.ui.actionAbout.triggered.connect(self.about_Dlg)
            
        fileMenu = self.ui.menubar.addMenu('&File')
        fileMenu.addAction(self.ui.actionFolder_Select)
        fileMenu.addAction(self.ui.actionExit)
        editMenu = self.ui.menubar.addMenu('&Edit')
        editMenu.addAction(self.ui.actionOptions)
        helpMenu = self.ui.menubar.addMenu('&Help')
        helpMenu.addAction(self.ui.actionAbout)

        self.ui.tableWidget.setColumnCount(len(TableHeaders))
        self.ui.tableWidget.setHorizontalHeaderLabels(TableHeaders)
        self.ui.tableWidget.horizontalHeader().resizeSection(headerIndexByName(self.ui.tableWidget,"Filename"),300)
        self.ui.tableWidget.horizontalHeader().setSectionsMovable(True)
        
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.tableContextMenu)
        
        windowState = settings.value("State/windowState")
        windowGeometry = settings.value("State/windowGeometry")
        tableGeometry = settings.value("State/tableGeometry")
        tableHeaderState = settings.value("State/tableHeaderState")
        
        if windowState is not None:
            self.restoreState(windowState)
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        if tableGeometry is not None:
            self.ui.tableWidget.restoreGeometry(tableGeometry)
        if tableHeaderState is not None:
            self.ui.tableWidget.horizontalHeader().restoreState(tableHeaderState)
            self.ui.tableWidget.sortByColumn(-1,Qt.AscendingOrder)
    
    def edit_Options(self):
        dialog = Options()
        result = dialog.exec_()
        dialog.show()

    def tableContextMenu(self, point):
        row = self.ui.tableWidget.rowAt(point.y())
        selected_items = self.ui.tableWidget.selectedItems()
        if not row == -1:
            menu = QMenu(self)
            viewInfoAction = QAction("View Info",menu)
            viewInfoAction.triggered.connect(partial(self.contextViewInfo,row))
            menu.addAction(viewInfoAction)
            rescanFileAction = QAction("Scan File(s)",menu)
            rescanFileAction.triggered.connect(partial(self.contextRescanFile,row,selected_items))
            if task_count > 0:
                rescanFileAction.setEnabled(False)
            menu.addAction(rescanFileAction)
            playFileAction = QAction("Play File",menu)
            playFileAction.triggered.connect(partial(self.contextPlayFile,row))
            menu.addAction(playFileAction)
            browseFolderAction = QAction("Browse Folder",menu)
            browseFolderAction.triggered.connect(partial(self.contextBrowseFolder,row))
            menu.addAction(browseFolderAction)
            menu.popup(self.ui.tableWidget.viewport().mapToGlobal(point))    
    
    def closeEvent(self,event):
        self.cancel_Tasks()
        windowState = self.saveState()
        windowGeometry = self.saveGeometry()
        tableGeometry = self.ui.tableWidget.saveGeometry()
        tableHeaderState = self.ui.tableWidget.horizontalHeader().saveState()
        
        if settings.value("Options/SaveWindowState", True, type=bool):
            settings.setValue("State/windowState",windowState)
            settings.setValue("State/windowGeometry",windowGeometry)
            settings.setValue("State/tableGeometry",tableGeometry)
            settings.setValue("State/tableHeaderState",tableHeaderState)
        
        event.accept()        
    
    def contextRescanFile(self, row,selected_items):
        file_list = []
        for filenameItem in selected_items:
            filenameItem.setData(dataScanned, False)
            file_list.append(filenameItem.data(dataFilenameStr))
        self.scan_Files(True,file_list)
        
    def contextViewInfo(self, row):
        filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
        codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
        dialog = FileInfo(filenameItem.data(dataFilenameStr),codecItem.data(dataRawOutput))
        result = dialog.exec_()
        dialog.show()

    def contextPlayFile(self, row):
        pass

    def contextBrowseFolder(self, row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Folder"))
        folderName = folderItem.toolTip()
        if os.name == 'nt':
            subprocess.Popen("explorer \"" + os.path.normpath(folderName) + "\"")
    
    def select_Folder(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory to Scan", os.path.expanduser("~")))
        
        filemask = settings.value('Options/FilemaskRegEx',r"\.mp3$|\.flac$|\.mpc$|\.ogg$|\.wav$|\.m4a$|\.aac$|\.ac3$|\.ra$|\.au$")
        filemask_regex = re.compile(filemask,re.IGNORECASE)

        followsymlinks = settings.value('Options/FollowSymlinks',False, type=bool)
        recursedirectories = settings.value('Options/RecurseDirectories',True, type=bool)
        clearfilelist = settings.value('Options/ClearFilelist',True, type=bool)
        usecache = settings.value('Options/UseCache',True, type=bool)
        
        if clearfilelist:
            self.clear_List()

        self.ui.tableWidget.setSortingEnabled(False)
        self.ui.tableWidget.setUpdatesEnabled(False)
        self.ui.tableWidget.setContextMenuPolicy(Qt.NoContextMenu)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(0)
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
        
        # walk through directory chosen by user
        # and add filenames to treeview
        i = 0
        for root, dirs, files in os.walk(directory, True, None, followsymlinks):
            if not recursedirectories:
                while len(dirs) > 0:
                    dirs.pop()
            for name in files:
                if filemask_regex.search(name) is not None:
#                    i = self.ui.tableWidget.rowCount()
                    self.ui.tableWidget.insertRow(i)
                    filenameItem = QTableWidgetItem(name)
                    filenameStr = os.path.join(root, name)
                    filenameItem.setToolTip(filenameStr)
                    filenameItem.setData(dataFilenameStr, filenameStr)
                    codecItem = QTableWidgetItem("Not scanned")
                    folderItem = QTableWidgetItem(os.path.basename(root))
                    folderItem.setToolTip(root)
                    bitrateItem = QTableWidgetItem("")
                    lengthItem = QTableWidgetItem("")
                    filesizeItem = QTableWidgetItem("")
                    qualityItem = QTableWidgetItem("")
                    
                    if usecache == True:
                        hashStr = filenameStr + str(os.path.getmtime(filenameStr))
                        filemd5 = md5Str(hashStr)
                        if not filecache.value('{}/Encoder'.format(filemd5)) == None:
                            codecItem.setText(filecache.value('{}/Encoder'.format(filemd5)))
                            bitrateItem.setText(filecache.value('{}/Bitrate'.format(filemd5)))
                            lengthItem.setText(filecache.value('{}/Length'.format(filemd5)))
                            filesizeItem.setText(filecache.value('{}/Filesize'.format(filemd5)))
                            cached_output = filecache.value('{}/RawOutput'.format(filemd5))
                            quality = filecache.value('{}/Quality'.format(filemd5))
                            if quality is not None:
                                qualityItem.setText(quality)
                            if cached_output is not None:
                                scanner_output = zlib.decompress(cached_output)
                                codecItem.setData(dataRawOutput,scanner_output.decode('utf-8'))

                            filenameItem.setData(dataScanned, True) # previously scanned
                    
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Filename"), filenameItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Folder"), folderItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Encoder"), codecItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Bitrate"), bitrateItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Length"), lengthItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Filesize"), filesizeItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Quality"), qualityItem)
                                                      
                    self.statusBar().showMessage("Scanning for files: {} found".format(i))
                    
                    i += 1
                    QApplication.processEvents()

        self.ui.tableWidget.setUpdatesEnabled(True)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        self.statusBar().showMessage('Ready')
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
        self.ui.actionFolder_Select.setEnabled(True)
                    
    def cancel_Tasks(self):
        if task_count > 0: # tasks are running
            global stop_tasks
            stop_tasks = True
    
    def scan_Files(self,checked,filelist=None):
    # loop through table and queue scanner processes for all files
    # filelist - optional list of files to scan, all others will be skipped
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
        
        numproc = settings.value('Options/Processes',0, type=int) # number of scanner processes to run, default = # of cpus
        if numproc <= 0:
            numproc = None
        pool = Pool(processes=numproc)
        
        self.ui.tableWidget.setSortingEnabled(False) # prevent row numbers changing
        self.ui.tableWidget.setUpdatesEnabled(True)
        
        mp3guessencbin = findGuessEncBin()
        if (mp3guessencbin == "") or (not os.path.exists(mp3guessencbin)):
            mp3guessencbin = ""

        mediainfo_bin = findMediaInfoBin()
        if (mediainfo_bin == "") or (not os.path.exists(mediainfo_bin)):
            mediainfo_bin = ""

        aucdtect_bin = findauCDtectBin()
        if (aucdtect_bin == "") or (not os.path.exists(aucdtect_bin)):
            aucdtect_bin = ""
            
        flac_bin = findFlacBin()
        if (flac_bin == "") or (not os.path.exists(flac_bin)):
            flac_bin = ""

        global task_count
        task_count = 0 # tasks remaining
        global task_total
        task_total = 0 # total tasks - used to calculate percentage remaining
        
        for i in range(0,self.ui.tableWidget.rowCount()):
            filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
            filenameStr = filenameItem.data(dataFilenameStr) # filename
            
            if filelist is not None:
                if filelist.count(filenameStr) == 0:
                    continue
            
            fileScanned = filenameItem.data(dataScanned) # boolean, true if file already scanned
            
            if not fileScanned:
#                codecItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Encoder"))
#                codecItem.setText("Scanning...")
            
                if debug_enabled:
                    print("DEBUG: About to run process for file {}".format(filenameStr))

                if fnmatch.fnmatch(filenameStr, "*.mp3") and not mp3guessencbin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mp3guessencbin,"-e",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                    task_total += 1
                elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"-",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                    task_total += 1
                elif not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"-",debug_enabled), callback=scanner_Finished) # queue processes
                    task_count += 1
                    task_total += 1

                if fnmatch.fnmatch(filenameStr, "*.flac"):
                    if settings.value('Options/auCDtect_scan',False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = settings.value('Options/auCDtect_mode',10, type=int)
                            pool.apply_async(aucdtect_Thread, args=(i,filenameStr,flac_bin,"-df",aucdtect_bin,"-m{}".format(aucdtect_mode),debug_enabled), callback=aucdtect_Finished) # queue processes
                            task_count += 1
                            task_total += 1
                    
            QApplication.processEvents()
            
        pool.close()

        def update_Table(row,song_info,scanner_output):
        # update table with info from scanner
            error_status = song_info['error']
            if not error_status:
                quality = song_info['quality']
                if quality is not None:
                    # aucdtect
                    qualityItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Quality"))
                    qualityItem.setText(quality)
                    if settings.value('Options/UseCache',True, type=bool) == True:
                        filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
                        filenameStr = filenameItem.data(dataFilenameStr)
                        hashStr = filenameStr + str(os.path.getmtime(filenameStr))
                        filemd5 = md5Str(hashStr)
                        filecache.setValue('{}/Quality'.format(filemd5),qualityItem.text())
                else:
                    filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
                    filenameItem.setData(dataScanned, True) # boolean, true if file already scanned
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
                
                    codecItem.setData(dataRawOutput,scanner_output)
                    bitrateItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Bitrate"))
                    bitrateItem.setText(song_info['bitrate'])
                    lengthItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Length"))
                    lengthItem.setText(song_info['length'])
                    filesizeItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filesize"))
                    filesizeItem.setText(song_info['filesize'])

                    if settings.value('Options/UseCache',True, type=bool) == True:
                        filenameStr = filenameItem.data(dataFilenameStr)
                        hashStr = filenameStr + str(os.path.getmtime(filenameStr))
                        filemd5 = md5Str(hashStr)
                        filecache.setValue('{}/Encoder'.format(filemd5),codecItem.text())
                        filecache.setValue('{}/Bitrate'.format(filemd5),bitrateItem.text())
                        filecache.setValue('{}/Length'.format(filemd5),lengthItem.text())
                        filecache.setValue('{}/Filesize'.format(filemd5),filesizeItem.text())
                        if settings.value('Options/CacheRawOutput',False, type=bool) == True:
                            filecache.setValue('{}/RawOutput'.format(filemd5),zlib.compress(scanner_output.encode('utf-8')))

            else:
                codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
                codecItem.setText("error scanning file")
                codecItem.setData(dataRawOutput,scanner_output)
            
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
        task_count = 0
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
        self.ui.actionFolder_Select.setEnabled(True)
        self.ui.tableWidget.setSortingEnabled(True)
            
    def clear_List(self):
        self.ui.progressBar.setValue(0)
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def about_Dlg(self):
        QMessageBox.about(self, "About",
                                """Specton Audio Analyser
                                
Copyright (C) 2016 D. Bird <somesortoferror@gmail.com>
https://github.com/somesortoferror/specton

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""
                                )
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
