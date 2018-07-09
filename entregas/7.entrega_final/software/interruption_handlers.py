import log


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
        self.kernel.memory_manager.create_page_table(pcb, program)
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

