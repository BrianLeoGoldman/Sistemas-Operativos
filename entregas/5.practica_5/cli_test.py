from so import *
import log

#
#  MAIN
#
if __name__ == '__main__':
    log.setup_logger()
    log.logger.info('Starting emulator')

    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(1)])
    prg2 = Program("prg2.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(2)])
    prg3 = Program("prg3.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3)])
    prg4 = Program("prg4.exe", [ASM.CPU(2)])
    prg5 = Program("prg5.exe", [ASM.CPU(7)])

    # setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(25)
    # add programs to hardware hard disk
    HARDWARE.addProgram(prg1)
    HARDWARE.addProgram(prg2)
    HARDWARE.addProgram(prg3)
    HARDWARE.addProgram(prg4)
    HARDWARE.addProgram(prg5)

    # new create the Operative System Kernel
    kernel = Kernel()
    # variable used to count the tick number
    tickNbr = 0
    # variable used to run the test
    running = True

    # Test command line interface

    def tick():
        global tickNbr
        HARDWARE.clock.tick(tickNbr)
        tickNbr += 1


    def do_ticks():
        times = input()
        HARDWARE.clock.do_ticks(int(times))


    def print_timer():
        print("Timer is on: " + str(HARDWARE.timer.is_on) +
              " / Quantum: " + str(HARDWARE.timer.quantum) +
              " / Counter: " + str(HARDWARE.timer.counter))


    def print_current():
        print(kernel.get_current())


    def print_cpu():
        print(HARDWARE.cpu)


    def print_memory():
        print(HARDWARE.memory)


    def print_mmu():
        print(HARDWARE.mmu)


    def print_ready():
        kernel.scheduler.print_ready()


    def print_io():
        print(kernel.io_device_controller)


    def print_pcb_table():
        pcb_list = kernel.table.elements
        print("Current process: " + str(kernel.table.current))
        for pcb in pcb_list:
            print(pcb)


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
        "mmu": print_mmu,
        "ready": print_ready,
        "io": print_io,
        "table": print_pcb_table,
        "execute": execute_program,
        "exit": finish_test
    }

    while running:
        text = input()
        process_input(text)
