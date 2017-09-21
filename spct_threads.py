# -*- coding: utf-8 -*-

import os,fnmatch,json,logging
from PyQt5.QtCore import QRunnable
from spct_utils import debug_log, runCmd, getTempFileName
from spct_parsers import parse_mp3guessenc_output, parse_aucdtect_output, parse_mediainfo_output
from spct_defs import *
from spct_objects import infoobj,main_info,song_info_obj
from spct_cfg import app_dirs

def getScannerThread(i, filenameStr, mp3guessenc_bin, mediainfo_bin, fileinfo_dialog_update=None, cmd_timeout=300,debug_enabled=False,main_q=None,info_q=None):
    threads = set()
    if fnmatch.fnmatch(filenameStr, "*.mp3"):
        # use mp3guessenc if available
        if not mp3guessenc_bin == "":
            threads.add(scanner_Thread(i, filenameStr, mp3guessenc_bin, "mp3guessenc", "-e", debug_enabled, info_q,
                                    main_q, fileinfo_dialog_update, cmd_timeout))
        elif not mediainfo_bin == "":  # always use mediainfo
            threads.add(scanner_Thread(i, filenameStr, mediainfo_bin, "mediainfo", "-", debug_enabled, info_q, main_q,
                                    fileinfo_dialog_update, cmd_timeout))

    elif fnmatch.fnmatch(filenameStr, "*.flac") and not mediainfo_bin == "":
        threads.add(scanner_Thread(i, filenameStr, mediainfo_bin, "mediainfo", "-", debug_enabled, info_q, main_q,
                                fileinfo_dialog_update, cmd_timeout))
    elif not mediainfo_bin == "":  # default for all files is mediainfo
        threads.add(scanner_Thread(i, filenameStr, mediainfo_bin, "mediainfo", "-", debug_enabled, info_q, main_q,
                                fileinfo_dialog_update, cmd_timeout))
    return threads


class scanner_Thread(QRunnable):
    def __init__(self,row,filenameStr,binary,scanner_name,options,debug_enabled,infodlg_q,main_q,fileinfo_dialog_update=None,cmd_timeout=300):
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
        debug_log("scanner thread running for row {}, file: {}".format(self.row,self.filenameStr))
        
        if os.path.lexists(self.filenameStr): 
            try:
                output_str,output_err = runCmd([self.binary,self.options,self.filenameStr],self.cmd_timeout)
            except SubprocessError as e:
                debug_log("Exception {} in runCmd {} for file {}".format(e,self.binary,self.filenameStr),logging.ERROR)
                output_str = "Error running command {}".format(self.binary)
        else:
            output_str = "Error: file {} not found".format(self.filenameStr) # handle the case where file has been deleted while in queue e.g. temp files or user deletion
                
        if self.fileinfo_dialog_update is not None:
            info = infoobj(infoobj.SCANNER_OUTPUT,output_str,self.fileinfo_dialog_update,self.filenameStr)
            self.infodlg_q.put(info)
            return

        if not (output_str.startswith("Error")):
            if self.scanner_name == "mp3guessenc":
                song_info = parse_mp3guessenc_output(output_str)
            elif self.scanner_name == "mediainfo":
                song_info = parse_mediainfo_output(output_str)
            else: # unknown
                debug_log("scanner thread finished but scanner {} unknown".format(self.scanner_name),logging.WARNING)
                return
            debug_log("{} scanner thread finished - row {}, result: {}".format(self.scanner_name,self.row,song_info.encoder))
    
            debug_log("{} scanner thread posting to queue - row {}".format(self.scanner_name,self.row))
        else:
            debug_log("{} scanner thread posting to queue with cmd error - row {}".format(self.scanner_name,self.row),logging.WARNING)
            song_info = song_info_obj()
            song_info.result_type = song_info_obj.SCANNER_OUTPUT
            song_info.cmd_error = True
            debug_log("{} scanner thread finished with cmd error - row {}, result: {}".format(self.scanner_name,self.row,output_str),logging.WARNING)
            
        maininfo_obj = main_info(main_info.SCANNER_OUTPUT,output_str,self.row,song_info)
        self.main_q.put(maininfo_obj)
                
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
        debug_log("aucdtect thread started for row {}, file: {}".format(self.row,self.filenameStr))
        if os.path.lexists(self.filenameStr): 
            try:
                temp_file = getTempFileName()
                if not self.decoder_bin == "": # need to decode to wav
                    decoder_output,output_err = runCmd([self.decoder_bin,self.decoder_options,self.filenameStr,"-o",temp_file],self.cmd_timeout)
                    output_str,output_err = runCmd([self.aucdtect_bin,self.aucdtect_options,temp_file],self.cmd_timeout)
                else:
                    output_str,output_err = runCmd([self.aucdtect_bin,self.aucdtect_options,self.filenameStr],self.cmd_timeout)
            except SubprocessError as e:
                debug_log("Exception {} in runCmd {} for file {}".format(e,self.aucdtect_bin,self.filenameStr),logging.ERROR)
                output_str = "Error"
        else:
            output_str = "Error"
    
        try:
            os.remove(temp_file)
        except OSError:
            pass
        
        if not (output_str == "Error"):
            song_info = parse_aucdtect_output(output_str)
            debug_log("aucdtect thread finished - row {}, result: {}".format(self.row,song_info.quality))
    
        else:
            song_info = song_info_obj()
            song_info.result_type = song_info_obj.SCANNER_OUTPUT
            song_info.cmd_error = True
            debug_log("aucdtect thread finished with cmd error - row {}, result: {}".format(self.row,output_str),logging.WARNING)

        maininfo_obj = main_info(main_info.SCANNER_OUTPUT,output_str,self.row,song_info)
        self.main_q.put(maininfo_obj)

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
            debug_log("error check thread started for row {}, file: {}".format(self.row,self.filenameStr))
            if os.path.lexists(self.filenameStr): 
                try:
                    cmd = [self.decoder_bin,self.decoder_options,self.filenameStr]
                    debug_log("cmd: {}".format(cmd))
                    output_str,output_err = runCmd(cmd,self.cmd_timeout)
                except SubprocessError as e:
                    debug_log("Exception {} in runCmd {} for file {}".format(e,self.decoder_bin,self.filenameStr),logging.ERROR)
                    output_str = "Error"
                    output_err = "Error"
            else:
                output_str = "Error"
                output_err = "Error"
                debug_log("error check thread file: {} does not exist".format(self.filenameStr),logging.WARNING)
                            
            if self.use_stderr: # flac writes everything to stderr
                check_str = output_err
            else:
                check_str = output_str
            
            song_info = song_info_obj()
            song_info.result_type = song_info_obj.ERROR_CHECK
            maininfo_obj = main_info(main_info.ERROR_CHECK,check_str,self.row,song_info)
            
            if (check_str == "Error") or ("ERROR while decoding" in check_str): 
                if check_str == "Error":
                    song_info.cmd_error = True
                else:
                    song_info.file_error = True
                debug_log("error check thread finished with error - row {}, result: {}".format(self.row,check_str),logging.WARNING)
            else:
                song_info.file_error = False
                debug_log("error check thread finished - row {}, result: {}".format(self.row,check_str))
                
            self.main_q.put(maininfo_obj)
        except Exception as e:
            debug_log(e,logging.ERROR)
            
