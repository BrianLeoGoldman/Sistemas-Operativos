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

    def execute(self, irq):
        log.logger.info("Program Finished ")
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
        pcb = self.kernel.table.create_pcb(program.name)
        self.kernel.memory_manager.create_page_table(pcb.pid, len(program.instructions))
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
        pcb = self.kernel.get_current()
        self.kernel.memory_manager.switch_table(pcb.pid, self.kernel.dispatcher.get_page_table())
        frame = self.kernel.memory_manager.next_frame()
        self.kernel.memory_manager.add_possible_victim(frame, page_number, pcb.pid)
        self.kernel.loader.load_page(pcb, page_number, frame)
        self.kernel.memory_manager.update_page_table(pcb.pid, page_number, frame)
        self.kernel.dispatcher.set_page_table(self.kernel.memory_manager.get_table(pcb.pid))


# emulates the core of an Operative System
class Kernel:

    def __init__(self, frame_size):
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
        self._memory_manager = MemoryManager(self, frame_size, HARDWARE.memory.size)
        self._swap_manager = SwapManager(self, frame_size)
        self._loader = Loader(self)
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
        self.dispatcher.start()

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

    def create_pcb(self, name):
        pcb = PCB(name)
        pcb.set_pid(self.counter)
        self.add_counter()
        self.elements.append(pcb)
        return pcb

    def get_pcb(self, pid):
        pcb = self._elements[pid]
        return pcb

    def update_state(self, pid, state):
        for pcb in self.elements:
            if pcb.pid == pid:
                pcb.state = state

    def __repr__(self):
        string = "\n"
        for pcb in self.elements:
            string = string + str(pcb) + "\n"
        return "PCB TABLE\nCurrent: {current} \nTable: {table}" \
            .format(current=self.current, table=string)


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

    def __init__(self, kernel):
        self._kernel = kernel
        self._frame_size = self.kernel.memory_manager.frame_size

    @property
    def kernel(self):
        return self._kernel

    @property
    def frame_size(self):
        return self._frame_size

    def load_page(self, pcb, page, frame):
        log.logger.info("Loading page")
        if self.kernel.memory_manager.page_is_in_swap(pcb.pid, page):
            log.logger.info("Its in swap")
            swap_frame = self.kernel.memory_manager.get_current_frame(pcb.pid, page)
            instructions = self.swap_out(swap_frame)
            self.kernel.swap_manager.release_frame(swap_frame)
            self.kernel.memory_manager.set_swap_flag(pcb.pid, swap_frame, False)
        else:
            log.logger.info("Its in disk")
            instructions = HARDWARE.disk.getPage(pcb.name, page, self.frame_size)
        base_dir_memory = frame * self.frame_size
        for instruction in instructions:
            HARDWARE.memory.put(base_dir_memory, instruction)
            base_dir_memory += 1

    def swap_in(self, victim_frame, swap_frame):
        offset = 0
        while offset < self.frame_size:
            instruction = HARDWARE.memory.get(victim_frame * self.frame_size + offset)
            HARDWARE.swap.put(swap_frame * self.frame_size + offset, instruction)
            offset = offset + 1

    def swap_out(self, frame):
        instructions = []
        base_dir = frame * self.frame_size
        counter = 0
        while counter < self.frame_size:
            instructions.append(HARDWARE.swap.get(base_dir))
            counter += 1
            base_dir += 1
        return instructions

    def update_page_table(self, pid, page, frame, swap_is_on):
        self.kernel.memory_manager.update_page_table(pid, page, frame, swap_is_on)
        HARDWARE.mmu.page_table.update(page, frame, swap_is_on)


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

    @staticmethod
    def get_page_table():
        return HARDWARE.mmu.page_table

    @staticmethod
    def set_page_table(new_table):
        HARDWARE.mmu.page_table = new_table

    @staticmethod
    def get_clock_tick():
        return HARDWARE.clock.tickNbr


