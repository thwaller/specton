#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

#    Specton Audio Analyser
#    Copyright (C) 2016 D. Bird <somesortoferror@gmail.com>
#    https://github.com/somesortoferror/specton

version = 0.161

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

import fnmatch
import json
import logging
import os
import queue
import re
import string
import subprocess
import sys
import tempfile
from functools import partial
from hashlib import md5
from io import TextIOWrapper
from time import sleep, ctime, asctime, gmtime, strftime

from PyQt5.QtCore import Qt, QSettings, QTimer, QThreadPool, QRunnable, QMutex, QReadLocker, QWriteLocker, QReadWriteLock, QEvent, QObject
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import QWidget, QApplication, QDialog, QDialogButtonBox,QMainWindow, QAction, QFileDialog, QTableWidgetItem, QMessageBox, QMenu, QLineEdit,QCheckBox,QSpinBox,QSlider,QTextEdit,QTabWidget,QLabel,QGridLayout,QPushButton
from spcharts import Bitrate_Chart, BitGraph, NavigationToolbar
from spct_info import Ui_FileInfoDialog
from spct_main import Ui_MainWindow
from spct_options import Ui_optionsDialog

dataScanned=32
dataFilenameStr=33
dataBitrate=35

aucdtect_confidence_threshold=90 # aucdtect results considered accurate when probability is higher than this

# define some colours
colourQualityUnknown = QColor(Qt.lightGray)
colourQualityUnknown.setAlpha(100)
colourQualityGood = QColor(Qt.green)
colourQualityGood.setAlpha(100)
colourQualityOk = QColor(Qt.darkGreen)
colourQualityOk.setAlpha(100)
colourQualityWarning = QColor(Qt.yellow)
colourQualityWarning.setAlpha(100)
colourQualityBad = QColor(Qt.red)
colourQualityBad.setAlpha(100)

defaultfilemask = r"\.mp3$|\.opus$|\.flac$|\.mpc$|\.ogg$|\.wav$|\.m4a$|\.aac$|\.ac3$|\.ra$|\.au$"

class fakestd(object):
    encoding = 'utf-8'
    def write(self, string):
        pass

    def flush(self):
        pass

def debug_log(debug_str):
    logging.debug(debug_str)
    
frozen = bool(getattr(sys, 'frozen', False))
        
if os.name == 'nt': # various hacks
    if not frozen:
        if sys.stdout is not None:
            sys.stdout = TextIOWrapper(sys.stdout.buffer,sys.stdout.encoding,'backslashreplace') # fix for printing utf8 strings on windows
        else:
            # win32gui doesn't have a console
            sys.stdout = fakestd()
            sys.stderr = fakestd()
    else: # frozen
        sys.stdout = fakestd()
        sys.stderr = fakestd()
        

if __name__ == '__main__':
    main_q = queue.Queue()
    infodlg_q = queue.Queue()
    infodlg_list = [] # list of dialog windows
    infodlg_threadpool = QThreadPool(None)
    scanner_threadpool = QThreadPool(None)
    TableHeaders = ["Folder","Filename","Length","Bitrate","Mode","Frequency","Filesize","Encoder","Quality"]
    ql = QReadWriteLock()
    task_count = 0
    task_total = 0
    file_hashlist = []
    
    settings = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-settings")
    filecache = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-cache")
        
    debug_enabled = settings.value("Options/Debug", False, type=bool)
    
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s - %(message)s')

def findBinary(settings_key="", nt_path="", posix_path=""):
# find executable files
# use paths from settings if available else use default locations
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
findSoxBin = partial(findBinary,'Paths/sox_bin','scanners/sox/sox.exe','/usr/bin/sox')


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

def runCmd(cmd,cmd_timeout=300):
# run command without showing console window on windows
# return stdout as string
    startupinfo = None
    output = ""
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        proc = subprocess.Popen(cmd,bufsize=-1,startupinfo=startupinfo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=None,shell=False,universal_newlines=True)
    except Exception as e:
        proc = None
        debug_log("exception in runCmd: {}".format(e))
    if proc is not None:
        try:
            output, unused_err = proc.communicate()
        except TimeoutExpired(timeout=cmd_timeout):
            proc.kill()
            debug_log("runCmd: Process killed due to timeout")
    return output

