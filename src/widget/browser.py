#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011~2012 Deepin, Inc.
#               2011~2012 Hou Shaohui
#
# Author:     Hou Shaohui <houshao55@gmail.com>
# Maintainer: Hou ShaoHui <houshao55@gmail.com>
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
import os

from dtk.ui.draw import draw_pixbuf
from dtk.ui.scrolled_window import ScrolledWindow
from dtk.ui.button import ImageButton
from dtk.ui.iconview import IconView
from dtk.ui.line import HSeparator

from library import MediaDB, DBQuery
from helper import SignalContainer, Dispatcher
from widget.skin import app_theme
from widget.ui import SearchEntry
from widget.song_view import MultiDragSongView
from widget.ui_utils import switch_tab, render_text, draw_alpha_mask, create_right_align
from widget.outlookbar import OptionBar, SongPathBar, SongImportBar
from source.local import ImportFolderJob, ReloadDBJob
from widget.combo import ComboMenuButton
from cover_manager import CoverManager
from pinyin import TransforDB
from nls import _


class IconItem(gobject.GObject):
    
    __gsignals__ = { "redraw-request" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),}
    
    def __init__(self, _tuple):
        super(IconItem, self).__init__()
        self.cell_width = 83        
        self.key_name, value_name, nums, self.tag = _tuple
        self.draw_side_flag = True
        
        if not self.key_name:
            self.name_label= _("Unknown")
            if self.tag == "genre":
                self.pixbuf = CoverManager.get_pixbuf_from_genre(self.name_label)
            else:    
                self.pixbuf = CoverManager.get_pixbuf_from_name(self.name_label, self.cell_width, self.cell_width)            
            
        elif self.key_name == "deepin-all-songs":    
            self.pixbuf = CoverManager.get_all_song_cover(self.cell_width, self.cell_width)
            self.name_label = _("All tracks")
            self.draw_side_flag = False
        else:    
            self.name_label = self.key_name
            if self.tag == "genre":
                self.pixbuf = CoverManager.get_pixbuf_from_genre(self.name_label)
            elif self.tag == "album":    
                self.pixbuf = CoverManager.get_pixbuf_from_name("%s-%s" % (value_name, self.key_name), 
                                                                self.cell_width, self.cell_width)            
            else:    
                self.pixbuf = CoverManager.get_pixbuf_from_name(self.key_name, self.cell_width, self.cell_width)
            
        self.labels = _("%d tracks") % nums
        self.padding_x = 4
        self.padding_y = 4
        self.hover_flag = False
        self.highlight_flag = False
        self.__draw_play_hover_flag = False
        self.__draw_play_press_flag = False
        self.__normal_side_pixbuf =  app_theme.get_pixbuf("filter/side_normal.png").get_pixbuf()
        self.__normal_play_pixbuf =  app_theme.get_pixbuf("filter/play_normal.png").get_pixbuf()
        
        self.play_rect = gtk.gdk.Rectangle(
            self.__normal_side_pixbuf.get_width() - self.__normal_play_pixbuf.get_width() - 2 - 6,
            self.__normal_side_pixbuf.get_height() - self.__normal_play_pixbuf.get_height() - 2 - 6,
            self.__normal_play_pixbuf.get_width(),
            self.__normal_play_pixbuf.get_height()
            )
        
        self.retrieve = TransforDB.convert(self.name_label.lower().replace(" ", "")) + self.name_label.lower().replace(" ", "")
        
    def pointer_in_play_rect(self, x, y):    
        if self.play_rect.x < x < self.play_rect.x + self.play_rect.width and self.play_rect.y < y < self.play_rect.y + self.play_rect.height:
            return True
        else:
            return False
        
    def pointer_in_pixbuf_rect(self, x, y):    
        pixbuf_rect = gtk.gdk.Rectangle(
            0, 0,
            self.__normal_side_pixbuf.get_width(),
            self.__normal_side_pixbuf.get_height(),
            )
        if pixbuf_rect.x < x < pixbuf_rect.x + pixbuf_rect.width and pixbuf_rect.y < y < pixbuf_rect.y + pixbuf_rect.height:
            return True
        else:
            return False
        
    def emit_redraw_request(self):    
        self.emit("redraw-request")
        
    def get_width(self):    
        return self.__normal_side_pixbuf.get_width() + self.padding_x * 2 + 8
    
    def get_height(self):
        return self.__normal_side_pixbuf.get_height() + self.padding_y * 2 + 40
    
    def render(self, cr, rect):
        
            
        # Draw cover.
        draw_pixbuf(cr, self.pixbuf, 
                    rect.x + self.padding_x,
                    rect.y + self.padding_y)
        
        if self.hover_flag or self.highlight_flag:
            side_pixbuf = app_theme.get_pixbuf("filter/side_hover.png").get_pixbuf()
            draw_pixbuf(cr, side_pixbuf, rect.x, rect.y )            
        else:    
            if self.draw_side_flag:
                side_pixbuf = self.__normal_side_pixbuf
                draw_pixbuf(cr, side_pixbuf, rect.x, rect.y )            
        
        if self.hover_flag:
            if self.__draw_play_hover_flag:
                play_pixbuf = app_theme.get_pixbuf("filter/play_hover.png").get_pixbuf()
            elif self.__draw_play_press_flag:    
                play_pixbuf = app_theme.get_pixbuf("filter/play_press.png").get_pixbuf()
            else:    
                play_pixbuf = self.__normal_play_pixbuf
                
            draw_pixbuf(cr, play_pixbuf, rect.x + self.play_rect.x, rect.y + self.play_rect.y)        
            
        # Draw text.    
        name_rect = gtk.gdk.Rectangle(rect.x + self.padding_x , 
                                      rect.y + self.__normal_side_pixbuf.get_height() + 5,
                                      self.cell_width, 11)
        num_rect = gtk.gdk.Rectangle(name_rect.x, name_rect.y + 16, name_rect.width, 9)
        
        render_text(cr, self.name_label, name_rect, 
                    app_theme.get_color("labelText").get_color(),
                    10)
        render_text(cr, self.labels, num_rect, 
                    app_theme.get_color("labelText").get_color(),
                    8)
        
    def icon_item_motion_notify(self, x, y):    
        self.hover_flag = True
        if self.pointer_in_play_rect(x, y):
            if self.__draw_play_press_flag:
                self.__draw_play_hover_flag =  False
            else:    
                self.__draw_play_hover_flag = True
        else:    
            self.__draw_play_hover_flag = False
            
        self.emit_redraw_request()
        
    def icon_item_lost_focus(self):    
        self.__draw_play_flag = False
        self.hover_flag = False
        self.emit_redraw_request()
        
    def icon_item_highlight(self):    
        self.highlight_flag = True
        self.emit_redraw_request()
        
    def icon_item_normal(self):    
        self.highlight_flag = False
        self.emit_redraw_request()
        
    def icon_item_button_press(self, x, y):    
        if self.pointer_in_play_rect(x, y):
            self.__draw_play_hover_flag =  False
            self.__draw_play_press_flag = True
        else:    
            self.__draw_play_press_flag = False
        self.emit_redraw_request()
    
    def icon_item_button_release(self, x, y):
        self.__draw_play_press_flag = False
        self.emit_redraw_request()
    
    def icon_item_single_click(self, x, y):
        pass
    
    def icon_item_double_click(self, x, y):
        pass
        
