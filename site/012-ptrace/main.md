<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="subtitle"><h2>${subtitle}</h2></div>

<div class="date">${date.strftime('%d %B %Y')}</div>

In recent years the _"Apple is evil"_ discussion started recurring
more and more often.

[In last week's edition](http://news.ycombinator.com/item?id=4765180)
on the YCombinator,
[jrockway](http://news.ycombinator.com/user?id=jrockway) mentioned a
[very interesting technical quirk](http://news.ycombinator.com/item?id=4765544):

> [...] I tried to run gdb on iTunes, and gdb segfaulted. I did some
> research and found that Apple added extra code to the OS just to
> prevent someone from doing exactly that. They spent additional
> engineering effort just to lock me out of my own computer. [...]

I won't comment on the evilness, but I can confirm the _gdb_ crash:

```
$ ps aux|grep iTunes
marek 28880 /Applications/iTunes.app/Contents/MacOS/iTunes
$ gdb -p 28880
Attaching to process 28880.
Segmentation fault: 11
```

Whoo! That's interesting. Fortunately
[comex](http://news.ycombinator.com/user?id=comex) quickly explained
what's going on: there exists a `PT_DENY_ATTACH` flag to `ptrace` that
explicitly forbids running `ptrace` on that process. iTunes uses exactly
that. Here goes an extract from the manpage `ptrace(2)`:

```
::text
PT_DENY_ATTACH
    [...] it allows a process that is not currently being
    traced to deny future traces by its parent. [...]
    If the process is currently being traced, it will exit
    with the exit status of ENOTSUP; otherwise, it sets
    a flag that denies future traces.  An attempt by the
    parent to trace a process which has set this flag will
    result in a segmentation violation in the parent.
```

It's pretty funny. According to OS X crashing parent process is
sometimes a valid and defined behaviour. I wonder if that signal can
be handled and if the kernel code for sending SIGSEGV isn't racy.


[mikeash](http://news.ycombinator.com/user?id=mikeash) explained how
to get around this stupid flag - you just need to override `ptrace`
syscall before iTunes calls it:

    $ gdb /Applications/iTunes.app/Contents/MacOS/iTunes
    > b ptrace
    > commands
    >return 0
    >cont
    >end
    > r


That's it. Another day, another useless API.

</%block>
</article>