class scanner_Thread(QRunnable):
    def __init__(self,row,filenameStr,binary,scanner_name,options,debug_enabled,fileinfo_dialog_update=False,cmd_timeout=300):
        super(scanner_Thread, self).__init__()
        self.row = row
        self.filenameStr = filenameStr
        self.binary = binary
        self.scanner_name = scanner_name
        self.options = options
        self.debug_enabled = debug_enabled
        self.fileinfo_dialog_update = fileinfo_dialog_update
        self.cmd_timeout = cmd_timeout
        
    def run(self):
        output_str = ""
        if self.debug_enabled:
            debug_log("scanner thread running for row {}, file: {}".format(self.row,self.filenameStr))
        
        if os.path.lexists(self.filenameStr): 
            try:
                output_str = runCmd([self.binary,self.options,self.filenameStr],self.cmd_timeout)
            except:
                output_str = "Error"
        else:
            output_str = "Error" # handle the case where file has been deleted while in queue e.g. temp files or user deletion
        
        with QWriteLocker(ql):
            global task_count
            task_count -= 1
        
        if self.fileinfo_dialog_update:
            infodlg_q.put(("Scanner_Output",output_str,self.row,self.filenameStr))
            return

        if not (output_str == "Error"):
            if self.scanner_name == "mp3guessenc":
                song_info = parse_mp3guessenc_output(output_str)
            elif self.scanner_name == "mediainfo":
                song_info = parse_mediainfo_output(output_str)
            else: # unknown
                debug_log("scanner thread finished but scanner unknown")
                return
            if self.debug_enabled:
                debug_log("scanner thread finished - row {}, result: {}, task count={}".format(self.row,song_info['encoder'],task_count))
    
            if self.debug_enabled:
                debug_log("scanner thread posting to queue - row {}".format(self.row))
            main_q.put((self.row,song_info,output_str))
        else:
            if self.debug_enabled:
                debug_log("scanner thread posting to queue with error - row {}".format(self.row))
            main_q.put((self.row,{'result_type':'Scanner_Output','error':True},output_str))
            if self.debug_enabled:
                debug_log("scanner thread finished with error - row {}, result: {}, task count={}".format(self.row,output_str,task_count))
                
