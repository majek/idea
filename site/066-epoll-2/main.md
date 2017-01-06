<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

In a previous blog post we discussed
[a brief history of the `select(2)` syscall](https://idea.popcount.org/2016-11-01-a-brief-history-of-select2/). The
article concludes that some I/O multiplexing was necessary to
do console emulation, games and non-trivial TCP/IP applications.

The BSD designers chose the `select` multiplexing model and other
Unixes followed. But is `select` the only multiplexing model?

A good explanation can be found in the old revision of
["The Design and Implementation of the FreeBSD Operating System"](https://www.freebsd.org/doc/en_US.ISO8859-1/books/design-44bsd/)
book. [Google books](https://books.google.pl/books?id=KfCuBAAAQBAJ&pg=PA325&lpg=PA325&redir_esc=y)
has it, here's a snippet:

> There are four possible alternatives that avoid the blocking problem:
>
> 1. Set all the descriptors in nonblocking mode. [...]
> 2. Enable all descriptors of interest to [send] signal when I/O can be done. [...]
> 3. Have the system provide a method for asking which descriptors are capable of performing the I/O [...]
> 4. Have the process register with the [operating] system all the events including I/O on descriptors that it is interested in tracking.

Option 1) is naive. The idea is to do busy-polling on non-blocking
descriptors. It requires using 100% CPU. It's not very practical.

Option 2) is the good old
[SIGIO](http://davmac.org/davpage/linux/async-io.html) async I/O
model. Linux implements it with
[`fcntl(F_SETSIG)`](https://linux.die.net/man/2/fcntl). With `fcntl`
set up, a signal will notify your process when readability /
writeability on descriptor changes. Sadly `F_SETSIG` model in its
current implementation is almost totally useless[^fsetsig].

Option 3) is a model exposed by the `select()`. It's simple, well
defined and easy to understand. This is the model shared by `poll` and
`epoll` syscalls.


[^fsetsig]: There are too many problems with `F_SETSIG`
implementation, don't get me started. Let's just say that when you
catch the `SIGIO` signal, you aren't given a reliable information
showing the file descriptor on which the event happened.

Option 4) is the interesting one. The idea is to shift some state to
the kernel and let it know what precisely we want to do on the file
descriptor. This is model exposed by `kqueue` and Windows IOCP.

Each of these four multiplexing models have their weaknesses, but I'd
like to focus specifically on the third option: `select`.


Heavyweight
------------

`Select()` was
[first implemented 33 years ago](https://idea.popcount.org/2016-11-01-a-brief-history-of-select2/),
and for that age it holds remarkably well. Unfortunately it's broken
by design.

It's not only `select()` syscall that is broken. All technologies
which inherit its semantics are broken too!  This includes `select`,
`poll`, and to lesser extent `epoll`.

The usual argument against `select` is that the API mandates a linear
traversal of file descriptors. This is true, but it's not the biggest
issue in my opinion. The `select` semantics prevent the kernel from
doing any optimizations. It is impossible to create fast kernel-side
`select` implementation.

Whenever your process enters the `select()`, the kernel must iterate
through the passed file descriptors, check their state and register
callbacks. Then when an event on _any_ of the fd's happens, the kernel
must iterate again to deregister the callbacks. Basically on the
kernel side entering and exiting `select()` is a heavyweight
operation, requiring touching many pointers, thrashing processor
cache, and there is no way around it.

`Epoll()` is Linux's solution. With it the developer can avoid
constantly registering and de-registering file descriptors. This is
done by explicitly managing the registrations with the `epoll_ctl`
syscall.

But `epoll` doesn't solve all the problems.

Thundering herd problem
-----------------------

Imagine a socket descriptor shared across multiple operating system
processes. When an event happens _all_ of the processes must be woken
up. This might sound like a bogus complaint - why would you share a
socket descriptor? - but it does happen in practice.

Let's say you run an HTTP server, serving a large number of short
lived connections. You want to `accept()` as many connections per
second as possible. Doing `accept()` in only one process will surely
be CPU-bound. How to fix it?

A naive answer is: let's share the file descriptor and allow multiple
processes to call `accept()` at the same time! Unfortunately doing
so will actually _degrade_ the performance.

To illustrate the problem I wrote two pieces of code.

First, there is
[`server.c`](https://github.com/majek/dump/blob/master/select-sucks/server.c)
program. It binds to TCP port 1025 and before blocking on `select` it
forks a number of times. Pseudo code:

```.py
sd = socket.socket()
sd.bind('127.0.0.1:1025')
sd.listen()
for i in range(N):
    if os.fork() == 0:
        break
select([sd])
```

To run 1024 forks all hanging in `select` on one bound socket:

```.sh
$ ./server 1024
forks = 1024, dupes per fork = 1, total = 1024
[+] started
```

The second program
[`client.c`](https://github.com/majek/dump/blob/master/select-sucks/client.c)
is trivial.  It's connecting to the TCP port measuring the time. To
better illustrate the issue it does a nonblocking `connect(2)`
call. In theory this should always be blazing fast.

There is a caveat though. Since the connection is going over loopback
to localhost, the packets are going to be processed in-line, during
the kernel handling of the `connect` syscall.

Measuring the duration of a nonblocking `connect` in practice shows
the kernel dispatch time. We will measure how long it takes for the
kernel to:

 - create a new connection over loopback,
 - find the relevant listen socket descriptor on the receiving side,
 - put the new connection into an accept queue
 - and notify the processes waiting for that listen socket.

The cost of the last step is proportional to the number of processes
waiting on that socket. Here is a chart showing the duration of the
`connect` syscall rising linearly with the number of processes waiting
in `select` on the listen socket:

<gnuplot>
size: 500x350
data: |
<% a=''' 0 min 0.048 avg 0.067 var 0.016
 128 min 0.303 avg 0.503 var 0.106
 256 min 0.648 avg 0.874 var 0.152
 512 min 0.937 avg 1.252 var 0.187
 3072 min 3.633 avg 5.960 var 0.496
 ''' %>
 1024 min 1.810 avg 2.383 var 0.142
 2048 min 3.456 avg 3.983 var 0.435
 4096 min 7.754 avg 8.966 var 1.158
 8192 min 14.838 avg 16.973 var 1.713
 12288 min 16.877 avg 23.213 var 4.236
 16384 min 27.672 avg 33.586 var 2.725
--

set datafile separator " "
set border 3;
set xtics nomirror;
set ytics nomirror;
set xtics 2048;
set boxwidth 0.5;
set style fill solid;
;#set yrange [0:1000];
;#set xrange [-0.5:6.5];
set xrange [0:16600];
set yrange [0:];

;#set format y "%.03f"
set key off

set xlabel "Number of processes"
set ylabel "Milliseconds"

unset surface;
unset contour;
set bars 3 front;

plot \
  "data.dat" using 1:($5):(($5-$7)):(($5+$7)) with errorbars title "stddev" ,  \
  "data.dat" using 1:($5) with lines title "connect() time";
</gnuplot>

Calling non-blocking `connect()` to a listen socket which is shared
across 16k processes takes 35 milliseconds on my machine.

These results are expected. The kernel needs to do linearly more work
for each process it needs to wake up, for each of the file descriptors
the process is blocking on in `select()`. This is also true for
`epoll()`.

Extreme experiment
--------------

Let's take this experiment to an extreme. Let's see what happens when
we have not one listen socket waiting in the `select` loop, but a
thousand. To make kernel job harder we will copy the TCP port 1025
bound socket a thousand times with `dup()`. Pseudo code:

```.py
sd = socket.socket()
sd.bind('127.0.0.1:1025')
sd.listen()

list_of_duplicated_sd = [dup(sd) for i in xrange(1019)]

for i in range(N):
    if os.fork() == 0:
        break
select([sd] + list_of_duplicated_sd)
```

This is implemented in the `server.c` as well:

```.sh
marek:~$ ./server 1024 1019
forks = 1024, dupes per fork = 1019, total = 1043456
[+] started
```

The chart will show a linear cost, but with a much greater constant
factor:

<gnuplot>
size: 500x350
data: |
<% pipe_data=  ''' 
 512 min 1.026 avg 2.759 var 1.035
 1024 min 1.831 avg 4.274 var 1.197
 2048 min 3.941 avg 8.429 var 1.580
 3072 min 10.422 avg 12.901 var 2.383
 4096 min 13.937 avg 16.158 var 1.456
''' %>
 1024 min 73.256 avg 100.852 var 21.145
 2048 min 191.156 avg 238.955 var 32.489
 4096 min 309.425 avg 357.304 var 73.880
 8192 min 690.868 avg 799.888 var 90
 12288 min 1103.110 avg 1124.126 var 120
 16384 min 1321.172 avg 1545.688 var 180
--

set datafile separator " "
set border 3;
set xtics nomirror;
set ytics nomirror;
set xtics 2048;
set boxwidth 0.5;
set style fill solid;
;#set yrange [0:1000];
;#set xrange [-0.5:6.5];

set xrange [0:16600];
set yrange [0:];

set xlabel "Number of processes"
set ylabel "Milliseconds"
set key off

unset surface;
unset contour;
set bars 3 front;

plot \
  "data.dat" using 1:($5):(($5-$7)):(($5+$7)) with errorbars title "stddev" ,  \
  "data.dat" using 1:($5) with lines title "connect() time";
</gnuplot>

The chart confirms a very large cost of such setup. With 16k running
processes, each with the listen socket dup'ed 1019 times (16M file
descriptors total) it takes the kernel an amazing 1.5 seconds to perform
the localhost non-blocking `connect()`.

This is how it looks in console:

```.sh
marek:~$ time nc localhost 1025 -q0
real    0m1.523s

marek:~$ strace -T nc localhost 1025 -q0
...
connect(3, {sa_family=AF_INET, sin_port=htons(1025), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress) <1.390385>
...
```

This setup overwhelms the machine. Our single event rapidly moves
thousands of our Linux processes from "sleep" process state to
"runnable" resulting in interesting load average numbers:

```.sh
marek:~$ uptime
 load average: 1388.77, 1028.89, 523.62
```

Epoll exclusive to the rescue
--------------

This is a classic thundering herd problem. It's helped with a new
`EPOLLEXCLUSIVE` `epoll_ctl` flag. It was added very recently to
kernel 4.5. [Man page](man7.org/linux/man-pages/man2/epoll_ctl.2.html)
says:

> EPOLLEXCLUSIVE (since Linux 4.5)
>   Sets an exclusive wakeup mode for the epoll file descriptor
>   that is being attached to the target file descriptor, fd.
>   When a wakeup event occurs and multiple epoll file descriptors
>   are attached to the same target file using EPOLLEXCLUSIVE, one
>   or more of the epoll file descriptors will receive an event
>   with epoll_wait(2).

Here's the relevant kernel patch:

  * [https://lwn.net/Articles/667087/](https://lwn.net/Articles/667087/)

If I understand the code right, it is intended to improve the average
case. The patch doesn't fundamentally solve the problem of the kernel
dispatch time being a costly `O(N)` on the number of processes /
descriptors.


Recap
-----

I explained two issues with the `select()` multiplexing model.

It is heavyweight. It requires constantly registering and
unregistering processes from the file descriptors, potentially
thousands of descriptors, thousands times per second.

Another issue is scalability of sharing socket between processes. In
the traditional model the kernel must wake up all the processes
hanging on a socket, even if there is only a single event to deliver.
This results in a thundering herd problem and plenty of wasteful
process wakeups.

Linux solves first issue with an `epoll` syscall and second with
`EPOLLEXCLUSIVE` band aid.

I think the real solution is to fundamentally rethink the socket
multiplexing. Instead of putting band aids on "Option 3)" from Kirk
McKusick's book, we should focus on "Option 4)" - the `kqueue` and
`IOCP` interfaces.

But that's a subject for another article.

</%block>
