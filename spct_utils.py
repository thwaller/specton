# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys
import tempfile
from functools import partial
from hashlib import md5

import spct_cfg as cfg

os.makedirs(cfg.app_dirs.user_log_dir, exist_ok=True)
logfile = os.path.join(cfg.app_dirs.user_log_dir, "debug.log")
try:
   os.remove(logfile)
except OSError:
   pass
   
logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(asctime)s - %(threadName)s - (%(levelname)s) %(message)s')
logging.raiseExceptions=False

def debug_log(debug_str,level=logging.INFO):
    if not cfg.debug_enabled: return
    logging.log(level,debug_str)

debug_log("Log start")

def findBinary(settings_key="", nt_path="", posix_path=""):
    ''' find executable files - use paths from settings if available else use default locations '''
    bin_exe = cfg.settings.value(settings_key)
    if (bin_exe is None) or (bin_exe == ""):
        if os.name == 'nt':
            return nt_path
        elif os.name == 'posix':
            return posix_path
        
    return bin_exe

findGuessEncBin = partial(findBinary,'Paths/mp3guessenc_bin',cfg.app_dirs.user_cache_dir+'/tools/mp3guessenc.exe','/usr/local/bin/mp3guessenc')
findMediaInfoBin = partial(findBinary,'Paths/mediainfo_bin',cfg.app_dirs.user_cache_dir+'/tools/MediaInfo.exe','/usr/bin/mediainfo')
findFlacBin = partial(findBinary,'Paths/flac_bin',cfg.app_dirs.user_cache_dir+'/tools/flac.exe','/usr/bin/flac')
findauCDtectBin = partial(findBinary,'Paths/aucdtect_bin',cfg.app_dirs.user_cache_dir+'/tools/auCDtect.exe','/usr/bin/aucdtect')
findSoxBin = partial(findBinary,'Paths/sox_bin',cfg.app_dirs.user_cache_dir+'/tools/sox/sox.exe','/usr/bin/sox')
findGnuPlotBin = partial(findBinary,'Paths/gnuplot_bin',cfg.app_dirs.user_cache_dir+'/tools/gnuplot/gnuplot.exe','/usr/bin/gnuplot')

def findffprobeBin(settings_key='Paths/ffprobe_bin', nt_path=cfg.app_dirs.user_cache_dir+'/tools/ffmpeg/ffprobe.exe', posix_path='/usr/bin/ffprobe'):
    ff_bin = cfg.settings.value(settings_key)
    if ff_bin is None:
        if os.name == 'nt':
            return nt_path
        elif os.name == 'posix':
            if os.path.exists(posix_path): # ffprobe
                return posix_path
            elif os.path.exists(os.path.dirname(posix_path) + "/avprobe"): # also try avprobe
                return os.path.dirname(posix_path) + "/avprobe"
        
    return ff_bin

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
            debug_log("Error running xdg-open (is it installed?)",logging.WARNING)
    else:
        debug_log("Folder/directory viewing not implemented on this platform",logging.WARNING)
        
def runCmd(cmd,cmd_timeout=300):
    ''' run command without showing console window on windows - return stdout and stderr as strings '''
    startupinfo = None
    output = ""
    output_err = ""
    debug_log("runCmd: {}".format(cmd))
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        proc = subprocess.Popen(cmd,bufsize=-1,startupinfo=startupinfo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=None,shell=False,universal_newlines=False)
    except SubprocessError as e:
        proc = None
        debug_log("exception in runCmd: {}".format(e),logging.ERROR)
    if proc is not None:
        try:
            outputb, output_errb = proc.communicate()
            output = outputb.decode('utf-8','replace')
            output_err = output_errb.decode('utf-8','replace')
        except subprocess.TimeoutExpired(timeout=cmd_timeout):
            proc.kill()
            debug_log("runCmd: Process killed due to timeout",logging.WARNING)
    else:
        debug_log("runCmd: Proc was none",logging.WARNING)
    return output,output_err
    
def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "{:3.1f} {}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:.1f} {}{}".format(num, 'Yi', suffix)

def md5Str(Str):
    return md5(Str.encode('utf-8')).hexdigest()
    
def findDlg(searchname,debug_enabled,infodlg_list):
    debug_log("findDlg called list: {} search: {}".format(infodlg_list, searchname),logging.DEBUG)
    for obj in infodlg_list:
        if obj.filename == searchname:
            debug_log("findDlg dialog found: {} filename: {}".format(obj, searchname),logging.DEBUG)
            return obj

    
    
