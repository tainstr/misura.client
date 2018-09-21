#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Video export tools"""
from misura.canon.option import ao, ConfigurationProxy
from copy import deepcopy
from . import conf
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
           acquisition_start_temperature=20,
           Tstep=0,
           tstep=0,
           centerx=False,
           centery=False):
    """Base video export function"""
    if cv is False:
        logging.debug('No OpenCV library')
        return False
    if not output.lower().endswith('.avi'):
        output += '.avi'

    nT = sh.col(T, raw=True)
    tT = nT.cols.t
    vT = nT.cols.v
    
    
    ref = reference.get_node_reference(sh, frame)
    N = sh.len(frame)
    
    # If dynamic roi is found
    roi = frame.split('/')[:-1]
    roi.append('roi')
    roi = '/'.join(roi)
    if sh.has_node(roi):
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
        logging.debug('translations', x_translation, y_translation)
        # Max dimension (video resolution)
        wMax = int(max(x + w))
        hMax = int(max(y + h))
    else: 
        # No dynamic roi - take first frame
        t, img = ref[0]
        ((w,h), x, y) = img
        x_translation = min(x)
        y_translation = min(y)
        logging.debug('first frame', w,h, max(x), x_translation, max(y), y_translation)
        dx = (max(x)-min(x))+50
        dy = (max(y)-min(y))+50
        d = max((dx, dy))
        wMax = hMax = d
        x_translation -= 25
        y_translation -= max((50, d/3))
        y_translation = max((0, y_translation))
    # Ensure even dimensions for broad codec compatibility
    wMax += wMax%2
    hMax += hMax%2
    logging.debug('Max resolution', wMax, hMax)    
    out = cv.VideoWriter(output, fourcc, framerate, (wMax, hMax))
    index_acquisition_T = csutil.find_nearest_val(vT, acquisition_start_temperature, seed=0)
    i = i0 = csutil.find_nearest_val(ref,
                                tT[index_acquisition_T],
                                seed=0,
                                get=lambda i: ref[i][0])
    ti = 0
    if prog:
        prog.setMaximum(N-i)
    logging.debug('Set progress bar', N, i, N-i)
    pg = 0
    while i < N:
        # Get image
        t, img = ref[i]
        print 'exporting {:.2f} {} {:.0f}'.format(100.*i/N,i,t)
        if isinstance(ref, reference.Binary):
            im = cv.imdecode(np.frombuffer(img, dtype='uint8'), 1)
        elif isinstance(ref, reference.Profile) or isinstance(ref, reference.CumulativeProfile):
            # Blank image
            im = np.ones((hMax, wMax), np.uint8) * 255
            # Color black area contained in path
            ((w, h), x, y) = img
            x -= np.uint16(x_translation)
            y -= np.uint16(y_translation)
            if centerx:
                x += np.uint16(wMax/2. - int(x.mean()))
            if centery:
                y += np.uint16(hMax/2. - int(y.mean()))
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
        Ti = vT[ti]
        cv.putText(im, "T: {:.1f}C".format(Ti), 
                   (10, hMax - 10), 
                   fontFace=cv.FONT_HERSHEY_DUPLEX, 
                   fontScale=1, 
                   color=(0, 0, 255))
        
        # Write frame
        out.write(im)
        # Calculate next frame
        nt = -1
        if Tstep>0:
            Ti += Tstep
            j = csutil.find_nearest_val(vT, Ti, seed=ti)
            if j<=i:
                Tstep*=-1
                logging.debug('Inverting search direction', Tstep)
                Ti += 2*Tstep
                j = csutil.find_nearest_val(vT, Ti, seed=ti)
                if j<=i:
                    logging.debug('No more temperature rise', Tstep)
                    break
            nt = tT[j]
        elif tstep>0:
            nt = tT[ti]+tstep
          
        # Get frame index at time nt
        if nt>0:
            j = ref.get_time(nt) 
            if j<=i:
                break 
            i = j
        else:
            # just take next frame
            i += 1
        if prog:
            QtGui.qApp.processEvents()
            if pg>1 and prog.value() == 0:
                logging.debug('Export cancelled at frame', i)
                break
            pg = i-i0
            prog.setValue(pg)
           

    logging.debug('releasing', output)
    out.release()
    return True

