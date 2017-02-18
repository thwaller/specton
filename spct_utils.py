# -*- coding: utf-8 -*-

import tempfile
import subprocess
import logging
import os, sys
from hashlib import md5
from spct_defs import app_dirs

os.makedirs(app_dirs.user_log_dir, exist_ok=True)
logfile = os.path.join(app_dirs.user_log_dir, "debug.log")
try:
   os.remove(logfile)
except:
   pass
   
logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s - %(message)s')

def debug_log(debug_str):
    logging.debug(debug_str)
    
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
            output, output_err = proc.communicate()
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
    
    
