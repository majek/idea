<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

In January [Lcamtuf announced][1] a complete rewrite of his
passive fingerprinting tool [p0f][]. Historically p0f was a low-level tool
focused on fingerprinting layer 4, mostly `SYN` and `SYN-ACK` TCP/IP
packets.

  [1]: http://lcamtuf.blogspot.co.uk/2012/01/p0f-is-back.html
  [p0f]: http://lcamtuf.coredump.cx/p0f3/

The new version of p0f is different: not only it can look at low level
packets, but also it is capable of fingerprinting higher-level
application protocols. Currently it is able to do HTTP fingerprinting
and the author [suggests][] other protocols might soon follow.

  [suggests]: https://github.com/p0f/p0f/blob/8f6712ec32dd745dd0f3749b3dd8738179c8680b/docs/README#L105
  
By a strange coincidence, recently I've been interested in SSL
fingerprinting.

Fingerprinting SSL
------------------

In [my previous article](/2012-06-16-dissecting-ssl-handshake/) I've
described the structure of SSL/TLS `ClientHello` packet.

Importantly, it contains a list of supported ciphers and extensions.

Unsurprisingly, those lists differ between clients and often it is
possible to identify an SSL client by looking at them. In other words
- it is possible to distinguish Firefox, Chrome, Opera and IE apart by
just looking at the initial HTTPS packet, which is unencrypted.

This topic was already researched in the past, most notably by
[Ivan Ristić][ir] in June 2009. Ivan published
[a lot of interesting data](http://blog.ivanristic.com/2009/07/examples-of-the-information-collected-from-ssl-handshakes.html),
but seemed to focus on the SSL cipher list, ignoring the ordering of ciphers
and other potential sources of data, like TLS extensions.

 [ir]: http://blog.ivanristic.com/2009/06/http-client-fingerprinting-using-ssl-handshake-analysis.html

SSL and p0f
-----------

I decided to work on more elaborate SSL fingerprinting and publish it
as a p0f module. The code is available as a
[patch against p0f 3.05b](https://gist.github.com/2721464).

Detailed description is available in
[docs/ssl-notes.txt](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/docs/ssl-notes.txt)
and
[README](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/docs/README#L716).

In summary, this code looks at traffic passing by and looks for SSL
`ClientHello` packets. It is able to decode both SSLv2 and SSLv3 / TLS
handshakes. Based on information in such a packet it generates a
fingerprint; for example, my Chrome 19 produces:

    3.1:c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a:?0,ff01,a,b,23,3374:compr

The fingerprint is composed out of four colon separated fields:

1. Requested **SSL version**.

        3.1

2. **Ciphers** the client supports, without changing the order. In
   theory ciphers are sent in an order of preference.

        c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a

3. Specified **extensions**, without altering the order.

        ?0,ff01,a,b,23,3374

4. Additional **flags**, which identify few types of special
   behaviour. In my case this field notes that Chrome supports SSL
   compression.

        compr


Next, the fingerprint is matched against
[a database of predefined signatures](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/p0f.fp). If
a match is found, p0f can say few things about the client, usually a
browser name, possible versions and sometimes a platform.

A full match for my Chrome looks like:

    app         = Chrome 6 or newer
    drift       = 0
    remote_time = 1338926865
    match_sig   = 3.1:c00a,c014,88,87,39,38,c00f,*,c003,feff,a:?0,ff01,a,b,23,3374:compr
    raw_sig     = 3.1:c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a:?0,ff01,a,b,23,3374:compr


Finally, the SSLv3 handshake contains a client's GMT time field which
you can see above in the `remote_time` field. It would be interesting
to see if it is possible to do fingerprinting based on
[clock skew](http://www.caida.org/publications/papers/2005/fingerprinting/KohnoBroidoClaffy05-devicefingerprinting.pdf).


You can see the fingerprint of your browser using the online experiment:

 * https://p0f.popcnt.org/

Continue reading about [scanning SSL servers &#8594;](/2012-11-12-ssl-scanners/)<br>

</%block>
</article>
