<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

-------------

I've published an article on the CloudFlare blog:

 * [https://blog.cloudflare.com/tld-glue-sticks-around-too-long/](https://blog.cloudflare.com/tld-glue-sticks-around-too-long/)

-------------



<% a = '''
Recent [headline grabbing DDoS attacks](https://en.wikipedia.org/wiki/2016_Dyn_cyberattack) provoked heated debates in the DNS community. Everyone has strong opinions on how to harden the DNS to avoid downtimes in future. Better to use a single DNS provider or multiple? What DNS TTL values are best? Does DNSSEC make you more or less exposed?

These are valid questions worth serious discussion, but tuning your own DNS settings is not the full story. Together, as a community, we need to harden the DNS protocol itself. We need to prepare it to sustain the toughest DDoS attacks the future will surely bring. In this blog post I'll point out an obscure feature that already exists in core DNS protocol. It is not practical now, but with a small tweak it could be extremely useful during attacks. The feature is not helpful due to DNS TLD operators negligence. Have we made it working - we could greatly reduce the DDoS recovery time for DNS providers under attack.

The feature in question is: TLD glue records. More specifically TLD glue records with low TTL values.

DNS glue is one of the least understood quirks in the DNS protocol. Allow me to explain why I think reducing glue TTL is a good idea. But first: what is a glue anyway?

DNS Glue
--------

DNS glue is a solution to ["the chicken or the egg problem"](https://en.wikipedia.org/wiki/Chicken_or_the_egg) that is inherent in DNS. It's easiest to explain it on a concrete example.

Imagine you want to resolve the `cloudflare.net` domain.  For that you ask your local recursive DNS server for the resolution. Ok, but that doesn't answer the question, what does the resolver do?

For simplicity let's make a couple of assumptions:

 - Our recursor doesn't have any data for `cloudflare.net` in local cache.
 - It does know that `.net` TLD is handled by couple of nameservers, among them `a.gtld-servers.net` which has IP address of `192.5.6.30`.
 - We ignore the first steps and start our investigation by looking at the recursor when it queries the `.net` nameserver.

To resolve `www.cloudflare.net` the recursor needs to figure out what nameservers host the `cloudflare.net` data - or in DNS speech: what nameservers are authoritative for that zone.

To do so, the recursor asks the `.net` nameserver. Let's assume we know that one of these is `192.5.6.30`. Recursor will launch a query which we can simulate with this `dig` command:

```
$ dig www.cloudflare.net @192.5.6.30
[ output truncated for brevity ]
;; AUTHORITY SECTION:
cloudflare.net.         172800  IN      NS      ns1.cloudflare.net.

;; ADDITIONAL SECTION:
[ skipped for now ]
```

We politely asked one of `.net` nameservers: where is `www.cloudflare.net`? The answer received: I don't know, but I know who to ask! Go talk to `ns1.cloudflare.net`, he knows all about `cloudflare.net` zone!

This is called a delegation. `.net` told us to go away and ask `ns1.cloudflare.net` instead.

Hold on, but where `ns1.cloudflare.net` is? What is its IP address? If we asked `.net` nameserver, he'd tell us the same thing - go and talk to `ns1.cloudflare.net`!

As you can see, here's a chicken and egg problem. To resolve `www.cloudflare.net` we need to resolve `ns1.cloudflare.net`. To resolve `ns1.cloudflare.net` we need to resolve `ns1.cloudflare.net`, and so on.

The glue
-------

This is where DNS glue comes in. I lied a bit in previous console output, the resolution of `ns1.cloudflare.net` is available in the response given by `.net` nameserver. This time allow me to show the relevant "ADDITIONAL" section of the answer:

```
$ dig www.cloudflare.net @192.5.6.30
[ output truncated for brevity ]
;; AUTHORITY SECTION:
cloudflare.net.         172800  IN      NS      ns1.cloudflare.net.

;; ADDITIONAL SECTION:
ns1.cloudflare.net.     172800  IN      A       173.245.59.31
```

To break the resolution loop we need the second bit of data in the answer - the ADDITIONAL SECTION. Here the server says: btw, in case you wondered where `ns1.cloudflare.net` is: it's in `173.245.59.31` at your convenience!

This is what is called a DNS glue. Conceptually it's a pretty weird invention. We are asking the authoritative name servers of `.net` zone, for resolution of `cloudflare.net`. In response we don't only get the delegation information but also an address of the server. Think about it - it's like a part of `cloudflare.net` zone was copied to `.net` TLD zone.

How far can this go? Can there be arbitrary resolutions sticked in the ADDITIONAL SECTION? Will this work?

```
$ dig www.cloudflare.net @192.5.6.30
[ output truncated for brevity ]
;; AUTHORITY SECTION:
cloudflare.net.         172800  IN      NS      ns1.cloudflare.net.

;; ADDITIONAL SECTION:
ns1.cloudflare.net.     172800  IN      A       173.245.59.31
www.google.com          172800  IN      A       1.2.3.4
```

The fun story is: it used to "work" and confuse recursors. This is precisely what [Kashpureff attack did in 1997](http://www.secure64.com/news-internic-alternic-dns-poisoning).

This kind of attack is a good old school DNS cache injection or cache poisoning. This logic of interpreting DNS glue answers on the DNS recursor side is pretty twisted. The details are poorly understood, vary with every implementation. Conceptually the barrier between valid glue record and cache injection is very thin. (Find more details in this [draft by Nicolas Weaver](https://tools.ietf.org/id/draft-weaver-dnsext-comprehensive-resolver-00.html#object_scope).)


What's the problem?
------------------

We've shown what DNS glue is, how it works, and why it is needed in the DNS protocol. Frankly speaking DNS glue is pretty ingenious solution to solve real struggle, Let me explain the problem now. Let's take a look at the glue the answer again:

```
;; ADDITIONAL SECTION:
ns1.cloudflare.net.     172800  IN      A       173.245.59.31
```

The problem is the TTL value. Here, you can see the TTL of that record is 172800 seconds = 48 hours. In normal situations a domain owner, in this case my colleague managing `cloudflare.net` domain, has a way to configure this value in glue record. It is not the value intended - if you ask a `cloudflare.com` authoritative nameserver for a this record:

```
$ dig ns1.cloudflare.net @173.245.59.31
ns1.cloudflare.net.	900	IN	A	173.245.59.31
```

You can see that the authoritative nameserver thinks this record is valid for only 900 seconds = 15 minutes.

Where this discrepancy comes from?

The glue records are usually managed in some kind of panel exposed by the registrar. This is fine, in the end we inject part of `cloudflare.net` namespace into `.net` zone. But here is the problem: while there is a way to set the glue IP address, there is no way to configure the TTL. The glue TTL is hardcoded to 48 hours by the TLD operators.


I strongly believe this is way too much and hurts aggressive DDoS mitigation techniques.

Scattering
---------

Had that DNS glue TTL been smaller, it would be possible to rotate the nameserver IP's during the attack. In fact, at Cloudflare we use this technique all the time on HTTP layer.

During significant attacks we have ability to promptly move customer traffic, by changing the DNS resolution of our customer orange-clouded domains. This allows us to shift legitimate traffic off the attacked IP addresses, and deploy aggressive DDoS mitigations on them. In extreme cases we can BGP nullroute the targeted IP's with little customer impact. Internally we call this technique "scattering".

"Scattering" on HTTP layer is very effectie against attacks where the target IP is hardcoded. It is only possible to do scattering because we serve DNS records with low DNS TTL values.

"Scattering" on DNS authoritative layer could be powerful against attacks launched directly against DNS authoritative servers, where packets from botnet hit auth servers directly, without being reflected by DNS recursors. Unfortunately though is impossible to do "dns auth scattering" because we don't have power to ajdust TLD glue TTL values. With the TTL stuck at 48h, changing the nameserver IP addresses dynamically is not an option.

I believe this should be fixed.


Testing things
------------

It's hard to prove the effectiveness of this technique since glue TTL's is hardcoded at large 48h. Instead we tested something different - we added a glue record and measured how long it to pick up its share of the traffic.

We performed the experiment on cloudflare.com domain. Here is a chart of traffic levels to two cloudflare nameservers with glue already present: ns3 and ns6, and new one we just added glue for: ns6-bis.

<gnuplot>
size: 500x350
--
set datafile separator ","

set xtics rotate
set border 3;
set xtics nomirror;
set ytics nomirror;
set xtics 7200;

set timefmt '%Y-%m-%dT%H:%M'

set ylabel "queries per second"
set xdata time
set format x "%H-%M"

set xrange ["2016-04-15T08:00": "2016-04-17"]
set yrange ["0":"400"]
# set key off

plot \
  "first.csv" using 1:2 with lines title "ns3", \
  "first.csv" using 1:5 with lines title "ns6", \
  "first.csv" using 1:7 with lines title "ns6-bis"
</gnuplot>

We added glue at 22pm UTC one night. It is nicely visible how the traffic on this IP address gradually increased as the caches on the recursors worldwide expired. The traffic seem to have reached levels comparable with other glue nameservers at about 4-6pm next day - around 8h.

There is at least 8h delay before a big chunk of the DNS resolvers will pick up new glued IP. The maximum time for the full switch is of course 48h.

Closing thoughts
------

We must use every possible technique in order to make DNS infrastructure more resilient against DDoS attacks. We may need to improve the core DNS protocol (aggressive NSEC caching), tune the defaults (advocate the use of low TTL's) and share advanced mitigation techniques (scattering).

In this article I explained what DNS glue is, and why I believe DNS glue TTL values hardcoded at large 48h are not helping with DDoS mitigations.  I hope this article will serve a a call to action for relevant TLD operators. I believe the ability to adjust DNS glue TTL's is a simple yet effective way to make DNS authoritative servers more reliable.



''' %>

</%block>
