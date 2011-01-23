MultiClient
==========

Simple module to distribute a workload to multiple processes, each
with muliple threads.

Overview
----------

It's a simple module that can take the work (in the form of an
iterable) and dispatch it to a number of processes and threads.
The worker function can return a result and that result is passed to a
result processing function (also user defined).
In addition to this, it also can accept a parameter (_ip\_range_)
containing a string specifying IP ranges. The ranges are in the form
"a.b.c.d[-e],...". One IP from the ranges will be sent along with each
work unit to the worker. Note that it's up to worker if/how it uses the IP.

Example
----------

A small example which sends each line of this file to a worker, along
with an IP from the ranges 192.168.0.1 to 192.168.0.128 and
192.168.1.20 to 192.168.1.30.  
This example is also in the module itself.

    from multiclient import MultiClient
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

