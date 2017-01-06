<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Operating a TCP server in under constant SYN-floods
===



Recently [Syn floods](https://en.wikipedia.org/wiki/SYN_flood) have
been on the raise. About 20 months ago a security company Radware
blogged about a new attack they identified and called ["Tsunami SYN flood"](https://blog.radware.com/security/2014/10/tsunami-syn-flood-attack/).

While we have a couple of super-secret mitigation techniques to
counter syn-floods this blog post is not about them. Instead it's
about explaining Linux's usual syn-flood defenses.



There's plenty of misconceptions about tuning Linux for operating in
the real world internet deployments. Some of it is understandable,
each server have different setup. But most of it is just lack of
understanding. People just copy and paste magical sysctl's with no
understanding. A typical cargo cult.

In past we discussed the pros and cons of tweaking various Linux sysctl's:
 - [tcp_rmem settings and net.core.netdev_budget](https://blog.cloudflare.com/the-story-of-one-latency-spike/)
 - [wmem](https://blog.cloudflare.com/the-curious-case-of-slow-downloads/)
 - [tcp_fin_timeout](https://blog.cloudflare.com/this-is-strictly-a-violation-of-the-tcp-specification/)
 - [tcp_mtu_probing](https://blog.cloudflare.com/path-mtu-discovery-in-practice/)
 - [rps_sock_flow_entries smp_affinity_list](https://blog.cloudflare.com/how-to-achieve-low-latency/)
 - [LHTABLE size](https://blog.cloudflare.com/revenge-listening-sockets/)
 - [tcp_no_metrics_save and tcp_slow_start_after_idle](https://blog.cloudflare.com/optimizing-the-linux-stack-for-mobile-web-per/)

https://gagor.pl/2016/02/prepare-for-dos-like-cloudflare-do/

This time let me dive into another subject - the Linux handling of SYN
packets. This is a very important, but pretty complex part of the
network stack. In Linux this code constantly evolves, which means
plenty of docs are outdated.

Ok, let's start with a server code:

listen()


Inside the kernel this creates TWO queues:

 - SYN queue
 - ACCEPT queue

(these queues have differnet names in literature, with listen queue,
backlog queeu and xx as examples. I find these names confusing. Let's use SYN and ACCEPT, as they are self-explanatory).

sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=65535


The usual flow
---------
The size of SYN queue is pretty much "syn's-in-flight" size.


Accept queue overflow
----------------

`tcp_abort_on_overflow`

Backlog queue overflow
--------------

syn cook

backlog decay
 sysctl -w net.ipv4.tcp_synack_retries=1


Engage syn cookies
-------------

tcp_timestamps


Corner case
-----------

We've noticed a very unusual case. During some syn floods the syn cookies were not engaged.


This happened when we were attacked by a lone attacker, using one IP address. Weird, isn' it?






</%block>
