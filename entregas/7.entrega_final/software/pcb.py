import random

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