class aucdtect_Thread(QRunnable):
# run aucdtect on a file and post results to queue
    def __init__(self,row,filenameStr,decoder_bin,decoder_options,aucdtect_bin,aucdtect_options,debug_enabled,cmd_timeout):
        super(aucdtect_Thread, self).__init__()
        self.row = row
        self.filenameStr = filenameStr
        self.decoder_bin = decoder_bin
        self.decoder_options = decoder_options
        self.aucdtect_bin = aucdtect_bin
        self.aucdtect_options = aucdtect_options
        self.debug_enabled = debug_enabled
        self.cmd_timeout = cmd_timeout

    def run(self):
        temp_file = ""
        if self.debug_enabled:
            debug_log("aucdtect thread started for row {}, file: {}".format(self.row,self.filenameStr))
        if os.path.lexists(self.filenameStr): 
            try:
                temp_file = getTempFileName()
                if not self.decoder_bin == "": # need to decode to wav
                    decoder_output = runCmd([self.decoder_bin,self.decoder_options,self.filenameStr,"-o",temp_file],self.cmd_timeout)
                    output_str = runCmd([self.aucdtect_bin,self.aucdtect_options,temp_file],self.cmd_timeout)
                else:
                    output_str = runCmd([self.aucdtect_bin,self.aucdtect_options,self.filenameStr],self.cmd_timeout)
            except:
                output_str = "Error"
        else:
            output_str = "Error"
    
        try:
            os.remove(temp_file)
        except OSError:
            pass
        
        with QWriteLocker(ql):
            global task_count
            task_count -= 1

        if not (output_str == "Error"):
            song_info = parse_aucdtect_output(output_str)

            if debug_enabled:
                debug_log("aucdtect thread finished - row {}, result: {}, task count={}".format(self.row,song_info['quality'],task_count))
    
            main_q.put((self.row,song_info,output_str))
        else:
            main_q.put((self.row,{'result_type':'Scanner_Output','error':True},output_str))
            if debug_enabled:
                debug_log("aucdtect thread finished with error - row {}, result: {}, task count={}".format(self.row,output_str,task_count))

            
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
    mediainfo_bitrate_regex = re.compile(r"^Bit rate.*?\: |^General.*Overall bit rate\s*?\:\s*?([\d\.]* [GMK]bps)",re.MULTILINE|re.DOTALL)
    mediainfo_bitrate_mode_regex = re.compile(r"^Audio.*Bit rate mode\s*: ([A-Za-z]*)",re.MULTILINE|re.DOTALL) # variable or constant
    mediainfo_filesize_regex = re.compile(r"^File size.*\: (.* .iB|.* Bytes)",re.MULTILINE)
    mediainfo_frequency_regex = re.compile(r"^Audio.*Sampling rate\s*: ([\d\.]* KHz)",re.MULTILINE|re.DOTALL)
    mediainfo_bitdepth_regex = re.compile(r"^Audio.*Bit depth\s*: ([\d\.]*) bits",re.MULTILINE|re.DOTALL)
    mediainfo_mode_regex = re.compile(r"^Audio.*[Mm]ode\s*: ([a-zA-Z ]*)",re.MULTILINE|re.DOTALL) # stereo/js
    aucdtect_regex = re.compile(r"^This track looks like (.*) with probability (\d*)%",re.MULTILINE)
    mp3_bitrate_data_regex = re.compile(r"(\d*?) kbps \: *(\d*?) \(")
    mp3_lame_tag_preset_regex = re.compile(r"^Lame tag.*Preset\s*:\s*(.*?)Orig",re.MULTILINE|re.DOTALL)
    mp3_xing_quality_regex = re.compile(r"^Xing.*?Quality\s*?:\s*?(\d*?)\s*?\(-q (\d*?) -V (\d*?)\)",re.MULTILINE|re.DOTALL)
    mp3_duration_format_regex = re.compile(r"(\d*?):(\d*?):(\d*\.\d*)")
    
