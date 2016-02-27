#!/usr/bin/env python3

#    Specton Audio Analyser
#    Copyright (C) 2016 D. Bird <somesortoferror@gmail.com>
#    https://github.com/somesortoferror/specton

version = 0.15

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
from PyQt5.QtWidgets import QWidget, QApplication, QDialog, QMainWindow, QAction, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, QMenu, QLineEdit,QCheckBox,QSpinBox,QSlider,QTextEdit,QTabWidget,QLabel,QGridLayout,QPushButton
from PyQt5 import uic
from PyQt5.QtCore import QByteArray, Qt, QSettings, QTimer
from PyQt5.QtGui import QPixmap, QColor
import os.path
import os
from os import walk
import fnmatch, re
import subprocess
from multiprocessing import Pool, Process,freeze_support, Queue,set_executable, Lock as mp_lock
from time import sleep, clock
from io import TextIOWrapper
from functools import partial
from hashlib import md5
import zlib
import tempfile
from spcharts import Bitrate_Chart, BitGraph, NavigationToolbar
import logging
import string
import json

dataScanned=32
dataFilenameStr=33
dataRawOutput=34
dataBitrate=35

# define some colours
colourQualityUnknown = QColor(Qt.lightGray)
colourQualityUnknown.setAlpha(100)
colourQualityGood = QColor(Qt.green)
colourQualityGood.setAlpha(100)
colourQualityWarning = QColor(Qt.yellow)
colourQualityWarning.setAlpha(100)
colourQualityBad = QColor(Qt.red)
colourQualityBad.setAlpha(100)

defaultfilemask = r"\.mp3$|\.flac$|\.mpc$|\.ogg$|\.wav$|\.m4a$|\.aac$|\.ac3$|\.ra$|\.au$"

class fakestd(object):
    def write(self, string):
        pass

    def flush(self):
        pass

def debug_log(debug_str):
    logging.debug(debug_str)
        
if os.name == 'nt':
    if sys.stdout is not None:
        sys.stdout = TextIOWrapper(sys.stdout.buffer,sys.stdout.encoding,'backslashreplace') # fix for printing utf8 strings on windows
    else:
        # win32gui doesn't have a console
        sys.stdout = fakestd()
        sys.stderr = fakestd()

if __name__ == '__main__':
    freeze_support() # PyInstaller requires this
    main_q = Queue()
    infodlg_q = Queue()
    infodlg_list = [] # list of dialog windows
    
    form_class = uic.loadUiType("specton.ui")[0]                 # Load the UI
    options_class = uic.loadUiType("options.ui")[0]
    fileinfo_class = uic.loadUiType("info.ui")[0]

    settings = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-settings")
    filecache = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-cache")
        
    debug_enabled = settings.value("Options/Debug", False, type=bool)
    stop_tasks = False
    
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s - %(message)s')

def findBinary(settings_key="", nt_path="", posix_path=""):
    bin = settings.value(settings_key)
    if bin is None:
        if os.name == 'nt':
            return nt_path
        elif os.name == 'posix':
            return posix_path
        
    return bin

findGuessEncBin = partial(findBinary,'Paths/mp3guessenc_bin','scanners/mp3guessenc.exe','/usr/local/bin/mp3guessenc')
findMediaInfoBin = partial(findBinary,'Paths/mediainfo_bin','scanners/MediaInfo.exe','/usr/bin/mediainfo')
findFlacBin = partial(findBinary,'Paths/flac_bin','scanners/flac.exe','/usr/bin/flac')
findauCDtectBin = partial(findBinary,'Paths/aucdtect_bin','scanners/auCDtect.exe','/usr/bin/aucdtect')
findSoxBin = partial(findBinary,'Paths/sox_bin','scanners/sox.exe','/usr/bin/sox')

