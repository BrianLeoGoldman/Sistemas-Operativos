#!/usr/bin/env python

from hardware import *
import log



## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        instruction1 = instruction
        self._instructions.append(instruction1)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        pcb.state = "Waiting"
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def hasFinished(self):
        return (len(self._waiting_queue) == 0) & (self._currentPCB is None)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def getReady(self, pcb):
        if self.kernel.hasRunning():
            self.kernel.addToReady(pcb)
            pcb.state = "Ready"
        else:
            self.kernel.setCurrent(pcb)
            self.kernel.dispatcher.load(pcb)
            pcb.state = "Running"

    def contextSwitch(self):
        if self.kernel.hasReady():
            pcb = self.kernel.nextReady()
            self.kernel.setCurrent(pcb)
            self.kernel.dispatcher.load(pcb)
            pcb.state = "Running"


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcb = self.kernel.getCurrent()
        pcb.state = "Terminated"
        self.kernel.terminate()
        self.kernel.dispatcher.save(pcb)
        self.contextSwitch()

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.table.getCurrent()
        self.kernel.dispatcher.save(pcb)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        self.kernel.terminate()
        log.logger.info(self.kernel.ioDeviceController)
        self.contextSwitch()


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        log.logger.info(self.kernel.ioDeviceController)
        self.getReady(pcb)


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        program = irq.parameters
        baseDir = self.kernel.loader.availableCell
        self.kernel.loader.load(program)
        pcb = self.kernel.createPCB(baseDir, baseDir + len(program.instructions))
        self.getReady(pcb)



# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        self._loader = Loader()
        self._dispatcher = Dispatcher()
        self._table = PCBTable(30)
        self._ready = []

    @property
    def loader(self):
        return self._loader

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def table(self):
        return self._table

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def ready(self):
        return self._ready

    def hasReady(self):
        return len(self._ready) > 0

    def nextReady(self):
        return self.ready.pop(0)

    def hasRunning(self):
        return self.table.hasCurrent()

    def addToReady(self, pcb):
        self._ready.append(pcb)

    def getCurrent(self):
        return self.table.current

    def setCurrent(self, pcb):
        self.table.current = pcb

    ## emulates a "system call" for programs execution
    def execute(self, program):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(newIRQ)

        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first instruction
        HARDWARE.cpu.pc = 0

    def hasFinished(self):
        return (not self.hasReady()) & (self.ioDeviceController.hasFinished())

    def terminate(self):
        self.table.current = None
        HARDWARE.cpu.pc = -1


    def createPCB(self, baseDir, maxDir):
        pcb = PCB(baseDir, maxDir)
        self.table.addPCB(pcb)
        return pcb

    def addReady(self, pcb):
        self._ready.append(pcb)

    def __repr__(self):
        return "Kernel "


class PCBTable():

    def __init__(self, size):
        self._elements = [ ] * size
        self._current = None
        self._counter = 0

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current):
        self._current = current

    @property
    def counter(self):
        return self._counter

    def addCounter(self):
        self._counter = self._counter + 1

    def hasCurrent(self):
        return not (self.current is None)

    def getCurrent(self):
        return self.current

    def addPCB(self, pcb):
        pcb.setPID(self.counter)
        self.addCounter()
        self._elements.append(pcb)
        return pcb

    def getPCB(self, pid):
        pcb = self._elements[pid]
        return pcb


class PCB():

    def __init__(self, baseDir, maxDir):
        self._pid = None
        self._state = "New"
        self._baseDir = baseDir
        self._maxDir = maxDir
        self._pc = 0

    @property
    def pid(self):
        return self._pid

    def setPID(self, pid):
        self._pid = pid

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, newState):
        self._state = newState

    @property
    def baseDir(self):
        return self._baseDir

    @property
    def maxDir(self):
        return self._maxDir

    @property
    def pc(self):
        return self._pc

    def setPC(self, pc):
        self._pc = pc

    def __repr__(self):
        return "PCB ---> pid: {pid} state: {state} baseDir: {baseDir} maxDir: {maxDir} pc: {pc}"\
            .format(pid=self.pid, state=self.state, baseDir=self.baseDir, maxDir=self.maxDir, pc=self.pc)

class Loader():

    def __init__(self):
        self._availableCell = 0

    @property
    def availableCell(self):
        return self._availableCell

    @availableCell.setter
    def availableCell(self, value):
        self._availableCell = value

    def load(self, program):
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.put(self.availableCell + index, inst)
        self.availableCell = self.availableCell + progSize

class Dispatcher():

    def save(self, pcb):
        pcb.setPC(HARDWARE.cpu.pc)
        HARDWARE.cpu.pc = -1

    def load(self, pcb):
        HARDWARE.mmu.baseDir = pcb.baseDir
        HARDWARE.mmu.limit = pcb.maxDir
        HARDWARE.cpu.pc = pcb.pc





