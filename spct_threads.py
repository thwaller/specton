# -*- coding: utf-8 -*-

import os
from PyQt5.QtCore import QRunnable
from spct_utils import debug_log, runCmd, getTempFileName
from specton import parse_mp3guessenc_output, parse_aucdtect_output, parse_mediainfo_output
from spct_defs import *

class scanner_Thread(QRunnable):
    def __init__(self,row,filenameStr,binary,scanner_name,options,debug_enabled,infodlg_q,main_q,fileinfo_dialog_update=False,cmd_timeout=300):
        super(scanner_Thread, self).__init__()
        self.row = row
        self.filenameStr = filenameStr
        self.binary = binary
        self.scanner_name = scanner_name
        self.options = options
        self.debug_enabled = debug_enabled
        self.fileinfo_dialog_update = fileinfo_dialog_update
        self.cmd_timeout = cmd_timeout
        self.infodlg_q = infodlg_q
        self.main_q = main_q
        
    def run(self):
        output_str = ""
        if self.debug_enabled:
            debug_log("scanner thread running for row {}, file: {}".format(self.row,self.filenameStr))
        
        if os.path.lexists(self.filenameStr): 
            try:
                output_str,output_err = runCmd([self.binary,self.options,self.filenameStr],self.cmd_timeout)
            except:
                output_str = "Error"
        else:
            output_str = "Error" # handle the case where file has been deleted while in queue e.g. temp files or user deletion
                
        if self.fileinfo_dialog_update:
            self.infodlg_q.put(("Scanner_Output",output_str,self.row,self.filenameStr))
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
                debug_log("scanner thread finished - row {}, result: {}".format(self.row,song_info['encoder']))
    
            if self.debug_enabled:
                debug_log("scanner thread posting to queue - row {}".format(self.row))
            self.main_q.put((self.row,song_info,output_str))
        else:
            if self.debug_enabled:
                debug_log("scanner thread posting to queue with error - row {}".format(self.row))
            self.main_q.put((self.row,{'result_type':'Scanner_Output','error':True},output_str))
            if self.debug_enabled:
                debug_log("scanner thread finished with error - row {}, result: {}".format(self.row,output_str))
                
class aucdtect_Thread(QRunnable):
    ''' run aucdtect on a file and post results to queue '''
    def __init__(self,row,filenameStr,decoder_bin,decoder_options,aucdtect_bin,aucdtect_options,debug_enabled,cmd_timeout,main_q):
        super(aucdtect_Thread, self).__init__()
        self.row = row
        self.filenameStr = filenameStr
        self.decoder_bin = decoder_bin
        self.decoder_options = decoder_options
        self.aucdtect_bin = aucdtect_bin
        self.aucdtect_options = aucdtect_options
        self.debug_enabled = debug_enabled
        self.cmd_timeout = cmd_timeout
        self.main_q = main_q

    def run(self):
        temp_file = ""
        if self.debug_enabled:
            debug_log("aucdtect thread started for row {}, file: {}".format(self.row,self.filenameStr))
        if os.path.lexists(self.filenameStr): 
            try:
                temp_file = getTempFileName()
                if not self.decoder_bin == "": # need to decode to wav
                    decoder_output,output_err = runCmd([self.decoder_bin,self.decoder_options,self.filenameStr,"-o",temp_file],self.cmd_timeout)
                    output_str,output_err = runCmd([self.aucdtect_bin,self.aucdtect_options,temp_file],self.cmd_timeout)
                else:
                    output_str,output_err = runCmd([self.aucdtect_bin,self.aucdtect_options,self.filenameStr],self.cmd_timeout)
            except:
                output_str = "Error"
        else:
            output_str = "Error"
    
        try:
            os.remove(temp_file)
        except OSError:
            pass
        
        if not (output_str == "Error"):
            song_info = parse_aucdtect_output(output_str)

            if self.debug_enabled:
                debug_log("aucdtect thread finished - row {}, result: {}".format(self.row,song_info['quality']))
    
            self.main_q.put((self.row,song_info,output_str))
        else:
            self.main_q.put((self.row,{'result_type':'Scanner_Output','error':True},output_str))
            if self.debug_enabled:
                debug_log("aucdtect thread finished with error - row {}, result: {}".format(self.row,output_str))

class errorCheck_Thread(QRunnable):
    ''' test file for decode errors and post results to queue '''
    def __init__(self,row,filenameStr,decoder_bin,decoder_options,debug_enabled,cmd_timeout,main_q,use_stderr=False):
        super(errorCheck_Thread, self).__init__()
        self.row = row
        self.filenameStr = filenameStr
        self.decoder_bin = decoder_bin
        self.decoder_options = decoder_options
        self.debug_enabled = debug_enabled
        self.cmd_timeout = cmd_timeout
        self.use_stderr = use_stderr
        self.main_q = main_q

    def run(self):
        try:
            if self.debug_enabled:
                debug_log("error check thread started for row {}, file: {}".format(self.row,self.filenameStr))
            if os.path.lexists(self.filenameStr): 
                try:
                    output_str,output_err = runCmd([self.decoder_bin,self.decoder_options,self.filenameStr],self.cmd_timeout)
                except:
                    output_str = "Error"
            else:
                output_str = "Error"
                if self.debug_enabled:
                    debug_log("error check thread file: {} does not exist".format(self.filenameStr))
                            
            if self.use_stderr: # flac writes everything to stderr
                check_str = output_err
            else:
                check_str = output_str
                        
            if (check_str == "Error") or ("ERROR while decoding" in check_str): 
                self.main_q.put((self.row,{'result_type':'Error_Check','error':True},check_str))
                if self.debug_enabled:
                    debug_log("error check thread finished with error - row {}, result: {}".format(self.row,check_str))
            else:
                self.main_q.put((self.row,{'result_type':'Error_Check','error':False},check_str))
                if self.debug_enabled:
                    debug_log("error check thread finished - row {}, result: {}".format(self.row,check_str))
        except Exception as e:
            self.debug_log(e)
            