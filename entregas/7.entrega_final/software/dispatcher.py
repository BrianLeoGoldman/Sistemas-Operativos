from hardware.hardware import *


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