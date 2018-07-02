from so import *
import log

#
#  MAIN
#
if __name__ == '__main__':
    log.setup_logger()
    log.logger.info('Starting emulator')

    # new create the Operative System Kernel and set the frame size
    kernel = Kernel(4, 3)

    prg1 = Program("prg1.exe", [ASM.CPU(3), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(3)])
    prg2 = Program("prg2.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(1), ASM.CPU(2), ASM.IO(),
                                ASM.CPU(1), ASM.CPU(2), ASM.IO()])
    prg3 = Program("prg3.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(2), ASM.CPU(1), ASM.IO(),
                                ASM.CPU(2), ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg4 = Program("prg4.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(1), ASM.IO(), ASM.CPU(1),
                                ASM.IO(), ASM.CPU(1), ASM.IO(), ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg5 = Program("prg5.exe", [ASM.CPU(11)])
    prg6 = Program("prg6.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg7 = Program("prg7.exe", [ASM.CPU(3)])

    # setup our hardware with memory size and swap size
    # HARDWARE.setup(20, 4)
    # add programs to hardware hard disk
    HARDWARE.addProgram(prg1)
    HARDWARE.addProgram(prg2)
    HARDWARE.addProgram(prg3)
    HARDWARE.addProgram(prg4)
    HARDWARE.addProgram(prg5)
    HARDWARE.addProgram(prg6)
    HARDWARE.addProgram(prg7)

    # variable used to count the tick number
    tickNbr = 0
    # variable used to run the test
    running = True

    # Test command line interface

    def tick():
        HARDWARE.clock.tick()

    def do_ticks():
        times = input()
        HARDWARE.clock.do_ticks(int(times))

    def print_timer():
        print(HARDWARE.timer)

    def print_current():
        print(kernel.get_current())

    def print_cpu():
        print(HARDWARE.cpu)

    def print_memory():
        print(HARDWARE.memory)

    def print_mmu():
        print(HARDWARE.mmu)

    def print_hdd():
        print(HARDWARE.disk)

    def print_ready():
        kernel.scheduler.print_ready()

    def print_io():
        print(kernel.io_device_controller)

    def print_memory_manager():
        print(kernel.memory_manager)

    def print_swap_manager():
        print(kernel.swap_manager)

    def print_victim_algorithm():
        print(kernel.memory_manager.victim_selector)

    def print_pcb_table():
        print(kernel.table)

    def print_swap():
        print(HARDWARE.swap)

    def execute_program():
        name = input()
        kernel.execute(name)

    def finish_test():
        global running
        running = False

    def process_input(name):
        processDictionary[name]()

    # dictionary with all inputs and its effect
    processDictionary = {
        "tick": tick,
        "ticks": do_ticks,
        "timer": print_timer,
        "current": print_current,
        "cpu": print_cpu,
        "memory": print_memory,
        "mem_manager": print_memory_manager,
        "swap_manager": print_swap_manager,
        "victim": print_victim_algorithm,
        "mmu": print_mmu,
        "hdd": print_hdd,
        "ready": print_ready,
        "io": print_io,
        "table": print_pcb_table,
        "swap": print_swap,
        "execute": execute_program,
        "exit": finish_test
    }

    while running:
        text = input()
        process_input(text)
