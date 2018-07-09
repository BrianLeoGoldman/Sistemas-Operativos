import log
from time import sleep

## emulates the Internal Clock
class Clock():

    def __init__(self):
        self._subscribers = []
        self._running = False
        self._tickNbr = 0

    @property
    def tickNbr(self):
        return self._tickNbr

    @tickNbr.setter
    def tickNbr(self, value):
        self._tickNbr = value

    def addSubscriber(self, subscriber):
        self._subscribers.append(subscriber)

    def stop(self):
        self._running = False

    def start(self):
        log.logger.info("---- :::: START CLOCK  ::: -----")
        self._running = True
        self.tickNbr = 0
        while (self._running):
            self.tick()

    def tick(self):
        log.logger.info("        --------------- tick: {tickNbr} ---------------".format(tickNbr=self.tickNbr))
        ## notify all subscriber that a new clock cycle has started
        for subscriber in self._subscribers:
            subscriber.tick(self.tickNbr)
        self.tickNbr += 1
        ## wait 1 second and keep looping
        sleep(1)

    def do_ticks(self, times):
        log.logger.info("---- :::: CLOCK do_ticks: {times} ::: -----".format(times=times))
        for tickNbr in range(0, times):
            self.tick()