def findffprobeBin(settings_key='Paths/ffprobe_bin', nt_path='scanners/ffmpeg/ffprobe.exe', posix_path='/usr/bin/ffprobe'):
    bin = settings.value(settings_key)
    if bin is None:
        if os.name == 'nt':
            return nt_path
        elif os.name == 'posix':
            if os.path.exists(posix_path): # ffprobe
                return posix_path
            elif os.path.exists(os.path.dirname(posix_path) + "/avprobe"): # also try avprobe
                return os.path.dirname(posix_path) + "/avprobe"
        
    return bin
        
def getTempFileName():
    temp_file = tempfile.NamedTemporaryFile()
    temp_file_str = temp_file.name
    temp_file.close()
    return temp_file_str
    

def scanner_Thread(row,filenameStr,binary,scanner_name,options,debug_enabled):
# run scanner on filenameStr as separate process
# and return output as strings
    if debug_enabled:
        debug_log("thread started for row {}, file: {}".format(row,filenameStr))
    try:
        output = subprocess.check_output([binary,options,filenameStr])
        output_str = output.decode(sys.stdout.encoding)
    except:
        output_str = "Error"
    return row,output_str,filenameStr,scanner_name

def aucdtect_Thread(row,filenameStr,decoder_bin,decoder_options,aucdtect_bin,aucdtect_options,debug_enabled):
    if debug_enabled:
        debug_log("aucdtect thread started for row {}, file: {}".format(row,filenameStr))
    try:
        temp_file = getTempFileName()
        decoder_output = subprocess.check_output([decoder_bin,decoder_options,filenameStr,"-o",temp_file],stderr=subprocess.PIPE)
        aucdtect_output = subprocess.check_output([aucdtect_bin,aucdtect_options,temp_file],stderr=subprocess.PIPE)
        output_str = aucdtect_output.decode(sys.stdout.encoding)
    except:
        output_str = "Error"
    
    try:
        os.remove(temp_file)
    except OSError:
        pass
        
    return (row,output_str,filenameStr)

def scanner_Finished(fileinfo):
# callback function
# runs after scanner process has completed
    i = fileinfo[0]
    scanner_output = fileinfo[1]
    filenameStr = fileinfo[2]
    scanner_name = fileinfo[3]
    global task_count
    task_count -= 1

    if not (scanner_output == "Error"):
        if scanner_name == "mp3guessenc":
            song_info = parse_mp3guessenc_output(scanner_output)
        elif scanner_name == "mediainfo":
            song_info = parse_mediainfo_output(scanner_output)
        else: # unknown
            debug_log("scanner thread finished but scanner unknown")
            return
        if debug_enabled:
            debug_log("thread finished - row {}, result: {}, task count={}".format(i,song_info['encoder'],task_count))
    
        main_q.put((i,song_info,scanner_output))
    else:
        main_q.put((i,{'error':True},scanner_output))
        if debug_enabled:
            debug_log("thread finished with error - row {}, result: {}, task count={}".format(i,scanner_output,task_count))

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
            debug_log("aucdtect thread finished - row {}, result: {}, task count={}".format(i,song_info['aucdtect_quality'],task_count))
    
        main_q.put((i,song_info,scanner_output))
    else:
        main_q.put((i,{'error':True},scanner_output))
        if debug_enabled:
            debug_log("aucdtect thread finished with error - row {}, result: {}, task count={}".format(i,scanner_output,task_count))

    
if __name__ == '__main__':
    TableHeaders = ["Folder","Filename","Length","Bitrate","Mode","Frequency","Filesize","Encoder","Quality"]
    task_count = 0

