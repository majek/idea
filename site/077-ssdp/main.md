<%inherit file="basecomment.html"/>
<%block filter="filters.markdown">

-------------

I've published an article on the Cloudflare blog:

 * [https://blog.cloudflare.com/ssdp-100gbps/](https://blog.cloudflare.com/ssdp-100gbps/)

-------------

<%doc>

SSDP attack crossing 100Gbps
------------------
<

Last month we [shared statistics of popular reflection](https://blog.cloudflare.com/reflections-on-reflections/) attacks. In the article we showed this histogram of SSDP attack sizes:

```
$ cat 1900-Gbps | ~/bin/mmhistogram -t "Bandwidth in Gbps"
Bandwidth in Gbps min:0.41 avg:11.95 max:78.03 dev:13.32 count:1692
Bandwidth in Gbps:
 value |-------------------------------------------------- count
     0 |                   ******************************* 331
     1 |                             ********************* 232
     2 |                            ********************** 235
     4 |                                   *************** 165
     8 |                                            ****** 65
    16 |************************************************** 533
    32 |                                       *********** 118
    64 |                                                 * 13
```

Back then the average SSDP attack size was ~12Gbps and largest SSDP reflection we recorded was:

 - 30Mpps
 - 80Gbps
 - using 940k reflector IP's

This changed a couple of days ago when we noticed an unusually large SSDP amplification. It's worth deeper investigation since it crossed a symbolic threshold of 100Gbps.

The packets per second chart during the attack looked like this:

![](/content/images/2017/06/7a9f87325c0e3921-qps-1.png)

The bandwidth usage:

![](/content/images/2017/06/7a9f87325c0e3921-bps.png)

This packet flood lasted 38 minutes. According to our sampled netflow data it utilized 930k reflector servers. Here is a histogram of how many samples per IP we saw:

```
$ cat ips-nf-sorted.txt |uniq -c|sed -s 's#^ \+##g'|cut -d " " -f 1| ~/bin/mmhistogram -t "Samples per reflector IP"
Samples per reflector IP min:1.00 avg:6.82 med=6.00 max:55.00 dev:3.49 count:929603
Samples per reflector IP:
 value |-------------------------------------------------- count
     0 |                                                ** 27361
     1 |                                              **** 42607
     2 |                                 ***************** 165549
     4 |************************************************** 460332
     8 |                           *********************** 216226
    16 |                                                 * 17526
    32 |                                                   2
```

On average we saw 7 sampled packets for each attacking IP. With netflow sampling rate of 1/16k packets, that means during 38 minutes of the attack each reflector hammered our infrastructure with 112k packets on average.

The reflector servers are localized across the globe, with larger presence in Argentine, Russia and China. Unique IP's per country:
```
$ cat ips-nf-ct.txt |uniq|cut -f 2|sort|uniq -c|sort -n | tail
   ...
   9103 IT
  10334 UA
  10824 KR
  14234 BR
  18962 CO
  19558 MY
  32850 CA
  41353 TW
  51222 US
  74825 AR
 135783 RU
 439126 CN
```

The reflector IP distribution across ASN's is usual. It pretty much follows the world largest ISP's:

```
$ cat ips-nf-asn.txt |uniq|cut -f 2|sort|uniq -c|sort -n|tail
   ...
   6377 12768  # RU JSC "ER-Telecom Holding"
   6604 3269   # IT Telecom Italia
   6840 8402   # RU OJSC "Vimpelcom"
   7070 10796  # US Time Warner Cable Internet
  11328 28573  # BR Claro SA
  18809 3816   # CO Colombia Telecomunicaciones
  19464 4788   # MY TM Net
  19518 6327   # CA Shaw Communications Inc.
  23823 3462   # TW Chunghwa Telecom
  72301 22927  # AR Telefonica de Argentina
  84781 4134   # CN China Telecom
 318405 4837   # CN China Unicom
```

What's SSDP anyway
------------------

The attack was composed of mostly packets with protocol UDP and source port 1900. This port is used by [SSDP](https://en.wikipedia.org/wiki/Simple_Service_Discovery_Protocol) which a part of the UPnP suite. UPnP is one of the [zero-configuration networking](https://en.wikipedia.org/wiki/Zero-configuration_networking#UPnP) protocols. Most likely your home appliances support it, allowing them to be easily discovered by your computer or phone. When a new device (like your laptop) joins the network, it can query local network for specific devices, like internet gateways, audio systems or printers.

[UPnP](http://www.upnp-hacks.org/upnp.html) is poorly standardized, but here's a snippet from [the spec](https://web.archive.org/web/20151107123618/http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v2.0.pdf) about the M-SEARCH frame - the main method for discovery:

> When a control point is added to the network, the UPnP discovery protocol allows that control point to search for devices of interest on the network. It does this by multicasting on the reserved address and port (239.255.255.250:1900) a search message with a pattern, or target, equal to a type or identifier for a device or service.

Responses to M-SEARCH frame:

> To be found by a network search, a device shall send a unicast UDP response to the source IP address and port that sent the request to the multicast address. Devices respond if the ST header field of the M-SEARCH request is “ssdp:all”, “upnp:rootdevice”, “uuid:” followed by a UUID that exactly matches the one advertised by the device, or if the M-SEARCH request matches a device type or service type supported by the device.

This works in practice. For example, my Chrome browser regularly asks for a Smart TV I guess:

```
$ sudo tcpdump -ni eth0 udp and port 1900 -A
IP 192.168.1.124.53044 > 239.255.255.250.1900: UDP, length 175
M-SEARCH * HTTP/1.1
HOST: 239.255.255.250:1900
MAN: "ssdp:discover"
MX: 1
ST: urn:dial-multiscreen-org:service:dial:1
USER-AGENT: Google Chrome/58.0.3029.110 Windows
```

This frame is delivered to mutlicast ethernet and IP addresses. Other devices supporting this specific "ST" (search-target) multiscreen type are supposed to answer.

Apart from specific device types queries, there are two "generic" ST query types:

 - `upnp:rootdevice`: search for root devices
 - `ssdp:all`: search for all UPnP devices and services

To emulate these queries you can run this python script (based on [this work](https://www.electricmonk.nl/log/2016/07/05/exploring-upnp-with-python/)):

```
#!/usr/bin/env python2
import socket
import sys

dst = "239.255.255.250"
if len(sys.argv) > 1:
    dst = sys.argv[1]
st = "upnp:rootdevice"
if len(sys.argv) > 2:
    st = sys.argv[2]

msg = [
    'M-SEARCH * HTTP/1.1',
    'Host:239.255.255.250:1900',
    'ST:%s' % (st,),
    'Man:"ssdp:discover"',
    'MX:1',
    '']

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.settimeout(10)
s.sendto('\r\n'.join(msg), (dst, 1900) )

while True:
    try:
        data, addr = s.recvfrom(32*1024)
    except socket.timeout:
        break
    print "[+] %s\n%s" % (addr, data)
```

On my home network two devices show up:

```
$ python ssdp-query.py
[+] ('192.168.1.71', 1026)
HTTP/1.1 200 OK
CACHE-CONTROL: max-age = 60
EXT:
LOCATION: http://192.168.1.71:5200/Printer.xml
SERVER: Network Printer Server UPnP/1.0 OS 1.29.00.44 06-17-2009
ST: upnp:rootdevice
USN: uuid:Samsung-Printer-1_0-mrgutenberg::upnp:rootdevice

[+] ('192.168.1.70', 36319)
HTTP/1.1 200 OK
Location: http://192.168.1.70:49154/MediaRenderer/desc.xml
Cache-Control: max-age=1800
Content-Length: 0
Server: Linux/3.2 UPnP/1.0 Network_Module/1.0 (RX-S601D)
EXT:
ST: upnp:rootdevice
USN: uuid:9ab0c000-f668-11de-9976-000adedd7411::upnp:rootdevice
```


The firewall
----------

Now that we understand the basics of SSDP, understanding the reflection attack should be easy. You see, there are in fact two ways of delivering the M-SEARCH frame:

 - what we presented, over multicast address
 - directly to host UPnP / SSDP enabled host over unicast

The latter method works. We can specifically target my printer IP address:

```
$ python ssdp-query.py 192.168.1.71
[+] ('192.168.1.71', 1026)
HTTP/1.1 200 OK
CACHE-CONTROL: max-age = 60
EXT:
LOCATION: http://192.168.1.71:5200/Printer.xml
SERVER: Network Printer Server UPnP/1.0 OS 1.29.00.44 06-17-2009
ST: upnp:rootdevice
USN: uuid:Samsung-Printer-1_0-mrgutenberg::upnp:rootdevice
```

Now the problem is easily seen: the SSDP protocol will not verify if the querying party is in the same network as the device. It will happily respond to M-SEARCH delivered over public internet. A tiny misconfiguration in a firewall - port 1900 UDP open to the world - and a perfect target for UDP amplification will be open.

Given a misconfigured target our script will happily work over the internet:

```
$ python ssdp-query.py 100.42.x.x
[+] ('100.42.x.x', 1900)
HTTP/1.1 200 OK
CACHE-CONTROL: max-age=120
ST: upnp:rootdevice
USN: uuid:3e55ade9-c344-4baa-841b-826bda77dcb2::upnp:rootdevice
EXT:
SERVER: TBS/R2 UPnP/1.0 MiniUPnPd/1.2
LOCATION: http://192.168.2.1:40464/rootDesc.xml
```

The amplification
-----------------

The real damage is done by the `ssdp:all` ST type though. These responses are _much_ larger:

```
$ python ssdp-query.py 100.42.x.x ssdp:all
[+] ('100.42.x.x', 1900)
HTTP/1.1 200 OK
CACHE-CONTROL: max-age=120
ST: upnp:rootdevice
USN: uuid:3e55ade9-c344-4baa-841b-826bda77dcb2::upnp:rootdevice
EXT:
SERVER: TBS/R2 UPnP/1.0 MiniUPnPd/1.2
LOCATION: http://192.168.2.1:40464/rootDesc.xml


[+] ('100.42.x.x', 1900)
HTTP/1.1 200 OK
CACHE-CONTROL: max-age=120
ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1
USN: uuid:3e55ade9-c344-4baa-841b-826bda77dcb2::urn:schemas-upnp-org:device:InternetGatewayDevice:1
EXT:
SERVER: TBS/R2 UPnP/1.0 MiniUPnPd/1.2
LOCATION: http://192.168.2.1:40464/rootDesc.xml

... 6 more response packets....
```

In this particular case a single SSDP M-SEARCH packet triggered 8 response packets. Tcpdump view:

```
$ sudo tcpdump -ni en7 host 100.42.x.x -ttttt
 00:00:00.000000 IP 192.168.1.200.61794 > 100.42.x.x.1900: UDP, length 88
 00:00:00.197481 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 227
 00:00:00.199634 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 299
 00:00:00.202938 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 295
 00:00:00.208425 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 275
 00:00:00.209496 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 307
 00:00:00.212795 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 289
 00:00:00.215522 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 291
 00:00:00.219190 IP 100.42.x.x.1900 > 192.168.1.200.61794: UDP, length 291
```

That target exposes 8x packet count amplification and 26x bandwidth amplification. Sadly, this is usual for SSDP.

IP Spoofing
-----------

The final step for the attack is to fool the vulnerable servers to flood the target IP - not the attacker. For that the attacker needs to [spoof source IP addresses](https://en.wikipedia.org/wiki/IP_address_spoofing).

We probed reflector the IP's used in the shown 100Gbps+ attack.  We found that out of the 920k reflector IP's used in attack only 350k (38%) still respond to SSDP probes. 

Out of the reflectors that responded, each sent on average 7 packets:

```
$ cat results-first-run.txt |cut -f 1|sort|uniq -c|sed -s 's#^ \+##g'|cut -d " " -f 1| ~/mmhistogram -t "Response packets per IP" -p
Response packets per IP min:1.00 avg:6.99 med=8.00 max:186.00 dev:4.44 count:350337
Response packets per IP:
 value |-------------------------------------------------- count
     0 |                    ****************************** 23.29%
     1 |                                              ****  3.30%
     2 |                                                **  2.29%
     4 |************************************************** 38.73%
     8 |            ************************************** 29.51%
    16 |                                               ***  2.88%
    32 |                                                    0.01%
    64 |                                                    0.00%
   128 |                                                    0.00%
```

Responses packets had 321 bytes (+/- 29 bytes) on average. Our request packets had 110 bytes.

According to our measurements with the `ssdp:all` M-SEARCH attacker would be able to achieve:

  - **7x** packet number amplification
  - **20x** bandwidth amplification

We can estimate the 43Mpps / 112Gbps attack was generated with roughly:

 - 6.1 Mpps of spoofing capacity
 - 5.6 Gbps of spoofed bandwidth

In other words: a single well connected 10Gbps server being able to perform IP spoofing can deliver pretty significant SSDP attack.

More on the SSDP servers
-----------------------

Since we probed the vulnerable SSDP servers, here are the most common `Server:` header values we received:

```
    ...
    347 Ubuntu/10.10 UPnP/1.0 miniupnpd/1.0
    352 Tenda UPnP/1.0 miniupnpd/1.0
    514 Fedora/8 UPnP/1.0 miniupnpd/1.0
    560 MIPS LINUX/2.4 UPnP/1.0 miniupnpd/1.0
    658 WNR2000v5 UPnP/1.0 miniupnpd/1.0
    770 Unspecified, UPnP/1.0, Unspecified
    793 Upnp/1.0 UPnP/1.0 IGD/1.00
    827 Allegro-Software-RomUpnp/4.07 UPnP/1.0 IGD/1.00
   1309 Linux/2.6.21.5, UPnP/1.0, Portable SDK for UPnP devices/1.6.6
   1365 1
   2052 miniupnpd/1.5 UPnP/1.0
   2788  1.0
   3326 Fedora/10 UPnP/1.0 MiniUPnPd/1.4
   4617 Linux/2.6.30.9, UPnP/1.0, Portable SDK for UPnP devices/1.6.6
   4661 AirTies/ASP 1.0 UPnP/1.0 miniupnpd/1.0
   5461 Ubuntu/lucid UPnP/1.0 MiniUPnPd/1.4
   6010 LINUX-2.6 UPnP/1.0 MiniUPnPd/1.5
   7193 Linux UPnP/1.0 Huawei-ATP-IGD
   7506 Net-OS 5.xx UPnP/1.0
   7962 TBS/R2 UPnP/1.0 MiniUPnPd/1.4
   9760 miniupnpd/1.0 UPnP/1.0
  11532 ASUSTeK UPnP/1.0 MiniUPnPd/1.4
  12857 Ubuntu/7.10 UPnP/1.0 miniupnpd/1.0
  66511 TBS/R2 UPnP/1.0 MiniUPnPd/1.2
  76340 System/1.0 UPnP/1.0 IGD/1.0
 103178 Linux/2.4.22-1.2115.nptl UPnP/1.0 miniupnpd/1.0
```

The most common `ST:` header values we saw:

```
   6063 urn:schemas-microsoft-com:service:OSInfo:1
   7737 uuid:WAN{84807575-251b-4c02-954b-e8e2ba7216a9}000000000000
   9822 urn:schemas-upnp-org:service:WANEthernetLinkConfig:1
  35511 uuid:IGD{8c80f73f-4ba0-45fa-835d-042505d052be}000000000000
  90818 urn:schemas-wifialliance-org:service:WFAWLANConfig:
  91108 urn:schemas-wifialliance-org:device:WFADevice:
  93987 urn:schemas-upnp-org:service:Layer3Forwarding:
  96259 urn:schemas-upnp-org:service:WANIPConnection:
  97246 urn:schemas-upnp-org:service:WANPPPConnection:
  98112 urn:schemas-upnp-org:device:WANConnectionDevice:
  99017 urn:schemas-upnp-org:service:WANCommonInterfaceConfig:
 100180 urn:schemas-upnp-org:device:WANDevice:
 100961 urn:schemas-upnp-org:device:InternetGatewayDevice:
 113453 urn:schemas-upnp-org:service:WANPPPConnection:1
 145602 urn:schemas-upnp-org:service:Layer3Forwarding:1
 146970 urn:schemas-upnp-org:service:WANIPConnection:1
 147461 urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1
 148593 urn:schemas-upnp-org:device:WANConnectionDevice:1
 151642 urn:schemas-upnp-org:device:WANDevice:1
 158442 urn:schemas-upnp-org:device:InternetGatewayDevice:1
 298497 upnp:rootdevice
```

The vulnerable IP's are seem to be mostly unprotected home routers.


Open SSDP is a vulnerability
----------------------------

It's not a novelty that allowing UDP port 1900 traffic from the internet to your home printer or such is not a good idea. This problem is known since at least January 2013:

 - ["Security Flaws in Universal Plug and Play: Unplug, Don't Play"](https://community.rapid7.com/community/infosec/blog/2013/01/29/security-flaws-in-universal-plug-and-play-unplug-dont-play)

Authors of SSDP clearly didn't give any thought to UDP amplification potential. There are a number of obvious recommendations about future use of SSDP protocol:

 - The authors of SSDP should answer if there is any real
   world use of unicast `M-SEARCH` queries. From what I understand
   M-SEARCH only makes practical sense as a multicast query in local area network.
 - Unicast M-SEARCH support should be either deprecated or at least
   rate limited, in similar way to [DNS Response Rate Limit techniques](http://www.redbarn.org/dns/ratelimits).
 - M-SEARCH responses should be only delivered to local network. Responses
   routed over the network make little sense and open described vulnerability.

In the mean time we recommend:

 - Network administrators should ensure inbound UDP port 1900 is blocked on firewall.
 - Internet service providers should **never allow IP spoofing** to be performed on their network. IP spoofing is the true root cause of the issue.
 - Internet service providers should allow their customers to use **BGP
   flowspec** to rate limit inbound UDP source port 1900 traffic, to relieve congestion during large SSDP attacks.
 - Internet providers should internally collect **netflow** protocol samples. The netflow is needed to identify the true source of the attack. With netflow it's trivial to answer questions like: "Which of my customers sent 6.4Mpps of traffic to port 1900?".
 - Developers should not roll out their own UDP protocols without careful consideration of UDP amplification problems.

Sadly, the most unprotected routers we saw in described attack were from China, Russia and Argentina, places not historically known for the most agile internet service providers.

Summary
-------

Cloudflare customers are fully protected from SSDP and other L3 amplification attacks. These attacks are nicely deflected by [Cloudflare anycast](https://blog.cloudflare.com/how-cloudflares-architecture-allows-us-to-scale-to-stop-the-largest-attacks/) infrastructure and require no special action. Unfortunately the raising SSDP attack sizes might be a tough problem for other internet citizens. We should encourage our ISP's to stop IP spoofing within their network, support BGP flowspec and configure in netflow collection.


_This article is a joint work of Marek Majkowski and Ben Cartwright-Cox._


Dealing with large attacks sounds like fun?
[Join our world famous DDoS team](https://boards.greenhouse.io/cloudflare/jobs/589572)
in London, Austin, San Francisco and our elite office in Warsaw, Poland.


</%doc>

</%block>


