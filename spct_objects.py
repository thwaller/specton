# -*- coding: utf-8 -*-

class infoobj(object):
    # result types:
    UNKNOWN = 0
    SCANNER_OUTPUT = 1
    BITGRAPH = 2
    BITHIST = 3
    SPECTROGRAM = 4
    
    def __init__(self, info_type=0, data=None, layout=None, fn=""):
        self.type = info_type
        self.data = data
        self.layout = layout
        self.fn = fn
        
class main_info(object):
    # result types:
    UNKNOWN = 0
    SCANNER_OUTPUT = 1
    ERROR_CHECK = 2
    
    def __init__(self,result_type=0,raw_output="",row=-1,song_info=None):
        self.result_type = result_type
        self.raw_output = raw_output
        self.row = row
        self.song_info = song_info

class song_info_obj(object):
    # result types:
    UNKNOWN = 0
    ERROR_CHECK = 1
    MEDIAINFO = 2
    MP3GUESSENC = 3
    AUCDTECT = 4
    
    def __init__(self):
        self.result_type = 0
        self.cmd_error = False
        self.file_error = False
        self.artist = ""
        self.quality = None
        self.quality_colour = None
        self.encoder = ""
        self.encoderstring = ""
        self.audio_format = ""
        self.bitrate = None
        self.frame_hist = None
        self.frequency = None
        self.mode = None
        self.filesize = None
        self.decode_errors = 0
        self.length = None
        
