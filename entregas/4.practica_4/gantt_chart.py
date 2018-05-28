from tabulate import tabulate
import log


class GanttChartCalculator:

    def __init__(self, kernel):
        self._kernel = kernel
        self._chart = []

    def start(self):
        table = self._kernel.table.elements
        pids = []
        for pcb in table:
            pids.append("PID " + str(pcb.pid))
        self._chart.append(pids)
        log.logger.info("Gantt Chart loaded correctly")

    def tick(self, tickNbr):
        table = self._kernel.table.elements
        states = []
        for pcb in table:
            states.append(pcb.state)
        self._chart.append(states)
        log.logger.info(self)

    def __repr__(self):
        return tabulate(self._chart, tablefmt='psql', headers="firstrow", stralign="center")
