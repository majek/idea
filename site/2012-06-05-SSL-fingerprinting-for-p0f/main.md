<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

Not everyone knows that SSL handshake is not encrypted. When you think
about it - there isn't other way, before the keys are exchanged the
communication must be unencrypted. But I doubt many people think about
it.

Here's how the [TLSv1 handshake works](http://tools.ietf.org/html/rfc2246#page-31):

```
      Client                                 Server
        |                                      |
        |  ----------- ClientHello --------->  |
        |                                      |
        |  <---------- ServerHello ----------  |
        |  <---------- Certificate ----------  |
        |                 ...                  |
        |  <-------- ServerHelloDone --------  |
        |                 ...                  |
```

Let's focus on the first message - `ClientHello`. It is actually
pretty interesting. RFC [defines the structure as](http://tools.ietf.org/html/rfc5246#page-41):

    struct {
        ProtocolVersion client_version;
        Random random;
        SessionID session_id;
        CipherSuite cipher_suites<2..2^16-1>;
        CompressionMethod compression_methods<1..2^8-1>;
        Extension extensions<0..2^16-1>;
    } ClientHello;


Translated to English:

client_version
: The SSL/TLS protocol version the client (like the browser) wishes to use
    during the session. Additionally there is a second version number
    on the [Record layer](http://tools.ietf.org/html/rfc5246#page-19).
    The [spec suggests](http://tools.ietf.org/html/rfc5246#page-88)
    the Record field may be use to indicate the lowest supported
    SSL/TLS version, but this is rarely used in practice. Only [older
    versions of Opera](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/p0f.fp#L1086-1089) used different values in Record and
    ClientHello layers.
    
random
: This value is formed of 4 bytes representing time since epoch on client
    host and 28 random bytes. Exposing timer sources may allow [clock skew
    measurments](http://www.cl.cam.ac.uk/~sjm217/papers/usenix08clockskew.pdf)
    and those may be used to identify hosts.
    
    > Your browser broadcasts current time on SSL layer, without any
    > JavaScript or even before HTTP.
       
session_id
: Instead of going throught full SSL handshake, the client may decide
  to reuse previously established one. Session cache is usually
  [shared between normal and privacy modes](http://trac.webkit.org/wiki/Fingerprinting#SessionIDs)
  of the browser.
  
    > Even in privacy mode, your browser may still be identifiable due
    > to the the SSL session reuse.

cipher_suites
: The client shares the list of supported SSL ciphers with the server.
  The server will later pick up the best cipher it knows. Some of the
  ciphers are proven to be insecure and should be deprecated, some
  other are
  [very new](https://en.wikipedia.org/wiki/Elliptic_curve_cryptography).
  But there isn't a single, coherent list of good ciphers, and as a result
  every client supports different ciphers.
  
    > By just looking at the supported SSL ciphers it is possible to
    > tell underlying SSL libraries apart and sometimes even particular
    > applications.
  
compression_methods
: Some clients (for example Chrome) support
  [Deflate compression](http://tools.ietf.org/html/rfc3749#section-2.1).
  on SSL layer. This usually makes sense - compressing HTTP headers
  usually saves bandwidth. Remember to disable compression on HTTP
  layer in this case.
  
extensions
: asd
  

Additionally,
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
