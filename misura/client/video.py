#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Video export tools"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import numpy as np
try:
    import cv2 as cv
except:
    logging.debug('OpenCV is not available. Video Export is disabled.')
    cv = False

from misura.canon import csutil, reference

import platform

from PyQt4 import QtGui
from misura.client import _

if 'Linux' in platform.platform() and cv:
    default_fourcc = cv.VideoWriter_fourcc('M', '4', 'S', '2')
else:
    default_fourcc = -1

# TODO: profile reconstruction. Use cvpolyfill


def export(sh, frame='/hsm/sample0/frame',
           T='/kiln/T',
           output='output.avi',
           framerate=50.0,
           fourcc=default_fourcc,
           prog=False,
           acquisition_start_temperature=20):
    """Base video export function"""
    if cv is False:
        logging.debug('No OpenCV library')
        return False
    if not output.lower().endswith('.avi'):
        output += '.avi'
    if T:
        nT = sh.col(T, raw=True)
        tT = nT.cols.t
        vT = nT.cols.v
    roi = frame.split('/')[:-1]
    roi.append('roi')
    roi = '/'.join(roi)
    roi = sh.col(roi, raw=True)
    x = roi.cols.x
    y = roi.cols.y
    w = roi.cols.w
    h = roi.cols.h
    # Translate to 0
    x_translation = min(x)
    y_translation = min(y)
    x -= x_translation
    y -= y_translation
    print 'translations', x_translation, y_translation
    # Max dimension (video resolution)
    wMax = int(max(x + w))
    hMax = int(max(y + h))
    out = cv.VideoWriter(output, fourcc, framerate, (wMax, hMax))
    ref = reference.get_node_reference(sh, frame)
    N = sh.len(frame)
    
    index_acquisition_T = csutil.find_nearest_val(vT, acquisition_start_temperature, seed=0)
    i = i0 = csutil.find_nearest_val(ref,
                                tT[index_acquisition_T],
                                seed=0,
                                get=lambda i: ref[i][0])
    ti = 0
    if prog:
        prog.setMaximum(N-i)

    while i < N:
        # Get image
        t, img = ref[i]
# 		print 'exporting {:.2f} {} {:.0f}'.format(100.*i/N,i,t)
        if isinstance(ref, reference.Binary):
            im = cv.imdecode(np.frombuffer(img, dtype='uint8'), 1)
        elif isinstance(ref, reference.Profile):
            # Blank image
            im = np.ones((hMax, wMax), np.uint8) * 255
            # Color black area contained in path
            ((w, h), x, y) = img
            x -= x_translation
            y -= y_translation
            # Avoid black-white inversion
            x = np.concatenate(([0,       0], x, [wMax,  wMax,    0]))
            y = np.concatenate(([hMax, y[0]], y, [y[-1], hMax, hMax]))
            p = np.array([x, y], np.int32).transpose()
            cv.fillPoly(im, [p], 0)
            m = im.mean() 
            if m==255 or m==0:
                print 'invalid frame',p
                import pylab
                pylab.plot(x,y)
                pylab.show()
                break
            im = np.dstack((im, im, im))
        else:
            logging.debug('Unsupported reference')
            break
        # Get T
        ti = csutil.find_nearest_val(tT, t, seed=ti)
        cv.putText(im, "T: {:.1f}C".format(
            vT[ti]), (10, hMax - 10), fontFace=cv.FONT_HERSHEY_DUPLEX, fontScale=1, color=(0, 0, 255))
        # Write frame
        out.write(im)
        i += 1
        if prog:
            QtGui.qApp.processEvents()
            if i > 1 and prog.value() == 0:
                logging.debug('Export cancelled at frame', i)
                break
            prog.setValue(i-i0)

    logging.debug('releasing', output)
    out.release()
    return True


class VideoExporter(QtGui.QDialog):

    def __init__(self, sh, src='/hsm/sample0', parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.setWindowTitle(_('Video Export Configuration'))
        self.lay = QtGui.QFormLayout()
        self.setLayout(self.lay)
        self.sh = sh
        
        src = src.split('/')
        exts = ('profile', 'frame')
        ext = 0
        if src[-1] in exts:
            ext = exts.index(src.pop(-1))
        src = '/'.join(src)
        
        self.src = QtGui.QLineEdit()
        self.src.setText(src)
        self.lay.addRow(_("Sample source"), self.src)

        self.ext = QtGui.QComboBox()
        self.ext.addItem("profile")
        self.ext.addItem("frame")
        self.ext.setCurrentIndex(ext)
        self.lay.addRow(_("Rendering source"), self.ext)

# self.meta=QtGui.QListWidget()
# for k in ['Sintering','Softening','Sphere','HalfSphere','Melting']:
# it=QtGui.QListWidgetItem(k)
# it.setCheckState(0)
# self.meta.addItem(it)
##		self.lay.addRow(_("Render metadata"),self.meta)
##
# self.vals=QtGui.QListWidget()
# for k in ['T','Vol','h']:
# it=QtGui.QListWidgetItem(k)
# it.setCheckState(0)
# self.vals.addItem(it)
##		self.lay.addRow(_("Render values"),self.vals)

        if 'Linux' in platform.platform():
            self.frm = QtGui.QComboBox()
            self.frm.addItem('X264')
            self.frm.addItem('XVID')
            self.frm.addItem('MJPG')
            self.frm.setCurrentIndex(0)
            self.lay.addRow(_("Output Video Codec"), self.frm)
        else:
            self.frm = False

        self.fps = QtGui.QDoubleSpinBox()
        self.fps.setMinimum(1)
        self.fps.setMaximum(100)
        self.fps.setValue(50)
        self.lay.addRow(_("Framerate"), self.fps)

        self.acquisition_start_temperature = QtGui.QSpinBox()
        self.acquisition_start_temperature.setMinimum(1)
        self.acquisition_start_temperature.setMaximum(2000)
        self.acquisition_start_temperature.setValue(20)
        self.lay.addRow(_("Start acquisition at temperature"), self.acquisition_start_temperature)

        self.out = QtGui.QLineEdit()
        self.out.setText(sh.get_path() + '.avi')
        self.lbl_out = QtGui.QPushButton(_("Output file"))
        self.lbl_out.pressed.connect(self.change_output)
        self.lay.addRow(self.lbl_out, self.out)

        self.btn_ok = QtGui.QPushButton("Start")
        self.btn_ok.pressed.connect(self.export)
        self.btn_ko = QtGui.QPushButton("Cancel")
        self.btn_ko.pressed.connect(self.cancel)
        self.lay.addRow(self.btn_ko, self.btn_ok)
        self.prog = False

    def export(self):
        """Start export thread"""
        prog = QtGui.QProgressBar()
        self.lay.addRow(_('Rendering:'), prog)
        src = str(self.src.text())
        ext = str(self.ext.currentText())
        if self.frm:
            frm = str(self.frm.currentText())
            fourcc = cv.VideoWriter_fourcc(*frm)
        else:
            fourcc = default_fourcc
        out = str(self.out.text())
        fps = self.fps.value()
        self.prog = prog
        export(self.sh, frame=src + '/' + ext, fourcc=fourcc,
               output=out, framerate=fps, prog=prog,
               acquisition_start_temperature=self.acquisition_start_temperature.value())
        self.done(0)

    def cancel(self):
        """Interrupt export thread"""
        logging.debug('Cancel clicked!', self.prog)
        if self.prog:
            self.prog.setValue(0)

    def change_output(self):
        new = QtGui.QFileDialog.getSaveFileName(
            self, _("Video output file"), filter=_("Video (*avi)"))
        if len(new):
            self.out.setText(new)