gobject.type_register(IconItem)        

ICON_VIEW_MODE, LIST_VIEW_MODE = 1, 2

class Browser(gtk.VBox, SignalContainer):
    
    def __init__(self, db_query):
        
        gtk.VBox.__init__(self)
        SignalContainer.__init__(self)
        
        self.__db_query = db_query
        self._tree = {}
        self.__selected_tag = {"album": [], "artist": [], "genre": []}
        self.view_mode = ICON_VIEW_MODE
        self.__search_flag = False
        self.__song_cache_items = []
        self.__cover_cache_items = []
        
        # init widget.
        self.entry_box = SearchEntry("")
        self.entry_box.set_size(155, 22)
        self.entry_box.entry.connect("changed", self.__search_cb)
        
        # upper box.
        self.back_button = self.__create_simple_button("back", self.__switch_to_filter_view)
        self.back_button.set_no_show_all(True)
        back_align = gtk.Alignment()
        back_align.set(0.5, 0.5, 0, 0)
        back_align.set_padding(0, 0, 0, 10)
        back_align.add(self.back_button)
        
        # path control
        self.path_combo_box = ComboMenuButton()
        self.path_combo_box.connect("list-actived", lambda w: self.update_path_list_view())
        self.path_combo_box.connect("combo-actived", lambda w, k : self.update_path_filter_view(k))
        path_combo_align = gtk.Alignment()
        path_combo_align.set_padding(0, 0, 10, 0)
        path_combo_align.add(self.path_combo_box)
        self.path_combo_box.set_no_show_all(True)
        
        upper_box = gtk.HBox(spacing=5)
        upper_box.pack_start(path_combo_align, False, False)
        upper_box.pack_start(create_right_align(), True, True)
        upper_box.pack_start(back_align, False, False)
        entry_box_align = gtk.Alignment()
        entry_box_align.set(0.5, 0.5, 0, 0)
        entry_box_align.set_padding(1, 0, 0, 0)
        entry_box_align.add(self.entry_box)
        upper_box.pack_start(entry_box_align, False, False)
        
        upper_box_align = gtk.Alignment()
        upper_box_align.set_padding(0, 10, 0, 10)
        upper_box_align.set(0.5, 0.5, 1, 1)
        upper_box_align.connect("expose-event", self.expose_upper_box_mask)
        upper_box_align.add(upper_box)
        
        self.categorybar_status = "artist"
        self.filter_categorybar = OptionBar(
            [(app_theme.get_pixbuf("filter/artist_normal.png"), app_theme.get_pixbuf("filter/artist_press.png"),
              _("By artist"), lambda : self.reload_filter_view("artist", True)),
             (app_theme.get_pixbuf("filter/album_normal.png"), app_theme.get_pixbuf("filter/album_press.png"),
              _("By album"), lambda : self.reload_filter_view("album", True)),
             (app_theme.get_pixbuf("filter/genre_normal.png"), app_theme.get_pixbuf("filter/genre_press.png"),
              _("By genre"), lambda : self.reload_filter_view("genre", True)),]
                                            )
        
        # Song path bar.
        self.__current_path = None
        self.current_icon_item = None
        self.reload_path_flag = True
        self.path_categorybar = SongPathBar(_("Local"))
        self.path_categorybar.set_size_request(-1, 205)
        
        # Song import bar.
        self.import_categorybar = SongImportBar()
        self.import_categorybar.reload_items(
            [
             (_("Scan Home dir"), lambda : ImportFolderJob([os.path.expanduser("~")])),                
             (_("Select dir to scan"), lambda : ImportFolderJob()),
             (_("Refresh library"), lambda : ReloadDBJob())]
            )
        
        # iconview.
        self.filter_view = IconView(10, 10)
        targets = [("text/deepin-songs", gtk.TARGET_SAME_APP, 1), ("text/uri-list", 0, 2)]
        self.filter_view.drag_source_set(gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        self.filter_view.connect("drag-data-get", self.__on_drag_data_get) 
        self.filter_view.connect("double-click-item", self.__on_double_click_item)
        self.filter_view.connect("single-click-item", self.__on_single_click_item)
        self.filter_view.draw_mask  = self.draw_filter_view_mask
        self.filter_scrolled_window = ScrolledWindow()
        self.filter_scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.filter_scrolled_window.add_child(self.filter_view)
        
        # songs_view
        self.songs_view = MultiDragSongView()
        self.songs_view.add_titles([_("Title"), _("Artist"), _("Album"), _("Added time")])
        self.songs_scrolled_window = ScrolledWindow(0, 0)
        self.songs_scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.songs_scrolled_window.add_child(self.songs_view)
        
        # left_vbox
        align = gtk.Alignment()
        align.set(0, 1, 0, 0)
        left_box = gtk.VBox(spacing=10)
        left_box.set_size_request(140, -1)
        left_box.pack_start(self.filter_categorybar, False, False)
        left_box.pack_start(self.create_separator_box(), False, False)
        left_box.pack_start(self.path_categorybar, False, False)
        left_box.pack_start(self.create_separator_box(), False, False)
        left_box.pack_start(self.import_categorybar, False, False)
        left_box.pack_start(align, True, True)
        left_box.connect("expose-event", self.expose_left_box_mask)
        
        # right_box.
        self.right_box = gtk.VBox()
        self.right_box.add(self.filter_scrolled_window)
        
        # swith_box
        right_box_align = gtk.Alignment()
        right_box_align.set_padding(0, 0, 0, 2)
        right_box_align.set(1, 1, 1, 1)
        right_box_align.add(self.right_box)
        browser_box = gtk.VBox()
        browser_box.pack_start(upper_box_align,  False, False)
        browser_box.pack_start(right_box_align, True, True)
        
        body_box = gtk.HBox()
        body_box.pack_start(left_box, False, False)
        body_box.pack_start(browser_box, True, True)
        self.pack_start(body_box, True, True)
        
        self.reload_flag = False
        Dispatcher.connect("reload-browser", self.reload_browser)
        gobject.timeout_add(5000, self.interval_reload_browser)
        
    def __create_simple_button(self, name, callback):    
        button = ImageButton(
            app_theme.get_pixbuf("filter/%s_normal.png" % name),
            app_theme.get_pixbuf("filter/%s_hover.png" % name),
            app_theme.get_pixbuf("filter/%s_press.png" % name),
            )
        if callback:
            button.connect("clicked", callback)
        return button    
    
    def expose_left_box_mask(self, widget, event):
        cr = widget.window.cairo_create()
        rect = widget.allocation
        draw_alpha_mask(cr, rect.x, rect.y, rect.width, rect.height, "layoutRight")
        return False
    
    def expose_upper_box_mask(self, widget, event):
        cr = widget.window.cairo_create()
        rect = widget.allocation
        draw_alpha_mask(cr, rect.x, rect.y, rect.width - 2, rect.height, "layoutLast")
        return False
    
    def draw_filter_view_mask(self, cr, x, y, width, height):
        draw_alpha_mask(cr, x, y, width, height, "layoutLast")
    
    def create_separator_box(self, padding_x=0, padding_y=0):
        separator_box = HSeparator(
            app_theme.get_shadow_color("hSeparator").get_color_info(),
            padding_x, padding_y)
        return separator_box
    
    def __switch_to_filter_view(self, widget):
        self.back_button.set_no_show_all(True)
        self.back_button.hide()
        self.switch_box(self.right_box, self.filter_scrolled_window)
        self.view_mode = ICON_VIEW_MODE
        
    def reload_filter_view(self, tag="artist", switch=False, use_path=False):    
        self.entry_box.entry.set_text("")
        self.back_button.set_no_show_all(True)
        self.back_button.hide()
        self.categorybar_status = tag
        self.filter_view.clear()
            
        if not use_path:    
            self.path_categorybar.set_index(-1)    
        
        _dict = self.get_infos_from_db(tag)
        keys = _dict.keys()
        keys.sort()
        items = []
        all_nb = len(self.__db_query.get_all_songs())
        items.append(IconItem(("deepin-all-songs", "deepin-all-songs", all_nb, tag)))

        for key in keys:
            value, nb = _dict[key] 
            items.append(IconItem((key, value, nb, tag)))
        self.filter_view.add_items(items)    
        
        if switch:
            self.switch_box(self.right_box, self.filter_scrolled_window)
            self.view_mode = ICON_VIEW_MODE
            if not use_path:
                self.change_combo_box_status(True)
            
    def get_infos_from_db(self, tag, values=None):
        genres = []
        artists = []
        extened = False
        return self.__db_query.get_info(tag, genres, artists, values, extened)
    
    def get_attr_infos_from_db(self, info_type="###ALL###", song_dir=None):
        return self.__db_query.get_attr_infos(info_type, song_dir)
    
    def change_combo_box_status(self, hide=False):    
        if not hide:
            self.path_combo_box.set_no_show_all(False)
            self.path_combo_box.show_all()
        else:    
            self.path_combo_box.hide_all()
            self.path_combo_box.set_no_show_all(True)
    
    def update_path_songs(self, key):
        self.back_button.set_no_show_all(True)
        self.back_button.hide()
        self.filter_categorybar.set_index(-1)        
        self.__current_path = key        
        self.change_combo_box_status()        
        
        if self.path_combo_box.get_combo_active():
            self.update_path_filter_view(self.path_combo_box.current_status)
        else:    
            songs = self.__db_query.get_attr_songs(key)
            self.update_songs_view(songs)
            
    def update_path_list_view(self):        
        self.back_button.set_no_show_all(True)
        self.back_button.hide()
        if self.__current_path == "###ALL###":
            songs = self.__db_query.get_all_songs()
        else:    
            songs = self.__db_query.get_attr_songs(self.__current_path)
        self.update_songs_view(songs)    
            
    def update_path_filter_view(self, name):
        self.back_button.set_no_show_all(True)
        self.back_button.hide()
        self.entry_box.entry.set_text("")
        
        self.filter_view.clear()
        if self.__current_path == "###ALL###":
            self.reload_filter_view(name, True, True)
        else:    
            attr_infos = self.get_attr_infos_from_db(name, self.__current_path)
            items = []
            for info in attr_infos:
                key, value, nb, tag = info
                items.append(IconItem((key, value, nb, tag)))
            self.filter_view.add_items(items)    
            
            if self.view_mode != ICON_VIEW_MODE:
                self.switch_box(self.right_box, self.filter_scrolled_window)
                self.view_mode = ICON_VIEW_MODE
                
    def reload_song_path(self):
        path_infos = self.get_attr_infos_from_db()
        if path_infos:
            self.path_categorybar.update_items([(name[0], self.update_path_songs, name[1]) for name in path_infos])
    
    def connect_to_db(self):    
        self.autoconnect(self.__db_query, "added", self.__added_song_cb)
        self.autoconnect(self.__db_query, "removed", self.__removed_song_cb)
        self.autoconnect(self.__db_query, "update-tag", self.__update_tag_view)
        self.autoconnect(self.__db_query, "full-update", self.__full_update)
        self.autoconnect(self.__db_query, "quick-update", self.__quick_update)
        self.__db_query.set_query("")                
        
    def __added_song_cb(self, db_query, songs):
        self.reload_song_path()        
        self.reload_flag = True

    def __removed_song_cb(self, db_query, songs):
        self.reload_song_path()        
        self.reload_flag = True
            
    def reload_browser(self,  obj, infos):
        if infos:
            self.reload_flag = True
            
    def interval_reload_browser(self):        
        if self.reload_flag and not self.__search_flag:
            self.reload_all_items()
            self.reload_flag = False    
        return True    
                    
    def reload_all_items(self):                
        if self.view_mode == ICON_VIEW_MODE:
            if self.path_categorybar.get_index() == -1:
                self.reload_filter_view(self.categorybar_status)
            else:    
                self.update_path_filter_view(self.path_combo_box.current_status)
        else:        
            if self.path_categorybar.get_index() == -1:
                if self.current_icon_item:
                    self.update_category_songs_view(self.current_icon_item)
            else:        
                if self.current_icon_item:
                    self.update_path_songs_view(self.current_icon_item)
    
    def __update_tag_view(self, db_query, tag, values):
        if values:
            self.reload_flag = True
    
    def __quick_update(self, db_query, songs):
        pass
        
    def __full_update(self, db_query):    
        self.reload_filter_view()
        self.reload_song_path()
    
    def __get_selected_songs(self, tag="artist"):
        artists = []
        albums = []
        genres = []
        
        if tag == "artist":
            artists = self.__selected_tag["artist"]
        elif tag == "album":    
            albums = self.__selected_tag["album"]
        elif tag == "genre":    
            genres = self.__selected_tag["genre"]
            
        return self.__db_query.get_songs(genres, artists, albums)    
    
    def __on_drag_data_get(self, widget, context, selection, info, timestamp):
        item = self.filter_view.highlight_item
        if not item:
            return 
        
        if item.key_name == "deepin-all-songs":
            songs = self.__db_query.get_all_songs()
        else:    
            del self.__selected_tag[item.tag]
            self.__selected_tag[item.tag] = [item.key_name]
            songs = self.__get_selected_songs(item.tag)
        if not songs:
            return 
        songs = list(songs)
        songs.sort()
        list_uris = list([ song.get("uri") for song in songs])
        selection.set("text/deepin-songs", 8, "\n".join(list_uris))
        selection.set_uris(list_uris)
    
    def __on_double_click_item(self, widget,  item, x, y):
        self.current_icon_item = item
        self.entry_box.entry.set_text("")
        self.back_button.set_no_show_all(False)
        self.back_button.show()
        if self.path_categorybar.get_index() == -1:
            self.update_category_songs_view(item)
        else:    
            self.update_path_songs_view(item)
        
    def update_category_songs_view(self, item):    
        if item.key_name == "deepin-all-songs":
            songs = self.__db_query.get_all_songs()
        else:    
            self.__selected_tag[item.tag] = [item.key_name]
            songs = self.__get_selected_songs(item.tag)
        self.update_songs_view(songs, item.tag)    
        
    def update_path_songs_view(self, item):    
        songs = self.__db_query.get_attr_songs(self.__current_path, item.tag, item.key_name)
        if songs:
            self.update_songs_view(songs, item.tag)
        
    def update_songs_view(self, items, sort_key="title"):    
        self.songs_view.clear()
        self.entry_box.entry.set_text("")
        self.songs_view.add_songs(items)
        self.songs_view.set_sort_keyword(sort_key)
        if self.view_mode != LIST_VIEW_MODE:
            self.switch_box(self.right_box, self.songs_scrolled_window)
            self.view_mode= LIST_VIEW_MODE
        
    def __on_single_click_item(self, widget, item, x, y):    
        if item.pointer_in_play_rect(x, y):
            if item.key_name == "deepin-all-songs":
                songs = self.__db_query.get_all_songs()
            else:    
                del self.__selected_tag[item.tag]
                self.__selected_tag[item.tag] = [item.key_name]
                songs = self.__get_selected_songs(item.tag)
            if not songs:
                return 
            songs = list(songs)
            songs.sort()
            if not songs:
                return 
            Dispatcher.play_and_add_song(songs)
        
        
    def __search_cb(self, widget, text):    
        if self.view_mode == LIST_VIEW_MODE:
            if not self.__search_flag:
                self.__song_cache_items = self.songs_view.items[:]
                
            # Clear song_view select status    
            self.songs_view.select_rows = []    
            if text != "":
                self.__search_flag = True
                results = filter(lambda item: text.lower().replace(" ", "") in item.get_song().get("search", ""), self.__song_cache_items)
                self.songs_view.items = results
                self.songs_view.update_item_index()
                self.songs_view.update_vadjustment()
            else:    
                self.__search_flag = False
                self.songs_view.items = self.__song_cache_items
                self.songs_view.update_item_index()
                self.songs_view.update_vadjustment()
            self.songs_view.queue_draw()    
        elif self.view_mode == ICON_VIEW_MODE:    
            if not self.__search_flag:
                self.__cover_cache_items = self.filter_view.items[:]
            if text != "":    
                self.__search_flag = True
                results = filter(lambda item: text.lower().replace(" ", "") in item.retrieve, self.__cover_cache_items)
                self.filter_view.items = results
            else:    
                self.__search_flag = False
                self.filter_view.items = self.__cover_cache_items
            self.filter_view.queue_draw()    
        
    def switch_box(self, parent, child):    
        switch_tab(parent, child)
    
class SimpleBrowser(Browser):    
    _type = "local"
    
    def __init__(self):
        Browser.__init__(self, DBQuery(self._type))
        
        if MediaDB.isloaded():
            self.__on_db_loaded(MediaDB)
        else:    
            self.autoconnect(MediaDB, "loaded", self.__on_db_loaded)
            
    def __on_db_loaded(self, db):        
        self.connect_to_db()