def doMP3Checks(bitrate,encoder,encoder_string,header_errors,mp3guessenc_output):
# do some MP3 quality checks here
    colour = colourQualityUnknown
    text = None
    
    if int(header_errors) > 0:
        colour = colourQualityBad
        text = "Errors"
        return text, colour
                
    if encoder.startswith("FhG"):
        bitrate_int = float(bitrate.split()[0])
        if bitrate_int > 300:
            colour = colourQualityGood
    elif encoder.startswith("Xing (old)") or encoder.startswith("BladeEnc") or encoder.startswith("dist10"):
        colour = colourQualityWarning
    elif encoder_string.upper().startswith("LAME"):
        bitrate_int = float(bitrate.split()[0])
        
        if bitrate_int > 300:
            colour = colourQualityGood # default if no lame tag
        elif bitrate_int > 170:
            colour = colourQualityOk
            
        search = mp3_lame_tag_preset_regex.search(mp3guessenc_output)
        if search is not None:
            preset = search.group(1).strip()
            if (preset[0:2] in ["V0","V1","V2","V3"]):
                colour = colourQualityGood
                return preset, colour
            elif preset in ["256 kbps","320 kbps","Standard.","Extreme.","Insane."]: 
                colour = colourQualityGood                
                return "--preset {}".format(preset.lower().strip(".")), colour
            elif ((preset in ["160", "192"]) or (preset[0:2] in ["V4","V5","V6"])):
                colour = colourQualityOk
                return preset, colour
                
        search = mp3_xing_quality_regex.search(mp3guessenc_output)
        if search is not None:
            try:
                quality = int(search.group(1))
            except:
                quality = 0
            try:
                q = int(search.group(2))
            except:
                q = 999
            try:
                V = int(search.group(3))
            except:
                V = 999
            if quality <= 50:
                colour = colourQualityWarning
            elif V <= 3:
                colour = colourQualityGood
            elif V <= 6:
                colour = colourQualityOk
            elif V < 999:
                colour = colourQualityWarning
            if q >= 7 and q < 999:
                colour = colourQualityWarning
            if q < 999 and V < 999:
                text = "-q{} -V{}".format(q,V)
                
    return text, colour

    
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
    bitrate_mode="" # vbr or cbr
    encoder_string=""
    length=""
    filesize=""
    frame_hist=() # tuple containing two sets of int lists
    block_usage=""
    mode_count=""
    mode=""
    frequency=""
    header_errors=0
    format_mode=""

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
        if mode.lower() == "stereo":
            mode = "S"
        elif mode.lower() == "joint stereo":
            mode = "JS"
    search = guessenc_frequency_regex.search(mp3guessenc_output)
    if search is not None:
        frequency_int=int(search.group(1))
        frequency = "{} KHz".format(frequency_int/1000)
    search = guessenc_header_errors_regex.search(mp3guessenc_output)
    if search is not None:
        header_errors=search.group(1)

    try:
        if len(frame_hist[0]) > 1:
            bitrate_mode = "VBR"
        elif len(frame_hist[0]) == 1:
            bitrate_mode = "CBR"
    except:
        bitrate_mode = ""
        
    if (not mode == "") and (not bitrate_mode == ""):
        format_mode = "{}/{}".format(mode,bitrate_mode)
    elif (not mode == "") and (bitrate_mode == ""):
        format_mode = "{}".format(mode)
    elif (mode == "") and (not bitrate_mode == ""):
        format_mode = "{}".format(bitrate_mode)

    def formatMP3GuessEncDate(length):
#        0:03:40.369 -> 3m 40s
        search = mp3_duration_format_regex.search(length)
        if search is not None:
            hours = int(search.group(1))
            minutes = int(search.group(2))
            seconds = float(search.group(3))
            return "{}m {}s".format((hours*60)+minutes,round(seconds))
        else:
            return length
                
    duration = formatMP3GuessEncDate(length)

    quality, quality_colour = doMP3Checks(bitrate,encoder,encoder_string,header_errors,mp3guessenc_output)
        
    return {'result_type':'mp3guessenc','encoder':encoder, 'audio_format':'MP3', 'bitrate':bitrate ,'encoder_string':encoder_string, 
            'length':duration, 'filesize':filesize, 'error':False, 'frame_hist':frame_hist, 
            'block_usage':block_usage, 'mode_count':mode_count, 'mode':format_mode,'frequency':frequency,'quality':quality,'quality_colour':quality_colour }

