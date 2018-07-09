#!/usr/bin/env python
from hardware.asm import *


# emulates a compiled program
class Program:

    def __init__(self, program_name, instructions):
        self._name = program_name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def add_instr(self, instruction):
        instruction1 = instruction
        self._instructions.append(instruction1)

    @staticmethod
    def expand(instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                # is a list of instructions
                expanded.extend(i)
            else:
                # a single instr (a String)
                expanded.append(i)

        # now test if last instruction is EXIT
        # if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})" \
            .format(name=self._name, instructions=self._instructions)









