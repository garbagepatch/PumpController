import RPi.GPIO as gp


class MasterflexPump():

    def __init__(self):
        self.isSetup = False
        self.dc = 0
        self.direction = True
        self.setup()
    def setup(self):
        if(self.isSetup == False):
            self.isSetup = True
            gp.setmode(gp.BOARD)


            gp.setup(35, gp.OUT)
            gp.setup(32, gp.OUT)
            gp.setup(38, gp.OUT)
            self.p = gp.PWM(32, 2000)
    
    def changeDir(self): 
       # gp.setup(36, gp.OUT)
        if(self.direction):
            gp.output(36, 1)
        else:
            gp.output(36, 0)
    def close(self):
        self.p.ChangeDutyCycle(0)
        gp.output(35, 0)
        gp.cleanup()
        self.setup = False
    def start(self, speed):
        if(self.setup == False):
            self.setup()
        self.dc = speed/6
        self.p.start(self.dc)
        gp.output(35, 1)
    def stop(self):
        gp.output(35, 0)
    def changeSpeed(self, speed):
        self.dc = speed
        self.p.ChangeDutyCycle(self.dc)


        
