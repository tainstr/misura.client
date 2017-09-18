from .. import _
from .. import widgets

from PyQt4 import QtGui

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
    if instrument['devpath'] in ['horizontal', 'vertical', 'flex']:
        val, st = QtGui.QInputDialog.getDouble(parent, _("Confirm initial sample dimension"),
                                               _("Initial dimension (micron)"),
                                               instrument.sample0['initialDimension'])
        if not st:
            return False
        instrument.sample0['initialDimension'] = val
    return True
   
        

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
        self.btn_cancel = QtGui.QPushButton(_('Cancel'))
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setFocus(False)
        self.btn_start = QtGui.QPushButton(_('Start'))
        
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_start.clicked.connect(self.start)
        
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.table)
        self.layout().addWidget(self.btn_update)
        self.layout().addWidget(self.btn_cancel)
        self.layout().addWidget(self.btn_start)
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
            
        