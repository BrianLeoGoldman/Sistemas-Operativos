import log

from hardware.hardware import *
from hardware.irq import *

## emulates the Memory Management Unit (MMU)
class MMU:

    def __init__(self, memory):
        self._memory = memory
        self._page_table = None
        self._frame_size = None

    @property
    def page_table(self):
        return self._page_table

    @page_table.setter
    def page_table(self, table):
        self._page_table = table

    @property
    def frame_size(self):
        return self._frame_size

    @frame_size.setter
    def frame_size(self, value):
        self._frame_size = value


class MMUPagination(MMU):

    def __init__(self, memory):
        super().__init__(memory)

    def fetch(self, logical_address):
        pair_div_mod = divmod(logical_address, self.frame_size)
        page_number = pair_div_mod[0]
        offset = pair_div_mod[1]
        log.logger.info(self.page_table)
        frame_number = self.page_table.page_list[page_number][0]
        physical_address = self.frame_size * frame_number + offset
        log.logger.info("Page number:" + str(page_number))
        log.logger.info("Offset: " + str(offset))
        log.logger.info("Logical address: " + str(logical_address))
        log.logger.info("Physical address: " + str(physical_address))
        return self._memory.get(physical_address)

    def __repr__(self):
        return "MMUPagination ---> {table}".format(table=self.page_table)


class MMUPaginationOnDemand(MMU):

    def __init__(self, memory):
        super().__init__(memory)

    def fetch(self, logical_address):
        pair_div_mod = divmod(logical_address, self.frame_size)
        page_number = pair_div_mod[0]
        offset = pair_div_mod[1]
        if not self.page_table.page_is_loaded(page_number):
            page_fault_IRQ = IRQ(PAGE_FAULT_INTERRUPTION_TYPE, page_number)
            HARDWARE.interruptVector.handle(page_fault_IRQ)
        frame_number = self.page_table.find_frame(page_number)
        physical_address = self.frame_size * frame_number + offset
        log.logger.info("Page number:" + str(page_number))
        log.logger.info("Offset: " + str(offset))
        log.logger.info("Logical address: " + str(logical_address))
        log.logger.info("Physical address: " + str(physical_address))
        return self._memory.get(physical_address)

    def __repr__(self):
        return "MMUPaginationOnDemand ---> {table}".format(table=self.page_table)