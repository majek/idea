<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Some time ago I started wondering - would it be possible for a CDN to
run customer code on the edge servers?  I read and asked around, over
time I got acquainted to what is and what is not technically
possible. But that didn't bring me closer to an useful
answer. Fortunately exploring this subject has been enormous fun. In
this blog post I'll describe my findings so far.

<div class="image"><img src="sandbox.jpg"><div>
<small><a href="https://www.flickr.com/photos/seattleparks/15539748239">image by Seattle Parks</a></small>
</div></div>


Generally speaking there are four ways of ensuring security when
running untrusted third-party code:

 1. *Programming language barrier*. The isolation can be ensured by a
    programming language runtime. Such a runtime would need to
    restrict the access to privileged operations, validate
    memory access and support preemptive multi-tasking.

 1. *Operating system isolation*. It's possible to use operating
    system processes for sandboxing. Together with features like
    [seccomp](https://en.wikipedia.org/wiki/Seccomp) and
    [namespaces](https://en.wikipedia.org/wiki/Linux_namespaces) it's
    possible effectively lock down untrusted code.

 1. *Software fault isolation*. SFI is a way to create an isolation
    boundary within a single process. It's conceptually
    simillar to running isolated "plugins". The best known
    implementation of SFI is
    [Google Native Client](https://en.wikipedia.org/wiki/Google_Native_Client).

 1. *Virtual machine isolation*. Modern CPU's have rich features to
    support virtualization. These features could be reused to create an
    isolation for untrusted code.

Let's discuss these options in more details.


<div class="image" style="height:364px"><img src="programming.jpg"><div>
<small><a href="https://www.flickr.com/photos/qnr/3140252218">image by Terry Ross</a></small>
</div></div>


Programming language barrier
----------------

A carefully designed programming language runtime might be used to
enforce isolation. Such a language runtime would need to:

 * *Be multi-tenant* allowing multiple foreign pieces of code to share
   a language runtime in a single operating system process.

 * Have *a scheduler* and support *a cooperative multitasking*
   model. We don't want one tenant to consume all the CPU.

 * Enforce memory limits. We don't want a single tenant to consume too
   much memory either.

 * Can safely run untrusted code and restrict access to unprivileged
   operations. Tenants shouldn't be able to escape the sandbox.

Unfortunately no such programming language currently exists. Let me
show it on an example of two promising languages: Lua and Javascript.


${ "###" }Lua

[Lua](https://www.lua.org/) is a perfect example. It was designed
specifically to be embeddable and run untrusted code. There has been
some
[sandbox escapes](http://benmmurphy.github.io/blog/2015/06/04/redis-eval-lua-sandbox-escape/)
but to my understanding these are all fixable. Unfortunately it
doesn't come with multi-tenancy support. It's impossible to run
multiple pieces of untrusted code in a single Lua runtime. Lua
struggles to enforce CPU and memory limits.

In Lua the only way to restrict CPU usage of a tenant is by relying on
a hacky debug hook. For example:

```.lua
while true do
end
```

Such a forever-loop like this could be escaped with a debug hook
`debug.sethook(handler, "c", 100)`. This will interrupt the tenant
code every 100 instructions and provide opportunity to implement a
scheduler. But since this feature is implemented in Lua layer, it
won't be able to interrupt slow C functions called from Lua.

Similarly, it's impossible to enforce memory limits for each
tenant. For example:

```.lua
string.rep("a", 100000000)
```

`string.rep()` is a
[good example](http://lua-users.org/lists/lua-l/2011-02/msg01106.html)
of a function that looks innocent but can be abused by a tenant and to
cause out of memory crash. Furthermore, `string.rep` is implemented in
C. It's not easily possible to restrict memory allocations done by
functions like this.

While Lua was designed to make it easy
[to create basic sandboxes](http://lua-users.org/wiki/SandBoxes), it
definitely doesn't come with multi-tenancy built in.

${ "###" }Javascript

An in-browser Javascript engine is another interesting
candidate. First, it's definitely created to be multi-tenant. In a
browser world a single tab can't escape and affect others. Browser JS
engines are an audited and mature piece of technology.

Unfortunately modern JS engines don't support preemptive
multitasking. If you've ever seen one of these alerts you know what
I'm talking about:

![unresponsive.jpg](unresponsive.jpg)

It's similar story with enforcing memory limits - generally speaking
browsers don't care about memory allocations done by one tab. It's
totally possible for one rogue Javascript context to consume all of
the available memory. A renderer process will just crash with a
generic error message.

${ "###" } Summary

I'm not aware of any language runtime designed to support running
multi-tenant sanboxed code. This is a pity though. Doing scheduling
and performing lightweight context switches within a single user-space
process is probably the best and most scalable design here. It would
be possible to easily run thousands of tenants that way. I guess it could be
possible to create such a runtime, but well, it's gonna be tough.
Let's move on to another technical solutions for sandboxing - OS layer
isolation.

<div class="image" style="height:${364+28}px"><img src="os.jpg"><div>
<small><a href="https://www.flickr.com/photos/br1otcom/13506846613/">image by Bruno Cordioli</a></small>
</div></div>

Operating system isolation
--------------

Enforcing isolation can be deferred to the operating system. Operating
systems already do a good job of isolating processes from each other.
With proper memory / CPU limit enforcement and good sandboxing of
untrusted syscalls we could try to execute untrusted code in a locked
down OS process.

This is a sound design and works for many others in the industry. For
example:

 * [Sandstorm](https://docs.sandstorm.io/en/latest/overview/)
 * [Docker](https://docs.docker.com/engine/security/security/)

To properly lock down the process it's necessary to restrict the
allowed syscalls. This is where [`seccomp`](https://lwn.net/Articles/656307/) comes in.

${ "###" } seccomp

To restrict syscalls we will need
[`seccomp-bpf`](https://www.kernel.org/doc/Documentation/prctl/seccomp_filter.txt). With
its help we can deny any dangerous syscalls and allow only a carefully
selected safe ones.. Unfortunately it's not that simple in
practice. Seccomp can only whitelist or blacklist syscalls by their
number. By design it cannot dereference
[the pointers passed as syscall parameters](http://man7.org/linux/man-pages/man2/seccomp.2.html).

For example, with `seccomp` it's possible to enable or disable
`connect` syscall, but that's it. `Seccomp` cannot be used to validate
the target IP address of `connect`. In practice you would want to
enforce sophisticated policies. For example, it makes sense to allow
`connect` to remote addresses, but disable it from connecting to
localhost.  Allowing untrusted code to connect to things like
`127.0.0.1:22` would be bad.

How do others solve this problem? There are three solutions.

${ "###" } Namespaces

Linux supports "namespaces" - an abstraction that is a basic building
block for container technologies like Lxc and Docker. With namespaces
it possible to redefine the scope of "things". For example you can
define a new abstract "127.0.0.1" address, dedicated to a given
sandboxed process. In such setup each sandboxed process could have its
own localhost.

Couple of projects using namespaces for sandboxing:

 * [Firejail](https://firejail.wordpress.com/)
 * [Bubblewrap](https://github.com/projectatomic/bubblewrap)

Enforcing `connect` limits with Linux network namespace would have to
be done by deploying dedicated iptables firewall rules for each and
every sandbox. This is a rather heavyweight solution.

There are other options though.  It's possible to perform syscall
payload verification in a more lightweight fashion.

${ "###" } Ptrace based sandboxes

A method often practiced is to trace the untrusted process with a
`ptrace`.  The tracing process would look for dangerous syscalls and
validate the arguments passed before passing it to kernel. With
`ptrace` one could enforce complex access policies.

This is how number of sandboxing projects work:

 * [Systrace](http://www.citi.umich.edu/u/provos/systrace/) by Niels Provos
 * [mbox](https://pdos.csail.mit.edu/archive/mbox/)

Using ptrace has its disadvantages. First, it's dead slow. Instead of
going straight to the kernel, each traced syscall must go back and forth
to the tracing process. This is really inefficient.

There is a second issue. Using ptrace for validation doesn't work with
a multi-threaded code.  It's impossible to work around
[time-of-check time-of-use (TOCTOU)](https://lwn.net/Articles/245630/)
bugs. In a multi-threaded scenario one process can call the syscall
with trusted arguments, get them through a trusted ptrace gateway
validation, just to allow another thread to overwrite them. With
proper timing it's possible to fool the ptrace gateway checks.

${ "###" } Trusted broker sandboxes

Another option is to launch a trusted process alongside `seccomp`ed
untrusted one. Instead of calling a dangerous syscalls, the untrusted
process would call an IPC and ask the trusted brother to perform the
action. The trusted process will have all the parameters in its own
memory space, preventing TOCTOU issue. It could reliably enforce any
access policies before performing the dangerous action. This design
needs a decent IPC mechanism, but more importantly needs the untrusted
code to be patched to use it when needed. All the calls to things like
`open`, `connect` or `socket` would need to go through the IPC. Hacks
like `LD_PRELOAD` are likely not to work - the untrusted code would
need to be specifically written with IPC in mind. Furthermore it's not
obvious how `brk` and `mmap` / `munmap` could be validated in this
model.

This is more or less how Google Chrome wanted to restrict its renderer
process in early days of `seccomp`. There are a couple of excellent
historical articles on the subject:

 * [Sandboxing on Linux (2008)](https://www.imperialviolet.org/2008/11/27/sandboxing-on-linux.html)
 * [Chromium sandbox (2009)](https://www.imperialviolet.org/2009/08/26/seccomp.html)
 * [LWN piece on Chromium (2009)](https://lwn.net/Articles/346902/)
 * [Chromium using seccomp-bpf (2012)](http://blog.cr0.org/2012/09/introducing-chromes-next-generation.html)

Bear in mind that
[`seccomp-bpf` was only added to Linux 3.5 in 2012](https://lwn.net/Articles/656307/).

${ "###" } Would it scale?

OS-level isolation does have its disadvantages. For one each untrusted
sandboxed piece of foreign code it would require at least dedicated
operating system process.

It's definitely possible to run many OS processes on a Linux server
but there are limits. It might be okay to run a couple of hundred such
sandboxes, but getting into thousands or tens of thousands would be
tricky.

Even assuming perfect Linux scheduler scalability there are other
implicit costs when running of thousands of OS processes. At this
scale
[the cost a context switch](http://blog.tsunanet.net/2010/11/how-long-does-it-take-to-make-context.html)
could be a problem, mostly due to
[cache pollution and TLB flushes](http://www.cs.rochester.edu/u/cli/research/switch.pdf).

The `seccomp` approach to sandboxing does work and it's suitable for
many others in the industry. I'm only worried that for thousands of
tenants it might scale poorer than the alternative lighter approaches.

There is yet another, more lightweight, solution worth considering.

<div class="image" style="height:${364+28}px"><img src="chrome.jpg"><div>
<small><a href="https://www.flickr.com/photos/br1otcom/13506846613/">image by Thomas Cloer</a></small>
</div></div>

Software fault isolation
----

There is a sandboxing approach known as software fault isolation -
SFI. SFI achieves isolation purely in userspace, without much kernel
support. In past SFI was mostly an unpractical academic subject, but
recently there was one significant production implementation - the
[Google Chrome NaCL project](https://en.wikipedia.org/wiki/Google_Native_Client).

SFI solutions have two major parts:

 - *control-flow integrity*: SFI must ensure the untrusted code won't
   execute any dangerous operations. This is usually achieved by
   [a dynamic recompilation](https://en.wikipedia.org/wiki/Dynamic_recompilation)
   phase. All the instructions passed to the CPU are validated and
   rewritten. This ensures the CPU would execute only trusted,
   validated code.

 - *memory integrity*: The untrusted code shares memory address space
   with the SFI runtime. This is a problem. An SFI runtime must
   therefore restrict memory access for tenants, and disallow
   untrusted code from touching sensitive memory ranges.

Unfortunately most SFI solutions solve the memory access problem only
half-way. In most cases the authors assume it's sufficient to restrict
memory writes only, leaving memory reads unrestricted. In
multiple academic SFI implementations a tenant can read all the
secrets of other tenants. Since, in its pure form, the SFI focuses on
isolating the _faults_ of the software, ensuring a failure of one
tenant will not affect others restricting writes only is sufficient.

${ "###" } NaCL

Google's NaCL is a truly awesome project. There are two main papers on
it:
[the original implementation](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/34913.pdf)
and the
[ARM and x86-64 improvements](http://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/35649.pdf).
NaCl allows anyone to execute an untrusted binary blob straight in
your browser. Google run a [security contest](https://developer.chrome.com/native-client/community/security-contest) after they announced the
project. Here is the best security review of the early NaCL
implementation:

 - [Mark Dowd and Ben Hawkes](https://www.lateralsecurity.com/downloads/hawkes_HAR_2009_exploiting_native_client.pdf) on [NaCL](https://bugs.chromium.org/p/nativeclient/issues/detail?id=86)
 - [Chris Rohlf's summary from 2012](https://media.blackhat.com/bh-us-12/Briefings/Rohlf/BH_US_12_Rohlf_Google_Native_Client_Slides.pdf)

Over the time the NaCL technology has been reused and
adapted for sandboxing outside the browser:

  - [Golang playground](https://blog.golang.org/playground)
  - [ZeroVM](http://www.zerovm.org/)

Interestingly NaCL doesn't do dynamic recompilation. Instead it
achieves the control-flow integrity by ensuring the binary is compiled
in a special way. When executing a blob the runtime runs a lightweight
code validator to confirm the code doesn't do anything naughty. For
completeness I should mention this has been changed in recent
[NaCL versions](https://docs.google.com/a/chromium.org/viewer?a=v&pid=sites&srcid=Y2hyb21pdW0ub3JnfGRldnxneDo3ZmQ2NjI2NjFkM2EzYjFl),
but the principle of avoiding dynamic recompilation stays.


Memory integrity is achieved by enforcing all memory instructions
explicitly mask write addresses. Without getting into too much details
- it doesn't really address the "restricting memory reads"
problem. NaCL has been designed to run exactly one tenant in one OS
process. Running thousands of NaCL sandboxes would share the cache
pollution and TLB flush scalability issues of `seccomp`-based designs.

${ "###" } VX32

[Vx32](https://pdos.csail.mit.edu/~baford/vm/) is a magical piece of
code. It was created
[by Bryan Ford and Russ Cox in 2008](https://pdos.csail.mit.edu/papers/vx32:usenix08/). One
of its aims was to allow running native Plan9 binaries on Linux. Vx32
is a little library that can be used to execute arbitrary statically
compiled x86 executable in sandboxed environment.

It enforces control flow integrity by doing dynamic
recompilation. Only a basic i386 opcodes can get through its
validator.

The memory restrictions are enforced by using
[the x86 segmentation registers](https://web.archive.org/web/20150117164025/http://www.lshift.net/blog/2010/03/31/what-has-happened-to-the-segment-registers). This
design has a couple of restrictions: segmentation on x86 is only
supported in 32 bit code and all the data must live in lower 4 GiB of
address space. This limits the number of loaded tenants. For example,
it's only possible to fit 32 separate tenants, each using 128MiB, into
4 gigs.

Vx32 has a strong advantage though - it has been created exactly for
multi-tenant use case. It can run multiple pieces of untrusted code,
exposes a nice API, allows creating a scheduler. Vx32 will enforce
hard memory restrictions, with each tenant fully isolated from
others. Vx32 is a surprisingly small and lightweight library,
consisting only of couple of thousands line of C.

Sadly, it hasn't been security audited and seems to never get out of
initial stages. I'm sure it contains a some (fixable) security bugs -
doing dynamic recompilation right is really hard.


<div class="image" style="height:${364+28}px"><img src="kvm.jpg"><div>
<small><a href="https://www.flickr.com/photos/naudinsylvain/8663443884">image by Sylvain Naudin</a></small>
</div></div>

Virtual machine isolation
----

There is one more way of doing sandboxing - it's possible to reuse the
x86 virtualization features. In theory it should be possible
[to use KVM for sandboxing](https://david.wragg.org/blog/2016/06/kvm-hello-world.html). To
my knowledge nobody had build a multi-tenant, single-process KVM
sandbox yet. There are some projects trying the KVM route though:

 * [KVMSandbox](https://cs.brown.edu/research/pubs/theses/masters/2012/ayer.pdf)
 * [libvirt](http://sandbox.libvirt.org/) and [a relevant presentation](http://people.redhat.com/berrange/kvm-forum-2012/libvirt-sandbox-kvm-forum-2012.pdf)


Final thoughts
----------

Exploring x86 and Linux sandboxing is very exciting. There is plenty
of momentum, with things like Docker and Sandstorm charging ahead.
Core technologies like KVM are improving all the time. Then there are
unexplored possibilities - for example, it may be possible
to reuse [Linux Security Module](https://en.wikipedia.org/wiki/Linux_Security_Modules)
infrastructure for sandboxing.

Unfortunately, from what I've seen, no technology ticks all the boxes
for my use case. I'm still looking for an audited, lightweight, easy
to use sandbox, geared for running multi-tenant code. I'm optimistic
though. Doing sandboxing right is a huge opportunity.



</%block>

