# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'options.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_optionsDialog(object):
    def setupUi(self, optionsDialog):
        optionsDialog.setObjectName("optionsDialog")
        optionsDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        optionsDialog.resize(644, 328)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons/150-cogs.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        optionsDialog.setWindowIcon(icon)
        optionsDialog.setModal(True)
        self.gridLayout = QtWidgets.QGridLayout(optionsDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.buttonBox = QtWidgets.QDialogButtonBox(optionsDialog)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Discard|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(optionsDialog)
        self.tabWidget.setAutoFillBackground(True)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tab.sizePolicy().hasHeightForWidth())
        self.tab.setSizePolicy(sizePolicy)
        self.tab.setAutoFillBackground(True)
        self.tab.setObjectName("tab")
        self.formLayout_2 = QtWidgets.QFormLayout(self.tab)
        self.formLayout_2.setObjectName("formLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_4 = QtWidgets.QLabel(self.tab)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout.addWidget(self.label_4)
        self.spinBox_processes = QtWidgets.QSpinBox(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spinBox_processes.sizePolicy().hasHeightForWidth())
        self.spinBox_processes.setSizePolicy(sizePolicy)
        self.spinBox_processes.setMinimum(0)
        self.spinBox_processes.setMaximum(200)
        self.spinBox_processes.setObjectName("spinBox_processes")
        self.horizontalLayout.addWidget(self.spinBox_processes)
        self.formLayout_2.setLayout(1, QtWidgets.QFormLayout.LabelRole, self.horizontalLayout)
        self.checkBox_followsymlinks = QtWidgets.QCheckBox(self.tab)
        self.checkBox_followsymlinks.setObjectName("checkBox_followsymlinks")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.checkBox_followsymlinks)
        self.checkBox_recursive = QtWidgets.QCheckBox(self.tab)
        self.checkBox_recursive.setObjectName("checkBox_recursive")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.checkBox_recursive)
        self.checkBox_cache = QtWidgets.QCheckBox(self.tab)
        self.checkBox_cache.setObjectName("checkBox_cache")
        self.formLayout_2.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.checkBox_cache)
        self.checkBox_cacheraw = QtWidgets.QCheckBox(self.tab)
        self.checkBox_cacheraw.setObjectName("checkBox_cacheraw")
        self.formLayout_2.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.checkBox_cacheraw)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.checkBox_aucdtect_scan = QtWidgets.QCheckBox(self.tab)
        self.checkBox_aucdtect_scan.setObjectName("checkBox_aucdtect_scan")
        self.horizontalLayout_2.addWidget(self.checkBox_aucdtect_scan)
        self.label_5 = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_2.addWidget(self.label_5)
        self.horizontalSlider_aucdtect_mode = QtWidgets.QSlider(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalSlider_aucdtect_mode.sizePolicy().hasHeightForWidth())
        self.horizontalSlider_aucdtect_mode.setSizePolicy(sizePolicy)
        self.horizontalSlider_aucdtect_mode.setMaximum(40)
        self.horizontalSlider_aucdtect_mode.setSliderPosition(8)
        self.horizontalSlider_aucdtect_mode.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_aucdtect_mode.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.horizontalSlider_aucdtect_mode.setTickInterval(10)
        self.horizontalSlider_aucdtect_mode.setObjectName("horizontalSlider_aucdtect_mode")
        self.horizontalLayout_2.addWidget(self.horizontalSlider_aucdtect_mode)
        self.label_6 = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.label_6.setFont(font)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_2.addWidget(self.label_6)
        self.formLayout_2.setLayout(6, QtWidgets.QFormLayout.LabelRole, self.horizontalLayout_2)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.label_3 = QtWidgets.QLabel(self.tab)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_8.addWidget(self.label_3)
        self.lineEdit_filemaskregex = QtWidgets.QLineEdit(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_filemaskregex.sizePolicy().hasHeightForWidth())
        self.lineEdit_filemaskregex.setSizePolicy(sizePolicy)
        self.lineEdit_filemaskregex.setMinimumSize(QtCore.QSize(200, 0))
        self.lineEdit_filemaskregex.setObjectName("lineEdit_filemaskregex")
        self.horizontalLayout_8.addWidget(self.lineEdit_filemaskregex)
        self.formLayout_2.setLayout(0, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_8)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setAutoFillBackground(True)
        self.tab_2.setObjectName("tab_2")
        self.formLayout_5 = QtWidgets.QFormLayout(self.tab_2)
        self.formLayout_5.setObjectName("formLayout_5")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.checkBox_savewindowstate = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_savewindowstate.setObjectName("checkBox_savewindowstate")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.checkBox_savewindowstate)
        self.checkBox_clearfilelist = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_clearfilelist.setObjectName("checkBox_clearfilelist")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.checkBox_clearfilelist)
        self.checkBox_spectrogram = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_spectrogram.setObjectName("checkBox_spectrogram")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.checkBox_spectrogram)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_9 = QtWidgets.QLabel(self.tab_2)
        self.label_9.setObjectName("label_9")
        self.horizontalLayout_3.addWidget(self.label_9)
        self.spinBox_spectrogram_palette = QtWidgets.QSpinBox(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spinBox_spectrogram_palette.sizePolicy().hasHeightForWidth())
        self.spinBox_spectrogram_palette.setSizePolicy(sizePolicy)
        self.spinBox_spectrogram_palette.setMinimum(1)
        self.spinBox_spectrogram_palette.setMaximum(6)
        self.spinBox_spectrogram_palette.setObjectName("spinBox_spectrogram_palette")
        self.horizontalLayout_3.addWidget(self.spinBox_spectrogram_palette)
        self.formLayout.setLayout(3, QtWidgets.QFormLayout.LabelRole, self.horizontalLayout_3)
        self.checkBox_bitrate_graph = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_bitrate_graph.setObjectName("checkBox_bitrate_graph")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.checkBox_bitrate_graph)
        self.formLayout_5.setLayout(0, QtWidgets.QFormLayout.LabelRole, self.formLayout)
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setAutoFillBackground(True)
        self.tab_3.setObjectName("tab_3")
        self.formLayout_3 = QtWidgets.QFormLayout(self.tab_3)
        self.formLayout_3.setObjectName("formLayout_3")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_2 = QtWidgets.QLabel(self.tab_3)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_4.addWidget(self.label_2)
        self.lineEdit_mediainfo_path = QtWidgets.QLineEdit(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_mediainfo_path.sizePolicy().hasHeightForWidth())
        self.lineEdit_mediainfo_path.setSizePolicy(sizePolicy)
        self.lineEdit_mediainfo_path.setObjectName("lineEdit_mediainfo_path")
        self.horizontalLayout_4.addWidget(self.lineEdit_mediainfo_path)
        self.pushButton_mediainfo_path = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_mediainfo_path.sizePolicy().hasHeightForWidth())
        self.pushButton_mediainfo_path.setSizePolicy(sizePolicy)
        self.pushButton_mediainfo_path.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_mediainfo_path.setAutoDefault(True)
        self.pushButton_mediainfo_path.setDefault(False)
        self.pushButton_mediainfo_path.setFlat(False)
        self.pushButton_mediainfo_path.setObjectName("pushButton_mediainfo_path")
        self.horizontalLayout_4.addWidget(self.pushButton_mediainfo_path)
        self.formLayout_3.setLayout(0, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_4)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label = QtWidgets.QLabel(self.tab_3)
        self.label.setObjectName("label")
        self.horizontalLayout_5.addWidget(self.label)
        self.lineEdit_mp3guessenc_path = QtWidgets.QLineEdit(self.tab_3)
        self.lineEdit_mp3guessenc_path.setObjectName("lineEdit_mp3guessenc_path")
        self.horizontalLayout_5.addWidget(self.lineEdit_mp3guessenc_path)
        self.pushButton_mp3guessenc_path = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_mp3guessenc_path.sizePolicy().hasHeightForWidth())
        self.pushButton_mp3guessenc_path.setSizePolicy(sizePolicy)
        self.pushButton_mp3guessenc_path.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_mp3guessenc_path.setAutoDefault(True)
        self.pushButton_mp3guessenc_path.setDefault(False)
        self.pushButton_mp3guessenc_path.setFlat(False)
        self.pushButton_mp3guessenc_path.setObjectName("pushButton_mp3guessenc_path")
        self.horizontalLayout_5.addWidget(self.pushButton_mp3guessenc_path)
        self.formLayout_3.setLayout(1, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_5)
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_7 = QtWidgets.QLabel(self.tab_3)
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_6.addWidget(self.label_7)
        self.lineEdit_sox_path = QtWidgets.QLineEdit(self.tab_3)
        self.lineEdit_sox_path.setObjectName("lineEdit_sox_path")
        self.horizontalLayout_6.addWidget(self.lineEdit_sox_path)
        self.pushButton_sox_path = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_sox_path.sizePolicy().hasHeightForWidth())
        self.pushButton_sox_path.setSizePolicy(sizePolicy)
        self.pushButton_sox_path.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_sox_path.setAutoDefault(True)
        self.pushButton_sox_path.setDefault(False)
        self.pushButton_sox_path.setFlat(False)
        self.pushButton_sox_path.setObjectName("pushButton_sox_path")
        self.horizontalLayout_6.addWidget(self.pushButton_sox_path)
        self.formLayout_3.setLayout(2, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_6)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_11 = QtWidgets.QLabel(self.tab_3)
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_7.addWidget(self.label_11)
        self.lineEdit_ffprobe_path = QtWidgets.QLineEdit(self.tab_3)
        self.lineEdit_ffprobe_path.setObjectName("lineEdit_ffprobe_path")
        self.horizontalLayout_7.addWidget(self.lineEdit_ffprobe_path)
        self.pushButton_ffprobe_path = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_ffprobe_path.sizePolicy().hasHeightForWidth())
        self.pushButton_ffprobe_path.setSizePolicy(sizePolicy)
        self.pushButton_ffprobe_path.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_ffprobe_path.setAutoDefault(True)
        self.pushButton_ffprobe_path.setDefault(False)
        self.pushButton_ffprobe_path.setFlat(False)
        self.pushButton_ffprobe_path.setObjectName("pushButton_ffprobe_path")
        self.horizontalLayout_7.addWidget(self.pushButton_ffprobe_path)
        self.formLayout_3.setLayout(3, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_7)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_12 = QtWidgets.QLabel(self.tab_3)
        self.label_12.setObjectName("label_12")
        self.horizontalLayout_9.addWidget(self.label_12)
        self.lineEdit_aucdtect_path = QtWidgets.QLineEdit(self.tab_3)
        self.lineEdit_aucdtect_path.setObjectName("lineEdit_aucdtect_path")
        self.horizontalLayout_9.addWidget(self.lineEdit_aucdtect_path)
        self.pushButton_aucdtect_path = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_aucdtect_path.sizePolicy().hasHeightForWidth())
        self.pushButton_aucdtect_path.setSizePolicy(sizePolicy)
        self.pushButton_aucdtect_path.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_aucdtect_path.setAutoDefault(True)
        self.pushButton_aucdtect_path.setDefault(False)
        self.pushButton_aucdtect_path.setFlat(False)
        self.pushButton_aucdtect_path.setObjectName("pushButton_aucdtect_path")
        self.horizontalLayout_9.addWidget(self.pushButton_aucdtect_path)
        self.formLayout_3.setLayout(4, QtWidgets.QFormLayout.SpanningRole, self.horizontalLayout_9)
        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QtWidgets.QWidget()
        self.tab_4.setAutoFillBackground(True)
        self.tab_4.setObjectName("tab_4")
        self.formLayout_4 = QtWidgets.QFormLayout(self.tab_4)
        self.formLayout_4.setObjectName("formLayout_4")
        self.checkBox_debug = QtWidgets.QCheckBox(self.tab_4)
        self.checkBox_debug.setObjectName("checkBox_debug")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.checkBox_debug)
        self.tabWidget.addTab(self.tab_4, "")
        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 1)

        self.retranslateUi(optionsDialog)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(optionsDialog)

    def retranslateUi(self, optionsDialog):
        _translate = QtCore.QCoreApplication.translate
        optionsDialog.setWindowTitle(_translate("optionsDialog", "Options"))
        self.label_4.setText(_translate("optionsDialog", "Number of processes: (0 = same as # of cpus):"))
        self.checkBox_followsymlinks.setText(_translate("optionsDialog", "Follow Symlinks"))
        self.checkBox_recursive.setText(_translate("optionsDialog", "Recursive folder selection"))
        self.checkBox_cache.setText(_translate("optionsDialog", "Cache results"))
        self.checkBox_cacheraw.setText(_translate("optionsDialog", "Cache raw scanner output"))
        self.checkBox_aucdtect_scan.setText(_translate("optionsDialog", "Run auCDtect on lossless files"))
        self.label_5.setText(_translate("optionsDialog", "Accurate"))
        self.label_6.setText(_translate("optionsDialog", "Fast"))
        self.label_3.setText(_translate("optionsDialog", "File types: (RegEx)"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("optionsDialog", "Scanning"))
        self.checkBox_savewindowstate.setText(_translate("optionsDialog", "Save window state"))
        self.checkBox_clearfilelist.setText(_translate("optionsDialog", "Clear file list"))
        self.checkBox_spectrogram.setText(_translate("optionsDialog", "Generate spectrogram (requires sox)"))
        self.label_9.setText(_translate("optionsDialog", "Colour set:"))
        self.checkBox_bitrate_graph.setText(_translate("optionsDialog", "Generate bitrate graph (requires ffprobe)"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("optionsDialog", "Display"))
        self.label_2.setText(_translate("optionsDialog", "Path to mediainfo executable:"))
        self.pushButton_mediainfo_path.setText(_translate("optionsDialog", ".."))
        self.label.setText(_translate("optionsDialog", "Path to mp3guessenc executable:"))
        self.pushButton_mp3guessenc_path.setText(_translate("optionsDialog", ".."))
        self.label_7.setText(_translate("optionsDialog", "Path to sox executable:"))
        self.pushButton_sox_path.setText(_translate("optionsDialog", ".."))
        self.label_11.setText(_translate("optionsDialog", "Path to ffprobe executable:"))
        self.pushButton_ffprobe_path.setText(_translate("optionsDialog", ".."))
        self.label_12.setText(_translate("optionsDialog", "Path to aucdtect executable:"))
        self.pushButton_aucdtect_path.setText(_translate("optionsDialog", ".."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), _translate("optionsDialog", "Paths"))
        self.checkBox_debug.setText(_translate("optionsDialog", "Debug Output"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), _translate("optionsDialog", "Advanced"))

