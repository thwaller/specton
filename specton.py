#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

'''
    Specton Audio Analyser
    Copyright (C) 2016-17 David Bird <somesortoferror@gmail.com>
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
    along with this program.  If not, see <http://www.gnu.org/licenses/>. 
'''

import fnmatch
import os
import queue
import re
import string
import sys
from functools import partial
from io import TextIOWrapper
from time import sleep, ctime, asctime, gmtime, strftime, time

from PyQt5.QtCore import Qt, QSettings, QTimer, QThreadPool, QRunnable, QMutex, QReadLocker, QWriteLocker, QReadWriteLock, QEvent, QObject
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import QWidget, QApplication, QDialog, QDialogButtonBox,QMainWindow, QAction, QFileDialog, QTableWidgetItem, QMessageBox, QMenu, QLineEdit,QCheckBox,QSpinBox,QSlider,QTextEdit,QTabWidget,QLabel,QGridLayout,QPushButton
from dlg_info import Ui_FileInfoDialog
from dlg_main import Ui_MainWindow
from dlg_options import Ui_optionsDialog
from spct_downloader import DownloaderDlg
from spct_utils import settings, filecache
from spct_utils import *
from spct_defs import *
from spct_threads import *
from spct_parsers import *
from spct_objects import infoobj,main_info,song_info_obj

scan_start_time = time()
    
frozen = bool(getattr(sys, 'frozen', False))
                
if os.name == 'nt': # various hacks

    stderr_fn = os.path.join(app_dirs.user_log_dir,"stderr.log")
    stdout_fn = os.path.join(app_dirs.user_log_dir,"stdout.log")

    try:
        os.remove(stderr_fn)
        os.remove(stdout_fn)
    except OSError:
        pass

    if not frozen:
        if sys.stdout is not None:
            sys.stdout = TextIOWrapper(sys.stdout.buffer,sys.stdout.encoding,'backslashreplace') # fix for printing utf8 strings on windows
        else:
            # win32gui doesn't have a console
            debug_log("Redirecting stdout/err to file...")
            sys.stdout = open(stdout_fn, "w");
            sys.stderr = open(stderr_fn, "w")
    else: # frozen
        debug_log("Redirecting stdout/err to file...(Frozen)")
        sys.stdout = open(stdout_fn, "w");
        sys.stderr = open(stderr_fn, "w")
        

if __name__ == '__main__':
    main_q = queue.Queue()
    infodlg_q = queue.Queue()
    infodlg_list = set() # list of dialog windows
    infodlg_threadpool = QThreadPool(None)
    scanner_threadpool = QThreadPool(None)
    TableHeaders = ("Folder","Filename","Length","Bitrate","Mode","Frequency","Filesize","Errors","Hash","Encoder","Quality")
    ql = QReadWriteLock()
    task_count = 0
    task_total = 0
    file_hashlist = set()
        
    debug_enabled = settings.value("Options/Debug", False, type=bool)
  
            
def headerIndexByName(table,headerName):
    ''' find column in tablewidget from headerName '''
    for i in range(0, table.columnCount()):
        if table.horizontalHeaderItem(i).text() == headerName:
            return i
    return -1

def getTableHeaders(table):
    header_list = []
    for i in range(0, table.columnCount()):
        header_list.append(table.horizontalHeaderItem(i).text())
    return header_list

def checkPrereq(self):    
    mi_bin = findMediaInfoBin()
    if not os.path.exists(mi_bin):
        if not os.name == 'nt': pass # downloader currently only implemented for windows
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("Some required tools are not found. Do you want to download them now?")
        msg.setWindowTitle("Specton")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        if retval == QMessageBox.Yes:
            dlg = DownloaderDlg()
            dlg.exec()
    