def parse_mediainfo_output(mediainfo_output):
    encoder=""
    bitrate=""
    encoder_string=""
    length=""
    filesize=""
    audio_format="Unknown"
    frequency=""
    bit_depth=""
    bitrate_mode=""
    mode=""
    format_mode=""

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
        
    search = mediainfo_bitrate_mode_regex.search(mediainfo_output)
    if search is not None:
        bitrate_mode=search.group(1) # vbr/cbr
        if bitrate_mode.lower() == "constant":
            bitrate_mode = "CBR"
        elif bitrate_mode.lower() == "variable":
            bitrate_mode = "VBR"
        
    search = mediainfo_mode_regex.search(mediainfo_output)
    if search is not None:
        mode=search.group(1) # stereo/js
        if mode.lower() == "stereo":
            mode = "S"
        elif mode.lower() == "joint stereo":
            mode = "JS"
        
    search = mediainfo_frequency_regex.search(mediainfo_output)
    if search is not None:
        frequency = search.group(1)
        
    search = mediainfo_bitdepth_regex.search(mediainfo_output)
    if search is not None:
        bit_depth = search.group(1)
        
    if not bit_depth == "":
        frequency = "{}/{}".format(bit_depth,frequency)

    if (not mode == "") and (not bitrate_mode == ""):
        format_mode = "{}/{}".format(mode,bitrate_mode)
    elif (not mode == "") and (bitrate_mode == ""):
        format_mode = "{}".format(mode)
    elif (mode == "") and (not bitrate_mode == ""):
        format_mode = "{}".format(bitrate_mode)
            
    return {'result_type':'mediainfo','encoder':encoder, 'audio_format':audio_format, 'bitrate':bitrate ,'encoder_string':encoder_string, 
            'length':length.replace("mn","m"),'mode':format_mode,'frequency':frequency,'filesize':filesize, 'error':False, 'quality':None}

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
        if prob_int > aucdtect_confidence_threshold:
            quality_colour = colourQualityGood
        else:
            quality_colour = colourQualityWarning
    elif detection == "MPEG":
        if prob_int > aucdtect_confidence_threshold:
            quality_colour = colourQualityBad
        else:
            quality_colour = colourQualityWarning
    
    if not detection == "Unknown":
        aucdtect_quality = "{} {}%".format(detection,probability)
    else:
        aucdtect_quality = detection
    
    return {'result_type':'aucdtect','error':False,'quality':aucdtect_quality,'quality_colour':quality_colour}
    
def md5Str(Str):
    return md5(Str.encode('utf-8')).hexdigest()
            
def headerIndexByName(table,headerName):
# find column in tablewidget from headerName
    index = -1
    for i in range(0, table.columnCount()):
        headerItem = table.horizontalHeaderItem(i)
        if headerItem.text() == headerName:
            index = i
    return index
    
class makeBitGraphThread(QRunnable):
# generate bitrate graph using ffprobe/avprobe
    def __init__(self,fn,grid,ffprobe_bin,cmd_timeout):
        super(makeBitGraphThread, self).__init__()
        self.fn = fn
        self.grid = grid
        self.ffprobe_bin = ffprobe_bin
        self.cmd_timeout = cmd_timeout

    def run(self):
        output_str = ""
        try:
            output_str = runCmd([self.ffprobe_bin,"-show_packets","-of","json",self.fn],self.cmd_timeout)
        except Exception as e:
            debug_log(e)
            return None
    
        x_list = []
        y_list = []
    
        try:
            json_packet_data = json.loads(output_str)
            packets = json_packet_data["packets"]
        except Exception as e:
            debug_log("Exception in makeBitGraphThread: {}".format(e))
            return None
    
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
    
#        if debug_enabled:
#           temp_file = open(temp_file_str + ".csv","w")
#           for i in range(0,len(x_list)):
#               temp_file.write(str(x_list[i]) + "," + str(y_list[i]) + "\n")
#           temp_file.close()

        infodlg_q.put(("BitGraph",(x_list,y_list),self.grid,self.fn))
    
    
