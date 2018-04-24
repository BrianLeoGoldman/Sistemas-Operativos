#!/usr/bin/env python

from hardware import *
import log
import random


# emulates a compiled program
class Program:

    def __init__(self, program_name, instructions):
        self._name = program_name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def add_instr(self, instruction):
        instruction1 = instruction
        self._instructions.append(instruction1)

    @staticmethod
    def expand(instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                # is a list of instructions
                expanded.extend(i)
            else:
                # a single instr (a String)
                expanded.append(i)

        # now test if last instruction is EXIT
        # if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})"\
            .format(name=self._name, instructions=self._instructions)


# emulates an Input/Output device controller (driver)
class IoDeviceController:

    def __init__(self, kernel, device):
        self._device = device
        self._waiting_queue = []
        self._current_pcb = None
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def run_operation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def get_finished_pcb(self):
        finished_pcb = self._current_pcb
        self._current_pcb = None
        self.__load_from_waiting_queue_if_apply()
        return finished_pcb

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            # pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            # print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._current_pcb = pcb
            self._device.execute(instruction)

    def has_finished(self):
        return (len(self._waiting_queue) == 0) & (self._current_pcb is None)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}"\
            .format(deviceID=self._device.deviceId, currentPCB=self._current_pcb, waiting_queue=self._waiting_queue)


# emulates the  Interruptions Handlers
class AbstractInterruptionHandler:
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDE in class {classname}"
                         .format(classname=self.__class__.__name__))

    def get_ready(self, pcb):
        if self.kernel.has_running():
            self.kernel.add(pcb)
            self.kernel.change_state(pcb, "Ready")
        else:
            self.kernel.set_current(pcb)
            self.kernel.dispatcher.load(pcb)
            self.kernel.change_state(pcb, "Running")

    def context_switch(self):
        self.kernel.dispatcher.context_switch()


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcb = self.kernel.scheduler.current
        self.kernel.change_state(pcb, "Terminated")
        self.kernel.terminate()
        self.kernel.dispatcher.save(pcb)
        self.context_switch()


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.scheduler.current
        self.kernel.change_state(pcb, "Waiting")
        self.kernel.dispatcher.save(pcb)
        self.kernel.io_device_controller.run_operation(pcb, operation)
        self.kernel.terminate()
        log.logger.info(self.kernel.io_device_controller)
        self.context_switch()


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.io_device_controller.get_finished_pcb()
        log.logger.info(self.kernel.io_device_controller)
        self.get_ready(pcb)


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        program = irq.parameters
        base_dir = self.kernel.loader.available_cell
        length = len(program.instructions)
        self.kernel.loader.load(program)
        pcb = self.kernel.create_pcb(program.name, base_dir, base_dir + length)
        self.get_ready(pcb)


class TimeOutInterruptionHandler(AbstractInterruptionHandler):
    # TODO: check handler

    def execute(self, irq):
        if self.kernel.has_running():
            old_pcb = self.kernel.scheduler.current
            self.kernel.dispatcher.save(old_pcb)
            self.kernel.scheduler.add(old_pcb)
            self.kernel.dispatcher.context_switch()


# emulates the core of an Operative System
class Kernel:

    def __init__(self):
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

        # controls the Hardware's I/O Device
        self._io_device_controller = IoDeviceController(self, HARDWARE.ioDevice)

        self._loader = Loader()
        self._dispatcher = Dispatcher(self)
        self._table = PCBTable(30)
        # self._scheduler = FirstComeFirstServed(self)
        # self._scheduler = RoundRobin(self, 4)
        self._scheduler = Priority(self, False)
        # self._scheduler = ShortestJobFirst(self)

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
        log.logger.info("\n Executing program: {name}"
                        .format(name=program_name))
        # log.logger.info(HARDWARE)
        self.dispatcher.start()

    def has_finished(self):
        return (not self.has_next()) & (self.io_device_controller.has_finished())

    def terminate(self):
        self.scheduler.set_current(None)
        self.table.current = None
        self.dispatcher.idle()

    def create_pcb(self, name, base_dir, max_dir):
        pcb = PCB(name, base_dir, max_dir)
        self.table.add_pcb(pcb)
        return pcb

    def change_state(self, pcb, new_state):
        pcb.state = new_state
        if new_state == "Running":
            self.table.current = pcb

    def __repr__(self):
        return "Kernel "


class SchedulingAlgorithm:

    def __init__(self, kernel):
        self._current = None
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    @property
    def current(self):
        return self._current

    def has_current(self):
        return not (self.current is None)

    def set_current(self, pcb):
        self._current = pcb


class FirstComeFirstServed(SchedulingAlgorithm):
    # Processes are assigned the CPU in the order they request it
    # Non-preemptive (lets a process run until it blocks)

    def __init__(self, kernel):
        super().__init__(kernel)
        self._queue = []

    def add(self, pcb):
        self._queue.append(pcb)
        self.kernel.change_state(pcb, "Ready")

    def next(self):
        return self._queue.pop(0)

    def has_next(self):
        return len(self._queue) > 0

    def print_ready(self):
        for pcb in self._queue:
            print(pcb)


class RoundRobin(SchedulingAlgorithm):
    # Each process is assigned a time interval (quantum), during which it is allowed to run
    # Preemptive (lets a process run for a maximum of some fixed time)

    def __init__(self, kernel, value):
        super().__init__(kernel)
        self._queue = []
        HARDWARE.timer.set_on(value)

    def add(self, pcb):
        self._queue.append(pcb)
        self.kernel.change_state(pcb, "Ready")

    def next(self):
        return self._queue.pop(0)

    def has_next(self):
        return len(self._queue) > 0

    def print_ready(self):
        for pcb in self._queue:
            print(pcb)


