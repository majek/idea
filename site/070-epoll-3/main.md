<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

In previous articles we talked about:

 - [The history of the Select(2) syscall](/2016-11-01-a-brief-history-of-select2/)
 - [Select(2) being fundamentally broken](/2017-01-06-select-is-fundamentally-broken/)

This time we'll focus on Linux's `select(2)` successor - the
[`epoll(2)`](http://man7.org/linux/man-pages/man7/epoll.7.html) I/O
multiplexing syscall.

Epoll is relatively young. It was
[created by Davide Libenzi](http://www.xmailserver.org/linux-patches/nio-improve.html)
in [2002](https://lwn.net/Articles/14168/). For comparison: Windows
did
[IOCP in 1994](https://en.wikipedia.org/wiki/Input/output_completion_port)
and FreeBSD's
[kqueue was introduced in July 2000](https://en.wikipedia.org/wiki/Kqueue). Unfortunately,
even though epoll is the youngest in the advanced IO multiplexing
family, it's the worse in the bunch.

Comparison with /dev/poll
----------

[Bryan Cantrill](https://en.wikipedia.org/wiki/Bryan_Cantrill) of
Joyent is known for bashing `epoll()`.  Here's one of the more
entertaining interviews:

<div>
<iframe width="640" height="356" src="https://www.youtube.com/embed/l6XQUciI-Sc?start=3362" frameborder="0" allowfullscreen></iframe>
</div>

He mentions two defects.

First he describes "a fatal flaw, that is subtle" in the Solaris
`/dev/poll` model. He starts by describing the "thundering herd"
problem (which
[we discussed earlier](/2017-01-06-select-is-fundamentally-broken/)). Then
he moves on to the real issue. In a multithreaded scenario, when the
`/dev/poll` descriptor is shared, it is impossible to deliver events
on one file descriptor to precisely one worker thread.  He
explains that band aids to level triggered `/dev/poll` model and naive
edge-triggered won't work in multithreaded case[^2].

[^2]: The only solution is to remove the active file descriptor from the
event set and have user re-arm it manually.

This argument is indeed subtle, but since `epoll` has semantics close
to `/dev/poll`, it's safe to say it wasn't designed to work in
multithreaded scenarios.

In the video Mr Cantrill raised a second argument against `epoll`: the
events registered in epoll aren't associated with file descriptor, but
with the underlying kernel object referred to by the file descriptor
(let's call this the file *description*). He mentions the "stunning"
effect of forking and closing an fd. We will leave this problem for
now and describe it in another blog post.

Why the critique?
-------------------

Most of the `epoll` critique is based on two fundamental design
issues:

1) Sometimes it is desirable to scale application by using multi
threading.  This was not supported by early implementations of `epoll`
and was fixed by `EPOLLONESHOT` and `EPOLLEXCLUSIVE` flags.

2) Epoll registers the _file descripton_, the kernel data structure,
not _file descriptor_, the userspace handler pointing to it.

The debate is heated because it's technically possible to avoid both
pitfalls with careful defensive programming. If you can you
should avoid using epoll for load balancing across
threads. Avoid sharing epoll file descriptor across
threads.  Avoid sharing epoll-registered file
descriptors. Avoid forking, and if you must: close all
epoll-registered file descriptors before calling `execve`.  Explicitly
deregister affected file descriptors from epoll set before calling
`dup`/`dup2`/`dup3` or `close`.

If you have simple code and follow the advice above you might be fine. The
problem starts when your epoll program gets complex.

Let's dig deeper. In this blog post I'll focus on the load balancing
argument.

Load balancing
--------------

There are two distinct load balancing scenarios:

 * scaling out `accept()` calls for a single bound TCP socket
 * scaling usual `read()` calls for large number of connected sockets

Scaling out accept()
--------

Sometimes it's necessary to serve lots of very short
TCP connections. A high throughput HTTP 1.0 server is one such
example. Since the rate of inbound connections is high, you want to
distribute the work of `accept()`ing connections across multiple
CPU's.

This is a real problem happening in large deployments. Tom Herbert
reported an application handling
[40k connections per second](https://lwn.net/Articles/542629/).  With
such a volume it does makes sense to spread the work across cores.

But it's not that simple. Up until kernel 4.5 it wasn't possible to use
epoll to scale out accepts.


${"###"} Level triggered - unnecessary wake-up

A naive solution is to have a single epoll file
descriptor shared across worker threads. This won't work well,
neither will sharing bound socket file descriptor and registering it
in each thread to unique epoll instance.

This is because "level triggered" (aka: normal) epoll inherits the
"thundering herd" semantics from `select()`. Without special flags, in
level-triggered mode, all the workers will be woken up on each and
every new connection. Here's an example:

 1. **Kernel:** Receives a new connection.
 1. **Kernel:** Notifies two waiting threads A and B. Due to "thundering herd" behavior with level-triggered notifications kernel must wake up both.
 1. **Thread A:** Finishes `epoll_wait()`.
 1. **Thread B:** Finishes `epoll_wait()`.
 1. **Thread A:** Performs `accept()`, this succeeds.
 1. **Thread B:** Performs `accept()`, this fails with EAGAIN.

Waking up "Thread B" was completely unnecessary and wastes precious
resources. Epoll in level-triggered mode scales out poorly.


${"###"} Edge triggered - unnecessary wake-up and starvation

Okay, since we ruled out naive level-triggered setup, maybe "edge
triggered" could do better?

Not really. Here is a possible pessimistic run:

 1. **Kernel:** Receives first connection. Two threads, A and B, are waiting. Due to "edge triggered" behavior only one is notified - let's say thread A.
 1. **Thread A:** Finishes `epoll_wait()`.
 1. **Thread A:** Performs `accept()`, this succeeds.
 1. **Kernel:** The accept queue is empty, the event-triggered socket moved from "readable" to "non readable", so the kernel must re-arm it.
 1. **Kernel:** Receives a second connection.
 1. **Kernel:** Only one thread is currently waiting on the `epoll_wait()`. Kernel wakes up Thread B.
 1. **Thread A:** Must perform `accept()` since it does not know if kernel received one or more connections originally. It hopes to get EAGAIN, but gets another socket.
 1. **Thread B:** Performs `accept()`, receives EAGAIN. This thread is confused.
 1. **Thread A:** Must perform `accept()` again, gets EAGAIN.

The wake-up of Thread B was completely unnecessary and is
confusing. Additionally, in edge triggered mode it's hard to avoid
starvation:

 1. **Kernel:** Receives two connections. Two threads, A and B, are waiting. Due to "edge triggered" behavior only one is notified - let's say thread A.
 1. **Thread A:** finished `epoll_wait()`.
 1. **Thread A:** performs `accept()`, this succeeds
 1. **Kernel:** Receives third connection. The socket was "readable", still is "readable". Since we are in "edge triggered" mode, no event is emitted.
 1. **Thread A:** Must perform `accept()`, hopes to get EGAIN, but gets another socket.
 1. **Kernel:** Receives fourth connection.
 1. **Thread A:** Must perform `accept()`, hopes to get EGAIN, but gets another socket.

In this case the socket moved only once from "non-readable" to
"readable" state. Since the socket is in edge-triggered mode, the
kernel will wake up epoll exactly once. In this case all the
connections will be received by Thread A and load balancing won't be
achieved.


${"###"} Correct solution

There are two workarounds.

The best and the only scalable approach is to use recent Kernel 4.5+ and
use level-triggered events with `EPOLLEXCLUSIVE` flag. This will
ensure only one thread is woken for an event, avoid "thundering herd"
issue and scale properly across multiple CPU's

Without `EPOLLEXCLUSIVE`, similar behavior it can be emulated with
edge-triggered and `EPOLLONESHOT`, at a cost of one extra `epoll_ctl()`
syscall after each event. This will distribute load across multiple
CPU's properly, but at most one worker will call `accept()`
at a time, limiting throughput.


 1. **Kernel:** Receives two connections. Two threads, A and B, are waiting. Due to "edge triggered" behavior only one is notified - let's say thread A.
 1. **Thread A:** Finishes epoll_wait().
 1. **Thread A:** Performs `accept()`, this succeeds.
 1. **Thread A:** Performs `epoll_ctl(EPOLL_CTL_MOD)`, this will reset the `EPOLLONESHOT` and re-arm the socket.


It's worth noting there are other ways to scale `accept()` without
relying on epoll. One option is to use
[`SO_REUSEPORT`](https://lwn.net/Articles/542629/) and create multiple
listen sockets sharing the same port number. This approach has
problems though - when one of the file descriptors is closed, the
sockets already waiting in the accept queue will be dropped. Read more
in this
[Yelp blog post](https://engineeringblog.yelp.com/2015/04/true-zero-downtime-haproxy-reloads.html)
and this [LWN comment](https://lwn.net/Articles/542866/).

[Kernel 4.4](https://kernelnewbies.org/Linux_4.4)
[introduced `SO_INCOMING_CPU`](https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=70da268b569d32a9fddeea85dc18043de9d89f89)
to further improve locality of `SO_REUSEPORT` sockets. I wasn't
able to find a good documentation of this very new feature.

Even better, [kernel 4.5](https://kernelnewbies.org/Linux_4.5)
introduced `SO_ATTACH_REUSEPORT_CBPF` and `SO_ATTACH_REUSEPORT_EBPF`
[socket options](http://man7.org/linux/man-pages/man7/socket.7.html). When
used properly, with a bit of magic, it should be possible to substitute
`SO_INCOMING_CPU` and overcome the usual `SO_REUSEPORT` dropped
connections on rebalancing problem.


Scaling out read()
------------

Apart from scaling `accept()` there is a second use case for scaling
`epoll` across many cores. Imagine a situation when you have a large
number of HTTP client connections and you want to serve them as
quickly as the data arrives. Each connection may require some
unpredictable processing, so sharding them into equal buckets across worker threads
will worsen mean latency. It's better to use "the combined queue" queuing
model - have one epoll set and use multiple threads to pull active
sockets and perform the work.


Here's The Engineer Guy explaining the combined queue model:

<div>
<iframe width="640" height="356" src="https://www.youtube.com/embed/F5Ri_HhziI0?start=118" frameborder="0" allowfullscreen></iframe>
</div>


In our case the shared queue is an epoll descriptor, the tills
are worker threads and the jobs are readable sockets.

${"###"}  Epoll level triggered

We don't want to use the level triggered model due to the "thundering
herd" behavior. Additionally the `EPOLLEXCLUSIVE` won't help since
there is a race condition possible. Here's how it may
materialize:

 * **Kernel:** receives 2047 bytes of data
 * **Kernel:** two threads are waiting on epoll, kernel wakes up due to `EPOLLEXCLUSIVE` behavior. Let's say kernel woke up Thread A.
 * **Thread A:** finishes `epoll_wait()`
 * **Kernel:** receives 2 bytes of data
 * **Kernel:** one thread is waiting on epoll, kernel wakes up Thread B.
 * **Thread A:** performs `read(2048)` and reads full buffer of 2048 bytes.
 * **Thread B:** performs `read(2048)` and reads remaining 1 byte of data

In this situation the data is split across two threads and without
using mutexes the data may be reordered.

${"###"}  Epoll edge triggered

Okay, so maybe edge triggered model will do better? Not really. The
same race condition occurs:

 * **Kernel:** receives 2048 bytes of data
 * **Kernel:** two threads are waiting for the data: A and B. Due to the "edge triggered" behavior only one is notified.
 * **Thread A:** finishes `epoll_wait()`
 * **Thread A:** performs a `read(2048)` and reads full buffer of 2048 bytes
 * **Kernel:** the buffer is empty so the kernel arms the file descriptor again
 * **Kernel:** receives 1 byte of data
 * **Kernel:** one thread is currently waiting in epoll_wait, wakes up Thread B
 * **Thread B:** finished `epoll_wait()`
 * **Thread B:** performs `read(2048)` and gets 1 byte of data
 * **Thread A:** retries `read(2048)`, which returns nothing, gets EAGAIN


${"###"} Correct solution

The correct solution is to use `EPOLLONESHOT` and re-arm the file
descriptor manually. This is the only way to guarantee that the data
will be delivered to only one thread and avoid race conditions.


Conclusion
--------------

Using `epoll()` correctly is hard. Understanding extra flags
`EPOLLONESHOT` and `EPOLLEXCLUSIVE` is necessary to achieve load
balancing free of race conditions.

Considering that `EPOLLEXCLUSIVE` is a very new epoll flag, we may
conclude that `epoll` was not originally designed for balancing load
across multiple threads.


In the next blog post in this series we will describe the `epoll`
"file descriptor vs file description" problem which occurs when used
with `close()` and `fork` calls.


</%block>