class makeBitGraphThread(QRunnable):
    ''' generate bitrate graph using ffprobe/avprobe 
        and plot with gnuplot '''
    
    def __init__(self,fn,grid,ffprobe_bin,cmd_timeout,infodlg_q,gnuplot_bin):
        super(makeBitGraphThread, self).__init__()
        self.fn = fn
        self.grid = grid
        self.ffprobe_bin = ffprobe_bin
        self.gnuplot_bin = gnuplot_bin
        self.cmd_timeout = cmd_timeout
        self.infodlg_q = infodlg_q

    def run(self):
        output_str = ""
        try:
            output_str,output_err = runCmd([self.ffprobe_bin,"-show_packets","-of","json",self.fn],self.cmd_timeout)
        except SubprocessError as e:
            debug_log(e,logging.ERROR)
            return None
    
        x_list = []
        y_list = []
    
        try:
            json_packet_data = json.loads(output_str)
            packets = json_packet_data["packets"]
        except Exception as e:
            debug_log("Exception in makeBitGraphThread: {}".format(e),logging.ERROR)
            return None
    
        for dictionary in packets:
            if not dictionary["codec_type"] == "audio":
                continue
            try:
                x = float(dictionary["pts_time"]) # time
            except (KeyError, ValueError, OverflowError) as e:
                x = 0
            try:
                t = float(dictionary["duration_time"]) # duration
            except (KeyError, ValueError, OverflowError) as e:
                t = 0
            try:
                sz = float(dictionary["size"]) # size in bytes
            except (KeyError, ValueError, OverflowError) as e:
                sz = 0
            try:
                y = round(((sz*8)/1024)/t)
            except (ZeroDivisionError, ValueError, OverflowError) as e:
                y = 0
        
            if y > 0:
                y_list.append(y) # bitrate
                x_list.append(round(x,3))

        assert len(x_list) == len(y_list)
                
        datfile = getTempFileName() + ".dat"
        with open(datfile, "w") as tf: # datfile tho
           for i in range(0,len(x_list)):
               tf.write(str(x_list[i]) + " " + str(y_list[i]) + "\n") 
               
        cmdfile_template = app_dirs.user_config_dir + "/bitgraph.plot"
        pngfile = getTempFileName() + ".png"
        if not os.path.lexists(cmdfile_template):
            with open(cmdfile_template, "w") as cft:
                cft.write(str("set style line 1 lc rgb '#0060ad' lt 1 lw 2 pt 0 ps 1.5   # --- blue\n"))
                cft.write(str("set title \"Bitrate vs time\"\n"))
                cft.write(str("set xlabel \"Time (s)\"\n"))
                cft.write(str("set ylabel \"Bitrate (KiB)\"\n"))
                cft.write(str("set terminal png size 800,600 enhanced font \"Helvetica,20\"\nset output '{pngfile}'\n"))
                cft.write(str("plot '{datfile}' notitle with lines\n"))

        cmdfile = getTempFileName() + ".plot"
        with open(cmdfile, "w") as cf:
            with open(cmdfile_template, "r") as cft:
                for line in cft:
                    if "{datfile}" in line:
                        cf.write(line.replace("{datfile}",datfile))
                    elif "{pngfile}" in line:
                        cf.write(line.replace("{pngfile}",pngfile))
                    else:
                        cf.write(line)
                    
        output_str = ""
        try:
            debug_log("running {} with cmdfile {}".format(self.gnuplot_bin,cmdfile))
            output_str,output_err = runCmd([self.gnuplot_bin,"{}".format(cmdfile)],self.cmd_timeout)
        except SubprocessError as e:
            debug_log(e,logging.ERROR)
            return None
            
        try:
            os.remove(cmdfile)
            os.remove(datfile)
        except OSError:
            pass        
            
        info = infoobj(infoobj.BITGRAPH,pngfile,self.grid,self.fn)
        self.infodlg_q.put(info)

