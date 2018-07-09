from software.interruption_handlers import *
from software.memory_manager import *
from software.swap_manager import *
from software.io_controller import *
from software.loader import *
from software.dispatcher import *
from software.pcb_table import *
from software.program import *


# emulates the core of an Operative System
class Kernel:

    def __init__(self, frame_size, scheduler):

        # TODO: set dependency injection to decide pagination mode

        # setup interruption handlers
        kill_handler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, kill_handler)

        io_in_handler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, io_in_handler)

        io_out_handler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, io_out_handler)

        new_handler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, new_handler)

        time_out_handler = TimeOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIME_OUT_INTERRUPTION_TYPE, time_out_handler)

        page_fault_handler = PageFaultInterruptionHandler(self)
        HARDWARE.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, page_fault_handler)

        # controls the Hardware's I/O Device
        self._io_device_controller = IoDeviceController(self, HARDWARE.ioDevice)
        self._memory_manager = MemoryManagerPagination(self, frame_size, HARDWARE.memory.size)
        # TODO: change for MemoryManagerPaginationOnDemand
        self._swap_manager = SwapManager(self, frame_size)
        self._loader = Loader(self)
        self._dispatcher = Dispatcher(self)
        self._table = PCBTable(30)
        scheduler.kernel = self
        self._scheduler = scheduler

    @property
    def memory_manager(self):
        return self._memory_manager

    @property
    def swap_manager(self):
        return self._swap_manager

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
    def io_device_controller(self):
        return self._io_device_controller

    @property
    def scheduler(self):
        return self._scheduler

    def has_next(self):
        return self.scheduler.has_next()

    def next(self):
        return self.scheduler.next()

    def add(self, pcb):
        self.scheduler.add(pcb)

    def has_running(self):
        return self.scheduler.has_current()

    def get_current(self):
        return self.scheduler.current

    def set_current(self, pcb):
        self.change_state(pcb, "Running")
        self.scheduler.set_current(pcb)

    # emulates a "system call" for programs execution
    def execute(self, program_name):
        instructions = HARDWARE.disk.getProgram(program_name)
        program = Program(program_name, instructions)
        new_irq = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(new_irq)
        log.logger.info("\nExecuting program: {name}".format(name=program_name))
        # self.dispatcher.start() # TODO: make sure this is not necessary!!!

    def has_finished(self):
        return (not self.has_next()) & (self.io_device_controller.has_finished())

    def terminate(self):
        self.scheduler.set_current(None)
        self.table.current = None
        self.dispatcher.idle()

    def change_state(self, pcb, new_state):
        pcb.state = new_state
        if new_state == "Running":
            self.table.current = pcb

    def __repr__(self):
        return "Kernel "