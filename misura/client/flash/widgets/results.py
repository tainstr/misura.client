#!/usr/bin/python
# -*- coding: utf-8 -*-
"""FlashLine compatibility text results tables"""
import functools
import codecs
import sys
from misura.client import _, iutils
from PyQt4 import QtGui, QtCore
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.csutil import isWindows

from misura.client.flash.flashline.convert import result_handles
from misura.client.flash.plugin import model_plugins

#TODO: look for fixed length fields formatting!

# .all format
header="""Title:     {title:9s}
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}   
Thickness: {thickness:1.4f} (cm) 

Filter Type  20    Points 0   Low 0   Avg 5 

Seg Temp   t1/2   Parker  Koski  Heckman  Cowan 5 Cowan 10 C&T R1 C&T R2  C&T R3 Degiovanni 2/3 1/2 1/3 
"""

header_csv="""Title:     {title:9s}
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}   
Thickness: {thickness:1.4f} (cm) 

Filter Type  20    Points 0   Low 0   Avg 5 

Seg, Temp,   t1/2,   Parker,  Koski,  Heckman,  Cowan 5, Cowan 10, C&T R1, C&T R2,  C&T R3, Degiovanni, "2/3", "1/2", "1/3" 
"""

line = "  {:4d}  "
line += "{:>2.4f} "*12
line += '\n'

segment_line = "{:2d}" + line
line = "  " + line

diff_keys = ['halftime', 'parker', 'koski', 'heckman', 'cowan5', 'cowan10', 'clarkTaylor1',
             'clarkTaylor2', 'clarkTaylor3', 'degiovanni']

#TODO: find out what 2/3 1/2 1/3 are!

def get_header(h, proxy, **kw):
    m = proxy.parent().measure
    fields = {'title': m['name'],
                        'fileID': proxy['fileID'],
                        'testNumber': m['id'],
                        'thickness': proxy['thickness'],
                        'oper': m['operator'], 
                        'diameter': proxy['diameter']}
    fields.update(kw)
    tab = h.format(**fields)
    return tab

def re_base(label):
    v = label[1:].split('_')
    v[0] = int(v[0])*1000
    # Multiple segments
    if len(v)==2:
        v[0]+=int(v[1])
    return v[0]
        
def from_based(v):
    v = divmod(v, 1000)
    lbl = 'T{}'.format(v[0])
    if v[1]:
       lbl += '_{}'.format(v[1]) 
    return lbl

def iter_numbered(proxy):
    # iterate segments
    segs = proxy.children.keys()
    d = {re_base(s):proxy.child(s) for s in segs}
    k = sorted(d)
    for i, j in enumerate(k):
        yield i, d[j]

def build_all_table(proxy, csv=False):
    h = header_csv if csv else header
    tab = get_header(h, proxy)
    for Ti, seg in iter_numbered(proxy):
        tab += '\n'
        for n, sh in iter_numbered(seg):
            vals = [sh[k] for k in diff_keys]
            # Missing 2/3, 1/2, 2/3
            vals += [0,0,0]
            T = int(round(sh['temperature'], 0))
            if n==0:
                ln = segment_line.format(Ti+1, T, *vals)
            else:
                ln = line.format(T, *vals)
            if csv:
                ln = ln.replace('  ', ' ').replace('  ', ' ')[1:].replace(' ', ', ')
            tab += ln
    tab += '\n'
    return tab

# .rst format
dheader = u"""Title:     {title:9s} 
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}        15.14  
Thickness: {thickness:1.4f} (cm) {diameter:1.4f} (cm)   {diffusivity} ({unit}) 

Segment Temperature   Avg     Shots 
            (C)     ({unit})  ({unit}) 
"""

dheader_csv = u"""Title:     {title:9s} 
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}        15.14  
Thickness: {thickness:1.4f} (cm) {diameter:1.4f} (cm)   {diffusivity} ({unit}) 

Segment, Temperature (C),  Avg ({unit}), Shots ({unit})
"""

#   1        383Q     0.4322  0.4297 0.4337 0.4332 
dline = "{:4d}     {:4d}{}     {:1.4f}  "

# With reference
rheader = u"""Title:     {title:9s} 
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}        15.14  
Thickness: {thickness:1.4f} (cm) {diameter:1.4f} (cm)   {diffusivity} ({unit}) 

Segment Temperature   Avg       Ref    Error  Shots 
            (C)         ({unit})       (%)    ({unit}) 
"""
rheader_csv = u"""Title:     {title:9s} 
File ID:   {fileID:9s} Test Number: {testNumber}   {oper}        15.14  
Thickness: {thickness:1.4f} (cm) {diameter:1.4f} (cm)   {diffusivity} ({unit}) 

Segment, Temperature (C),  Avg ({unit}),  Ref ({unit}), Error (%),  Shots ({unit})              
"""

#   1        383Q     0.4322  0.4297 0.4337 0.4332 
rline = "{:4d}     {:4d}{}     {:1.4f}"

