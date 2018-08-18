from so import *
import log
from tkinter import *

#
#  MAIN
#
if __name__ == '__main__':
    log.setup_logger()
    log.logger.info('Starting emulator')

    # new create the Operative System Kernel and set the frame size and memory factor
    kernel = Kernel(4)

    prg1 = Program("prg1.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg2 = Program("prg2.exe", [ASM.CPU(3)])
    prg3 = Program("prg3.exe", [ASM.CPU(2), ASM.IO()])
    prg4 = Program("prg4.exe", [ASM.CPU(5)])
    prg5 = Program("prg5.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
    prg6 = Program("prg6.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(1)])
    prg7 = Program("prg7.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(2), ASM.IO(), ASM.CPU(1)])

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


    def print_memory():
        memory_text.delete('1.0', END)
        memory_text.insert(INSERT, HARDWARE.memory)


    def print_pcb_table():
        pcb_list = kernel.table.elements
        table_text.delete('1.0', END)
        for pcb in pcb_list:
            table_text.insert(INSERT, "PID: " + str(pcb.pid) + " / " + "State: " + pcb.state + "\n")


    def print_ready():
        # TODO: Only works if scheduler is not priority scheduler
        queue = kernel.scheduler.queue
        ready_text.delete('1.0', END)
        for pcb in queue:
            ready_text.insert(INSERT, "PID: " + str(pcb.pid) + " / " + "Priority: " + str(pcb.priority) + "\n")


    def print_timer():
        var = HARDWARE.timer.is_on
        if var:
            status = "Status: on"
        else:
            status = "Status: off"
        timer_text.delete('1.0', END)
        timer_text.insert(INSERT, status + '\n' +
                          "Quantum: " + str(HARDWARE.timer.quantum) + '\n' +
                          "Counter: " + str(HARDWARE.timer.counter))


    def print_io():
        printing = kernel.io_device_controller.current_pcb
        if not printing is None:
            printing = "(PID->" + str(printing.pid) + ")"
        waiting = kernel.io_device_controller.waiting_queue
        var = ""
        if not waiting is None:
            for dictionary in waiting:
                var = var + str(dictionary['pcb'].pid)
        io_text.delete('1.0', END)
        io_text.insert(INSERT, "Printing: " + str(printing) + '\n' +
                       "Waiting: " + str(var))


    def tick():
        global tickNbr
        HARDWARE.clock.tick()
        tickNbr += 1
        print_system()


    def execute_program_1():
        kernel.execute("prg1.exe")


    def execute_program_2():
        kernel.execute("prg2.exe")


    def execute_program_3():
        kernel.execute("prg3.exe")


    def execute_program_4():
        kernel.execute("prg4.exe")


    def execute_program_5():
        kernel.execute("prg5.exe")


    def print_system():
        print_memory()
        print_pcb_table()
        print_ready()
        print_timer()
        print_io()


    # Test graphical user interface

    root = Tk()
    root.geometry("600x500")
    root.title("OS Emulator")

    memory_label = Label(root, text="Memory", width=10, height=1)
    memory_label.grid(row=0, column=0, padx=5, pady=5)

    table_label = Label(root, text="PCB Table", width=10, height=1)
    table_label.grid(row=0, column=3, padx=5, pady=5)

    ready_label = Label(root, text="Ready Queue", width=10, height=1)
    ready_label.grid(row=0, column=6, padx=5, pady=5)

    timer_label = Label(root, text="Timer", width=10, height=1)
    timer_label.grid(row=3, column=1, padx=5, pady=5)

    io_label = Label(root, text="I/O device", width=10, height=1)
    io_label.grid(row=3, column=6, padx=5, pady=5)

    mb = Menubutton(root, text="Programs", width=10, height=1, bg="cyan", relief=RAISED)
    mb.menu = Menu(mb, tearoff=0)
    mb["menu"] = mb.menu
    mb.menu.add_checkbutton(label="Program 1", command=execute_program_1)
    mb.menu.add_checkbutton(label="Program 2", command=execute_program_2)
    mb.menu.add_checkbutton(label="Program 3", command=execute_program_3)
    mb.menu.add_checkbutton(label="Program 4", command=execute_program_4)
    mb.menu.add_checkbutton(label="Program 5", command=execute_program_5)
    mb.grid(row=8, column=1)

    tick_button = Button(root, text="TICK", command=tick, width=10, height=1, bg="red")
    tick_button.grid(row=8, column=3)

    memory_text = Text(root, width=13, height=27)
    memory_text.grid(row=1, column=0, rowspan=10, columnspan=1, padx=5)
    memory_text.config(font=("consolas", 9), undo=True, wrap='word')
    # memory_text.yview()

    table_text = Text(root, width=27, height=10, wrap=WORD)
    table_text.grid(row=1, column=1, columnspan=5, padx=5)

    ready_text = Text(root, width=25, height=10, wrap=WORD)
    ready_text.grid(row=1, column=6, columnspan=1, padx=5)

    timer_text = Text(root, width=13, height=5, wrap=WORD)
    timer_text.grid(row=4, column=1, columnspan=1, padx=5)

    io_text = Text(root, width=26, height=5, wrap=WORD)
    io_text.grid(row=4, column=6)

    print_system()
    root.mainloop()
