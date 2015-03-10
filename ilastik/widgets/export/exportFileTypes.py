from PyQt4.QtGui import QWidget, QMessageBox
from PyQt4 import uic
from PyQt4.QtCore import Qt

from os.path import split as split_path
from operator import mul


class ExportFileTypeWidget(QWidget, object):
    uiFile = None

    def __init__(self, parent=None, raw_size=None, *args, **kwargs):
        super(ExportFileTypeWidget, self).__init__(parent, *args, **kwargs)

        if self.uiFile is None:
            raise RuntimeError("ExportFileTypeWidget need a UI")

        form, _ = uic.loadUiType("{}/{}.ui".format(split_path(__file__)[0], self.uiFile))
        self.ui = form()
        self.ui.setupUi(self)

        self.raw_size = raw_size

    @staticmethod
    def allowed_extensions():
        raise NotImplementedError

    @classmethod
    def default_extension(cls):
        return cls.allowed_extensions()[0]

    @staticmethod
    def filter_string():
        raise NotImplementedError

    @staticmethod
    def display_name():
        raise NotImplementedError

    def export_settings(self):
        raise NotImplementedError


class HDFType(ExportFileTypeWidget):
    uiFile = "hdfSettings"
    rawLayerSizeLimit = 1000000

    def __init__(self, *args, **kwargs):
        super(HDFType, self).__init__(*args, **kwargs)

    @staticmethod
    def allowed_extensions():
        return "h5", "hf5", "hdf5"

    @staticmethod
    def filter_string():
        return "HDF 5 (*.h5 *.hf5 *.hdf5)"

    @staticmethod
    def display_name():
        return "Hierarchical Data Format HDF"

    def export_settings(self):
        return {
            "include raw": self.ui.include_raw.checkState() == Qt.Checked,
            "margin": self.ui.add_margin.value(),
            "normalize": True,
            "compression": {
                "compression": "gzip",
                "shuffle": str(self.ui.enable_shuffle.checkState() == Qt.Checked),
                "compression_opts": self.ui.gzip_rate.value()
            }
        }

    def on_enable_compression_toggled(self, state):
        for widget in [self.ui.gzip_rate, self.ui.enable_shuffle, self.ui.compression_type, self.ui.rate_label]:
            widget.setEnabled(state)

    def on_include_raw_toggled(self, state):
        if state and self.raw_size >= self.rawLayerSizeLimit:
            title = "Warning"
            text = "Raw layer is very large ({} Pixel). Do you really want to include it?"
            buttons = QMessageBox.Yes | QMessageBox.No
            button = QMessageBox.question(self.parent(), title, text.format(self.raw_size), buttons)
            if button == QMessageBox.No:
                self.ui.include_raw.setCheckState(Qt.Unchecked)


class CSVType(ExportFileTypeWidget):
    uiFile = "csvSettings"

    def __init__(self, *args, **kwargs):
        super(CSVType, self).__init__(*args, **kwargs)

    @staticmethod
    def allowed_extensions():
        return "csv",

    @staticmethod
    def filter_string():
        return "CSV (*.csv)"

    @staticmethod
    def display_name():
        return "Comma-Separated Values CSV"

    def export_settings(self):
        return {
            "zip tables": self.ui.zip_tables.checkState() == Qt.Checked
        }


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    from sys import argv, exit as exit_

    app = QApplication(argv)

    hdf = HDFType()
    hdf.show()

    exit_(app.exec_())