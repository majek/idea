<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

[In June](/2012-06-17-ssl-fingerprinting-for-p0f/) I started playing
with fingerprinting SSL client requests. For example, an
SSL fingerprint of my browser is:

    ::bash
    3.2:c00a,c014,[...],c00d,c003,feff,a:?0,ff01,a,b,23,3374:ver

[Read the docs of fingerprint format](/2012-06-17-ssl-fingerprinting-for-p0f),
or
[even more detailed description](https://github.com/majek/p0f/blob/36a41b5afc37d0ebf0d99d3bb75362e1c39a3602/docs/README#L716-772).

[You can also check your fingerprint here](https://p0f.popcnt.org/).

I wanted to prepare a database of popular fingerprints, so I started
recording traffic on port 443.

I quickly noticed that apart from normal traffic there are some hosts
sending weird SSL requests that make no practical sense and look like
scanning. It's not really surprising, for example it is
well known that [EFF SSL Observatory](https://www.eff.org/observatory)
did an active SSL scan.


SSL Labs
-------

The first suspect is ip [`173.203.79.216`](./173.203.79.216.txt) belonging to
[SSL Labs](https://www.ssllabs.com/). This host spammed my server with
204 unique SSL probes.


Some highlights:

    ::bash
    # Probing SSL 2.0
    2.0:700c0,30080,10080,60040,40080,20080::v2,chlen
    3.1:15,ff::v2
    # Ciphers enumerating
    3.1:9:ff01:
    3.1:15:ff01:
    # Some probes don't have random data where necessary
    3.0:0::rand
    3.2:1f::rand
    3.3:c002:b,d:rand
    # 0xff is not really a valid cipher
    3.3:ff:b,d:rand
    # Ordering of ciphers
    3.3:4,5,9,a,15,16,2f,33,35,39:b,d:rand
    3.3:5,9,a,15,16,2f,33,35,39,4:b,d:rand
    # Repeated cipher 0x80
    3.0:80,80,40,c0,9,a,15,16,2f,33,35,39,80,80,4,5::rand


([Here's the full list of signatures from this host](./173.203.79.216.txt).)

Netco
-----

Requests from SSL Labs were pretty weird, but at least thet serve a
legitimate purpose - [www.ssllabs.com](https://www.ssllabs.com/)
provides a very useful service. But the clear winner in number of
probes is [`91.228.1.56`](./91.228.1.56.txt) belonging to "Netco
Solutions Ltd" form Norfolk which generated a record number of 862
unique signatures.

As opposed to SSL Labs I have no clue what their scans were for.



Highlights:

    ::bash
    # SSL 2.0 probe
    2.0:700c0,50080,30080,10080,80080,60040,40080,20080::v2,chlen
    # Support for compression
    3.3:2a,31,66,b,c,c038,3c,...,2b,25,29,1f,2,c001,23::
    3.3:2a,31,66,b,c,c038,3c,...,2b,25,29,1f,2,c001,23::compr
    # Random timestamp field
    3.0:16,13,a,66,5,4,65,64,63,62,61,60,15,12,9,14,11,8,6,3::rtime


Johns Hopkins University
-----

I recorded two nearly identical scans: one from Johns Hopkins University
[`128.220.247.212`](./128.220.247.212.txt) and another from a random Amazon
US-EAST host [`23.22.93.48`](./23.22.93.48.txt). They were composed of
91 signatures, mostly just enumerating ciphers.

I don't think there's anything special about those scans, maybe the
fact that they seem to be really detailed about SSL v2:

    ::bash
    2.0:10080::v2,chlen
    2.0:20080::v2,chlen
    2.0:30080::v2,chlen
    2.0:40080::v2,chlen
    2.0:60040::v2,chlen
    2.0:700c0::v2,chlen
    2.0:700c0,30080,10080,60040,40080,20080::v2,chlen

(Prof. [Matthew Green](http://blog.cryptographyengineering.com/) from
Johns Hopkins University might know more about the nature of the
scan.)

Another interesting scan came from Amazon UE-EAST
[`23.20.240.181`](./23.20.240.181.txt). This looks somewhat similar to
scans from Johns Hopkins University, but it's hard to judge if they
are related. Also, this scan was much larger with 344 unique probes.

Opera
-----

And finally, the most interesting scan came from IP address belonging
to Opera.com [`213.236.208.19`](./213.236.208.19.txt), consisting of
41 probes.

Except from the usual SSL v2 scanning it had some quite weird probes.

    ::bash
    # SSL v2 testing, with non-random data in challenge field
    2.0:ff,10080,30080,700c0,60040,20080,40080::v2,rand
    3.1:ff,35,2f,a,4,5,10080,30080,700c0,60040,20080,40080::v2,rand
    # Two probes: a valid and a random timestamp
    3.2:ff,35,2f,a,4,5::ver
    3.2:ff,35,2f,a,4,5::ver,rtime
    # Checking ciphers, in order?
    3.0:1,2,b,e,11,7,c,f,12,d,10,36,37,3e,3f,68,69,13,38,[...]
    [...],bf,c0,c1,c2,c3,c4,c5,80,81,82,83:?0,ff01,5,23:rtime
    # Is that a probe for TLS 1.3?
    3.4:3d,3c,35,2f,a,4,5:?0,ff01,5,23,d:ver,rtime
    3.4:ff,3d,3c,35,2f,a,4,5::ver,rtime
    # What exactly is protocol 4.1?
    4.1:3d,3c,35,2f,a,4,5:?0,ff01,5,23,d:ver,rtime
    4.1:ff,3d,3c,35,2f,a,4,5::ver,rtime

Checking the support of non-existent versions of SSL is definitely my
favourite scan. 

Actually, it's does serve a purpose - TLS spec vaguely defines how to
do TLS version negotiation but I don't think it's widely
supported. Most browsers just try a best TLS version first (TLS 1.2
nowadays) and
[fall back to older TLS 1.1 if server returns an error](http://www.imperialviolet.org/2012/06/08/tlsversions.html).

Requesting an impossible version of TLS may be used to detect how
servers behave in the fallback situation. Still, testing protocol
4.1 is quite suspicious.

It's also worth noting - the Opera browser has a custom SSL stack,
different from any other browser. Maybe those scans check if Opera
will actually work with real SSL servers.



Nmap
----

Although I didn't receive an SSL scan generated by Nmap, I thought it
would be useful to mention it.

For some time Nmap includes a scripting engine
and one of the scripts is capable of enumerating SSL ciphers
[`ssl-enum-ciphers'](https://github.com/nmap/nmap/blob/f97c8db5e8571f0cf91328503f0ea4103d1c0420/scripts/ssl-enum-ciphers.nse). To
run it:

    nmap -p443 --script scripts/ssl-enum-ciphers.nse host

For my server it generates this report:

```
PORT    STATE SERVICE
443/tcp open  https
| ssl-enum-ciphers: 
|   SSLv3: 
|     ciphers: 
|       TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_AES_128_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_AES_256_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_DES_CBC_SHA - weak
|       TLS_RSA_WITH_3DES_EDE_CBC_SHA - strong
|       TLS_RSA_WITH_AES_128_CBC_SHA - strong
|       TLS_RSA_WITH_AES_256_CBC_SHA - strong
|       TLS_RSA_WITH_DES_CBC_SHA - weak
|       TLS_RSA_WITH_RC4_128_MD5 - strong
|       TLS_RSA_WITH_RC4_128_SHA - strong
|     compressors: 
|       NULL
|   TLSv1.0: 
|     ciphers: 
|       TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_AES_128_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_AES_256_CBC_SHA - strong
|       TLS_DHE_RSA_WITH_DES_CBC_SHA - weak
|       TLS_RSA_WITH_3DES_EDE_CBC_SHA - strong
|       TLS_RSA_WITH_AES_128_CBC_SHA - strong
|       TLS_RSA_WITH_AES_256_CBC_SHA - strong
|       TLS_RSA_WITH_DES_CBC_SHA - weak
|       TLS_RSA_WITH_RC4_128_MD5 - strong
|       TLS_RSA_WITH_RC4_128_SHA - strong
|     compressors: 
|       NULL
```

On the server it generates 71 signatures (for my particular setup),
looking like [this](./nmap.txt).


Final thoughts
-------

Things like EFF Observatory and SSL Labs prove SSL scanning may be
used for legitimate purposes, but much more scanning is happening in
the wild. I'm not sure it it's good or bad, but I fear that there
isn't enough visibility generated by the SSL servers. SSL errors seem
not to be logged and servers don't notice they are being scanned.

I think there is much more to SSL scanning, I feel this article barely
scratches the surface.


</%block>
</article>
