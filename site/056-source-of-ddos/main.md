<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

A couple of weeks back we wrote a long article about [yet another large
L3 DDoS attack](https://blog.cloudflare.com/a-winter-of-400gbps-weekend-ddos-attacks/) hitting CloudFlare.

An obvious question comes to mind - where do these attacks come from?

Sadly, it's easier said than done. Atributing L3 attacks is very
hard. Unless large interenet carriers get their act together, I'm
afraid we won't free the internet of DDoS problem.


Let me explain.

It's technically hard
---------------------

Spoofed.

Which router port?

No pcap on a router.

Raw netflow contains too detailed data.


Our solution
-------------


Convert netflow to pcap. Use tcpdump to filter. Record. Ship.


Carriers have misaligned incentives
----------------------------------

We are paying our carriers to deliver traffic to us. Traffic we don't really want.



How we should fix it
--------------------

Carriers should not censor. Carriers should incentivise theri
customers to forbid IP spoofing.
Carriers should help with attribution.


The black future
----------------

If we don't sort out the IP spoofing problem soon two things will happen:

The internet will get even more centralized, since it will require immense network capacity to withstand these attacks.
 
The legislators will eventually notice the problem and will put BCP38 into a law. This was already mentioned a number of times
 
https://www.youtube.com/watch?v=zyjCcup0zAE

Neither of these is outcomes is good. Please, put the pressure on
internet carriers to finally solve the IP spoofing problem.

</%block>
