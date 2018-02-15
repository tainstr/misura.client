#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import functools
from PyQt4 import QtGui, QtCore
from ...canon import csutil
from misura.client import _
import os

def meta_lbl(opt):
    opt = opt.replace('summary', '').replace('//', '/').split('/')[-1]
    if opt.endswith(':t'):
        return 'Time'
    return opt

class MiniImage(QtGui.QWidget):

    """Image from test chronology"""
    saveDir = False
    decoder = False
    idx = 0
    """Current data index"""
    doc_idx = 0
    """Current document data index"""
    t = 0
    """Current data time"""
    meta = {'T': None}
    """Current metadata for label"""
    metaChanged = QtCore.pyqtSignal(object)
    """Emitted when meta label changes keys. Emits new list of keys."""
    zoomChanged = QtCore.pyqtSignal(float)

    def __init__(self, doc, datapath=False, curWidth=100, maxWidth=600, minWidth=15, slider=False, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.lay = QtGui.QVBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.setLayout(self.lay)
        self.setAcceptDrops(True)
        # Proper image label
        self.lbl_img = QtGui.QLabel(parent=self)
        self.lbl_img.setPixmap(QtGui.QPixmap())
        self.lay.addWidget(self.lbl_img)
        # Optional Metadata label
        self.lbl_info = QtGui.QLabel(parent=self)
        self.lay.addWidget(self.lbl_info)
        self.lbl_info.hide()
        logging.debug('datapath', datapath)
        Tpath = '/'.join(datapath.split('/')[:-1])+'/T'
        self.meta = {Tpath: None}
        self.doc = doc
        self.decoder = doc.decoders.get(datapath, False)
        self.img = QtGui.QImage()
        self.curWidth = curWidth
        self.defaultWidth = curWidth
        self.maxWidth = maxWidth
        self.minWidth = minWidth
        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.menu.addAction(_('Next'), self.next)
        self.menu.addAction(_('Previous'), self.prev)
        self.menu.addAction(_('Save'), self.save_frame)
        self.menu.addAction(_('To Clipboard'), self.copy_to_clipboard)
        self.meta_menu = self.menu.addMenu(_('Labels'))
        # Slider for image navigation
        self.slider = QtGui.QScrollBar(parent=self)
        if self.decoder:
            self.slider.setMaximum(len(self.decoder))
        self.slider.setMinimum(0)
        self.slider.setTracking(False)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.valueChanged.connect(self.set_idx)
        if not slider:
            self.slider.hide()
        if self.decoder:
            self.connect(
                self.decoder, QtCore.SIGNAL('cached(int)'), self.cached)

    def save_frame(self):
        """Save current frame"""
        if not self.saveDir:
            self.saveDir = QtGui.QFileDialog.getExistingDirectory(
                self, "Images destination folder", "/tmp")
        saved_file = os.path.join(self.saveDir, str(self.idx)) + '.png'
        self.img.save(saved_file, 'PNG', 25)
        return saved_file
    
    def copy_to_clipboard(self):
        QtGui.qApp.clipboard().setImage(self.img)

    def empty(self):
        """Set the image as empty"""
        self.lbl_img.setPixmap(QtGui.QPixmap())
        self.lbl_info.hide()

    def next(self):
        self.set_idx(self.idx + 1)

    def prev(self):
        self.set_idx(self.idx - 1)

    def cached(self, idx):
        if idx == self.idx:
            self.set_idx()

    def set_idx(self, idx=-1):
        if not self.decoder:
            logging.debug('set_idx no decoder')
            return False
        if idx < 0:
            idx = self.idx
        logging.debug('set_idx', idx)
        self.idx = idx
        ln = len(self.decoder)
        self.slider.setMaximum(ln)
        if self.idx >= ln:
            logging.debug('Index out of bounds ({} of {}): setting empty image. '.format(self.idx, ln))
            self.empty()
            return False
        logging.debug('getting idx from decoder',
                      self.decoder.datapath, self.decoder.ext, idx)
        img = self.decoder.get(idx)

        self.slider.valueChanged.disconnect(self.set_idx)
        logging.debug('GOT IMG', repr(img))
        if img:
            self.t, self.img = img
            self.emit(QtCore.SIGNAL('set_time(float)'), self.t)
        self.zoom(self.curWidth)

        self.slider.setValue(self.idx)
        logging.debug('sliderValue', self.slider.value())
        self.emit(QtCore.SIGNAL('changedIdx()'))
        self.emit(QtCore.SIGNAL('changedIdx(int)'), self.idx)
        self.slider.valueChanged.connect(self.set_idx)
#         self.setToolTip(metaToText(self.meta,self.decoder.visibleOptions))
        self.update_info()
        return True

    def set_time(self, t):
        # TODO: implement this in order to be introduce time stepping in slider.
        # This will in turn enable value stepping.
        self.update_info()

    @property
    def base_dataset_path(self):
        # Base dataset path name
        p = self.decoder.datapath.split('/')
        # Remove last name (/profile or /frame)
        p.pop(-1)
        p = '/'.join(p)
        return p

    def update_info(self):
        """Update info label"""
        if not len(self.meta):
            return
        tk = list(self.meta.keys())[0].split(':')[0]+':t'
        if not self.doc.data.has_key(tk):
            logging.debug('No time dataset still', tk)
            self.lbl_info.hide()
            return False
        p = self.base_dataset_path

        # Document-based index
        idx = csutil.find_nearest_val(self.doc.data[tk].data, self.t)
        self.doc_idx = idx
        for k in self.meta.keys():
            ds = self.doc.data.get(k, None)
            if ds is None:
                logging.debug('update_info: no target dataset was found', k)
                self.meta[k] = None
                continue
            self.meta[k] = ds.data[idx]

        msg = ''
        for k, v in self.meta.items():
            lbl = meta_lbl(k)
            if v is None:
                continue
            if k.endswith(':t'):
                m, s = divmod(v, 60.)
                h, m = divmod(m, 60.)
                print(v, h,m,s)
                msg += '{}:{}:{}\n'.format(int(h), int(m), int(s))
            else:
                msg += '{}: {:.2f}\n'.format(lbl, v)
        if not len(msg):
            logging.debug('No metadata to update', self.meta)
            self.lbl_info.hide()
            return False
        self.lbl_info.setText(msg[:-1])
        self.lbl_info.show()
        return True

    def sync_meta_keys(self, keys):
        """To be connected with metaChanged signal from other mini images"""
        new = set(keys)
        old = set(self.meta.keys())
        logging.debug('sync', new, old)
        for k in new - old:
            self.meta[k] = 0
        for k in old - new:
            del self.meta[k]
        if new != old:
            self.update_info()

    def minimumSizeHint(self):
        return self.lbl_img.pixmap().size()

    def sizeHint(self):
        return self.lbl_img.pixmap().size()

    def showMenu(self, pt):
        self.meta_menu.clear()
        self.meta_act = []
        for k in self.meta.keys():
            f = functools.partial(self.del_meta, k)
            a = self.meta_menu.addAction(meta_lbl(k), f)
            self.meta_act.append((a, f))

        self.menu.popup(self.mapToGlobal(pt))

    def del_meta(self, k):
        if not self.meta.has_key(k):
            return False
        del self.meta[k]
        self.metaChanged.emit(self.meta.keys())
        self.update_info()

    def zoom(self, width=0):
        if not width:
            width = self.defaultWidth
        width = min(width, self.maxWidth)
        width = max(width, self.minWidth)
        
        pix = QtGui.QPixmap.fromImage(self.img)
        pix = pix.scaledToWidth(width)
        self.lbl_img.clear()
        self.lbl_img.setPixmap(pix)
        if self.curWidth!=width:
            self.curWidth = width
            self.zoomChanged.emit(self.curWidth)

    def zoomIn(self):
        self.zoom(self.curWidth * 1.1)

    def zoomOut(self):
        self.zoom(self.curWidth * 0.9)

    def wheelEvent(self, event):
        d = event.delta()
        if d == 0:
            return
        if d > 0:
            self.zoomOut()
        else:
            self.zoomIn()

    def copy(self):
        new = MiniImage(self.doc, self.decoder.prefix + self.decoder.datapath[1:], parent=self, curWidth=self.img.width(
        ), maxWidth=self.img.width() * 4, slider=True)
        new.set_idx(self.idx)
#         new.zoom()
        return new

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        if event.mimeData().hasFormat("text/plain"):
            if not event.mimeData().text().startswith('point:'):
                event.acceptProposedAction()

    def dropEvent(self, event):
        logging.debug('DROP EVENT')
        # TODO: intercept aMeta drops
        opt = str(event.mimeData().text())
        if opt.startswith('point:'):
            return
        logging.debug('Adding sample option:', opt)
        self.meta[opt] = 0
        self.update_info()
        self.metaChanged.emit(self.meta.keys())

    def start_drag(self):
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()
        ds = self.doc.data.get('0:kiln/Ts', False)
        if ds is False:
            ds = self.doc.data.get('0:kiln/T')
        T = ds.data[self.doc_idx]
        # Text copy
        mimeData.setData(
            "text/plain", 'point:{}:{}:{}'.format(self.base_dataset_path, self.t, T))
        # Image copy
        ba = QtCore.QByteArray()
        buf = QtCore.QBuffer(ba)
        buf.open(QtCore.QIODevice.WriteOnly)
        self.img.save(buf, 'PNG')
        mimeData.setData("image/png", ba)
        ba1 = QtCore.QByteArray()
        buf1 = QtCore.QBuffer(ba1)
        buf1.open(QtCore.QIODevice.WriteOnly)
        self.img.save(buf1, 'BMP')
        mimeData.setData("image/bmp", ba1) 
        # File copy
        name = '{}_{}.png'.format(self.base_dataset_path.replace('/','_').replace(':',''), self.idx)
        name = os.path.join(self.decoder.tmpdir, name)
        self.img.save(name, 'PNG')
        mimeData.setData("text/uri-list", "file:///"+name)
        
        mimeData.setImageData(self.img)
        drag.setMimeData(mimeData)
        drag.setPixmap(self.lbl_img.pixmap())
        logging.debug('start drag', mimeData.text())
        drag.exec_()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.start_drag()
        return QtGui.QWidget.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Opens a dialog containing a new MiniImage instance"""
        logging.debug(event)
        self.new = self.copy()
        dia = ImageDialog(self.new, parent=self)
        dia.show()


class ImageDialog(QtGui.QDialog):

    """Show a MiniImage in a separate dialog"""

    def __init__(self, mini, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        self.mini = mini
        self.lay.addWidget(self.mini)
        # FIXME: sync problem!
#         self.meta=RowView(parent=self)
#         self.meta.set_doc(mini.doc)
#         self.meta.model().refresh()
# #         self.meta.set_idx(self.mini.idx)
#         self.lay.addWidget(self.meta)
