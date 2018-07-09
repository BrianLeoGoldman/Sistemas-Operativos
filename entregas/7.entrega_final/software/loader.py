from hardware.hardware import *


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