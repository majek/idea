
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


Every once in a while I run into an obscure computer technology that
is a hidden gem, which over the years has become mostly
forgotten. This is exactly how I feel about the `tcpdump` tool and its
kernel counterpart the packet filter interface.

For example, say you run:

    $ tcpdump -ni eth0 udp and port 53

For most of us this command is pure magic, almost nobody understands
what happens behind the scenes. This is understandable, there is
little need to know how it works: the tool does its job very well,
it's descriptive and very fast.

In this article I'll try to explain how `tcpdump` works and how we use
its spinoffs to help fight the packet floods that hit us every day.

But first, we need a bit of history.

Historical context
------------------

Since workstations became interconnected, network administrators had a
need to "see" what is flowing on the wires. The ability to sniff the
network traffic is necessary when things go wrong, even for the most
basic debugging.

For this reason operating systems developed APIs for packet
sniffing. But, as there wasn't any real standard for it every OS had
to invent
[a different API](http://www.cs.columbia.edu/~nahum/w6998/lectures/vpk-columbia-nsdi-pf.pdf):
Sun’s STREAMS NIT, DEC's Ultrix Packet Filter, SGI’s Snoop and Xerox
Alto had CMU/Stanford Packet Filter. This led to many
complications. The simpler APIs just copied all the packets to the
user space sniffer, which on a busy system resulted in a flood of
useless work. The more complex APIs were able to filter packets before
passing them to userspace, but it was often cumbersome and slow.

All this changed in 1993 when Steven McCanne and
[Van Jacobson](https://en.wikipedia.org/wiki/Van_Jacobson) published
the paper introducing a better way of filtering packets in the kernel,
they called it
["The BSD Packet Filter" (BPF)](http://www.tcpdump.org/papers/bpf-usenix93.pdf).

Since then
[the BPF](https://en.wikipedia.org/wiki/Berkeley_Packet_Filter) has
taken the world by a storm and along with `libpcap` and `tcpdump`
become the de-facto standard in network debugging.

Tcpdump dissected
-----------------

Tcpdump is composed of three logical parts:

 - Expression parser: Tcpdump first parses a readable filter
   expression like `udp and port 53`. The result is a short program in
   a special minimal bytecode, the BPF bytecode.

 - The BPF bytecode (filter program) is attached to the network tap
   interface.

 - Finally, tcpdump pretty prints filtered packets received from the
   network tap. Pretty printing is far from a simple task, tcpdump
   needs to understand many network protocols to do it.

Expression parser
-----------------

Given a packet filtering expression, tcpdump produces a short program
in the BPF bytecode. The easiest way to see the parser in action is to
pass a `-d` flag, which will produce a readable assembly-like program:

    $ sudo tcpdump -ni en0 -d "udp"
    (000) ldh      [12]
    (001) jeq      #0x86dd          jt 2	jf 7
    (002) ldb      [20]
    (003) jeq      #0x11            jt 10	jf 4
    (004) jeq      #0x2c            jt 5	jf 11
    (005) ldb      [54]
    (006) jeq      #0x11            jt 10	jf 11
    (007) jeq      #0x800           jt 8	jf 11
    (008) ldb      [23]
    (009) jeq      #0x11            jt 10	jf 11
    (010) ret      #65535
    (011) ret      #0

Here you can find
[the documentation of the assembly syntax](https://www.kernel.org/doc/Documentation/networking/filter.txt).

Less readable compiled bytecode is printed with `-ddd` option:

    $ sudo tcpdump -ni en0 -ddd "udp"|tr "\n" ","
    12,40 0 0 12,21 0 5 34525,48 0 0 20,21 6 0 17,21 0 6 44,48 0 0 54,21 3 4 17,21 0 3 2048,48 0 0 23,21 0 1 17,6 0 0 65535,6 0 0 0,


Kernel API
----------

Tcpdump can open a network tap by requesting a `SOCK_RAW` socket and
after a few magical `setsockopt` calls a filter can be set with
`S_ATTACH_FILTER` option:

    sock = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_ALL))
    ...
    setsockopt(sock, SOL_SOCKET, SO_ATTACH_FILTER, ...)

From now on the BPF filter will be run against all received packets on
a network interface and only packets matching that filter will be
passed to that network tap file descriptor.

All the gritty details are described in the
[`Documentation/networking/filter.txt`](https://www.kernel.org/doc/Documentation/networking/filter.txt)
file. For the best preformance one can use
[a zero-copy `PACKET_MMAP` / `PACKET_RX_RING` interface](https://www.kernel.org/doc/Documentation/networking/packet_mmap.txt),
though most people should probably stick to the
[high level `libpcap` API](http://www.tcpdump.org/manpages/pcap.3pcap.html).

The BPF bytecode
--------------------------

In essence Tcpdump asks the kernel to execute a BPF program within the
kernel context. This might sound risky, but actually isn't. Before
executing the BPF bytecode kernel ensures that it's safe:

- All the jumps are only forward, which guarantees that there aren't
  any loops in the BPF program. Therefore it must terminate.
- All instructions, especially memory reads are valid and within range.
- The single BPF program has less than 4096 instructions.

All this guarantees that the BPF programs executed within kernel
context will run fast and will never infinitely loop. That means the
BPF programs are not Turing complete, but in practice they are
expressive enough for the job and deal with packet filtering very
well.

The original concepts underlying the BPF were described in a 1993 and
didn't require updates for many years. The Linux implementation on the
other hand is steadily evolving: recently a
[new and shiny just-in-time BPF compiler](http://lwn.net/Articles/437981/)
was introduced, and a few months ago an attempt was made to upgrade
the [BPF assembly to a 64-bit form](https://lwn.net/Articles/584377/).


Not only tcpdump
----------------

BPF is an absolutely marvelous and flexible way of filtering
packets. For years it got reused in more places and now Linux uses BPF
filters for:

 - tcpdump-style packet filtering

 - ["cls_bpf"](http://lxr.free-electrons.com/source/net/sched/cls_bpf.c)
   classifier for traffic shaping (QoS)

 - ["seccomp-bpf"](https://www.kernel.org/doc/Documentation/prctl/seccomp_filter.txt)
   syscalls filter to sandbox applications

 - "xt_bpf" iptables module


How we use it
-------------

CloudFlare deals with massive packet floods on a daily basis. It's
very important for us to be able to drop malicious traffic fast, long
before it hits the application.

Unfortunately matching before the application is not easy. Naive
iptables filtering, for example looking just at the source IP, doesn't
work as floods get more sophisticated. The iptables module closest to
our needs is
["xt_u32"](http://www.stearns.org/doc/iptables-u32.current.html), but
it's hard to understand and somewhat limited. Though it's generally
[pretty useful](https://github.com/smurfmonitor/dns-iptables-rules/blob/master/domain-blacklist.txt),
and to make it easier people wrote
[rule generators](http://www.bortzmeyer.org/files/generate-netfilter-u32-dns-rule.py).

But what works for us best is the "xp_bpf" iptables module by Willem
de Bruijn. With it we can match an iptable rule based on any BPF
expression.

Unfortunately, our BPF bytecode became pretty complex and it can't be
written as a usual tcpdump expression any more. Instead we rely on a
custom crafted BPF bytecode, for example, this is an "xt_bpf" bytecode
that matches a DNS query for "www.example.com":


        ld #20
        ldx 4*([0]&0xf)
        add x
        tax

    lb_0:
        ; Match: 076578616d706c6503636f6d00 '\x07example\x03com\x00'
        ld [x + 0]
        jneq #0x07657861, lb_1
        ld [x + 4]
        jneq #0x6d706c65, lb_1
        ld [x + 8]
        jneq #0x03636f6d, lb_1
        ldb [x + 12]
        jneq #0x00, lb_1
        ret #1

    lb_1:
        ret #0

To compile it we use the tools from the
[`tools/net`](https://github.com/torvalds/linux/tree/master/tools/net)
directory:

    $ bpf_asm drop_example_com.bpf
    14,0 0 0 20,177 0 0 0,12 0 0 0,7 0 0 0,64 0 0 0,21 0 7 124090465,64 0 0 4,21 0 5 1836084325,64 0 0 8,21 0 3 56848237,80 0 0 12,21 0 1 0,6 0 0 1,6 0 0 0

Finally you can apply the rule like so:

    iptables -A INPUT \
        -p udp --dport 53 \
        -m bpf --bytecode "14,0 0 0 20,177 0 0 0,12 0 0 0,7 0 0 0,64 0 0 0,21 0 7 124090465,64 0 0 4,21 0 5 1836084325,64 0 0 8,21 0 3 56848237,80 0 0 12,21 0 1 0,6 0 0 1,6 0 0 0," \
        -j DROP

This is a fairly simple rule just looking for a particular bytes in
the packet. The same could be achieved using "u32" or "string"
modules. But "xt_bpf" gives us more flexibility. For example we can
make the rule case insensitive:

    ...
    lb_0:
        ; Match: 076578616d706c6503636f6d00 '\x07example\x03com\x00'
        ld [x + 0]
        or #0x00202020
        jneq #0x07657861, lb_1
        ld [x + 4]
        or #0x20202020
        jneq #0x6d706c65, lb_1
        ld [x + 8]
        or #0x00202020
        jneq #0x03636f6d, lb_1
        ldb [x + 12]
        jneq #0x00, lb_1
        ret #1
    ...

Or match all the subdomains of "example.com":

     ...
    lb_0:
        ; Match: *
        ldb [x + 0]
        add x
        add #1
        tax
        ; Match: 076578616d706c6503636f6d00 '\x07example\x03com\x00'
        ld [x + 0]
        jneq #0x07657861, lb_1
        ld [x + 4]
        jneq #0x6d706c65, lb_1
        ld [x + 8]
        jneq #0x03636f6d, lb_1
        ldb [x + 12]
        jneq #0x00, lb_1
        ret #1
    ...

These kind of rules are very useful, they allow us to pinpoint the
malicious traffic and drop very early. Just in the last couple of
weeks we dropped 870,213,889,941 packets with few BPF rules. We often
see 41 billion packets dropped throughout a night due to a single well
placed rule.

Summary
------

Just as intended by Steven McCanne and Van Jacobson, the BPF is still
very useful and extremely fast. Even without enabling the BPF JIT we
don't see any performance hit of applying complex BPF rules.

I'm sure we'll use more BPF filters in the future to shield ourselves
from malicious traffic and to have more CPU to deal with legitimate
requests.


Does generating BPF assembly sound like fun?
[We're hiring talented developers](http://www.cloudflare.com/join-our-team),
including to our
[elite office in London](http://blog.cloudflare.com/cloudflare-london-were-hiring).




</%block>
