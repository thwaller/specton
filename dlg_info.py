# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'info.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FileInfoDialog(object):
    def setupUi(self, FileInfoDialog):
        FileInfoDialog.setObjectName("FileInfoDialog")
        FileInfoDialog.resize(579, 472)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons/157-stats-bars.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        FileInfoDialog.setWindowIcon(icon)
        self.gridLayout = QtWidgets.QGridLayout(FileInfoDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tabWidget = QtWidgets.QTabWidget(FileInfoDialog)
        self.tabWidget.setObjectName("tabWidget")
        self.gridLayout_2.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(FileInfoDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout_2.addWidget(self.buttonBox, 1, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 0, 1, 1)

        self.retranslateUi(FileInfoDialog)
        self.tabWidget.setCurrentIndex(-1)
        self.buttonBox.accepted.connect(FileInfoDialog.accept)
        self.buttonBox.rejected.connect(FileInfoDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(FileInfoDialog)

    def retranslateUi(self, FileInfoDialog):
        _translate = QtCore.QCoreApplication.translate
        FileInfoDialog.setWindowTitle(_translate("FileInfoDialog", "Info"))