class FileInfo(QDialog):
# right click file info dialog
    def __init__(self,filenameStr,frame_hist):
        super(FileInfo,self).__init__()
        self.ui = Ui_FileInfoDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Info - {}".format(os.path.basename(filenameStr)))
        self.filename = filenameStr
        self.frame_hist = frame_hist # tuple
        infodlg_list.add(self) # keep track of dialogs so we can reuse them if still open
        
        windowGeometry = settings.value("State/InfoWindowGeometry")
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        tabWidget.clear()

        try:
            if self.frame_hist is not None:
                x,y = self.frame_hist
            else:
                x = []
                y = []
        except:
            x = []
            y = []
            
        if debug_enabled:
            debug_log("Frame histogram - {}".format(self.frame_hist))
            debug_log("Frame histogram - {}".format(x))
            debug_log("Frame histogram - {}".format(y))
        if len(x) > 0:
            try:
                if debug_enabled:
                    debug_log("Running gnuplot to create frame histogram for file {}".format(filenameStr))

                tab = QWidget()
                grid = QGridLayout(tab)
                grid.setObjectName("BitrateHistLayout-{}".format(md5Str(filenameStr)))
                tabWidget.addTab(tab,"Bitrate Distribution")

                thread = makeBitHistThread(filenameStr,grid.objectName(),settings.value("Options/Proc_Timeout",300, type=int),infodlg_q,findGnuPlotBin(),x,y)
                infodlg_threadpool.start(thread)

            except Exception as e:
                debug_log(e)
                
        updateGuiTimer = QTimer(self)
        updateGuiTimer.timeout.connect(self.updateGui)
        updateGuiTimer.setInterval(100)
        updateGuiTimer.start()
        
        if debug_enabled:
            debug_log("Running scanner for file {}".format(filenameStr))
        
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setObjectName("OutputLayout-{}".format(md5Str(filenameStr)))
        tabWidget.addTab(tab,"Scanner Output")
        
        mp3guessenc_bin = findGuessEncBin()
        if (mp3guessenc_bin == "") or (not os.path.exists(mp3guessenc_bin)):
            mp3guessenc_bin = ""

        mediainfo_bin = findMediaInfoBin()
        if (mediainfo_bin == "") or (not os.path.exists(mediainfo_bin)):
            mediainfo_bin = ""
        
        thread = getScannerThread(grid.objectName(),filenameStr,mp3guessenc_bin,mediainfo_bin,grid,settings.value("Options/Proc_Timeout",300, type=int))
        if thread is not None:
            infodlg_threadpool.start(thread)
                
        if settings.value('Options/EnableSpectrogram',True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("SpectrogramLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab,"Spectrogram")

            sox_bin = findSoxBin()
            temp_file = getTempFileName() + ".png"
            palette = settings.value('Options/SpectrogramPalette',1, type=int)
            
            if debug_enabled:
                debug_log("Running sox to create spectrogram for file {}".format(filenameStr))

            thread = makeSpectrogramThread(filenameStr,sox_bin,temp_file,palette,grid.objectName(),settings.value("Options/Proc_Timeout",300, type=int),infodlg_q)
            infodlg_threadpool.start(thread)
            
        if settings.value('Options/EnableBitGraph',True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("BitgraphLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab,"Bitrate Graph")
            if debug_enabled:
                debug_log("Running ffprobe to create bitrate graph for file {}".format(filenameStr))
            thread = makeBitGraphThread(filenameStr,grid.objectName(),findffprobeBin(),settings.value("Options/Proc_Timeout",300, type=int),infodlg_q,findGnuPlotBin())
            infodlg_threadpool.start(thread)
               
         
    def updateGui(self):
        ''' called from timer - subprocesses post to queue when finished '''
        if not infodlg_q.empty():
            update_info = infodlg_q.get(False,1)
            # class infoobj
            # type - type of update e.g. "Spectrogram"
            # data - handler specific data
            # layout - QLayout to update
            # fn - name of file the update is for

            if not isinstance(update_info, infoobj):
                debug_log("updateGui received wrong data: {}".format(update_info))
                return
            
            if update_info.type in ["Spectrogram", "BitGraph", "BitHist"]:
                if debug_enabled:
                    debug_log("updateGui received {} update".format(update_info.type))
                px = QLabel()
                dlg = findDlg(update_info.fn)
                if dlg is not None:
                    layout = dlg.findChild(QGridLayout,update_info.layout)
                    if layout is not None:
                        layout.addWidget(px)
                        px.setPixmap(QPixmap(update_info.data))
                    else:
                        debug_log("updateGui ran but layout not found type={} str={} layout={}".format(update_info.type,update_info.data,update_info.layout))
                else:
                    debug_log("updateGui couldn't find dlg type={} str={} layout={}".format(update_info.type,update_info.data,update_info.layout))                    
                try:
                    os.remove(update_info.data) # delete generated spectrogram image
                except:
                    pass

            elif update_info.type == "Scanner_Output":
                if debug_enabled:
                    debug_log("updateGui received Scanner_Output update")
                if update_info.layout is not None:
                    textEdit_scanner = QTextEdit()
                    textEdit_scanner.setReadOnly(True)
                    textEdit_scanner.setPlainText(update_info.data)
                    update_info.layout.addWidget(textEdit_scanner)

                        
    def closeEvent(self,event):
        windowGeometry = self.saveGeometry()
        
        if settings.value("Options/SaveWindowState", True, type=bool):
            settings.setValue("State/InfoWindowGeometry",windowGeometry)
        
        infodlg_list.remove(self)
        event.accept()

def findDlg(searchname):
    if debug_enabled:
        debug_log("findDlg called list: {} search: {}".format(infodlg_list,searchname))
    for obj in infodlg_list:
        if obj.filename == searchname:
            if debug_enabled:
                debug_log("findDlg dialog found: {} filename: {}".format(obj,searchname))
            return obj
            
                
class Options(QDialog):
    def __init__(self):
        super(Options,self).__init__()
        self.ui = Ui_optionsDialog()
        self.ui.setupUi(self)
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        filemask_regex = settings.value('Options/FilemaskRegEx',defaultfilemask)
        if not filemask_regex == "":
            lineEdit_filemaskregex.setText(filemask_regex)
        else:
            lineEdit_filemaskregex.setText(defaultfilemask)
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        lineEdit_mediainfo_path.setText(findMediaInfoBin())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        lineEdit_mp3guessenc_path.setText(findGuessEncBin())
        lineEdit_sox_path = self.findChild(QLineEdit, "lineEdit_sox_path")
        lineEdit_sox_path.setText(findSoxBin())
        lineEdit_ffprobe_path = self.findChild(QLineEdit, "lineEdit_ffprobe_path")
        lineEdit_ffprobe_path.setText(findffprobeBin())
        lineEdit_aucdtect_path = self.findChild(QLineEdit, "lineEdit_aucdtect_path")
        lineEdit_aucdtect_path.setText(findauCDtectBin())
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
        spinBox_spectrogram_palette = self.findChild(QSpinBox, "spinBox_spectrogram_palette")
        spinBox_spectrogram_palette.setValue(settings.value('Options/SpectrogramPalette',1, type=int))
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        checkBox_debug.setChecked(settings.value("Options/Debug", False, type=bool))
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        checkBox_savewindowstate.setChecked(settings.value("Options/SaveWindowState", True, type=bool))
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        checkBox_clearfilelist.setChecked(settings.value('Options/ClearFilelist',True, type=bool))
        checkBox_spectrogram = self.findChild(QCheckBox, "checkBox_spectrogram")
        checkBox_spectrogram.setChecked(settings.value('Options/EnableSpectrogram',True, type=bool))
        checkBox_bitrate_graph = self.findChild(QCheckBox, "checkBox_bitrate_graph")
        checkBox_bitrate_graph.setChecked(settings.value('Options/EnableBitGraph',True, type=bool))
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        checkBox_aucdtect_scan.setChecked(settings.value('Options/auCDtect_scan',False, type=bool))
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        horizontalSlider_aucdtect_mode.setValue(settings.value('Options/auCDtect_mode',8, type=int))
        
        pushButton_mediainfo_path = self.findChild(QPushButton, "pushButton_mediainfo_path")
        pushButton_mediainfo_path.clicked.connect(self.choosePathButton)
        pushButton_mp3guessenc_path = self.findChild(QPushButton, "pushButton_mp3guessenc_path")
        pushButton_mp3guessenc_path.clicked.connect(self.choosePathButton)
        pushButton_sox_path = self.findChild(QPushButton, "pushButton_sox_path")
        pushButton_sox_path.clicked.connect(self.choosePathButton)
        pushButton_ffprobe_path = self.findChild(QPushButton, "pushButton_ffprobe_path")
        pushButton_ffprobe_path.clicked.connect(self.choosePathButton)
        pushButton_aucdtect_path = self.findChild(QPushButton, "pushButton_aucdtect_path")
        pushButton_aucdtect_path.clicked.connect(self.choosePathButton)        
        buttonBox = self.findChild(QDialogButtonBox, "buttonBox")
        buttonBox.button(QDialogButtonBox.Save).clicked.connect(self.saveSettings)
        buttonBox.button(QDialogButtonBox.Discard).clicked.connect(self.close)
        
    def choosePathButton(self):
        sender = self.sender()
        if sender.objectName() == "pushButton_mediainfo_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
            exe_name = "mediainfo"
        elif sender.objectName() == "pushButton_mp3guessenc_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
            exe_name = "mp3guessenc"
        elif sender.objectName() == "pushButton_sox_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_sox_path")
            exe_name = "sox"
        elif sender.objectName() == "pushButton_ffprobe_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_ffprobe_path")
            exe_name = "ffprobe"
        elif sender.objectName() == "pushButton_aucdtect_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_aucdtect_path")
            exe_name = "aucdtect"
        if lineEdit is not None:
            path = lineEdit.text()
            file = str(QFileDialog.getOpenFileName(parent=self,caption="Browse to {} executable file".format(exe_name),directory=path)[0])
            if not file == "":
                lineEdit.setText(file)
        
    def saveSettings(self):
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        settings.setValue('Options/FilemaskRegEx',lineEdit_filemaskregex.text())
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        settings.setValue('Paths/mediainfo_bin',lineEdit_mediainfo_path.text())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        settings.setValue('Paths/mp3guessenc_bin',lineEdit_mp3guessenc_path.text())
        lineEdit_aucdtect_path = self.findChild(QLineEdit, "lineEdit_aucdtect_path")
        settings.setValue('Paths/aucdtect_bin',lineEdit_aucdtect_path.text())
        lineEdit_sox_path = self.findChild(QLineEdit, "lineEdit_sox_path")
        settings.setValue('Paths/sox_bin',lineEdit_sox_path.text())
        lineEdit_ffprobe_path = self.findChild(QLineEdit, "lineEdit_ffprobe_path")
        settings.setValue('Paths/ffprobe_bin',lineEdit_ffprobe_path.text())
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
        spinBox_spectrogram_palette = self.findChild(QSpinBox, "spinBox_spectrogram_palette")
        settings.setValue('Options/SpectrogramPalette',spinBox_spectrogram_palette.value())
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        settings.setValue('Options/Debug',checkBox_debug.isChecked())
        global debug_enabled
        debug_enabled = checkBox_debug.isChecked()
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        settings.setValue('Options/SaveWindowState',checkBox_savewindowstate.isChecked())
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        settings.setValue('Options/ClearFilelist',checkBox_clearfilelist.isChecked())
        checkBox_spectrogram = self.findChild(QCheckBox, "checkBox_spectrogram")
        settings.setValue('Options/EnableSpectrogram',checkBox_spectrogram.isChecked())
        checkBox_bitrate_graph = self.findChild(QCheckBox, "checkBox_bitrate_graph")
        settings.setValue('Options/EnableBitGraph',checkBox_bitrate_graph.isChecked())
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        settings.setValue('Options/auCDtect_scan',checkBox_aucdtect_scan.isChecked())
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        settings.setValue('Options/auCDtect_mode',horizontalSlider_aucdtect_mode.value())
        self.close()
        
def getScannerThread(i,filenameStr,mp3guessenc_bin,mediainfo_bin,fileinfo_dialog_update=None,cmd_timeout=300):
    thread = None    
    if fnmatch.fnmatch(filenameStr, "*.mp3"):
        # use mp3guessenc if available
        if not mp3guessenc_bin == "":
            thread = scanner_Thread(i,filenameStr,mp3guessenc_bin,"mp3guessenc","-e",debug_enabled,infodlg_q,main_q,fileinfo_dialog_update,cmd_timeout)
        elif not mediainfo_bin == "": # fall back to mediainfo
            thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,infodlg_q,main_q,fileinfo_dialog_update,cmd_timeout)
                        
    elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
        thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,infodlg_q,main_q,fileinfo_dialog_update,cmd_timeout)
    elif not mediainfo_bin == "": # default for all files is mediainfo
        thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,infodlg_q,main_q,fileinfo_dialog_update,cmd_timeout)
    return thread
    
