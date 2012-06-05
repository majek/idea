<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

In January [lcamtuf announced][1] a complete rewrite of his [p0f][]
passive fingerprinting tool. Historically p0f was a low-level tool,
mostly focused on fingerprinting layer 4 `SYN` and `SYN-ACK` packets.

  [1]: http://lcamtuf.blogspot.co.uk/2012/01/p0f-is-back.html
  [p0f]: http://lcamtuf.coredump.cx/p0f3/

New p0f moves up the stack and is capable of fingerprinting
application level protocols. By default it is able to create HTTP
fingerprints. The author also [suggests][] that other protocols are
likely to follow.

  [suggests]: https://github.com/p0f/p0f/blob/8f6712ec32dd745dd0f3749b3dd8738179c8680b/docs/README#L105
  
By a strange coincidence, recently I've been interested in SSL
fingerprinting.

Fingerprinting SSL
------------------

Not everyone knows that SSL handshake is not encrypted. Additionally,
the initial ClientHello frame is pretty interesting - it contains a
list of ciphers supported by the client.

Unsurpisingly, this list differs between clients, it is possible to
identify an SSL client by looking at this list. In other words - it is
possible to distingish Firefox, Chrome, Opera and IE apart by just
looking at raw SSL traffic.

This topic was already researched in the past, most notably by
[Ivan Ristić][ir] in June 2009. Ivan published
[a lot of interesting data](http://blog.ivanristic.com/2009/07/examples-of-the-information-collected-from-ssl-handshakes.html),
but seem to focus on SSL cipher list, ignoring the ordering of ciphers
and other potential sources of data.

 [ir]: http://blog.ivanristic.com/2009/06/http-client-fingerprinting-using-ssl-handshake-analysis.html

SSL and p0f
-----------

I decided to work on a tiny bit more elaborate SSL fingerprinting and
publish it as a p0f module. The code is available as a
[patch against p0f 3.05b](https://gist.github.com/2721464).

Detailed descriptin is avaliable in
[`docs/ssl-notes.txt`](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/docs/ssl-notes.txt)
and
[README](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/docs/README#L716).

In summary, this code looks at traffic passing by, and looks for SSL
ClientHello packets. It is able to decode both SSLv2 and SSLv3 / TLS
handshakes. Based on information in from packet it generates an SSL
fingerprint, for example a fingerprint for my Chrome 19 looks like:

    3.1:c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a:?0,ff01,a,b,23,3374:compr

The fingerprint is composed out of four fileds:

1. Requested **SSL version**.

        3.1

2. **Ciphers** the client supports, without changing the order.

        c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a

3. Specified **extensions**.

        ?0,ff01,a,b,23,3374

4. Additional **flags**, which identify few types of special
   behaviour. In my case this field notes that Chrome supports SSL
   compression.

        compr


This fingerprint is then matched against a database of predefined
signatures. If a match is found, p0f can say few things about the
client, usually a browser name, possible versions and sometimes even a
platform.

A full match for my Chrome looks like:

         raw_sig 3.1:c00a,c014,88,87,39,38,c00f,c005,84,35,c007,c009,c011,c013,45,44,66,33,32,c00c,c00e,c002,c004,96,41,5,4,2f,c008,c012,16,13,c00d,c003,feff,a:?0,ff01,a,b,23,3374:compr
       match_sig 3.1:c00a,c014,88,87,39,38,c00f,*,c003,feff,a:?0,ff01,a,b,23,3374:compr
             app Chrome 6 or newer
           drift 0
      remote_time 1338926865


Finally, SSLv3 handshake contains a client's GMT time field which you
can see above. It would be interesting to see if it is possible to do
fingerprinting based on
[clock skew](http://www.caida.org/publications/papers/2005/fingerprinting/KohnoBroidoClaffy05-devicefingerprinting.pdf).


You can see your fingerprint your browser here:

 * https://p0f.popcnt.org/
 
<br>
<br>

</%block>
</article>