model_tables = {'jg2d_diffusivity': 'gembarovic',
                'inpl_diffusivity': 'inplane',
                'ml2_diffusivity': 'twolayers',
                'ml3_diffusivity': 'threelayers',
    }

def build_single_table(proxy, diffusivity, reference=False, csv=False):
    unit = u'cm²/s'
    if diffusivity == 'halftime':
        unit = 's'
    reftab = False
    if reference:
        refname = model_tables.get(diffusivity, diffusivity+'s')
        reftab = proxy[refname][1:]
    if not reftab:
        reference = False
    if csv:
        h = rheader_csv if reference else dheader_csv
    else:
        h = rheader if reference else dheader
    tab = get_header(h, proxy, diffusivity=diffusivity, unit=unit)
    logging.debug('build_single_table', diffusivity, unit, tab)
    index = []
    ln = ''
    sep = ', ' if csv else ' '
    def app(obj):
        index.append((len(tab)+len(ln), obj['fullpath'][:-1]))

    for Ti, seg in iter_numbered(proxy):
        ln = ''
        app(seg)
        val = 0. if diffusivity not in seg else seg[diffusivity]
        ln = dline.format(Ti+1, int(round(seg['temperature'], 0)), '', val)
        ln += sep
        if reftab:
            row = reftab[Ti]
            ln += "  {:1.4f}{}  {:1.1f}    ".format(row[-1], sep, row[-2])
        app(seg)
        for n, sh in iter_numbered(seg):
            app(sh)
            val = 0. if diffusivity not in sh else sh[diffusivity]
            ln += '{:1.4f}{}'.format(val, sep)
            app(sh)
        if csv:
            ln = ln.replace('    ', sep)
        tab += ln + '\n'
    tab += '\n'
    return tab, index


def find_index(index, target):
    found = None
    for i, (start, path) in enumerate(index):
        if target<start:
            break
        found = i
    return found


class ResultsTextArea(QtGui.QTextEdit):
    mouseOverChar = QtCore.pyqtSignal(int)
    user_selecting = False
    timer = False
    
    def mouseMoveEvent(self, event):
        if not self.user_selecting:
            cur = self.cursorForPosition(event.pos()).position()
            if cur:
                self.mouseOverChar.emit(cur)
        return super(ResultsTextArea, self).mouseMoveEvent(event)
    
    def mousePressEvent(self, ev):
        if ev.button()==QtCore.Qt.LeftButton:
            self.user_selecting = True
        return super(self.__class__, self).mousePressEvent(ev)
    
    def restart_tracking(self):
        self.user_selecting = False
        self.timer = False
    
    def mouseReleaseEvent(self, ev):
        if ev.button()==QtCore.Qt.LeftButton:
            if self.user_selecting and not self.timer:
                QtCore.QTimer.singleShot(1000, self.restart_tracking)
                self.timer = True
        return super(self.__class__, self).mouseReleaseEvent(ev)
    
    def mouseDoubleClickEvent(self, ev):
        if ev.button()==QtCore.Qt.LeftButton:
            self.restart_tracking()
        return super(self.__class__, self).mouseDoubleClickEvent(ev)
    
        