class FileInfo(QDialog):
# right click file info dialog
    def __init__(self,filenameStr,scanner_output,frame_hist):
        super(FileInfo,self).__init__()
        self.ui = Ui_FileInfoDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Info - {}".format(os.path.basename(filenameStr)))
        self.filename = filenameStr
        infodlg_list.append(self) # keep track of dialogs so we can reuse them if still open
        
        windowGeometry = settings.value("State/InfoWindowGeometry")
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        tabWidget.clear()

        try:
            if frame_hist is not None:
                x = frame_hist[0]
                y = frame_hist[1]
            else:
                x = []
                y = []
        except:
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
        
        thread = getScannerThread(grid.objectName(),filenameStr,mp3guessenc_bin,mediainfo_bin,True,settings.value("Options/Proc_Timeout",300, type=int))
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

            thread = makeSpectrogramThread(filenameStr,sox_bin,temp_file,palette,grid.objectName(),settings.value("Options/Proc_Timeout",300, type=int))
            infodlg_threadpool.start(thread)
            
        if settings.value('Options/EnableBitGraph',True, type=bool):
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setObjectName("BitgraphLayout-{}".format(md5Str(filenameStr)))
            tabWidget.addTab(tab,"Bitrate Graph")
            if debug_enabled:
                debug_log("Running ffprobe to create bitrate graph for file {}".format(filenameStr))
            thread = makeBitGraphThread(filenameStr,grid.objectName(),findffprobeBin(),settings.value("Options/Proc_Timeout",300, type=int))
            infodlg_threadpool.start(thread)
               
         
    def updateGui(self):
    # called from timer
    # subprocesses post to queue when finished
        if not infodlg_q.empty():
            update_info = infodlg_q.get(False,1)
            update_type = update_info[0] # type of update e.g. "Spectrogram"
            update_data = update_info[1] # handler specific data
            update_layout = update_info[2] # QLayout to update
            update_filename = update_info[3] # name of file the update is for

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
                try:
                    os.remove(update_data) # delete generated spectrogram image
                except:
                    pass

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

            elif update_type == "Scanner_Output":
                if debug_enabled:
                    debug_log("updateGui received Scanner_Output update")
                dlg = findDlg(update_filename)
                if dlg is not None:
                    layout = dlg.findChild(QGridLayout,update_layout)
                    if layout is not None:
                        textEdit_scanner = QTextEdit()
                        textEdit_scanner.setReadOnly(True)
                        textEdit_scanner.setPlainText(update_data)
                        layout.addWidget(textEdit_scanner)

                        
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

class makeSpectrogramThread(QRunnable):
    def __init__(self,fn,sox_bin,temp_file,palette,grid,cmd_timeout):
        super(makeSpectrogramThread, self).__init__()
        self.fn = fn
        self.sox_bin = sox_bin
        self.temp_file = temp_file
        self.palette = palette
        self.grid = grid
        self.cmd_timeout = cmd_timeout

    def run(self):
        try:
            sox_output = runCmd([self.sox_bin,self.fn,"-n","spectrogram","-p{}".format(self.palette),"-o",self.temp_file],self.cmd_timeout)
        except Exception as e:
            debug_log(e)
            self.temp_file = ""
        if not self.temp_file == "":
            try:
                infodlg_q.put(("Spectrogram",self.temp_file,self.grid,self.fn)) # Timer watches this queue and updates gui
            except Exception as e:
                debug_log(e)
                
class notifyEnd(QRunnable):
    def __init__(self):
        super(notifyEnd, self).__init__()

    def run(self):
        while True:
            with QReadLocker(ql):
                global task_count
                if task_count == 0:
                    break
                else:
                    sleep(1)
        
        main_q.put((-2,{},""))
        if debug_enabled:
            debug_log("notifyEnd")
            
                
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
        
