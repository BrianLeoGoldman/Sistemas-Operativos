## emulates the Hard Disk Drive (HDD)
class Disk():

    def __init__(self):
        self._memory = { }

    @property
    def memory(self):
        return self._memory

    def addProgram(self, program):
        name = program.name
        instructions = program.instructions
        self._memory[name] = instructions

    def getProgram(self, name):
        return self._memory[name]

    def deleteProgram(self, name):
        del self._memory[name]

    def getPage(self, name, page, frame_size):
        program = self.getProgram(name)
        direction = page * frame_size
        program_size = len(program)
        counter = 0
        instructions = []
        while (direction < program_size) & (counter < frame_size):
            instructions.append(program[direction])
            direction += 1
            counter += 1
        return instructions

    def __repr__(self):
        string = ""
        for key, value in self._memory.items():
            string = string + "\n" + str(key) + " ---> " + str(value)
        return "DISK\n{programs}"\
            .format(programs=string)