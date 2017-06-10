# -*- coding: utf-8 -*-

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QTreeWidgetItemIterator, QDialogButtonBox, QApplication
from PyQt5.QtGui import QIcon
from dlg_downloader import Ui_DownloaderDlg
from spct_utils import debug_log,findMediaInfoBin,findGuessEncBin,findFlacBin,findauCDtectBin,findSoxBin,findGnuPlotBin,findffprobeBin
from spct_defs import app_dirs
import os, json
import requests,zipfile

dataURL=0x0200
dataInstallDir=0x0201

json_url = "http://cognito.me.uk/uploads/specton/tools_urls.json"

class DownloaderDlg(QDialog):
    def __init__(self):
        super(DownloaderDlg,self).__init__()
        self.ui = Ui_DownloaderDlg()
        self.ui.setupUi(self)
        self.setWindowTitle("Tools downloader")
        icon = QIcon("./icons/097-download.png")
        self.setWindowIcon(icon)
        self.tw = self.findChild(QTreeWidget, "downloads_treeWidget")
        self.statusLabel = self.findChild(QLabel, "statusLabel")
        bbox = self.findChild(QDialogButtonBox, "downloads_buttonBox")
        bbox.setStandardButtons(QDialogButtonBox.Close)
        self.install_button = QPushButton("Install selected",self.tw)
        self.install_button.clicked.connect(self.installSelected)
        bbox.addButton(self.install_button,QDialogButtonBox.ActionRole)
        self.loadToolsJSON(self.tw)
        
    def checkInstalled(self,tool):
        debug_log("Checking for {}".format(tool))
        bin=""
        if tool == 'MediaInfo':
            bin = findMediaInfoBin()
        elif tool == 'mp3guessenc':
            bin = findGuessEncBin()
        elif tool == 'SoX':
            bin = findSoxBin()
        elif tool == 'Gnuplot':
            bin = findGnuPlotBin()
        elif tool == 'FFmpeg':
            bin = findffprobeBin()
        elif tool == 'auCDtect':
            bin = findauCDtectBin()
        elif tool == 'Flac':
            bin = findFlacBin()
        else: debug_log("checkInstalled unknown tool {}".format(tool))

        return (bin == "") or os.path.exists(bin)
        
    def loadToolsJSON(self,tw):
        json_tools_path = app_dirs.user_config_dir + "/tools_urls.json"
        if not os.path.exists(json_tools_path):
            try:
                r = requests.get(json_url)
                r.raise_for_status()
                with open(json_tools_path,"w") as f:
                    f.write(r.text)
            except requests.exceptions.RequestException as e:
                debug_log(e)

        if not os.path.exists(json_tools_path):
            return
            
        with open(json_tools_path,"r") as tools_url_file:
            tools_json = json.load(tools_url_file)
            
            tw.setColumnCount(4)
            tw.headerItem().setHidden(False)
            tw.headerItem().setText(0,"Name")
            tw.headerItem().setText(1,"Category")
            tw.headerItem().setText(2,"Download")
            tw.headerItem().setText(3,"Status")
            req = QTreeWidgetItem()
            req.setText(0,"Required")
#            req.setCheckState(0,2)
            tw.addTopLevelItem(req)
            opt = QTreeWidgetItem()
            opt.setText(0,"Optional")
#            opt.setCheckState(0,0)
            tw.addTopLevelItem(opt)
            
            for title, values in tools_json.items():
                item = QTreeWidgetItem()
                item.setText(0,title)
                font = item.font(0)
                font.setBold(True)
                item.setFont(0,font)
                required = values['required']
                if required:
                    req.addChild(item)
                    item.setCheckState(0,2)
                else:
                    opt.addChild(item)
                    item.setCheckState(0,0)
                if self.checkInstalled(title):   
                    item.setText(3,"Installed")
                    item.setDisabled(True)
                    item.setCheckState(0,2)
                else:
                    item.setText(3,"Not installed")                    
                url = values['url']
                install_dir = values['install_dir']
                item.setData(0,dataURL,url)
                item.setData(0,dataInstallDir,install_dir)
                category = values['category']
                item.setText(1,category)
                platform = values['platform']
                description = values['description']
                di = QTreeWidgetItem()
                label = QLabel(description)
                label.setWordWrap(True)
                item.addChild(di)
                tw.setItemWidget(di,0,label)
                tw.setFirstItemColumnSpanned(di,False)
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
            url_test = item.data(0,dataURL)
            if url_test is not None:
                try:
                    r = requests.head(url_test)
                    r.raise_for_status()
                    try:
                        size = (int(r.headers['Content-Length'])/1024)/1024
                    except:
                        size=0
                    if size > 0:
                        item.setText(2,"{} MiB".format(round(size,2)))
                except requests.exceptions.HTTPError:
                    debug_log("Error {} getting DL size: {}".format(r.status_code,r.headers))
                    item.setText(2,r.status_code)
                except requests.exceptions.RequestException as e:
                    item.setText(2,"Error")
                    debug_log(e)
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
                url_test = item.data(0,dataURL)
                install_dir = item.data(0,dataInstallDir)
                if url_test is not None:
                    fn = os.path.basename(url_test)
                    self.statusLabel.setText("Downloading {}...".format(fn))
                    QApplication.processEvents()
                    try:
                        r = requests.get(url_test)
                        r.raise_for_status()
                        debug_log("{}".format(r.headers))
                        with open(app_dirs.user_cache_dir + "/" + fn,"wb") as zip:
                            zip.write(r.content)
                        self.installZip(app_dirs.user_cache_dir + "/" + fn,install_dir)
                        item.setText(3,"Installed")
                        QApplication.processEvents()
                        item.setDisabled(True)
                    except requests.exceptions.HTTPError:
                        debug_log("Error {} downloading file {}, headers: {}".format(r.status_code,url_test,r.headers))
                    except requests.exceptions.RequestException as e:
                        debug_log(e)                        
            self.statusLabel.setText("")
            it += 1
        self.install_button.setEnabled(True)

    def installZip(self,fn,install_dir):
        debug_log("installZip: Installing {} to {}...".format(fn,install_dir))
        self.statusLabel.setText("Installing {}...".format(os.path.basename(fn)))
        QApplication.processEvents()
        zip = zipfile.ZipFile(fn)
        zip.extractall(path=app_dirs.user_cache_dir + "/" + install_dir)
        self.statusLabel.setText("")
        QApplication.processEvents()