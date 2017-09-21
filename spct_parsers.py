# -*- coding: utf-8 -*-

import string
from spct_defs import *
from spct_objects import infoobj,main_info,song_info_obj
from spct_utils import format_bytes, debug_log

def doQualityChecks(bitrate,audio_format,encoder):
#    debug_log("doQualityChecks: {},{},{}".format(bitrate,audio_format,encoder))

    colour = colourQualityUnknown
    text = None
    bitrate_min = None
    try:
        bitrate_int = float(bitrate.split()[0])
    except (IndexError,ValueError):
        bitrate_int = None
    
    if audio_format.startswith("Musepack"):
        bitrate_min = 100
        bitrate_good = 160
    elif audio_format.startswith("Vorbis"):
        bitrate_min = 80
        bitrate_good = 150
    elif audio_format.startswith("AAC"):
        bitrate_min = 80
        bitrate_good = 150
    elif audio_format.startswith("Opus"):
        bitrate_min = 40
        bitrate_good = 128

    if not bitrate_min or not bitrate_int:
        return text, colour
        
    if bitrate_int > bitrate_good:
        colour = colourQualityGood
    elif bitrate_int < bitrate_min:
        colour = colourQualityBad
    else:
        colour = colourQualityOk
    
    return text, colour

def doMP3QualityChecks(bitrate,encoder,encoder_string,lame_preset,quality=-1,q=-1,V=-1):
    ''' do some MP3 quality checks '''
    colour = colourQualityUnknown
    text = None
    try:
        bitrate_int = float(bitrate.split()[0])
    except (IndexError,ValueError):
        bitrate_int = None
    
    if not bitrate_int:
        return text,colour
                   
    if encoder.startswith("FhG"):
        if bitrate_int >= 200:
            colour = colourQualityOk
        elif bitrate_int < 128:
            colour = colourQualityBad
        else:
            colour = colourQualityWarning
        
    elif encoder.startswith("Xing (old)") or encoder.startswith("BladeEnc") or encoder.startswith("dist10"):
        if bitrate_int < 160:
            colour = colourQualityBad
        else:
            colour = colourQualityWarning

    elif encoder.startswith("Xing (new)") or encoder.startswith("Helix"):
        if bitrate_int < 128:
            colour = colourQualityBad
        elif bitrate_int > 200:
                colour = colourQualityOk
        else:
            colour = colourQualityWarning

    elif encoder_string.upper().startswith("LAME"):        
        if bitrate_int > 300:
            colour = colourQualityGood # default if no lame tag
        elif bitrate_int > 170:
            colour = colourQualityOk
            
        if lame_preset:
            if lame_preset[0:2] in ["V0", "V1", "V2", "V3"]:
                colour = colourQualityGood
                return lame_preset, colour
            elif lame_preset in ["256 kbps","320 kbps","Standard.","Extreme.","Insane."]: 
                colour = colourQualityGood                
                return "--preset {}".format(lame_preset.lower().strip(".")), colour
            elif (lame_preset in ["160", "192"]) or (lame_preset[0:2] in ["V4", "V5", "V6"]):
                colour = colourQualityOk
                return lame_preset, colour
                
        if quality <= 50:
            colour = colourQualityWarning
        if V > 6:
            colour = colourQualityWarning
        elif V >= 4:
            colour = colourQualityOk            
        elif V >= 0:
            colour = colourQualityGood
        if q > 6:
            colour = colourQualityWarning
        if q > -1 and V > -1:
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
    si.result_type = song_info_obj.MP3GUESSENC
    si.audio_format = "MP3"
    
    if "Cannot find valid mpeg header" in mp3guessenc_output:
        si.file_error = True
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
    search = guessenc_artist_regex.search(mp3guessenc_output)
    if search is not None:
        si.artist=search.group(1).rstrip('.\r')
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
    except IndexError:
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
            
    search = mp3_lame_tag_preset_regex.search(mp3guessenc_output)
    lame_preset = ""
    if search is not None:
        lame_preset = search.group(1).strip()

    search = mp3_xing_quality_regex.search(mp3guessenc_output)
    quality = -1
    q = -1
    V = -1
    if search is not None:
        try:
            quality = int(search.group(1))
        except ValueError:
            quality = -1
        try:
            q = int(search.group(2))
        except ValueError:
            q = -1
        try:
            V = int(search.group(3))
        except ValueError:
            V = -1

    si.quality, si.quality_colour = doMP3QualityChecks(si.bitrate,si.encoder,si.encoderstring,lame_preset,quality,q,V)
    si.length = formatMP3GuessEncDate(length)
    
    return si

def parse_mediainfo_output(mediainfo_output):
    bitrate=""
    length=""
    frequency=""
    bit_depth=""
    bitrate_mode=""
    mode=""
    format_mode=""
    
    si = song_info_obj()
    si.result_type = song_info_obj.MEDIAINFO

    search = mediainfo_encoder_regex.search(mediainfo_output)
    if search is not None:
        si.encoder=search.group(1)
        
    search = mediainfo_artist_regex.search(mediainfo_output)
    if search is not None:
        si.artist=search.group(1)

    search = mediainfo_format_regex.search(mediainfo_output)
    if search is not None:
        si.audio_format=search.group(1)

    search = mediainfo_length_regex.search(mediainfo_output)
    if search is not None:
        length=search.group(1)

    search = mediainfo_bitrate_regex.search(mediainfo_output)
    if search is not None:
        bitrate=search.group(1)

    search = mediainfo_filesize_regex.search(mediainfo_output)
    if search is not None:
        si.filesize=search.group(1)
        
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

    si.bitrate = formatMediaInfoBitrate(bitrate)
    si.length = length.replace(" min","m")
    si.mode = format_mode
    si.frequency = frequency
    si.file_error = False
    si.quality, si.quality_colour = doQualityChecks(si.bitrate,si.audio_format,si.encoder)
    
    return si

def parse_aucdtect_output(aucdtect_output):
    si = song_info_obj()
    si.result_type = song_info_obj.AUCDTECT

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
    
    si.file_error = False

    return si
