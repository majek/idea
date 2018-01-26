<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Previous articles in this series:

 1. [The history of the Select(2) syscall](/2016-11-01-a-brief-history-of-select2/)
 2. [Select(2) is fundamentally broken](/2017-01-06-select-is-fundamentally-broken/)
 3. [Epoll(2) is fundamentally broken](/2017-02-20-epoll-is-fundamentally-broken-12/)

In this post we'll discuss the second argument on why the `epoll()`
is broken. The problem is best described [in an LWN comment by Foom](https://lwn.net/Articles/430804/):

> And epoll certainly has a *HUGE* misdesign in it, that anyone who
> actually understood what a file descriptor is should've seen
> coming. But if you look back in the history of epoll, you'll see
> that it looks like the implementors apparently didn't understand the
> difference between file descriptors and file descriptions. :(

`epoll` is broken because it mistakes the "file descriptor" with the
underlying kernel object (the "file description"). The issue shows up
when relying on the `close()` semantics to clean up the epoll
subscriptions.

`epoll_ctl(EPOLL_CTL_ADD)` doesn't actually register a file
descriptor. Instead it registers a tuple[^tuple] of a file descriptor
and a pointer to underlying kernel object. Most confusingly the
lifetime of an epoll subscription is not tied to the lifetime of a
file descriptor. It's tied to the life of the kernel object.

Due to this implementation quirk calling `close()` on a file
descriptor might or might not trigger epoll unsubscription. If the
`close` call removes the last pointer to kernel object and causes the
object to be freed, then it will cause epoll subscription cleanup. But
if there are more pointers to kernel object, more file descriptors, in
any process on the system, then `close` will not cause the epoll
subscription cleanup. It is totally possible to receive events on
previously closed file descriptors.

[^tuple]: This was mentioned in this [email by Davide Libenzi](https://lkml.org/lkml/2008/2/26/298).

dup() as example
----

The simplest way to show the problem is with [`dup()`](http://man7.org/linux/man-pages/man2/dup.2.html). [Here's the code](https://github.com/majek/dump/blob/master/epoll/epoll-dup-example.c):

```.py
rfd, wfd = pipe()
write(wfd, "a")             # Make the "rfd" readable

epfd = epoll_create()
epoll_ctl(efpd, EPOLL_CTL_ADD, rfd, (EPOLLIN, rfd))

rfd2 = dup(rfd)
close(rfd)

r = epoll_wait(epfd, -1ms)  # What will happen?
```

You may think: the `epoll_wait` will block forever, since the only
registered file descriptor "rfd" was closed. But that's not what will
happen. By calling `dup`, we kept the reference to the underlying
"rfd" kernel object, we prevented it from being cleaned up.  The
thing is still subscribed to the epoll. `epoll_wait` will in fact
terminate reporting an event on a dead handle "rfd".

To make matters worse, you need a valid file descriptor handle to
manage subscriptions on "epfd". After we called
`close(rfd)`, there is no way to unregister it from epfd!

Neither of these will work:

```.py
epoll_ctl(efpd, EPOLL_CTL_DEL, rfd)
epoll_ctl(efpd, EPOLL_CTL_DEL, rfd2)
```

[Marc Lehmann phrased](http://lists.schmorp.de/pipermail/libev/2016q1/002680.html)
it well:

> Thus it is possible to close an fd, and afterwards forever
> receive events for it, and you can't do anything about that.

You can't rely on `close` to clean up epoll subscriptions.  If you
ever called `close` in such bad corner case, you can't fix the
"epfd". The only way froward is to trash the old "epfd", create new
one and recreate all the valid subscriptions.


Remember this advice:

> You always must always explicitly call `epoll_ctl(EPOLL_CTL_DEL)` before
> calling `close()`.

Summary
----


Explicitly deregistering file descriptors before `close` is nescesary
and works well if you control all the code. In some cases though it
may not be possible - for example when writing an epoll wrapper
library. Sometimes it's impossible to forbid users from calling
`close` themselves. For this reason it's [hard to build correct thin
abstraction layers](http://cvs.schmorp.de/libev/ev_epoll.c?view=markup#l41) on top of epoll.

Hopefully this and
[the previous](2017-02-20-epoll-is-fundamentally-broken-12/) blog
posts on `epoll()` had shedded some light on the dark corners of the
Linux epoll implementation. I can only wonder how closely Microsoft
recreated these quirks in the
[Windows Subsystem for Linux](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux).

*Update:* [Illumos](https://illumos.org/) has a custom `epoll`
implementation as well. In the [man page](https://illumos.org/man/5/epoll)
they explicitly mention the `close` weirdness and refuse to support
Linux's broken semantics.

</%block>


