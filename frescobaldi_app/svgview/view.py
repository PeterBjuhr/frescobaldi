# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2014 by Wilbert Berendsen
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
The SVG view (a QWebView displaying a SVG file).

Interaction between the SVG object and Python is done via a JavaScript bridge
that runs inside the displayed SVG file.

"""

from __future__ import unicode_literals
from __future__ import absolute_import

import os
import sys

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtWebKit

import app
import util
import textedit
import textformats
import pointandclick
import scratchdir


from . import __path__


def getJsScript(filename):
    """fetch the js file"""
    directory = __path__[0]
    with open(os.path.join(directory, filename), 'r') as fileObject:
        jsValue = fileObject.read()
	return jsValue


class View(QtWebKit.QWebView):
    zoomFactorChanged = QtCore.pyqtSignal(float)
    objectDragged = QtCore.pyqtSignal(float, float)
    objectDragging = QtCore.pyqtSignal(float, float)
    objectStartDragging = QtCore.pyqtSignal(float, float)

    cursor = QtCore.pyqtSignal(QtGui.QTextCursor)
    selectedObject = QtCore.pyqtSignal(str)
    selectedUrl = QtCore.pyqtSignal(QtGui.QTextCursor)
    
    def __init__(self, parent):
        super(View, self).__init__(parent)
        self._highlightFormat = QtGui.QTextCharFormat()
        self.jslink = JSLink(self)
        self.loadFinished.connect(self.svgLoaded)
        app.settingsChanged.connect(self.readSettings)
        self.readSettings()
    
    def mainwindow(self):
        return self.parent().mainwindow()
        
    def currentSVG(self):
        return self.parent().getCurrent()

    def document(self, filename, load=False):
        """Get the document with the specified filename.
        
        If load is True, the document is loaded if it wasn't already.
        Also takes scratchdir into account for unnamed or non-local documents.
        
        """
        for d in app.documents:
            s = scratchdir.scratchdir(d)
            if (s.directory() and util.equal_paths(filename, s.path())
                or d.url().toLocalFile() == filename):
                return d
        if load:
            doc = app.openUrl(QtCore.QUrl.fromLocalFile(filename))
            
            return doc
        

    def svgLoaded(self):
        if not self.url().isEmpty():
            frame = self.page().mainFrame()
            frame.addToJavaScriptWindowObject("pyLinks", self.jslink)
            
            jsCode = ""
            jsCode = getJsScript('scripts/jquery-2.1.0.js')
            #jsCode = getJsScript('scripts/jquery-1.11.0.js')
            jsCode += getJsScript('pointandclick.js')
            jsCode += getJsScript('editsvg.js') # Remove this for stable releases
            
            frame.evaluateJavaScript(jsCode)
            
#            frame.evaluateJavaScript("test = $('svg')")
#            frame.evaluateJavaScript("pyLinks.pyLog(test.toString())")
            
#            frame.evaluateJavaScript(getJsScript('scripts/jquery-2.1.0.js'))
#            print frame.evaluateJavaScript("var test = $('svg'); return test;")
#            print "test executed"
#            frame.evaluateJavaScript(getJsScript('pointandclick.js'))
#            print "evaluate editsvg"
#            frame.evaluateJavaScript("test = 4")
#            frame.evaluateJavaScript(getJsScript('scripts/jquery-2.1.0.js') + "\n" +
#                                     getJsScript('editsvg.js'))
#            frame.evaluateJavaScript(getJsScript('editsvg.js')) #remove this for stable releases
            print "have evaluated editsvg"
            
    def evalSave(self):
        frame = self.page().mainFrame()
        # to enable useful save of SVG edits to file uncomment the line below
        # frame.evaluateJavaScript(getJsScript('cleansvg.js'))
        frame.evaluateJavaScript(getJsScript('savesvg.js'))
    
    def clear(self):
        """Empty the View."""
        self.load(QtCore.QUrl())
    
    def dragElement(self, url):
        t = textedit.link(url)
        # Only process textedit links
        if not t:
            return False
        doc = self.document(t.filename, True)
        if doc:
            cursor = QtGui.QTextCursor(doc)
            b = doc.findBlockByNumber(t.line - 1)
            p = b.position() + t.column
            cursor.setPosition(p)
        self.emitCursor(cursor)
    
    def doObjectDragged(self, offsX, offsY):
        """announce extra-offsets an element has been dragged to"""
        self.objectDragged.emit(offsX, offsY)
    
    def doObjectDragging(self, offsX, offsY):
        """announce extra-offsets while dragging an element"""
        self.objectDragging.emit(offsX, offsY)    

    def doObjectStartDragging(self, offsX, offsY):
        """announce extra-offsets when starting to drag an element"""
        self.objectStartDragging.emit(offsX, offsY)

    def doTextEdit(self, url, setCursor = False):
        """Process a textedit link and either highlight
           the corresponding source code or set the 
           cursor to it.
        """
        t = textedit.link(url)
        # Only process textedit links
        if not t:
            return False
        doc = self.document(t.filename, setCursor)
        if doc:
            cursor = QtGui.QTextCursor(doc)
            b = doc.findBlockByNumber(t.line - 1)
            p = b.position() + t.column
            cursor.setPosition(p)
            cursors = pointandclick.positions(cursor)
            # Do highlighting if the document is active
            if cursors and doc == self.mainwindow().currentDocument():
                import viewhighlighter
                view = self.mainwindow().currentView()
                viewhighlighter.highlighter(view).highlight(self._highlightFormat, cursors, 2, 0)
            # set the cursor and bring the document to front
            if setCursor:
                mainwindow = self.mainwindow()
                mainwindow.setTextCursor(cursor)
                import widgets.blink
                widgets.blink.Blinker.blink_cursor(mainwindow.currentView())
                self.mainwindow().setCurrentDocument(doc)
                mainwindow.activateWindow()
                mainwindow.currentView().setFocus()
        return True
    
    def emitCursor(self, cursor):
        self.cursor.emit(cursor)    
    
    def readSettings(self):
        """Reads the settings from the user's preferences."""
        color = textformats.formatData('editor').baseColors['selectionbackground']
        color.setAlpha(128)
        self._highlightFormat.setBackground(color)
    
    def saveSVG(self, svg_string):
        """Pass string from JavaScript and save to current SVG page."""
        f = open(self.currentSVG(),'w')
        f.write(svg_string.encode('utf8'))
        f.close()

    def unHighlight(self):
        import viewhighlighter
        view = self.mainwindow().currentView()
        viewhighlighter.highlighter(view).clear(self._highlightFormat)

    def zoomIn(self):
        self.setZoomFactor(self.zoomFactor() * 1.1)
        
    def zoomOut(self):
        self.setZoomFactor(self.zoomFactor() / 1.1)
        
    def zoomOriginal(self):
        self.setZoomFactor(1.0)
    
    def setZoomFactor(self, value):
        changed = self.zoomFactor() != value
        super(View, self).setZoomFactor(value)
        if changed:
            self.zoomFactorChanged.emit(self.zoomFactor())


