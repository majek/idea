<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">



Things we monitor
==================

At CloudFlare we operate a large number of edge servers. 24/7 we must be sure a single misbehaving website or a hardware fault won't affect the performance of our customers.

To achieve that we monitor thousands of parameters from every single Linux edge server. In fact, we monitor so much that any single engineer won't understand all the charts. Although every person at CloudFlare prefers different set of graphs, over years we found that some parameters are more meaningful and easier to interpret than the others.

Here is the list of metrics that I personally find the most meaningful.

General system health
----------

Load average 5 min
++++++++++++++++++++

    cat /proc/loadavg | cut -d " " -f 2

My collegues hate me for this, but I love looking at the load average on our Linux servers. This generally shows how busy the server is, and that's pretty much it. Many people think load average is meaningless, as you can have a high load while the server is working perfectly fine. Generally speaking high load doesn't necessairly indicate anything went wrong, especially when you have spinning drives. But with SSD's load seems to show pretty much how much CPU is used.

IO time CPU percentage
++++++++++++

If you have spinning drives you might want to measure how much time is wasted by your software on waiting on the disks. You may also be intrested in used disk bandwidth or performed operations per second. Since we are relying on SSD's we don't find this metrics very meaningful in our setup.


Free memory
+++++++++++

    vmstat

The virtual memory system in Linux is very complex, and there doesn't exist a single value that can tell you if you're running out of memory. In our case we are heavily relying on kernel caching of hot files, so we must be sure there is enough of "free" memory that can be used as read cache.

The highest this value, the higher probability of things going into swap, which is pretty much a death sentence for a box.

Swap
+++

    vmstat
    


slabtop
++++

    sudo slabtop -o

Since we are on Linux memory subsystem, it's worthwhile to notice


Received bytes
++++++++++++++

    cat /sys/devices/*/*/*/net/eth*/statistics/rx_bytes

There are two ways of congesting the network interface: you can push too much bytes over it or too many packets. The former is easy to detect: make sure you don't send more than say 70% of theoretical maximum bandwidh over a single interface (~84MiB over signle 1 Gig link).

Received packets
++++++++++++++++

    cat /sys/devices/*/*/*/net/eth*/statistics/rx_packets

During packet floods, we regularly see gigantic number of incoming packets to our server network interfaces. Without special tuning you shouldn't expect your server to be able to withstand more than say 1m pps on inbound (or ~250k pps per core, watch out, not all cores are equal due to NUMA). Above that you will see your processor being busy in "softirq" and likely going to hit an irq storm - ie: server using all the cpu on receiving and processing incoming packets.

Dropped packets
++++++++++

    cat /sys/devices/*/*/*/net/eth*/statistics/rx_dropped

If for some reason the kernel is not able to receive packets from the network card, it will increase this counter. Depending on your setup it might be acceptable to drop some packets. It's not for us.


netstat statistics
++++++++++++++++++

There are two command which you should monitor always:

    netstat -s
    netstat -s -6

We found that although at any point in time we are interested only in few of the "netstat -s" counters, it's very useful to be able to dig for past values when the need arrives.

Unfortunately, unless you upgrade netstat regularly, it will report an outdated list of counters. To get all the kernel counters use newer "netstat" contunter part "nstat":

    nstat -az

Here are the most useful of netstat counters:

Udp Receive Errors
+++++++++++++++++++++++++++++++++

    nstat -az|grep UdpRcvbufErrors

When our DNS server receive buffer overflows, this counter increases. Dropping DNS requests is not nice, so we monitor this metric closely.

netstat.tcpext.syns_to_listen_sockets_dropped
+++++++++++++++

    nstat -az|grep TcpExtListenDrops

syn cookies
+++++++++++

TcpExtSyncookiesSent
TcpExtSyncookiesRecv
TcpExtSyncookiesFailed


retranssegs
+++++++++++

TcpRetransSegs
TcpOutSegs

This is one of the most important metrics we look at, showing number of packets that were TCP retransmissions. The absolute value is pretty meaningless, as it's proportional to the traffic volume. Instead we monitor the derivative of "(retranssegs / tcp.outsegs) * 100", which indicates the percentage of retransmissed packets to total sent. This shows us clearly if we have a problem with network congestion. In our case more than 4% of retransmitted packets is bad, more than 8% is awful. But the baseline of course depends on location, for example in oceania where the networks are poor and lossy, we regularly see higher values and can't do much about it.


proc.net.sockstat.tcp.inuse
+++++++++++++++++++++++++++

    ss -s|egrep "^TCP:"

Number of connections is a finite resource, we monitor this to make sure a single slow origin server will consume too many connections. But since our systems are well tuned now, this metric is no longer as useful as it used to be when CloudFlare was younger.

proc.net.sockstat.tcp.orphan
+++++++++++++++++++++++++++

Orphan connections is a pretty interesting beast. In Linux it's totally possible that a connection socket will have no process as an owner - this is reported as "orphan" socket. Again, in the past we used to correlate orphan sockets counter with ceirtain L7 attacks, but we don't hit this condition very often any more.


proc.net.sockstat.tcp.tw
++++++++++++++++++++++++

Some of my friends monitor the time-wait socket count, as an indcation of high connection churn caused by L7. I presonally don't think high time-wait count is anything particularly bad.






















Softirq CPU percentage
++++++++++++++++

    extracted from /proc/stat

Number of time the kernel spent in handling soft IRQ's. In our profile that's mostly the time spent handling network interrupts. It's important to understand that the iptables (firewall) time is counted against softirq as well. High value of this metric indicates either slowness in iptables layer or just too many received packets.

Percent of used disk
++++++++++++++++

    df

Well, this one is self explanatory. General rule of thumb is to never your servers with <20% of free disk space.

Percent of used inodes
+++++++++++++++++++

    df -i

Since we sometimes use ext3 file system, the number of inodes is a limited resource. With many small files, for example used for cache, it's possible to run out of inodes, while not running out of disk free space. Make sure it doesn't happen. Also - by default 5% of inodes are reserved for root user, so make sure to alert on at most 94% of capacity.

</%block>


