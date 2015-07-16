from numpy import uint8, require, append
import logging
from ilastik.utility.exportFile import ProgressPrinter
from ilastik.utility import log_exception
from lazyflow.request import Request
from functools import partial

logger = logging.getLogger(__name__)


class ExportingOperator(object):
    """
    A Mixin for the Operators that can export h5/csv data
    """

    def export_object_data(self, settings, selected_features, gui=None):
        """
        Initialize progress displays and start the actual export in a new thread using the lazyflow.request framework
        :param settings: the settings from the GUI export dialog
        :type settings: dict
        :param selected_features: the features to export from the GUI dialog
        :type selected_features: list
        :param gui: the Progress bar and callbacks for finish/fail/cancel see ExportingGui.show_export_dialog
        :type gui: dict
        """
        self.save_export_progress_dialog(None)
        if gui is None or "dialog" not in gui:
            progress_display = ProgressPrinter("Export Progress", xrange(100, -1, -5), 2)
        else:
            progress_display = gui["dialog"]
            self.save_export_progress_dialog(progress_display)

        export = partial(self.do_export, settings, selected_features, progress_display)
        request = Request(export)
        if gui is not None:
            if "fail" in gui:
                request.notify_failed(gui["fail"])
            if "ok" in gui:
                request.notify_finished(gui["ok"])
            if "cancel" in gui:
                request.notify_cancelled(gui["cancel"])
            if "unlock" in gui:
                request.notify_cancelled(gui["unlock"])
                request.notify_failed(gui["unlock"])
                request.notify_finished(gui["unlock"])
            if "lock" in gui:
                lock = gui["lock"]
                lock()
        request.notify_failed(self.export_failed)
        request.notify_finished(self.export_finished)
        request.notify_cancelled(self.export_cancelled)
        request.submit()

        if gui is not None and "dialog" in gui:
            progress_display.cancel.connect(request.cancel)

    @staticmethod
    def export_failed(_, exc_info):
        """
        Default callback for Request failure
        """
        log_exception(logger, "Export failed", exc_info)

    @staticmethod
    def export_finished(status):
        """
        Default callback for Request success
        """
        logger.info("Export finished. {}".format(status))

    @staticmethod
    def export_cancelled():
        """
        Default callback for Request cancellation
        """
        logger.info("Export cancelled")

    def do_export(self, settings, selected_features, progress_slot):
        """
        Implement this in the exporting Operator
        :param settings: the settings for the export,
            see ilastik.widgets.exportObjectInfoDialog.ExportObjectInfoDialog.settings
        :type settings: dict
        :param selected_features: the features to export
        :type selected_features: list
        :param progress_slot: an object that can display the export progress.
            usage: progress_slot(progress)
            make sure to call it with progress=0 at the start and progress=100 in the end
        """
        raise NotImplementedError

    def save_export_progress_dialog(self, dialog):
        """
        Implement this to save the dialog in a member variable
        Otherwise the dialog will be hidden too fast
        This method is automatically called from ExportingOperator.export_object_data
        :param dialog: the dialog
        :type dialog: most likely QDialog
        """
        raise NotImplementedError


class ExportingGui(object):
    """
    A Mixin for the GUI that can export h5/csv data and hilite objects
    """

    def get_object_hilite_information(self, time, object_id):
        """
        :type time: int
        :type object_id: int
        :return: the bounding box (top_left, bot_right) of the object. Always x=0, y=0, z=0
                If no object exists at the given position None is returned
        :rtype: (numpy.ndarray, numpy.ndarray) | (None, None)
        """
        if object_id == 0:
            return None, None, None, None

        features = self.topLevelOperatorView.viewed_operator().ObjectFeatures[0]([time]).wait()
        min_coord = map(int, features[time][u"Default features"][u"Coord<Minimum>"][object_id])
        max_coord = map(int, features[time][u"Default features"][u"Coord<Maximum>"][object_id])
        center = map(int, features[time][u"Default features"][u"RegionCenter"][object_id])

        while len(min_coord) < 3:
            min_coord = append(min_coord, [0])
            max_coord = append(max_coord, [0])
            center = append(center, [0])

        time_slice = [slice(time, time + 1)]
        ranges = [[slice(min_coord[i], max_coord[i] + 1)] for i in xrange(3)]
        points = [[slice(center[i], center[i] + 1)] for i in xrange(3)]

        slot = self.get_labeling_slot()
        label_slices = [require(ls.wait().squeeze().T, uint8, "C") for ls in (
            slot(time_slice + points[0] + ranges[1] + ranges[2]),
            slot(time_slice + ranges[0] + points[1] + ranges[2]),
            slot(time_slice + ranges[0] + ranges[1] + points[2]),
        )]
        for ls in label_slices:
            ls[ls != object_id] = 0
            ls[ls == object_id] = 255
            require(ls, uint8, "C")

        return min_coord, center, max_coord, label_slices

    def get_exporting_operator(self, lane=0):
        raise NotImplementedError

    @property
    def gui_applet(self):
        raise NotImplementedError

    def show_export_dialog(self):
        """
        Shows the ExportObjectInfoDialog and calls the operators export_object_data method
        """
        # Late imports here, so we don't accidentally import PyQt during headless mode.
        from ilastik.widgets.exportObjectInfoDialog import ExportObjectInfoDialog

        dimensions = self.get_raw_shape()
        feature_names = self.get_feature_names()

        dialog = ExportObjectInfoDialog(dimensions, feature_names, title=self.get_export_dialog_title())
        if not dialog.exec_():
            return

        settings = dialog.settings()
        selected_features = dialog.checked_features()

        from ilastik.widgets.progressDialog import ProgressDialog
        progress = ProgressDialog(["Feature Data", "Labeling Rois", "Raw Image", "Exporting"])
        progress.set_busy(True)
        progress.show()
        gui = {
            "dialog": progress,
            "ok": partial(progress.safe_popup, "information", "Information", "Export successful!"),
            "cancel": partial(progress.safe_popup, "information", "Information", "Export cancelled!"),
            "fail": partial(progress.safe_popup, "critical", "Critical", "Export failed!"),
            "unlock": self.unlock_gui,
            "lock": self.lock_gui
        }
        self.get_exporting_operator().export_object_data(settings, selected_features, gui)

    def get_raw_shape(self):
        """
        Implement this to provide the shape of the raw image in the show_export_dialog method
        :return: the raw image's shape

        e.g. return self.exportingOperator.RawImage.meta.shape
        """
        raise NotImplementedError

    def get_feature_names(self):
        """
        Implement this to provide the computed feature names in the show_export_dialog method
        :return: the computed feature names
        :rtype: dict

        e.g. return self.exportingOperator.ComputedFeatureNames([]).wait()
        """
        raise NotImplementedError

    def get_labeling_slot(self):
        """
        Implement this to provide the labeling slot
        :return: the labeling slot
        """
        raise NotImplementedError

    def unlock_gui(self, *_):
        self.gui_applet.busy = False
        self.gui_applet.appletStateUpdateRequested.emit()

    def lock_gui(self):
        self.gui_applet.busy = True
        self.gui_applet.appletStateUpdateRequested.emit()

    def get_export_dialog_title(self):
        raise NotImplementedError
