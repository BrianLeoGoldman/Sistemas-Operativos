import log


## emulates the Interrupt Vector Table
class InterruptVector():

    def __init__(self):
        self._handlers = dict()

    def register(self, interruptionType, interruptionHandler):
        self._handlers[interruptionType] = interruptionHandler

    def handle(self, irq):
        log.logger.info("Handling {type} irq with parameters = {parameters}"
                        .format(type=irq.type, parameters=irq.parameters ))
        self._handlers[irq.type].execute(irq)