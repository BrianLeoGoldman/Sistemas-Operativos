from hardware.hardware import *


class SchedulingAlgorithm:

    def __init__(self):
        self._current = None
        self._kernel = None

    @property
    def kernel(self):
        return self._kernel

    @kernel.setter
    def kernel(self, new_kernel):
        self._kernel = new_kernel

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

    def __init__(self):
        super().__init__()
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

    def __init__(self, value):
        super().__init__()
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

    def __init__(self, boolean):
        super().__init__()
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