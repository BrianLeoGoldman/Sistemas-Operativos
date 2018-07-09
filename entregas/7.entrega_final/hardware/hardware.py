#!/usr/bin/env python

from time import sleep
from tabulate import tabulate
import log

from hardware.cpu import *
from hardware.memory import *
from hardware.swap import *
from hardware.timer import *
from hardware.clock import *
from hardware.interrupt_vector import *
from hardware.io_device import *
from hardware.mmu import *
from hardware.disk import *


## emulates the Hardware that were the Operative System run
class Hardware():

    ## Setup our hardware
    def setup(self, frame_size):
        ## add the components to the "motherboard"
        self._swap = Swap(frame_size * 2)
        self._disk = Disk()
        self._memory = Memory(frame_size * 4)
        self._interruptVector = InterruptVector()
        self._clock = Clock()
        self._timer = Timer(self._interruptVector)
        self._ioDevice = PrinterIODevice()
        self._mmu = MMUPagination(self._memory)  # TODO: change for MMUPaginationOnDemand
        self._cpu = Cpu(self._mmu, self._interruptVector)
        self._clock.addSubscriber(self._timer)
        self._clock.addSubscriber(self._ioDevice)
        self._clock.addSubscriber(self._cpu)

    def switchOn(self):
        log.logger.info(" ---- SWITCH ON ---- ")
        return self.clock.start()

    def switchOff(self):
        self.clock.stop()
        log.logger.info(" ---- SWITCH OFF ---- ")

    @property
    def cpu(self):
        return self._cpu

    @property
    def clock(self):
        return self._clock

    @property
    def timer(self):
        return self._timer

    @property
    def interruptVector(self):
        return self._interruptVector

    @property
    def memory(self):
        return self._memory

    @property
    def disk(self):
        return self._disk

    @property
    def swap(self):
        return self._swap

    def addProgram(self, program):
        self._disk.addProgram(program)

    @property
    def mmu(self):
        return self._mmu

    @property
    def ioDevice(self):
        return self._ioDevice

    def add_suscriber(self, suscriber):
        self.clock.addSubscriber(suscriber)

    def __repr__(self):
        return "HARDWARE state {cpu}\n{mem}".format(cpu=self._cpu, mem=self._memory)

### HARDWARE is a global variable
### can be access from any
HARDWARE = Hardware()
