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
