<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


I've realized that "virtualization" is a major driving force in the
computer industry. I know, this sounds pretty obvious, but previously
I didn't realize just how strong the virtualization force is.

By "virtualization" I don't only mean virtual machines. I mean a wider
concept of fault isolation, resource isolation, process separation and
so on. For the purposes of this article "virtualization" is anything
that allows running more than one process with isolated fault domain:
from virtual memory through VMWare to docker.


Let me show a [brief time line](https://en.wikipedia.org/wiki/Timeline_of_virtualization_development).

Back in the days, the memory layout was flat. For example on
[Z80](https://en.wikipedia.org/wiki/Zilog_Z80) and
[8088](https://en.wikipedia.org/wiki/Intel_8088) there was only a
single piece of code (process) running on the physical CPU. There was no
memory separation or hardware resource isolation. DOS was based on
that model back in the days and nowadays Arduino is like that.

Then [286](https://en.wikipedia.org/wiki/Intel_80286#Protected_mode)
came along, and it was a revolutionary CPU:

> [286] was the first commercially available microprocessor with on-chip MMU capabilities

Truth to be told, mainframes like
[System/360](https://en.wikipedia.org/wiki/IBM_System/360_Model_67#Virtual_memory)
invented a concept of virtual memory 20 years earlier, but it took 286
to deploy MMU to the mass market.

With MMU included in 286 it was possible to provide memory isolation
between many processes. This spurred exciting developments - ever
heard of [OS/2](https://en.wikipedia.org/wiki/OS/2)? It targeted 286
CPU. [Xenix](https://en.wikipedia.org/wiki/Xenix) targeted only 286 as
well.  There was even an attempt to create
[Concurrent DOS](https://en.wikipedia.org/wiki/Multiuser_DOS#Concurrent_DOS_286_and_FlexOS)
to integrate the new features into an established DOS
ecosystem. Sadly, due to number of critical bugs multitasking in 286
just didn't work.

This all changed with the introduction of
[386](https://en.wikipedia.org/wiki/Intel_80386). Not only it was a 32
bit CPU but also allow proper process separation. Windows 95 and Linux
are based on the process separation model introduced by
386. Furthermore with
[Virtual 8086 mode](https://en.wikipedia.org/wiki/Virtual_8086_mode)
you could safely sandbox older DOS applications.

The next milestone happened gradually. As the CPU's got faster, it
became possible to ["emulate"](https://en.wikipedia.org/wiki/X86_virtualization#Software-based_virtualization) a CPU in user space. This allowed
[full operating system virtualization](https://en.wikipedia.org/wiki/Operating-system-level_virtualization)
and triggered the raise of VMWare and Xen.

It took a while for CPU vendors to catch up with the concept of
operating system virtualization, but we're there now. Now your desktop
CPU has features to run multiple operating systems in parallel,
without the need to pay VMware a commission. Commoditization of
operating system virtualization paved way for Amazon EC2 and "The
Cloud".

But the virtualization story is not over yet. These days the trend
seems to go in two directions. On one hand side the operating system
virtualization progresses and you should expect to be able to run "a
datacenter" on your desktop. On the other side "the virtualization"
also goes down, closer to the process level. Docker (or Linux namespaces to be
specific) allow lightweight resource isolation. The same concept, but
on different abstraction layer.

Docker is somewhat special. It's the first technology that might not
incur cost with each next added abstraction layers - you can
[run docker inside a docker](http://blog.docker.com/2013/09/docker-can-now-run-within-docker/)
with little concern.


If there's a moral from this story, is that multi-tenancy in the
computing world is infinitely deep. One CPU can run multiple operating
systems, which allow multiple users to run multiple processes, which
may be further isolated in containers. These containers can further
slice available resources into smaller containers. Oh, and the
processes at the end of the chain may want to run third party plugins.

Turtles all the way down.

Furthermore changes in the "virtualization" always caused big changes
to the industry. This is yet another reason to closely observe Docker,
and be even more excited about things like
[vx32](http://pdos.csail.mit.edu/~baford/vm/),
[Google Native Client](https://en.wikipedia.org/wiki/Google_Native_Client)
or [ZeroVM](http://www.zerovm.org/).


</%block>
