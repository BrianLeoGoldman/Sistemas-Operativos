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
        return "Program({name}, {instructions})" \
            .format(name=self._name, instructions=self._instructions)


# emulates an Input/Output device controller (driver)
class IoDeviceController:

    def __init__(self, kernel, device):
        self._device = device
        self._waiting_queue = []
        self._current_pcb = None
        self._kernel = kernel

    @property
    def waiting_queue(self):
        return self._waiting_queue

    @property
    def current_pcb(self):
        return self._current_pcb

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
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}" \
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
            if self.kernel.scheduler.check_preemptive():
                self.check_priorities(pcb)
            else:
                self.kernel.add(pcb)
                self.kernel.change_state(pcb, "Ready")
        else:
            self.kernel.set_current(pcb)
            self.kernel.dispatcher.load(pcb)
            self.kernel.change_state(pcb, "Running")

    def context_switch(self):
        self.kernel.dispatcher.context_switch()

    def check_priorities(self, pcb):
        current = self.kernel.get_current()
        if pcb.priority < current.priority:
            log.logger.info(" Switching processes based on priority ")
            self.kernel.dispatcher.save(current)
            self.kernel.add(current)
            self.kernel.change_state(current, "Ready")
            self.kernel.set_current(pcb)
            self.kernel.dispatcher.load(pcb)
            self.kernel.change_state(pcb, "Running")
        else:
            self.kernel.add(pcb)
            self.kernel.change_state(pcb, "Ready")


class KillInterruptionHandler(AbstractInterruptionHandler):
    # TODO: this interruption should release memory

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcb = self.kernel.scheduler.current
        self.kernel.change_state(pcb, "Terminated")
        self.kernel.terminate()
        self.kernel.dispatcher.save(pcb)
        self.kernel.memory_manager.release_space(pcb.pid)
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
        # TODO: when the Loader loads a program, it should return a boolean indicating if the loading was successful?
        pcb = self.kernel.create_pcb(program.name)
        self.kernel.loader.load(program, pcb.pid)
        self.get_ready(pcb)


class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        if self.kernel.has_running():
            old_pcb = self.kernel.scheduler.current
            self.kernel.dispatcher.save(old_pcb)
            self.kernel.scheduler.add(old_pcb)
            self.kernel.dispatcher.context_switch()


class PageFaultInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        page_number = irq.parameters
        pid = self.kernel.get_current().pid
        page_table = self.kernel.memory_manager.find_table(pid)
        row = page_table.find_row(page_number)
        if row.swap:
            pass
            # TODO: Look in swap
        else:
            program_name = self.kernel.get_current().name
            program = HARDWARE.disk.getProgram(program_name)
            log.logger.info(program)
            self.kernel.loader.load_page(program, page_number, self.kernel.memory_manager.next_frame())
            # TODO: Look in HDD
        # TODO: the page_table has to be updated (the page is now associated with a frame and the valid_bit is True)


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

        page_fault_handler = PageFaultInterruptionHandler(self)
        HARDWARE.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, page_fault_handler)

        # controls the Hardware's I/O Device
        self._io_device_controller = IoDeviceController(self, HARDWARE.ioDevice)
        self._memory_manager = MemoryManager(4, HARDWARE.memory.size)
        self._loader = Loader(self.memory_manager)
        self._dispatcher = Dispatcher(self)
        self._table = PCBTable(30)
        self._scheduler = FirstComeFirstServed(self)
        # self._scheduler = RoundRobin(self, 4)
        # self._scheduler = Priority(self, True)
        # self._scheduler = ShortestJobFirst(self)

    @property
    def memory_manager(self):
        return self._memory_manager

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

    def create_pcb(self, name):
        pcb = PCB(name)
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

    def check_preemptive(self):
        return False


class FirstComeFirstServed(SchedulingAlgorithm):
    # Processes are assigned the CPU in the order they request it
    # Non-preemptive (lets a process run until it blocks)

    def __init__(self, kernel):
        super().__init__(kernel)
        self._queue = []

    @property
    def queue(self):
        return self._queue

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

    @property
    def queue(self):
        return self._queue

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
        self._queue = [[], [], [], [], []]
        self._has_pcbs = [False, False, False, False, False]

    @property
    def queue(self):
        return self._queue

    def add(self, pcb):
        priority = pcb.priority
        self._queue[priority].append(pcb)
        self._has_pcbs[priority] = True

    def next(self):
        level = self._has_pcbs.index(True)
        next_pcb = self._queue[level].pop(0)
        self.check_level(level)
        self.aging()
        return next_pcb

    def aging(self):
        for i in range(1, 5):
            if self._has_pcbs[i]:
                going_up = self._queue[i].pop(0)
                self._queue[i - 1].append(going_up)
                self.check_level(i)
                self.check_level(i-1)

    def check_level(self, level):
        if len(self._queue[level]) == 0:
            self._has_pcbs[level] = False
        else:
            self._has_pcbs[level] = True

    def has_next(self):
        return any(b == True for b in self._has_pcbs)

    def check_preemptive(self):
        return self._is_preemptive

    def print_ready(self):
        for i in range(0, 5):
            print(self._queue[i])


