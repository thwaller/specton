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
import logging
import os
import queue
import subprocess
import sys
from functools import partial
from collections import deque
from io import TextIOWrapper
from time import asctime, gmtime, strftime, time

from PyQt5.QtCore import QTimer, QThreadPool, QRunnable, QReadLocker, QWriteLocker, \
    QReadWriteLock, QEvent, QTranslator, QLocale
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QFileDialog, \
    QTableWidgetItem, QMessageBox, QMenu, QPushButton, QPlainTextEdit

import spct_cfg as cfg
from dlg_main import Ui_MainWindow
from spct_defs import *
from spct_downloader import DownloaderDlg
from spct_fileinfodialog import FileInfo
from spct_objects import main_info, song_info_obj
from spct_optionsdialog import OptionsDialog
from spct_threads import getScannerThread, aucdtect_Thread, errorCheck_Thread
from spct_utils import findGuessEncBin, findMediaInfoBin, findFlacBin, findauCDtectBin, md5Str, debug_log, findDlg, \
    openFolder

frozen = bool(getattr(sys, 'frozen', False))

if os.name == 'nt':  # various hacks

    stderr_fn = os.path.join(cfg.app_dirs.user_log_dir, "stderr.log")
    stdout_fn = os.path.join(cfg.app_dirs.user_log_dir, "stdout.log")

    try:
        os.remove(stderr_fn)
        os.remove(stdout_fn)
    except OSError:
        pass

    if not frozen:
        if sys.stdout is not None:
            pass
            sys.stdout = TextIOWrapper(sys.stdout.buffer, sys.stdout.encoding,
                                       'backslashreplace')  # fix for printing utf8 strings on windows
        else:
            # win32gui doesn't have a console
            debug_log("Redirecting stdout/err to file...")
            sys.stdout = open(stdout_fn, "w")
            sys.stderr = open(stderr_fn, "w")
    else:  # frozen
        debug_log("Redirecting stdout/err to file...(Frozen)")
        sys.stdout = open(stdout_fn, "w")
        sys.stderr = open(stderr_fn, "w")


def headerIndexByName(table, headerName):
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
        if not os.name == 'nt': return  # downloader currently only implemented for windows
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("Some required tools are not found. Do you want to download them now?")
        msg.setWindowTitle("Specton")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        if retval == QMessageBox.Yes:
            dlg = DownloaderDlg()
            dlg.exec()


