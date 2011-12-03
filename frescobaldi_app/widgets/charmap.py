# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2011 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Provides a widget displaying characters from a font.

When a character is clicked, a signal is emitted.

"""

from __future__ import unicode_literals

import unicodedata

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class CharMap(QWidget):
    """A widget displaying a table of characters."""
    characterSelected = pyqtSignal(unicode)
    characterClicked = pyqtSignal(unicode)
    
    def __init__(self, parent=None):
        super(CharMap, self).__init__(parent)
        self.setBackgroundRole(QPalette.Base)
        self._showToolTips = True
        self._selected = -1
        self._column_count = 32
        self._square = 24
        self._range = (0, 0)
        self._font = QFont()
        
    def setRange(self, first, last):
        self._range = (first, last)
        self._selected = -1
        self.adjustSize()
        self.update()
    
    def range(self):
        return self._range
    
    def square(self):
        """Returns the width of one item (determined by font size)."""
        return self._square
    
    def select(self, charcode):
        """Selects the specifed character (int or str)."""
        if not isinstance(charcode, int):
            charcode = ord(charcode)
        if not self._range[0] <= charcode <= self._range[1]:
            charcode = -1
        if self._selected != charcode:
            self._selected = charcode
            self.characterSelected.emit(unichr(charcode))
            self.update()
    
    def character(self):
        """Returns the currently selected character, if any."""
        if self._selected != -1:
            return unichr(self._selected)
    
    def setDisplayFont(self, font):
        self._font.setFamily(font.family())
        self.update()
    
    def displayFont(self):
        return QFont(self._font)
    
    def setDisplayFontSize(self, size):
        self._font.setPointSize(size)
        self._square = max(24, QFontMetrics(self._font).xHeight() * 3)
        self.adjustSize()
        self.update()
    
    def setColumnCount(self, count):
        """Sets how many columns should be used."""
        count = max(1, count)
        self._column_count = count
        self.adjustSize()
        self.update()
    
    def columnCount(self):
        return self._column_count
        
    def sizeHint(self):
        return self.sizeForColumnCount(self._column_count)

    def paintEvent(self, ev):
        rect = ev.rect()
        s = self._square
        rows = range(rect.top() / s, rect.bottom() / s + 1)
        cols = range(rect.left() / s, rect.right() / s + 1)
        
        painter = QPainter(self)
        painter.setPen(QPen(self.palette().color(QPalette.Window)))
        painter.setFont(self._font)
        metrics = QFontMetrics(self._font)
        # draw squares
        for row in rows:
            for col in cols:
                painter.drawRect(col * s, row * s, s - 1, s - 1)
        # draw selection box?
        if self._range[0] <= self._selected <= self._range[1]:
            row, col = divmod(self._selected - self._range[0], self._column_count)
            color = self.palette().color(QPalette.Highlight)
            color.setAlpha(96)
            painter.fillRect(col * s, row * s, s - 1, s - 1, color)
            color.setAlpha(255)
            painter.setPen(QPen(color))
            painter.drawRect(col * s, row * s, s - 1, s - 1)
        # draw the characters
        painter.setPen(QPen(self.palette().text()))
        for row in rows:
            for col in cols:
                char = row * self._column_count + col + self._range[0]
                if char > self._range[1]:
                    break
                t = unichr(char)
                painter.setClipRect(col * s, row * s, s, s)
                x = col * s + s / 2 - metrics.width(t) / 2
                y = row * s + 4 + metrics.ascent()
                painter.drawText(x, y, t)
            else:
                continue
            break
    
    def sizeForColumnCount(self, count):
        """Returns the size the widget would have in a certain column count.
        
        This can be used in e.g. a resizable scroll area.
        
        """
        first, last = self._range
        rows = ((last - first) // count) + 1
        return QSize(count, rows) * self._square

    def columnCountForWidth(self, width):
        """Returns the number of columns that would fit into the given width."""
        return width // self._square

    def mousePressEvent(self, ev):
        charcode = self.charcodeAt(ev.pos())
        if charcode != -1:
            self.select(charcode)
            if ev.button() != Qt.RightButton:
                self.characterClicked.emit(unichr(charcode))
    
    def charcodeRect(self, charcode):
        """Returns the rectangular box around the given charcode, if any."""
        if self._range[0] <= charcode <= self._range[1]:
            row, col = divmod(charcode - self._range[0], self._column_count)
            s = self._square
            return QRect(col * s, row * s, s, s)
        
    def charcodeAt(self, position):
        row = position.y() // self._square
        col = position.x() // self._square
        if col <= self._column_count:
            charcode = self._range[0] + row * self._column_count + col
            if charcode <= self._range[1]:
                return charcode
        return -1

    def event(self, ev):
        if ev.type() == QEvent.ToolTip:
            c = self.charcodeAt(ev.pos())
            self.toolTipEvent(ev.globalPos(), c)
            ev.accept()
            return True
        else:
            return super(CharMap, self).event(ev)
    
    def toolTipEvent(self, position, charcode):
        if self._showToolTips:
            try:
                text = unicodedata.name(unichr(charcode))
            except ValueError:
                return
            QToolTip.showText(position, text, self, self.charcodeRect(charcode))
    
    def setShowToolTips(self, enabled):
        self._showToolTips = bool(enabled)
    
    def showToolTips(self):
        return self._showToolTips


