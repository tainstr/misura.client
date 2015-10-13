#!/usr/bin/python
# -*- coding: utf-8 -*-
"""A point connected to an xy plot."""
from misura.canon.logger import Log as logging
from PyQt4 import QtGui
import veusz.utils
import veusz.widgets
import veusz.document as document
import veusz.setting as setting
import numpy as np
from scipy import interpolate
import utils
from ...canon import csutil
from misura.client.plugin.RemoveGaps import remove_gaps_from
from copy import copy


def searchWidgetName(widget, name):
    # get parent widget
    while not widget.isWidget() and widget is not None:
        widget = widget.parent

    while widget is not None:
        for w in widget.children:
            if w.name == name:
                return w
        widget = widget.parent
    return None


class DataPoint(utils.OperationWrapper, veusz.widgets.BoxShape):
    typename = 'datapoint'
    description = 'Data Point'
    allowusercreation = True

    def __init__(self, parent, name=None):
        veusz.widgets.BoxShape.__init__(self, parent, name=name)

        self.addAction(veusz.widgets.widget.Action('up', self.actionUp,
                                                   descr='Update Data Point',
                                                   usertext='Update Data Point'))

        self.addAction(veusz.widgets.widget.Action('removeGaps', self.removeGaps,
                                                   descr='Remove Gaps',
                                                   usertext='Remove Gaps'))

        self.labelwidget = None

    def removeGaps(self):
        gap_range = self.settings.setdict['remove_gaps_range'].val
        gaps_thershold = self.settings.setdict['remove_gaps_thershold'].val
        start_index = int(round(self.i - gap_range / 2.0))
        end_index = start_index + gap_range
        data = self.xy.settings.get('yData').getFloatArray(self.document)
        dataset_name = self.xy.settings.get('yData').val
        dataset = copy(self.document.data[dataset_name])
        data_without_gap = remove_gaps_from(data, gaps_thershold, start_index, end_index)

        dataset.data = data_without_gap
        operation = document.OperationDatasetSet(dataset_name, dataset)

        self.ops.append(operation)
        self.up_coord(yData = data_without_gap)

        self.apply_ops('Remove Gap')








    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        veusz.widgets.BoxShape.addSettings(s)

        s.add(setting.Float(
            'remove_gaps_range', 100,
            descr = "Remove gaps range",
            usertext = "Remove gaps range"),
            1)

        s.add(setting.Float(
            'remove_gaps_thershold', 10,
            descr = "Remove gaps thershold",
            usertext = "Remove gaps thershold"),
            2
            )

        s.add(setting.WidgetChoice(
            'xy', '',
            descr='Curve this point is attached to.',
            widgettypes=('xy',),
            usertext='XY Reference'),
            3)

        s.add(setting.ChoiceSwitch(
            'search', ['None', 'Maximum', 'Minimum',
                       'Inflection', 'Stationary'], 'None',
            settingstrue=['searchRange'], settingsfalse=[], showfn=lambda val: val != 'None',
            descr='Search nearest critical point',
            usertext='Search nearest'),
            4)
        s.add(setting.Float(
            'searchRange', 10,
            descr='Critical search range',
            usertext='Search range'),
            5)

        s.add(setting.WidgetChoice(
            'secondPoint', '',
            descr='Second Data Point for passing-through line placement.',
            widgettypes=('datapoint',),
            usertext='Second Data Point'),
            6)
        s.add(setting.WidgetChoice(
            'pt2ptLine', '',
            descr='Dispose this line as passing through this and second data point.',
            widgettypes=('line',),
            usertext='Passing-through Line'),
            7)

        # OVERRIDES
        n = setting.Choice('positioning',
                           ['axes'], 'axes',
                           descr='Axes positioning',
                           usertext='Position mode',
                           formatting=False)
        n.parent = s
        s.setdict['positioning'] = n

        n = setting.DatasetExtended('width', [0.04],
                                    descr='List of fractional widths or dataset',
                                    usertext='Widths',
                                    formatting=False)
        n.parent = s
        s.setdict['width'] = n
        n = setting.DatasetExtended('height', [0.04],
                                    descr='List of fractional heights or dataset',
                                    usertext='Heights',
                                    formatting=False)
        n.parent = s
        s.setdict['height'] = n

        # FORMATTING
        s.add(setting.Marker('marker',
                             'linecross',
                             descr='Type of marker to plot',
                             usertext='Marker', formatting=True), 0)

        s.add(setting.BoolSwitch('showLabel', True,
                                 descr='Show Label',
                                 usertext='Show Label',
                                 settingstrue=['labelText', 'coordLabel'],
                                 formatting=True),
              1)
        s.add(setting.Str(
            'labelText', '%(xlabel)s=%(x)i \\\\%(ylabel)s=%(y)E',
            descr='Output label text',
            usertext='Output label text',
            formatting=True),
            2)
        s.add(setting.WidgetChoice(
            'coordLabel', '',
            descr='Write coordinates to this label.',
            widgettypes=('label',),
            usertext='Coord. label',
            formatting=True),
            3)

        s.add(setting.BoolSwitch('showTangent', False,
                                 descr='Show Tangent',
                                 usertext='Show tangent line',
                                 settingstrue=['tangentLine'],
                                 formatting=True),
              4)
        s.add(setting.WidgetChoice(
            'tangentLine', '',
            descr='Dispose this line as tangent to curve xy.',
            widgettypes=('line',),
            usertext='Tangent Line',
            formatting=True),
            5)

        s.add(setting.BoolSwitch('showPerpendicular', False,
                                 descr='Show Perpend.',
                                 usertext='Show perpendicular line',
                                 settingstrue=['perpendicularLine'],
                                 formatting=True),
              6)
        s.add(setting.WidgetChoice(
            'perpendicularLine', '',
            descr='Dispose this line as perpendicular to curve xy.',
            widgettypes=('line',),
            usertext='Perpendicular Line',
            formatting=True),
            7)

    def drawShape(self, painter, rect):
        s = self.settings
        h = 1 + min((rect.width(), rect.height())) / 3
        path, enablefill = veusz.utils.getPainterPath(painter, s.marker, h)
        veusz.utils.brushExtFillPath(
            painter, s.Fill, path, stroke=painter.pen())

    def check_axis(self):
        aligned = self.toset(self, 'positioning', 'axes')
        aligned = aligned and self.eqset(self.xy, 'xAxis')
        aligned = aligned and self.eqset(self.xy, 'yAxis')

        # Styling
        self.toset(self, 'Border/color', self.xy.settings.PlotLine.color)
        self.toset(self, 'Border/style', self.xy.settings.PlotLine.style)

        return aligned

    def actionUp(self, oldx=None, oldy=None):
        logging.debug('%s', 'ACTION UP')

        d = self.document
        self.doc = d
        s = self.settings
        self.ops = []

        xy = s.get('xy').findWidget()
        if xy is None:
            logging.debug('%s', 'No xy widget was defined!')
            return False
        self.xy = xy

        # Settings coerence
        aligned = self.check_axis()
        if not aligned:
            self.apply_ops('DataPoint: Align')

        aligned = self.check_axis()
        if not aligned:
            logging.debug('%s', 'Impossible to align DataPoint settings')
            return False
        self.dependencies()
        self.up_coord(oldx, oldy)
        self._tg_ang = None
        self.up_tangent()
        self.up_perpendicular()
        self.up_passing()
        self.updateOutputLabel()
        self.apply_ops('DataPoint: Up')
        return True

    def dependencies(self):
        """Create/destroy dependent widgets"""
        s = self.settings
        # Tangent
        tg = s.get('tangentLine').findWidget()
        if tg is None:
            logging.debug('%s', 'No tangent line specified')
            if s.showTangent:
                name = 'tg_' + self.name
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'line', name=name))
                self.toset(self, 'tangentLine', name)
        # Destroy if not needed
        elif not s.showTangent:
            self.ops.append(document.OperationWidgetDelete(tg))

        # Perpendicular
        tg = s.get('perpendicularLine').findWidget()
        if tg is None:
            logging.debug('%s', 'No pp line specified')
            if s.showTangent:
                name = 'pp_' + self.name
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'line', name=name))
                self.toset(self, 'perpendicularLine', name)
        # Destroy if not needed
        elif not s.showPerpendicular:
            self.ops.append(document.OperationWidgetDelete(tg))

        # PT2PT
        tg = s.get('pt2ptLine').findWidget()
        p2 = s.get('secondPoint').findWidget()
        if tg is None:
            logging.debug('%s', 'No p2p line specified')

            if p2 is not None:
                name = 'p2p_%s_%s' % (self.name, p2.name)
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'line', name=name))
                self.toset(self, 'pt2ptLine', name)
        # Destroy if not needed
        elif p2 is None:
            self.ops.append(document.OperationWidgetDelete(tg))

        # Label
        labelwidget = s.get('coordLabel').findWidget()
        if labelwidget is None:
            if s.showLabel:
                name = 'lbl_' + self.name
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'label', name=name))
                self.toset(self, 'coordLabel', name)
        # Destroy if no longer needed
        elif labelwidget and not s.showLabel:
            self.ops.append(document.OperationWidgetDelete(labelwidget))

        self.apply_ops('Datapoint: Dependencies')

    def distance(self, x, y, xData=None, yData=None, xRange=None, yRange=None):
        """Curve-point distance"""
        if xData is None:
            xData = self.xData
        if yData is None:
            yData = self.yData
        if xRange is None:
            xRange = self.xRange
        if yRange is None:
            yRange = self.yRange
        dst = ((xData - x) / xRange)**2 + ((yData - y) / yRange)**2
        i = np.where(dst == dst.min())[0][0]
        return i, xData[i], yData[i]

    def up_coord(self, oldx=None, oldy=None, xData=None, yData=None):
        """Place in the nearest point to the current x,y coord"""
        d = self.document
        s = self.settings
        xSet = self.xy.settings.get('xData')
        ySet = self.xy.settings.get('yData')

        if (xData is None):
            xData = xSet.getFloatArray(d)
        if (yData is None):
            yData = ySet.getFloatArray(d)
        N = len(xData)

        # Compute visible ranges
        xAx = searchWidgetName(s.parent, s.xAxis)
        yAx = searchWidgetName(s.parent, s.yAxis)
        if None in [xAx, yAx]:
            return False
        m = lambda v, alt: v if v != 'Auto' else alt
        xMax = m(xAx.settings.max, xData.max())
        xMin = m(xAx.settings.min, xData.min())
        xRange = xMax - xMin
        yMax = m(yAx.settings.max, yData.max())
        yMin = m(yAx.settings.min, yData.min())
        yRange = yMax - yMin

        # Calc new coord
        ox_set = s.get('xPos')
        oy_set = s.get('yPos')
        if oldx is None:
            oldx = ox_set.get()
        if oldy is None:
            oldy = oy_set.get()

        if 0 in [xRange, yRange]:
            logging.debug(
                '%s %s %s', 'ERROR: Datapoint divide for ranges', xRange, yRange)
            return

        # Store values in class attributes in order for other methods to find
        # them
        self.xData = xData
        self.yData = yData
        self.xRange = xRange
        self.yRange = yRange
        self.N = N
        # Curve-curve distance
        self.i, self.x, self.y = self.distance(oldx, oldy)

        self.xMax = xMax
        self.xMin = xMin
        self.yMax = yMax
        self.yMin = yMin
        self.xAx = xAx
        self.yAx = yAx

        # perform nearest critical point search
        self.critical_search()  # may update self.x, self.y, self.i
        self.ops.append(document.OperationSettingSet(ox_set, float(self.x)))
        self.ops.append(document.OperationSettingSet(oy_set, float(self.y)))
        return True

    def critical_search(self):
        """Search for critical points in curve"""
        src = self.settings.search
        if src == 'None':
            logging.debug('%s', 'No search defined')
            return False
        # Calculate slice
        rg = self.settings.searchRange / 2.

        x, xd, err = utils.rectify(self.xData)
        xm, ym = x, self.yData

        iL = None
        iR = None
        if rg > 0:
            i1 = self.i
            xmi = xm[i1]
            logging.debug('%s %s %s %s', 'searching', xmi, i1, rg)
            iL = csutil.find_nearest_val(xm, xmi - rg, seed=i1)
            iR = csutil.find_nearest_val(xm, xmi + rg, seed=i1)

        sl = slice(iL, iR)
        logging.debug('%s %s %s', 'Slicing', iL, iR)

        def result(i):
            """Set result"""
            s = 0
            if sl.start:
                s = sl.start
            i += s
            self.i = i
            self.x = self.xData[self.i]
            self.y = self.yData[self.i]
            logging.debug(
                '%s %s %s %s %s', 'result', src, self.i, self.x, self.y)

        if src in ('Maximum', 'Minimum'):
            # Compute x range
            f = max if src == 'Maximum' else min
            y = f(ym[sl])
            i = np.where(ym[sl] == y)[0][0]
            result(i)
            return True

        r = []
        xm1 = xm[sl]
        ym1 = ym[sl]
        step = int(min(50, len(xm1) / 3.) + 1)
        if src == 'Stationary':
            sp = interpolate.LSQUnivariateSpline(
                xm1, ym1, xm1[step:-step:step], k=4)
            r = sp.derivative(1).roots()
        elif src == 'Inflection':
            sp = interpolate.LSQUnivariateSpline(
                xm1, ym1, xm1[step:-step:step], k=5)
            r = sp.derivative(2).roots()
        if len(r) == 0:
            logging.debug('%s %s', 'NO CRITICAL POINTS FOUND', src)
            return False
        logging.debug('%s %s %s', 'CRITICAL POINTS', src, r)
        logging.debug('%s %s', 'xm1', xm1)
        # Find the nearest root
        rr = abs(r - self.x)
        ri = np.where(rr == min(rr))[0][0]
        # Find nearest to root value in curve
        r = abs(xm[sl] - r[ri])
        i = np.where(r == min(r))[0][0]
        result(i)
        return True

    _tg_ang = None

    @property
    def tg_ang(self):
        """Calculate the tangent angle in current point"""
        # use one-tenth of available points
        if self._tg_ang is not None:
            return self._tg_ang
        n = 6
        if n < 3:
            logging.debug(
                '%s', 'Too few points in order to calculate the tangent line')
            self._tg_ang = None
            return None
        # Select a sequence of points around datapoint. Translate to the dp is
        # the origin.
        left = slice(max(self.i - n, 0), self.i)
        right = slice(self.i + 1, min(self.i + n, self.N - 1))
        vx = np.concatenate((self.xData[left], self.xData[right]))
        vy = np.concatenate((self.yData[left], self.yData[right]))
        vx -= self.x
        vy -= self.y
        logging.debug('%s %s', 'vx', vx)
        logging.debug('%s %s', 'vy', vy)
        # Angle as a mean of arctan2 values (avoid zero-denominator problems)

        self._tg_ang = np.arctan(vy / vx).mean()
        return self._tg_ang

    def check_point(self, pt, name=False):
        """Check point settings coherence"""
        aligned = self.toset(pt, 'positioning', 'axes')
        aligned = aligned and self.cpset(self, pt, 'xAxis')
        aligned = aligned and self.cpset(self, pt, 'yAxis')
        if name:
            self.toset(pt, name, self.name)
            self.cpset(self, pt, 'xy')
            self.cpset(self, pt, 'xAxis')
            self.cpset(self, pt, 'yAxis')
        return aligned

    def check_line(self, ln, mode='point-to-point'):
        """Check line settings coherence"""
        aligned = self.check_point(ln)
        aligned = aligned and self.toset(ln, 'mode', mode)
        return aligned

    def line_points(self, line, ang):
        """Get delta x,y for positioning a line passing through datapoint with `ang`"""
        # Check settings coherence
        aligned = self.check_line(line)

        c = np.cos(ang)
        s = np.sin(ang)

        if aligned:
            dx = (line.settings.xPos2[0] - line.settings.xPos[0])
            dy = (line.settings.yPos2[0] - line.settings.yPos[0])
            ang0 = np.arctan2(dy, dx)
            L = np.sqrt(dx**2 + dy**2)
            # Rotate the length in order to maintain the same apparent length
            c2 = c**2
            s2 = s**2
            c02 = np.cos(ang0)**2
            s02 = np.sin(ang0)**2
            xR2 = self.xRange**2
            yR2 = self.yRange**2
            dn = (L**2) * (xR2 * s02 + yR2 * c02)
            nr = (xR2 * s2 + yR2 * c2)
            L = np.sqrt(dn / nr)
            logging.debug('%s %s', 'convL', L)
        else:
            L = np.sqrt(self.xRange**2 + self.yRange**2) / 2

        logging.debug('%s %s %s %s', 'preL', L, c, s)

        logging.debug('%s %s %s', 'ranges', self.xRange, self.yRange)
        logging.debug(
            '%s %s %s', 'rangesL', self.xRange / abs(c), self.yRange / abs(s))
        # Scale the length inside graph margins
        if c != 0:
            L = min(L, self.xRange / abs(c))
        if s != 0:
            L = min(L, self.yRange / abs(s))

        xL = 0.5 * c * L
        yL = 0.5 * s * L

        logging.debug('%s %s %s %s %s %s %s %s %s', line.name,
                      'L', L, 'xL', xL, 'yL', yL, 'angle', ang * 180 / np.pi)
        self.toset(line, 'xPos', float(self.x - xL))
        self.toset(line, 'yPos', float(self.y - yL))
        self.toset(line, 'xPos2', float(self.x + xL))
        self.toset(line, 'yPos2', float(self.y + yL))
        return xL, yL, L

    def up_tangent(self):
        """Update tangent line widget position"""
        s = self.settings

        tg = s.get('tangentLine').findWidget()
        if tg is None:
            return
        if self.tg_ang is None:
            return

        xL, yL, L = self.line_points(tg, self.tg_ang)

    def up_perpendicular(self):
        """Update perpendicular line widget position"""
        s = self.settings
        pp = s.get('perpendicularLine').findWidget()
        if pp is None:
            logging.debug('%s', 'No perpendicular line specified')
            return

        if self.tg_ang is None:
            return

        ang = self.tg_ang + (np.pi / 2)
        xL, yL, L = self.line_points(pp, ang)

    def up_passing(self):
        """Update datapoint-to-datapoint line"""
        s = self.settings
        pp = s.get('pt2ptLine').findWidget()
        if pp is None:
            logging.debug('%s', 'No passing line defined')
            return
        pt2 = s.get('secondPoint').findWidget()
        if pt2 is None:
            logging.debug('%s', 'No second point defined')
            return
        aligned = self.check_line(pp)
        aligned = aligned and self.check_point(pt2, name='secondPoint')
        self.cpset(self, pt2, 'pt2ptLine')
        if not aligned:
            logging.debug('%s', 'Point2point references were not aligned')
            return

        self.toset(pp, 'xPos', self.x)
        self.toset(pp, 'yPos', self.y)
        self.toset(pp, 'xPos2', pt2.settings.xPos[0])
        self.toset(pp, 'yPos2', pt2.settings.yPos[0])

    def updateOutputLabel(self):
        """Update output label with the coordinates of the point."""
        s = self.settings
        labelwidget = s.get('coordLabel').findWidget()
        if labelwidget is None:
            return
        txt = s.labelText
        self.labelwidget = labelwidget
        var = {'xlabel': self.xAx.settings.label,
               'ylabel': self.yAx.settings.label,
               'x': self.x,	'y': self.y}
        txt = txt % var
        self.toset(labelwidget, 'label', txt)
        self.toset(labelwidget, 'positioning', 'axes')
        self.cpset(self, labelwidget, 'xAxis')
        self.cpset(self, labelwidget, 'yAxis')
        xsig = 5
        if self.x / self.xRange > 0.7:
            xsig = -15
        ysig = 2
        if self.y / self.yRange > 0.7:
            ysig = -4
        self.toset(labelwidget, 'xPos', self.x + xsig * self.xRange / 100)
        self.toset(labelwidget, 'yPos', self.y + ysig * self.yRange / 100)
        # Styling
        self.toset(labelwidget, 'Text/color', self.xy.settings.PlotLine.color)

    def updateControlItem(self, cgi):
        """If control items are moved, update line."""
        # First do any changes to the datapoint.
        veusz.widgets.BoxShape.updateControlItem(self, cgi)
        # Then re-attach it to the curve
        act = self.actionUp()


document.thefactory.register(DataPoint)
