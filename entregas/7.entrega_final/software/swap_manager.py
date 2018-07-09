import sys

from hardware.hardware import *


class SwapManager:

    def __init__(self, kernel, frame_size):
        self._kernel = kernel
        self._frame_size = frame_size
        self._free_frames = []
        self._used_frames = []
        self.assign_frames()

    def assign_frames(self):
        frames_number = HARDWARE.swap.size / self.frame_size
        for index in range(0, int(frames_number)):
            self.free_frames.append(index)

    @property
    def kernel(self):
        return self._kernel

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def free_frames(self):
        return self._free_frames

    @property
    def used_frames(self):
        return self._used_frames

    def next_frame(self):
        frame = None
        try:
            frame = self.free_frames.pop(0)
        except IndexError:
            log.logger.info("ERROR: there are no empty frames in swap")
            sys.exit("SYSTEM SHUTTING DOWN...")
        self.used_frames.append(frame)
        return frame

    def release_frame(self, frame):
        self.used_frames.remove(frame)
        self.free_frames.append(frame)

    def __repr__(self):
        return "SWAP MANAGER\nFree frames: {free} \nUsed frames: {used}"\
            .format(free=self.free_frames, used=self.used_frames)