<%inherit file="basecomment.html"/>
<%block filter="filters.markdown">

-------------

I've published an article on the Cloudflare blog:

 * [https://blog.cloudflare.com/ip-fragmentation-is-broken/](https://blog.cloudflare.com/ip-fragmentation-is-broken/)

-------------


<%doc>

<%def name="img(fname, h, comment)">
<%
  v = ((h) / 28)+2
%>
<div class="image" style="height:${ v * 28 }px;"><img src="${fname}" height="${ h }px"></div>
<small>${comment}</small>

</%def>

IP Fragmentation is fundamentally broken
----------------------------------------

As opposed to the [public telephone network](https://en.wikipedia.org/wiki/Public_switched_telephone_network) which historically was [Circuit Switched](https://en.wikipedia.org/wiki/Circuit_switching), the internet is a [Packet Switched](https://en.wikipedia.org/wiki/Packet_switching) network. But just how big these packets can be?

This is an old question. The IPv4 protocol was designed with flexibility in mind and the RFC's answer it pretty clearly. The idea was to split the problem into two separate concerns:

 - What is the maximum permitted datagram size that can be safely pushed through the physical cables between two hosts?

 - What is the maximum packet size that can be handled by operating systems on both sides?

When the physical medium isn't able to transmit a big  packet, an intermediate router might decide to chop it into multiple smaller datagrams. This process is called "forward" IP fragmentation and the smaller datagrams are called IP fragments.

${ img("fragments.jpg", 400,
"Image by [Geoff Huston](https://blog.apnic.net/2016/01/28/evaluating-ipv4-and-ipv6-packet-frangmentation/), reproduced with permission") }


IPv4 defines the minimal requirements, they are pretty low by today's standards. From [RFC791](https://tools.ietf.org/html/rfc791):

    Every internet module must be able to forward a datagram of 68
    octets without further fragmentation. [...]

    Every internet destination must be able to receive a datagram
    of 576 octets either in one piece or in fragments to
    be reassembled.

All physical connections (aka: "links") used to deliver "The Internet" must be able to transmit datagrams of at least 68 bytes. For IPv6 that value has been bumped up to 1280 octets (see [RFC2460](https://tools.ietf.org/html/rfc2460#section-5)).

On the other hand, the maximum possible datagram size - called an MTU ([Maximum Transmission Unit](https://en.wikipedia.org/wiki/Maximum_transmission_unit))[^2] - is not defined by the specs.


[^2]: On a side note, there also exists a "minimum transmission unit"!

In commonly used Ethernet framing, each transmitted datagram must have at least 64 bytes on Layer 2. This translates to 22 bytes on UDP and 10 bytes on TCP layer. Multiple implementations used to leaked uninitialized memory on shorter packets!

The second value - maximum permitted reassembled packet size - is typically not problematic. Popular operating systems are able to reassemble very big packets, typically up to 65KiB.

Better to avoid fragmentation
------------------------

One may think that's it's fine to build applications that transmit very big packets and rely on routers to perform IP fragmentation.

In practice though the IP fragmentation is strongly undesired. This was first discussed by [Kent and Mogul](http://www.hpl.hp.com/techreports/Compaq-DEC/WRL-87-3.pdf) in 1987. There are a couple of big problems:

 - To successfully re-assemble a packet, all fragments must be delivered. No fragment datagram can become corrupt or get lost in-flight. There simply is no way to notify the other party about missing fragments!
 - The last fragment will almost never have the optimal size. For large transfers this means a significant part of the traffic will be composed of too short packets. This is a waste of precious router resources.
 - Before the re-assembly a host must hold partial, fragmented IP packets in memory. This exposes opens an opportunity for memory exhaustion attacks.
 - Subsequent fragments don't have the higher-layer header: TCP or UDP header is only present in the first fragment. This makes it impossible for firewalls to filter fragmented datagrams based on criteria like source or destination ports.

More elaborate description of IP fragmentation issues can be found in these articles by Geoff Huston:

 * [Evaluating IPv4 and IPv6 packet fragmentation](https://blog.apnic.net/2016/01/28/evaluating-ipv4-and-ipv6-packet-frangmentation/)
 * [Fragmenting IPv6](https://blog.apnic.net/2016/05/19/fragmenting-ipv6/)

Don't fragment - ICMP "Packet too big"
---------------------------------------

${ img("df.jpg", 220,
"Image by [Geoff Huston](https://blog.apnic.net/2016/01/28/evaluating-ipv4-and-ipv6-packet-frangmentation/), reproduced with permission") }


A solution to these problems has been included in the IPv4 protocol. A sender can set a DF (Don't Fragment) flag in IP header, asking intermediate routers to never perform fragmentation of a packet. Instead, a router with a link with smaller MTU than a packet size, should send an ICMP message "backward" and inform the sender to reduce the MTU for this connection.

DF flag is used by the TCP protocol. The network stack looks carefully for incoming "Packet too big"[^3] ICMP messages and keeps track of the "path MTU" characteristic for every connection[^4]. Being able to deliver the ICMP "packet too big" messages is critical in keeping the TCP stack working optimally.


[^3]: Strictly speaking in IPv4 the ICMP packet is named "Destination Unreachable, Fragmentation Needed and Don't Fragment was Set". But I find the IPv6 ICMP error description "Packet Too Big" much clearer.

[^4]: As a hint, TCP stack also include a maximum allowed "MSS" value in SYN packets (MSS is basically an MTU value reduced by size of IP and TCP headers). This allows the hosts to know what is the MTU on _their_ links. Notice: this doesn't say what is the MTU on the dozens internet links between the two hosts!


How the internet actually works
------------------

In perfect world the internet connected devices would cooperate and support basic Internet Protocol features like processing fragmented datagrams and passing ICMP. Unfortunately we don't live in that world. In practice IP fragments and ICMP packets very often filtered out.

This is because today's internet is much more complex than anticipated 36 years ago. In modern internet basically nobody is plugged in directly to the public internet.

${ img("thecloud2.png", 230, "")}

The customer devices connect through home routers which do [NAT](https://en.wikipedia.org/wiki/Network_address_translation) translation and usually enforce some firewall rules. Increasingly often there is more than than one NAT installation on the packet path (see: [carrier-grade NAT](https://en.wikipedia.org/wiki/Carrier-grade_NAT)). Then, the packets hit the ISP infrastructure, where the ISP's install "middle boxes" which perform all matter of weird things on the traffic. They are often used to enforce plan caps, throttle connections, perform logging, hijack DNS requests, do transparent caching or arguably "optimize" the traffic in some other magical way. The middle boxes are very often used in mobile telcos.


Similarly, the servers are distanced from the public internet by multiple layers. Major service providers often use [Anycast BGP routing](https://en.wikipedia.org/wiki/Anycast#Internet_Protocol_Version_4). That is: they handle the same IP ranges from multiple physical locations around the world. Within a datacenter it's increasingly common to use an ECMP [Equal Cost Multi Path](https://en.wikipedia.org/wiki/Equal-cost_multi-path_routing) for load balancing.


Each of these points between the client and a server can cause a Path MTU problem. Allow me to illustrate this using four scenarios.

client -> server DF+ / ICMP
---------------------------

In first scenario, let's imagine a client who wishes to upload some data to the server using TCP (which sets DF flag on the packets). If the client will fail to predict an appropriate MTU, an intermediate router will drop the big packets and send ICMP back to the client. Delivery of these packets might fail when client NAT or ISP middle box drops are misconfigured.

According to the [paper by Maikel de Boer and Jeffrey Bosma](https://www.nlnetlabs.nl/downloads/publications/pmtu-black-holes-msc-thesis.pdf) from 2012 around 5% of IPv4 and 1% of IPv6 hosts block inbound packet too big ICMP packets.

My experience confirms this. ICMP messages are indeed often dropped for perceived security advantages, but this is usually relatively easy to fix. Bigger issue is with certain Mobile ISP's with weird middle boxes. These often completely ignore ICMP and perform very aggressive connection rewriting. For example Orange Polska completely rewrites the connection state, [clamps the MSS](http://lartc.org/howto/lartc.cookbook.mtu-mss.html) to a non-negotiable 1344 bytes and ignores inbound packet-too-big ICMP messages.


client -> server DF- / fragmentation
---------------------------

If the client tries to upload some data with protocol other than TCP, the DF flag might not be set. In such case outbound packets will get fragmented at some point in the path.

We can emulate this by launching `ping` with large payload size:

```.bash
$ ping -s 2048 www.google.com
```

This will fail with payload bigger than single packet - 1472 bytes. This can't work due to ECMP. ECMP-enabled routers usually hash 5-tuple of (protocol, src IP, dst IP, src port, dst port). Fragmented packets from our `ping` will be forwarded to incorrect server.


In practice, due to ECMP, fragmented packets flying towards internet servers rarely work.

I recommend further reads:

 - Our [previous write up on ECMP](https://blog.cloudflare.com/path-mtu-discovery-in-practice/).
 - How Google attempts to solve ECMP packet fragmentation issues with [Maglev L4 Load balancer](https://research.google.com/pubs/archive/44824.pdf).

Furthermore server and router misconfiguration is a significant issue. According to [RFC7852](https://tools.ietf.org/html/rfc7872) between 30% and 55% of servers drop IPv6 packets containing Fragmentation header.

server -> client DF+ / ICMP
----------------------------

Next scenario is about client downloading some data. When the server fails to predict the correct MTU, it should get back ICMP packet too big message. Easy.

Sadly, it's not. Due to the ECMP routing, the ICMP message will get delivered, but to the wrong server. The 5-tuple hash of ICMP packet will not match the 5-tuple hash of problematic connection.  We [blogged about this in past](https://blog.cloudflare.com/path-mtu-discovery-in-practice/), and wrote a simple userspace daemon to solve it. It broadcasts inbound ICMP across to all the ECMP servers, hoping one of them still has the underlying problematic connection.

Furthermore due to Anycast routing, the ICMP might be delivered to the wrong datacenter. Internet routing is often asymmetric and some intermediate router might direct ICMP message to the wrong place.

Missing an packet-too-big ICMP message is pretty bad and will result in a connection stalling and later timing out. This situation is called a [PMTU blackhole](https://en.wikipedia.org/wiki/Path_MTU_Discovery#Problems_with_PMTUD). To aid this pessimistic case Linux implements a workaround - MTU Probing [RFC4821](http://www.ietf.org/rfc/rfc4821.txt). MTU Probing tries to identify when packets are dropped due to MTU and reduces it. This feature is controlled via a sysctl:

```.bash
$ echo 1 > /proc/sys/net/ipv4/tcp_mtu_probing
```

Unfortunately MTU probing is not without its problems. First, it tends to miscategorize congestion-related packet loss as MTU issues. Long running connections tend to end up with way to small MTU. Secondly, Linux lacks IPv6 MTU Probing implementation.

server -> client DF- / fragmentation
----------------------

Finally, there is a situation when the server sends big packets using non-TCP protocol, with DF bit clear. The packets will get fragmented and sent to the client. This situation is best illustrated with big DNS responses. Here are two DNS requests that will generate large responses, delivered as IP fragments:

```.bash
$ dig +notcp +dnssec DNSKEY org @199.19.56.1
$ dig +notcp +dnssec DNSKEY org @2001:500:f::1
```

Again, these requests might fail due to misconfigured [home router](https://en.wikipedia.org/wiki/Customer-premises_equipment), broken NAT, broken ISP installations or too restrictive firewall settings.

According to [Boer and Bosma](https://www.nlnetlabs.nl/downloads/publications/pmtu-black-holes-msc-thesis.pdf) around 6% of IPv4 and 10% of IPv6 hosts block inbound fragmented packets.


But the internet still works!
-----------------------

With all these things going wrong, how can the internet be still working?

${ img("nic.jpg", 400, 
"CC BY-SA 3.0, source: [Wikipedia](https://commons.wikimedia.org/w/index.php?curid=122201)")}

This mainly due to the success of the [Ethernet](https://en.wikipedia.org/wiki/Ethernet_frame). The great majority the links in the public internet are Ethernet (or derived from it) and support the MTU of 1500 bytes.

You can blindly assume the MTU of almost any path to be 1500[^9], and you will be surprised how well that works. The internet keeps on working mostly because we are all using MTU of 1500 and rarely need to rely on forward IP fragmentation and reverse ICMP messages.

[^9]: Let's err on the safe side. Better MTU is 1492, to accommodate for DSL and PPPoE connections.

This breaks with unusual setups though. The problem will show when your link has a non-standard MTU. For example if you have a VPN or are using IPv6 over a tunnel. In such case, to get a stable internet connectivity, you absolutely must ensure that the fragments and ICMP messages aren't blocked.

This is especially visible in IPv6 world, where many users connect through tunnels. Having a healthy passage of ICMP, in both ways, is very important, especially since fragmentation in IPv6 basically doesn't work.

Trust but verify - the online ICMP blackhole checker
-----------------------------

To help with debugging these issues we prepared an online checker. You can find two versions of the test:

 - IPv4 version: [http://icmpcheck.popcount.org](http://icmpcheck.popcount.org)
 - IPv6 version: [http://icmpcheckv6.popcount.org](http://icmpcheckv6.popcount.org)

The sites will launch two tests:

 - First will deliver ICMP messages to your computer, with the intention of reducing the Path MTU to laughingly small value.
 - Second will try to deliver fragmented packets back to you, to verify it they can pass freely.

Receiving a "pass" in both these tests should give you reasonable assurance that the internet on your side of the cable is behaving well.

It's very easy to run the tests  from command line, in case you want to run it  on the server:

```.bash
perl -e "print 'packettoolongyaithuji6reeNab4XahChaeRah1diej4' x 180" > payload.bin
# ipv4
curl -v -s http://icmpcheck.popcount.org/icmp --data @payload.bin
# ipv6
curl -v -s http://icmpcheckv6.popcount.org/icmp --data @payload.bin
```

This should reduce the path MTU to our server to 905 bytes. You should be able to verify this by looking into routing table cache:

```.bash
ip route get `dig +short icmpcheck.popcount.org`
```

It's possible to clear the routing cache on Linux:

```.bash
ip route flush cache to `dig +short icmpcheck.popcount.org`
```

Second test verifies if IPv4 and IPv6 fragments are properly delivered to the client:

```.bash
# ipv4
curl -v -s http://icmpcheck.popcount.org/frag -o /dev/null
# ipv6
curl -v -s http://icmpcheckv6.popcount.org/frag -o /dev/null
```

Summary
---------

In this blog post we described the problems with detecting Path MTU values in the internet. ICMP and fragmented packets are often blocked on both sides of the connections. Clients often have misconfigured firewalls, NAT devices or use ISP's which aggressively intercept connections. Clients also often use VPN's or IPv6 tunnels which, misconfigured, can cause issues as well.

Servers on the other hand increasingly often rely on Anycast or ECMP. Both of these things, as well as router and firewall misconfiguration often causes ICMP and fragmented packets to be dropped.

Finally, we hope the online test we prepared will be useful and give you more insight into inner workings of your networks. The test has useful `tcpdump` examples. Happy network debugging!

</%doc>
</%block>