class Main(QMainWindow):
    main_q = queue.Queue()
    infodlg_list = set()  # list of dialog windows
    scanner_threadpool = QThreadPool(None)
    ql = QReadWriteLock()
    file_hashlist = set()

    def __init__(self):
        super(Main, self).__init__()

        # build ui
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.task_count = 0
        self.task_total = 0
        self.scan_start_time = time()
        
        self.filterTimer = QTimer(self)
        self.recentFiles = deque([],cfg.maxMRU)
        
        self.ui.actionExit.triggered.connect(sys.exit)
        self.ui.actionExit.setText(self.tr("E&xit"))
        self.ui.actionScan_Files.triggered.connect(self.scan_Files)
        self.ui.actionFolder_Select.triggered.connect(self.select_folder_click)        
        
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.clicked.connect(self.ui.actionScan_Files.trigger)
        scanButton.setIcon(self.ui.actionScan_Files.icon())
        self.ui.actionFolder_Select.setText(self.tr("Select F&older"))
        self.ui.actionClear_Filelist.triggered.connect(self.clear_List)
        self.ui.actionStop.triggered.connect(self.cancel_Tasks)
        self.ui.actionOptions.triggered.connect(self.edit_Options)
        self.ui.actionOptions.setText(self.tr("&Options"))
        self.ui.actionAbout.triggered.connect(self.about_Dlg)
        self.ui.actionAbout.setText(self.tr("&About"))
        self.ui.actionViewConfigDir.triggered.connect(self.viewConfigDir)
        self.ui.actionViewConfigDir.setText(self.tr("&Config files"))
        self.ui.actionViewLogDir.triggered.connect(self.viewLogDir)
        self.ui.actionViewLogDir.setText(self.tr("&Logs"))
        self.ui.actionTools_Downloader.setText(self.tr("&Tools downloader"))
        self.ui.actionTools_Downloader.triggered.connect(self.tools_downloader)
        
        self.recentFiles = cfg.settings.value("State/MRU",[]) # todo add favourites
        if not self.recentFiles:
            self.recentFiles = deque([],cfg.maxMRU)

        fileMenu = self.ui.menubar.addMenu(self.tr('&File'))
        fileMenu.addAction(self.ui.actionFolder_Select)
        self.mruMenu = fileMenu.addMenu(self.tr("&Recent Folders"))
        self.mruMenuUpdate()
        fileMenu.addAction(self.ui.actionExit)
        editMenu = self.ui.menubar.addMenu(self.tr('&Edit'))
        editMenu.addAction(self.ui.actionOptions)
        viewMenu = self.ui.menubar.addMenu(self.tr('&View'))
        viewMenu.addAction(self.ui.actionViewConfigDir)
        viewMenu.addAction(self.ui.actionViewLogDir)
        viewMenu.addAction(self.ui.actionTools_Downloader)
        languageMenu = self.ui.menubar.addMenu(self.tr('&Language'))
        
        for fn in os.listdir("./i18n"):
            if fn.endswith(".qm"):
                match = re.search("_(.*)\.",os.path.basename(fn))
                if match:
                    lang_name = match.group(1)
                    lang_action = languageMenu.addAction(lang_name)
                    lang_action.triggered.connect(partial(self.langClick, languageMenu, lang_name))
                    lang_action.setCheckable(True)
                    if lang_name == QLocale.system().name():
                        lang_action.setChecked(True)
            
        helpMenu = self.ui.menubar.addMenu(self.tr('&Help'))
        helpMenu.addAction(self.ui.actionAbout)

        self.ui.tableWidget.setColumnCount(len(TableHeaders))
        self.ui.tableWidget.setHorizontalHeaderLabels(TableHeaders)
        self.ui.tableWidget.horizontalHeader().resizeSection(headerIndexByName(self.ui.tableWidget, "Filename"), 300)
        self.ui.tableWidget.horizontalHeader().setSectionsMovable(True)
        self.ui.tableWidget.installEventFilter(self)

        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.tableContextMenu)

        windowState = cfg.settings.value("State/windowState")
        windowGeometry = cfg.settings.value("State/windowGeometry")
        tableGeometry = cfg.settings.value("State/tableGeometry")
        tableHeaderState = cfg.settings.value("State/tableHeaderState")
        
        if windowState is not None:
            self.restoreState(windowState)
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        if tableGeometry is not None:
            self.ui.tableWidget.restoreGeometry(tableGeometry)
        if tableHeaderState is not None:
            self.ui.tableWidget.horizontalHeader().restoreState(tableHeaderState)
            self.ui.tableWidget.sortByColumn(-1, Qt.AscendingOrder)

        self.ui.filterBox.textChanged.connect(self.filterBoxChanged)
        self.ui.filter_comboBox.currentIndexChanged.connect(self.filterBoxChanged)
        self.filterTimer.setSingleShot(True)
        self.filterTimer.timeout.connect(self.doFilterTable)
            
        updateMainGuiTimer = QTimer(self)  # this timer watches main_q and updates tablewidget with scanner results
        updateMainGuiTimer.timeout.connect(self.updateMainGui)
        updateMainGuiTimer.setInterval(500)
        updateMainGuiTimer.start()

    def eventFilter(self, obj, event):
        if obj is self.ui.tableWidget:
            # handle file/folder drag & drop
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                else:
                    event.ignore()
                return True
            if event.type() == QEvent.Drop:
                if event.mimeData().hasUrls():
                    links = []
                    for url in event.mimeData().urls():
                        links.append(str(url.toLocalFile()))
                    self.addFilesFolders(filedirlist=links, clearfilelist=False)
                    event.accept()
                else:
                    event.ignore()
                return True
            return False

    @staticmethod
    def edit_Options():
        dialog = OptionsDialog()
        result = dialog.exec_()

    @staticmethod
    def viewLogDir():
        openFolder(cfg.app_dirs.user_log_dir)

    @staticmethod
    def viewConfigDir():
        openFolder(os.path.dirname(cfg.settings.fileName()))

    @staticmethod
    def tools_downloader():
        dlg = DownloaderDlg()
        dlg.exec()
    
    def langClick(self,lang_menu,lang,checked):
        for action in lang_menu.actions():
            if action.text() == lang:
                action.setChecked(True)
#                translator = QTranslator()
                if translator.load("specton_"+lang, "./i18n", "", ".qm"):
                    self.ui.retranslateUi(main)
