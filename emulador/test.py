from hardware import *
from so import *
import log

##
##  MAIN
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## create 3 programs
    ###################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(1)])
    prg2 = Program("prg2.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(2)])
    prg3 = Program("prg3.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3)])


    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(25)
    # add programs to hardware hard disk
    HARDWARE.addProgram(prg1)
    HARDWARE.addProgram(prg2)
    HARDWARE.addProgram(prg3)

    ## new create the Operative System Kernel
    kernel = Kernel()

    # execute all programs "concurrently"
    kernel.execute("prg1.exe")
    kernel.execute("prg2.exe")
    kernel.execute("prg3.exe")

    tickNbr = 0


    def tick():
        global tickNbr
        HARDWARE.clock.tick(tickNbr)
        tickNbr += 1

    def current():
        print(kernel.getCurrent())

    def memory():
        print(HARDWARE.memory)


    processDictionary = {
        "tick": tick,
        "current": current,
        "memory": memory
}

    def processInput(name):
        processDictionary[name]()

    ## start

    while(True):
        text = input()
        processInput(text)
