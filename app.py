import vtk
import sys
from PyQt5 import QtCore, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog, QFileDialog
from win import Ui_MainWindow
from PyQt5 import Qt
from vtk.util import numpy_support

path='./data'
dataDir = 'headsq/quarter'
surfaceExtractor = vtk.vtkContourFilter()

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.vtkWidget = None
        self.vl = None
        self.ren = None
        self.iren = None
        self.reader= None
        self.PathDicom =''
        self.mode = True
        self.volumeColor = None
        self.pushButton2.clicked.connect(self.changeMood)
        self.pushButton.clicked.connect(self.openDICOM)
        self.slider.valueChanged.connect(self.slider_SLOT)
    
    def changeMood(self):
        self.mode = not(self.mode)
        #update button names
        _translate = QtCore.QCoreApplication.translate
        if (self.mode):
            self.pushButton2.setText(_translate("MainWindow", "Current Mode: Surface Rendering, Click to Change Mode"))
        else:
            self.pushButton2.setText(_translate("MainWindow", "Current Mode: Ray Casting, Click to Change Mode"))
        
        self.OpenVTK()

    def openDICOM(self):
        if (self.PathDicom == ''):
            fname=QFileDialog.getExistingDirectory(self, 'Open folder',path)
            self.PathDicom = fname
            try:
                self.initializeVTK()
            except:
                return
        else:
            fname=QFileDialog.getExistingDirectory(self, 'Open folder',path)
            self.PathDicom = fname
            self.OpenVTK() 

    def initializeVTK(self):
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl = Qt.QVBoxLayout() 
        self.vl.addWidget(self.vtkWidget)
        self.OpenVTK()
        
        

    def OpenVTK(self):
        self.ren = vtk.vtkRenderer()
        try:
            self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        except:
            return
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        ######################################Read Data##############################################
        try:
            self.reader = vtk.vtkDICOMImageReader()
        except:
            return
        
        self.reader.SetDataByteOrderToLittleEndian()
        self.reader.SetDirectoryName(self.PathDicom)
        self.reader.Update()
        ########################################Get Mode#########################################
        if(self.mode):
            self.surfaceMode()
        else:
            self.castingMode()



    def surfaceMode(self):
        surfaceExtractor.SetInputConnection(self.reader.GetOutputPort())
        surfaceExtractor.SetValue(0, -500)
        surfaceNormals = vtk.vtkPolyDataNormals()
        surfaceNormals.SetInputConnection(surfaceExtractor.GetOutputPort())
        surfaceNormals.SetFeatureAngle(60.0)
        surfaceMapper = vtk.vtkPolyDataMapper()
        surfaceMapper.SetInputConnection(surfaceNormals.GetOutputPort())
        surfaceMapper.ScalarVisibilityOff()
        surface = vtk.vtkActor()
        surface.SetMapper(surfaceMapper)

        #camera
        aCamera = vtk.vtkCamera()
        aCamera.SetViewUp(0, 0, -1)
        aCamera.SetPosition(0, 1, 0)
        aCamera.SetFocalPoint(0, 0, 0)
        aCamera.ComputeViewPlaneNormal()
        
        self.ren.AddActor(surface)
        self.ren.SetActiveCamera(aCamera)
        self.ren.ResetCamera()
        self.ren.SetBackground(0, 0, 0)
        self.ren.ResetCameraClippingRange()

        self.frame.setLayout(self.vl)
        self.vtkWidget.Initialize()
        self.vtkWidget.GetRenderWindow().Render()
        self.vtkWidget.Start()
        self.vtkWidget.show()

    def castingMode(self):
        # self.surfaceMode()
        # The volume will be displayed by ray-cast alpha compositing.
        volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        volumeMapper.SetInputConnection(self.reader.GetOutputPort())
        volumeMapper.SetBlendModeToComposite()

        # The color transfer function maps voxel intensities to colors.
        self.volumeColor = vtk.vtkColorTransferFunction()
        self.volumeColor.AddRGBPoint(-500, 0.0, 0.0, 0.0)
        self.volumeColor.AddRGBPoint(0,  1.0, 0.5, 0.3)
        self.volumeColor.AddRGBPoint(500, 1.0, 0.5, 0.3)
        self.volumeColor.AddRGBPoint(1000, 1.0, 1.0, 0.9)

        # The opacity transfer function is used to control the opacity
        # of different tissue types.
        volumeScalarOpacity = vtk.vtkPiecewiseFunction()
        volumeScalarOpacity.AddPoint(-500,    0.00)
        volumeScalarOpacity.AddPoint(0,  0.15)
        volumeScalarOpacity.AddPoint(500, 0.15)
        volumeScalarOpacity.AddPoint(1000, 0.85)

        # The gradient opacity function is used to decrease the opacity
        # in the "flat" regions of the volume while maintaining the opacity
        # at the boundaries between tissue types.
        volumeGradientOpacity = vtk.vtkPiecewiseFunction()
        volumeGradientOpacity.AddPoint(0,   0.0)
        volumeGradientOpacity.AddPoint(90,  0.5)
        volumeGradientOpacity.AddPoint(100, 1.0)

        # The VolumeProperty attaches the color and opacity functions to the
        # volume, and sets other volume properties. 
        volumeProperty = vtk.vtkVolumeProperty()
        volumeProperty.SetColor(self.volumeColor)
        volumeProperty.SetScalarOpacity(volumeScalarOpacity)
        volumeProperty.SetGradientOpacity(volumeGradientOpacity)
        volumeProperty.SetInterpolationTypeToLinear()
        volumeProperty.ShadeOn()
        volumeProperty.SetAmbient(0.4)
        volumeProperty.SetDiffuse(0.6)
        volumeProperty.SetSpecular(0.2)

        # The vtkVolume is a vtkProp3D (like a vtkActor) and controls the position
        # and orientation of the volume in world coordinates.
        volume = vtk.vtkVolume()
        volume.SetMapper(volumeMapper)
        volume.SetProperty(volumeProperty)

        # Finally, add the volume to the renderer
        self.ren.AddViewProp(volume)

        # Set up an initial view of the volume.  
        camera =  self.ren.GetActiveCamera()
        c = volume.GetCenter()
        camera.SetFocalPoint(c[0], c[1], c[2])
        camera.SetPosition(c[0] + 700, c[1], c[2])
        camera.SetViewUp(0, 0, -1)

        self.frame.setLayout(self.vl)
        self.vtkWidget.Initialize()
        self.vtkWidget.GetRenderWindow().Render()
        self.vtkWidget.Start()
        self.vtkWidget.show()

    def slider_SLOT(self,val):
        if(self.mode):
            # surface rendering slider behavior
            surfaceExtractor.SetValue(0, val)
            self.vtkWidget.update()
        else:
            #ray casting slider behavior (BONUS)
            newVal = self.maps(val,-1100,1800,0,1)
            self.volumeColor.AddRGBPoint(-500, 0.0, newVal, newVal)
            self.volumeColor.AddRGBPoint(0, newVal, 0.2, 0.3)
            self.volumeColor.AddRGBPoint(500, 1.0, 0.5, newVal)
            self.volumeColor.AddRGBPoint(1000, newVal, 1.0, newVal)
            self.vtkWidget.update()

    def maps(self, inputValue: float, inMin: float, inMax: float, outMin: float, outMax: float):
        slope = (outMax-outMin) / (inMax-inMin)
        return outMin + slope*(inputValue-inMin)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())