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

TLS
---

Here's how the [TLS handshake works](http://tools.ietf.org/html/rfc2246#page-31):

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
: The SSL/TLS protocol version the client (like the browser) wishes to
  use during the session. Additionally there is a second version
  number on the
  [Record layer](http://tools.ietf.org/html/rfc5246#page-19).  The
  [spec suggests](http://tools.ietf.org/html/rfc5246#page-88) the
  Record field may be use to indicate the lowest supported SSL/TLS
  version, but this is rarely used in practice. Only
  [older versions of Opera](https://github.com/majek/p0f/blob/6b1570c6caf8e6c4de0d67e72eb6892030223b01/p0f.fp#L1086-1089)
  are using different values in Record and ClientHello layers.

random
: This value is formed of 4 bytes representing time since epoch on client
    host and 28 random bytes. Exposing timer sources may allow [clock skew
    measurments](http://www.cl.cam.ac.uk/~sjm217/papers/usenix08clockskew.pdf)
    and those may be used to identify hosts.
    
    > Your browser broadcasts current time on SSL layer, without any
    > JavaScript or even before HTTP.

session_id
: Instead of going through full SSL handshake, the client may decide
  to reuse previously established session. The session cache is usually
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
  There isn't a global coherent list of good ciphers, and as a result
  every client can support different set of ciphers. Additionally the
  [ordering of the ciphers is significant](http://tools.ietf.org/html/rfc5246#page-40)
  and therefore even if clients agreed on ciphers the ordering
  might be completely different.
  
    > By just looking at the supported ciphers list it is often
    > possible to tell what exact application had started the
    > connection.
  
compression_methods
: Some clients (for example Chrome) support
  [Deflate compression](http://tools.ietf.org/html/rfc3749#section-2.1).
  on SSL layer. This usually makes sense - compressing HTTP headers
  does save bandwidth. Remember to disable gzip compression on higher
  HTTP layers.
  
extensions
:   TLS introduces
    [a number of extensions](http://www.iana.org/assignments/tls-extensiontype-values/tls-extensiontype-values.xml).
    Most notably the `server_name` /
    [Server Name Indication](http://tools.ietf.org/html/rfc4366#section-3.1)
    [(SNI)](https://en.wikipedia.org/wiki/Server_Name_Indication)
    extension is used to specify a remote host name. This allows the
    server to choose apporpriate certificate based on the host name.
    This allows hosting many domains on a single IP address, and
    famously
    [doesn't work on any IE on Windows XP](http://adam.heroku.com/past/2009/9/22/sni_ssl/).
  
    > When using SSL, the remote domain name is transferred over the
    > wire in plain text. Anyone able to sniff the traffic can know
    > exactly what domains you're looking at, even when you're using
    > HTTPS.
    
    Similairly to the cipher list extensions and their order are
    application specific. For example:
    [FireFox 11 bundled with TOR](http://www.torproject.us/projects/torbrowser.html.en)
    is distinguishable from standalone installation - it doesn't send
    `SessionTicket TLS` extension.


That's it, now you know what's hidden in SSL ClientHello message. For
a completeness, few words on historical protocols.

SSL 3.0
-------

[SSLv3](https://tools.ietf.org/html/rfc6101) is identical to described
TLS with one exception - in theory SSLv3 ClientHello packet doesn't
have
[an extensions field](https://tools.ietf.org/html/rfc6101#page-26).
In theory SSLv3 doesn't do
[SNI](https://en.wikipedia.org/wiki/Server_Name_Indication).

In practice this is more
complicated. [TLS 1.0](http://tools.ietf.org/html/rfc2246#page-35)
also doesn't specify extensions, but most clients do send them anyway.

SSL 2.0
--------

[SSL 2.0](http://www.mozilla.org/projects/security/pki/nss/ssl/draft02.html)
was [originally developed by Netscape](https://en.wikipedia.org/wiki/Transport_Layer_Security#SSL_1.0.2C_2.0_and_3.0). It's old, barely documented and
insecure. But some applications still support it, for compatibility
with old servers. Some versions of `wget` and google crawler use SSLv2
handshake. `CLIENT-HELLO` message is defined as:

    char MSG-CLIENT-HELLO
    char CLIENT-VERSION-MSB
    char CLIENT-VERSION-LSB
    char CIPHER-SPECS-LENGTH-MSB
    char CIPHER-SPECS-LENGTH-LSB
    char SESSION-ID-LENGTH-MSB
    char SESSION-ID-LENGTH-LSB
    char CHALLENGE-LENGTH-MSB
    char CHALLENGE-LENGTH-LSB
    char CIPHER-SPECS-DATA[(MSB<<8)|LSB]
    char SESSION-ID-DATA[(MSB<<8)|LSB]
    char CHALLENGE-DATA[(MSB<<8)|LSB]

The fields are familiar - `client_version`, `cipher_suites`,
`session_id` and `challenge`. It's worth noting that SSLv2 doesn't
have extensions - there is no way to specify
[SNI](https://en.wikipedia.org/wiki/Server_Name_Indication) .

On a final note `challenge-data` length must be between 16 and 32
bytes long. In practice I've only seen lengths equal to 16 or 32.

Summary
-------

Things to remember:

 * Anyone snooping the HTTPS traffic is able to see the remote domain
   name in plain text due to SNI.

 * `ClientHello` message contains a lot of stuff and it is often
   possible to identify a client application just by looking at it.


</%block> </article>
