import log
from hardware.irq import *


class Timer:

    def __init__(self, interruptVector):
        self._interruptVector = interruptVector
        self._quantum = None
        self._counter = None
        self._is_on = False

    @property
    def quantum(self):
        return self._quantum

    @property
    def counter(self):
        return self._counter

    @property
    def is_on(self):
        return self._is_on

    def tick(self, tickNbr):
        if self._is_on:
            self._counter -= 1
            log.logger.info("Counter value: " + str(self._counter))
            if self._counter == 0:
                log.logger.info("Process time finished")
                timeoutIRQ = IRQ(TIME_OUT_INTERRUPTION_TYPE)
                self._interruptVector.handle(timeoutIRQ)

    def set_on(self, value):
        self._is_on = True
        self._quantum = value
        self._counter = value
        log.logger.info("Timer is set on with quantum " + str(self._quantum) + " and counter " + str(self._counter))

    def reset(self):
        if self._is_on:
            self._counter = self._quantum - 1
            log.logger.info("Timer reset")

    def __repr__(self):
        return "TIMER\nTimer is on: {status} \nQuantum: {quantum} \nCounter: {counter}" \
            .format(status=self.is_on, quantum=self.quantum, counter=self.counter)