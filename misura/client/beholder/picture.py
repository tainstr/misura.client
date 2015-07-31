#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from functools import partial
from PyQt4 import QtGui, QtCore
from misura.client import widgets, _
import overlay
import functools
from misura.client import conf
from misura.client.live import FrameProcessor, SampleProcessor
from motionplane import SensorPlane
from sample_picture import SamplePicture
import calibration
from time import sleep


class ViewerPicture(QtGui.QGraphicsView):

    """Display widget for camera frames"""
    role = 'camera'
    sampleProcessor = False
    processor = False

    @property
    def inv(self):
        inv = 0
        if self.remote.encoder.has_key('invert'):
            inv = self.remote.encoder['invert']
        self._inv = inv  # cached inv
        return inv

    def __init__(self, remote, server, parent=None,
                 frameProcessor=False, sampleProcessor=False):
        QtGui.QGraphicsView.__init__(self, parent)
        self.windows = {}
        self.objects = {}
        self.conf_win = {}
        self.conf_act = {}
        self.motor_ctrl = {}
        self._res = {'x': -1, 'y': -1}
        self._inv = 0
        self.samples = []
        self.parent = parent
        self.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.lightGray))
        self.remote = remote
        self.server = server
        self.fullpath = self.remote['fullpath']
        self.setWindowTitle('Camera Viewer: %s' % remote['name'])

        # Setup the graphical scene
        self.gscene = QtGui.QGraphicsScene(self)
        self.plane = SensorPlane(remote)
        self.gscene.addItem(self.plane)
        self.plane.setVisible(True)
        self.plane.setPos(0, 0)

        self.setScene(self.gscene)

        if self.inv != 0:
            self.rotate(self.inv * 90.)

        self.saveDir = False
        self.saveN = 0

        self.calibrationTool = False

        self.menu = QtGui.QMenu(self)
        self.addActions()
        self.connect(
            self.menu, QtCore.SIGNAL('aboutToShow()'), self.updateActions)

        self.setFrameProcessor(frameProcessor)
        self.setSampleProcessor(sampleProcessor)
        self.reconnectSample()
        # Monitor number of samples
        self.nsmp_obj = widgets.ActiveObject(
            self.server, self.remote, self.remote.gete('nSamples'), parent=self)
        self.nsmp_obj.register()
        self.connect(self.nsmp_obj, QtCore.SIGNAL(
            'changed()'), self.reconnectSample, QtCore.Qt.QueuedConnection)

    def close(self):
        logging.debug('%s', 'Closing ViewerPicture')
        if self.processor:
            logging.debug('%s', 'Closing FrameProcessor')
            self.processor.toggle_run(False)
            logging.debug('%s', 'quitting')
            self.processor.wait()
            self.processor.terminate()
            self.processor.deleteLater()
#       self.processor=False
        if self.sampleProcessor:
            logging.debug('%s', 'Closing SampleProcessor')
            self.sampleProcessor.toggle_run(False)
            logging.debug('%s', 'quitting')
            self.sampleProcessor.wait()
            self.sampleProcessor.terminate()
            self.sampleProcessor.deleteLater()
#       self.sampleProcessor=False
        if self.calibrationTool:
            self.calibrationTool.close()

    def setFrameProcessor(self, fp=False):
        """Create or set the thread receiving frames from the remote camera"""
        if not fp:
            fp = FrameProcessor(self.remote, self)
        if self.processor is not False:
            self.processor.toggle_run(False)
            self.processor.deleteLater()
            self._oldproc = self.processor
#           del self.processor
        self.processor = fp
