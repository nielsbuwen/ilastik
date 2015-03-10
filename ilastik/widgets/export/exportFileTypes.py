from PyQt4.QtGui import QWidget, QMessageBox
from PyQt4 import uic
from PyQt4.QtCore import Qt

from ilastik.utility.decorators import classproperty

from os.path import split as split_path


class ExportFileTypeWidget(QWidget, object):
    """
    Base Class for the ExportFile configuration widget module

    Extend this to add support for different export types
    Currently there are CSV and HDF5

    Note: this only affects the GUI, not the exporter itself

    class attributes
    _ui_file: set this to the name of the ui file for the settings widget
    """
    _ui_file = None

    def __init__(self, parent=None, raw_size=None, *args, **kwargs):
        """

        :param parent: This gets passed to the QWidget __init__
        :param raw_size: the total pixel size of the raw image. Needed by HDF to display warnings
        :type raw_size: int
        :param args: these are passed to the super __init__
        :param kwargs: these are passe to the super __init__
        :return:
        """
        super(ExportFileTypeWidget, self).__init__(parent, *args, **kwargs)

        if self._ui_file is None:
            raise RuntimeError("ExportFileTypeWidget needs a UI. Set the _ui_file variable")

        form, _ = uic.loadUiType("{}/{}.ui".format(split_path(__file__)[0], self._ui_file))
        self.ui = form()
        self.ui.setupUi(self)

        self.raw_size = raw_size

    @classproperty
    def allowed_extensions(self):
        """
        Override this to specify the allowed extensions by this export type
        :return: tuple
        """
        raise NotImplementedError

    @classproperty
    def default_extension(self):
        """
        The default extension to use is always the first allowed extension
        :return: str
        """
        return self.allowed_extensions[0]

    @classproperty
    def display_name(self):
        """
        Override this to provide the long name of the file type
        :return: str
        """
        raise NotImplementedError

    @classproperty
    def short_name(self):
        """
        Override this to provide a short name of the file type
        :return: str
        """
        raise NotImplementedError

    @classproperty
    def filter_string(self):
        """
        Constructs the filter string for the QFileDialog using the short name and the allowed extensions
        When overridden use this format:
        "some_name ( *.ext1 *.ext2 *.extn )"
        :return:
        """
        return "{} ( {} )".format(self.short_name, " ".join(("*.{}".format(ext) for ext in self.allowed_extensions)))

    def export_settings(self):
        """
        Override this to return the settings that where chosen in the widget
        :return: dict
        """
        raise NotImplementedError


class HDFType(ExportFileTypeWidget):
    _ui_file = "hdfSettings"
    raw_layer_size_limit = 1000000

    def __init__(self, *args, **kwargs):
        super(HDFType, self).__init__(*args, **kwargs)

    @classproperty
    def allowed_extensions(self):
        return "h5", "hf5", "hdf5"

    @classproperty
    def display_name(self):
        return "Hierarchical Data Format HDF"

    @classproperty
    def short_name(self):
        return "HDF 5"

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
        if state and self.raw_size >= self.raw_layer_size_limit:
            title = "Warning"
            text = "Raw layer is very large ({} Pixel). Do you really want to include it?"
            buttons = QMessageBox.Yes | QMessageBox.No
            button = QMessageBox.question(self.parent(), title, text.format(self.raw_size), buttons)
            if button == QMessageBox.No:
                self.ui.include_raw.setCheckState(Qt.Unchecked)


class CSVType(ExportFileTypeWidget):
    _ui_file = "csvSettings"
    delimiters = [",", ";", "\t"]

    def __init__(self, *args, **kwargs):
        super(CSVType, self).__init__(*args, **kwargs)

    @classproperty
    def allowed_extensions(self):
        return "csv",

    @classproperty
    def display_name(self):
        return "Comma-Separated Values CSV"

    @classproperty
    def short_name(self):
        return "CSV"

    def export_settings(self):
        return {
            "zip": self.ui.zip_tables.checkState() == Qt.Checked,
            "delimiter": self.delimiters[self.ui.delimeter.currentIndex()]
        }


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    from sys import argv, exit as exit_
    from pprint import PrettyPrinter as Pp

    pp = Pp(indent=4).pprint

    app = QApplication(argv)

    hdf = CSVType()
    hdf.show()

    code = app.exec_()

    pp(hdf.export_settings())

    exit_(code)