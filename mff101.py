
#! /usr/bin/python

# from msilib.schema import ListView
from importlib.resources import path
import sys, os, getopt
from tkinter.tix import Tree
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.uic import loadUiType
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_gtk3 import (NavigationToolbar2GTK3 as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
import matplotlib
from fpdf import FPDF
from skimage.restoration import unwrap_phase
from skimage.draw import circle
import wrapAuto_ui 
from wrapAutoMenu import *
from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
import numpy as np
from attr import s
import numpy as np
from thorlabs_apt_device import BBD201
from thorlabs_apt_device import APTDevice_BayUnit  
from serial.tools.list_ports import comports
from PIL import Image
import serial
import time
import shmlib
import krtc
import random
import logging

class mpl_Widget(QWidget):
    def __init__(self, parent = None):
        super(mpl_Widget, self).__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # plt.figure(figsize=(10,10))
        # plt.subplot(221)
        self.layoutvertical = QVBoxLayout(self)
        self.layoutvertical.addWidget(self.canvas)

   
    
    def calcturbPlates(self, path):

        Plate_Inter_Trans = np.load(path+'plate_t2.npy')
        Plate_Inter_Reflect = np.load(path+'plate_r2.npy')
        Plate_Test_Trans = np.load(path+'ref_blocked_t.npy')
        Plate_Test_Reflect = np.load(path+'ref_blocked_r.npy')
        Plate_Refer_Trans = np.load(path+'test_blocked_t.npy')
        Plate_Refer_Reflect = np.load(path+'test_blocked_r.npy')

        #Scale interference to range of -1 to +1
        Plate_Sin_Trans = (Plate_Inter_Trans/(Plate_Refer_Trans + Plate_Test_Trans)) - 1
        Plate_Cos_Reflect = (Plate_Inter_Reflect/(Plate_Refer_Reflect + Plate_Test_Reflect)) - 1
        Plate_Phase_Both = np.arctan2(Plate_Sin_Trans,Plate_Cos_Reflect)
        unwr_phase = unwrap_phase(Plate_Phase_Both)

        self.axis1 = self.figure.add_subplot(221)
        pc = self.axis1.imshow(Plate_Sin_Trans)
        self.axis1.set_title("Transmitted Interference")
        self.figure.colorbar(pc)

        self.axis2 = self.figure.add_subplot(222)
        pc2 = self.axis2.imshow(Plate_Cos_Reflect)
        self.axis2.set_title("Reflected Interference")
        self.figure.colorbar(pc2)

        # self.axis2.clim(-1,1)
        # self.axis2.colorbar()

        self.axis3 = self.figure.add_subplot(223)
        self.axis3.imshow(Plate_Phase_Both)
        self.axis3.set_title("Phase Estimate")

        self.axis4 = self.figure.add_subplot(224)
        pc3 = self.axis4.imshow(unwr_phase)
        self.axis4.set_title("Unwrapped Phase Estimate")
        self.figure.colorbar(pc3)

        self.canvas.draw()


    def createPDFCanvas(self, path_, finalMean, finalUnc):

        self.PDF_Img = Image.fromarray(np.asarray(self.canvas.buffer_rgba()))

        print(finalMean, finalUnc)
        New_PDF = FPDF()
        New_PDF.add_page()
        New_PDF.set_font("helvetica", "B", 16)
        New_PDF.cell(30,10, path_)
        New_PDF.ln(10)
        New_PDF.image(self.PDF_Img, w=New_PDF.epw)
        New_PDF.ln(10)
        New_PDF.cell(30, 10, "Final Estimate of r_0 is " + str(finalMean) +" +/-" + str(finalUnc))
        os.chdir(path_)
        New_PDF.output( "doc-with-figure.pdf")




class Window(QMainWindow, wrapAuto_ui.Ui_MainWindow): #Changed from class Window(QMainWindow, wrapAuto_ui.Ui_MainWindow)

    def __init__(self, shmimname1, shmimname2):
        super(Window, self).__init__()

        logging.getLogger('matplotlib.font_manager').disabled = True

        self.setupUi(self)

        self.basedir = '/home/lab/Data/12bitData/'
        
        self.init_graph()
        self.connectSignalsSlots()

          # Create SHM object
        print(shmimName1)
        self.shmim1 = shmlib.shm(shmimName1)
        # Create SHM object
        print(shmimName2)
        self.shmim2 = shmlib.shm(shmimName2)

        # Get first imagels
        im1 = self.shmim1.get_data()
        im1 = im1.reshape(im1.shape[1], im1.shape[0])
        # Get first image
        im2 = self.shmim2.get_data()
        im2 = np.fliplr(im2.reshape(im2.shape[1], im2.shape[0]))

        im = np.concatenate((im1,im2))
        ims = im1-im2
        
        self.vb = pg.ViewBox()
        
        self.graphicsView_1.setCentralItem(self.vb)
        self.vb.setAspectLocked()
        self.img = pg.ImageItem()
        #self.img.setLevels([0, 100])
        self.vb.addItem(self.img)
        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        self.scaleView_1.setCentralItem(self.hist)        
        # set display according to SHM size
        self.vb.setRange(QtCore.QRectF(0, 0, im.shape[1], im.shape[0]))
        self.img.setImage(np.rot90(np.flipud(np.fliplr((im)))))
        # save first counter
        self.imCnt1 = self.shmim1.get_counter()

        # 2nd SHM
        self.vb2 = pg.ViewBox()
        self.graphicsView_2.setCentralItem(self.vb2)
        self.vb2.setAspectLocked()
        self.img2 = pg.ImageItem()
        #self.img2.setLevels([0, 100])
        self.vb2.addItem(self.img2)
        # Contrast/color control
        self.hist2 = pg.HistogramLUTItem()
        self.hist2.setImageItem(self.img2)
        self.scaleView_2.setCentralItem(self.hist2)        
        # set display according to SHM size
        self.vb.setRange(QtCore.QRectF(0, 0, ims.shape[0], ims.shape[1]))
        self.img2.setImage(np.rot90(np.flipud(np.fliplr((ims)))))
        # save first counter
        self.imCnt12 = self.shmim2.get_counter()
 
        # Create QT timer to update display
        self.timer = QtCore.QTimer(self)
        # Throw event timeout with an interval of 50 milliseconds
        self.timer.setInterval(100) 
        # each time timer counts done call self.Update
        self.timer.timeout.connect(self.Update) 

        # save initial time for frequency display purpose
        self.t1=time.time()
        self.log1=False
        self.log2=False

        
    def connectSignalsSlots(self):

        #interface buttons
        self.dirButton.clicked.connect(self.Set_Directory)
        self.mtbButton.clicked.connect(self.Update_Graph) #changed from self.update_Graph
        self.sfButton.clicked.connect(self.Save_Frames)
        self.osButton.clicked.connect(lambda: Open_Shutters(self))
        
        #menu buttons
        
        self.actionOpen_Shutters_2.triggered.connect(lambda: Open_Shutters(self))
        self.actionExport_to_PDF.triggered.connect(self.Export_PDF)
        self.actionClose_Shutters.triggered.connect(lambda: Close_Shutters(self))
        self.actionOpen_Reference_Shutter.triggered.connect(lambda: Open_Reference_Shutter(self))
        self.actionClose_Reference_Shutter.triggered.connect(lambda: Close_Reference_Shutter(self))
        self.actionOpen_Test_Shutter.triggered.connect(lambda: Open_Test_Shutter(self))
        self.actionClose_Test_Shutter.triggered.connect(lambda: Close_Test_Shutter(self))
        self.actionDirections_for_QPI_Test.triggered.connect(self.show_popup)

    def show_popup(self):
        msg = QMessageBox()
        msg.setWindowTitle("Help Window")
        msg.setText("Instructions")
        msg.setDetailedText("After Reboot:Run: krtcInit.py\nBe sure camera are on... (192.168.3.69)\n\nwait 5-10 sec  once up and running, then run: startEvtHT5000DuoProcess")

        x = msg.exec_()

    def init_graph(self):
        self.mpl_widget = mpl_Widget()
        self.layoutvertical = QVBoxLayout(self.mplWidget)
        self.layoutvertical.addWidget(self.mpl_widget)

    def Update_Graph(self):
        # self.mpl_widget.axis1.clear()
        # self.mpl_widget.axis4.clear()
        self.checkPath()

    
        self.mpl_widget.calcturbPlates(self.path)
        self.intframesButtonMTB()

        


    def intframesButtonMTB(self):

    ##6/21 trying to figure out how to start mtbAuto from adfAuto 


        #This script will measure the phase variation statistics based on a prescribed set of images taken with QPI.

        #August 2021 	Cesar Laguna  - Original Algorithm from Code_3_v2.py
        #August 5, 2021	Phil Hinz - cleanup and reorganization

        #path = 'Data/8bitData/DarenA/'				#remember trailing /
        # path = '/home/lab/Data/12bitData/testDir7/'	#remember trailing /
        path = self.path
        
        print(path)
        #path = 'Data/8bitData/GPIPlate/'

        ############## Read in all of the images
        Plate_Inter_Trans = np.load(path+'plate_t2.npy')
        Plate_Inter_Reflect = np.load(path+'plate_r2.npy')
        Plate_Test_Trans = np.load(path+'ref_blocked_t.npy')
        Plate_Test_Reflect = np.load(path+'ref_blocked_r.npy')
        Plate_Refer_Trans = np.load(path+'test_blocked_t.npy')
        Plate_Refer_Reflect = np.load(path+'test_blocked_r.npy')

        #np.seterr(divide='ignore',invalid='ignore')	#PMH - not sure about this, so commenting out for now.


        #Scale interference to range of -1 to +1
        Plate_Sin_Trans = (Plate_Inter_Trans/(Plate_Refer_Trans + Plate_Test_Trans)) - 1

        
        # plt.figure(figsize=(10,10))
        # plt.subplot(221)
        # plt.imshow(Plate_Sin_Trans)
        # plt.title('Transmitted Interference')
        # plt.clim(-1,1)
        # plt.colorbar()

        # #Scale interference to range of -1 to +1
        Plate_Cos_Reflect = (Plate_Inter_Reflect/(Plate_Refer_Reflect + Plate_Test_Reflect)) - 1

        # plt.subplot(222)
        # plt.imshow(Plate_Cos_Reflect)
        # plt.title('Reflected Interference')
        # plt.clim(-1,1)
        # plt.colorbar()


        Plate_Phase_Both = np.arctan2(Plate_Sin_Trans,Plate_Cos_Reflect)

        # plt.subplot(223)
        # plt.title('Phase Estimate')
        # plt.imshow(Plate_Phase_Both)

        unwr_phase = unwrap_phase(Plate_Phase_Both)

        # plt.subplot(224)
        # plt.imshow(unwr_phase)
        # plt.title('Unwrapped Phase Estimate')
        # plt.colorbar()

        # print("")
        # #print('Please look at the "Unwrapped" image. You will have the option to analyze the entire image or a selected area of the image. If you would like to anaylyze only an area I recommend writing down the x range and y range, you will be asked for it.', '\n')
        # print('Please close the 4-panel plot to continue.')

        
        # # plt.show()
        # self.mpl_widget.canvas.draw()


        ##########Calculate Statistics

        pixel_value_ = list()
        pixel_coord_ = list()
        '''
        print('Please select the area of the image for which you would like to analyze r_o.', '\n')
        ask = input("To the analyze the full image please type 'Full' otherwise type 'No': ")
        if ask == 'Full':
            column_ = range(500, 1800)
            row_ = range(400, 1700)
        else:
            y_min = int(input('Y minimum value: '))
            y_max = int(input('Y maximum value: '))
            x_min = int(input('X minimum value: '))
            x_max = int(input('X maximum value: '))
            column_ = range(y_min, y_max)
            row_ = range(x_min, x_max)
        #iterate = np.arange(30, 50)
        #num = np.arange(1)
        response_ = int(input('Select Radius size for circle, this will be used to calculate r_o: '))
        '''

        #Hard Code the values for now
        column_ = range(500,1800)	# X Axis
        row_ = range(400,1700)		# Y Axis
        response_= 25		#50 is ~750 um diameter
        QListWidgetItem('Pixel Radius [in pixels] = '+ str(response_), self.listWidget)
        QListWidgetItem('Pixel Radius [in mu] = ' + str(response_ * 14.84), self.listWidget)

        numsamples = 100	#number of random samplings on the plate per iteration
        numiter	= 10		#number of times to measure

        Fried_Length = []
        for ii in range(numiter) :
            random_column_ = random.sample(column_, numsamples)
            random_row_ = random.sample(row_, numsamples)
            QListWidgetItem('#############################################################################', self.listWidget)
            QListWidgetItem('Iteration :' + str(ii)+ '\n', self.listWidget)
            for j in range(len(random_column_)):
                pixel_value_ = np.append(pixel_value_, [np.array([unwr_phase[random_column_[j], random_row_[j]]])])
            pixel_values = list()
            for i in range(len(random_column_)):
                pixel_values = np.append(pixel_values, unwr_phase[random_column_[i], random_row_[i]])
            phi_ = list()
            r_o_ = list()
            r_o_mu_ = list()
            #plt.figure()
            #plt.imshow(unwr_phase)
            #plt.colorbar()
            for i in range(len(random_column_)):
                pixel_radius_ = (circle(random_row_[i], random_column_[i], response_))
                pixel_radius_x_ = pixel_radius_[0][:]
                pixel_radius_y_ = pixel_radius_[1][:]
                pixel_radius_values_ = unwr_phase[pixel_radius_y_, pixel_radius_x_]
                phi_ = np.append(phi_, [(np.std(pixel_radius_values_))*(633/550)])

                diameter_ = response_ * 2
                r_o_ = np.append(r_o_, (diameter_)/((phi_[i]/(0.162*2*np.pi))**(6/5)))
                response_mu_ = (diameter_) * (14.84) #pixel * mu/pixel = mu
                r_o_mu_ = np.append(r_o_mu_, response_mu_/((phi_[i]/(0.162*2*np.pi))**(6/5)))

                #plt.imshow(unwr_phase)
                plt.plot(random_row_[i], random_column_[i], marker = 'x', color = 'k')
                plt.scatter(pixel_radius_[0][:], pixel_radius_[1][:], marker = '.', color = 'r', linewidths = .1)
                #plt.title('')

            QListWidgetItem('Great! Your Values:', self.listWidget)
            #print('r_o value (microns)= ', r_o_mu_, '\n')
            QListWidgetItem('Average r_o value (microns) = '+ str(np.mean(r_o_mu_))+'\n', self.listWidget)
            Fried_Length =np.append(Fried_Length,np.mean(r_o_mu_))
            
        #plt.show()

        meanFL = np.mean(Fried_Length)
        uncFL = np.std(Fried_Length)

        QListWidgetItem("Final Estimate of r_0 is " + str(meanFL) +" +/-" + str(uncFL), self.listWidget)
        self.finalMean = meanFL
        self.finalUnc = uncFL

    def Start(self):
        """ Start timer """
        self.timer.start()

    def Stop(self):
        """ Stop timer """
        self.timer.stop()

    def Set_Directory(self) : 
        dirinput = self.dirEdit.text()
        self.path=self.basedir+dirinput+'/'
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.dirLabel.setStyleSheet("color: black;")
        self.dirLabel.setText(self.path)

    def getImPair(self) :
        im1=self.shmim1.get_data()
        #im1 = (np.rot90(im1.reshape(im1.shape[1], im1.shape[0]),3))
        im1 = (im1.reshape(im1.shape[1], im1.shape[0]))
        # Update the displayed image with the data of the SHM
        im2=self.shmim2.get_data()
        #im2 = np.flipud(np.rot90(im2.reshape(im2.shape[1], im2.shape[0]),3))
        im2 = np.fliplr(im2.reshape(im2.shape[1], im2.shape[0]))
        return im1,im2	

    @QtCore.pyqtSlot()
    def Update(self):
        """ Update the GUI """
        # Update the displayed image with the data of the SHM
        im1=self.shmim1.get_data()
        #im1 = (np.rot90(im1.reshape(im1.shape[1], im1.shape[0]),3))
        im1 = (im1.reshape(im1.shape[1], im1.shape[0]))
        # Update the displayed image with the data of the SHM
        im2=self.shmim2.get_data()
        #im2 = np.flipud(np.rot90(im2.reshape(im2.shape[1], im2.shape[0]),3))
        im2 = np.fliplr(im2.reshape(im2.shape[1], im2.shape[0]))
        im = np.concatenate((im1,im2))
        ims = im2
  
        if self.log1==True:
            im=np.log(im)
        self.img.setImage(np.rot90(np.flipud(np.fliplr(im))))
        # get the counter
        self.imCnt2 = self.shmim1.get_counter()
        self.t2=time.time()
        ellapsedTime = self.t2-self.t1
        nbImage = self.imCnt2-self.imCnt1
        # display frequency
        self.freqLabel.setText(str('%.2f Hz' %(nbImage/ellapsedTime)))
        self.imCnt1=self.imCnt2

        if self.log2==True:
            ims=np.log(ims)
        self.img2.setImage(np.rot90(np.flipud(np.fliplr(ims))))
        # get the counter
        self.imCnt22 = self.shmim2.get_counter()
        nbImage = self.imCnt22-self.imCnt12
        # display frequency
        self.freqLabel_2.setText(str('%.2f Hz' %(nbImage/ellapsedTime)))
        self.imCnt12=self.imCnt22
        
        self.t1=self.t2
            
    def Save_Frames(self) :

        self.checkPath()

        flipMount = APTDevice_BayUnit #create flipMount object using APTDevice class from thorlabs_apt_devices lib.

        #Identify mounts seperately using their serial number (found on sticker on device) 
        stageTest = flipMount(serial_number="37869") 
        stageReference = flipMount(serial_number="37868")

        #Open Gates
        if stageReference.status['forward_limit_switch'] == False: #if true- OPEN / if false - CLOSED
            print("Reference gate opening")
            stageReference.move_jog(False) #OPEN flip mount
        else:
            print("Reference gate open")

        if stageTest.status['forward_limit_switch'] == False: #if true- OPEN / if false - CLOSED
            print("Test gate opening")
            stageTest.move_jog(False) #OPEN flip mount
        else: 
            print("Test gate open")

        #Capture Images
        time.sleep(3)
        for i in range (10) :
            im1,im2 = self.getImPair() 
            im1label = 'plate_t{}.npy'.format(i)
            im2label = 'plate_r{}.npy'.format(i)
            np.save(self.path+im1label,im1)
            np.save(self.path+im2label,im2)

        time.sleep(3)
        
        #Movement 
        stageTest.move_jog(True)
        time.sleep(3) #pause in between movements to steadily capture images.
        self.testblockedframesButtonCB()
        time.sleep(3)
        stageTest.move_jog(False)
        time.sleep(3)
        stageReference.move_jog(True)
        time.sleep(3)
        self.refblockedframesButtonCB()
        time.sleep(3)
        stageReference.move_jog(False)

        time.sleep(3)

    def Export_PDF(self):
        print("expdf\n", self.path)
        self.mpl_widget.createPDFCanvas(self.path, self.finalMean, self.finalUnc)

    def testblockedframesButtonCB(self) :
        print("test taken")
        im1,im2 = self.getImPair()
        im1label = 'test_blocked_t.npy'
        im2label = 'test_blocked_r.npy'
        np.save(self.path+im1label,im1)
        np.save(self.path+im2label,im2)

    def refblockedframesButtonCB(self) :
        print("ref taken")
        im1,im2 = self.getImPair()
        im1label = 'ref_blocked_t.npy'
        im2label = 'ref_blocked_r.npy'
        np.save(self.path+im1label,im1)
        np.save(self.path+im2label,im2)

    def checkPath(self):
        try: 
            self.path

        except:
            print("path does not exist")
            self.dirLabel.setText("Directory Not Entered")
            self.dirLabel.setStyleSheet("color: red;")
            return


class PDF(FPDF):
    pass
    



if __name__ == "__main__":
    shmimName1 = '/tmp/ca09im.im.shm'
    shmimName2 = '/tmp/ca10im.im.shm'
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hs1:s2",["help", "shmimName1=", "shmimName2="])
    except getopt.GetoptError:
      print('err, usage: imDisp.py -s1 <shmimName1> -s2 <shmimName2>')
      sys.exit(2)
    print(opts)
    print(args)
    for opt, arg in opts:
        if opt == '-h':
            print('imDisp.py -s1 <shmimName1> -s2 <shmimName1>')
            sys.exit()
        elif opt in ("-s1", "--shm1"):
            shmimName1 = str(arg)
        elif opt in ("-s2", "--shm2"):
            shmimName2 = str(arg)
    
    app = QtGui.QApplication([])
    # app = QApplication(sys.argv) 
    win = Window(shmimName1, shmimName2)
    win.show()
    win.Start()
    sys.exit(app.exec_())