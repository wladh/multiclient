from multiprocessing import Process, Queue, cpu_count
from threading import Thread
from time import time
import re

class MultiClient(object):
    """ This class implements a multiprocess and multithreaded client"""

    def __init__(self, num_threads, work, worker, processor, ip_ranges="",
                 num_procs=None, processor_args=None, worker_args=None):
        """ num_threads - number of threads per process
        work - is a list or generator of work units
        worker - is the worker function performing tasks on units of work
        processor - is the processor function which processes the results
        ip_ranges - ranges of IPs to assign to workers
        num_procs - number of processes
        processor_args - initial arguments for results function
        worker_args - initial arguments for worker function
        """

        self._num_threads = num_threads
        self._work = work
        self._worker = worker
        self._processor = processor
        self._ip_ranges = ip_ranges
        self._num_procs = num_procs or cpu_count()
        self._processor_args = processor_args
        self._worker_args = worker_args

        # Statistics - these are reliable only after run has completed

        self.runtime = 0
        self.work_units = 0

    def _iprange(self, line):
        """ Parses and ip range and returns a list of individual IPs
        Range format: ipsubrange1,ipsubrange2,....
        Subrange format: a-b.c-d.e-f.g-h
        """

        ranges = []
        for subrange in line.split(","):
            subrange = subrange.strip()
            if not re.match(
                "([0-9]{1,3}(-[0-9]{1,3})?\.){3}[0-9]{1,3}(-[0-9]{1,3})?",
                subrange):
                raise ValueError, "Invalid range %s" % subrange
            ipr = []
            for ip in subrange.split("."):
                start, s, end = ip.partition("-")
                if not s:
                    start = ip
                    end = ip
                ipr.append([i for i in range(int(start), int(end) + 1)])
            ranges.extend([".".join(map(str, (i1, i2, i3, i4)))
                           for i1 in ipr[0] for i2 in ipr[1]
                           for i3 in ipr[2] for i4 in ipr[3]])

        return ranges

    def _process_results(self, res_queue):
        """ Invokes the processor on results returned by workers """

        for result in iter(res_queue.get, 'STOP'):
            if self._processor_args:
                self._processor(result, *self._processor_args)
            else:
                self._processor(result)

    def run(self):
        """ Runs the show """

        ips = self._iprange(self._ip_ranges)
        l = len(ips)
        chunk, r = divmod(l, self._num_procs)
        if r > 0:
            ips.extend([ips[i % l] for i in range(self._num_procs - r)])
            chunk += 1

        self.runtime = 0
        self.work_units = 0

        task_queue = Queue()
        res_queue = Queue()
        tasks = []

        start_time = time()

        for i in range(self._num_procs):
            task = MultiProcess(self._num_threads, task_queue, res_queue,
                                self._worker, self._worker_args,
                                ips[i * chunk:(i + 1) * chunk])
            tasks.append(task)
            task.start()

        process_thread = Thread(target=self._process_results,
                                args=(res_queue,))
        process_thread.start()

        for work in self._work:
            task_queue.put(work)
            self.work_units += 1

        for i in range(self._num_procs * self._num_threads):
            task_queue.put("STOP")

        for task in tasks:
            task.join()

        res_queue.put("STOP")
        process_thread.join()

        self.runtime = int(time() - start_time)

class MultiProcess(Process):
    """ A process in the MultiClient. It will have many threads """

    def __init__(self, num_threads, in_queue, out_queue,
                 worker, worker_args, ips):
        """ num_threads - number of threads per process
        in_queue - queue to get work
        out_queue - queue to send results
        worker - worker function for mail handling
        worker_args - initial arguments for worker function
        ips - a range of ips which can be used as originating connection
        """

        Process.__init__(self)

        self._num_threads = num_threads
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._worker = worker
        self._worker_args = worker_args
        self._ips = ips

    def run(self):
        """ Runs the show """

        l = len(self._ips)
        chunk, r = divmod(l, self._num_threads)
        if r > 0:
            self._ips.extend(
                [self._ips[i % l] for i in range(self._num_threads - r)])
            chunk += 1

        threads = []

        for i in range(self._num_threads):
            thread = MultiThread(self._in_queue, self._out_queue,
                                 self._worker, self._worker_args,
                                 self._ips[i * chunk:(i + 1) * chunk])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

class MultiThread(Thread):
    """ A thread in the MultiClient. It's controlled by a process """

    def __init__(self, in_queue, out_queue, worker, worker_args, ips):
        """ in_queue - queue to get work
        out_queue - queue to send results
        worker - worker function for mail handling
        worker_args - initial arguments for worker function
        ips - a range of ips which can be used as originating connection
        """

        Thread.__init__(self)

        self._in_queue = in_queue
        self._out_queue = out_queue
        self._worker = worker
        self._worker_args = worker_args
        self._ips = ips

    def run(self):
        """ Runs the show """

        i = 0
        ipslen = len(self._ips)
        for work in iter(self._in_queue.get, "STOP"):
            if ipslen > 0:
                ip = self._ips[i]
                i += 1
                if i >= ipslen:
                    i = 0
            else:
                ip = None

            if self._worker_args is not None:
                res = self._worker(work, ip, *self._worker_args)
            else:
                res = self._worker(work, ip)
            if res is not None:
                self._out_queue.put(res)

if __name__ == "__main__":
    from multiprocessing import current_process
    from threading import current_thread
    import sys

    def worker(work, ip):
        return ("%s/%s: Processing [%s] with IP %s" %
                (current_process().name, current_thread().name,
                 work.rstrip(), ip))

    def processor(result, counter):
        counter["total"] += 1
        print result

    counter = {"total": 0}
    work = open("README.md")
    mc = MultiClient(5, work, worker, processor,
                     "192.168.0.1-128,192.168.1.20-30",
                     processor_args=(counter,))
    mc.run()
    work.close()

    print >> sys.stderr, "%d/%d work units. Processing took %d seconds" % (
        counter["total"], mc.work_units, mc.runtime)
