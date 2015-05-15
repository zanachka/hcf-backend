import os
import atexit
import uuid
import shutil
from os.path import join
from queuelib import PriorityQueue

from frontera.utils.misc import load_object

class DiskQueue(object):
    def __init__(self, dqclasspath, request_model):
        self.dqclass = load_object(dqclasspath)
        self.request_model = request_model
        self.dq = PriorityQueue(self._dqfactory)
        self.__dqdir = 'requests.queue-' + str(uuid.uuid1())
        os.makedirs(self.__dqdir)
        def _remove_dir():
            shutil.rmtree(self.__dqdir)
        atexit.register(_remove_dir)
        self.__ids_count = 0
        self.__func_ids = {} # double map func <-> id

    def get_func_id(self, func):
        if func not in self.__func_ids:
            self.__func_ids[func] = self.__ids_count
            self.__func_ids[self.__ids_count] = func
            self.__ids_count += 1
        return self.__func_ids[func]

    def get_function_from_id(self, fid):
        return self.__func_ids[fid]

    def _dqfactory(self, priority):
        return self.dqclass(join(self.__dqdir, 'p%s' % priority))

    def push(self, request):
        rdict = self.request_to_dict(request)
        self.dq.push(rdict)

    def pop(self):
        rdict = self.dq.pop()
        if rdict:
            return self.request_from_dict(rdict)

    def request_to_dict(self, request):
        rdict = {}
        for attr in ('url', 'method', 'headers', 'cookies', 'meta'):
            rdict[attr] = getattr(request, attr)
        if 'scrapy_callback' in rdict['meta']:
            func = rdict['meta'].pop('scrapy_callback')
            rdict['meta']['scrapy_callback_id'] = self.get_func_id(func)
        return rdict

    def request_from_dict(self, rdict):
        if 'scrapy_callback_id' in rdict['meta']:
            fid = rdict['meta'].pop('scrapy_callback_id')
            rdict['meta']['scrapy_callback'] = self.get_function_from_id(fid)
        return self.request_model(**rdict)

    def __len__(self):
        return len(self.dq)

    def close(self):
        self.dq.close()
