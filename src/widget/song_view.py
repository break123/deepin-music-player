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
import random
import time
import os

from collections import OrderedDict
from dtk.ui.listview import ListView
from dtk.ui.menu import Menu
from dtk.ui.threads import post_gui
from dtk.ui.dialog import InputDialog

import utils
import common
from config import config
from player import Player
from helper import Dispatcher
from library import MediaDB
from widget.dialog import WinFile, WinDir
from widget.song_item import SongItem
from widget.skin import app_theme
from widget.song_editor import SongEditor
from source.local import ImportPlaylistJob
from widget.ui_utils import draw_single_mask, draw_alpha_mask
from nls import _

class SongView(ListView):
    ''' song view. '''
    __gsignals__ = {
        "begin-add-items" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "empty-items" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }
    
    
    def __init__(self):
        
        ListView.__init__(self)        
        targets = [("text/deepin-songs", gtk.TARGET_SAME_APP, 1), ("text/uri-list", 0, 2), ("text/plain", 0, 3)]        
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_DROP,
                           targets, gtk.gdk.ACTION_COPY)
        self.pl = None
        self.add_song_cache = []
        sort_key = ["album", "genre", "artist", "title", "#playcount", "#added"]
        self.sort_reverse = {key : False for key in sort_key }
        self.connect_after("drag-data-received", self.on_drag_data_received)
        self.connect("double-click-item", self.double_click_item_cb)
        self.connect("button-press-event", self.button_press_cb)
        self.connect("delete-select-items", self.try_emit_empty_signal)
        
        MediaDB.connect("removed", self.__remove_songs)
        MediaDB.connect("simple-changed", self.__songs_changed)
        
    def try_emit_empty_signal(self, widget, items):    
        if len(self.items) <= 0:
            self.emit("empty-items")
        
    def double_click_item_cb(self, widget, item, colume, x, y):    
        self.reset_error_items()
        if item:
            song = item.get_song()
            if song.exists():
                self.set_highlight(item)                
                Player.play_new(item.get_song())
                if Player.get_source() != self:
                    Player.set_source(self)
            else:        
                pass
                
    def draw_mask(self, cr, x, y, width, height):            
        draw_alpha_mask(cr, x, y, width, height, "layoutMiddle")
        
    def draw_item_hover(self, cr, x, y, w, h):
        draw_single_mask(cr, x, y, w, h, "simpleItemHover")
        
    def draw_item_select(self, cr, x, y, w, h):    
        draw_single_mask(cr, x, y, w, h, "simpleItemSelect")
        
    def draw_item_highlight(self, cr, x, y, w, h):    
        draw_single_mask(cr, x, y, w, h, "simpleItemHighlight")
        
    def get_songs(self):        
        songs = []
        for song_item in self.items:
            songs.append(song_item.get_song())
        return songs    
    
    def is_empty(self):
        return len(self.items) == 0
    
    def get_loop_mode(self):
        return config.get("setting", "loop_mode")
        
    def set_loop_mode(self, value):    
        config.set("setting", "loop_mode", value)
        
    def get_previous_song(self):
        del self.select_rows[:]
        self.queue_draw()
        self.reset_error_items()
        
        if self.is_empty():
            if config.get("setting", "empty_random") == "true":
                return MediaDB.get_random_song("local")
        else:    
            valid_items = self.get_valid_items()
            if not valid_items: return None
            
            if config.get("setting", "loop_mode") == "random_mode":
                return self.get_random_song()
            
            if self.highlight_item != None:
                if self.highlight_item in valid_items:
                    current_index = valid_items.index(self.highlight_item)
                    prev_index = current_index - 1
                    if prev_index < 0:
                        prev_index = len(valid_items) - 1
                    highlight_item = valid_items[prev_index]    
            else:        
                highlight_item = valid_items[0]
            self.set_highlight(highlight_item)    
            return highlight_item.get_song()
    
    def get_next_song(self, manual=False):
        del self.select_rows[:]
        self.queue_draw()
        self.reset_error_items()
        
        if self.is_empty():
            if config.getboolean("setting", "empty_random"):
                return MediaDB.get_random_song("local")
        else:    
            if manual:
                if config.get("setting", "loop_mode") != "random_mode":
                    return self.get_manual_song()
                else:
                    return self.get_random_song()
            
            elif config.get("setting", "loop_mode") == "list_mode":
                return self.get_manual_song()
            
            elif config.get("setting", "loop_mode") == "order_mode":            
                return self.get_order_song()
            
            elif config.get("setting", "loop_mode") == "single_mode":
                if self.highlight_item != None:
                    return self.highlight_item.get_song()
                
            elif config.get("setting", "loop_mode") == "random_mode":    
                return self.get_random_song()
            
    def get_order_song(self):        
        valid_items = self.get_valid_items()
        if not valid_items: return None
        
        if self.highlight_item:
            if self.highlight_item in valid_items:
                current_index = valid_items.index(self.highlight_item)
                next_index = current_index + 1
                if next_index <= len(valid_items) -1:
                    highlight_item = valid_items[next_index]    
                    self.set_highlight(highlight_item)
                    return highlight_item.get_song()
        return None        
            
    def reset_error_items(self):        
        for each_item in self.items:
            if each_item.exists():
                each_item.clear_error()
            else:    
                each_item.set_error()
                        
    def get_manual_song(self):                    
        valid_items = self.get_valid_items()
        if not valid_items: return None
        if self.highlight_item:
            if self.highlight_item in valid_items:
                current_index = valid_items.index(self.highlight_item)
                next_index = current_index + 1
                if next_index > len(valid_items) - 1:
                    next_index = 0
                highlight_item = valid_items[next_index]    
            else:    
                highlight_item = valid_items[0]
        else:        
            highlight_item = valid_items[0]
        self.set_highlight(highlight_item)    
        return highlight_item.get_song()
    
    def get_valid_songs(self):
        self.reset_error_items()
        songs = []
        for item in self.get_valid_items():
            songs.append(item.get_song())
        return songs    
    
    def get_random_song(self):
        valid_items = self.get_valid_items()
        if not valid_items: return None
        
        if self.highlight_item in valid_items:
            current_index = [valid_items.index(self.highlight_item)]
        else:    
            current_index = [-1]
        items_index = set(range(len(valid_items)))
        remaining = items_index.difference(current_index)
        highlight_item = valid_items[random.choice(list(remaining))]
        self.set_highlight(highlight_item)
        return highlight_item.get_song()
    
    def get_valid_items(self):
        return [item for item in self.items if not item.is_error()]

    def add_songs(self, songs, pos=None, sort=False, play=False):    
        '''Add song to songlist.'''
        if songs == None:
            return
        if not isinstance(songs, (list, tuple)):
            songs = [ songs ]

        song_items = [ SongItem(song) for song in songs if song not in self.get_songs()]
            
        if song_items:
            if not self.items:
                self.emit_add_signal()
            self.add_items(song_items, pos, sort)
            
            
        if len(songs) >= 1 and play:
            if songs[0].exists():
                del self.select_rows[:]
                self.queue_draw()
                self.set_highlight_song(songs[0])
                gobject.idle_add(Player.play_new, self.highlight_item.get_song())
            
    def emit_add_signal(self):
        self.emit("begin-add-items")
    
    def play_uris(self, uris, pos=None, sort=True):        
        self.get_toplevel().window.set_cursor(None)
        songs = []
        for uri in uris:
            song = MediaDB.get_song(uri)
            if song:
                songs.append(song)
        if not songs:        
            return
        if sort: songs.sort()
        self.add_songs(song, pos, sort, True)
            
    def add_uris(self, uris, pos=None, sort=True):
        if uris == None:
            return
        if not isinstance(uris, (tuple, list, set)):
            uris = [ uris ]

        uris = [ utils.get_uri_from_path(uri) for uri in uris ]    
        utils.ThreadLoad(self.load_taginfo, uris, pos, sort).start()
        # self.load_taginfo(uris, pos, sort)
    
    def load_taginfo(self, uris, pos=None, sort=True):
        start = time.time()
        if pos is None:
            pos = len(self.items)
        for uri in uris:    
            song = MediaDB.get_song(uri)
            if not song:
                continue
            self.add_song_cache.append(song)
            end = time.time()
            if end - start > 0.2:
                self.render_song(self.add_song_cache, pos, sort)
                pos += len(self.add_song_cache)
                del self.add_song_cache[:]
                start = time.time()

        if self.add_song_cache:
            self.render_song(self.add_song_cache, pos, sort)
            del self.add_song_cache[:]
                
    @post_gui
    def render_song(self, songs, pos, sort):    
        if songs:
            self.add_songs(songs, pos, sort)
        
    def get_current_song(self):        
        return self.highlight_item.get_song()
    
    def random_reorder(self, *args):
        with self.keep_select_status():
            random.shuffle(self.items)
            self.update_item_index()
            self.queue_draw()
            
    def set_highlight_song(self, song):        
        if not song: return 
        if SongItem(song) in self.items:
            self.set_highlight(self.items[self.items.index(SongItem(song))])
            self.visible_highlight()
            self.queue_draw()
        
    def play_select_item(self):    
        if len(self.select_rows) > 0:
            select_item = self.items[self.select_rows[0]]
            if select_item.exists():
                self.highlight_item = self.items[self.select_rows[0]]
                Player.play_new(self.highlight_item.get_song())
    
    def remove_select_items(self):
        self.delete_select_items()
        return True
    
    def erase_items(self):
        self.clear()
        self.emit_empty_signal(None, None)
        return True
    
    def open_song_dir(self):
        if len(self.select_rows) > 0:
            song = self.items[self.select_rows[0]].get_song()
            utils.open_file_directory(song.get_path())
    
    def open_song_editor(self):
        if len(self.select_rows) > 0:
            index = self.select_rows[0]
            select_item = self.items[index]
            if select_item.exists():
                SongEditor([select_item.get_song()]).show_all()
    
    def move_to_trash(self):
        flag = False
        if len(self.select_rows) > 0:
            songs = [ self.items[self.select_rows[index]].get_song() for index in range(0, len(self.select_rows))]
            if self.highlight_item and self.highlight_item.get_song() in songs:
                Player.stop()
                self.highlight_item = None
                flag = True
            MediaDB.remove(songs)    
            [ utils.move_to_trash(song.get("uri")) for song in songs ]
            self.delete_select_items()            
            if flag:
                Player.next()
        return True    
        
    def on_drag_data_received(self, widget, context, x, y, selection, info, timestamp):    
        root_y = widget.allocation.y + y
        try:
            pos = self.get_coordinate_row(root_y)
        except:    
            pos = None
            
        if pos == None:    
            pos = len(self.items)
            
        if selection.target in ["text/uri-list", "text/plain", "text/deepin-songs"]:
            if selection.target == "text/deepin-songs" and selection.data:
                self.add_uris(selection.data.splitlines(), pos, False)
            elif selection.target == "text/uri-list":    
                selected_uris = selection.get_uris()
                if len(selected_uris) == 1 and os.path.isdir(utils.get_path_from_uri(selected_uris[0])):
                    self.recursion_add_dir(utils.get_path_from_uri(selected_uris[0]))
                else:
                    utils.async_parse_uris(selection.get_uris(), True, False, self.add_uris, pos)
            elif selection.target == "text/plain":    
                raw_path = selection.data
                path = eval("u" + repr(raw_path).replace("\\\\", "\\"))
                utils.async_get_uris_from_plain_text(path, self.add_uris, pos)
    
    def set_sort_keyword(self, keyword, reverse=False):
        with self.keep_select_status():
            reverse = self.sort_reverse[keyword]
            self.items = sorted(self.items, 
                                key=lambda item: item.get_song().get_sortable(keyword),
                                reverse=reverse)
            self.sort_reverse[keyword] = not reverse
            self.update_item_index()
            if self.highlight_item != None:
                self.visible_highlight()
            self.queue_draw()
    
    def get_playmode_menu(self, pos=[], align=False):
        mode_dict = OrderedDict()

        mode_dict["single_mode"] = _("Repeat")
        mode_dict["order_mode"] = _("Play(ordered)")
        mode_dict["list_mode"] = _("Repeat list")
        mode_dict["random_mode"] = _("Shuffle")        
        
        mode_items = []
        for key, value in mode_dict.iteritems():
            if self.get_loop_mode() == key:
                tick = (app_theme.get_pixbuf("menu/tick.png"),
                        app_theme.get_pixbuf("menu/tick_press.png"))
                mode_items.append((tick, value, self.set_loop_mode, key))                    
            else:    
                tick = None
                mode_items.append((None, value, self.set_loop_mode, key))                    

        if pos:
            Menu(mode_items, True).show((pos[0], pos[1]))
        else:    
            return Menu(mode_items)
        
    def button_press_cb(self, widget, event):    
        if event.button == 3 and not self.items:
            self.popup_add_menu(int(event.x_root), int(event.y_root))

    def popup_delete_menu(self, x, y):    
        items = [(None, _("Remove track this list"), self.remove_select_items),
                 (None, _("Remove unavailable track"), self.delete_error_items),
                 (None, _("Move to trash"), self.move_to_trash),
                 (None, _("Clear list"), self.erase_items)]
        Menu(items, True).show((int(x), int(y)))
        
    def delete_error_items(self):    
        self.reset_error_items()
        self.items = self.get_valid_items()
        self.update_item_index()
        self.update_vadjustment()
        self.queue_draw()
        
    def popup_add_menu(self, x, y):
        menu_items = [
            (None, _("URI"), self.add_unknow_uri),            
            (None, _("File"), self.add_file),
            (None, _("Directory(recursion)"), self.recursion_add_dir),
            (None, _("Directory"), self.add_dir),
            ]
        Menu(menu_items, True).show((x, y))
        
    def get_add_menu(self):    
        menu_items = [
            (None, _("File"), self.add_file),
            (None, _("Directory(recursion)"), self.recursion_add_dir),
            (None, _("Directory"), self.add_dir),
            ]
        return Menu(menu_items)
    
    def add_unknow_uri(self, uri=None):
        def play_or_add_uri(uri):
            MediaDB.get_or_create_song({"uri": uri}, "unknown")
            self.play_uris([uri])
            
        if not uri:
            input_dialog = InputDialog(_("Add URI"), "", 300, 100, lambda name : play_or_add_uri(name))
            input_dialog.show_all()
        else:    
            play_or_add_uri(uri)    
    
    def add_file(self, filename=None, play=False):
        if filename is None:
            uri = WinFile().run()        
        else:    
            uri = utils.get_uri_from_path(filename)
            
        if uri and common.file_is_supported(utils.get_path_from_uri(uri)):
            tags = {"uri": uri}
            try:
                song = MediaDB.get_or_create_song(tags, "local", read_from_file=True)
            except:    
                pass
            else:
                self.add_songs(song, play=play)
                
    def add_dir(self):            
        select_dir = WinDir().run()
        if select_dir:
            utils.async_parse_uris([select_dir], True, False, self.add_uris)
            
    def recursion_add_dir(self, init_dir=None):        
        pos = len(self.items)
        ImportPlaylistJob(init_dir, self.add_uris, pos, False)
            
    def async_add_uris(self, uris, follow_folder=True):        
        if not isinstance(uris, (list, tuple, set)):
            uris = [ uris ]
        utils.async_parse_uris(uris, follow_folder, True, self.add_uris)
        
    def __songs_changed(self, db, infos):    
        indexs = []
        view_songs = self.get_songs()
        for each_song in infos:
            if each_song in view_songs:
                indexs.append(view_songs.index(each_song))
                
        if indexs:        
            for index in indexs:
                item = self.items[index]
                item.update(MediaDB.get_song(item.get_song().get("uri")), True)
        
    def __remove_songs(self, db, song_type, songs):    
        indexs = []
        flag = False
        view_songs = self.get_songs()
        
        if self.highlight_item and self.highlight_item.get_song() in songs:
            Player.stop()
            self.highlight_item = None
            flag = True
        
        for song in songs:
            if song in view_songs:
                indexs.append(view_songs.index(song))
        if indexs:        
            for index in indexs:
                del self.items[index]
            self.update_item_index()
            self.update_vadjustment()        
            self.queue_draw()    
            
        if flag:    
            if len(self.get_valid_items()) > 0:
                item = self.get_valid_items()[0]
                self.set_highlight(item)
                Player.play_new(item.get_song())

