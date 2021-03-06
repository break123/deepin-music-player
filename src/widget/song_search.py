#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 ~ 2012 Deepin, Inc.
#               2011 ~ 2012 Hou Shaohui
# 
# Author:     Hou Shaohui <houshao55@gmail.com>
# Maintainer: Hou Shaohui <houshao55@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk
import gobject

from dtk.ui.dialog import DialogBox, DIALOG_MASK_SINGLE_PAGE
from dtk.ui.label import Label
from dtk.ui.entry import TextEntry
from dtk.ui.button import Button
from dtk.ui.listview import ListView
from dtk.ui.scrolled_window import ScrolledWindow
from dtk.ui.utils import get_content_size
from dtk.ui.threads import post_gui

from constant import DEFAULT_FONT_SIZE
from query_song import multi_ways_query_song
from widget.ui_utils import render_item_text
from nls import _
import utils


class SongSearchUI(DialogBox):
    
    def __init__(self):
        DialogBox.__init__(self, _("Search"), 460, 300, DIALOG_MASK_SINGLE_PAGE,
                           modal=False, window_hint=None, close_callback=self.hide_all)
        title_label = Label(_("Title:"))
        self.title_entry = TextEntry("")
        self.title_entry.set_size(300, 25)
        self.search_button = Button(_("Search"))
        self.search_button.connect("clicked", self.search_song)
        
        control_box = gtk.HBox(spacing=5)
        control_box.pack_start(title_label, False, False)
        control_box.pack_start(self.title_entry, False, False)
        control_box.pack_start(self.search_button, False, False)
        
        scrolled_window = ScrolledWindow(0, 0)
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.result_view = ListView()
        self.result_view.connect("double-click-item", self.double_click_cb)
        self.result_view.draw_mask = self.get_mask_func(self.result_view)
        self.result_view.add_titles([_("Title"), _("Artist"), _("Album"), _("Type"), _("Size")])
        scrolled_window.add_child(self.result_view)
        
        self.prompt_label = Label("")
        download_button = Button(_("Download"))
        download_button.connect("clicked", self.download_song)
        cancel_button = Button(_("Close"))
        cancel_button.connect("clicked", lambda w: self.hide_all())
        
        self.body_box.set_spacing(5)
        self.body_box.pack_start(control_box, False, False)
        self.body_box.pack_start(scrolled_window, True, True)
        self.left_button_box.set_buttons([self.prompt_label])
        self.right_button_box.set_buttons([download_button, cancel_button])
        
    def search_song(self, widget):    
        self.result_view.clear()
        title = self.title_entry.entry.get_text()
        if not title.strip():
            return 
        self.prompt_label.set_text(_("Now searching"))        
        # widget.set_sensitive(False)
        utils.ThreadRun(multi_ways_query_song, self.render_song_infos, [title]).start()
        
    @post_gui    
    def render_song_infos(self, song_infos):
        if song_infos:
            try:
                items = [QueryInfoItem(song_info) for song_info in song_infos]
            except Exception, e:    
                print e
            else:    
                self.result_view.add_items(items)
        self.prompt_label.set_text(_("Finish!"))        
                
        
    def download_song(self, widget):    
        pass
    
    
    def double_click_cb(self):
        pass
    
        
class QueryInfoItem(gobject.GObject):       
    
    __gsignals__ = {"redraw-request" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),}
    
    def __init__(self, query_info):
        super(QueryInfoItem, self).__init__()
        self.update(query_info)
        
    def set_index(self, index):    
        self.index = index
        
    def get_index(self):    
        return self.index
    
    def emit_redraw_request(self):
        self.emit("redraw-request")
        
    def update(self, query_info):    
        self.title = query_info["title"]
        self.artist = query_info["artist"]
        self.album = query_info["album"]
        self.song_type = query_info["type"]
        self.song_size = query_info["size"]
        self.downlink  = query_info["down"]
        self.song_from = query_info["from"]
    
        # Calculate item size.
        self.title_padding_x = 10
        self.title_padding_y = 5
        (self.title_width, self.title_height) = get_content_size(self.title, DEFAULT_FONT_SIZE)
        
        self.artist_padding_x = 10
        self.artist_padding_y = 5
        (self.artist_width, self.artist_height) = get_content_size(self.artist, DEFAULT_FONT_SIZE)
        
        self.album_padding_x = 10
        self.album_padding_y = 5
        (self.album_width, self.album_height) = get_content_size(self.album, DEFAULT_FONT_SIZE)
        
        self.song_type_padding_x = 10
        self.song_type_padding_y = 5
        (self.song_type_width, self.song_type_height) = get_content_size(self.song_type, DEFAULT_FONT_SIZE)
        
        self.song_size_padding_x = 10
        self.song_size_padding_y = 5
        (self.song_size_width, self.song_size_height) = get_content_size(self.song_size, DEFAULT_FONT_SIZE)
        
        
    def render_title(self, cr, rect, in_select, in_highlight):
        '''Render title.'''
        rect.x += self.title_padding_x
        rect.width -= self.title_padding_x * 2
        render_item_text(cr, self.title, rect, in_select, in_highlight)
    
    def render_artist(self, cr, rect, in_select, in_highlight):
        '''Render artist.'''
        rect.x += self.artist_padding_x
        rect.width -= self.artist_padding_x * 2
        render_item_text(cr, self.artist, rect, in_select, in_highlight)
        
    def render_album(self, cr, rect, in_select, in_highlight):
        '''Render album.'''
        rect.x += self.album_padding_x
        rect.width -= self.album_padding_x * 2
        render_item_text(cr, self.album, rect, in_select, in_highlight)
        
    def render_song_type(self, cr, rect, in_select, in_highlight):
        '''Render song_type.'''
        rect.x += self.song_type_padding_x
        rect.width -= self.song_type_padding_x * 2
        render_item_text(cr, self.song_type, rect, in_select, in_highlight)
        
    def render_song_size(self, cr, rect, in_select, in_highlight):
        '''Render song_size.'''
        rect.x += self.song_size_padding_x
        rect.width -= self.song_size_padding_x * 2
        render_item_text(cr, self.song_size, rect, in_select, in_highlight)
        
        
    def get_column_sizes(self):
        '''Get sizes.'''
        return [(100, self.title_height + self.title_padding_y * 2),
                (100, self.artist_height + self.artist_padding_y * 2),
                (100, self.album_height + self.album_padding_y * 2),
                (30, self.song_type_height + self.song_type_padding_y * 2),
                (30, self.song_size_height + self.song_size_padding_y * 2),
                ]    
    
    def get_renders(self):
        '''Get render callbacks.'''
        return [
            self.render_title,
            self.render_artist,
            self.render_album,
            self.render_song_type,
            self.render_song_size,
            ]
    
    def get_downlink(self):
        return self.downlink
    
    def get_from(self):
        return self.song_from