def getScannerThread(i,filenameStr,mp3guessenc_bin,mediainfo_bin,fileinfo_dialog_update=False,cmd_timeout=300):
    thread = None    
    if fnmatch.fnmatch(filenameStr, "*.mp3"):
        # use mp3guessenc if available
        if not mp3guessenc_bin == "":
            thread = scanner_Thread(i,filenameStr,mp3guessenc_bin,"mp3guessenc","-e",debug_enabled,fileinfo_dialog_update,cmd_timeout)
        elif not mediainfo_bin == "": # fall back to mediainfo
            thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,fileinfo_dialog_update,cmd_timeout)
                        
    elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
        thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,fileinfo_dialog_update,cmd_timeout)
    elif not mediainfo_bin == "": # default for all files is mediainfo
        thread = scanner_Thread(i,filenameStr,mediainfo_bin,"mediainfo","-",debug_enabled,fileinfo_dialog_update,cmd_timeout)
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
        self.ui.actionFolder_Select.setText("Select F&older")
        self.ui.actionClear_Filelist.triggered.connect(self.clear_List)
        self.ui.actionStop.triggered.connect(self.cancel_Tasks)
        self.ui.actionOptions.triggered.connect(self.edit_Options)
        self.ui.actionOptions.setText("&Options")
        self.ui.actionAbout.triggered.connect(self.about_Dlg)
        self.ui.actionAbout.setText("&About")
            
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
        
        report_file = open(report_dir + "/specton.log","w")
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
        report_file.close()
        if not silent:
            self.statusBar().showMessage("Report generated for folder {}".format(report_dir_displayname))
        
        
    def contextRescanFile(self,row,selected_items):
        file_list = []
        for filenameItem in selected_items:
            filenameItem.setData(dataScanned, False)
            file_list.append(filenameItem.data(dataFilenameStr))
        self.scan_Files(True,file_list)

    def contextScanFolder(self,row):
        folderItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Folder"))
        scan_dir = folderItem.toolTip()
        file_list = []
        for i in range(0,self.ui.tableWidget.rowCount()):
            folderItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Folder"))
            dir = folderItem.toolTip()
            if scan_dir == dir:
                filenameItem = self.ui.tableWidget.item(i, headerIndexByName(self.ui.tableWidget,"Filename"))
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
            dlg = FileInfo(filenameStr,"",bitrateItem.data(dataBitrate))
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
    
    def addTableWidgetItem(self,row,name,dir,usecache):
        filenameStr = os.path.join(dir, name)
        hashStr = filenameStr.replace("/", "\\") + str(os.path.getmtime(filenameStr)) # use mtime so hash changes if file changed
        filemd5 = md5Str(hashStr)
        
        try: # don't add same file twice
            index = file_hashlist.index(filemd5)
        except:
            index = -1 # not found in list
        
        if index > -1:
            return # file already added
        else:
            file_hashlist.append(filemd5)

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

                filenameItem.setData(dataScanned, True) # previously scanned
        
        self.ui.tableWidget.insertRow(row)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Filename"), filenameItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Folder"), folderItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Encoder"), codecItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Bitrate"), bitrateItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Length"), lengthItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Filesize"), filesizeItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Quality"), qualityItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Frequency"), frequencyItem)
        self.ui.tableWidget.setItem(row, headerIndexByName(self.ui.tableWidget,"Mode"), modeItem)    
    
    def recursiveAdd(self,directory,filemask_regex,followsymlinks=False,recursedirectories=True,usecache=True):
        # walk through directory
        # and add filenames to treeview
        i = 0
        c = 0
        for root, dirs, files in os.walk(directory, True, None, followsymlinks):
            c += 1
            if c % 2 == 0:
                QApplication.processEvents()
                if (i > 0) and (i % 10 == 0): # update count every 10 files
                    self.statusBar().showMessage("Scanning for files: {} found".format(i))
            if not recursedirectories:
                while len(dirs) > 0:
                    dirs.pop()
            for name in sorted(files):
                if filemask_regex.search(name) is not None:
                    self.addTableWidgetItem(i,name,root,usecache)
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
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
    
        for filedir in filedirlist:
            if os.path.isdir(filedir):
                self.recursiveAdd(directory=filedir,filemask_regex=filemask_regex,followsymlinks=followsymlinks,recursedirectories=recursedirectories,usecache=usecache)
            else:
                self.addTableWidgetItem(0,os.path.basename(filedir),os.path.dirname(filedir),usecache)
                
        
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
        global task_count
        with QWriteLocker(ql):
            if task_count > 0: # tasks are running
                scanner_threadpool.clear()
                task_count = scanner_threadpool.activeThreadCount()
                thread = notifyEnd()
                scanner_threadpool.start(thread)
 
    def update_Table(self,row,song_info):
        # update table with info from scanner
            usecache = settings.value('Options/UseCache',True, type=bool)
            error_status = song_info['error']
            result_type = song_info['result_type']
            if not error_status:
                filenameItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Filename"))
                filenameStr = filenameItem.data(dataFilenameStr)
                if usecache:
                    hashStr = filenameStr.replace("/", "\\") + str(os.path.getmtime(filenameStr))
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
                    quality = song_info['quality']
                except KeyError:
                    quality = None

                if quality is not None:
                    qualityItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Quality"))
                    qualityItem.setText(quality)
                    if usecache:
                        filecache.setValue('{}/Quality'.format(filemd5),quality)
                if not result_type == "aucdtect":
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

            else: # error status
                codecItem = self.ui.tableWidget.item(row, headerIndexByName(self.ui.tableWidget,"Encoder"))
                codecItem.setText("error scanning file")
                
    def updateMainGui(self):
    # runs from timer
    # takes results from main_q and adds to tablewidget

        while not main_q.empty():
            if debug_enabled:
                debug_log("updateMainGui: main_q not empty")
            with QReadLocker(ql):
                global task_total,task_count
                tasks_done = task_total - task_count
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
                try:
                    row = q_info[0]
                except Exception as e:
                    debug_log("updateMainGui: q_info exception {}".format(e))
                    row = -1
                try:
                    song_info = q_info[1]
                except Exception as e:
                    debug_log("updateMainGui: q_info exception {}".format(e))
                    song_info = {}