class MultiDragSongView(ListView):        
    def __init__(self):
        targets = [("text/deepin-songs", gtk.TARGET_SAME_APP, 1), ("text/uri-list", 0, 2), ("text/plain", 0, 3)]        
        ListView.__init__(self, drag_data=(targets, gtk.gdk.ACTION_COPY, 1))
        
        self.sorts = [
            (lambda item: item.get_song().get_sortable("title"), cmp),
            (lambda item: item.get_song().get_sortable("artist"), cmp),
            (lambda item: item.get_song().get_sortable("album"), cmp),
            (lambda item: item.get_song().get_sortable("#added"), cmp),
            ]
        
        sort_key = ["album", "genre", "artist", "title", "#playcount", "#added"]
        self.sort_reverse = {key : False for key in sort_key }
        
        self.set_expand_column(0)
        self.connect("drag-data-get", self.__on_drag_data_get) 
        self.connect("double-click-item", self.__on_double_click_item)
        self.connect("right-press-items", self.popup_right_menu)
        
    def draw_item_hover(self, cr, x, y, w, h):
        draw_single_mask(cr, x, y, w, h, "simpleItemHover")
        
    def draw_item_select(self, cr, x, y, w, h):    
        draw_single_mask(cr, x, y, w, h, "simpleItemHighlight")
        
    def draw_item_highlight(self, cr, x, y, w, h):    
        draw_single_mask(cr, x, y, w, h, "simpleItemSelect")
        
    def get_selected_songs(self):    
        songs = []
        if len(self.select_rows) > 0:
            songs = [ self.items[index].get_song() for index in self.select_rows ]
        return songs
            
    def __on_drag_data_get(self, widget, context, selection, info, timestamp):    
        songs = self.get_selected_songs()
        if not songs:
            return
        songs.sort()
        list_uris = list([ song.get("uri") for song in songs])
        selection.set("text/deepin-songs", 8, "\n".join(list_uris))
        selection.set_uris(list_uris)
        
    def __on_double_click_item(self, widget, item, colume, x, y):    
        if item:
            Dispatcher.play_and_add_song(item.get_song())
        
    def add_songs(self, songs, pos=None, sort=False):        
        if not songs:
            return 
        if not isinstance(songs, (list, tuple, set)):
            songs = [ songs ]
        song_items = [ SongItem(song, True) for song in songs if song not in self.get_songs() ]    
        
        if song_items:
            self.add_items(song_items, pos, sort)

    def get_songs(self):        
        songs = []
        for song_item in self.items:
            songs.append(song_item.get_song())
        return songs    
            
    def is_empty(self):        
        return len(self.items) == 0
    
    def set_sort_keyword(self, keyword, reverse_able=False):
        with self.keep_select_status():
            reverse = self.sort_reverse[keyword]
            self.items = sorted(self.items, 
                                key=lambda item: item.get_song().get_sortable(keyword),
                                reverse=reverse)
            if reverse_able:
                self.sort_reverse[keyword] = not reverse
            self.update_item_index()
            self.queue_draw()
            
    def open_song_dir(self):
        if len(self.select_rows) > 0:
            song = self.items[self.select_rows[0]].get_song()
            if song.exists():
                utils.open_file_directory(song.get_path())
    
    def emit_to_playlist(self):
        if len(self.select_rows) > 0:
            songs = [self.items[index].get_song() for index in self.select_rows]
            Dispatcher.add_songs(songs)
    
    def play_song(self):
        if len(self.select_rows) > 0:
            song = self.items[self.select_rows[0]].get_song()
            Dispatcher.play_and_add_song(song)
        return True    
    
    def open_song_editor(self):
        if len(self.select_rows) > 0:
            index = self.select_rows[0]
            select_item = self.items[index]
            if select_item.exists():
                SongEditor([select_item.get_song()]).show_all()
                
            
    def remove_songs(self, fully=False):
        if len(self.select_rows) > 0:
            songs = [ self.items[self.select_rows[index]].get_song() for index in range(0, len(self.select_rows))]
            MediaDB.remove(songs)    
            if fully:
                [ utils.move_to_trash(song.get("uri")) for song in songs ]
            self.delete_select_items()            
        return True    

    def popup_right_menu(self, widget, x, y, item, select_items):
        menu_items = [
            (None, _("Play track"), self.play_song),
            (None, _("Add to playlist"), self.emit_to_playlist),
            None,
            (None, _("Remove from library"), self.remove_songs),
            (None, _("Move to trash"), self.remove_songs, True),
            None,
            (None, _("Open directory"), self.open_song_dir),
            (None, _("Property"), self.open_song_editor)
                        ]
            
        Menu(menu_items, True).show((int(x), int(y)))
