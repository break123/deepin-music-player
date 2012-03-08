#!/usr/bin/env python
#-*- coding: utf-8 -*-

        

import utils
from player import Player
import gtk
from library import MediaDB
from widget.dialog import WinDir
from source.local import ImportFolderJob
from widget.jobs_manager import jobs_manager

from ui_toolkit import *
from widget.headerbar import HeaderBar

class PlayList(object):
    def __init__(self):
        MediaDB.load()
        self.songs = MediaDB.get_songs("local")
        self.index = 0
        
    def get_next_song(self):    
        self.songs = MediaDB.get_songs("local")
        self.index += 1
        if self.index > len(self.songs) - 1:
            self.index = 0
        return self.songs[self.index], False   
            
    def get_previous_song(self):
        self.songs = MediaDB.get_songs("local")
        self.index -= 1
        if self.index < 0:
            self.index = len(self.songs) - 1
        return self.songs[self.index]
        
playlists = PlayList()        

class DeepinPlayer(object):
    '''Music player for linux deepin.'''
    def __init__(self):
        self.window = Application("DMuisc")
        self.window.set_default_size(320, 157)
        self.window.add_titlebar(["max", "min", "close"], 
                                 None,
                                 "  Deepin Music")
        

        mainbox = gtk.VBox(spacing=5)
        
        # self.file_chooser = gtk.FileChooserButton("select file")        
        # self.file_chooser.connect("file-set", self.play_cb)
        
        mainbox.pack_start(HeaderBar(), False, False)
        # mainbox.pack_start(self.file_chooser, False, False)
        
        test_button = gtk.Button("PlayList")
        test_button.connect("clicked", self.test_cb)
        
        mainbox.pack_start(test_button)
        mainbox.pack_start(jobs_manager)
        self.window.window.change_background(app_theme.get_pixbuf("skin/main.png"))
        self.window.main_box.pack_start(mainbox)
        
        self.player = Player        
        self.player.set_source(playlists)
        self.window.run()
        
        
    def test_cb(self, widget):    
        # print "dd"
        MediaDB.full_erase("local")
        ImportFolderJob()
        

        
        
    def play_cb(self, widget):
        '''play song'''
        song_uri = utils.get_uri_from_path(widget.get_filename())
        song = MediaDB.create_song({"uri": song_uri}, "local", True)

        self.player.play_new(song)
        
        


        
if __name__ == "__main__":       
    DeepinPlayer()

    

        