#       self.connect(self.processor, QtCore.SIGNAL('readyFrame(int,int,int,int,int,QByteArray)'), self.updateFrame, QtCore.Qt.QueuedConnection)
        self.connect(self.processor, QtCore.SIGNAL(
            'readyImage(int,int,int,int,int,QImage)'), self.updateImage, QtCore.Qt.QueuedConnection)
        self.connect(self.processor, QtCore.SIGNAL(
            'crop(int,int,int,int)'), self.set_crop)
        self.termProcessor = lambda * foo: self.processor.toggle_run(False)
        self.connect(
            self, QtCore.SIGNAL('destroyed(QObject)'), self.termProcessor)

    def set_crop(self, x, y, w, h):
        """Broadcast new image crop value to all overlays. It is used as the region of interest."""
        self.plane.set_crop(x, y, w, h)
        g = {'x': w, 'y': h}
        if self._inv:
            g = {'y': w, 'x': h}
        # Update motor control stepping
        for c in ('x', 'y'):
            # skip if equal to cached resolution
            if g[c] == self._res[c]:
                continue
            # skip if no motor control defined
            m = self.motor_ctrl.get(c, False)
            if not m:
                continue
            enc = self.plane.enc(c)
            if not enc:
                continue
            # Calc new tick interval for camera
            align = enc['align']
            ps = abs(int(1. * g[c] / align))  # page step
            ps = max(ps, 50)  # at least 50 steps
            s = int(0.2 * ps)  # single step
            s = max(s, 10)  # at least 10 steps
            # Invert controls and appearance?
            orient = m.slider.orientation()
            invc = (align > 0 and orient == QtCore.Qt.Horizontal) or (align < 0 and orient == QtCore.Qt.Vertical )
            logging.debug('############ INVERSION?',m.prop['kid'],invc)
            # Skip if no change
            if ps != m.slider.pageStep() or s != m.slider.singleStep() or invc != m.slider.invertedControls():
                m.slider.setPageStep(ps)
                m.slider.setSingleStep(s)
                m.slider.setInvertedControls(invc)
                m.slider.setInvertedAppearance(invc)
                m.remObj.setattr(m.handle, 'step', s)
        self._res = g  # cache resolution
        # Update all overlays
        for smp in self.samples:
            smp.update({'crop': [x, y, w, h]})

    def setSampleProcessor(self, rp=False):
        """Create or set the thread receiving sample information from the remote camera"""
        if not rp:
            rp = SampleProcessor(parent=self)
        if self.sampleProcessor is not False:
            self.sampleProcessor.toggle_run(False)
            del self.sampleProcessor
        self.sampleProcessor = rp

    def unscale(self, factor):
        """Keep dimension of UI elements while zooming in/out"""
        self.plane.unscale(factor)
        for smp in self.samples:
            smp.unscale(factor)
        r = self.plane.boundingRect() & self.plane.box.boundingRect(
        ) & self.plane.cropBox.boundingRect()
        r.adjust(-50, -50, 50, 50)
        self.scene().setSceneRect(r)
        self.plane.pt.ensureVisible()

    def wheelEvent(self, event):
        """Zoom in/out, center the scene and unscale all UI elements."""
        factor = 1 + event.delta() / 2000.0
        self.scale(factor, factor)
        self.unscale(factor)

    def unzoom(self):
        """Remove user zoom"""
        # Get current zooming factor
        s = self.transform().m11()
        self.unscale(1. / s)
        self.fitInView(self.plane.boundingRect(), QtCore.Qt.KeepAspectRatio)

    def bool_action(self, name, prop, obj=False, menu=False):
        """Create a menu action representing a remote obj true/false option"""
        if obj is False:
            obj = self.remote
        if menu is False:
            menu = self.menu
        if isinstance(prop, str):
            prop = obj.gete(prop)
        if prop is None:
            logging.debug('%s', 'Sample not found!')
            return False
        handle = prop['handle']
        fp = obj['fullpath']
        act = widgets.aBooleanAction(obj, prop, menu)
        act.setText(name)
        menu.addAction(act)
        return act

    def button_action(self, name, label=False,  obj=False, menu=False):
        if obj is False:
            obj = self.remote
        if menu is False:
            menu = self.menu
        fp = obj['fullpath']
        f = partial(obj.get, name)
        if not label:
            label = name.capitalize()
        act = menu.addAction(label, f)

    def updateActions(self):
        """Set actions status."""
        self.streamAct.setChecked(self.processor.isRunning())
        if self.calibrationTool:
            self.calAct.setChecked(self.calibrationTool.isVisible())
        else:
            self.calAct.setChecked(False)
        for fp, win in self.conf_win.iteritems():
            act = self.conf_act[fp]
            act.setChecked(2 * win.isVisible())
            logging.debug('%s %s %s', 'updateActions', fp, act.isChecked())

    def configure_object(self, obj):
        """Show object configuration window"""
        fp = obj['fullpath']
        logging.debug('%s %s', 'configure object', fp)
        act = self.conf_act.get(fp, False)
        if act is False:
            logging.debug(
                '%s %s', 'configure_object: Object path not found', fp)
            return
        win = self.conf_win.get(fp, False)
        if win is False:
            win = conf.TreePanel(obj, select=obj)
            win.setWindowTitle('Configuration tree from: %s' % obj['name'])
            self.conf_win[fp] = win
        if act.isChecked():
            logging.debug('%s %s', 'SHOWING', fp)
            win.show()
            win.activateWindow()
            win.raise_()
        else:
            logging.debug('%s %s', 'HIDING', fp)
            win.hide()

    def add_conf_action(self, menu, obj, fp=False, txt=False):
        """Create a "Configure" action in menu and return it."""
        if not fp:
            fp = obj['fullpath']
        if txt is False:
            txt = 'Configure'
        act = menu.addAction(
            _(txt), functools.partial(self.configure_object, obj))
        act.setCheckable(True)
        self.conf_act[fp] = act
        return act

    def addActions(self):
        """Add actions to right-click context menu."""
        self.menu.setTitle('Cam %s /dev/%s' %
                           (self.remote['name'], self.remote['dev']))
        self.streamAct = self.menu.addAction('Stream', self.toggle)
        self.streamAct.setCheckable(True)
        self.autoresAct = self.menu.addAction('Fit view', self.unzoom)

        # Camera configuration option
        self.add_conf_action(self.menu, self.remote, self.fullpath)
        self.bool_action('Simulation', 'Analysis_Simulation')

        # Per-Sample Menu
        self.menus = {}

        # Controls Menu
        self.imenu = self.menu.addMenu(_('Imaging'))
        self.add_imaging_actions(self.imenu)

        #########
        # Analysis menu
        #########
        self.amenu = self.menu.addMenu(_('Analysis'))

        # General view entries
        self.roiAct = self.amenu.addAction('View Regions',
                                           functools.partial(self.over_by_name, 'roi'))
        self.roiAct.setCheckable(True)
        
        roiResetAct = self.amenu.addAction('Reset Regions', self.reset_regions)
        roiResetAct.setCheckable(False)
        
        self.profileAct = self.amenu.addAction(_('Profile'),
                                               functools.partial(self.over_by_name, 'profile'))
        self.profileAct.setCheckable(True)

        self.labelAct = self.amenu.addAction(_('Values Label'),
                                             functools.partial(self.over_by_name, 'label'))
        self.labelAct.setCheckable(True)

        self.pointsAct = self.amenu.addAction(_('Points'),
                                              functools.partial(self.over_by_name, 'points'))

        # Shape entries
        self.pointsAct.setCheckable(True)

        self.baseHeightAct = self.amenu.addAction(_('Base and Height'),
                                                  functools.partial(self.over_by_name, 'baseHeight'))
        self.baseHeightAct.setCheckable(True)

        self.circleAct = self.amenu.addAction(_('Circle Fitting'),
                                              functools.partial(self.over_by_name, 'circle'))
        self.circleAct.setCheckable(True)

        # Border entries
        # TODO: Border overlays

        # Pixel Calibration
        self.calAct = self.amenu.addAction(
            'Pixel Calibration', self.calibration)
        self.calAct.setCheckable(True)
        # Remove tool action if modification is not allowed
        if not self.remote.check_write('Analysis_umpx'):
            self.amenu.removeAction(self.calAct)
        #########
        # Motion menu
        #########
        self.mmenu = self.menu.addMenu(_('Motion'))
        self.add_motion_actions(self.mmenu)
        # Other stuff
        self.menu.addAction('Save frame', self.save_frame)
        
    def reset_regions(self):
        """Re-init samples, resetting regions of interest."""
        r=self.remote.init_samples()
        QtGui.QMessageBox.information(self, 'Region reset', r)

    def add_motion_actions(self, menu):
        """Create menu actions for motion control"""
        cpos = {'x': 'bottom', 'y': 'left'}