#                    app.installTranslator(translator)
            else:
                action.setChecked(False)

    def mruClick(self,folder):
        if os.path.exists(folder):
            self.addFilesFolders([folder],cfg.settings.value('Options/ClearFilelist', True, type=bool))
    
    def mruMenuUpdate(self):
        self.mruMenu.clear()
        for folder in self.recentFiles:
            actionMRU = self.mruMenu.addAction(folder)
            actionMRU.triggered.connect(partial(self.mruClick, folder))
        
    def filterBoxChanged(*args):
        if not args: return
        self = args[0]
        
        if self.sender()==self.ui.filter_comboBox:
            delay=0
        else:
            delay=1000
        
        if self.filterTimer.isActive():
            self.filterTimer.stop() # reset timer if already running
            
        self.filterTimer.start(delay)
                    
    def doFilterTable(self):

        def doTableHideTypes(table,filtertypes,row):
            if filtertypes == 0: # "All"
                return False
            elif filtertypes == 1: # "Errors only"
                errorsItem = table.item(row, headerIndexByName(table, "Errors"))
                if errorsItem.background() == colourQualityBad:
                    return False
                else:
                    return True
            elif filtertypes == 2: # "Lossless"
                fnItem = table.item(row, headerIndexByName(table, "Filename"))
                fn, ext = os.path.splitext(fnItem.toolTip())
                if ext.lower() in LosslessFormats:
                    return False
                else:
                    return True
            elif filtertypes == 3: # "Lossy"
                fnItem = table.item(row, headerIndexByName(table, "Filename"))
                fn, ext = os.path.splitext(fnItem.toolTip())
                if ext.lower() in LossyFormats:
                    return False
                else:
                    return True
            elif filtertypes in (4,5): # "High quality", "Low quality"
                qualityItem = table.item(row, headerIndexByName(table, "Quality"))
                background_colour = qualityItem.background()
                if filtertypes == 4:
                    return False if background_colour in (colourQualityGood,colourQualityOk) else True
                else:
                    return False if background_colour in (colourQualityWarning,colourQualityBad) else True
                    
            elif filtertypes == 6: # "Unscanned"  
                filenameItem = table.item(row, headerIndexByName(table, "Filename"))
                fileScanned = filenameItem.data(dataScanned)
                if fileScanned:
                    return True
                else:
                    return False
                
        filterText = self.ui.filterBox.text().lower()        
        filtertypes = self.ui.filter_comboBox.currentIndex()
        
        if filterText == "":
            for i in range(0, self.ui.tableWidget.rowCount()):
                self.ui.tableWidget.setRowHidden(i,False or (doTableHideTypes(self.ui.tableWidget,filtertypes,i)))
        else:
            for i in range(0, self.ui.tableWidget.rowCount()):
                artistItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Artist"))
                fnItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Filename"))
                encoderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Encoder"))
                fn = fnItem.toolTip().lower()
                if (filterText in fn) or (filterText in artistItem.text().lower()) or (filterText in encoderItem.text().lower()):
                    self.ui.tableWidget.setRowHidden(i,False or (doTableHideTypes(self.ui.tableWidget,filtertypes,i)))
                else:
                    self.ui.tableWidget.setRowHidden(i,True)

    def tableContextMenu(self, point):
        row = self.ui.tableWidget.rowAt(point.y())
        selected_items = self.ui.tableWidget.selectedItems()
        if not row == -1:
            menu = QMenu(self)
            viewInfoAction = QAction(self.tr("View &Info"), menu)
            viewInfoAction.triggered.connect(partial(self.contextViewInfo, row))
            menu.addAction(viewInfoAction)
            rescanFileAction = QAction(self.tr("&Scan File(s)"), menu)
            rescanFileAction.triggered.connect(partial(self.contextRescanFile, row, selected_items))
            if self.task_count > 0:
                rescanFileAction.setEnabled(False)
            scanFolderAction = QAction(self.tr("Scan &Folder"), menu)
            scanFolderAction.triggered.connect(partial(self.contextScanFolder, row))
            if self.task_count > 0:
                scanFolderAction.setEnabled(False)
            menu.addAction(rescanFileAction)
            menu.addAction(scanFolderAction)
            playFileAction = QAction(self.tr("&Play File"), menu)
            playFileAction.triggered.connect(partial(self.contextPlayFile, row))
            menu.addAction(playFileAction)
            browseFolderAction = QAction(self.tr("&Browse Folder"), menu)
            browseFolderAction.triggered.connect(partial(self.contextBrowseFolder, row))
            menu.addAction(browseFolderAction)
            writeReportAction = QAction(self.tr("Write &Report (Folder)"), menu)
            writeReportAction.triggered.connect(partial(self.contextWriteReport, row))
            menu.addAction(writeReportAction)
            menu.popup(self.ui.tableWidget.viewport().mapToGlobal(point))

    def closeEvent(self, event):
        self.cancel_Tasks()

        if cfg.settings.value("Options/SaveWindowState", True, type=bool):
            windowState = self.saveState()
            windowGeometry = self.saveGeometry()
            tableGeometry = self.ui.tableWidget.saveGeometry()
            tableHeaderState = self.ui.tableWidget.horizontalHeader().saveState()
            cfg.settings.setValue("State/windowState", windowState)
            cfg.settings.setValue("State/windowGeometry", windowGeometry)
            cfg.settings.setValue("State/tableGeometry", tableGeometry)
            cfg.settings.setValue("State/tableHeaderState", tableHeaderState)

        cfg.settings.setValue("State/MRU", self.recentFiles)
        event.accept()

    def contextWriteReport(self, row, silent=False):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Folder"))
        report_dir = folderItem.toolTip()
        report_dir_displayname = folderItem.text()
        file_list = []
        for i in range(0, self.ui.tableWidget.rowCount()):
            folderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Folder"))
            directory = folderItem.toolTip()
            if report_dir == directory:
                filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Filename"))
                filenameStr = filenameItem.data(dataFilenameStr)
                modified_date = strftime("%d/%m/%Y %H:%M:%S UTC", gmtime(os.path.getmtime(filenameStr)))
                codecItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Encoder"))
                bitrateItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Bitrate"))
                lengthItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Length"))
                filesizeItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Filesize"))
                qualityItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Quality"))
                frequencyItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Frequency"))
                modeItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Mode"))
                file_list.append([filenameItem.text(), lengthItem.text(), filesizeItem.text(), bitrateItem.text(),
                                  modeItem.text(), frequencyItem.text(), codecItem.text(), qualityItem.text(),
                                  modified_date])

        with open(report_dir + "/specton.log", "w") as report_file:
            report_file.write("Report for folder: {}\n".format(report_dir_displayname))
            report_file.write(
                "Generated by Specton Audio Analyser v{} (https://github.com/somesortoferror/specton) on {}\n\n".format(
                    cfg.version, asctime()))
            report_file.write(
                "------------------------------------------------------------------------------------------\n")
            report_file.write(
                "{:<50}{:<28}{:<15}{:<15}{:<14}{:<25}{}\n".format("Filename", "Last Modified Date", "Duration",
                                                                  "Filesize", "Frequency", "Bitrate/Mode",
                                                                  "Encoder/Quality"))
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
            report_file.write(
                "------------------------------------------------------------------------------------------\n")

        if not silent:
            self.statusBar().showMessage("Report generated for folder {}".format(report_dir_displayname))

    def contextRescanFile(self, row, selected_items):
        file_list = set()
        for filenameItem in selected_items:
            filenameItem.setData(dataScanned, False)
            file_list.add(filenameItem.data(dataFilenameStr))
        self.scan_Files(True, file_list)

    def contextScanFolder(self, row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Folder"))
        scan_dir = folderItem.toolTip()
        file_list = set()
        for i in range(0, self.ui.tableWidget.rowCount()):
            folderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Folder"))
            directory = folderItem.toolTip()
            if scan_dir == directory:
                filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Filename"))
                file_list.add(filenameItem.data(dataFilenameStr))
        self.scan_Files(True, file_list)

    def contextViewInfo(self, row):
        filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Filename"))
        codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Encoder"))
        bitrateItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Bitrate"))
        filenameStr = filenameItem.data(dataFilenameStr)
        dlg = findDlg(filenameStr, cfg.debug_enabled, self.infodlg_list)
        if dlg is None:
            debug_log("contextViewInfo: dialog was None")
            dlg = FileInfo(filenameStr, bitrateItem.data(dataBitrate), self.infodlg_list)
            debug_log(dlg.objectName())
            dlg.show()
        else:
            dlg.showNormal()
            dlg.activateWindow()

    def contextPlayFile(self, row):  # todo implement this
        pass

    def contextBrowseFolder(self, row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget, "Folder"))
        folderName = folderItem.toolTip()
        if os.name == 'nt':
            subprocess.Popen("explorer \"" + os.path.normpath(folderName) + "\"")

    def addTableWidgetItem(self, row, name, directory, usecache, tableheaders):
        filenameStr = os.path.join(directory, name)
        hashStr = filenameStr.replace("/", "\\") + str(
            os.path.getmtime(filenameStr))  # use mtime so hash changes if file changed
        filemd5 = md5Str(hashStr)

        if filemd5 in self.file_hashlist:
            return  # don't add same file twice

        self.file_hashlist.add(filemd5)

        filenameItem = QTableWidgetItem(name)
        filenameItem.setToolTip(filenameStr)
        filenameItem.setData(dataFilenameStr, filenameStr)
        codecItem = QTableWidgetItem("")
        folderItem = QTableWidgetItem(os.path.basename(directory))
        folderItem.setToolTip(directory)
        artistItem = QTableWidgetItem("")
        bitrateItem = QTableWidgetItem("")
        lengthItem = QTableWidgetItem("")
        filesizeItem = QTableWidgetItem("")
        qualityItem = QTableWidgetItem("")
        frequencyItem = QTableWidgetItem("")
        modeItem = QTableWidgetItem("")
        errorItem = QTableWidgetItem("")

        if usecache:
            if cfg.filecache.value('{}/Encoder'.format(filemd5)) is not None:
                artistItem.setText(cfg.filecache.value('{}/Artist'.format(filemd5)))
                codecItem.setText(cfg.filecache.value('{}/Encoder'.format(filemd5)))
                bitrateItem.setText(cfg.filecache.value('{}/Bitrate'.format(filemd5)))
                lengthItem.setText(cfg.filecache.value('{}/Length'.format(filemd5)))
                filesizeItem.setText(cfg.filecache.value('{}/Filesize'.format(filemd5)))
                frame_hist = cfg.filecache.value('{}/FrameHist'.format(filemd5))
                if frame_hist is not None:
                    bitrateItem.setData(dataBitrate, frame_hist)
                quality = cfg.filecache.value('{}/Quality'.format(filemd5))
                if quality is not None:
                    qualityItem.setText(quality)
                frequency = cfg.filecache.value('{}/Frequency'.format(filemd5))
                if frequency is not None:
                    frequencyItem.setText(frequency)
                mode = cfg.filecache.value('{}/Mode'.format(filemd5))
                if mode is not None:
                    modeItem.setText(mode)
                quality_colour = cfg.filecache.value('{}/QualityColour'.format(filemd5))
                if quality_colour is not None:
                    qualityItem.setBackground(quality_colour)
                error_colour = cfg.filecache.value('{}/ErrorColour'.format(filemd5))
                if error_colour is not None:
                    errorItem.setBackground(error_colour)

                filenameItem.setData(dataScanned, True)  # previously scanned

        self.ui.tableWidget.insertRow(row)
        self.ui.tableWidget.setItem(row, tableheaders.index("Filename"), filenameItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Artist"), artistItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Folder"), folderItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Encoder"), codecItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Bitrate"), bitrateItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Length"), lengthItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Filesize"), filesizeItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Quality"), qualityItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Errors"), errorItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Frequency"), frequencyItem)
        self.ui.tableWidget.setItem(row, tableheaders.index("Mode"), modeItem)

    def recursiveAdd(self, directory, filemask_regex, followsymlinks=False, recursedirectories=True, usecache=True,
                     tableheaders=None):
        ''' walk through directory and add filenames to treeview'''
        i = 0
        c = 0
        scan_start = time()
        for root, dirs, files in os.walk(directory, True, None, followsymlinks):
            c += 1
            if c % 2 == 0:
                QApplication.processEvents()
                if (i > 0) and (i % 10 == 0):  # update count every 10 files
                    self.statusBar().showMessage(
                        "Scanning for files: {} found ({} files/s)".format(i, round(i / (time() - scan_start))))
            if not recursedirectories:
                while len(dirs) > 0:
                    dirs.pop()
            for name in sorted(files):
                if filemask_regex.search(name) is not None:
                    self.addTableWidgetItem(i, name, root, usecache, tableheaders)
                    i += 1

    def select_folder_click(self, checked):
        clearfilelist = cfg.settings.value('Options/ClearFilelist', True, type=bool)
        self.addFilesFolders([], clearfilelist)

    def addFilesFolders(self, filedirlist=None, clearfilelist=True):

        if filedirlist is None:
            filedirlist = []

        if not filedirlist:
            select = str(QFileDialog.getExistingDirectory(self, self.tr("Select Directory to Scan"), os.path.expanduser("~")))
            if not select == "":
                filedirlist.append(select)
            else:
                return

        filemask = cfg.settings.value('Options/FilemaskRegEx', defaultfilemask)

        try:
            filemask_regex = re.compile(filemask, re.IGNORECASE)
        except re.error as e:
            debug_log("Error in filemask regex: {}, using default".format(e), logging.WARNING)
            filemask_regex = re.compile(defaultfilemask, re.IGNORECASE)

        followsymlinks = cfg.settings.value('Options/FollowSymlinks', False, type=bool)
        recursedirectories = cfg.settings.value('Options/RecurseDirectories', True, type=bool)
        if clearfilelist is None:
            clearfilelist = cfg.settings.value('Options/ClearFilelist', True, type=bool)
        usecache = cfg.settings.value('Options/UseCache', True, type=bool)

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
                self.recursiveAdd(directory=filedir, filemask_regex=filemask_regex, followsymlinks=followsymlinks,
                                  recursedirectories=recursedirectories, usecache=usecache, tableheaders=tableheaders)
                if filedir in self.recentFiles:
                    self.recentFiles.remove(filedir)
                self.recentFiles.appendleft(filedir)
            else:
                self.addTableWidgetItem(0, os.path.basename(filedir), os.path.dirname(filedir), usecache, tableheaders)

        self.mruMenuUpdate()
        self.doFilterTable()
        self.ui.tableWidget.setUpdatesEnabled(True)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.progressBar.setMinimum(0)
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        self.statusBar().showMessage('Ready')
        self.enableScanning()

    def cancel_Tasks(self):
        with QWriteLocker(self.ql):
            if self.task_count > 0:  # tasks are running
                self.scanner_threadpool.clear()
                self.task_count = self.scanner_threadpool.activeThreadCount()

    def update_Table(self, row, song_info):
        ''' update table with info from scanner '''
        if not isinstance(song_info, song_info_obj):
            debug_log("update_Table received wrong data: {}".format(song_info), logging.WARNING)
            return

        if song_info.cmd_error:
            debug_log("update_Table received cmd_error update for row {}: {}".format(row, vars(song_info)),
                      logging.WARNING)  # todo: notify user of this
            return

        usecache = cfg.settings.value('Options/UseCache', True, type=bool)
        table_headers = getTableHeaders(self.ui.tableWidget)

        if song_info.file_error:
            debug_log("Setting error status for row {}".format(row))
            errorItem = self.ui.tableWidget.item(row, table_headers.index("Errors"))
            errorItem.setBackground(colourQualityBad)
            return

        filenameItem = self.ui.tableWidget.item(row, table_headers.index("Filename"))
        filenameStr = filenameItem.data(dataFilenameStr)
        if usecache:
            hashStr = filenameStr.replace("/", "\\") + str(os.path.getmtime(filenameStr))
            filemd5 = md5Str(hashStr)

        if song_info.result_type in (song_info_obj.MEDIAINFO, song_info_obj.MP3GUESSENC, song_info_obj.AUCDTECT):

            if song_info.quality is not None:
                qualityItem = self.ui.tableWidget.item(row, table_headers.index("Quality"))
                qualityItem.setText(song_info.quality)
                if usecache:
                    cfg.filecache.setValue('{}/Quality'.format(filemd5), song_info.quality)

            if song_info.quality_colour is not None:
                qualityItem = self.ui.tableWidget.item(row, table_headers.index("Quality"))
                qualityItem.setBackground(song_info.quality_colour)
                if usecache:
                    cfg.filecache.setValue('{}/QualityColour'.format(filemd5), qualityItem.background())

            if song_info.result_type in (song_info_obj.MEDIAINFO, song_info_obj.MP3GUESSENC):

                if song_info.decode_errors > 0:
                    debug_log("{} decode errors detected for file {}".format(song_info.decode_errors, filenameStr))
                    errorColour = colourQualityBad
                else:
                    errorColour = colourQualityGood

                errorsItem = self.ui.tableWidget.item(row, table_headers.index("Errors"))
                if not errorsItem.background() == colourQualityBad:
                    errorsItem.setBackground(errorColour)
                if usecache:
                    cfg.filecache.setValue('{}/ErrorColour'.format(filemd5), errorsItem.background())

                filenameItem.setData(dataScanned, True)  # boolean, true if file already scanned
                codecItem = self.ui.tableWidget.item(row, table_headers.index("Encoder"))

                # prefer mp3guessenc encoder info over mediainfo

                if song_info.result_type == song_info_obj.MP3GUESSENC:
                    if not song_info.encoderstring == "":
                        codecText = "{} ({})".format(song_info.audio_format, song_info.encoderstring)
                    elif not song_info.encoder == "":
                        codecText = "{} ({})".format(song_info.audio_format, song_info.encoder)
                    else:
                        codecText = "{}".format(song_info.audio_format)
                    codecItem.setText(codecText)
                elif not codecItem.text():  # mediainfo
                    if not song_info.encoder == "":
                        codecText = "{} ({})".format(song_info.audio_format, song_info.encoder)
                    else:
                        codecText = "{}".format(song_info.audio_format)
                    codecItem.setText(codecText)

                bitrateItem = self.ui.tableWidget.item(row, table_headers.index("Bitrate"))
                if song_info.bitrate is not None:
                    bitrateItem.setText(song_info.bitrate)

                artistItem = self.ui.tableWidget.item(row, table_headers.index("Artist"))
                if not song_info.artist == "":
                    artistItem.setText(song_info.artist)

                if song_info.frame_hist is not None:
                    bitrateItem.setData(dataBitrate, song_info.frame_hist)

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
                    cfg.filecache.setValue('{}/Artist'.format(filemd5), artistItem.text())
                    cfg.filecache.setValue('{}/Encoder'.format(filemd5), codecItem.text())
                    cfg.filecache.setValue('{}/Bitrate'.format(filemd5), bitrateItem.text())
                    cfg.filecache.setValue('{}/Length'.format(filemd5), lengthItem.text())
                    cfg.filecache.setValue('{}/Filesize'.format(filemd5), filesizeItem.text())
                    cfg.filecache.setValue('{}/Mode'.format(filemd5), modeItem.text())
                    cfg.filecache.setValue('{}/Frequency'.format(filemd5), frequencyItem.text())
                    try:
                        cfg.filecache.setValue('{}/FrameHist'.format(filemd5), bitrateItem.data(dataBitrate))
                    except KeyError:
                        cfg.filecache.remove('{}/FrameHist'.format(filemd5))

        elif song_info.result_type == song_info_obj.ERROR_CHECK:
            debug_log(vars(song_info))  # todo something here
        else:
            debug_log("Update_Table: Result type {} unknown".format(song_info.result_type), logging.WARNING)

    def updateMainGui(self):
        ''' runs from timer - takes results from main_q and adds to tablewidget '''

        while not self.main_q.empty():
            debug_log("updateMainGui: main_q not empty")
            with QReadLocker(self.ql):
                tasks_done = self.task_total - self.task_count
                debug_log("updateMainGui: tasks_done {} self.task_total {} self.task_count {}".format(tasks_done,
                                                                                                      self.task_total,
                                                                                                      self.task_count))
            try:
                self.ui.progressBar.setValue(round((tasks_done / self.task_total) * 100))
            except ZeroDivisionError:
                self.ui.progressBar.setValue(0)
                # scanner processes add results to main_q when finished
            try:
                q_info = self.main_q.get(False)
            except queue.Empty as e:
                debug_log("updateMainGui: main_q.get exception {}".format(e), logging.WARNING)
                q_info = None

            if q_info is not None:
                if not isinstance(q_info, main_info):
                    debug_log("updateMainGui received wrong data: {}".format(q_info), logging.WARNING)
                    return

                debug_log(
                    "updateMainGui: calling update_Table for row {}".format(q_info.row))
                self.ui.tableWidget.setUpdatesEnabled(False)
                self.update_Table(q_info.row, q_info.song_info)
                self.ui.tableWidget.setUpdatesEnabled(True)

                with QWriteLocker(self.ql):
                    self.task_count -= 1

                scan_rate = tasks_done / (time() - self.scan_start_time)
                files_scanned = self.task_total - self.task_count
                try:
                    eta_min = (self.task_count / scan_rate) / 60  # estimated finish time in mins
                except ZeroDivisionError as e:
                    eta_min = 0
                if eta_min < 0:
                    eta_min = 0
                self.statusBar().showMessage(
                    'Scanning... {}/{} tasks completed ({}/min, {}m {}s estimated)'.format(files_scanned,
                                                                                           self.task_total,
                                                                                           round(scan_rate * 60),
                                                                                           int(eta_min), round(
                            (eta_min - int(eta_min)) * 60)))

                if self.task_count < 1:
                    debug_log("updateMainGui: all threads finished, task count={}".format(self.task_count))

                    self.enableScanning()
                    self.ui.tableWidget.setSortingEnabled(True)
                    if self.main_q.empty():
                        debug_log("updateMainGui: task queue empty, task count={}".format(self.task_count))
                        self.ui.progressBar.setValue(100)
                        self.statusBar().showMessage('Done')
        
    def doScanFile(self, thread):
        self.scanner_threadpool.start(thread)
        with QWriteLocker(self.ql):
            self.task_count += 1
            self.task_total += 1

    def disableScanning(self):
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.setText(self.tr("Cancel"))
        scanButton.setIcon(self.ui.actionStop.icon())
        scanButton.clicked.connect(self.ui.actionStop.trigger)

    def enableScanning(self):
        self.ui.actionScan_Files.setEnabled(True)
        self.ui.actionClear_Filelist.setEnabled(True)
        self.ui.actionFolder_Select.setEnabled(True)
        scanButton = self.findChild(QPushButton, "scanButton")
        scanButton.setText(self.tr("Scan"))
        scanButton.setIcon(self.ui.actionScan_Files.icon())
        scanButton.clicked.connect(self.ui.actionScan_Files.trigger)

    def scan_Files(self, checked, filelist=None):
        ''' loop through table and queue scanner processes for all files
        filelist - optional set of files to scan, all others will be skipped '''
        self.disableScanning()
        thread_list = deque()

        numproc = cfg.settings.value('Options/Processes', 0,
                                     type=int)  # number of scanner processes to run, default = # of cpus
        if numproc > 0:
            self.scanner_threadpool.setMaxThreadCount(numproc)

        self.ui.tableWidget.setSortingEnabled(False)  # prevent row numbers changing
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

        with QWriteLocker(self.ql):
            self.task_count = 0  # tasks remaining
        self.task_total = 0  # total tasks - used to calculate percentage remaining

        cmd_timeout = cfg.settings.value("Options/Proc_Timeout", 300, type=int)

        for i in range(0, self.ui.tableWidget.rowCount()):
            if self.ui.tableWidget.isRowHidden(i):
                continue
        
            filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget, "Filename"))
            filenameStr = filenameItem.data(dataFilenameStr)  # filename

            if filelist is not None:
                if not filenameStr in filelist:
                    continue

            fileScanned = filenameItem.data(dataScanned)  # boolean, true if file already scanned

            if not fileScanned:

                debug_log("Queuing process for file {}".format(filenameStr))

                threads = getScannerThread(i, filenameStr, mp3guessenc_bin, mediainfo_bin, None, cmd_timeout,
                                           cfg.debug_enabled, self.main_q, None)
                if threads:
                    for thread in threads:
                        if isinstance(thread, QRunnable):
                            thread_list.append(thread)
                        else:
                            debug_log("getScannerThread not QRunnable: {}".format(thread), logging.WARNING)

                # if lossless audio also run aucdtect if enabled and available

                if fnmatch.fnmatch(filenameStr, "*.flac"):
                    if cfg.settings.value('Options/auCDtect_scan', False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = cfg.settings.value('Options/auCDtect_mode', 10, type=int)
                            thread = aucdtect_Thread(i, filenameStr, flac_bin, "-df", aucdtect_bin,
                                                     "-m{}".format(aucdtect_mode), cfg.debug_enabled, cmd_timeout,
                                                     self.main_q)
                            thread_list.append(thread)
                    if cfg.settings.value('Options/ScanForErrors', True, type=bool):
                        if not flac_bin == "":
                            thread = errorCheck_Thread(i, filenameStr, flac_bin, "-t", cfg.debug_enabled, cmd_timeout,
                                                       self.main_q, True)
                            thread_list.append(thread)
                elif fnmatch.fnmatch(filenameStr, "*.wav"):
                    if cfg.settings.value('Options/auCDtect_scan', False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = cfg.settings.value('Options/auCDtect_mode', 10, type=int)
                            thread = aucdtect_Thread(i, filenameStr, "", "", aucdtect_bin, "-m{}".format(aucdtect_mode),
                                                     cfg.debug_enabled, cmd_timeout, self.main_q)
                            thread_list.append(thread)

            QApplication.processEvents()

        self.scan_start_time = time()  # used to calculate scanning rate
        #        self.statusBar().showMessage('Scanning files...')

        if len(thread_list) == 0:  # nothing to do
            self.enableScanning()
        else:
            debug_log("Starting threads... {} tasks".format(len(thread_list)))
            for thread in thread_list:
                self.doScanFile(thread)

    def clear_List(self):
        self.ui.progressBar.setValue(0)
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        self.file_hashlist.clear()

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

""".format(cfg.version, sys.version)
                          )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    translator = QTranslator()
    if translator.load(QLocale(), "specton", "_", "./i18n"):
        app.installTranslator(translator)
    main = Main()
    main.show()
    checkPrereq(main)
    sys.exit(app.exec_())
