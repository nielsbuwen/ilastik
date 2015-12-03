from PyQt4.QtGui import QWidget
from PyQt4.uic import loadUiType
from PyQt4.QtCore import pyqtSignal, Qt
from os.path import split
from ilastik.shell.gui.ipcManager import Loopback


class LoopbackInfoWidget(QWidget):
    """
    Displays the options for the Loopback module
    """
    UI_FILE = "/loopbackInfoWidget.ui"

    optionsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(LoopbackInfoWidget, self).__init__(parent)

        ui_class, _ = loadUiType(split(__file__)[0] + self.UI_FILE)
        self.ui = ui_class()
        self.ui.setupUi(self)

        self.ui.hilite.stateChanged.connect(self.optionsChanged)
        self.ui.unhilite.stateChanged.connect(self.optionsChanged)
        self.ui.clear.stateChanged.connect(self.optionsChanged)

    @property
    def loopbacks(self):
        if self.ui.hilite.checkState() == Qt.Checked:
            yield Loopback.hilite
        if self.ui.unhilite.checkState() == Qt.Checked:
            yield Loopback.unhilite
        if self.ui.clear.checkState() == Qt.Checked:
            yield Loopback.clear

    def add_sent_command(self, *_):
        pass  # no logging here
