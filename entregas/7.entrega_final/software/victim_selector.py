import log


class PageReplacementAlgorithm:

    def __init__(self, memory_manager):
        self._memory_manager = memory_manager

    @property
    def memory_manager(self):
        return self._memory_manager


class FIFOPageReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)
        self._frames_used = []

    @property
    def frames_used(self):
        return self._frames_used

    def add_frame(self, frame, page_info):
        self._frames_used.append(frame)

    def get_victim(self):
        return self._frames_used.pop(0)

    def __repr__(self):
        return "FIFO MEMORY ALGORITHM\nFrames: {frames}".format(frames=self.frames_used)


class LRUPageReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)
        self._frames_used = {}

    @property
    def frames_used(self):
        return self._frames_used

    def add_frame(self, frame, page_info):
        self.frames_used[frame] = page_info

    def get_victim(self):
        first_key = list(self.frames_used.keys())[0]
        first_frame_info = self.frames_used[0]
        victim = first_key
        minimum = first_frame_info[2]
        for key, value in self.frames_used.items():
            if value[2] < minimum:
                minimum = value[2]
                victim = key
        del self.frames_used[victim]
        return victim

    def __repr__(self):
        return "LRU MEMORY ALGORITHM\n{frames}".format(frames=self.frames_used)


class SecondChanceReplacementAlgorithm(PageReplacementAlgorithm):

    def __init__(self, memory_manager):
        super().__init__(memory_manager)
        self._frames_used = []

    @property
    def frames_used(self):
        return self._frames_used

    def add_frame(self, frame, page_info):
        self.frames_used.append((frame, page_info))

    def get_victim(self):
        victim = None
        victimChosen = False
        log.logger.info("El metodo recien empieza")
        log.logger.info("La lista esta: " + str(self.frames_used))
        while not victimChosen:
            pair = self.frames_used.pop(0)
            page_info = pair[1]
            log.logger.info("Analizando " + str(pair))
            if (not victimChosen) & (page_info[3] == 0):
                log.logger.info("Encontre una victima")
                victim = pair[0]
                victimChosen = True
                page_info[3] = 1
                log.logger.info("victimChosen quedo en " + str(victimChosen))
                log.logger.info("La lista quedo " + str(self.frames_used))
            if (not victimChosen) & (page_info[3] == 1):
                log.logger.info("Este no es una victima")
                page_info[3] = 0
                self.frames_used.append(pair)
                log.logger.info("La lista quedo " + str(self.frames_used))
            log.logger.info("Pasando al siguiente elemento de la lista")
        log.logger.info("El metodo termino, la victima elegida es " + str(victim))
        log.logger.info("La lista quedo " + str(self.frames_used))
        return victim

    def __repr__(self):
        return "SECOND CHANCE MEMORY ALGORITHM\n{frames}".format(frames=self.frames_used)