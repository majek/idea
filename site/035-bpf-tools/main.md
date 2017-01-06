
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

In
[the recent article](http://blog.cloudflare.com/bpf-the-forgotten-bytecode)
I've described the basic concepts behind the BPF bytecode and the "xt_bpf"
iptables module. In this post I'll explain how exactly we use it and
what tools we created to generate and deploy the BPF rules.

The code
--------

The BPF Tools are now available on GitHub:

 - https://github.com/cloudflare/bpftools

For installation instruction review the
[README](https://github.com/cloudflare/bpftools#bpf-tools), but typing
"make" should do most of the work:

    $ git clone https://github.com/cloudflare/bpftools.git
    $ cd bpftools
    $ make

BPF Tools repository contains a number simple Python scripts, some of
them focus on analyzing pcap files, others focus more on the BPF:

 - `pcap2hex`, `hex2pcap`
 - `parsedns`
 - `bpfgen`
 - `filter`
 - `iptables_bpf`, `iptables_bpf_chain`

We rely on tools from Linux Kernel
[`/tools/net`](https://github.com/torvalds/linux/tree/master/tools/net)
directory for BPF assembler. To make your life easier we ship a copy
in the `linux_tools` subdirectory.

The BPF Tools should be usable and working, but don't expect too much.
This small utilities were written to be easily hackable and they will
be in a state of constant flux: this _is_ our toolkit. Please expect
some degree of code instability.

Here at CloudFlare we run a number of
[authoritative DNS servers](https://en.wikipedia.org/wiki/Domain_Name_System#Authoritative_name_server)
and we constantly deal with malicious actors flooding our servers with
DNS requests. It should no surprise that our BPF Tools focus on DNS
traffic, although they are easily adaptable to any other stateless
floods.

It all starts with a pcap
----------------------

To start you need a
[pcap savefile](http://www.tcpdump.org/manpages/pcap-savefile.5.txt)
containing a traffic dump. For example to capture a pcap of DNS
requests we run:

    $ sudo tcpdump -pni eth0 -s0 -w example.pcap -vv -c 10000 ${"\\"}
           "ip and dst port 53"
    listening on eth0, link-type EN10MB (Ethernet)

It's important to record the traffic on EN10MB (Ethernet) device, as
the scripts expect to see packets with a 14-byte Ethernet header. If
you forget about that and record on `any` interface (LINUX_SLL) you
can fix the pcap by using the `pcap2hex` / `hex2pcap` tools. They are
able to amend the L2 header and make it look like Ethernet again:

    $ cat sll.pcap | ./pcap2hex | ./hex2pcap > ethernet.pcap

As we are on this, here is a sample output of `pcap2hex` tool, say we
captured requests going to our favorite domain `www.example.uk`
(notice the `--ascii` flag):

    $ cat example.pcap | ./pcap2hex --ascii | head
    000ffffff6603c94d5cb47f0080045000056817b4000f91147a3cba204c6adf53a1aa408003500426dd26366000000010000000000010e697471766d6e737a656c757a6f6a03777777076578616d706c6502756b00000100010000291000000080000000        ..S..`<...G...E..V.{@...G.......:....5.Bm.cf...........itqvmnszeluzoj.www.example.uk.......)........
    000ffffff6603c94d5cb47f008004520004fdf234000f41110107b1e341cadf53a1a84a00035003b4a99e25c00000001000000000001076969766c69657903777777076578616d706c6502756b00000100010000291000000080000000      ..S..`<...G...E..O.#@.....{.4...:....5.;J..\...........iivliey.www.example.uk.......)........

Take a look at the traffic, it looks like we captured a flood of
requests to `<random string>.www.example.uk`! We see this kind of
floods all the time. I believe the goal of this flood is to keep our
DNS server busy with preparing NXDOMAIN responses and run out of CPU.

Let's take a closer look at these packets.


Parsing the DNS request
---------------

With a DNS traffic handy you may want to take a closer look at the
details of the DNS requests. For that pick a hex-encoded packet from
the output of `pcap2hex` and pass it to the `parsedns` script:

    $ ./parsedns 000ffffff6603c94d5...
    ...
    [.] l4: a408003500426dd2
          source port: 41992
     destination port: 53
               length: 66
    [.] l5: 6366000000010000000000010e6974717...
                   id: 0x6366
                flags: 0x0000 query op=0 rcode=0
            questions: 1
              answers: 0
                 auth: 0
                extra: 1
    #-46         q[0]: 'itqvmnszeluzoj' 'www' 'example' 'uk' .
                        type=0x0001 class=0x0001
             extra[0]: .
                        type=0x0029 class=0x1000
                        ttl=32768 rrlen=0:
                            bufsize=4096
                            dnssec_ok_flag

This tool pretty prints a DNS packet and presents all the interesting
bits. Sometimes the flooding tools have bugs and set a bit somewhere
making it easy to distinguish malicious requests.

Unfortunately the request above looks pretty normal. We could
distinguish the traffic on the `EDNS` DNS extension but some real
recursors also set this flag as well, so this strategy could result in
false positives.

Preparing the BPF
-----------------

Blocking this flood is simple - we can safely assume `www.example.uk`
domain doesn't have _any_ subdomains, Instead of looking at low level
bits of DNS packets we can drop all the packets asking for
`*.www.example.uk`.

The tool `bpfgen` generates the BPF bytecode. This is the most
important tool here.

Right now it has three "BPF generators": `dns`, `dns_validate` and
`suffix`. We'll focus only on the first one which generates BPF rules
matching given DNS domains. To match all the requests matching the
pattern `*.www.example.uk` run:

    $ ./bpfgen dns -- *.www.example.uk
    18,177 0 0 0,0 0 0 20,12 0 0 0,7 0 0 0,80 0 0 0, ...

That does look pretty cryptic, here's how can you generate an
assembly-like BPF syntax:

    $ ./bpfgen --assembly dns -- *.www.example.uk
        ldx 4*([0]&0xf)
        ; l3_off(0) + 8 of udp + 12 of dns
        ld #20
        add x
        tax
    ...

The generated code is way too long to post and explain here, I
strongly recommend looking at the `bpftools/gen_dns.py` file and
reviewing the Kernel
[`networking/filter.txt`](https://github.com/torvalds/linux/blob/master/Documentation/networking/filter.txt)
documentation.

For more details about the `bpfgen` tool and its features see the
documentation:

    $ ./bpfgen --help
    $ ./bpfgen dns -- --help
    $ ./bpfgen dns_validate -- --help
    $ ./bpfgen suffix -- --help

The BPF bytecode generated by `bpfgen` is somewhat special - it's
prepared to be passed to the `xt_bpf` iptables module and _not_ the
usual tcpdump. The bytecode passed to `xt_bpf` must assume the packet
starts from the IP header without any L2 header. This is not how it
usually works for tcpdump which assumes packets do have a proper L2
header. In other words: you can't reuse bytecodes between tcpdump and
`xt_bpf`.

To work around that `bpfgen` has an `--offset` flag. To create bpf for
`xt_bpf` you can supply the explicit `--offset=0` flag:

    $ ./bpfgen --offset=0 dns -- *.www.example.uk

To create bpf for tcpdump on Ethernet packets you must supply
`--offset=14` flag:

    $ ./bpfgen --offset=14 dns -- *.www.example.uk


Verification
------------

It's always a good idea to test the bytecode before putting it on
production servers. For that we have a `filter` script. It consumes a
pcap file, runs it through a _tcpdump_-like BPF and produces another
pcap with only packets that matched given bytecode.

To see what traffic will _match_ our BPF:

    $ cat example.pcap ${"\\"}
        | ./filter -b "`./bpfgen --offset 14 dns -- *.www.example.uk`" ${"\\"}
        | tcpdump -nr - | wc -l
    9997

Hurray, our BPF successfully matches 99.97% of the flood we
recorded. Now let's see that what packets it will _not match_:

    $ cat example.pcap ${"\\"}
        | ./filter -b "`./bpfgen -o 14 --negate dns *.www.example.uk`" ${"\\"}
        | tcpdump -nr - | wc -l
    3

It's often worthwhile to inspect the matched and unmatched packets and
make sure the BPF is indeed correct.

**Note**: `filter` uses the usual `libpcap` infrastructure, that's why it
requires the BPF to consume L2 header. We will likely rewrite that
code and change `filter` to use BPF generated for `xt_bpf`.

Iptables
--------

With the BPF bytecode tested we can safely deploy it to the
servers. The simplest way to do it is to apply an `iptables` rule
manually:

    iptables -I INPUT 1 ${"\\"}
        --wait -p udp --dport 53 ${"\\"}
        -m bpf --bytecode "14,0 0 0 20,177 0 0 0,12... ${"\\"}
        -j DROP

(You will need a recent iptables with `xt_bpf` support.)

This can be very cumbersome. Especially that the `--bytecode`
parameter does contain spaces which makes it pretty unfriendly for
passing with bash or ssh.

Generating a bash script
------------------------

To speed up the process we have another tool `iptables_bpf`. It
accepts almost the same parameters as `bpfgen` but, as opposed to
printing a raw BPF bytecode, it produces a bash script:

    $ ./iptables_bpf dns -- *.example.uk
    Generated file 'bpf_dns_ip4_any_example_uk.sh'

The generated script is fairly straightforward and at its core it
applies an iptables rule like this:

    iptables ${"\\"}
        --wait -I INPUT 1 ${"\\"}
        -i eth0 ${"\\"}
        -p udp --dport 53 ${"\\"}
        -m set --match-set bpf_dns_ip4_any_example_uk dst ${"\\"}
        -m bpf --bytecode "16,177 0 0 0,0 0 0 20,12 ... ${"\\"}
        -m comment --comment "dns -- *.example.uk" ${"\\"}
        -j DROP


As you can see it depends on an ipset "match-set" named
`bpf_dns_ip4_any_example_uk`. Ipsets are a pretty recent addition to
iptables family and they allow us to control what destination ip's the
rule will be applied to. We use this for additional safety. When you
deploy the generated script by default it will not match any
traffic. Only when you add a server ip to the ipset the BPF rule will
be executed. To add a server ip to the ipset run:

    ipset add bpf_dns_ip4_any_example_uk 1.1.1.1/32

Alternatively rerun the script with an ip as a parameter:

    $ sudo ./bpf_dns_ip4_any_example_uk.sh 1.1.1.1/32

If things go wrong pass `--delete` to remove the BPF iptables rule and
the ipset:

    $ sudo ./bpf_dns_ip4_any_example_uk.sh --delete

Although fairly advanced and I hope practical, this generated script
is not really intended as a fit-for-all deployment tool for all BPF
scripts. Feel encouraged to tweak it to your needs.

Chaining bpf rules
-------------------

In extreme cases you might want to chain BPF rules. As an example see
`iptables_bpf_chain` script, you can run it like this:

    $ ./iptables_bpf_chain -w example_uk ${"\\"}
        --accept www.example.uk ${"\\"}
        --accept ns.example.uk ${"\\"}
        --drop any
    Generated file 'example_uk_ip4.sh'

The generated file will create iptables chain "EXAMPLE_UK" and it will
add three rules to it: two BPF rules accepting some packets and one
rule dropping everything else. The chain will be referenced from the
"INPUT" chain in similar fashion to previous example. Before using
`iptables_bpf_chain` please do review it carefully.

Summary
-------

This article only scratched the surface of our tools. They can do much
more things, like:

 - match IPv6 packets
 - do suffix matching
 - match domains case insensitively
 - perform basic DNS request validation

For details read the documentation with `--help`.

Fighting packets floods is tough, but with tools in place it can be
managed efficiently. The `xt_bpf` iptables module is very effective
and with our BPF generation tools it allows us to drop malicious
traffic in iptables before it hits the application.

By sharing these tools we hope to help administrators around the
world, we know we are not the only ones fighting packet floods!




</%block>