class FlashLineResultsTable(QtGui.QWidget):
    tab = ''
    tab_csv = ''
    ext = '.rst'
    index = False
    def __init__(self, node, proxy, nav= None, parent=None):
        super(QtGui.QWidget, self).__init__(parent=parent)
        self.node = node
        self.nav = nav
        self.proxy = proxy
        self.setWindowTitle('{}: {}'.format(self.proxy['devpath'], self.proxy['name']))
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.txt = ResultsTextArea()
        self.txt.setMouseTracking(True)
        self.txt.mouseOverChar.connect(self.update_tooltip)
        self.txt.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.txt.customContextMenuRequested.connect(self.show_menu)
        self.txt.setReadOnly(True)
        f = QtGui.QFont("Courier")
        f.setPointSize(10)
        f.setStyleHint(QtGui.QFont.Monospace)
        self.txt.setFont(f)
        self.toolbar = QtGui.QToolBar(self)
        self.act_update = self.toolbar.addAction(_('Update'), self.update)
        self.toolbar.addAction(iutils.theme_icon('media-floppy'), 
                               _('Export'), 
                               self.export)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.txt)
        self.update()
        self.update_tooltip(-1)
        
        
    def update_tooltip(self, cur):
        if self.index:
            c = self.txt.textCursor()
            i  = find_index(self.index, cur)
            if i is None:
                self.txt.setToolTip(_('Right-click on a segment or shot for shortcuts'))
                c.clearSelection()
            else:
                self.txt.setToolTip(self.index[i][1])
                
                s = self.index[i][0]
                c.setPosition(s, QtGui.QTextCursor.MoveAnchor)
                if i==len(self.index)-1:
                    c.clearSelection()
                else:
                    e = self.index[i+1][0]-1
                    c.setPosition(e, QtGui.QTextCursor.KeepAnchor)
            self.txt.setTextCursor(c)
        
    def show_menu(self, pos):
        menu  = self.txt.createStandardContextMenu()
        if not self.index or not self.nav:
            menu.exec_(self.txt.mapToGlobal(pos))
            return False
        
        
        cur = self.txt.cursorForPosition(pos).position()
        i  = find_index(self.index, cur)
        if i is not None:
            path  = self.index[i][1]
            menu.insertAction(menu.actions()[0], QtGui.QAction(path, self))
            menu.addSeparator()
            navmenu = QtGui.QMenu()
            path = self.node.path.split(':')[0]+':'+path[1:]
            node = self.nav.model().tree.traverse(path)
            self.nav.selectionModel().clear()
            self.nav.expand_node_path(node, select=True)
            
            self.nav.build_recursive_menu(node, menu)
            for a in navmenu.actions():
                a.setParent(menu)
                menu.addAction(a)
                
            
            
            # Add Navigator entries for segment or shot...
        menu.exec_(self.txt.mapToGlobal(pos))
        return True
        
    def export(self):
        dfilter = "FlashLine Results (*{});; Comma separed values (*.csv)".format(self.ext)
        name = QtGui.QFileDialog.getSaveFileName(parent=self, 
                                          caption=_('Save as FlashLine {}'.format(self.ext)),
                                          filter = dfilter)
        if not name:
            logging.debug('export aborted', name)
            return False
        logging.debug('exporting', name)
        ext = name[-4:].lower() 
        if ext in ('.csv', '.xls'):
            tab = self.tab_csv
        elif ext == '.rst':
            tab = self.tab
        else:
            name+=self.ext
        if isWindows:
            cod = 'WINDOWS-1252'
        else:
            cod = 'utf-8'
        codecs.open(name, 'w', cod).write(tab)
        return True
    
    def update(self, diffusivity=False):
        pass
        
        
    
class ResultsAll(FlashLineResultsTable):
    ext = '.all'
    
    def update(self, *a):
        super(ResultsAll, self).update(*a)
        self.tab = build_all_table(self.proxy, csv=False)
        self.tab_csv = build_all_table(self.proxy, csv=True)
        self.txt.setPlainText(self.tab)
        

                    
class ResultsSingle(FlashLineResultsTable):
    diffusivity = 'clarkTaylor'
    ext = '.rst'
    act_ref = False
    def __init__(self, node, proxy, diffusivity='clarkTaylor', nav=None, parent=None):
        self.diffusivity = diffusivity        
        super(ResultsSingle, self).__init__(node, proxy, nav, parent=None)
        
        self.menu_diff = QtGui.QMenu()
        self.menu_diff.aboutToShow.connect(self.update_diffusivities_menu)
        self.act_update.setMenu(self.menu_diff)
        
        self.act_ref = self.toolbar.addAction(_('Reference'), self.update)
        self.act_ref.setCheckable(True)
        self.update()
        
    @staticmethod
    def get_model_diffusivity_name(section_name):
        if not section_name:
            return False
        for model in model_plugins:
            if section_name==model._params_class.section_name:
                return model._params_class.section+'_diffusivity'
        return False
        
        
    def update_diffusivities_menu(self):
        self.menu_diff.clear()
        fit = self.proxy.root.flash.measure.gete('fitting')
        models = fit['current'] or fit['values']
        for model in model_plugins:
            if model._params_class.section_name not in models:
                continue
            sec = model._params_class.section_name
            diff = model._params_class.section+'_diffusivity'
            self.menu_diff.addAction(iutils.theme_icon('flash_'+sec), sec, 
                                     functools.partial(self.update, diffusivity=diff, section=sec))
            if diff == self.diffusivity:
                self.act_update.setText(sec)
        for h in result_handles:
            self.menu_diff.addAction(h[1], functools.partial(self.update, diffusivity=h[0], section=h[1]))
            if h[0]==self.diffusivity:
                self.act_update.setText(h[1])
            
    def ref_update(self, *a):
        self.update()
        
        
    def update(self, diffusivity=False, section=False):
        if not self.act_ref:
            return 
        super(ResultsSingle, self).update()
        if diffusivity:
            self.diffusivity = diffusivity
        v = 'references' in self.proxy
        v *= diffusivity!='halftime'
        self.act_ref.setVisible(v)
        if not v:
            self.act_ref.setChecked(v)
        else:
            v = self.act_ref.isChecked()
        
        sec = section if section else self.diffusivity
        self.tab, self.index = build_single_table(self.proxy, self.diffusivity, v, csv=False)
        self.tab_csv, foo = build_single_table(self.proxy, self.diffusivity, v, csv=True)
        self.txt.setPlainText(self.tab)
        self.setWindowTitle('{}: {}, {}'.format(self.proxy['devpath'], self.proxy['name'], self.diffusivity))
        self.update_diffusivities_menu()

        
