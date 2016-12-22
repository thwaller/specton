# -*- coding: utf-8 -*-

import tempfile
import subprocess
import logging
import os
from hashlib import md5

logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s - %(message)s')

class fakestd(object):
    encoding = 'utf-8'
    def write(self, string):
        pass

    def flush(self):
        pass

def debug_log(debug_str):
    logging.debug(debug_str)
    
def getTempFileName():
    with tempfile.NamedTemporaryFile() as temp_file:
        return temp_file.name
        
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
        except TimeoutExpired(timeout=cmd_timeout):
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
    
    
