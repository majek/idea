<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Is it possible to inject a million packets?
===================

In previous part we've discussed how to capture packets with kernel
bypass. This all work well and nice, but what, if due to some reason
we capture a packet that was actually heading to kernel.

In that case we want to give it back to the kernel. 

Prerequisites
---------------

rp_filter must be disabled to allow.
(arp_filter?)



tun/tap
-------

The best way to achieve what we want is to use the most suitable, high
level API. Tun/tap device is ....


Sadly, tun/tap is slow.

`sendmmsg`

multiqueue tun/tap
------


raw sockets on loopback
------

Slow again.


packet_mmap
---------

To accelerate raw sockets. But the performance is poor again.


Loopback is blocking
----

It turns out the loopback device is very special on linux. It does
little to no buffering in the virtual interface itself and tries to
handle ...

For example udp program is as fast as receiver.


RPS - request packet steering
------


dpdk http://dpdk.org/doc/guides/prog_guide/kernel_nic_interface.html


</%block>
