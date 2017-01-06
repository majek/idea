<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

There are a lot of misconceptions about the
[fragmentation on the IP layer](https://en.wikipedia.org/wiki/IP_fragmentation). In
my opinion, the IP fragmentation is pretty much dead nowadays. Let me
explain.


IP fragmentation is a feature that allows splitting long IP packets
into a number smaller chunks called fragments. In IPv4 the routers
could perform the fragmentation, while in IPv6 only the originating
network stack is allowed to do that.

In the IPv4 header there are couple of fields related to fragmentation:

 - **DF Dont-fragment** bit, indicating that the packet should never be
   fragmented by any router on the way. Instead, the rotuter may send
   a PMTU ICMP message back.

 - **MF More-fragments** and fragment offset field - fields set on the
   fragmented packets.

 - **IPID field**, being an identifier shared by all the fragments related
   to that packet.


Packet fragmentation is usually pretty straightforward - take a big
packet, split it in MTU-sized fragments and send it off. There are
some complications, for example what
[IP options](https://en.wikipedia.org/wiki/IPv4#Options) should be
copied onto the fragments? But, fortunately it's well defined
(["copy" bit](http://www.iana.org/assignments/ip-parameters/ip-parameters.xhtml))
and IP options are rarely used anyway, so this is not a problem in
practice.

<% '''
It's worth mentioning that in IPv4 a fragment might be further
fragmented by a router on the way.
Even if the upper-layer decides to retransmit the data, the
outgoing packet will have differnt IPID field, making it impossible to

IPSTATS_MIB_FRAGCREATES, IPSTATS_MIB_FRAGOKS, and
IPSTATS_MIB_FRAGFAILS

''' %>

While the process of fragmentation is easy to perform, defragmentation is not.



Defragmentation is fundamentally flawed
-----------------

Let's start with a gimmick - in what order the fragments should be
transmitted?

In theory it doesn't matter, since the receiving host should deal with
the possibility of reordered fragments anyway. But the reality is more
complex. Early on Linux developers realized that it's better for
performance to send the fragments in _reverse_ order. This is because
only the last fragments indicates the length of the entire packet,
which would allow for more efficient buffer allocation.

This worked happily until Linux 2.4, when they realized that it some
network appliencies don't like it. For example
[the Cisco PIX firewall](https://books.google.com.sg/books?id=ALapr7CvAKkC&lpg=PP1&pg=PT537#v=onepage&q&f=false)
has an option that drops IP fragments unless they are received in
order. Linux 2.4 reversed the policy and sends frames in less-optimal
forward order.

This reveals a fundamental problem - in order to make an informed
decision firewalls and NAT devices must defragment packets before
processing them. This adds load and increases the surface for
potential overlapping-fragments bugs.

NAT devices are affected by one more significant problem. The
fragments are only identified by the tuple (src ip, dst ip, IPID). In
a situation when many NAT-ed devices speak to the same destination
server, the the identifying tuple is reduced to only (IPID)
field. It's totally concievable that the 16-bit IPID field would wrap
and collide between two distinct NAT'ed connections, making the packet
reassembly impossible.

Finally, there is no such a thing as retransmission of fragments. If
_any_ of the fragmens is lost in transit, the whole packet is
lost.


With ECMP fragments don't make any sense
-----------

In
[a blog post from February 2015](https://blog.cloudflare.com/path-mtu-discovery-in-practice/)
we described our use of ECMP. A quick recap - ECMP is a feature on
routers, that allows it to split traffic across many servers (or more
genrally - links), based on a hash of the tuple (src ip, dst ip,
protocol, src port, dst port). Unfortunately the port numbers are only
visible in the first packet fragment, making it impossible for the
router to deliver subsequent fragments to appropriate server.

To put that blantly - none of the fragmented IP packets delivered to
CloudFlare Anycast IP range will be reassembled correctly.


In practice
------

Since the fragmentation can't be trusted, in order to get relible
packet delivery everyone is using a combination of two alternative
strategies:

 - Avoid sending long packets alltogether.

 - Send long packets, but with DF bit set, and expect ICMP path MTU
   detection messages in case of any problems.


Clamp MSS to avoid long packets
--------

The first technique is especially visible on IPv6. IPv6 is actually
more problematic than IPv4 since many customers are behind
tunnels. Tunneling reduces the MTU of the path, in order to accomodate
the header bytes of the tunneling protocol. For example doing IPv6
over IPv4 GRE will reduce the MTU by at least 24 bytes. While this is
not neccesairly bad, the network stack on the devices behind the
tunnel is often unaware of it, and it's advertising large MTU on the
TCP options layer. This may lead to both parties trying, and failing
to deliver too large TCP segments.

This is very common situation in IPv6 networks. To spare the trouble
many internet services avoid the problem alltogether and just
advertise the lowest-possible MSS size on the TCP layer, which is
1280. Some examples:

```
$ sudo tcpdump -n -ttt port 80 and host 2a02:26f0:f5:281::22df and inbound
IP6 2a02:26f0:f5:281::22df.80 > 2400:cb00::beef.65366: Flags [S.], seq 1086457902, ack 903687771, win 23680, options [mss 1184,nop,nop,sackOK,nop,wscale 5], length 0
```

Notice the MSS TCP option advertising the MSS reported by the server
is clamped to only 1184 bytes.


Path MTU detection
-----------

The alternative to clamping the MSS to small values, is to rely on
Path MTU detection. The idea is advertise large MSS, set DF don't
fragment bit, and wait fo ICMP errors coming back from routers.

This works fine, is well integrated with TCP stacks and reasonably
cached. For example by default Linux caches the path MTU for 600
seconds:

```
$ cat /proc/sys/net/ipv4/route/mtu_expires
600

$ ip route get 6.1.136.14
6.1.136.14 via 1.1.240.1 dev eth0  src 1.1.240.5
    cache  expires 568sec mtu 1400
```


Linux exposes this data to a programmer as a `getsockopt`:

```.c
unsigned v = 0, vl = sizeof(v);
r = getsockopt(sd, IPPROTO_IP, IP_MTU, &v, &vl);
if (r != 0) perror("getsockopt()");
printf("MTU: %d\n", v);
```

If you writing an UDP application you can choose differnent
behaviour with the IP_MTU_DISCOVER `setsockopt`:

```.c
unsigned on = IP_PMTUDISC_DO;
r = setsockopt(fd, IPPROTO_IP, IP_MTU_DISCOVER, &on, sizeof(on));
if (r != 0) perror("setsockopt()");
```

The values are:

* `IP_PMTUDISC_DONT` - Never set DF bit, expect the routers to
  fragment the packet if needed.

* `IP_PMTUDISC_DO` - Set DF, track path MTU reported by ICMP. Fail
  with error `EMSGSIZE` if a programmer wants to transmit too long
  packet.

* `IP_PMTUDISC_PROBE` - Set DF, but don't upset the programmer with
  `EMSGSIZE` errors - send large packets anyway.

* `IP_PMTUDISC_WANT` - Set DF on short packets under MTU size. Perform
  fragmentation otherwise.



For Path MTU detection to be successful the transmitting host must
not reject ICMP messages XXX on firewall.


Statistics
-------

Fortunately fragmentation don't occur in the real internet too
often. Here are some numbers extracted from 1M packets incoming to
CloudFlare. Out of 1M packets IPv4 snapshot:

 - 250 packets were Path MTU ICMP errors
 - 95.7% were TCP packets with DF set
 - 2.4% were TCP packets without DF
 - 1.8% other packets

I don't know where the 2.5% of TCP packets without DF come from, but .



<% '''

ICMP_MIB_INERRORS if not enough bytes of payload in icmp
http://lxr.free-electrons.com/source/net/ipv4/icmp.c#L730

or no socket found
http://lxr.free-electrons.com/source/net/ipv4/udp.c#L637

/proc/sys/net/ipv4/route/mtu_expires


1) Packets fragmented _to CF_ won't work - due to ECMP

** How many fragments CF receives?


2) Packet fragmented to customer networks might not work - NAT's might
not be able to reassemble inbound fragments.


3) It's cutomer's fault. Why they are fragmented in the first
place. Internet can happily forward 1.5k, so the ower MTU is local to
customer. So the customer will notice that _many_ services won't work.

This means customer PMTU _must_ work or it must clamp MSS on TCP
level.



4) Packets _from CF_ will never be fragmented - our PMTU inbound works fine.

RFC draft.

** Statistics on our outbound packets.


5) Modern protocols are good at PMTU detection
a) you should never fragment TCP frames
b) believing in fragmentation UDP is naive



Current state of affairs
----------

On IPv4 everyone uses reasonable MTU settings.

On IPv6 Tunnels are much more prevelant, so everyone clamps to minimal 1280.




''' %>

 marek@20m21:~$ sudo tcpdump -n -r x.pcap  "ip[6] & 0x40 != 0 and tcp" |wc -l
reading from file x.pcap, link-type EN10MB (Ethernet)
957389
marek@20m21:~$ sudo tcpdump -n -r x.pcap  "ip[6] & 0x40 == 0 and tcp" |wc -l
reading from file x.pcap, link-type EN10MB (Ethernet)
24133
marek@20m21:~$ sudo tcpdump -n -r x.pcap  "icmp" |wc -l
reading from file x.pcap, link-type EN10MB (Ethernet)
423
marek@20m21:~$ sudo tcpdump -n -r x.pcap  "icmp" |grep mtu|wc -l
reading from file x.pcap, link-type EN10MB (Ethernet)
254
marek@20m21:~$ sudo tcpdump -n -r x.pcap  "udp" |wc -l
reading from file x.pcap, link-type EN10MB (Ethernet)
2528



</%block>