class ShortestJobFirst(SchedulingAlgorithm):
    # The process with the shortest CPU burst is allowed to run
    # Non-preemptive
    # Preemptive

    def __init__(self, kernel):
        super().__init__(kernel)
        self._queue = []

    def add(self, pcb):
        pass

    def next(self):
        pass

    def has_next(self):
        pass

    def print_ready(self):
        pass


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

    def __init__(self, name):
        self._pid = None
        self._name = name
        self._state = "New"
        self._pc = 0
        self._priority = random.randint(0, 4)

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
    def pc(self):
        return self._pc

    def set_pc(self, pc):
        self._pc = pc

    @property
    def priority(self):
        return self._priority

    def __repr__(self):
        return "PCB ---> pid: {pid} program: {name} state: {state} " \
               "priority: {priority} pc: {pc}" \
            .format(pid=self.pid, name=self.name, state=self.state,
                    priority=self.priority, pc=self.pc)


class Loader:

    def __init__(self, manager):
        self._memory_manager = manager
        self._frame_size = manager.frame_size

    @property
    def memory_manager(self):
        return self._memory_manager

    @property
    def frame_size(self):
        return self._frame_size

    def load(self, program, pid):
        if self.memory_manager.has_enough_space(len(program.instructions)):
            prog_size = len(program.instructions)
            page_table = self.create_page_table(pid, prog_size, self.frame_size)
            # for page_tuple in page_table.table:
            #    self.load_page(program, page_tuple[0], page_tuple[1])
            # TODO: it should not load anything at the beginning, only when there is #PAGE_FAULT
        else:
            # TODO: if there is not enough space, another process page should be removed from memory
            log.logger.info("The amount of empty space is insufficient to load this program")
            raise SystemExit

    def create_page_table(self, pid, prog_size, frame_size):
        pages_number = prog_size / frame_size + 1
        table = PageTable(pid)
        for page in range(0, int(pages_number)):
            # self.memory_manager.next_frame()
            table.add(page, None)
        self.memory_manager.add_table(table)
        log.logger.info(table)
        return table

    def load_page(self, instructions, page, frame):
        log.logger.info("Loading Page " + str(page) + " in Frame " + str(frame))
        base_dir_program = page * self.frame_size
        base_dir_memory = frame * self.frame_size
        prog_size = len(instructions)
        counter = 0
        while (counter < self.frame_size) & (base_dir_program < prog_size):
            instruction = instructions[base_dir_program]
            HARDWARE.memory.put(base_dir_memory + counter, instruction)
            base_dir_program = base_dir_program + 1
            counter = counter + 1
        log.logger.info("Page " + str(page) + " loaded successfully")


class Dispatcher:

    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    @staticmethod
    def save(pcb):
        pcb.set_pc(HARDWARE.cpu.pc)
        HARDWARE.cpu.pc = -1

    def load(self, pcb):
        table = self.kernel.memory_manager.find_table(pcb.pid)
        HARDWARE.mmu.page_table = table
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


class MemoryManager:

    def __init__(self, frame_size, memory_size):
        self._frame_size = frame_size
        self._free_memory = memory_size
        self._page_table = []
        self._free_frames = []
        self._used_frames = []
        pages_number = self._free_memory / self.frame_size
        for index in range(0, int(pages_number)):
            self._free_frames.append(index)
        HARDWARE.mmu.frame_size = frame_size

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def free_memory(self):
        return self._free_memory

    @free_memory.setter
    def free_memory(self, value):
        self._free_memory = value

    @property
    def page_table(self):
        return self._page_table

    @property
    def free_frames(self):
        return self._free_frames

    @property
    def used_frames(self):
        return self._used_frames

    def next_frame(self):
        frame = self.free_frames.pop(0)
        self.free_memory = self.free_memory - self.frame_size
        self.used_frames.append(frame)
        return frame

    def add_table(self, table):
        self.page_table.append(table)

    def find_table(self, pid):
        res = None
        for table in self.page_table:
            if table.pid == pid:
                res = table.clone()
        return res

    def has_enough_space(self, program_size):
        return self.free_memory >= program_size

    def release_space(self, pid):
        used_frames = self.process_used_frames(pid)
        self.free_memory = self.free_memory + len(used_frames) * self.frame_size
        for frame in used_frames:
            self.used_frames.remove(frame)
            self.free_frames.append(frame)

    def process_used_frames(self, pid):
        page_table = self.find_table(pid)
        final_list = []
        for pair in page_table.table:
            final_list.append(pair[1])
        return final_list


class PageRow:

    def __init__(self, page_number, frame_number):
        self._page = page_number
        self._frame = frame_number
        self._valid_bit = False
        self._swap = False

    @property
    def page(self):
        return self._page

    @property
    def frame(self):
        return self._frame

    @property
    def valid_bit(self):
        return self._valid_bit

    @property
    def swap(self):
        return self._swap

    def __repr__(self):
        return "Row ---> page: {page} frame: {frame} valid_bit: {valid_bit} swap: {swap}"\
            .format(page=self.page, frame=self.frame, valid_bit=self.valid_bit, swap=self.swap)


class PageTable:

    def __init__(self, pid):
        self._pid = pid
        self._page_list = []

    @property
    def pid(self):
        return self._pid

    @property
    def page_list(self):
        return self._page_list

    @page_list.setter
    def page_list(self, new_list):
        self._page_list = new_list

    def add(self, page, next_frame):
        self._page_list.append(PageRow(page, next_frame))

    def clone(self):
        res = PageTable(self.pid)
        res.page_list = self.page_list
        return res

    def find_row(self, page_number):
        res = None
        for page_row in self.page_list:
            if page_row.page == page_number:
                res = page_row
        return res

    def page_is_loaded(self, page_number):
        row = self.find_row(page_number)
        return row.valid_bit

    def __repr__(self):
        return "Page Table ---> pid: {pid} list: {list}".format(pid=self.pid, list=self.page_list)