class JSLink(QtCore.QObject):
    """functions to be called from JavaScript
    
    using addToJavaScriptWindowObject
    
    """
    def __init__(self, view):
        super(JSLink, self).__init__()
        self.view = view

    @QtCore.pyqtSlot(str)
    def click(self, url):
        """set cursor in source by clicked textedit link""" 
        if not self.view.doTextEdit(url, True):
            import helpers
            helpers.openUrl(QtCore.QUrl(url))

    @QtCore.pyqtSlot(float, float)
    def dragged(self, offX, offY):
        """announce extra-offsets an element has been dragged to"""
        self.view.doObjectDragged(offX, offY)
        
    @QtCore.pyqtSlot(str)
    def draggedObject(self, JSON_string):
        # leave the following commented code as an idea how to proceed from here
        #print "Dragged object JSON representation:"
        #import json
        #js = json.JSONDecoder()
        #print js.decode(JSON_string)
        pass
        
    @QtCore.pyqtSlot(str)
    def dragElement(self, url):
        self.view.dragElement(url)

    @QtCore.pyqtSlot(float, float)
    def dragging(self, offX, offY):
        """announce extra-offsets while dragging an element"""
        self.view.doObjectDragging(offX, offY)
        
    @QtCore.pyqtSlot(str)	    
    def hover(self, url):
        """actions when user set mouse over link"""
        self.view.doTextEdit(url, False)
    
    @QtCore.pyqtSlot(str)	    
    def leave(self, url):
        """actions when user moves mouse off link"""
        self.view.unHighlight()
        
    @QtCore.pyqtSlot(str)	    
    def pyLog(self, txt):
        """Temporary function. Print to Python console."""
        print(txt)
    
    @QtCore.pyqtSlot(str)	    
    def saveSVG(self, svg_string):
        """Pass string from JavaScript and save to current SVG page."""
        self.view.saveSVG(svg_string)

    @QtCore.pyqtSlot(float, float)
    def startDragging(self, offX, offY):
        """announce extra-offsets when starting to drag an element"""
        self.view.doObjectStartDragging(offX, offY)