class Main(QMainWindow):
    def __init__(self):
        super(Main, self).__init__()

        # build ui
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.actionExit.triggered.connect(sys.exit)
        self.ui.actionExit.setText("E&xit")
        self.ui.actionScan_Files.triggered.connect(self.scan_Files)
        self.ui.actionFolder_Select.triggered.connect(self.select_folder_click)
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.clicked.connect(self.ui.actionScan_Files.trigger)        
        scanButton.setIcon(self.ui.actionScan_Files.icon())
        self.ui.actionFolder_Select.setText("Select F&older")
        self.ui.actionClear_Filelist.triggered.connect(self.clear_List)
        self.ui.actionStop.triggered.connect(self.cancel_Tasks)
        self.ui.actionOptions.triggered.connect(self.edit_Options)
        self.ui.actionOptions.setText("&Options")
        self.ui.actionAbout.triggered.connect(self.about_Dlg)
        self.ui.actionAbout.setText("&About")
        self.ui.actionViewConfigDir.triggered.connect(self.viewConfigDir)
        self.ui.actionViewConfigDir.setText("&Config files")
        self.ui.actionViewLogDir.triggered.connect(self.viewLogDir)
        self.ui.actionViewLogDir.setText("&Logs")
        self.ui.actionTools_Downloader.setText("&Tools downloader")
        self.ui.actionTools_Downloader.triggered.connect(self.tools_downloader)
            
        fileMenu = self.ui.menubar.addMenu('&File')
        fileMenu.addAction(self.ui.actionFolder_Select)
        fileMenu.addAction(self.ui.actionExit)
        editMenu = self.ui.menubar.addMenu('&Edit')
        editMenu.addAction(self.ui.actionOptions)
        viewMenu = self.ui.menubar.addMenu('&View')
        viewMenu.addAction(self.ui.actionViewConfigDir)
        viewMenu.addAction(self.ui.actionViewLogDir)
        viewMenu.addAction(self.ui.actionTools_Downloader)
        helpMenu = self.ui.menubar.addMenu('&Help')
        helpMenu.addAction(self.ui.actionAbout)

        self.ui.tableWidget.setColumnCount(len(TableHeaders))
        self.ui.tableWidget.setHorizontalHeaderLabels(TableHeaders)
        self.ui.tableWidget.horizontalHeader().resizeSection(headerIndexByName(self.ui.tableWidget,"Filename"),300)
        self.ui.tableWidget.horizontalHeader().setSectionsMovable(True)
        self.ui.tableWidget.installEventFilter(self)
        
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
            
        updateMainGuiTimer = QTimer(self) # this timer watches main_q and updates tablewidget with scanner results
        updateMainGuiTimer.timeout.connect(self.updateMainGui)
        updateMainGuiTimer.setInterval(500)
        updateMainGuiTimer.start()
        
    def eventFilter(self, object, event):
        if object is self.ui.tableWidget:
            # handle file/folder drag & drop
            if (event.type() == QEvent.DragEnter):
                if event.mimeData().hasUrls():
                    event.accept()
                else:
                    event.ignore()
                return True
            if (event.type() == QEvent.Drop):
                if event.mimeData().hasUrls():
                    links = []
                    for url in event.mimeData().urls():
                        links.append(str(url.toLocalFile()))
                    self.addFilesFolders(filedirlist=links,clearfilelist=False)
                    event.accept()
                else:
                    event.ignore()
                return True
            return False
                    
    def edit_Options(self):
        dialog = Options()
        result = dialog.exec_()

    def viewLogDir(self):
        openFolder(app_dirs.user_log_dir)
        
    def viewConfigDir(self):
        openFolder(os.path.dirname(settings.fileName()))
        
    def tools_downloader(self):
        dlg = DownloaderDlg()
        dlg.exec()
        
    
    def tableContextMenu(self, point):
        row = self.ui.tableWidget.rowAt(point.y())
        selected_items = self.ui.tableWidget.selectedItems()
        if not row == -1:
            menu = QMenu(self)
            viewInfoAction = QAction("View &Info",menu)
            viewInfoAction.triggered.connect(partial(self.contextViewInfo,row))
            menu.addAction(viewInfoAction)
            rescanFileAction = QAction("&Scan File(s)",menu)
            rescanFileAction.triggered.connect(partial(self.contextRescanFile,row,selected_items))
            if task_count > 0:
                rescanFileAction.setEnabled(False)
            scanFolderAction = QAction("Scan &Folder",menu)
            scanFolderAction.triggered.connect(partial(self.contextScanFolder,row))
            if task_count > 0:
                scanFolderAction.setEnabled(False)
            menu.addAction(rescanFileAction)
            menu.addAction(scanFolderAction)
            playFileAction = QAction("&Play File",menu)
            playFileAction.triggered.connect(partial(self.contextPlayFile,row))
            menu.addAction(playFileAction)
            browseFolderAction = QAction("&Browse Folder",menu)
            browseFolderAction.triggered.connect(partial(self.contextBrowseFolder,row))
            menu.addAction(browseFolderAction)
            writeReportAction = QAction("Write &Report (Folder)",menu)
            writeReportAction.triggered.connect(partial(self.contextWriteReport,row))
            menu.addAction(writeReportAction)
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
    
    def contextWriteReport(self,row,silent=False):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Folder"))
        report_dir = folderItem.toolTip()
        report_dir_displayname = folderItem.text()
        file_list = []
        for i in range(0,self.ui.tableWidget.rowCount()):
            folderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Folder"))
            dir = folderItem.toolTip()
            if report_dir == dir:
                filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
                filenameStr = filenameItem.data(dataFilenameStr)
                modified_date = strftime("%d/%m/%Y %H:%M:%S UTC",gmtime(os.path.getmtime(filenameStr)))
                codecItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Encoder"))
                bitrateItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Bitrate"))
                lengthItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Length"))
                filesizeItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filesize"))
                qualityItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Quality"))
                frequencyItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Frequency"))
                modeItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Mode"))
                file_list.append([filenameItem.text(),lengthItem.text(),filesizeItem.text(),bitrateItem.text(),
                                    modeItem.text(),frequencyItem.text(),codecItem.text(),qualityItem.text(),modified_date])
        
        with open(report_dir + "/specton.log","w") as report_file:
            report_file.write("Report for folder: {}\n".format(report_dir_displayname))
            report_file.write("Generated by Specton Audio Analyser v{} (https://github.com/somesortoferror/specton) on {}\n\n".format(version,asctime()))
            report_file.write("------------------------------------------------------------------------------------------\n")
            report_file.write("{:<50}{:<28}{:<15}{:<15}{:<14}{:<25}{}\n".format("Filename","Last Modified Date","Duration","Filesize","Frequency","Bitrate/Mode","Encoder/Quality"))
            for file_details in file_list:
                report_file.write("{:<50.49}{:<28}{:<15}{:<15}{:<14}{:<10} {:<14}{}  {}\n".format(file_details[0],
                                              file_details[8],
                                              file_details[1],
                                              file_details[2],
                                              file_details[5],
                                              file_details[3],
                                              file_details[4],
                                              file_details[6],
                                              file_details[7]))
            report_file.write("------------------------------------------------------------------------------------------\n")
            
        if not silent:
            self.statusBar().showMessage("Report generated for folder {}".format(report_dir_displayname))
        
        
    def contextRescanFile(self,row,selected_items):
        file_list = set()
        for filenameItem in selected_items:
            filenameItem.setData(dataScanned, False)
            file_list.add(filenameItem.data(dataFilenameStr))
        self.scan_Files(True,file_list)

    def contextScanFolder(self,row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Folder"))
        scan_dir = folderItem.toolTip()
        file_list = set()
        for i in range(0,self.ui.tableWidget.rowCount()):
            folderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Folder"))
            dir = folderItem.toolTip()
            if scan_dir == dir:
                filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
                file_list.add(filenameItem.data(dataFilenameStr))
        self.scan_Files(True,file_list)
                         
        
    def contextViewInfo(self, row):
        filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
        codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
        bitrateItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Bitrate"))
        filenameStr = filenameItem.data(dataFilenameStr)
        dlg = findDlg(filenameStr)
        if dlg is None:
            if debug_enabled:
                debug_log("contextViewInfo: dialog was None")
            dlg = FileInfo(filenameStr,bitrateItem.data(dataBitrate))
            if debug_enabled:
                debug_log(dlg.objectName())
            dlg.show()
        else:
            dlg.showNormal()
            dlg.activateWindow()

    def contextPlayFile(self, row):
        pass

    def contextBrowseFolder(self, row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Folder"))
        folderName = folderItem.toolTip()
        if os.name == 'nt':
            subprocess.Popen("explorer \"" + os.path.normpath(folderName) + "\"")
    
    def addTableWidgetItem(self,row,name,dir,usecache,tableheaders):
        filenameStr = os.path.join(dir, name)
        hashStr = filenameStr.replace("/", "\\") + str(os.path.getmtime(filenameStr)) # use mtime so hash changes if file changed
        filemd5 = md5Str(hashStr)
        
        if filemd5 in file_hashlist:
            return # don't add same file twice
        
        file_hashlist.add(filemd5)

        filenameItem = QTableWidgetItem(name)
        filenameItem.setToolTip(filenameStr)
        filenameItem.setData(dataFilenameStr, filenameStr)
        codecItem = QTableWidgetItem("Not scanned")
        folderItem = QTableWidgetItem(os.path.basename(dir))
        folderItem.setToolTip(dir)
        bitrateItem = QTableWidgetItem("")
        lengthItem = QTableWidgetItem("")
        filesizeItem = QTableWidgetItem("")
        qualityItem = QTableWidgetItem("")
        frequencyItem = QTableWidgetItem("")
        modeItem = QTableWidgetItem("")
        errorItem = QTableWidgetItem("")
        
        if usecache:
            if filecache.value('{}/Encoder'.format(filemd5)) is not None:
                codecItem.setText(filecache.value('{}/Encoder'.format(filemd5)))
                bitrateItem.setText(filecache.value('{}/Bitrate'.format(filemd5)))
                lengthItem.setText(filecache.value('{}/Length'.format(filemd5)))
                filesizeItem.setText(filecache.value('{}/Filesize'.format(filemd5)))
                frame_hist = filecache.value('{}/FrameHist'.format(filemd5))
                if frame_hist is not None:
                    bitrateItem.setData(dataBitrate,frame_hist)
                quality = filecache.value('{}/Quality'.format(filemd5))
                if quality is not None:
                    qualityItem.setText(quality)
                frequency = filecache.value('{}/Frequency'.format(filemd5))
                if frequency is not None:
                    frequencyItem.setText(frequency)
                mode = filecache.value('{}/Mode'.format(filemd5))
                if mode is not None:
                    modeItem.setText(mode)
                quality_colour = filecache.value('{}/QualityColour'.format(filemd5))
                if quality_colour is not None:
                    qualityItem.setBackground(quality_colour)
                error_colour = filecache.value('{}/ErrorColour'.format(filemd5))
                if error_colour is not None:
                    errorItem.setBackground(error_colour)

                filenameItem.setData(dataScanned, True) # previously scanned
        
        self.ui.tableWidget.insertRow(row)
        self.ui.tableWidget.setItem(row, tableheaders.index("Filename"), filenameItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Folder"), folderItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Encoder"), codecItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Bitrate"), bitrateItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Length"), lengthItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Filesize"), filesizeItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Quality"), qualityItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Errors"), errorItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Frequency"), frequencyItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Mode"), modeItem)    
    
    def recursiveAdd(self,directory,filemask_regex,followsymlinks=False,recursedirectories=True,usecache=True,tableheaders=[]):
        ''' walk through directory and add filenames to treeview'''
        i = 0
        c = 0
        scan_start = time()
        for root, dirs, files in os.walk(directory, True, None, followsymlinks):
            c += 1
            if c % 2 == 0:
                QApplication.processEvents()
                if (i > 0) and (i % 10 == 0): # update count every 10 files
                    self.statusBar().showMessage("Scanning for files: {} found ({} files/s)".format(i, round(i/(time()-scan_start))))
            if not recursedirectories:
                while len(dirs) > 0:
                    dirs.pop()
            for name in sorted(files):
                if filemask_regex.search(name) is not None:
                    self.addTableWidgetItem(i,name,root,usecache,tableheaders)
                    i += 1
        
    def select_folder_click(self, checked):
        clearfilelist = settings.value('Options/ClearFilelist',True, type=bool)
        self.addFilesFolders([],clearfilelist)
        
    def addFilesFolders(self,filedirlist=[],clearfilelist=True):
        
        if filedirlist == []:
            select = str(QFileDialog.getExistingDirectory(self, "Select Directory to Scan", os.path.expanduser("~")))
            if not select == "":
                filedirlist.append(select)
            else:
                return
                
        filemask = settings.value('Options/FilemaskRegEx',defaultfilemask)
        
        try:
            filemask_regex = re.compile(filemask,re.IGNORECASE)
        except re.error as e:
            debug_log("Error in filemask regex: {}, using default".format(e))
            filemask_regex = re.compile(defaultfilemask,re.IGNORECASE)
            
        followsymlinks = settings.value('Options/FollowSymlinks',False, type=bool)
        recursedirectories = settings.value('Options/RecurseDirectories',True, type=bool)
        if clearfilelist is None:
            clearfilelist = settings.value('Options/ClearFilelist',True, type=bool)
        usecache = settings.value('Options/UseCache',True, type=bool)
    
        if clearfilelist:
            self.clear_List()

        self.ui.tableWidget.setSortingEnabled(False)
        self.ui.tableWidget.setUpdatesEnabled(False)
        self.ui.tableWidget.setContextMenuPolicy(Qt.NoContextMenu)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(0)
        self.disableScanning()

        tableheaders = getTableHeaders(self.ui.tableWidget)
        
        for filedir in filedirlist:
            if os.path.isdir(filedir):
                self.recursiveAdd(directory=filedir,filemask_regex=filemask_regex,followsymlinks=followsymlinks,recursedirectories=recursedirectories,usecache=usecache,tableheaders=tableheaders)
            else:
                self.addTableWidgetItem(0,os.path.basename(filedir),os.path.dirname(filedir),usecache,tableheaders)
                        
        self.ui.tableWidget.setUpdatesEnabled(True)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        self.statusBar().showMessage('Ready')
        self.enableScanning()
                    
    def cancel_Tasks(self):
        global task_count
        with QWriteLocker(ql):
            if task_count > 0: # tasks are running
                scanner_threadpool.clear()
                task_count = scanner_threadpool.activeThreadCount()
 
    def update_Table(self,row,song_info):
            ''' update table with info from scanner '''
            if not isinstance(song_info, song_info_obj):
                debug_log("update_Table received wrong data: {}".format(song_info))
                return
            
            if debug_enabled:
                debug_log("update_Table received song_info: {}".format(vars(song_info)))
            
            usecache = settings.value('Options/UseCache',True, type=bool)
            table_headers = getTableHeaders(self.ui.tableWidget)
                            
            if song_info.error:
                if debug_enabled:
                    debug_log("Setting error status for row {}".format(row))
                errorItem = self.ui.tableWidget.item(row, table_headers.index("Errors"))
                errorItem.setBackground(colourQualityBad)
                return

            filenameItem = self.ui.tableWidget.item(row, table_headers.index("Filename"))
            filenameStr = filenameItem.data(dataFilenameStr)
            if usecache:
                hashStr = filenameStr.replace("/", "\\") + str(os.path.getmtime(filenameStr))
                filemd5 = md5Str(hashStr)
                                
            if song_info.result_type in ("mediainfo", "mp3guessenc", "aucdtect"):

                if song_info.quality is not None:
                    qualityItem = self.ui.tableWidget.item(row, table_headers.index("Quality"))
                    qualityItem.setText(song_info.quality)
                    if usecache:
                        filecache.setValue('{}/Quality'.format(filemd5),song_info.quality)
                    
                if song_info.quality_colour is not None:
                    qualityItem = self.ui.tableWidget.item(row, table_headers.index("Quality"))
                    qualityItem.setBackground(song_info.quality_colour)
                    if usecache:
                        filecache.setValue('{}/QualityColour'.format(filemd5),qualityItem.background())
                
                if song_info.result_type in ("mediainfo", "mp3guessenc"):
                    
                    if song_info.decode_errors > 0:
                        debug_log("{} decode errors detected for file {}".format(song_info.decode_errors,filenameStr))
                        errorColour = colourQualityBad
                    else:
                        errorColour = colourQualityGood
                    
                    errorsItem = self.ui.tableWidget.item(row, table_headers.index("Errors"))
                    if not errorsItem.background() == colourQualityBad:
                        errorsItem.setBackground(errorColour)
                    if usecache:
                        filecache.setValue('{}/ErrorColour'.format(filemd5),errorsItem.background())                    
                        
                    filenameItem.setData(dataScanned, True) # boolean, true if file already scanned
                    codecItem = self.ui.tableWidget.item(row, table_headers.index("Encoder"))
                    if not song_info.encoderstring == "":
                        codecItem.setText("{} ({})".format(song_info.audio_format,song_info.encoderstring))
                    else:
                        if song_info.encoder == "":
                            codecItem.setText("{}".format(song_info.audio_format))
                        else:
                            codecItem.setText("{} ({})".format(song_info.audio_format,song_info.encoder))
                
                    bitrateItem = self.ui.tableWidget.item(row, table_headers.index("Bitrate"))
                    if song_info.bitrate is not None:
                        bitrateItem.setText(song_info.bitrate)

                    if song_info.frame_hist is not None:
                        bitrateItem.setData(dataBitrate,song_info.frame_hist)
                        
                    frequencyItem = self.ui.tableWidget.item(row, table_headers.index("Frequency"))
                    if song_info.frequency is not None:
                        frequencyItem.setText(song_info.frequency)
                        
                    modeItem = self.ui.tableWidget.item(row, table_headers.index("Mode"))
                    if song_info.mode is not None:
                        modeItem.setText(song_info.mode)

                    lengthItem = self.ui.tableWidget.item(row, table_headers.index("Length"))
                    if song_info.length is not None:
                        lengthItem.setText(song_info.length)
                        
                    filesizeItem = self.ui.tableWidget.item(row, table_headers.index("Filesize"))
                    if song_info.filesize is not None:
                        filesizeItem.setText(song_info.filesize)

                    if usecache:
                        filecache.setValue('{}/Encoder'.format(filemd5),codecItem.text())
                        filecache.setValue('{}/Bitrate'.format(filemd5),bitrateItem.text())
                        filecache.setValue('{}/Length'.format(filemd5),lengthItem.text())
                        filecache.setValue('{}/Filesize'.format(filemd5),filesizeItem.text())
                        filecache.setValue('{}/Mode'.format(filemd5),modeItem.text())
                        filecache.setValue('{}/Frequency'.format(filemd5),frequencyItem.text())
                        try:
                            filecache.setValue('{}/FrameHist'.format(filemd5),bitrateItem.data(dataBitrate))
                        except KeyError:
                            filecache.remove('{}/FrameHist'.format(filemd5))
                        
            elif song_info.result_type == "Error Check":
                pass
            else: 
                debug_log("Update_Table: Result type {} unknown".format(song_info.result_type))
                    
    def updateMainGui(self):
        ''' runs from timer - takes results from main_q and adds to tablewidget '''
        
        while not main_q.empty():
            if debug_enabled:
                debug_log("updateMainGui: main_q not empty")
            global task_total, task_count
            with QReadLocker(ql):
                tasks_done = task_total - task_count
                if debug_enabled:
                    debug_log("updateMainGui: tasks_done {} task_total {} task_count {}".format(tasks_done,task_total,task_count))
            try:
                self.ui.progressBar.setValue(round((tasks_done/task_total)*100))
            except ZeroDivisionError:
                self.ui.progressBar.setValue(0)
        # scanner processes add results to main_q when finished
            try:
                q_info = main_q.get(False)
            except Empty as e:
                debug_log("updateMainGui: main_q.get exception {}".format(e))
                q_info = None
                                
            if q_info is not None:
                if not isinstance(q_info, main_info):
                    debug_log("updateMainGui received wrong data: {}".format(q_info))
                    return
                
                if debug_enabled:
                    debug_log("updateMainGui: calling update_Table for row {}".format(q_info.row))
                self.ui.tableWidget.setUpdatesEnabled(False)
                self.update_Table(q_info.row,q_info.song_info)
                self.ui.tableWidget.setUpdatesEnabled(True)

                with QWriteLocker(ql):
                    task_count -= 1
                    
                scan_rate = tasks_done/(time()-scan_start_time)
                files_scanned = task_total-task_count
                try:
                    eta_min = (task_count/scan_rate)/60 # estimated finish time in mins
                except ZeroDivisionError as e:
                    eta_min = 0
                if eta_min < 0: 
                    eta_min = 0
                self.statusBar().showMessage('Scanning... {}/{} tasks completed ({}/min, {}m {}s estimated)'.format(files_scanned, task_total, round(scan_rate*60), int(eta_min), round((eta_min-int(eta_min))*60)))
    
                if task_count < 1:
                    if debug_enabled:
                        debug_log("updateMainGui: all threads finished, task count={}".format(task_count))
                           
                    self.enableScanning()
                    self.ui.tableWidget.setSortingEnabled(True)
                    if main_q.empty():
                        if debug_enabled:
                            debug_log("updateMainGui: task queue empty, task count={}".format(task_count))
                        self.ui.progressBar.setValue(100)
                        self.statusBar().showMessage('Done')

    
    def doScanFile(self,thread):
        scanner_threadpool.start(thread)
        with QWriteLocker(ql):
            global task_count
            global task_total
            task_count += 1
            task_total += 1

    def disableScanning(self):
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.setText("Cancel")
        scanButton.setIcon(self.ui.actionStop.icon())
        scanButton.clicked.connect(self.ui.actionStop.trigger)        

    def enableScanning(self):
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
        self.ui.actionFolder_Select.setEnabled(True)
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.setText("Scan")
        scanButton.setIcon(self.ui.actionScan_Files.icon())
        scanButton.clicked.connect(self.ui.actionScan_Files.trigger)        
                    
    def scan_Files(self,checked,filelist=None):
        ''' loop through table and queue scanner processes for all files
        filelist - optional set of files to scan, all others will be skipped '''
        self.disableScanning()
        thread_list = []
        
        global debug_enabled
        debug_enabled = settings.value("Options/Debug", False, type=bool)
        
        numproc = settings.value('Options/Processes',0, type=int) # number of scanner processes to run, default = # of cpus
        if numproc > 0:
            scanner_threadpool.setMaxThreadCount(numproc)
        
        self.ui.tableWidget.setSortingEnabled(False) # prevent row numbers changing
        self.ui.tableWidget.setUpdatesEnabled(True)
        
        mp3guessenc_bin = findGuessEncBin()
        if (mp3guessenc_bin == "") or (not os.path.exists(mp3guessenc_bin)):
            mp3guessenc_bin = ""

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
        with QWriteLocker(ql):
            task_count = 0 # tasks remaining
            global task_total
        task_total = 0 # total tasks - used to calculate percentage remaining
        
        cmd_timeout = settings.value("Options/Proc_Timeout",300, type=int)
        
        row_count = self.ui.tableWidget.rowCount()
        
        for i in range(0,row_count):
            filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
            filenameStr = filenameItem.data(dataFilenameStr) # filename
            
            if filelist is not None:
                if not filenameStr in filelist:
                    continue
            
            fileScanned = filenameItem.data(dataScanned) # boolean, true if file already scanned
            
            if not fileScanned:
            
                if debug_enabled:
                    debug_log("Queuing process for file {}".format(filenameStr))
                    
                thread = getScannerThread(i,filenameStr,mp3guessenc_bin,mediainfo_bin,None,cmd_timeout)
                if thread is not None:
                    thread_list.append(thread)
                    
                # if lossless audio also run aucdtect if enabled and available

                if fnmatch.fnmatch(filenameStr, "*.flac"):
                    if settings.value('Options/auCDtect_scan',False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = settings.value('Options/auCDtect_mode',10, type=int)
                            thread = aucdtect_Thread(i,filenameStr,flac_bin,"-df",aucdtect_bin,"-m{}".format(aucdtect_mode),debug_enabled,cmd_timeout,main_q)
                            thread_list.append(thread)
                    if settings.value('Options/ScanForErrors',True, type=bool):
                        if not flac_bin == "":
                            thread = errorCheck_Thread(i,filenameStr,flac_bin,"-t",debug_enabled,cmd_timeout,main_q,True)
                            thread_list.append(thread)
                elif fnmatch.fnmatch(filenameStr, "*.wav"):
                    if settings.value('Options/auCDtect_scan',False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = settings.value('Options/auCDtect_mode',10, type=int)
                            thread = aucdtect_Thread(i,filenameStr,"","",aucdtect_bin,"-m{}".format(aucdtect_mode),debug_enabled,cmd_timeout,main_q)
                            thread_list.append(thread)
                                        
            QApplication.processEvents()
        
        global scan_start_time
        scan_start_time = time() # used to calculate scanning rate
#        self.statusBar().showMessage('Scanning files...')

        if len(thread_list) == 0: # nothing to do
            self.enableScanning()
        else:
            debug_log("Starting threads... {} tasks".format(len(thread_list)))
            for thread in thread_list:
                self.doScanFile(thread)
        
    def clear_List(self):
        self.ui.progressBar.setValue(0)
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        file_hashlist.clear()

    def about_Dlg(self):
        QMessageBox.about(self, "About",
                                """Specton Audio Analyser v{}
                                
Copyright (C) 2016-17 David Bird <somesortoferror@gmail.com>
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
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Python version: {}

""".format(version,sys.version)
                                )
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    checkPrereq(main)
    sys.exit(app.exec_())
