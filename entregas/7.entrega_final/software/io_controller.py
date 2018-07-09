# emulates an Input/Output device controller (driver)
class IoDeviceController:

    def __init__(self, kernel, device):
        self._device = device
        self._waiting_queue = []
        self._current_pcb = None
        self._kernel = kernel

    @property
    def waiting_queue(self):
        return self._waiting_queue

    @property
    def current_pcb(self):
        return self._current_pcb

    @property
    def kernel(self):
        return self._kernel

    def run_operation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def get_finished_pcb(self):
        finished_pcb = self._current_pcb
        self._current_pcb = None
        self.__load_from_waiting_queue_if_apply()
        return finished_pcb

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            # pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            # print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._current_pcb = pcb
            self._device.execute(instruction)

    def has_finished(self):
        return (len(self._waiting_queue) == 0) & (self._current_pcb is None)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}" \
            .format(deviceID=self._device.deviceId, currentPCB=self._current_pcb, waiting_queue=self._waiting_queue)