class MemoryManager:

    def __init__(self, kernel, frame_size, memory_size):
        self._kernel = kernel
        self._frame_size = frame_size
        self._free_memory = memory_size
        self._page_table = {}
        self._free_frames = []
        self._used_frames = []
        self._victim_selector = FIFOPageReplacementAlgorithm(self)
        self.assign_frames()

    def assign_frames(self):
        frames_number = self._free_memory / self.frame_size
        for index in range(0, int(frames_number)):
            self._free_frames.append(index)
        HARDWARE.mmu.frame_size = self.frame_size

    @property
    def kernel(self):
        return self._kernel

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

    @property
    def victim_selector(self):
        return self._victim_selector

    def next_frame(self):
        if len(self.free_frames) > 0:
            frame = self.free_frames.pop(0)
            # self.victim_selector.add_frame(frame)
            self.free_memory = self.free_memory - self.frame_size
            self.used_frames.append(frame)
        else:
            swap_frame = self.kernel.swap_manager.next_frame()
            victim_frame = self.victim_selector.get_victim()
            self.kernel.loader.swap_in(victim_frame, swap_frame)
            owner = self.find_frame_owner(victim_frame)
            table = self.find_table(owner)
            table.set_swap(victim_frame, True)
            table.set_new_frame(victim_frame, swap_frame)
            self.release_frame(victim_frame)
            frame = self.next_frame()
        return frame

    def create_page_table(self, pid, program_size):
        pair_div_mod = divmod(program_size, self.frame_size)
        pages_number = pair_div_mod[0]
        if pair_div_mod[1] != 0:
            pages_number += 1
        table = PageTable()
        for page in range(0, int(pages_number)):
            table.add(page, None)
        self.page_table[pid] = table

    def find_table(self, pid):
        table = self.page_table[pid].clone()
        return table

    def switch_table(self, pid, new_table):
        self.page_table[pid] = new_table

    def has_enough_space(self, program_size):
        return self.free_memory >= program_size

    def release_space(self, pid):
        table = self.find_table(pid)
        for key, value in table.page_list.items():
            if not value[1]:
                self.release_frame(value[0])
            else:
                self.kernel.swap_manager.release_frame(value[0])
        table.reset()

    def update_page_table(self, pid, page, frame):
        table = self.page_table[pid]
        table.update(page, frame)

    def find_frame_owner(self, frame_number):
        owner = None
        for key, value in self.page_table.items():
            if value.owns_frame(frame_number):
                owner = key
        return owner

    def release_frame(self, frame):
        if frame in self.used_frames:
            self.used_frames.remove(frame)
            self.free_frames.append(frame)
            self.free_memory += self.frame_size

    def get_table(self, pid):
        return self.page_table[pid]

    def set_swap_flag(self, pid, frame, boolean):
        table = self.page_table[pid]
        table.set_swap(frame, boolean)

    def page_is_in_swap(self, pid, page):
        table = self.page_table[pid]
        page_info = table.page_list[page]
        return page_info[1]

    def get_current_frame(self, pid, page):
        table = self.find_table(pid)
        page_info = table.page_list[page]
        return page_info[0]

    def add_possible_victim(self, frame, page, pid):
        page_info = self.update_table_flags(pid, page)
        self.victim_selector.add_frame(frame, page_info)

    def update_table_flags(self, pid, page):
        table = self.find_table(pid)
        page_info = table.page_list[page]
        page_info[2] = self.kernel.dispatcher.get_clock_tick()
        page_info[3] = 1
        return page_info

    def __repr__(self):
        string = ""
        for key, value in self.page_table.items():
            string = string + "\n" + "PID " + str(key) + " ---> " + str(value)
        return "MEMORY MANAGER\nFree frames: {free} \nUsed frames: {used}\nFree memory: {space}\nPage tables: {table}"\
            .format(free=self.free_frames, used=self.used_frames, space=self.free_memory, table=string)


class SwapManager:

    def __init__(self, kernel, frame_size):
        self._kernel = kernel
        self._frame_size = frame_size
        self._free_frames = []
        self._used_frames = []
        self.assign_frames()

    def assign_frames(self):
        frames_number = HARDWARE.swap.size / self.frame_size
        for index in range(0, int(frames_number)):
            self.free_frames.append(index)

    @property
    def kernel(self):
        return self._kernel

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def free_frames(self):
        return self._free_frames

    @property
    def used_frames(self):
        return self._used_frames

    def next_frame(self):
        frame = self.free_frames.pop(0)
        self.used_frames.append(frame)
        return frame

    def release_frame(self, frame):
        self.used_frames.remove(frame)
        self.free_frames.append(frame)

    def __repr__(self):
        return "SWAP MANAGER\nFree frames: {free} \nUsed frames: {used}"\
            .format(free=self.free_frames, used=self.used_frames)


class PageReplacementAlgorithm:

    def __init__(self, memory_manager):
        self._memory_manager = memory_manager

    @property
    def memory_manager(self):
        return self._memory_manager


class FIFOPageReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)
        self._frames_used = []

    @property
    def frames_used(self):
        return self._frames_used

    def add_frame(self, frame, page_info):
        self._frames_used.append(frame)

    def get_victim(self):
        return self._frames_used.pop(0)

    def __repr__(self):
        return "FIFO MEMORY ALGORITHM\nFrames: {frames}".format(frames=self.frames_used)


class LRUPageReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)
        self._frames_used = {}

    @property
    def frames_used(self):
        return self._frames_used

    def add_frame(self, frame, page_info):
        self.frames_used[frame] = page_info

    def get_victim(self):
        victim = None
        minimum = None
        for key, value in self.frames_used.items():
            if minimum is None | value[2] < minimum:
                minimum = value[2]
                victim = key
        # TODO: check this!!! I have to take the chosen victim out!!!
        # self.frames_used.pop(victim)
        return victim

    def __repr__(self):
        return "LRU MEMORY ALGORITHM"


class SecondChanceReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)

    def add_frame(self, frame):
        pass

    def get_victim(self):
        pass

    def __repr__(self):
        return "SECOND CHANCE MEMORY ALGORITHM"


class PageTable:

    def __init__(self):
        self._page_list = {}

    @property
    def page_list(self):
        return self._page_list

    @page_list.setter
    def page_list(self, new_list):
        self._page_list = new_list

    def add(self, page, frame):
        self._page_list[page] = [frame, False, None, None]

    def clone(self):
        res = PageTable()
        res.page_list = self.page_list
        return res

    def page_is_loaded(self, page_number):
        page_info = self.page_list[page_number]
        return (page_info[0] is not None) & (not page_info[1])

    def update(self, page, frame):
        page_info = self.page_list[page]
        page_info[0] = frame

    def find_frame(self, page):
        page_info = self.page_list[page]
        return page_info[0]

    def set_swap(self, frame, boolean):
        for key, value in self.page_list.items():
            if value[0] == frame:
                value[1] = boolean

    def owns_frame(self, frame_number):
        res = False
        for key, value in self.page_list.items():
            if value[0] == frame_number & (not value[1]):
                res = True
        return res

    def set_new_frame(self, old_frame, new_frame):
        for key, value in self.page_list.items():
            if value[0] == old_frame & value[1]:
                value[0] = new_frame

    def reset(self):
        for key, value in self.page_list.items():
            value[0] = None
            value[1] = False
            value[2] = None
            value[3] = None

    def __repr__(self):
        string = ""
        for key, value in self.page_list.items():
            string = string + "   " + "Page " + str(key) + ": " + str(value)
        return "{list} ".format(list=string)
