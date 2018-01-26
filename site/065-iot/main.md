<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


-------------

I've published an article on the CloudFlare blog:

 * [https://blog.cloudflare.com/say-cheese-a-snapshot-of-the-massive-ddos-attacks-coming-from-iot-cameras/](https://blog.cloudflare.com/say-cheese-a-snapshot-of-the-massive-ddos-attacks-coming-from-iot-cameras/)

Mentions:

 * [Threat post](https://threatpost.com/iot-botnet-uses-http-traffic-to-ddos-targets/121199/
)

-------------

<% a = """



Over last two weeks we've seen worrying new DDoS attacks hitting our
servers. To our best knowledge they come from the Mirai botnet (or its
off-shoots) which was responsible for the [large attacks against Brian
Krebs](https://krebsonsecurity.com/2016/09/krebsonsecurity-hit-with-record-ddos/).

Let's take a look at some actual numbers we observed.

Requests per second
-------------


There are many ways to measure the size of an attack. One of the
dimensions is sheer number of HTTP requests per seconds. Recently we
were hit by a couple of unusually large attacks, crossing 1 million HTTP
requests per second. Here is one of them:

<div class="image" style="height:364px"><img style="height:336px;" src="10e8560bcc246812-pps.png"></div>

It was running for about 15 minutes. This is a characteristic
shared by this kind of very high RPS attacks.

In the example above the volume in peak was 1.75M RPS. The request
attack was composed of short HTTP requests, without anything unusual
in HTTP headers. It had a fixed `Cookie` header. The HTTP requests
were fairly small, at around 121 bytes each. We counted 52467 unique
addresses taking part in this attack.

Due to the anycast nature of Cloudflare network, the malicious traffic
was spread across multiple points of presence. Here are the top
affected datacenters:

<div class="image" style="height:364px"><img style="height:336px;" src="10e8560bcc246812-colos.png"></div>

This attack went mostly to our Hong Kong and Prague datacenters. This
is another common characteristic. Most of the recent attacks looked
similar hitting Hong Kong and Prague the most.

Since the attack looks concentrated, maybe only a small number of AS
numbers take part? Unfortunately no, the IP addresses participating in
the flood are evenly distributed. Out of 10 thousand random requests
we analyzed (a tiny fraction of all requests), we've seen source IP
addresses from over 300 AS numbers. These are the biggest offenders:

```
   48 AS24086
  101 AS4134
  128 AS7552
  329 AS45899
 2366 AS15895
```

These attacks are really a new trend, so it's not fair to blame the AS
operators for not cleaning up devices participating in them. Having
said that, the Ukrainian "AS15895 Kyivstar PJSC" and Vietnamise
"AS45899 VNPT Corp" seem to stand out. We'll get back to this in a
moment.

Bandwidth
--------------


While requests per second is a very common metric to measure the
attacks, it's not the only one. We can also measure bandwidth used
in the attack.

By this count the mentioned event was pretty small, at roughly 2gbps
in peak. We've noticed another attack that as a record breaker in
terms of bandwidth. First, let's see the requests per second graph:

<div class="image" style="height:364px"><img style="height:336px;" src="b482cbecc09cb9ba-pps.png"></div>

This attack generaetd 220k requests per second in peak. It's still
significant, but it's not really record breaking. Hovewer, it generated
a significant bandwidth on inbound:

<div class="image" style="height:364px"><img style="height:336px;" src="b482cbecc09cb9ba-bps.png"></div>

This attack topped at 360 gbps per second of inbound traffic. It's
pretty unusual for an HTTP attack to generate a substantial network
traffic. This attack was special, and was composed of HTTP requests
like this:

```
GET /en HTTP/1.1
User-Agent: <some string>
Cookie: <some cookie>
Host: target.com
Connection: close
Content-Length: 800000

a[]=&b[]=&a[]=&b[]=&a[]=&b[]=&a[]=&b[]=&a[]=&b[]=&a[]=&b[]=...
```

It's the long payload sent after the request headers that allowed the attackers
to generate substantial traffic. In following days we've seen more
events like this, and they came with varying parameters. For example
sometimes they came as GET requests, sometimes as POST.

Additionally, this particular attack was fairly long at roughly
1h, with 128833 unique IP addresses.

Interestingly the datacenter distribution was different, with most of
the attack concentratred on Frankfurt:

<div class="image" style="height:364px"><img style="height:336px;" src="b482cbecc09cb9ba-colo.png"></div>

As the attack was composed of a very large number of bots, we can
expect the AS distribution to be fairly even. Indeed, in the 10k
request sample we recorded a whopping of 737 unique AS numbers. Here
are the top offenders:

```
  286 AS45899
  314 AS7552
  316 AS3462
  323 AS18403
 1510 AS15895
```

Similarly, the Ukrainian AS15895 and another Vietnamese network
"AS18403 The Corporation for Financing & Promoting Technology" are the
top two hitters.

More on the sources
-----------------

We wondered why is AS15895 so special. First, we investigated our
traffic charts. Here is the inbound traffic we received from them over
last 30 days:

<div class="image" style="height:130px"><img style="height:112px;" src="AS15895.png"></div>

The first significant attack was clearly seen as a spike on September 29th
and reached 30gbps. Very similar chart is visible for AS45899:

<div class="image" style="height:130px"><img style="height:112px;" src="AS45899.png"></div>

We can see some smaller attacks attempted around 26th September, and a
couple of days later the attackers turned the throttle on hitting 7.5gbps almost non
stop. Other AS numbers we investigated reveal a similar story.

Devices
-------

While it's not possible for us to investigate all the attacking
devices, it is fair to say that these attacks came from
internet-of-things category of devices.

There are multiple hints confirming this theory.

First, all of the attacking devices have port 23 (telnet) open
(closing connection immediately) or closed. Never filtered. This is a
strong hint that the malware disabled the telnet port just after it
installed itself.

Most of the hosts from the Vietnamese networks look like connected
CCTV cameras. Multiple have open port 80 with presenting
"NETSurveillance WEB" page.

<div class="image" style="height:130px"><img style="height:112px;" src="cam02.png"></div>
<div class="image" style="height:130px"><img style="height:112px;" src="cam03.png"></div>
<div class="image" style="height:130px"><img style="height:112px;" src="cam04.png"></div>

This style of botnets composed of CCTV cameras were previously
reported by
[sucuri](https://blog.sucuri.net/2016/06/large-cctv-botnet-leveraged-ddos-attacks.html)
and
[Incapsula](https://www.incapsula.com/blog/cctv-ddos-botnet-back-yard.html).

The Ukrainian devices are a bit different though. Most have port 80
closed, making it harder to identify.

We had noticed one deivce with port 443 open serving a valid TLS cert
issued by Western Digital, handling domain `device-xxxx.wd2go.com`
suggesting it was a hard drive.


Summary
-------

We can confirm the findings of others. A large Internet-of-Things botnet is in the
wild. It's composed mostly out of CCTV cameras in Asia region, and
some other kind of devices in Ukraine, perhaps hard drives or modems. In one case 
we've seen over 120 thousand devices participating in the attack.

We plan to continue our investigation and collaborate with external
researchers to find a permanent solution to this rising threat.

In the mean time we're looking forward to fridges joininig the CCTV revolt.

""" %>

</%block>