class makeBitHistThread(QRunnable):
    ''' plot bitrate histogram with gnuplot '''
    
    def __init__(self,fn,grid,cmd_timeout,infodlg_q,gnuplot_bin,x,y):
        super(makeBitHistThread, self).__init__()
        self.fn = fn
        self.grid = grid
        self.gnuplot_bin = gnuplot_bin
        self.cmd_timeout = cmd_timeout
        self.infodlg_q = infodlg_q
        self.x = x
        self.y = y

    def run(self):
    
        assert len(self.x) == len(self.y)
    
        datfile = getTempFileName() + ".dat"
        with open(datfile, "w") as tf:
           for i in range(0,len(self.x)):
               tf.write(str(self.x[i]) + " " + str(self.y[i]) + "\n") 
               
        cmdfile_template = app_dirs.user_config_dir + "/bithist.plot"
        pngfile = getTempFileName() + ".png"
        if not os.path.lexists(cmdfile_template):
            with open(cmdfile_template, "w") as cft:
                cft.write(str("set style data histogram\nset style fill solid border\nset boxwidth 0.95 relative\nset grid\n"))
                cft.write(str("set title \"Bitrate distribution\"\n"))
                cft.write(str("set xlabel \"Bitrate (kB)\"\n"))
                cft.write(str("set ylabel \"Number of frames\"\n"))
                cft.write(str("set terminal png size 800,600 enhanced font \"Helvetica,20\"\nset output '{pngfile}'\n"))
                cft.write(str("plot '{datfile}' using 2:xticlabels(1) notitle\n"))

        cmdfile = getTempFileName() + ".plot"
        with open(cmdfile, "w") as cf:
            with open(cmdfile_template, "r") as cft:
                for line in cft:
                    if "{datfile}" in line:
                        cf.write(line.replace("{datfile}",datfile))
                    elif "{pngfile}" in line:
                        cf.write(line.replace("{pngfile}",pngfile))
                    else:
                        cf.write(line)
               
        output_str = ""
        try:
            debug_log("running {} with cmdfile {}".format(self.gnuplot_bin,cmdfile))
            output_str,output_err = runCmd([self.gnuplot_bin,"{}".format(cmdfile)],self.cmd_timeout)
            debug_log(output_str)
            debug_log(output_err)
        except SubprocessError as e:
            debug_log(e,logging.ERROR)
            return None
            
        try:
            os.remove(cmdfile)
            os.remove(datfile)
        except OSError:
            pass        
            
        info = infoobj(infoobj.BITHIST,pngfile,self.grid,self.fn)
        self.infodlg_q.put(info)
        
class makeSpectrogramThread(QRunnable):
    def __init__(self,fn,sox_bin,temp_file,palette,grid,cmd_timeout,infodlg_q):
        super(makeSpectrogramThread, self).__init__()
        self.fn = fn
        self.sox_bin = sox_bin
        self.temp_file = temp_file
        self.palette = palette
        self.grid = grid
        self.cmd_timeout = cmd_timeout
        self.infodlg_q = infodlg_q

    def run(self):
        try:
            sox_output,output_err = runCmd([self.sox_bin,self.fn,"-n","spectrogram","-l","-p{}".format(self.palette),"-c ","-o",self.temp_file],self.cmd_timeout)
        except SubprocessError as e:
            debug_log(e,logging.ERROR)
            self.temp_file = ""
        if not self.temp_file == "":
            try:
                info = infoobj(infoobj.SPECTROGRAM,self.temp_file,self.grid,self.fn)
                self.infodlg_q.put(info) # Timer watches this queue and updates gui
            except Exception as e:
                debug_log(e,logging.ERROR)               