class Priority(SchedulingAlgorithm):
    # Each process is assigned a priority, and the runnable process with the highest priority is allowed to run
    # The priority has to be a value between a finite range
    # Non-preemptive
    # Preemptive

    def __init__(self, kernel, boolean):
        super().__init__(kernel)
        self._is_preemptive = boolean
        self._priorities = [[], [], [], [], []]
        # for i in self._priorities:
        #     self._priorities[i] = []
        self._has_pcbs = [False, False, False, False, False]

    def add(self, pcb):
        priority = pcb.priority
        print(pcb)
        log.logger.info("La prioridad es" + str(priority))
        log.logger.info("La cantidad de colas es " + str(len(self._priorities)))
        self._priorities[priority].append(pcb)
        self._has_pcbs[priority] = True

    def next(self):
        # TODO: aging is implemented here
        i = self._has_pcbs.index(True)
        if len(self._priorities[i]) == 1:
            self._has_pcbs[i] = False
        return self._priorities[i].pop(0)

    def has_next(self):
        return any(b == True for b in self._has_pcbs)

    def print_ready(self):
        for i in range(0, 5):
            print(self._priorities[i])


class ShortestJobFirst(SchedulingAlgorithm):
    # The process with the shortest CPU burst is allowed to run
    # Non-preemptive
    # Preemptive

    def __init__(self, kernel):
        super().__init__(kernel)
        self._queue = []

    def add(self, pcb):
        pass
        # TODO: implement add
        # time = pcb.remaining
        # if time < self._current.remaining:
        #     oldCurrent = self.current
        #     self.setCurrent(None)
        #     self.kernel.switchPCBs(oldCurrent, pcb)
        # else:
        #     self._queue.append(pcb)
        #     self.kernel.changeState(pcb, "Ready")
        #     sorted(self._queue, key=lambda time: pcb.remaining)  # sort by time CPU burst

    def next(self):
        return self._queue.pop(0)

    def has_next(self):
        return len(self._queue) > 0

    def print_ready(self):
        for pcb in self._queue:
            print(pcb)


class PCBTable:

    def __init__(self, size):
        self._elements = [] * size
        self._counter = 0
        self._current = None

    @property
    def elements(self):
        return self._elements

    @property
    def counter(self):
        return self._counter

    def add_counter(self):
        self._counter = self._counter + 1

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, pcb):
        self._current = pcb

    def add_pcb(self, pcb):
        pcb.set_pid(self.counter)
        self.add_counter()
        self._elements.append(pcb)
        return pcb

    def get_pcb(self, pid):
        pcb = self._elements[pid]
        return pcb

    def update_state(self, pid, state):
        for pcb in self.elements:
            if pcb.pid == pid:
                pcb.state = state


class PCB:

    def __init__(self, name, base_dir, max_dir):
        self._pid = None
        self._name = name
        self._state = "New"
        self._base_dir = base_dir
        self._max_dir = max_dir
        self._pc = 0
        self._priority = random.randint(0, 4)
        # TODO: review priority

    @property
    def pid(self):
        return self._pid

    @property
    def name(self):
        return self._name

    def set_pid(self, pid):
        self._pid = pid

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self._state = new_state

    @property
    def base_dir(self):
        return self._base_dir

    @property
    def max_dir(self):
        return self._max_dir

    @property
    def pc(self):
        return self._pc

    def set_pc(self, pc):
        self._pc = pc

    @property
    def priority(self):
        return self._priority

    def __repr__(self):
        return "PCB ---> pid: {pid} program: {name} state: {state} " \
               "baseDir: {baseDir} maxDir: {maxDir} priority: {priority} pc: {pc}" \
            .format(pid=self.pid, name=self.name, state=self.state,
                    baseDir=self.base_dir, maxDir=self.max_dir, priority=self.priority, pc=self.pc)


class Loader:

    def __init__(self):
        self._available_cell = 0

    @property
    def available_cell(self):
        return self._available_cell

    @available_cell.setter
    def available_cell(self, value):
        self._available_cell = value

    def load(self, program):
        prog_size = len(program.instructions)
        for index in range(0, prog_size):
            inst = program.instructions[index]
            HARDWARE.memory.put(self.available_cell + index, inst)
        self.available_cell = self.available_cell + prog_size


class Dispatcher:

    def __init__(self, kernel):
        self._kernel = kernel

    @staticmethod
    def save(pcb):
        pcb.set_pc(HARDWARE.cpu.pc)
        HARDWARE.cpu.pc = -1

    def load(self, pcb):
        HARDWARE.mmu.base_dir = pcb.base_dir
        HARDWARE.mmu.limit = pcb.max_dir
        HARDWARE.cpu.pc = pcb.pc
        if self._kernel.has_running():
            HARDWARE.timer.reset()

    @staticmethod
    def start():
        # set CPU program counter at program's first instruction
        HARDWARE.cpu.pc = 0

    @staticmethod
    def idle():
        # set CPU program counter at -1
        HARDWARE.cpu.pc = -1

    def context_switch(self):
        if self._kernel.has_next():
            pcb = self._kernel.next()
            self._kernel.set_current(pcb)
            self.load(pcb)
            self._kernel.change_state(pcb, "Running")
