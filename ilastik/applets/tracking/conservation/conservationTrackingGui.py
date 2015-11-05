from PyQt4 import uic, QtGui
from PyQt4.QtGui import *
import os
import logging
import sys
import re
import traceback
import numpy
from PyQt4.QtCore import pyqtSignal
from ilastik.applets.tracking.base.trackingBaseGui import TrackingBaseGui
from ilastik.utility.exportFile import Default
from ilastik.utility import log_exception
from ilastik.utility.exportingOperator import ExportingGui
from ilastik.utility.gui.threadRouter import threadRouted
from ilastik.utility.gui.titledMenu import TitledMenu
from ilastik.utility.ipcProtocol import Protocol
from ilastik.shell.gui.ipcManager import IPCFacade
from ilastik.config import cfg as ilastik_config

from lazyflow.request.request import Request

logger = logging.getLogger(__name__)
traceLogger = logging.getLogger('TRACE.' + __name__)

class ConservationTrackingGui(TrackingBaseGui, ExportingGui):
    
    withMergers = True
    @threadRouted
    def _setMergerLegend(self, labels, selection):
        param = self.topLevelOperatorView.Parameters.value
        if 'withMergerResolution' in param.keys():
            if param['withMergerResolution']:
                selection = 1
        elif self._drawer.mergerResolutionBox.isChecked():
            selection = 1

        for i in range(2,len(labels)+1):
            if i <= selection:
                labels[i-1].setVisible(True)
            else:
                labels[i-1].setVisible(False)

        # hide merger legend if selection < 2
        self._drawer.label_4.setVisible(selection > 1)
        labels[0].setVisible(selection > 1)

    def _loadUiFile(self):
        # Load the ui file (find it in our own directory)
        localDir = os.path.split(__file__)[0]
        self._drawer = uic.loadUi(localDir+"/drawer.ui")
        
        parameters = self.topLevelOperatorView.Parameters.value        
        if 'maxDist' in parameters.keys():
            self._drawer.maxDistBox.setValue(parameters['maxDist'])
        if 'maxObj' in parameters.keys():
            self._drawer.maxObjectsBox.setValue(parameters['maxObj'])
        if 'divThreshold' in parameters.keys():
            self._drawer.divThreshBox.setValue(parameters['divThreshold'])
        if 'avgSize' in parameters.keys():
            self._drawer.avgSizeBox.setValue(parameters['avgSize'][0])
        if 'withTracklets' in parameters.keys():
            self._drawer.trackletsBox.setChecked(parameters['withTracklets'])
        if 'sizeDependent' in parameters.keys():
            self._drawer.sizeDepBox.setChecked(parameters['sizeDependent'])
        if 'divWeight' in parameters.keys():
            self._drawer.divWeightBox.setValue(parameters['divWeight'])
        if 'transWeight' in parameters.keys():
            self._drawer.transWeightBox.setValue(parameters['transWeight'])
        if 'withDivisions' in parameters.keys():
            self._drawer.divisionsBox.setChecked(parameters['withDivisions'])
        if 'withOpticalCorrection' in parameters.keys():
            self._drawer.opticalBox.setChecked(parameters['withOpticalCorrection'])
        if 'withClassifierPrior' in parameters.keys():
            self._drawer.classifierPriorBox.setChecked(parameters['withClassifierPrior'])
        if 'withMergerResolution' in parameters.keys():
            self._drawer.mergerResolutionBox.setChecked(parameters['withMergerResolution'])
        if 'borderAwareWidth' in parameters.keys():
            self._drawer.bordWidthBox.setValue(parameters['borderAwareWidth'])
        if 'cplex_timeout' in parameters.keys():
            self._drawer.timeoutBox.setText(str(parameters['cplex_timeout']))
        if 'appearanceCost' in parameters.keys():
            self._drawer.appearanceBox.setValue(parameters['appearanceCost'])
        if 'disappearanceCost' in parameters.keys():
            self._drawer.disappearanceBox.setValue(parameters['disappearanceCost'])
        
        return self._drawer

    def initAppletDrawerUi(self):
        super(ConservationTrackingGui, self).initAppletDrawerUi()        

        self._allowedTimeoutInputRegEx = re.compile('^[0-9]*$')
        self._drawer.timeoutBox.textChanged.connect(self._onTimeoutBoxChanged)

        if not ilastik_config.getboolean("ilastik", "debug"):
            def checkboxAssertHandler(checkbox, assertEnabled=True):
                if checkbox.isChecked() == assertEnabled:
                    checkbox.hide()
                else:
                    checkbox.setEnabled(False)

            checkboxAssertHandler(self._drawer.trackletsBox, True)

            if self._drawer.classifierPriorBox.isChecked():
                self._drawer.hardPriorBox.hide()
                self._drawer.classifierPriorBox.hide()
                self._drawer.sizeDepBox.hide()
            else:
                self._drawer.hardPriorBox.setEnabled(False)
                self._drawer.classifierPriorBox.setEnabled(False)
                self._drawer.sizeDepBox.setEnabled(False)

            checkboxAssertHandler(self._drawer.opticalBox, False)
            checkboxAssertHandler(self._drawer.mergerResolutionBox, True)

            self._drawer.maxDistBox.hide() # hide the maximal distance box
            self._drawer.label_2.hide() # hie the maximal distance label
            self._drawer.label_5.hide() # hide division threshold label
            self._drawer.divThreshBox.hide()
            self._drawer.label_25.hide() # hide avg. obj size label
            self._drawer.avgSizeBox.hide()
          
        self.mergerLabels = [self._drawer.merg1,
                             self._drawer.merg2,
                             self._drawer.merg3,
                             self._drawer.merg4,
                             self._drawer.merg5,
                             self._drawer.merg6,
                             self._drawer.merg7]
        for i in range(len(self.mergerLabels)):
            self._labelSetStyleSheet(self.mergerLabels[i], self.mergerColors[i+1])
        
        self._onMaxObjectsBoxChanged()
        self._drawer.maxObjectsBox.valueChanged.connect(self._onMaxObjectsBoxChanged)
        self._drawer.mergerResolutionBox.stateChanged.connect(self._onMaxObjectsBoxChanged)

    @threadRouted
    def _onTimeoutBoxChanged(self, *args):
        inString = str(self._drawer.timeoutBox.text())
        if self._allowedTimeoutInputRegEx.match(inString) is None:
            self._drawer.timeoutBox.setText(inString.decode("utf8").encode("ascii", "replace")[:-1])

    def _setRanges(self, *args):
        super(ConservationTrackingGui, self)._setRanges()        
        maxx = self.topLevelOperatorView.LabelImage.meta.shape[1] - 1
        maxy = self.topLevelOperatorView.LabelImage.meta.shape[2] - 1
        maxz = self.topLevelOperatorView.LabelImage.meta.shape[3] - 1
        
        maxBorder = min(maxx, maxy)
        if maxz != 0:
            maxBorder = min(maxBorder, maxz)
        self._drawer.bordWidthBox.setRange(0, maxBorder/2)
        
        
    def _onMaxObjectsBoxChanged(self):
        self._setMergerLegend(self.mergerLabels, self._drawer.maxObjectsBox.value())
        
    def _onTrackButtonPressed( self ):    
        if not self.mainOperator.ObjectFeatures.ready():
            self._criticalMessage("You have to compute object features first.")            
            return
        
        def _track():    
            self.applet.busy = True
            self.applet.appletStateUpdateRequested.emit()
            maxDist = self._drawer.maxDistBox.value()
            maxObj = self._drawer.maxObjectsBox.value()        
            divThreshold = self._drawer.divThreshBox.value()
            
            from_t = self._drawer.from_time.value()
            to_t = self._drawer.to_time.value()
            from_x = self._drawer.from_x.value()
            to_x = self._drawer.to_x.value()
            from_y = self._drawer.from_y.value()
            to_y = self._drawer.to_y.value()        
            from_z = self._drawer.from_z.value()
            to_z = self._drawer.to_z.value()        
            from_size = self._drawer.from_size.value()
            to_size = self._drawer.to_size.value()        
            
            self.time_range =  range(from_t, to_t + 1)
            avgSize = [self._drawer.avgSizeBox.value()]

            cplex_timeout = None
            if len(str(self._drawer.timeoutBox.text())):
                cplex_timeout = int(self._drawer.timeoutBox.text())

            withTracklets = self._drawer.trackletsBox.isChecked()
            sizeDependent = self._drawer.sizeDepBox.isChecked()
            hardPrior = self._drawer.hardPriorBox.isChecked()
            classifierPrior = self._drawer.classifierPriorBox.isChecked()
            divWeight = self._drawer.divWeightBox.value()
            transWeight = self._drawer.transWeightBox.value()
            withDivisions = self._drawer.divisionsBox.isChecked()        
            withOpticalCorrection = self._drawer.opticalBox.isChecked()
            withMergerResolution = self._drawer.mergerResolutionBox.isChecked()
            borderAwareWidth = self._drawer.bordWidthBox.value()
            withArmaCoordinates = True
            appearanceCost = self._drawer.appearanceBox.value()
            disappearanceCost = self._drawer.disappearanceBox.value()
    
            ndim=3
            if (to_z - from_z == 0):
                ndim=2
            
            try:
                self.mainOperator.track(
                    time_range = self.time_range,
                    x_range = (from_x, to_x + 1),
                    y_range = (from_y, to_y + 1),
                    z_range = (from_z, to_z + 1),
                    size_range = (from_size, to_size + 1),
                    x_scale = self._drawer.x_scale.value(),
                    y_scale = self._drawer.y_scale.value(),
                    z_scale = self._drawer.z_scale.value(),
                    maxDist=maxDist,         
                    maxObj = maxObj,               
                    divThreshold=divThreshold,
                    avgSize=avgSize,                
                    withTracklets=withTracklets,
                    sizeDependent=sizeDependent,
                    divWeight=divWeight,
                    transWeight=transWeight,
                    withDivisions=withDivisions,
                    withOpticalCorrection=withOpticalCorrection,
                    withClassifierPrior=classifierPrior,
                    ndim=ndim,
                    withMergerResolution=withMergerResolution,
                    borderAwareWidth = borderAwareWidth,
                    withArmaCoordinates = withArmaCoordinates,
                    cplex_timeout = cplex_timeout,
                    appearance_cost = appearanceCost,
                    disappearance_cost = disappearanceCost,
                    force_build_hypotheses_graph = False
                    )

                # update showing the merger legend,
                # as it might be (no longer) needed if merger resolving
                # is disabled(enabled)
                self._setMergerLegend(self.mergerLabels, self._drawer.maxObjectsBox.value())
            except Exception as ex:
                log_exception(logger, "Error during tracking.  See above error traceback.")
                self._criticalMessage("Error during tracking.  See error log.\n\n"
                                      "Exception was:\n\n{})".format( ex ))
                return
        
        def _handle_finished(*args):
            self.applet.busy = False
            self.applet.appletStateUpdateRequested.emit()
            self.applet.progressSignal.emit(100)
            self._drawer.TrackButton.setEnabled(True)
            self._drawer.exportButton.setEnabled(True)
            self._drawer.exportTifButton.setEnabled(True)
            self._setLayerVisible("Objects", False) 
            
        def _handle_failure( exc, exc_info ):
            self.applet.busy = False
            self.applet.appletStateUpdateRequested.emit()
            self.applet.progressSignal.emit(100)
            traceback.print_exception(*exc_info)
            sys.stderr.write("Exception raised during tracking.  See traceback above.\n")
            self._drawer.TrackButton.setEnabled(True)
        
        self.applet.progressSignal.emit(0)
        self.applet.progressSignal.emit(-1)
        req = Request( _track )
        req.notify_failed( _handle_failure )
        req.notify_finished( _handle_finished )
        req.submit()

    def menus(self):
        m = QtGui.QMenu("&Export", self.volumeEditorWidget)
        m.addAction("Export Tracking Information").triggered.connect(self.show_export_dialog)

        return [m]

    def get_raw_shape(self):
        return self.topLevelOperatorView.RawImage.meta.shape

    def get_feature_names(self):
        params = self.topLevelOperatorView.Parameters
        if params.ready() and params.value["withDivisions"]:
            return self.topLevelOperatorView.ComputedFeatureNamesWithDivFeatures([]).wait()
        return self.topLevelOperatorView.ComputedFeatureNames([]).wait()

    def get_color(self, pos5d):
        slicing = tuple(slice(i, i+1) for i in pos5d)
        color = self.mainOperator.CachedOutput(slicing).wait()
        return color.flat[0]

    def get_object(self, pos5d):
        slicing = tuple(slice(i, i+1) for i in pos5d)
        label = self.mainOperator.RelabeledImage(slicing).wait()
        return label.flat[0], pos5d[0]

    @property
    def gui_applet(self):
        return self.applet

    def get_export_dialog_title(self):
        return "Export Tracking Information"

    def handleEditorRightClick(self, position5d, win_coord):
        debug = ilastik_config.getboolean("ilastik", "debug")

        obj, time = self.get_object(position5d)
        if obj == 0:
            menu = TitledMenu(["Background"])
            self.create_background_hilite_options(menu, time)
            menu.exec_(win_coord)
            return

        try:
            extra = self.mainOperator.extra_track_ids
        except (IndexError, KeyError):
            extra = {}

        # if this is a resolved merger, find which of the merged IDs we actually clicked on
        if time in extra and obj in extra[time]:
            colors = [self.mainOperator.label2color[time][t] for t in extra[time][obj]]
            tracks = [self.mainOperator.track_id[time][t] for t in extra[time][obj]]
            selected_track = self.get_color(position5d)
            idx = colors.index(selected_track)
            color = colors[idx]
            track = tracks[idx]
        else:
            try:
                color = self.mainOperator.label2color[time][obj]
                track = [self.mainOperator.track_id[time][obj]][0]
            except (IndexError, KeyError):
                color = None
                track = []
            tracks = [track]

        if track:
            children, parents = self.mainOperator.track_family(track)
        else:
            children, parents = None, None

        menu = TitledMenu([
            "Object {} of lineage id {}".format(obj, color),
            "Track id: " + (str(track) or "None"),
        ])

        if not debug:
            menu.exec_(win_coord)
            return

        if any(IPCFacade().sending):
            parameters = self.topLevelOperatorView.Parameters
            try:
                multi_move_max = parameters.value["maxObj"] if parameters.ready() else 2
            except KeyError:
                multi_move_max = 1

            self.create_object_hilite_options(menu, obj, time)

            sub_menus = [
                ("Tracks", Protocol.simple_in, tracks),
                ("Parents", Protocol.simple_in, parents),
                ("Children", Protocol.simple_in, children)
            ]
            for name, protocol, args in sub_menus:
                if args:
                    sub = menu.addMenu("Hilite {}".format(name))
                    for mode in Protocol.ValidHiliteModes[:-1]:
                        mode = mode
                        where = protocol("track_id*", args, wildcard_filler=range(1, multi_move_max+1))
                        cmd = Protocol.cmd(mode, where)
                        sub.addAction(mode.capitalize(), IPCFacade().broadcast(cmd))
                else:
                    sub = menu.addAction("Hilite {}".format(name))
                    sub.setEnabled(False)
            sub = menu.addMenu("Hilite Lineage")
            for mode in Protocol.ValidHiliteModes[:-1]:
                where_dict = {
                    Default.Lineage["names"][0]: color
                }
                where = Protocol.simple("or", **where_dict)
                cmd = Protocol.cmd(mode, where)
                sub.addAction(mode.capitalize(), IPCFacade().broadcast(cmd))

            self.create_background_hilite_options(menu, time)
        else:
            menu.addAction("Open IPC Server Window", IPCFacade().show_info)
            menu.addAction("Start IPC Server", IPCFacade().start)

        menu.exec_(win_coord)

    def get_labeling_slot(self):
        return self.mainOperator.LabelImage