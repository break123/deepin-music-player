#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Deepin, Inc.
#               2011 Hou Shaohui
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

from dtk.ui.window import Window
from dtk.ui.titlebar import Titlebar
from dtk.ui.utils import move_window
from dtk.ui.entry import InputEntry
from dtk.ui.button import ImageButton
from dtk.ui.draw import draw_pixbuf, draw_text
from widget.skin import app_theme
from widget.ui_utils import draw_alpha_mask
from helper import Dispatcher

class NormalWindow(Window):
    
    def __init__(self):
        super(NormalWindow, self).__init__(True)
        
        # Init Window
        self.set_position(gtk.WIN_POS_CENTER)
        self.titlebar = Titlebar(["close"])
        self.titlebar.close_button.connect_after("clicked", self.hide_window)
        self.titlebar.drag_box.connect('button-press-event', lambda w, e: move_window(w, e, self.window))
        
        main_align = gtk.Alignment()
        main_align.set(0.0, 0.0, 1.0, 1.0)
        main_align.set_padding(5, 10, 10, 10)
        self.main_box = gtk.VBox(spacing=5)
        main_align.add(self.main_box)
        self.window_frame.pack_start(self.titlebar, False, False)
        self.window_frame.pack_start(main_align, True, True)
        
    def show_window(self):    
        self.show_all()
        print ""
            
    def hide_window(self, widget):        
        self.hide_all()
        
        
class SearchEntry(InputEntry):
    
    def __init__(self, *args, **kwargs):


        entry_button = ImageButton(
            app_theme.get_pixbuf("toolbar/search_normal.png"),
            app_theme.get_pixbuf("toolbar/search_hover.png"),
            app_theme.get_pixbuf("toolbar/search_press.png")
            )
        super(SearchEntry, self).__init__(action_button=entry_button, *args, **kwargs)        
        
        self.action_button = entry_button
        self.set_size(250, 24)
        
gobject.type_register(SearchEntry)        

        
    
class ProgressBox(gtk.VBox):
    
    def __init__(self, scalebar):
        super(ProgressBox, self).__init__()
        scalebar_align = gtk.Alignment()
        scalebar_align.set_padding(0, 0, 2, 2)
        scalebar_align.set(0, 0, 1, 1)
        scalebar_align.add(scalebar)
        
        self.draw_right_mask_flag = True
        self.set_size_request(-1, 17)
        self.rect_left_list = [
            (98, "layoutLeft"),
            (220, "layoutMiddle")
            ]
        
        self.pack_start(scalebar_align, False, True)
        self.connect("expose-event", self.draw_mask)
        Dispatcher.connect("window-mode", self.window_mode_changed)
        
    def window_mode_changed(self, obj, status):    
        if status == "simple":
            self.draw_right_mask_flag = False
        else:    
            self.draw_right_mask_flag = True
        
    def draw_mask(self, widget, event):    
        cr = widget.window.cairo_create()
        rect = widget.allocation
        start_x = rect.x + 2
        start_y = rect.y + 8

        for size, color_info in self.rect_left_list:
            draw_alpha_mask(cr, start_x, start_y, size, rect.height - 8, color_info)
            start_x += size
        if self.draw_right_mask_flag:    
            draw_alpha_mask(cr, start_x, start_y, 140, rect.height - 8, "layoutRight")
            start_x += 140
            last_width = rect.width - (start_x - rect.x)    
            draw_alpha_mask(cr, start_x, start_y, last_width - 2, rect.height - 8, "layoutLast")
        return False

    
class ComplexButton(gtk.Button):    
    
    def __init__(self, bg_group, icon, content, left_padding=20, label_padding=10, font_size=9):
        super(ComplexButton, self).__init__()
        
        # Init.
        self.normal_bg, self.hover_bg, self.press_bg = bg_group
        self.button_icon = icon
        self.content = content
        self.font_size = font_size
        self.left_padding = left_padding
        self.label_padding = label_padding
        
        # Set size.
        self.set_button_size()
        self.connect("expose-event", self.expose_button)
        
    def set_button_size(self):    
        request_width  = self.normal_bg.get_pixbuf().get_width()
        request_height = self.normal_bg.get_pixbuf().get_height()
        self.set_size_request(request_width, request_height)
        
    def expose_button(self, widget, event):    
        
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        if widget.state == gtk.STATE_NORMAL:
            bg_pixbuf = self.normal_bg.get_pixbuf()
        elif widget.state == gtk.STATE_PRELIGHT:    
            bg_pixbuf = self.hover_bg.get_pixbuf()
        elif widget.state == gtk.STATE_ACTIVE:    
            bg_pixbuf = self.press_bg.get_pixbuf()
            
        icon_pixbuf = self.button_icon.get_pixbuf()    
            
        icon_y = rect.y + (rect.height - icon_pixbuf.get_height()) / 2    
        
        # Draw bg.
        draw_pixbuf(cr, bg_pixbuf, rect.x, rect.y)
        
        # Draw icon.
        draw_pixbuf(cr, icon_pixbuf, rect.x + self.left_padding, icon_y)
        
        # Draw label.
        draw_text(cr, self.content, rect.x + self.left_padding + self.label_padding + icon_pixbuf.get_width(),
                  rect.y, rect.width - self.left_padding - self.label_padding - icon_pixbuf.get_width(), rect.height,
                  self.font_size, text_color="#FFFFFF")
        
        return True

gobject.type_register(ComplexButton)    