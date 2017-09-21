# -*- coding: utf-8 -*-

import queue, os, logging
from PyQt5.QtCore import QTimer, QThreadPool, QRunnable
from PyQt5.QtWidgets import QWidget,QDialog,QTabWidget,QGridLayout,QTextEdit,QLabel
from PyQt5.QtGui import QPixmap
from spct_utils import debug_log
from dlg_info import Ui_FileInfoDialog
from spct_utils import md5Str,findGuessEncBin,findGnuPlotBin,findMediaInfoBin,findSoxBin,getTempFileName,findffprobeBin,findDlg
from spct_cfg import settings
from spct_objects import infoobj
from spct_threads import getScannerThread,makeSpectrogramThread,makeBitGraphThread,makeBitHistThread

class FileInfo(QDialog):
    # right click file info dialog
    def __init__(self, filenameStr, frame_hist, infodlg_list, debug_enabled=False):
        super(FileInfo, self).__init__()
        self.ui = Ui_FileInfoDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(self.tr("Info") + " - {}".format(os.path.basename(filenameStr)))
        self.filename = filenameStr
        self.frame_hist = frame_hist  # tuple
        self.infodlg_q = queue.Queue()
        self.infodlg_threadpool = QThreadPool(None)
        self.debug_enabled = debug_enabled
        self.infodlg_list = infodlg_list
        self.infodlg_list.add(self)  # keep track of dialogs so we can reuse them if still open

        windowGeometry = settings.value("State/InfoWindowGeometry")
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        tabWidget.clear()

        if self.frame_hist is not None:
            x, y = self.frame_hist
        else:
            x = []
            y = []

        debug_log("Frame histogram - {}".format(self.frame_hist),logging.DEBUG)
        debug_log("Frame histogram - {}".format(x),logging.DEBUG)
        debug_log("Frame histogram - {}".format(y),logging.DEBUG)
            
        if len(x) > 0:
            try:
                debug_log("Running gnuplot to create frame histogram for file {}".format(filenameStr))

                tab = QWidget()
                grid = QGridLayout(tab)
                grid.setObjectName("BitrateHistLayout-{}".format(md5Str(filenameStr)))
                tabWidget.addTab(tab, self.tr("Bitrate Distribution"))

                thread = makeBitHistThread(filenameStr, grid.objectName(),
                                           settings.value("Options/Proc_Timeout", 300, type=int), self.infodlg_q,
                                           findGnuPlotBin(), x, y)
                self.infodlg_threadpool.start(thread)

            except Exception as e:
                debug_log(e,logging.ERROR)

        updateGuiTimer = QTimer(self)
        updateGuiTimer.timeout.connect(self.updateGui)
        updateGuiTimer.setInterval(100)
        updateGuiTimer.start()

        debug_log("Running scanner for file {}".format(filenameStr))

        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setObjectName("OutputLayout-{}".format(md5Str(filenameStr)))
        tabWidget.addTab(tab, self.tr("Scanner Output"))

        mp3guessenc_bin = findGuessEncBin()
        if (mp3guessenc_bin == "") or (not os.path.exists(mp3guessenc_bin)):
            mp3guessenc_bin = ""

        mediainfo_bin = findMediaInfoBin()
        if (mediainfo_bin == "") or (not os.path.exists(mediainfo_bin)):
            mediainfo_bin = ""

        threads = getScannerThread(grid.objectName(), filenameStr, mp3guessenc_bin, mediainfo_bin, grid,
                                  settings.value("Options/Proc_Timeout", 300, type=int),debug_enabled,None,self.infodlg_q)
        if threads:
            for thread in threads:
                if isinstance(thread,QRunnable):
                    self.infodlg_threadpool.start(thread)
                else:
                    debug_log("getScannerThread not QRunnable: {}".format(thread),logging.WARNING)

        if settings.value('Options/EnableSpectrogram', True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("SpectrogramLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab, self.tr("Spectrogram"))

            sox_bin = findSoxBin()
            temp_file = getTempFileName() + ".png"
            palette = settings.value('Options/SpectrogramPalette', 1, type=int)

            debug_log("Running sox to create spectrogram for file {}".format(filenameStr))

            thread = makeSpectrogramThread(filenameStr, sox_bin, temp_file, palette, grid.objectName(),
                                           settings.value("Options/Proc_Timeout", 300, type=int), self.infodlg_q)
            self.infodlg_threadpool.start(thread)

        if settings.value('Options/EnableBitGraph', True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("BitgraphLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab, self.tr("Bitrate Graph"))
            debug_log("Running ffprobe to create bitrate graph for file {}".format(filenameStr))
            thread = makeBitGraphThread(filenameStr, grid.objectName(), findffprobeBin(),
                                        settings.value("Options/Proc_Timeout", 300, type=int), self.infodlg_q,
                                        findGnuPlotBin())
            self.infodlg_threadpool.start(thread)

    def updateGui(self):
        ''' called from timer - subprocesses post to queue when finished '''
        if not self.infodlg_q.empty():
            update_info = self.infodlg_q.get(False, 1)
            # class infoobj
            # type - type of update e.g. "Spectrogram"
            # data - handler specific data
            # layout - QLayout to update
            # fn - name of file the update is for

            if not isinstance(update_info, infoobj):
                debug_log("updateGui received wrong data: {}".format(update_info),logging.WARNING)
                return
                
            if update_info.type in [infoobj.BITGRAPH, infoobj.BITHIST, infoobj.SPECTROGRAM]:
                debug_log("updateGui received type {} update".format(update_info.type))
                px = QLabel()
                dlg = findDlg(update_info.fn,self.debug_enabled,self.infodlg_list)
                if dlg is not None:
                    layout = dlg.findChild(QGridLayout, update_info.layout)
                    if layout is not None:
                        layout.addWidget(px)
                        px.setPixmap(QPixmap(update_info.data))
                    else:
                        debug_log("updateGui ran but layout not found type={} str={} layout={}".format(update_info.type,
                                                                                                       update_info.data,
                                                                                                       update_info.layout),logging.WARNING)
                else:
                    debug_log("updateGui couldn't find dlg type={} str={} layout={}".format(update_info.type,
                                                                                            update_info.data,
                                                                                            update_info.layout),logging.WARNING)
                try:
                    os.remove(update_info.data)  # delete generated spectrogram image
                except OSError:
                    pass

            elif update_info.type == infoobj.SCANNER_OUTPUT:
                debug_log("updateGui received Scanner_Output update")
                if update_info.layout is not None:
                    textEdit_scanner = QTextEdit()
                    textEdit_scanner.setReadOnly(True)
                    textEdit_scanner.setPlainText(update_info.data)
                    update_info.layout.addWidget(textEdit_scanner)

    def closeEvent(self, event):
        windowGeometry = self.saveGeometry()

        if settings.value("Options/SaveWindowState", True, type=bool):
            settings.setValue("State/InfoWindowGeometry", windowGeometry)

        self.infodlg_list.remove(self)
        event.accept()
