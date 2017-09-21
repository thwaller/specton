# -*- coding: utf-8 -*-

import os, json
import requests, zipfile
import platform
import logging
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QTreeWidgetItemIterator, \
    QDialogButtonBox, QApplication
from PyQt5.QtGui import QIcon
from dlg_downloader import Ui_DownloaderDlg
from spct_utils import debug_log, findMediaInfoBin, findGuessEncBin, findFlacBin, findauCDtectBin, findSoxBin, \
    findGnuPlotBin, findffprobeBin
from spct_cfg import app_dirs

dataURL = 0x0200
dataInstallDir = 0x0201

json_url = "http://cognito.me.uk/uploads/specton/tools_urls.json"


class DownloaderDlg(QDialog):
    def __init__(self):
        super(DownloaderDlg, self).__init__()
        self.ui = Ui_DownloaderDlg()
        self.ui.setupUi(self)
        self.setWindowTitle(self.tr("Tools downloader"))
        icon = QIcon("./icons/097-download.png")
        self.setWindowIcon(icon)
        self.tw = self.findChild(QTreeWidget, "downloads_treeWidget")
        self.statusLabel = self.findChild(QLabel, "statusLabel")
        bbox = self.findChild(QDialogButtonBox, "downloads_buttonBox")
        bbox.setStandardButtons(QDialogButtonBox.Close)
        self.install_button = QPushButton(self.tr("Install selected"), self.tw)
        self.install_button.clicked.connect(self.installSelected)
        bbox.addButton(self.install_button, QDialogButtonBox.ActionRole)
        self.loadToolsJSON(self.tw)

    @staticmethod
    def checkInstalled(tool):
        debug_log("Checking for {}".format(tool))
        bin_exe = ""
        if tool == 'MediaInfo':
            bin_exe = findMediaInfoBin()
        elif tool == 'mp3guessenc':
            bin_exe = findGuessEncBin()
        elif tool == 'SoX':
            bin_exe = findSoxBin()
        elif tool == 'Gnuplot':
            bin_exe = findGnuPlotBin()
        elif tool == 'FFmpeg':
            bin_exe = findffprobeBin()
        elif tool == 'auCDtect':
            bin_exe = findauCDtectBin()
        elif tool == 'Flac':
            bin_exe = findFlacBin()
        else:
            debug_log("checkInstalled unknown tool {}".format(tool))

        return (bin_exe == "") or os.path.exists(bin_exe)

    def loadToolsJSON(self, tw):
        json_tools_path = app_dirs.user_config_dir + "/tools_urls.json"
        if not os.path.exists(json_tools_path):  # todo: update if too old
            try:
                r = requests.get(json_url)
                r.raise_for_status()
                with open(json_tools_path, "w") as f:
                    f.write(r.text)
            except requests.exceptions.RequestException as e:
                debug_log(e, logging.ERROR)

        if not os.path.exists(json_tools_path):
            return

        with open(json_tools_path, "r") as tools_url_file:
            tools_json = json.load(tools_url_file)

            tw.setColumnCount(4)
            tw.headerItem().setHidden(False)
            tw.headerItem().setText(0, self.tr("Name"))
            tw.headerItem().setText(1, self.tr("Category"))
            tw.headerItem().setText(2, self.tr("Download"))
            tw.headerItem().setText(3, self.tr("Status"))
            req = QTreeWidgetItem()
            req.setText(0, self.tr("Required"))
            #            req.setCheckState(0,2)
            tw.addTopLevelItem(req)
            opt = QTreeWidgetItem()
            opt.setText(0, self.tr("Optional"))
            #            opt.setCheckState(0,0)
            tw.addTopLevelItem(opt)

            for title, values in tools_json.items():
                item = QTreeWidgetItem()
                item.setText(0, title)
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                required = values['required']
                platform_s = values['platform']
                if required:
                    req.addChild(item)
                    item.setCheckState(0, 2)
                else:
                    opt.addChild(item)
                    item.setCheckState(0, 0)
                if self.checkInstalled(title):
                    item.setText(3, self.tr("Installed"))
                    item.setDisabled(True)
                    item.setCheckState(0, 2)
                else:
                    item.setText(3, self.tr("Not installed"))
                url = values['url']
                try:
                    url64 = values['url64']
                except KeyError:
                    url64 = ""
                install_dir = values['install_dir']
                if (platform.machine() == "AMD64") and not (url64 == ""):
                    item.setData(0, dataURL, url64)
                else:
                    item.setData(0, dataURL, url)
                item.setData(0, dataInstallDir, install_dir)
                category = values['category']
                item.setText(1, category)
                description = values['description']
                di = QTreeWidgetItem()
                label = QLabel(description)
                label.setWordWrap(True)
                item.addChild(di)
                tw.setItemWidget(di, 0, label)
                tw.setFirstItemColumnSpanned(di, False)
                item.setExpanded(True)
            #        req.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)
            #        opt.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)
        req.setExpanded(True)
        opt.setExpanded(True)
        tw.resizeColumnToContents(1)
        tw.resizeColumnToContents(2)
        tw.resizeColumnToContents(3)
        tw.resizeColumnToContents(0)

        delayTimer = QTimer(self)
        delayTimer.timeout.connect(self.getDLsize)
        delayTimer.setInterval(100)
        delayTimer.setSingleShot(True)
        delayTimer.start()

    def getDLsize(self):
        debug_log("getDLsize called")
        it = QTreeWidgetItemIterator(self.tw)
        while it.value():
            item = it.value()
            url_test = item.data(0, dataURL)
            if url_test is not None:
                try:
                    r = requests.head(url_test)
                    r.raise_for_status()
                    try:
                        size = (int(r.headers['Content-Length']) / 1024) / 1024
                    except ValueError:
                        size = 0
                    if size > 0:
                        item.setText(2, "{} MiB".format(round(size, 2)))
                except requests.exceptions.HTTPError:
                    debug_log("Error {} getting DL size: {}".format(r.status_code, r.headers))
                    item.setText(2, r.status_code)
                except requests.exceptions.RequestException as e:
                    item.setText(2, self.tr("Error"))
                    debug_log(e, logging.ERROR)
            it += 1

    def installSelected(self):
        debug_log("installSelected")
        self.install_button.setEnabled(False)
        it = QTreeWidgetItemIterator(self.tw)
        if not os.path.exists(app_dirs.user_cache_dir):
            os.mkdir(app_dirs.user_cache_dir)
        if not os.path.exists(app_dirs.user_cache_dir):
            os.mkdir(app_dirs.user_cache_dir)
        while it.value():
            item = it.value()
            if (not item.isDisabled()) and (item.checkState(0) == 2):
                url_test = item.data(0, dataURL)
                install_dir = item.data(0, dataInstallDir)
                if url_test is not None:
                    fn = os.path.basename(url_test)
                    self.statusLabel.setText(self.tr("Downloading")+" {}...".format(fn))
                    QApplication.processEvents()
                    try:
                        r = requests.get(url_test)
                        r.raise_for_status()
                        debug_log("{}".format(r.headers))
                        with open(app_dirs.user_cache_dir + "/" + fn, "wb") as zip_f:
                            zip_f.write(r.content)
                        self.installZip(app_dirs.user_cache_dir + "/" + fn, install_dir)
                        item.setText(3, self.tr("Installed"))
                        QApplication.processEvents()
                        item.setDisabled(True)
                    except requests.exceptions.HTTPError:
                        debug_log(
                            "Error {} downloading file {}, headers: {}".format(r.status_code, url_test, r.headers),
                            logging.WARNING)
                    except requests.exceptions.RequestException as e:
                        debug_log(e, logging.ERROR)
            self.statusLabel.setText("")
            it += 1
        self.install_button.setEnabled(True)

    def installZip(self, fn, install_dir):
        debug_log("installZip: Installing {} to {}...".format(fn, install_dir))
        self.statusLabel.setText(self.tr("Installing")+" {}...".format(os.path.basename(fn)))
        QApplication.processEvents()
        zip_f = zipfile.ZipFile(fn)
        zip_f.extractall(path=app_dirs.user_cache_dir + "/" + install_dir)
        self.statusLabel.setText("")
        QApplication.processEvents()