#                try:
#                    scanner_output = q_info[2]
#                except Exception as e:
#                    debug_log("updateMainGui: q_info exception {}".format(e))
#                    scanner_output = ""
                    
                if row == -2:   # posted by notifyEnd thread
                    if debug_enabled:
                        debug_log("all threads finished, task count={}".format(task_count))
                           
                    self.ui.progressBar.setValue(100)
                    self.statusBar().showMessage('Done')
#                    with QWriteLocker(ql):
#                        task_count = 0
                    self.ui.actionScan_Files.setEnabled(True)
                    self.ui.actionClear_Filelist.setEnabled(True)
                    self.ui.actionFolder_Select.setEnabled(True)
                    self.ui.tableWidget.setSortingEnabled(True)
                else:
                    if debug_enabled:
                        debug_log("updateMainGui: calling update_Table for row {}".format(row))
                    self.ui.tableWidget.setUpdatesEnabled(False)
                    self.update_Table(row,song_info)
                    self.ui.tableWidget.setUpdatesEnabled(True)
    
    def doScanFile(self,thread):
        scanner_threadpool.start(thread)
        with QWriteLocker(ql):
            global task_count
            global task_total
            task_count += 1
            task_total += 1
                        
    def scan_Files(self,checked,filelist=None):
    # loop through table and queue scanner processes for all files
    # filelist - optional list of files to scan, all others will be skipped
        self.ui.actionScan_Files.setEnabled(False)
        self.ui.actionClear_Filelist.setEnabled(False)
        self.ui.actionFolder_Select.setEnabled(False)
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
                    
                thread = getScannerThread(i,filenameStr,mp3guessenc_bin,mediainfo_bin,False,cmd_timeout)
                if thread is not None:
                    thread_list.append(thread)
                    
                # if lossless audio also run aucdtect if enabled and available

                if fnmatch.fnmatch(filenameStr, "*.flac"):
                    if settings.value('Options/auCDtect_scan',False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = settings.value('Options/auCDtect_mode',10, type=int)
                            thread = aucdtect_Thread(i,filenameStr,flac_bin,"-df",aucdtect_bin,"-m{}".format(aucdtect_mode),debug_enabled,cmd_timeout)
                            thread_list.append(thread)
                elif fnmatch.fnmatch(filenameStr, "*.wav"):
                    if settings.value('Options/auCDtect_scan',False, type=bool):
                        if not aucdtect_bin == "":
                            aucdtect_mode = settings.value('Options/auCDtect_mode',10, type=int)
                            thread = aucdtect_Thread(i,filenameStr,"","",aucdtect_bin,"-m{}".format(aucdtect_mode),debug_enabled,cmd_timeout)
                            thread_list.append(thread)
                                        
            QApplication.processEvents()
            
        self.statusBar().showMessage('Scanning files...')
        for thread in thread_list:
            self.doScanFile(thread)
        thread = notifyEnd()
        scanner_threadpool.start(thread)
        
    def clear_List(self):
        self.ui.progressBar.setValue(0)
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        file_hashlist.clear()

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
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