if __name__ == '__main__':
    guessenc_encoder_regex = re.compile(r"^Maybe this file is encoded by (.*)",re.MULTILINE)
    guessenc_encoder_string_regex = re.compile(r"^Encoder string \: (.*)",re.MULTILINE)
    guessenc_bitrate_regex = re.compile(r"Data rate.*\: (.*)",re.MULTILINE)
    guessenc_length_regex = re.compile(r"Length.*\: ([\d\:\.]*)",re.MULTILINE)
    guessenc_frequency_regex = re.compile(r"^\s*Audio frequency\s*: (\d*) Hz",re.MULTILINE)
    guessenc_mode_regex = re.compile(r"Detected MPEG stream.*?Encoding mode\s*?: (.*?)\n",re.DOTALL)
    guessenc_filesize_regex = re.compile(r"Detected .*?\n  File size.*?\: (\d*) bytes",re.MULTILINE)
    guessenc_frame_hist_regex = re.compile(r"Frame histogram(.*?)(\d*) header errors",re.DOTALL)
    guessenc_block_usage_regex = re.compile(r"^Block usage(.*?)-",re.DOTALL|re.MULTILINE)
    guessenc_mode_count_regex = re.compile(r"^Mode extension: (.*?)--",re.DOTALL|re.MULTILINE)
    guessenc_header_errors_regex = re.compile(r"^\s*(\d*) header errors",re.MULTILINE)
    mediainfo_format_regex = re.compile(r"^Audio.*?Format.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_encoder_regex = re.compile(r"^Writing library.*\: (.*)",re.MULTILINE)
    mediainfo_length_regex = re.compile(r"^Audio.*?Duration.*?\: (.*?)$",re.DOTALL|re.MULTILINE)
    mediainfo_bitrate_regex = re.compile(r"^Bit rate.*\: ([\d\. ]* [MK]bps)",re.MULTILINE)
    mediainfo_filesize_regex = re.compile(r"^File size.*\: (.* .iB|.* Bytes)",re.MULTILINE)
    aucdtect_regex = re.compile(r"^This track looks like (.*) with probability (\d*)%",re.MULTILINE)
    mp3_bitrate_data_regex = re.compile(r"(\d*?) kbps \: *(\d*?) \(")

    
def doMP3Checks(bitrate,encoder,encoder_string,header_errors,mp3guessenc_output):
# do some MP3 quality checks here
    colour = colourQualityUnknown
    
    if int(header_errors) > 0:
        colour = colourQualityBad

    return colour

    
def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "{:3.1f} {}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:.1f} {}{}".format(num, 'Yi', suffix)
    
def get_bitrate_hist_data(frame_hist):
    x = []
    y = []
    
    if frame_hist is not None:
        for line in str.splitlines(frame_hist):
            search = mp3_bitrate_data_regex.search(line)
            if search is not None:
                bitrate = search.group(1)
                x.append(int(bitrate))
                framecount = search.group(2)
                y.append(int(framecount))
    
    return (x,y)
    
    
def parse_mp3guessenc_output(mp3guessenc_output):
# parse mp3guessenc output using regex
# return parsed variables as a dictionary
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""
    frame_hist=() # tuple containing two sets of int lists
    block_usage=""
    mode_count=""
    mode=""
    frequency=""
    header_errors=0

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
        frame_hist=get_bitrate_hist_data(search.group(1))
    search = guessenc_block_usage_regex.search(mp3guessenc_output)
    if search is not None:
        block_usage=search.group(1)
    search = guessenc_mode_count_regex.search(mp3guessenc_output)
    if search is not None:
        mode_count=search.group(1)
    search = guessenc_mode_regex.search(mp3guessenc_output)
    if search is not None:
        mode=string.capwords(search.group(1))
    search = guessenc_frequency_regex.search(mp3guessenc_output)
    if search is not None:
        frequency_int=int(search.group(1))
        frequency = "{} KHz".format(frequency_int/1000)
    search = guessenc_header_errors_regex.search(mp3guessenc_output)
    if search is not None:
        header_errors=search.group(1)

    quality_colour = doMP3Checks(bitrate,encoder,encoder_string,header_errors,mp3guessenc_output)
        
    return {'encoder':encoder, 'audio_format':'MP3', 'bitrate':bitrate ,'encoder_string':encoder_string, 
            'length':length, 'filesize':filesize, 'error':False, 'frame_hist':frame_hist, 
            'block_usage':block_usage, 'mode_count':mode_count, 'mode':mode,'frequency':frequency,'quality':None,'quality_colour':quality_colour }

def parse_mediainfo_output(mediainfo_output):
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""
    audio_format="Unknown"

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
            'length':length, 'filesize':filesize, 'error':False, 'quality':None}

