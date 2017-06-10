# -*- coding: utf-8 -*-

import string
from spct_defs import *
from spct_objects import infoobj,main_info,song_info_obj
from spct_utils import format_bytes

def doMP3Checks(bitrate,encoder,encoder_string,mp3guessenc_output):
    ''' do some MP3 quality checks '''
    colour = colourQualityUnknown
    text = None
                   
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
    ''' parse mp3guessenc output using regex - return parsed variables as song_info_obj '''
    si = song_info_obj()
    si.result_type = "mp3guessenc"
    si.audio_format = "MP3"
    si.error = False
    
    if "Cannot find valid mpeg header" in mp3guessenc_output:
        si.error = True
        si.audio_format = "MP3?"
        return si
    
    
    bitrate_mode="" # vbr or cbr
    length=""
    mode=""
    format_mode=""

    search = guessenc_encoder_regex.search(mp3guessenc_output)
    if search is not None:
        si.encoder=search.group(1)
    search = guessenc_encoder_string_regex.search(mp3guessenc_output)
    if search is not None:
        si.encoderstring=search.group(1)
    search = guessenc_bitrate_regex.search(mp3guessenc_output)
    if search is not None:
        si.bitrate=search.group(1)
    search = guessenc_length_regex.search(mp3guessenc_output)
    if search is not None:
        length=search.group(1)
    search = guessenc_filesize_regex.search(mp3guessenc_output)
    if search is not None:
        si.filesize=format_bytes(int(search.group(1)))
    search = guessenc_frame_hist_regex.search(mp3guessenc_output)
    if search is not None:
        si.frame_hist=get_bitrate_hist_data(search.group(1))
    search = guessenc_block_usage_regex.search(mp3guessenc_output)
    if search is not None:
        si.block_usage=search.group(1)
    search = guessenc_mode_count_regex.search(mp3guessenc_output)
    if search is not None:
        si.mode_count=search.group(1)
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
        si.frequency = "{} KHz".format(frequency_int/1000)
    search = guessenc_header_errors_regex.search(mp3guessenc_output)
    if search is not None:
        si.decode_errors=int(search.group(1))

    try:
        if len(si.frame_hist[0]) > 1:
            bitrate_mode = "VBR"
        elif len(si.frame_hist[0]) == 1:
            bitrate_mode = "CBR"
    except:
        bitrate_mode = ""
        
    if (not mode == "") and (not bitrate_mode == ""):
        si.mode = "{}/{}".format(mode,bitrate_mode)
    elif (not mode == "") and (bitrate_mode == ""):
        si.mode = "{}".format(mode)
    elif (mode == "") and (not bitrate_mode == ""):
        si.mode = "{}".format(bitrate_mode)

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
                
    si.quality, si.quality_colour = doMP3Checks(si.bitrate,si.encoder,si.encoderstring,mp3guessenc_output)
    si.length = formatMP3GuessEncDate(length)
    
    return si

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
        
    def formatMediaInfoBitrate(br):
#        6 697 kb/s -> 6697 kbps
        br = br.replace(" ","")
        br = br.replace("kb/s"," kbps")
        return br

    si = song_info_obj()
    si.result_type = "mediainfo"
    si.encoder = encoder
    si.audio_format = audio_format
    si.bitrate = formatMediaInfoBitrate(bitrate)
    si.encoderstring = encoder_string
    si.length = length.replace(" min","m")
    si.mode = format_mode
    si.frequency = frequency
    si.filesize = filesize
    si.error = False
    
    return si

def parse_aucdtect_output(aucdtect_output):
    si = song_info_obj()
    si.result_type = "aucdtect"

    detection = ""
    probability = ""
    si.quality_colour = colourQualityUnknown

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
            si.quality_colour = colourQualityGood
        else:
            si.quality_colour = colourQualityWarning
    elif detection == "MPEG":
        if prob_int > aucdtect_confidence_threshold:
            si.quality_colour = colourQualityBad
        else:
            si.quality_colour = colourQualityWarning
    
    if not detection == "Unknown":
        si.quality = "{} {}%".format(detection,probability)
    else:
        si.quality = detection
    
    si.error = False

    return si
