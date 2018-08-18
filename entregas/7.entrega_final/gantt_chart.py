import itertools

from tabulate import tabulate
import log
from hardware import HARDWARE


class GanttChartCalculator:

    def __init__(self, kernel):
        self._kernel = kernel
        self._chart = {}
        self._ticks = 0
        HARDWARE.add_suscriber(self)

    @property
    def kernel(self):
        return self._kernel

    @property
    def chart(self):
        return self._chart

    @property
    def ticks(self):
        return self._ticks

    @ticks.setter
    def ticks(self, value):
        self._ticks = value

    def tick(self, tickNbr):
        table = self.kernel.table.elements
        if len(table) > 0:
            for pcb in table:
                if self.chart.keys().__contains__(pcb.pid):
                    self.chart[pcb.pid] = self.chart[pcb.pid] + self.get_symbol(pcb.state)
                else:
                    self.chart[pcb.pid] = self.initiate_chart()
                    self.chart[pcb.pid] = self.chart[pcb.pid] + self.get_symbol(pcb.state)
        self.ticks = self.ticks + 1

    def get_symbol(self,  state):
        if state == "Running":
            return " R "
        if state == "Ready":
            return " W "
        if state == "Terminated":
            return " - "
        if state == "Waiting":
            return " - "

    def initiate_chart(self):
        res = " "
        counter = self.ticks
        while counter > 0:
            res = res + " - "
            counter = counter - 1
        return res

    def __repr__(self):
        string = ""
        for key, value in self.chart.items():
            string = string + "\n" + "PID " + str(key) + " ---> " + str(value)
        return "\nGANTT CHART: {table}" \
            .format(table=string)
        # return tabulate(self.chart, tablefmt='psql', headers="firstrow", stralign="center")