def parse_aucdtect_output(aucdtect_output):
    detection = ""
    probability = ""
    quality_colour = colourQualityUnknown

    search = aucdtect_regex.search(aucdtect_output)
    if search is not None:
        detection=search.group(1)
        probability=search.group(2)
    else:
        detection="Unknown"

    try:
        prob_int = int(probability)
    except ValueError:
        prob_int = 0
        
    if detection == "CDDA":
        if prob_int > 90:
            quality_colour = colourQualityGood
        else:
            quality_colour = colourQualityWarning
    elif detection == "MPEG":
        if prob_int > 90:
            quality_colour = colourQualityBad
        else:
            quality_colour = colourQualityWarning
    
    if not detection == "Unknown":
        aucdtect_quality = "{} {}%".format(detection,probability)
    else:
        aucdtect_quality = detection
    
    return {'error':False,'aucdtect_quality':aucdtect_quality,'quality_colour':quality_colour}
    
def md5Str(Str):
    return md5(Str.encode('utf-8')).hexdigest()
            
def headerIndexByName(table,headerName):
    index = -1
    for i in range(0, table.columnCount()):
        headerItem = table.horizontalHeaderItem(i)
        if headerItem.text() == headerName:
            index = i
    return index
    
def makeBitGraph(fn,grid,ffprobe_bin):
    try:
        output = subprocess.check_output([ffprobe_bin,"-show_packets","-of","json",fn],stderr=None)
        output_str = output.decode(sys.stdout.encoding)
    except Exception as e:
        if debug_enabled:
            debug_log(e)
            return None
    
    x_list = []
    y_list = []
    
    json_packet_data = json.loads(output_str)
    packets = json_packet_data["packets"]
    
    for dict in packets:
        if not dict["codec_type"] == "audio":
            continue
        try:
            x = float(dict["pts_time"]) # time
        except (ValueError, OverflowError) as e:
            x = 0
        try:
            t = float(dict["duration_time"]) # duration
        except (ValueError, OverflowError) as e:
            t = 0
        try:
            sz = float(dict["size"]) # size in bytes
        except (ValueError, OverflowError) as e:
            sz = 0
        try:
            y = round((sz*8)/1000/t)
        except (ValueError, OverflowError) as e:
            y = 0
        
        if y > 0:
            y_list.append(y) # bitrate
            x_list.append(round(x,3))
        
#uncomment this to write out bitrate data in csv
    
#    if debug_enabled:
#        temp_file = open(temp_file_str + ".csv","w")
#        for i in range(0,len(x_list)):
#            temp_file.write(str(x_list[i]) + "," + str(y_list[i]) + "\n")
#        temp_file.close()
    
    return ((x_list,y_list),fn,grid)

