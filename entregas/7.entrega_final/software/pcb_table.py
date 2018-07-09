from software.pcb import *

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