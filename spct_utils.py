# -*- coding: utf-8 -*-

import tempfile
import subprocess
import logging
import os, sys
from hashlib import md5
from spct_defs import app_dirs
from PyQt5.QtCore import QSettings
from functools import partial

os.makedirs(app_dirs.user_log_dir, exist_ok=True)
logfile = os.path.join(app_dirs.user_log_dir, "debug.log")
try:
   os.remove(logfile)
except:
   pass
   
logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(asctime)s - %(threadName)s - %(message)s')

settings = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-settings")
filecache = QSettings(QSettings.IniFormat,QSettings.UserScope,"Specton","Specton-cache")

def debug_log(debug_str):
    try:
        logging.debug(debug_str)
    except:
        pass

debug_log("Log start")

def findBinary(settings_key="", nt_path="", posix_path=""):
    ''' find executable files - use paths from settings if available else use default locations '''
    bin = settings.value(settings_key)
    if bin is None:
        if os.name == 'nt':
            return nt_path
        elif os.name == 'posix':
            return posix_path
        
    return bin

findGuessEncBin = partial(findBinary,'Paths/mp3guessenc_bin',app_dirs.user_cache_dir+'/tools/mp3guessenc.exe','/usr/local/bin/mp3guessenc')
findMediaInfoBin = partial(findBinary,'Paths/mediainfo_bin',app_dirs.user_cache_dir+'/tools/MediaInfo.exe','/usr/bin/mediainfo')
findFlacBin = partial(findBinary,'Paths/flac_bin',app_dirs.user_cache_dir+'/tools/flac.exe','/usr/bin/flac')
findauCDtectBin = partial(findBinary,'Paths/aucdtect_bin',app_dirs.user_cache_dir+'/tools/auCDtect.exe','/usr/bin/aucdtect')
findSoxBin = partial(findBinary,'Paths/sox_bin',app_dirs.user_cache_dir+'/tools/sox/sox.exe','/usr/bin/sox')
findGnuPlotBin = partial(findBinary,'Paths/gnuplot_bin',app_dirs.user_cache_dir+'/tools/gnuplot/gnuplot.exe','/usr/bin/gnuplot')

def findffprobeBin(settings_key='Paths/ffprobe_bin', nt_path=app_dirs.user_cache_dir+'/tools/ffmpeg/ffprobe.exe', posix_path='/usr/bin/ffprobe'):
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
    with tempfile.NamedTemporaryFile() as temp_file:
        return temp_file.name

def openFolder(folder_name):
    ''' open folder/dir in file viewer - platform specific '''
    if sys.platform=='win32':
        subprocess.Popen("explorer \"" + os.path.normpath(folder_name) + "\"")
    elif sys.platform=='darwin':
        subprocess.Popen(["open", folder_name])
    elif sys.platform.startswith('linux'):
        try:
            subprocess.Popen(["xdg-open", folder_name])
        except OSError:
            debug_log("Error running xdg-open (is it installed?)")
    else:
        debug_log("Folder/directory viewing not implemented on this platform")
        
def runCmd(cmd,cmd_timeout=300):
    ''' run command without showing console window on windows - return stdout and stderr as strings '''
    startupinfo = None
    output = ""
    output_err = ""
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        proc = subprocess.Popen(cmd,bufsize=-1,startupinfo=startupinfo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=None,shell=False,universal_newlines=False)
    except Exception as e:
        proc = None
        debug_log("exception in runCmd: {}".format(e))
    if proc is not None:
        try:
            outputb, output_errb = proc.communicate()
            output = outputb.decode('utf-8')
            output_err = output_errb.decode('utf-8')
        except subprocess.TimeoutExpired(timeout=cmd_timeout):
            proc.kill()
            debug_log("runCmd: Process killed due to timeout")
    else:
        debug_log("runCmd: Proc was none")
    return output,output_err
    
def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "{:3.1f} {}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:.1f} {}{}".format(num, 'Yi', suffix)
    
def md5Str(Str):
    return md5(Str.encode('utf-8')).hexdigest()
    
    
