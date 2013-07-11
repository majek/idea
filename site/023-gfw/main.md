<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

I was playing with the [Tor Project](https://www.torproject.org/) and
decided to understand how the Chinese block Tor servers.

[Philipp Winter wrote an amazing paper](http://www.cs.kau.se/philwint/pdf/foci2012.pdf)
on that subject. He noticed
[The Great Firewall of China](https://en.wikipedia.org/wiki/Great_Firewall_of_China)
is actively scanning services and if it detects a Tor bridge it blocks
the ip:port tuple for a few hours.

TCP/IP
---

When a port gets censored "ACK" packets are dropped by the GFW. Most
importantly `SYN+ACK` and `RST+ACK`. Here's how it looks on the server
side:

   https://gist.github.com/majek/e9761d833d789534b651

This can possibly be useful: a connection stuck in `SYN_RECV` state
for too long may indicate a GFW blockade. I wonder if there's a
counter for this in `netstat -s`.


Active probing
---

Chinese infrastructure seem to be changing right now. My results from
last week are _not_ consistent with what I see today.


Late June
----

The active scans sent by GFW in June were pretty consistent with what
Philipp described in the paper. When triggered (for example by sending
[a byte sequence looking like a Tor handshake](https://github.com/NullHypothesis/tcis/blob/master/tcis.c#L37))
one could see two scans: one from a random IP address and another from
"202.108.181.70".


Using my [SSL patch to p0f](/2012-06-17-ssl-fingerprinting-for-p0f/)
the ClientHello frames from the scans can be printed as:

* First probe, from random IP:

```
  ::text
  3.1:39,38,35,16,13,a,33,32,2f,7,5,ff:23:
```

* Second probe, always from "202.108.181.70":

```
  ::text
  3.1:39,38,35,16,13,a,33,32,2f,5::compr
```

They are identifiable and look different than legit Tor
traffic. Here's the raw payload if you can read SSL (underscores for
readability):

```
16_0301_51C9ACF6_D33152B60F193207521974EDEF6370D013D489D201C4E208720DDA29_00_00_18_00390038003500160013000A00330032002F0007000500FF0100000400230000

16_0301_51C9A4EB_8532D7F7E86A31D61BF23C2861B7D5D1F37A0027D29A8DF7284E1368_00_00_14_00390038003500160013000A00330032002F0005020100
```

With that data we can easily log these probes on the iptables
layer. For example:

```
::bash
$ iptables -A INPUT -p tcp -m string --hex-string "|00001800390038003500160013000A00330032002F0007000500FF0100000400230000|" --algo kmp -j LOG --log-prefix "china_long "

$ iptables -A INPUT -p tcp -m string --hex-string "|00001400390038003500160013000A00330032002F0005020100|" --algo kmp -j LOG --log-prefix "china_short "
```

One could do `-j REJECT` to block these probes. I did that but I've
noticed the port still got censored, I'm a bit confused about it and
I'm not sure what really happened, maybe I missed something.

Early July
----

Recent GFW probes were different. First, for _any_ outgoing connection
from China there are two probes initiated sending data that looks
randomly. The length of the payload is usually 1388 or 1448
bytes. Sometimes I was able to see 233 bytes or multiplies of these
numbers (2776).

Tor server drops connection when it reads junk. I'm not sure what
those probes are for, but they seem to be _independent_ from the SSL
probes Philipp noticed.

Sometimes when I initiated a legitimate Tor connection to a bridge I
was able to record SSL scans that looked different than before:

```
::text
3.1:39,38,88,87,35,84,16,13,a,33,32,9a,99,45,44,2f,96,41,5,ff:23:compr
```

Raw payload:

```
::text
16_03_01_005a_01_000056_0301_51d54481_37ac662aee3017988f284d7a629269e24acf50cd59b40f720fd174e6_00_0028_00390038008800870035008400160013000a00330032009a009900450044002f00960041000500ff_02_0100_0004_00230000
```

This scan comes from two random IP address, I've also seen it coming
from "202.108.181.70". It's worth noting that the hosts are able to
speak SSL and do a full SSL handshake, not only send initial data. See
this log: https://gist.github.com/majek/b59d4b4a6516240e47d2

Again, it is possible to easily log the initial SSL packet sent by
GFW on the firewall:

```
::bash
$ iptables -A INPUT -p tcp -m string --hex-string "|00002800390038008800870035008400160013000a00330032009a009900450044002f00960041000500ff020100000400230000|" --algo kmp -j LOG --log-prefix "china_new "
```

This time blocking this traffic seem to work and the service seems not
to get censored by GFW any more. At last that's what I recorded in
early July 2013.


Finally
----

It's unclear what purpose the random probes serve. We can guess they
could be used to reveal Obfsproxy or a VPN server.

[I also publicised](https://lists.torproject.org/pipermail/tor-talk/2013-July/028897.html)
this work on the tor-talk mailing list.

</%block>
</article>
