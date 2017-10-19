from .. import _
from .. import widgets

from PyQt4 import QtGui
from misura.canon import option
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)



class StartedFinishedNotification():

    def __init__(self, parent, signal_to_emit_if_started):
        self.started_set = set()
        self.finished_messages_shown_set = set()
        self.parent = parent
        self.signal_to_emit_if_started = signal_to_emit_if_started

    def show(self, isRunning, remote_is_running, uid):
        if isRunning is not None and isRunning != remote_is_running:
            if remote_is_running and uid not in self.started_set:
                self.started_set.add(uid)
                self._show_message(_('A new test was started'))
                self.signal_to_emit_if_started.emit()
            elif uid not in self.finished_messages_shown_set:
                self.finished_messages_shown_set.add(uid)
                self._show_message(_('Finished test'))

    def _show_message(self, message):
        QtGui.QMessageBox.warning(self.parent, message, message)


def initial_sample_dimension(instrument, parent=None):
    """Show a confirmation dialog immediately before starting a new test"""
    # TODO: generalize
    opts = 0
    wg = QtGui.QWidget()
    wg.setLayout(QtGui.QGridLayout())
    root = instrument.root
    # Check measurement name
    m = instrument['mro'][0]
    if instrument.measure['name'] in ['measure', m]:
        w = widgets.build(root, 
                      instrument.measure, 
                      instrument.measure.gete('name'))
        wg.layout().addWidget(w.label_widget, opts, 0)
        wg.layout().addWidget(w, opts, 1)        
        opts += 1
    # Check initial dimension
    if instrument['devpath'] in ['horizontal', 'vertical', 'flex']:
        w = widgets.build(root, 
                      instrument.sample0, 
                      instrument.sample0.gete('initialDimension'))
        wg.layout().addWidget(w.label_widget, opts, 0)
        wg.layout().addWidget(w, opts, 1)
        opts += 1
        
    if not opts:
        return True
    
    label = QtGui.QLabel(_('Please review these important configurations:'))
    dia, btn_start, btn_cancel = create_widgets_dialog([label, wg])
    dia.setWindowTitle(_('Review test configuration'))
    btn_start.clicked.connect(dia.accept)
    btn_start.setDefault(True)
    btn_start.setFocus(True)
    btn_cancel.clicked.connect(dia.reject)
    if dia.exec_():
        return True
    return False
   

def create_widgets_dialog(widget_list, dia=False):
    if dia is False:
        dia = QtGui.QDialog()
    dia.setLayout(QtGui.QVBoxLayout())
    for wg in widget_list:
        dia.layout().addWidget(wg)
    
    btn_cancel = QtGui.QPushButton(_('Cancel'))
    btn_cancel.setDefault(False)
    btn_cancel.setFocus(False)
    btn_start = QtGui.QPushButton(_('Start test'))    
    dia.layout().addWidget(btn_cancel)
    dia.layout().addWidget(btn_start)
    
    return dia, btn_start, btn_cancel

class ValidationDialog(QtGui.QDialog):
    def __init__(self, server, parent=None):
        super(ValidationDialog, self).__init__(parent)
        self.setWindowTitle(_('Review and confirm'))
        self.setMinimumWidth(400)
        self.server = server
        
        opt = self.server.gete('validate')
        opt['attr'].remove('Hidden')
        self.table = widgets.build(server, server, opt)
        self.label = QtGui.QLabel(_('A new test will start. Do you confirm?'))
        
        self.btn_update = QtGui.QPushButton(_('Update'))
        self.btn_update.clicked.connect(self.update)
        
        
        foo, self.btn_start, self.btn_cancel = create_widgets_dialog([self.label, 
                                                            self.table, 
                                                            self.btn_update], 
                                                           dia=self)
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_start.clicked.connect(self.start)
        
        self.update()

    def update(self):
        self.table.update()
        vals = self.server['validate'][1:]
        rows = []
        ok = True
        
        for (status, msg, path) in self.table.current[1:]:
            ok = ok*status
            
        # Default button
        self.btn_start.setDefault(ok)
        self.btn_start.setFocus(ok)
        # Hide unrelevant buttons
        if len(vals):
            self.table.show()
            self.btn_update.show()
            self.btn_update.setDefault(not ok)
            self.btn_update.setFocus(not ok)
        else:
            self.table.hide()
            self.btn_update.hide()
            
        self.btn_start.setEnabled(ok) 
        return ok
        
    def start(self):
        if self.update():
            self.accept()
        else:
            logging.error('Cannot start: validation failed!')
            
        