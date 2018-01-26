<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


---------

Some time ago I wrote about
[a history of `select()` syscall](/2016-11-01-a-brief-history-of-select2/). While
that piece was a necessary introduction to
[the followup](https://idea.popcount.org/2017-01-06-select-is-fundamentally-broken/)
post, it triggered interesting discussions.

It took me a while but I finally realized what is the core question I
asked myself. Here it is:

> Were Unix processes intended to be CSP-style processes? Are file
> descriptors a CSP-derived "channels"? Is "select()" equivalent to ALT
> statement?

The direct answer is "no". CSP is younger than
Unix. As [Tony Garnock-Jones](https://twitter.com/leastfixedpoint) points out, the first
[paper about CSP](http://weblab.cs.uml.edu/~bill/cs515/CSP_Hoare_78.pdf)
was published in 1978 and file descriptors had been around since the
very early days of Unix.

While file descriptors are not channels, maybe they should have
been? CSP-like channels are generally composable, while I believe
Unix's `select` is not. This goes to the second point:

> Unix programs using "select()" don't compose. But maybe they could?
> Could "select()" have been implemented in a way that would allow
> composability?

When programming in Golang, one can make use of ALT statement and
built in channels. Generally speaking Golang channels are
composeable. Similar thing is true in Erlang - you can avoid complex
state machines by skilfully stacking `gen_server` processes.

Why this isn't possible with the Unix process model? Why can't we
combine Unix processes in the same way as we combine Golang or Erlang
ones?

I'll intuitively blame the `select` syscall, but the problem is
deeper and I don't know the answer.

The buffering proxy
----

Couldn't we just drop `select`? How far in could we go without it? In
[the previous article](/2016-11-01-a-brief-history-of-select2/) we
mentioned two use cases:

 - inet daemon
 - console multiplexing

There are more problems that absolutely need `select`. [David Wragg](https://twitter.com/dwragg) mentioned "the buffering proxy" problem:

> Imagine a process that does buffering.  Consider a simple program
> that reads data from one stream, buffers it, and writes to another
> stream.  If you split this into two processes using a pipe between
> them, you become constrained by the kernel's pipe buffer limit.  To
> have an arbitrary buffer size, it has to be in a single process that
> does a select for readability of the input stream and writability of
> the output stream.

The same problem was mentioned by Chris Siebenmann in his blog in 2010:

 * [The processing flow of a network copying program](https://utcc.utoronto.ca/~cks/space/blog/programming/NetcopyLogic)

Memory consumption of idle connections
----

Earlier this year Chris mentioned another problem requiring `select`:
the "memory consumption for idle connections":

 * [One downside of a queued IO model is memory consumption for idle connections](https://utcc.utoronto.ca/~cks/space/blog/programming/QueuedIOMemoryUsageDownside)

This writeup was a followup to Evan Klitzke's article:

  * [Goroutines, Nonblocking I/O, And Memory Usage](https://eklitzke.org/goroutines-nonblocking-io-and-memory-usage)
  * [YCombinator discussion](https://news.ycombinator.com/item?id=13331284)

To make the story even more fascinating this "memory consumption"
argument was raised in the Golang bug tracker:

 * [net: add mechanism to wait for readability on a TCPConn](https://github.com/golang/go/issues/15735#issuecomment-266574151)

For my taste this sounds like introduction of a callback hell, so I'm
skeptical. But whatever the outcome, I'm sure the discussion is going
to be interesting.

BSD Socket API revamp
---

Finally, ever-productive Martin Sustrick wrote this nice RFC proposal
of purely-blocking sockets API:

 * [BSD Socket API Revamp](https://raw.githubusercontent.com/sustrik/dsock/master/rfc/sock-api-revamp-01.txt)
 * [YCombinator discussion](https://news.ycombinator.com/item?id=13676804)

This document doesn't address the `select` question by pushing the
multiplexing discussion under the carpet:

>  [...] This memo assumes that there already exists an efficient
> concurrency implementation where forking a new lightweight process
> takes at most hundreds of nanoseconds and context switch takes tens
> of nanoseconds.  Note that there are already such concurrency
> systems deployed in the wild.  One well-known example are Golang's
> goroutines but there are others available as well.

But nonetheless, I very much like the idea of only blocking API's
being exposed to the user.

Final thoughts
---

While the Unix socket model and CSP has been with us for almost 40
years, they certainly aren't closed subjects. There is plenty of
fresh thought in this area: optimizing memory usage, finding
right composability abstractions and going back to the idea of
exposing purely blocking API's.


</%block>



