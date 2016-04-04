from PyQt4 import QtGui
from .. import _

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


def validate_start_acquisition(instrument, parent=None):
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
