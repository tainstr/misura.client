#!/usr/bin/python
# -*- coding: utf-8 -*-
"""A point connected to an xy plot."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.widgets
import veusz.document as document
import veusz.setting as setting
import numpy as np
import copy
import utils


def translateCoord(ax, vc):
    return [ax.plottedrange[0] + c * (ax.plottedrange[1] - ax.plottedrange[0]) for c in vc]


class SynAxis(utils.OperationWrapper, veusz.widgets.Axis):
    typename = 'synaxis'
    description = 'Synchronizing Axis'
    allowusercreation = True
    ncurves = 3
    """Enable this number of curves"""

    def __init__(self, parent, name=None):
        veusz.widgets.Axis.__init__(self, parent, name=name)

        self.addAction(veusz.widgets.widget.Action('up', self.actionUp,
                                                   descr='Update Synchronizing Axis',
                                                   usertext='Update Synchronizing Axis'))

        self.addAction(veusz.widgets.widget.Action('restore', self.actionRestore,
                                                   descr='Restore',
                                                   usertext='Restore'))

        self.settings.direction = 'vertical'
        self.settings.TickLabels.hide = True
        self.settings.MajorTicks.hide = True
        self.settings.MinorTicks.hide = True
        self.trcum = {}
        """Cumulative translations map"""
        # TODO: enable restore also for Axis translations by recovering
        # original axis coupling
        self.axmap = {}  # curve:(newax,oldax,(min,max))
        """Added axes map"""

    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        veusz.widgets.Axis.addSettings(s)
        s.add(setting.Choice(
            'trans', ['Axis', 'Values'], 'Axis',
            descr='Translation mode',
            usertext='Translation mode',),
            2)
        s.add(setting.WidgetChoice(
            'curve0', '',
            descr='Reference curve',
            widgettypes=('xy',),
            usertext='Reference curve'),
            3)
        for i in range(klass.ncurves):
            u = str(i + 1)
            s.add(setting.WidgetChoice(
                'curve' + u, '',
                descr='Sync curve ' + u,
                widgettypes=('xy',),
                usertext='Sync curve ' + u),
                i + 4)

    @property
    def doc(self):
        return self.document

    def actionUp(self):
        logging.debug('%s', 'SYNC LINE UP')
        self.ops = []
        doc = self.document
        ref = None  # Reference curve is the first child
        xref = []
        yref = []
        # Fractional position on x axis
        apos = self.settings.otherPosition
        # Translation mode
        trmode = self.settings.trans
        # Maximum translations
        up_ext = 0
        down_ext = 0
        axmap = {}
        objmap = {}
        # Search for all curves in parent graph
        for i in range(self.ncurves):
            u = 'curve' + str(i)
            uc = getattr(self.settings, u)
            obj = self.parent.getChild(uc)
            if obj is None:
                if i == 0:
                    logging.debug('%s', 'No reference curve defined')
                    return
                break
            xax = self.parent.getChild(obj.settings.xAxis)
            # Get the y axis
            yax = self.parent.getChild(obj.settings.yAxis)
            if None in [xax, yax]:
                continue
            # Obtain real position relative to xax
            pos = apos * \
                (xax.plottedrange[1] - xax.plottedrange[0]) + \
                xax.plottedrange[0]
            # Set reference values
            if ref is None:
                ref = obj
                xref = doc.data[ref.settings.xData].data
                yref = doc.data[ref.settings.yData].data
                yaxref = yax
                # Reference ranges
                ymin_ref, ymax_ref = yaxref.plottedrange
                # Search the nearest X value on ref X-array
                dst = np.abs(xref - pos)
                i = np.where(dst == dst.min())[0][0]
                # Get the corresponding Y value on the ref Y-array
                yval_ref = yref[i]
                axmap[yax.name] = obj
                objmap[obj] = (yax, 0)
                continue

            # Getting curve data
            xtr = doc.data[obj.settings.xData].data
            yds_name = obj.settings.yData
            yds = doc.data[yds_name]
            ytr = yds.data
            # Search the nearest X value on trans X-array
            dst = np.abs(xtr - pos)
            i = np.where(dst == dst.min())[0][0]
            # Delta
            d = ytr[i] - yval_ref
            objmap[obj] = (yax, d)
            # Create axes - only for axis translation
            if trmode == 'Values':
                new = yds.data - d
                # Create a copy of the dataset
                ydsn = copy.copy(yds)
                # Change copy's values
                ydsn.data = new
                # Set original dataset to copied one
                op = document.OperationDatasetSet(yds_name, ydsn)
                self.ops.append(op)
                # Remember translation
                if not self.trcum.has_key(obj.path):
                    self.trcum[obj.path] = 0
                self.trcum[obj.path] += d
                continue

            # Remember for future translation
            if ytr.min() < ymin_ref:
                ymin_ref = ytr.min()
            if ytr.max() > ymax_ref:
                ymax_ref = ytr.max()

            # Each Y axis MUST be unique.
            # Create new one if current obj happens to share its axis with a
            # previous one
            if axmap.has_key(yax.name):
                axname = 'ax_%s_%s' % (obj.name, self.name)
                axset = {'name': axname, 'direction': 'vertical', 'label': 'Trans:' + yax.settings.label,
                         'hide': False}  # will be True! don't want to see all that axes
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'axis', **axset))
                self.toset(obj, 'yAxis', axname)
                axmap[axname] = obj
                self.axmap[obj.path] = (
                    axname, yax.name, (yax.settings.min, yax.settings.max))
# 			else:
# 				self.axmap[obj.path]=(yax.name,yax.name,(yax.settings.min,yax.settings.max))

        if trmode == 'Values':
            # Remove dissociated objects
            ucs = set([obj.path for obj in objmap.keys()])
            for uc in set(self.trcum.keys()) - ucs:
                del self.trcum[uc]
            self.apply_ops('SynAxis: Translation')
            return

        # Remove unused restore info
        ucs = set([obj.path for obj in objmap.keys()])
        for uc in set(self.axmap.keys()) - ucs:
            del self.axmap[uc]

        self.trcum = {}
        # Apply axis creation
        self.apply_ops('SynAxis: Create')
        # Extend axes and apply translations
        self.toset(yaxref, 'max', float(ymax_ref))
        self.toset(yaxref, 'min', float(ymin_ref))
        for obj, (yax, d) in objmap.iteritems():
            self.toset(yax, 'max', float(ymax_ref + d))
            self.toset(yax, 'min', float(ymin_ref + d))

        self.apply_ops('SynAxis: Update')

    def actionRestore(self):
        """Restore dataset translated by values"""
        for uc, d in self.trcum.iteritems():
            obj = self.document.resolveFullWidgetPath(uc)
            logging.debug('%s %s %s %s', 'restoring curve', uc, d, obj)
            yds_name = obj.settings.yData
            yds = self.document.data[yds_name]
            new = yds.data + d
            # Create a copy of the dataset
            ydsn = copy.copy(yds)
            # Change copy's values
            ydsn.data = new
            # Set original dataset to copied one
            op = document.OperationDatasetSet(yds_name, ydsn)
            self.ops.append(op)
        logging.debug('%s %s', 'axmap', self.axmap)
        for uc, (newax, oldax, (minVal, maxVal)) in self.axmap.iteritems():
            obj = self.document.resolveFullWidgetPath(uc)
            self.toset(obj, 'yAxis', oldax)
            ox = self.parent.getChild(oldax)
            self.toset(ox, 'min', minVal)
            self.toset(ox, 'max', minVal)

            if newax != oldax:
                n = self.parent.getChild(newax)
                op = document.OperationWidgetDelete(n)
                self.ops.append(op)

        self.trcum = {}
        self.axmap = {}
        self.apply_ops('SynAxis: Restore')

    def updateControlItem(self, cgi):
        """If control items are moved, update line."""
        # Call the line method
        veusz.widgets.Axis.updateControlItem(self, cgi)
        self.actionUp()


document.thefactory.register(SynAxis)