class FileInfo(QDialog):
    def __init__(self,filenameStr,scanner_output,frame_hist):
        super(FileInfo,self).__init__()
        self.ui = fileinfo_class()
        self.ui.setupUi(self)
        self.setWindowTitle("Info - {}".format(os.path.basename(filenameStr)))
        self.filename = filenameStr
        infodlg_list.append(self)
        
        windowGeometry = settings.value("State/InfoWindowGeometry")
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)

        closeButton = self.findChild(QTabWidget, "")
    
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        tabWidget.clear()
        textEdit_scanner = QTextEdit()
        textEdit_scanner.setReadOnly(True)
        textEdit_scanner.setPlainText(scanner_output)
        tabWidget.addTab(textEdit_scanner,"Scanner Output")
        if frame_hist is not None:
            x = frame_hist[0]
            y = frame_hist[1]
        else:
            x = []
            y = []
        if debug_enabled:
            debug_log("Frame histogram - {}".format(frame_hist))
            debug_log("Frame histogram - {}".format(x))
            debug_log("Frame histogram - {}".format(y))
        if len(x) > 0:
            try:
                sc = Bitrate_Chart(self, width=5, height=4, dpi=100, x=x, y=y)
                tabWidget.addTab(sc,"Bitrate Distribution")
            except Exception as e:
                debug_log(e)
                
        updateGuiTimer = QTimer(self)
        updateGuiTimer.timeout.connect(self.updateGui)
        updateGuiTimer.setInterval(1000)
        updateGuiTimer.start()
                
        infopool = Pool(None)
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
            
            infopool.apply_async(makeSpectrogram, args=(filenameStr,sox_bin,temp_file,palette,grid.objectName()),callback=spectrogramCallback)
            
        if settings.value('Options/EnableBitGraph',True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("BitgraphLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab,"Bitrate Graph")
            if debug_enabled:
                debug_log("Running ffprobe to create bitrate graph for file {}".format(filenameStr))
            infopool.apply_async(makeBitGraph, args=(filenameStr,grid.objectName(),findffprobeBin()),callback=bitgraphCallback)
               
        infopool.close()
         
    def updateGui(self):
    # called from timer every 1s
    # subprocesses post to queue when finished
        if not infodlg_q.empty():
            update_info = infodlg_q.get(False,1)
            update_type = update_info[0]
            update_data = update_info[1]
            update_layout = update_info[2]
            update_filename = update_info[3]

            if update_type == "Spectrogram":
                if debug_enabled:
                    debug_log("updateGui received Spectrogram update")
                px = QLabel()
                dlg = findDlg(update_filename)
                if dlg is not None:
                    layout = dlg.findChild(QGridLayout,update_layout)
                    if layout is not None:
                        layout.addWidget(px)
                        px.setPixmap(QPixmap(update_data))
                    else:
                        debug_log("updateGui ran but layout not found type={} str={} layout={}".format(update_type,update_data,update_layout))
                else:
                    debug_log("updateGui couldn't find dlg type={} str={} layout={}".format(update_type,update_data,update_layout))                    
                os.remove(update_data) # delete generated spectrogram image

            elif update_type == "BitGraph":
                if debug_enabled:
                    debug_log("updateGui received BitGraph update")
                x = update_data[0]
                y = update_data[1]
                try:
                    sc = BitGraph(self, width=5, height=4, dpi=100, x=x, y=y)
                    dlg = findDlg(update_filename)
                    if dlg is not None:
                        layout = dlg.findChild(QGridLayout,update_layout)
                        if layout is not None:
                            layout.addWidget(sc)
                            mpl_toolbar = NavigationToolbar(sc, self)
                            layout.addWidget(mpl_toolbar)
                except Exception as e:
                    debug_log(e)
                        
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

def makeSpectrogram(fn,sox_bin,temp_file,palette,grid):
    try:
        sox_output = subprocess.check_output([sox_bin,fn,"-n","spectrogram","-p{}".format(palette),"-o",temp_file],stderr=subprocess.PIPE)
    except Exception as e:
        if debug_enabled:
            debug_log(e)
        temp_file = ""
    return (temp_file,grid,fn)

def spectrogramCallback(data):
    if debug_enabled:
        debug_log("spectrogramCallback called")
    spec_file = data[0]
    grid_name = data[1]
    fn = data[2]
    if not spec_file == "":
        try:
            infodlg_q.put(("Spectrogram",spec_file,grid_name,fn)) # Timer watches this queue and updates gui
        except Exception as e:
            debug_log(e)

def bitgraphCallback(data):
    if debug_enabled:
        debug_log("bitgraphCallback called")
    graph_data_xy_tuple = data[0]
    grid_name = data[2]
    fn = data[1]
    if graph_data_xy_tuple is not None:
#        if debug_enabled:
#            debug_log(graph_data_xy_tuple)
        infodlg_q.put(("BitGraph",graph_data_xy_tuple,grid_name,fn))
        
                
class Options(QDialog):
    def __init__(self):
        super(Options,self).__init__()
        self.ui = options_class()
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
        
    def choosePathButton(self):
        sender = self.sender()
        if sender.objectName() == "pushButton_mediainfo_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        elif sender.objectName() == "pushButton_mp3guessenc_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        elif sender.objectName() == "pushButton_sox_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_sox_path")
        elif sender.objectName() == "pushButton_ffprobe_path":
            lineEdit = self.findChild(QLineEdit, "lineEdit_ffprobe_path")
        if lineEdit is not None:
            path = lineEdit.text()
            file = str(QFileDialog.getOpenFileName(parent=self,caption="Browse to executable file",directory=path)[0])
            if not file == "":
                lineEdit.setText(file)
        
    def accept(self):
        lineEdit_filemaskregex = self.findChild(QLineEdit, "lineEdit_filemaskregex")
        settings.setValue('Options/FilemaskRegEx',lineEdit_filemaskregex.text())
        lineEdit_mediainfo_path = self.findChild(QLineEdit, "lineEdit_mediainfo_path")
        settings.setValue('Paths/mediainfo_bin',lineEdit_mediainfo_path.text())
        lineEdit_mp3guessenc_path = self.findChild(QLineEdit, "lineEdit_mp3guessenc_path")
        settings.setValue('Paths/mp3guessenc_bin',lineEdit_mp3guessenc_path.text())
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
        bitrateItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Bitrate"))
        filenameStr = filenameItem.data(dataFilenameStr)
        dlg = findDlg(filenameStr)
        if dlg is None:
            if debug_enabled:
                debug_log("contextViewInfo: dialog was None")
            dlg = FileInfo(filenameStr,codecItem.data(dataRawOutput),bitrateItem.data(dataBitrate))
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
    
    def select_Folder(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory to Scan", os.path.expanduser("~")))
        filemask = settings.value('Options/FilemaskRegEx',defaultfilemask)
        
        try:
            filemask_regex = re.compile(filemask,re.IGNORECASE)
        except re.error as e:
            debug_log("Error in filemask regex: {}, using default".format(e))
            filemask_regex = re.compile(defaultfilemask,re.IGNORECASE)
            
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
                    frequencyItem = QTableWidgetItem("")
                    modeItem = QTableWidgetItem("")
                    
                    if usecache:
                        hashStr = filenameStr + str(os.path.getmtime(filenameStr))
                        filemd5 = md5Str(hashStr)
                        if filecache.value('{}/Encoder'.format(filemd5)) is not None:
                            codecItem.setText(filecache.value('{}/Encoder'.format(filemd5)))
                            bitrateItem.setText(filecache.value('{}/Bitrate'.format(filemd5)))
                            lengthItem.setText(filecache.value('{}/Length'.format(filemd5)))
                            filesizeItem.setText(filecache.value('{}/Filesize'.format(filemd5)))
                            cached_output = filecache.value('{}/RawOutput'.format(filemd5))
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
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Frequency"), frequencyItem)
                    self.ui.tableWidget.setItem(i, headerIndexByName(self.ui.tableWidget,"Mode"), modeItem)
                                                      
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
        
    def update_Table(self,row,song_info,scanner_output,usecache=True):
        # update table with info from scanner
            error_status = song_info['error']
            if not error_status:
                filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
                filenameStr = filenameItem.data(dataFilenameStr)
#                usecache = settings.value('Options/UseCache',True, type=bool)
                if usecache:
                    hashStr = filenameStr + str(os.path.getmtime(filenameStr))
                    filemd5 = md5Str(hashStr)

                try:
                    quality_colour = song_info['quality_colour']
                except KeyError:
                    quality_colour = None
                    
                if quality_colour is not None:
                    qualityItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Quality"))
                    qualityItem.setBackground(quality_colour)
                    if usecache:
                        filecache.setValue('{}/QualityColour'.format(filemd5),qualityItem.background())
                
                try:
                    aucdtect_quality = song_info['aucdtect_quality']
                except KeyError:
                    aucdtect_quality = None

                if aucdtect_quality is not None:
                    # aucdtect
                    qualityItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Quality"))
                    qualityItem.setText(aucdtect_quality)
                    if usecache:
                        filecache.setValue('{}/Quality'.format(filemd5),aucdtect_quality)
                else: # not aucdtect
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
                    try:
                        frame_hist = song_info['frame_hist']
                        bitrateItem.setData(dataBitrate,frame_hist)
                    except KeyError:
                        pass
                        
                    try:
                        frequencyItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Frequency"))
                        frequency = song_info['frequency']
                        frequencyItem.setText(frequency)
                    except KeyError:
                        pass
                        
                    try:
                        modeItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Mode"))
                        mode = song_info['mode']
                        modeItem.setText(mode)
                    except KeyError:
                        pass

                    lengthItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Length"))
                    lengthItem.setText(song_info['length'])
                    filesizeItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filesize"))
                    filesizeItem.setText(song_info['filesize'])

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
                        if settings.value('Options/CacheRawOutput',False, type=bool) == True:
                            filecache.setValue('{}/RawOutput'.format(filemd5),zlib.compress(scanner_output.encode('utf-8')))

            else: # error status
                codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
                codecItem.setText("error scanning file")
                codecItem.setData(dataRawOutput,scanner_output)
            
            QApplication.processEvents()
    
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
                    debug_log("Queuing process for file {}".format(filenameStr))
                    
                if fnmatch.fnmatch(filenameStr, "*.mp3"):
                    # use mp3guessenc if available
                    if not mp3guessencbin == "":
                        pool.apply_async(scanner_Thread, args=(i,filenameStr,mp3guessencbin,"mp3guessenc","-e",debug_enabled), callback=scanner_Finished) # queue processes
                        task_count += 1
                        task_total += 1
                    elif not mediainfo_bin == "": # fall back to mediainfo
                        pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled), callback=scanner_Finished)
                        task_count += 1
                        task_total += 1
                        
                elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled), callback=scanner_Finished)
                    task_count += 1
                    task_total += 1
                elif not mediainfo_bin == "":
                    pool.apply_async(scanner_Thread, args=(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled), callback=scanner_Finished)
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

        self.statusBar().showMessage('Scanning files...')
        usecache = settings.value('Options/UseCache',True, type=bool)
        
        global stop_tasks
        while (task_count > 0) and (not stop_tasks):
            tasks_done = task_total - task_count
            self.ui.progressBar.setValue(round((tasks_done/task_total)*100))
            QApplication.processEvents()
            sleep(0.025)

            if not main_q.empty():
            # scanner processes add results to main_q when finished
                q_info = main_q.get(False,5)
                row = q_info[0]
                song_info = q_info[1]
                scanner_output = q_info[2]
                self.update_Table(row,song_info,scanner_output,usecache)
                        
        if debug_enabled:
            debug_log("all threads finished, task count={}".format(task_count))

        if stop_tasks:
            pool.terminate()
            stop_tasks = False
        
        while not main_q.empty():
        # keep going until results queue is empty
            q_info = main_q.get(False,5)
            row = q_info[0]
            song_info = q_info[1]
            scanner_output = q_info[2]
            self.update_Table(row,song_info,scanner_output,usecache)
                           
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
                                """Specton Audio Analyser v{}
                                
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
along with this program.  If not, see <http://www.gnu.org/licenses/>.""".format(version)
                                )
if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
