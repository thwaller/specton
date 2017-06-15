# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'downloader.ui'
#
# Created by: PyQt5 UI code generator 5.8.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DownloaderDlg(object):
    def setupUi(self, DownloaderDlg):
        DownloaderDlg.setObjectName("DownloaderDlg")
        DownloaderDlg.resize(524, 443)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(DownloaderDlg.sizePolicy().hasHeightForWidth())
        DownloaderDlg.setSizePolicy(sizePolicy)
        self.downloads_buttonBox = QtWidgets.QDialogButtonBox(DownloaderDlg)
        self.downloads_buttonBox.setGeometry(QtCore.QRect(350, 400, 161, 32))
        self.downloads_buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.downloads_buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close | QtWidgets.QDialogButtonBox.Ok)
        self.downloads_buttonBox.setCenterButtons(False)
        self.downloads_buttonBox.setObjectName("downloads_buttonBox")
        self.downloads_treeWidget = QtWidgets.QTreeWidget(DownloaderDlg)
        self.downloads_treeWidget.setGeometry(QtCore.QRect(10, 10, 501, 381))
        self.downloads_treeWidget.setObjectName("downloads_treeWidget")
        self.downloads_treeWidget.headerItem().setText(0, "1")
        self.statusLabel = QtWidgets.QLabel(DownloaderDlg)
        self.statusLabel.setGeometry(QtCore.QRect(20, 400, 321, 31))
        self.statusLabel.setText("")
        self.statusLabel.setObjectName("statusLabel")

        self.retranslateUi(DownloaderDlg)
        self.downloads_buttonBox.accepted.connect(DownloaderDlg.accept)
        self.downloads_buttonBox.rejected.connect(DownloaderDlg.reject)
        QtCore.QMetaObject.connectSlotsByName(DownloaderDlg)

    def retranslateUi(self, DownloaderDlg):
        _translate = QtCore.QCoreApplication.translate
        DownloaderDlg.setWindowTitle(_translate("DownloaderDlg", "Dialog"))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    DownloaderDlg = QtWidgets.QDialog()
    ui = Ui_DownloaderDlg()
    ui.setupUi(DownloaderDlg)
    DownloaderDlg.show()
    sys.exit(app.exec_())
