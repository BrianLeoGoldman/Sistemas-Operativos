from tabulate import tabulate


## emulates the swap memory
class Swap:

    def __init__(self, size):
        self._cells = [''] * size
        self._size = size
    @property
    def size(self):
        return self._size

    def put(self, addr, value):
        self._cells[addr] = value

    def get(self, addr):
        return self._cells[addr]

    def __repr__(self):
        return "{cells}".format(cells=tabulate(enumerate(self._cells), tablefmt='psql'))