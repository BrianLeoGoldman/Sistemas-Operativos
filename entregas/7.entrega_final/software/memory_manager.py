from software.victim_selector import *
from software.page_table import *
from software.program import *
from hardware.mmu import *
from hardware.hardware import *


class MemoryManager:

    def __init__(self, kernel, frame_size, memory_size):
        self._kernel = kernel
        self._page_table = {}
        self._frame_size = frame_size
        self._free_memory = memory_size
        self._free_frames = []
        self._used_frames = []

    @property
    def kernel(self):
        return self._kernel

    @property
    def page_table(self):
        return self._page_table

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
    def free_frames(self):
        return self._free_frames

    @property
    def used_frames(self):
        return self._used_frames

    def assign_frames(self):
        frames_number = self._free_memory / self.frame_size
        for index in range(0, int(frames_number)):
            self._free_frames.append(index)
        HARDWARE.mmu.frame_size = self.frame_size


class MemoryManagerPagination(MemoryManager):

    def __init__(self, kernel, frame_size, memory_size):
        super().__init__(kernel, frame_size, memory_size)
        self.assign_frames()

    def next_frame(self):
        frame = self.free_frames.pop(0)
        self.free_memory = self.free_memory - self.frame_size
        self.used_frames.append(frame)
        return frame

    def find_table(self, pid):
        table = self.page_table[pid]
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
        for key, value in page_table.page_list.items():
            final_list.append(value[0])
        return final_list

    def create_page_table(self, pcb, program):
        program_length = len(program.instructions)
        if self.has_enough_space(program_length):
            pair_div_mod = divmod(program_length, self.frame_size)
            pages_number = pair_div_mod[0]
            if pair_div_mod[1] != 0:
                pages_number += 1
            log.logger.info("Number of pages:" + str(pages_number))
            table = PageTable()
            for page in range(0, int(pages_number)):
                table.add(page, self.next_frame())
            self.page_table[pcb.pid] = table
            self.load_all_pages(table, pcb)
        else:
            log.logger.info("The amount of empty space is insufficient to load this program")
            raise SystemExit

    def load_all_pages(self, table, pcb):
        for key, value in table.page_list.items():
            self.kernel.loader.load_page(pcb, key, value[0])

    def page_is_in_swap(self, pid, page):
        return False

    def __repr__(self):
        string = ""
        for key, value in self.page_table.items():
            string = string + "\n" + "PID " + str(key) + " ---> " + str(value)
        return "MEMORY MANAGER\nFree frames: {free} \nUsed frames: {used}\nFree memory: {space}\nPage tables: {table}"\
            .format(free=self.free_frames, used=self.used_frames, space=self.free_memory, table=string)


class MemoryManagerPaginationOnDemand(MemoryManager):

    def __init__(self, kernel, frame_size, memory_size):
        super().__init__(kernel, frame_size, memory_size)
        self._victim_selector = SecondChanceReplacementAlgorithm(self)
        self.assign_frames()

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

    def create_page_table(self, pcb, program):
        program_size = len(program.instructions)
        pair_div_mod = divmod(program_size, self.frame_size)
        pages_number = pair_div_mod[0]
        if pair_div_mod[1] != 0:
            pages_number += 1
        table = PageTable()
        for page in range(0, int(pages_number)):
            table.add(page, None)
        self.page_table[pcb.pid] = table

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