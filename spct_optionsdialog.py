# -*- coding: utf-8 -*-

from dlg_options import Ui_optionsDialog
from PyQt5.QtWidgets import QDialog,QFileDialog,QLineEdit,QCheckBox,QSpinBox,QSlider,QDialogButtonBox,QPushButton
import spct_cfg as cfg
from spct_utils import findGuessEncBin,findMediaInfoBin,findFlacBin,findauCDtectBin,findSoxBin,findGnuPlotBin,findffprobeBin
from spct_defs import defaultfilemask

class OptionsDialog(QDialog):
    def __init__(self):
        super(OptionsDialog, self).__init__()
        self.ui = Ui_optionsDialog()
        self.ui.setupUi(self)
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        filemask_regex = cfg.settings.value('Options/FilemaskRegEx', defaultfilemask)
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
        checkBox_recursive.setChecked(cfg.settings.value('Options/RecurseDirectories', True, type=bool))
        checkBox_followsymlinks = self.findChild(QCheckBox, "checkBox_followsymlinks")
        checkBox_followsymlinks.setChecked(cfg.settings.value('Options/FollowSymlinks', False, type=bool))
        checkBox_cache = self.findChild(QCheckBox, "checkBox_cache")
        checkBox_cache.setChecked(cfg.settings.value('Options/UseCache', True, type=bool))
        checkBox_cacheraw = self.findChild(QCheckBox, "checkBox_cacheraw")
        checkBox_cacheraw.setChecked(cfg.settings.value('Options/CacheRawOutput', False, type=bool))
        spinBox_processes = self.findChild(QSpinBox, "spinBox_processes")
        spinBox_processes.setValue(cfg.settings.value('Options/Processes', 0, type=int))
        spinBox_spectrogram_palette = self.findChild(QSpinBox, "spinBox_spectrogram_palette")
        spinBox_spectrogram_palette.setValue(cfg.settings.value('Options/SpectrogramPalette', 1, type=int))
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        checkBox_debug.setChecked(cfg.settings.value("Options/Debug", False, type=bool))
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        checkBox_savewindowstate.setChecked(cfg.settings.value("Options/SaveWindowState", True, type=bool))
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        checkBox_clearfilelist.setChecked(cfg.settings.value('Options/ClearFilelist', True, type=bool))
        checkBox_spectrogram = self.findChild(QCheckBox, "checkBox_spectrogram")
        checkBox_spectrogram.setChecked(cfg.settings.value('Options/EnableSpectrogram', True, type=bool))
        checkBox_bitrate_graph = self.findChild(QCheckBox, "checkBox_bitrate_graph")
        checkBox_bitrate_graph.setChecked(cfg.settings.value('Options/EnableBitGraph', True, type=bool))
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        checkBox_aucdtect_scan.setChecked(cfg.settings.value('Options/auCDtect_scan', False, type=bool))
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        horizontalSlider_aucdtect_mode.setValue(cfg.settings.value('Options/auCDtect_mode', 8, type=int))

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
            file = str(QFileDialog.getOpenFileName(parent=self, caption=self.tr("Browse to")+" {} ".format(exe_name)+self.tr("executable file"),
                                                   directory=path)[0])
            if not file == "":
                lineEdit.setText(file)

    def saveSettings(self):
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        cfg.settings.setValue('Options/FilemaskRegEx', lineEdit_filemaskregex.text())
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        cfg.settings.setValue('Paths/mediainfo_bin', lineEdit_mediainfo_path.text())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        cfg.settings.setValue('Paths/mp3guessenc_bin', lineEdit_mp3guessenc_path.text())
        lineEdit_aucdtect_path = self.findChild(QLineEdit, "lineEdit_aucdtect_path")
        cfg.settings.setValue('Paths/aucdtect_bin', lineEdit_aucdtect_path.text())
        lineEdit_sox_path = self.findChild(QLineEdit, "lineEdit_sox_path")
        cfg.settings.setValue('Paths/sox_bin', lineEdit_sox_path.text())
        lineEdit_ffprobe_path = self.findChild(QLineEdit, "lineEdit_ffprobe_path")
        cfg.settings.setValue('Paths/ffprobe_bin', lineEdit_ffprobe_path.text())
        checkBox_recursive = self.findChild(QCheckBox, "checkBox_recursive")
        cfg.settings.setValue('Options/RecurseDirectories', checkBox_recursive.isChecked())
        checkBox_followsymlinks = self.findChild(QCheckBox, "checkBox_followsymlinks")
        cfg.settings.setValue('Options/FollowSymlinks', checkBox_followsymlinks.isChecked())
        checkBox_cache = self.findChild(QCheckBox, "checkBox_cache")
        cfg.settings.setValue('Options/UseCache', checkBox_cache.isChecked())
        checkBox_cacheraw = self.findChild(QCheckBox, "checkBox_cacheraw")
        cfg.settings.setValue('Options/CacheRawOutput', checkBox_cacheraw.isChecked())
        spinBox_processes = self.findChild(QSpinBox, "spinBox_processes")
        cfg.settings.setValue('Options/Processes', spinBox_processes.value())
        spinBox_spectrogram_palette = self.findChild(QSpinBox, "spinBox_spectrogram_palette")
        cfg.settings.setValue('Options/SpectrogramPalette', spinBox_spectrogram_palette.value())
        checkBox_debug = self.findChild(QCheckBox, "checkBox_debug")
        cfg.settings.setValue('Options/Debug', checkBox_debug.isChecked())
        cfg.debug_enabled = checkBox_debug.isChecked()
        checkBox_savewindowstate = self.findChild(QCheckBox, "checkBox_savewindowstate")
        cfg.settings.setValue('Options/SaveWindowState', checkBox_savewindowstate.isChecked())
        checkBox_clearfilelist = self.findChild(QCheckBox, "checkBox_clearfilelist")
        cfg.settings.setValue('Options/ClearFilelist', checkBox_clearfilelist.isChecked())
        checkBox_spectrogram = self.findChild(QCheckBox, "checkBox_spectrogram")
        cfg.settings.setValue('Options/EnableSpectrogram', checkBox_spectrogram.isChecked())
        checkBox_bitrate_graph = self.findChild(QCheckBox, "checkBox_bitrate_graph")
        cfg.settings.setValue('Options/EnableBitGraph', checkBox_bitrate_graph.isChecked())
        checkBox_aucdtect_scan = self.findChild(QCheckBox, "checkBox_aucdtect_scan")
        cfg.settings.setValue('Options/auCDtect_scan', checkBox_aucdtect_scan.isChecked())
        horizontalSlider_aucdtect_mode = self.findChild(QSlider, "horizontalSlider_aucdtect_mode")
        cfg.settings.setValue('Options/auCDtect_mode', horizontalSlider_aucdtect_mode.value())
        self.close()
