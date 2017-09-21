# -*- coding: utf-8 -*-

import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

TableHeaders = (
    "Artist", "Folder", "Filename", "Length", "Bitrate", "Mode", "Frequency", "Filesize", "Errors", "Hash", "Encoder",
    "Quality")

dataScanned = 32
dataFilenameStr = 33
dataBitrate = 35

aucdtect_confidence_threshold = 90  # aucdtect results considered accurate when probability is higher than this

LossyFormats=(".mp3",".opus",".mpc",".ogg",".m4a",".aac",".ac3",".ra",".au")
LosslessFormats=(".flac",".wav",".shn",".ape",".tta",".wv")

# define some colours
colourQualityUnknown = QColor(Qt.lightGray)
colourQualityUnknown.setAlpha(100)
colourQualityGood = QColor(Qt.green)
colourQualityGood.setAlpha(100)
colourQualityOk = QColor(Qt.darkGreen)
colourQualityOk.setAlpha(100)
colourQualityWarning = QColor(Qt.yellow)
colourQualityWarning.setAlpha(100)
colourQualityBad = QColor(Qt.red)
colourQualityBad.setAlpha(100)

defaultfilemask = r"\.(mp3|opus|flac|mpc|ogg|wav|m4a|aac|ac3|ra|au|shn|ape|tta|wv)$"

guessenc_encoder_regex = re.compile(r"^Maybe this file is encoded by (.*)", re.MULTILINE)
guessenc_encoder_string_regex = re.compile(r"^Encoder string \: (.*)", re.MULTILINE)
guessenc_artist_regex = re.compile(r"Artist.*\: (.*)", re.MULTILINE)
guessenc_bitrate_regex = re.compile(r"Data rate.*\: (.*)", re.MULTILINE)
guessenc_length_regex = re.compile(r"Length.*\: ([\d\:\.]*)", re.MULTILINE)
guessenc_frequency_regex = re.compile(r"^\s*Audio frequency\s*: (\d*) Hz", re.MULTILINE)
guessenc_mode_regex = re.compile(r"Detected MPEG stream.*?Encoding mode\s*?: (.*?)\n", re.DOTALL)
guessenc_filesize_regex = re.compile(r"Detected .*?\n  File size.*?\: (\d*) bytes", re.MULTILINE)
guessenc_frame_hist_regex = re.compile(r"Frame histogram(.*?)(\d*) header errors", re.DOTALL)
guessenc_block_usage_regex = re.compile(r"^Block usage(.*?)-", re.DOTALL | re.MULTILINE)
guessenc_mode_count_regex = re.compile(r"^Mode extension: (.*?)--", re.DOTALL | re.MULTILINE)
guessenc_header_errors_regex = re.compile(r"^\s*(\d*) header errors", re.MULTILINE)
mediainfo_format_regex = re.compile(r"^Audio.*?Format.*?\: (.*?)$", re.DOTALL | re.MULTILINE)
mediainfo_encoder_regex = re.compile(r"^Writing library.*\: (.*)", re.MULTILINE)
mediainfo_artist_regex = re.compile(r"^Performer.*\: (.*)", re.MULTILINE)
mediainfo_length_regex = re.compile(r"^Audio.*?Duration.*?\: (.*?)$", re.DOTALL | re.MULTILINE)
mediainfo_bitrate_regex = re.compile(
    r"^(?:General.*Overall bit rate|Audio.*Bit rate).*?: ([\d\. ]+ [GMK]bps|[\d\. ]+ kb/s)", re.MULTILINE | re.DOTALL)
mediainfo_bitrate_mode_regex = re.compile(r"^Audio.*Bit rate mode\s*: ([A-Za-z]*)",
                                          re.MULTILINE | re.DOTALL)  # variable or constant
mediainfo_filesize_regex = re.compile(r"^File size.*\: (.* .iB|.* Bytes)", re.MULTILINE)
mediainfo_frequency_regex = re.compile(r"^Audio.*Sampling rate\s*: ([\d\.]* [kK]Hz)", re.MULTILINE | re.DOTALL)
mediainfo_bitdepth_regex = re.compile(r"^Audio.*Bit depth\s*: ([\d\.]*) bits", re.MULTILINE | re.DOTALL)
mediainfo_mode_regex = re.compile(r"^Audio.*[Mm]ode\s*: ([a-zA-Z ]*)", re.MULTILINE | re.DOTALL)  # stereo/js
aucdtect_regex = re.compile(r"^This track looks like (.*) with probability (\d*)%", re.MULTILINE)
mp3_bitrate_data_regex = re.compile(r"(\d*?) kbps \: *(\d*?) \(")
mp3_lame_tag_preset_regex = re.compile(r"^Lame tag.*Preset\s*:\s*(.*?)Orig", re.MULTILINE | re.DOTALL)
mp3_xing_quality_regex = re.compile(r"^Xing.*?Quality\s*?:\s*?(\d*?)\s*?\(-q (\d*?) -V (\d*?)\)",
                                    re.MULTILINE | re.DOTALL)
mp3_duration_format_regex = re.compile(r"(\d*?):(\d*?):(\d*\.\d*)")
