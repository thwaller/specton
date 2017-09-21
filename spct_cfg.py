# -*- coding: utf-8 -*-
from appdirs.appdirs import AppDirs
from PyQt5.QtCore import QSettings

AppName = "Specton"
version = 0.172

settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "Specton", "Specton-settings")
filecache = QSettings(QSettings.IniFormat, QSettings.UserScope, "Specton", "Specton-cache")
app_dirs = AppDirs(AppName, "", roaming=True)
debug_enabled = settings.value("Options/Debug", False, type=bool)

maxMRU=8