#       if self.inv!=0:
#           cpos={'x':'left','y':'bottom'}
        self.motor_ctrl = {}

        def add_coord(name):
            # TODO: replace with enc.role2dev('motor')
            enc = getattr(self.remote.encoder, name)
            m = enc['motor']
            if m is False:
                return False
            logging.debug('%s', m)
            path = m[0]
            if path in ('None', None):
                return False
            if self.server.searchPath(path) is False:
                return False
            obj = self.server.toPath(path)
            if obj is None:
                return False
            submenu = menu.addMenu(_(name.capitalize()))
            act = widgets.MotorSliderAction(self.server, obj, submenu)
            submenu.addAction(act)
            align=enc['align']
            if name in ('x', 'y'):
                slider = widgets.MotorSlider(
                    self.server, obj, parent=self.parent)
                slider.spinbox.hide()
                self.parent.setControl(slider, cpos[name])
                self.motor_ctrl[name] = slider

            act = widgets.aBooleanAction(
                obj, obj.gete('moving'), parent=submenu)
            submenu.addAction(act)
            self.button_action(
                'limits', label='Search limits',  obj=obj, menu=submenu)
            self.button_action(
                'zero', label='Set zero position',  obj=obj, menu=submenu)
            self.add_conf_action(submenu, obj, path, txt='Configure motor')
            self.add_conf_action(submenu, enc, txt='Configure encoder')

        for label, name in self.remote.encoder.list():
            add_coord(name)
        self.add_conf_action(menu, self.remote.encoder, txt='Spatial encoder')

    def add_imaging_actions(self, menu):
        """Create menu actions for imaging controls"""
        for h in ['exposureTime', 'contrast', 'brightness', 'gamma', 'gain', 'saturation', 'hue']:
            if not self.remote.has_key(h):
                continue
            act = widgets.aNumberAction(
                self.server, self.remote, self.remote.gete(h), parent=menu)
            menu.addAction(act)

    def over_by_name(self, name):
        """Show or hide overlay by name"""
        act = getattr(self, name + 'Act')
        opt = set([])
        for smp in self.samples:
            overlay = getattr(smp, name, False)
            container = overlay
            if not container:
                logging.debug('%s %s', 'No overlay named:', name)
            if act.isChecked():
                logging.debug('%s %s', 'show', name)
                overlay.show()
