from so import *
import log
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

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


    # Test function
    def execute_program_1():
        kernel.execute("prg1.exe")


    # Test function
    def execute_program_2():
        kernel.execute("prg2.exe")


    def finish_test():
        global running
        running = False


    def print_memory():
        print(HARDWARE.memory)
        # Test
        print_memory2(HARDWARE.memory)


    root = Tk()
    root.geometry("300x300")
    root.title("OS Emulator")

    table_button = Button(root, text="PCB Table", command=print_pcb_table, width=10, height=1, bg="green")
    # table_button.pack(side=RIGHT)
    table_button.place(x=20, y=10)

    ready_button = Button(root, text="Ready Queue", command=print_ready, width=10, height=1, bg="red")
    ready_button.place(x=110, y=10)

    io_button = Button(root, text="I/O device", command=print_io, width=10, height=1, bg="cyan")
    io_button.place(x=210, y=10)

    memory_button = Button(root, text="Memory", command=print_memory, width=10, height=1, bg="blue")
    memory_button.place(x=20, y=50)

    timer_button = Button(root, text="Timer", command=print_timer, width=10, height=1, bg="yellow")
    timer_button.place(x=110, y=50)

    tick_button = Button(root, text="TICK", command=tick, width=10, height=1, bg="magenta", cursor="cross")
    tick_button.place(x=210, y=50)

    ##################################

    # txt_frm = Frame(root, width=100, height=100)
    # txt_frm.pack(fill="both", expand=True)
    # # ensure a consistent GUI size
    # txt_frm.grid_propagate(False)
    # # implement stretchability
    # txt_frm.grid_rowconfigure(0, weight=1)
    # txt_frm.grid_columnconfigure(0, weight=1)
    #
    # # create a Text widget
    # txt = Text(txt_frm, borderwidth=3, relief="sunken")
    # txt.config(font=("consolas", 12), undo=True, wrap='word')
    # txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    #
    # # create a Scrollbar and associate it with txt
    # scrollb = Scrollbar(txt_frm, command=txt.yview)
    # scrollb.grid(row=0, column=1, sticky='nsew')
    # txt['yscrollcommand'] = scrollb.set

    #####################################

    scrollbar = Scrollbar(root)
    scrollbar.pack(side=RIGHT, fill=Y)

    text = Text(root, width=32, height=10)
    # text.insert(INSERT, "Waiting.....")
    # text.insert(END, "Bye Bye.....")
    text.yview()
    text.place(x=20, y=120)

    # text.tag_add("here", "1.0", "1.4")
    # text.tag_add("start", "1.8", "1.13")
    # text.tag_config("here", background="yellow", foreground="blue")
    # text.tag_config("start", background="black", foreground="green")

    def print_memory2(text_string):
        text.insert(INSERT, text_string)


    scrollbar.config(command=text.yview)
    text['yscrollcommand'] = scrollbar.set

    ###################################################

    mb = Menubutton(root, text="Programs", relief=RAISED)
    # mb.grid()
    mb.menu = Menu(mb, tearoff=0)
    mb["menu"] = mb.menu
    prg1 = IntVar()
    prg2 = IntVar()
    mb.menu.add_checkbutton(label="Program 1", variable=prg1, command=execute_program_1)
    mb.menu.add_checkbutton(label="Program 2", variable=prg2, command=execute_program_2)
    mb.place(x=20, y=90)

    # def test():
    #     res = E1.get()
    #     process_input(res)
    #     msg = messagebox.showinfo("Hello Python", res)
    #
    # L1 = Label(root, text="User Name")
    # L1.pack(side=LEFT)
    #
    # E1 = Entry(root, bd=5)
    # E1.pack(side=RIGHT)

    root.mainloop()