opts = {}
ao(opts, 'src', 'String', '', _('Sample source'))
ao(opts, 'T', 'String', '', _('Temperature source'))
ao(opts, 'ext', 'Chooser', 'profile', _('Rendering source'), options=['profile', 'frame'])
ao(opts, 'startTemp', 'Float', 0, _('Start temperature'))
ao(opts, 'fps', 'Integer', 50, _('Framerate'), min=1, max=100, step=1, unit='hertz')
ao(opts, 'Tstep', 'Float', 0, _('Temperature steps'), min=0, max=50, step=1, unit='celsius')
ao(opts, 'tstep', 'Float', 0, _('Time steps'), min=0, max=600, step=1, unit='second')
ao(opts, 'centerx', 'Boolean', False, _('Center X coord'))
ao(opts, 'centery', 'Boolean', False, _('Center Y coord'))
ao(opts, 'codec', 'Chooser', 'X264', _('Output video codec'), options=['X264', 'XVID', 'MJPG'])



class VideoExporter(QtGui.QDialog):

    def __init__(self, sh, src='/hsm/sample0', parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.setWindowTitle(_('Video Export Configuration'))
        self.lay = QtGui.QFormLayout()
        
        self.sh = sh
        
        src = src.split('/')
        exts = ('profile', 'frame', 'filteredProfile')
        ext = 0
        if src[-1] in exts:
            ext = exts.index(src.pop(-1))
        src = '/'.join(src)
        T = src + '/T'
        ropts = deepcopy(opts)
        ropts['src']['current'] = src
        ropts['T']['current'] = T
        if ext:
            ropts['ext']['current'] = ext
        if 'Linux' in platform.platform():
            ropts.pop('codec')
                
        self.cfg = ConfigurationProxy({'self': ropts})
        self.wg = conf.Interface(self.cfg, self.cfg, ropts)
        self.lay.addRow(self.wg)

        self.out = QtGui.QLineEdit(self)
        self.out.setText(sh.get_path() + '.avi')
        self.lbl_out = QtGui.QPushButton(_("Output file"))
        self.lbl_out.pressed.connect(self.change_output)
        self.lay.addRow(self.lbl_out, self.out)

        self.btn_ok = QtGui.QPushButton("Start")
        self.btn_ok.pressed.connect(self.export)
        self.btn_ko = QtGui.QPushButton("Cancel")
        self.btn_ko.pressed.connect(self.cancel)
        self.btn_ko.setEnabled(False)
        self.lay.addRow(self.btn_ko, self.btn_ok)
        self.prog = False
        self.setLayout(self.lay)

    def export(self):
        """Start export thread"""
        self.btn_ko.setEnabled(True)
        prog = QtGui.QProgressBar()
        self.lay.addRow(_('Rendering:'), prog)
        src = str(self.cfg['src'])
        ext = str(self.cfg['ext'])
        if 'frm' in self.cfg:
            frm = str(self.cfg['frm'])
            fourcc = cv.VideoWriter_fourcc(*frm)
        else:
            fourcc = default_fourcc
        out = str(self.out.text())
        self.prog = prog
        export(self.sh, frame=src + '/' + ext, T=self.cfg['T'], 
               fourcc=fourcc,
               output=out, framerate=self.cfg['fps'], prog=prog,
               acquisition_start_temperature=self.cfg['startTemp'],
               Tstep=self.cfg['Tstep'],
               tstep=self.cfg['tstep'],
               centerx=self.cfg['centerx'],
               centery=self.cfg['centery'])
        self.done(0)

    def cancel(self):
        """Interrupt export thread"""
        logging.debug('Cancel clicked!', self.prog)
        self.btn_ko.setEnabled(False)
        if self.prog:
            self.prog.setValue(0)

    def change_output(self):
        new = QtGui.QFileDialog.getSaveFileName(
            self, _("Video output file"), filter=_("Video (*avi)"))
        if len(new):
            self.out.setText(new)
