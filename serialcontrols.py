
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtUiTools import QUiLoader
import sys
from Ui_mainwindow import Ui_MainWindow
import serial
import serial.tools.list_ports
from mettler_toledo_device import MettlerToledoDevice
import threading
import asyncio.tasks
import asyncio
import queue
from MasterflexPump import MasterflexPump



class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 

    '''
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    connected = Signal(str)
    progress = Signal(int)
    pumpStart = Signal()
    pumpStop = Signal()



class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, name,pumpname,max, isSerial, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.name = name
        self.max = max
        self.pumpname = pumpname
        self.isSerial = isSerial
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.running = True
        if(self.isSerial == True):
            try:
                self.pumpPort = serial.Serial(port=self.pumpname, baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
            except:
                self.pumpPort.close()
                self.pumpPort = serial.Serial(port=self.pumpname, baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
        

        
        self.scalePort = MettlerToledoDevice(port=self.name)
            
        # Add the callback to our kwargs
    def stop(self):
        self.event

    def cancel(self):
        if(self.isSerial == True):
            try:
                self.scalePort.close()
                self.running = False
                self.pumpPort.close()
            except: 
                self.scalePort = None
                self.pumpPort = None
        else:
            
            self.signals.pumpStop.emit()
            self.scalePort.close()
            self.running = False
    def factor_conversion(self):
        if 0 < self.max < 5001:
            factor = 0.9
        elif 5001 <= self.max < 20001:
            factor = 0.99
        elif 20001 <= self.max:
            factor = 0.999
        return factor 

    def convertToVoltage(self, rpm):
        volt = self.rpm*0.016 
    @Slot()
    def run(self):
        if(self.isSerial == True):
            if(self.pumpPort):
                self.pumpPort.close()

        while(self.running):
            try:
                s = self.scalePort.get_weight()
                if s:
                    num = s[0]
                    inum = int(num)
                    result = str(num)
                    self.signals.result.emit(result)
                    self.signals.progress.emit(100 * inum/int(0.9*self.factor_conversion()))
                    if (inum > int(self.factor_conversion())):
                        self.cancel()
                        break
   
                if self.scalePort is None:
                    self.cancel()
                    break
            except:
                 self.cancel()
                 break
           # Return the result of the processin
              # Done
        if (self.running == False):
            self.signals.finished.emit()


         
class SerialControls(QMainWindow, Ui_MainWindow):
    text_update = Signal(str)
    start_scale = Signal(str)


    def __init__(self):
        super(SerialControls, self).__init__()
        self.setupUi(self)
        sys.stdout = self
        self.speed = 0
        app.aboutToQuit.connect(self.closeEvent)
        self.direction = False

        self.res = ''   
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.scalePortList.addItem(port.device)
            self.pumpPortList.addItem(port.device)
        if(len(ports)<=1):
            self.pump = MasterflexPump()
        self.stopButton.clicked.connect(self.stopShit)
        self.setWindowTitle("Sup")
        self.counter = 0
        self.timer = QTimer()
        self.event_stop = threading.Event()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.progressBar.setValue(1)
        self.progressBar.minimum = 0
        self.rpm = self.dial.value
        self.progressBar.maximum = 100
        self.pumpStarted = False
        self.dial.valueChanged.connect(self.change_speed)
        if(self.serialCheck == True):
            try:
                self.pumpPort = serial.Serial(port=self.pumpPortList.currentText(), baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
            except:
                self.pumpPort = None

        self.threadpool = QThreadPool()
        self.expStart.clicked.connect(self.startTheExp)
        self.mutex = QMutex()
    def closeEvent(self):
        self.resultBox.appendPlainText('Close button pressed')
        import sys
        sys.exit(0)
    def stopPump(self):
        self.pumpStarted = False
        self.pump.stop()

    def stopShit(self):
        self.event_stop.set()
        self.timer.stop()
        self.expStart.setChecked(False)
        if(self.serialCheck==True):
            self.pumpPort = serial.Serial(port=self.pumpPortList.currentText(), baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
        elif(self.serialCheck ==False):
            if(self.pumpStarted == True):
                self.pump.cancel()

        self.resultBox.appendPlainText('Shit has stopped, hopefully')
    def change_speed(self):
        rpm = self.dial.value
       
        self.pump.changeSpeed(rpm)     
    def change_dir(self):
        self.pump.changeDir()       

    def setText(self, s):
        self.mutex.lock()
        self.res = s
        self.mutex.unlock()
    def startTheExp(self):
        name =self.scalePortList.currentText()
        self.timer.start()
        self.expStart.setChecked(True)
        if(self.serialCheck.isChecked() == True):


           
            pumpname = self.pumpPortList.currentText()
            try:
                max = float(str(self.weightBox.text()))
            except:
                max = 0.00
            try:
                self.pumpPort.close()
            except:
                self.pumpPort = None
        elif(self.serialCheck.isChecked() == False):
            try:
                pumpname = "PWM"
                self.pumpStarted = True
                self.pump.start()
                max = float(str(self.weightBox.text()))
            except:
                max = 0.00
            


        worker = Worker(name, pumpname, max, self.serialCheck.isChecked())
        worker.signals.result.connect(self.setText)
        worker.signals.finished.connect(self.stopShit)
        worker.signals.progress.connect(self.setBar)
        worker.singals.pumpStop.connect(self.stopPump)
        self.threadpool.start(worker)

   
    def setBar(self, per):
        self.progressBar.setValue(per)

    def recurring_timer(self):
        self.resultBox.appendPlainText(self.res)
        

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    main = SerialControls()
    main.show()
    sys.exit(app.exec_())