#               if name=='roi':
#                   self.reconnectSample()
                self.connect(self.sampleProcessor,
                             QtCore.SIGNAL('updated(int, PyQt_PyObject)'),
                             self.updateSample)
            else:
                container.hide()
                self.disconnect(self.sampleProcessor,
                                QtCore.SIGNAL('updated(int, PyQt_PyObject)'),
                                self.updateSample)
            # Update active options list
            opt = opt.union(smp.opt)
        # Update sampleProcessor options:
        self.sampleProcessor.opt = opt
        if act.isChecked() and not self.sampleProcessor.isRunning():
            self.sampleProcessor.start()

    def calibration(self):
        """Show/hide the pixel calibration tool"""
        # TODO: coherent way to fire caltool in multicrop mode
        if self.calibrationTool:
            self.calibrationTool.close()
        self.calibrationTool = calibration.CalibrationTool(
            self.plane, self.remote)
        self.calibrationTool.show()

    def save_frame(self):
        """Save current frame"""
        # FIXME: multicrop...
        assert False
        if not self.saveDir:
            self.saveDir = QtGui.QFileDialog.getExistingDirectory(
                self, "Images destination folder", "/tmp")
        self.saveN += 1
        self.pix.save('%s/%s_%i.jpg' %
                      (self.saveDir, self.remote['name'], self.saveN), 'JPG', 25)

    def toggle(self, do=None):
        """Toggle data streams"""
        if not self.processor:
            logging.debug('%s', 'No processor. Cannot start/stop.')
            return False
        if do == None:
            self.processor.toggle_run()
        elif do > 0:
            logging.debug('%s', 'proc start')
            self.reconnectSample()
            self.processor.toggle_run(True)
        else:
            logging.debug('%s', 'proc stop')
            self.processor.toggle_run(False)

        self.sampleProcessor.toggle_run(do=self.processor.isRunning())

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        logging.debug('%s %s', 'got item', item)
        if hasattr(item, 'menu'):
            item.menu.popup(event.globalPos())
        else:
            self.menu.popup(event.globalPos())

    def updateSample(self, i, multiget):
        logging.debug('%s %s %s', 'updateSample', i, multiget.keys())
        smp = self.samples[i]
        r = smp.update(multiget)
        if smp.opt_changed:
            opt = set([])
            for smp in self.samples:
                opt = opt.union(smp.opt)
            self.sampleProcessor.opt = opt

    def updateImage(self, *args):
        self.updateFrame(*args, img=True)

    def updateFrame(self, i, x, y, w, h, data, img=False):
        """Called when a new frame is available from processor"""
        # Nota: non posso usare direttamente QPixmap.loadFromData per via di un
        # memory leak in Qt
        if img:
            qimg = data
        else:
            qimg = QtGui.QImage()
            qimg.loadFromData(data)
        if len(self.samples) == 0 or i >= len(self.samples):
            self.reconnectSample()
            return
        smp = self.samples[i]
        if not smp.isVisible():
            smp.show()
        smp.pix = QtGui.QPixmap.fromImage(qimg)
        smp.pixItem.setPixmap(smp.pix)
        smp.update({'roi': [x, y, w, h]})
        self.emit(QtCore.SIGNAL('frameUpdated()'))

    def reconnectSample(self):
        """Remove and regenerate all samples."""
        self.sampleProcessor.toggle_run(False)
        stream = self.processor.stream
        self.processor.toggle_run(False)
        n = self.remote['nSamples']
        for smp_pix in self.samples:
            smp_pix.hide()
            smp_pix.close()
            self.gscene.removeItem(smp_pix)
            del smp_pix
        self.samples = []
        samples = []
        for i in range(n):
            logging.debug(
                '%s %s %s %s', 'RECONNECTING SAMPLES', i, n, self.remote['fullpath'])
            name = 'smp%i' % i
            if not self.remote.has_key(name):
                logging.debug('%s %s', 'Sample not found', name)
                continue
            # Get the current analysis sample
            path = self.remote[name][0]
            if path in [None, 'None']:
                logging.debug('%s %s', 'No sample path defined', path)
                continue
            sample = self.server.toPath(path)
            if sample is None:
                logging.debug('%s %s', 'Sample path not found', path)
                continue
            fp = sample['fullpath']
            samples.append(sample)
            smp_pix = SamplePicture(self.plane, sample, i)
            smp_pix.roi.get()
            # Show the roi only if option is checked
            if self.roiAct.isChecked():
                smp_pix.roi.show()
            self.samples.append(smp_pix)
            # Menu structure for samples
            m = self.menus.get(name, False)
            if m is False:
                m = self.menu.addMenu(_('Sample ') + str(i))
                self.menus[name] = m
            m.clear()
            self.add_conf_action(m, sample, fp)
            self.bool_action(
                'Black/white levelling', 'blackWhite', sample.analyzer, m)
            self.bool_action(
                'Adaptive Threshold', 'adaptiveThreshold', sample.analyzer, m)
            self.bool_action(
                'Dynamic Regions', 'autoregion', sample.analyzer, m)

        self.sampleProcessor.set_samples(samples)
        self.sampleProcessor.toggle_run(do=stream)
        self.processor.toggle_run(do=stream)
        self.emit(QtCore.SIGNAL('updatedROI()'))
