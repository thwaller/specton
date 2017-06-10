# -*- coding: utf-8 -*-

class infoobj(object):
    def __init__(self, type="", data=None, layout=None, fn=""):
        self.type = type
        self.data = data
        self.layout = layout
        self.fn = fn
        
class main_info(object):
    def __init__(self,result_type="",raw_output="",row=-1,song_info=None):
        self.result_type = result_type
        self.raw_output = raw_output
        self.row = row
        self.song_info = song_info

class song_info_obj(object):
    def __init__(self):
        self.result_type = None
        self.error = False
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
        
