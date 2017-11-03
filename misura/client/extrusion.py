#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Render 3D extrusion by overlapping all profiles"""
from copy import deepcopy
import numpy as np

from misura.canon.reference import get_node_reference
from misura.canon.option import ao, ConfigurationProxy
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client import widgets, conf, _
from misura.client.live import registry

try:
    import OpenGL
    OpenGL.ERROR_ON_COPY = False
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from OpenGL_accelerate.numpy_formathandler import NumpyHandler
    enabled = True
except:
    pg = False
    gl = False
    enabled = False
    logging.debug('Disabled 3D: no pyqtgraph')

from PyQt4 import QtCore, QtGui

STEPS = np.array([0.0, 0.33, 0.66, 1.0])
CLRS = ['b', 'r', 'y', 'w']

clrmp = False
if pg:
    clrmp = pg.ColorMap(STEPS, np.array(
        [pg.colorTuple(pg.Color(c)) for c in CLRS]))


# TODO: parametrize start, end, max_layers
# TODO: step by time/temperature
# TODO: write temperature labels
def read_file(profile, startTime=10, endTime=-1, maxLayers=500, cut=0, deplete=1,
              T=False,
              aborted=[False],
              jobs=lambda *x, **k: 0,
              job=lambda *x, **k: 0,
              done=lambda *x, **k: 0):
    xs = []
    ys = []
    zs = []
    colors = []
    start = 0
    if startTime > 0:
        start = profile.get_time(startTime)
    end = -1
    if endTime > 0:
        end = profile.get_time(endTime)
    c = 0.
    n = len(profile)
    if end < 0:
        end += n
    n = end - start + 1
    step = max(n // maxLayers, 1)
    tot = n // step
    fz = 0.6
    z = -fz * tot / 2
    maxWidth = 0
    maxHeight = 0
    minX = 1e10
    minY = 1e10

    scut, ecut = None, None
    if cut > 0:
        scut, ecut = cut, -cut
    # Color calculation
    delta = tot
    minT = 0
    maxT = 0
    if T is not False:
        mi, mt, minT = T.outfile.min(T.path,
                                     start_time=startTime,
                                     end_time=endTime)
        Mi, Mt, maxT = T.outfile.max(T.path,
                                     start_time=startTime,
                                     end_time=endTime)
        delta = maxT - minT

    def get_color(c, t):
        if T is False:
            pos = 1. * c / delta
        else:
            mi = T.get_time(t)
            pos = (T[mi][1] - minT) / delta
            print pos, T[mi][1], minT, delta
        col = list(clrmp.map(pos))
        # Adjust transparency to reduce bightness of saturated colors
        col[-1] = int(255 - (col[0] + col[1] + col[2]) / 5)
        return col

    def abort():
        aborted[0] = True

    jobs((end - start), 'Extrusion', abort=abort)
    for i in range(start, end, step):
        if aborted[0]:
            return False, False, False, False
        job(i - start, 'Extrusion')
        t, ((w, h), x, y) = profile[i]
        x = x.astype(np.float32)-x[0]
        y = y.astype(np.float32)
        if cut or deplete:
            x = x[scut:ecut:deplete]
            y = y[scut:ecut:deplete]
        _minx = min(x)
        if _minx<minX:
            minX=_minx
        mW = max(x) - _minx
        if mW > maxWidth:
            maxWidth = mW
        _miny = min(y)
        if _miny<minY:
            minY=_miny
        mH = max(y) - _miny
        if mH > maxHeight:
            maxHeight = mH
        xs.append(x)
        ys.append(y)
        zs.append(z)
        colors.append(get_color(c, t))
        # Should be calc depending on shot height
        z += fz
        c += 1
    
    for i,x in enumerate(xs):
        x -=minX+maxWidth/2
        ys[i]-=minY+maxHeight/2
    return xs, ys, zs, colors, minT, maxT


def plot_line(x, y, z, color='w'):
    # first line
    p = np.array([z, x, y])
    h = NumpyHandler()
    h.ERROR_ON_COPY = 0
    p = h.asArray(p.transpose().astype(np.float16))
    C = pg.glColor(color)
    plt = gl.GLLinePlotItem(pos=p, color=C, width=0.5, antialias=True)
    return plt


def add_grids(view):
    # create three grids, add each to the view
    xgrid = gl.GLGridItem()
    ygrid = gl.GLGridItem()
    zgrid = gl.GLGridItem()
    view.addItem(xgrid)
    view.addItem(ygrid)
    view.addItem(zgrid)

    # rotate x and y grids to face the correct direction
    xgrid.rotate(90, 0, 1, 0)
    ygrid.rotate(90, 1, 0, 0)


def mesh3d(xs, ys, zs, colors, start=0, end=-1, step=1):
    # Extremely slow. Frequent crashes.
    w = gl.GLViewWidget()
    nx, ny, nz = [], [], []
    for i, x in enumerate(xs):
        sampled_x = x[start:end:step]
        sampled_y = ys[i][start:end:step] - ys[i][0]
        z = np.ones(len(sampled_x)) * zs[i]
        nx.append(sampled_x)
        ny.append(sampled_y)
        nz.append(z)

    verts = np.array([nx[0], ny[0], nz[0]]).transpose()
    faces = []
    fcolors = []
    vcolors = [colors[0]] * len(verts)
    vi = 0
    for i in range(1, len(nx)):
        nverts = np.array([nx[i], ny[i], nz[i]]).transpose()
        vj = len(verts)
        for j, v in enumerate(nverts):
            if j < len(nverts) - 1:
                faces += [[vi + j, vj + j, vj + j + 1],
                          [vi + j, vi + j + 1, vj + j + 1]]

                fcolors += [colors[i]] * 2
        verts = np.concatenate((verts, nverts))
        vcolors += [colors[i]] * len(nverts)
        vi = vj

    mesh = gl.MeshData(verts, np.array(
        faces), faceColors=fcolors, vertexColors=vcolors)
    plt = gl.GLMeshItem(meshdata=mesh, drawFaces=True, drawEdges=False)

    w.addItem(plt)
    # add_grids(w)
    ax = gl.GLAxisItem()
    w.addItem(ax)
    return w


def surface3d(xs, ys, zs, colors, start=0, end=-1, step=1):
    w = gl.GLViewWidget()
    for i, x in enumerate(xs):
        sampled_x = x[start:end:step]
        sampled_y = ys[i][start:end:step] - ys[i][0]
        z = np.ones(len(sampled_x)) * zs[i]
        plt = plot_line(sampled_x, sampled_y, z, color=colors[i])
        w.addItem(plt)
    # add_grids(w)
    ax = gl.GLAxisItem()
    w.addItem(ax)
    # w.pan(0,0,0)
    return w


def plot3d(xs, ys, zs, colors,
           aborted=[False],
           jobs=lambda *x, **k: 0,
           job=lambda *x, **k: 0,
           done=lambda *x, **k: 0):

    def abort():
        aborted[0] = True
    jobs(len(xs), 'Extrusion', abort=abort)
    objects = []
    for i, x in enumerate(xs):
        if aborted[0]:
            logging.debug('Estrusion aborted')
            return False
        job(i, 'Extrusion')
        z = np.ones(len(x)) * zs[i]
        plt = plot_line(x, -ys[i], -z, color=colors[i])
        plt.scale(0.005, 0.005, 0.005)
        objects.append(plt)

    # add_grids(w)
    ax = gl.GLAxisItem()
    objects.append(ax)
    done('Extrusion')
    return objects


def extrude(f, data_path, config={'cut': 0}):
    data_path = data_path.split(':')[-1]
    if not data_path.startswith('/'):
        data_path = '/' + data_path
    prf = get_node_reference(f, data_path)
    T = '/'.join(data_path.split('/')[:-1]) + '/T'
    T = get_node_reference(f, T)
    xs, ys, zs, colors, minT, maxT = read_file(prf, T=T, **config)
    w = plot3d(xs, ys, zs, colors)
    return w


def deferred_extrusion(prf, T, config={}, aborted=[False],
                       jobs=lambda *x, **k: 0,
                       job=lambda *x, **k: 0,
                       done=lambda *x, **k: 0):
    """Run data collection in a separate thread and emit signal when GL widget is ready"""

    def abort():
        aborted[0] = True

    thread = widgets.RunMethod(
        read_file, prf, T=T, aborted=aborted, jobs=jobs, job=job, done=done, **config)

    thread.pid = 'Extrusion'
    thread.abort = abort
    thread.emit_result = False

    def process_result():
        if thread.result is None:
            logging.error('No Extrusion result!')
            return
        xs, ys, zs, colors, minT, maxT = thread.result
        if xs is False:
            logging.info('Invalid Extrusion result. Aborted?')
            return
        w = plot3d(xs, ys, zs, colors)
        thread.objects = w
        thread.notifier.emit(QtCore.SIGNAL('widget_ready()'))

    thread.notifier.connect(
        thread.notifier, QtCore.SIGNAL('done()'), process_result)
    QtCore.QThreadPool.globalInstance().start(thread)

    return thread


opts = {}
ao(opts, 'dataPath', 'String', '', _('Profile source'))
ao(opts, 'startTime', 'Float', 0, _('Start time'), min=0, max=36000, unit='second')
ao(opts, 'endTime', 'Float', -1, _('End time'), min=-1, max=36000, unit='second')
ao(opts, 'maxLayers', 'Integer', 500, _('Max layers'), max=2000, min=10)
ao(opts, 'cut', 'Integer', 0, _('Remove points from start/end'), min=0, step=1)
ao(opts, 'animation', 'Float', 0, _('Animation'), min=0, step=1, unit='second')
ao(opts, 'reset', 'Boolean', False, _('Reset scene'))


class ColorMapLegend(QtGui.QWidget):
    levels = 10

    def __init__(self, low=0, high=1, parent=None):
        super(ColorMapLegend, self).__init__(parent=parent)
        self.labels = []
        self.colors = []
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.clrmp = clrmp
        self.low = low
        self.high = high
        self.delta = high - low

    def set_range(self, low, high):
        self.low = low
        self.high = high
        self.delta = high - low
        d = self.delta / (self.levels - 1)

        for i in range(self.levels):
            if i > len(self.labels) - 1:
                lbl = QtGui.QLabel()
                self.labels.append(lbl)
                self.lay.addWidget(lbl)
            lbl = self.labels[i]
            cur = low + d * i
            lbl.setText('{:.0f}'.format(cur))
            f0 = 1. * i / self.levels
            c = self.clrmp.mapToQColor(f0)
            c1 = 'white' if f0 < 0.5 else 'black'

            lbl.setStyleSheet(
                "background-color: {}; color: {};".format(c.name(), c1))

        # Remove excess labels if any
        for i in range(self.levels - len(self.labels)):
            lbl = self.labels[i + self.levels]
            lbl.hide()
            lbl.deleteLater()


# TODO: add startTemp, endTemp and update one/another as a function
# TODO: display colormap legend
class ExtrusionRender(QtGui.QWidget):
    render_thread = False
    render_widget = False

    def __init__(self, shared_file, data_path, parent=None):
        super(ExtrusionRender, self).__init__(parent=parent)
        self.setWindowTitle(_('3D Sample Profile Extrusion'))
        self.shared_file = shared_file
        self.timer = QtCore.QTimer()
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        ropts = deepcopy(opts)
        ropts['dataPath']['current'] = data_path
        self.cfg = ConfigurationProxy({'self': ropts})
        self.cfg.callbacks_set = set([self.set_limits])
        self.wg = conf.Interface(self.cfg, self.cfg, opts)
        self.labelT = QtGui.QLabel()
        self.btn_ok = QtGui.QPushButton(_('Render'))
        self.legend = ColorMapLegend()
        self.left_lay = self.wg.sectionsMap['Main'].layout()
        self.left_lay.addWidget(self.labelT)
        self.left_lay.addWidget(self.legend)
        self.left_lay.layout().addWidget(self.btn_ok)
        self.left_lay.layout().addStretch()
        self.wg.setSizePolicy(QtGui.QSizePolicy.Minimum,
                              QtGui.QSizePolicy.Preferred)
        self.wg.setMaximumWidth(300)
        self.lay.addWidget(self.wg)
        self.btn_ok.clicked.connect(self.refresh)
        self.set_limits()

    def set_limits(self, cfg=None, key=None, old=None, new=None):
        data_path = self.cfg['dataPath'].split(':')[-1]
        if not data_path.startswith('/'):
            data_path = '/' + data_path
        self.ref_profile = get_node_reference(self.shared_file, data_path)
        T = '/'.join(data_path.split('/')[:-1]) + '/T'
        self.ref_T = get_node_reference(self.shared_file, T)

        mintime = self.ref_profile[0][0]
        maxtime = self.ref_profile[-1][0]
        
        st = self.cfg['startTime']
        et = self.cfg['endTime']
        if key == 'endTime':
            et = new
        elif key == 'startTime':
            st = new
        if et<0:
            et = maxtime
            
        if key!='endTime':
            self.cfg['endTime'] = et
            
        self.cfg.setattr('startTime', 'min', mintime)
        self.cfg.setattr('startTime', 'max', et)
        self.wg.widgetsMap['startTime'].update_option()
        self.wg.widgetsMap['startTime'].changed_option()
        self.cfg.setattr('endTime', 'max', maxtime)
        
        self.wg.widgetsMap['endTime'].update_option()
        self.wg.widgetsMap['endTime'].changed_option()

        i = 0
        if st > 0:
            i = self.ref_T.get_time(st)
        t0, T0 = self.ref_T[i]
        i = -1
        if et > st:
            i = self.ref_T.get_time(et)
        t1, T1 = self.ref_T[i]
        self.labelT.setText(
            u'Temperature range:\n {:.1f}°C - {:.1f}°C'.format(T0, T1))
        return new
    
    refreshing = False
    def refresh(self):
        if self.refreshing:
            return False
        self.timer.stop()
        self.refreshing = True
        config = self.cfg.asdict()
        config.pop('dataPath')
        config.pop('reset')
        config.pop('animation')
        self.render_thread = deferred_extrusion(
            self.ref_profile, self.ref_T, config,
            jobs=registry.tasks.jobs,
            job=registry.tasks.job,
            done=registry.tasks.done )
        self.render_thread.connect(self.render_thread.notifier,
                                   QtCore.SIGNAL('widget_ready()'),
                                   self.replace_widget)
        self.set_limits()

    def replace_widget(self):
        opts = {}
        if self.render_widget and self.render_widget.isVisible():
            opts = self.render_widget.opts
            self.render_widget.hide()
            self.render_widget.deleteLater()
        
        self.render_widget = gl.GLViewWidget()
        if not self.cfg['animation']:
            map(self.render_widget.addItem, self.render_thread.objects)
        else:
            self.animate()
        # self.render_widget.show()
        self.render_widget.setMinimumWidth(800)
        self.render_widget.setMinimumHeight(600)
        self.render_widget.setSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        self.lay.addWidget(self.render_widget)
        minT, maxT = self.render_thread.result[-2:]
        self.labelT.setText(
            u'Temperature range:\n {:.1f}°C - {:.1f}°C'.format(minT, maxT))
        self.legend.set_range(minT, maxT)
        if opts and not self.cfg['reset']:
            self.render_widget.setCameraPosition(distance=opts['distance'],
                                                 elevation=opts['elevation'],
                                                 azimuth=opts['azimuth'])
            c = opts['center']
            self.render_widget.pan(c.x(), c.y(), c.z(), relative=False)
        
        self.refreshing = False
        
    def _addItem(self):
        if not len(self.render_thread.objects):
            self.timer.stop()
        else:
            self.render_widget.addItem(self.render_thread.objects.pop(0))  
                  
    def animate(self):
        dt = int(self.cfg['animation']*1000./len(self.render_thread.objects))
        if dt==0:
            dt=1
        self.timer.timeout.connect(self._addItem)
        self.timer.start(dt)
        


if __name__ == '__main__':
    test_path = '/home/daniele/MisuraData/hsm/BORAX powder 10 C min.h5'
    data_path = '/hsm/sample0/profile'
    #test_path = '/home/daniele/MisuraData/horizontal/profiles/System Interbau 80 1400.h5'
    #data_path = '/horizontal/sample0/Right/profile'
    app = pg.QtGui.QApplication([])
    from misura.canon.indexer import SharedFile
    f = SharedFile(test_path)
    w = ExtrusionRender(f, data_path)
    #w = extrude(f, data_path)
    w.show()
    pg.QtGui.QApplication.exec_()
