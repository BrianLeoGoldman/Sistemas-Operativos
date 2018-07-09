class PageTable:

    def __init__(self):
        self._page_list = {}

    @property
    def page_list(self):
        return self._page_list

    @page_list.setter
    def page_list(self, new_list):
        self._page_list = new_list

    def add(self, page, frame):
        self._page_list[page] = [frame, False, None, None]

    def clone(self):
        res = PageTable()
        res.page_list = self.page_list
        return res

    def page_is_loaded(self, page_number):
        page_info = self.page_list[page_number]
        return (page_info[0] is not None) & (not page_info[1])

    def update(self, page, frame):
        page_info = self.page_list[page]
        page_info[0] = frame

    def find_frame(self, page):
        page_info = self.page_list[page]
        return page_info[0]

    def set_swap(self, frame, boolean):
        for key, value in self.page_list.items():
            if value[0] == frame:
                value[1] = boolean

    def owns_frame(self, frame_number):
        res = False
        for key, value in self.page_list.items():
            if value[0] == frame_number & (not value[1]):
                res = True
        return res

    def set_new_frame(self, old_frame, new_frame):
        for key, value in self.page_list.items():
            if value[0] == old_frame & value[1]:
                value[0] = new_frame

    def reset(self):
        for key, value in self.page_list.items():
            value[0] = None
            value[1] = False
            value[2] = None
            value[3] = None

    def __repr__(self):
        string = ""
        for key, value in self.page_list.items():
            string = string + "   " + "Page " + str(key) + ": " + str(value)
        return "{list} ".format(list=string)