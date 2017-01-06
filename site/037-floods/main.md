
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Serving DNS on the Internet is far from trivial.

Every [authoritative DNS](https://en.wikipedia.org/wiki/Name_server#Authoritative_name_server) server will, sooner or later, get flooded with a large number of DNS requests. These floods are created by anything from single malicious users to large botnets, with the intention to knock the DNS server offline and cause a [denial-of-service](https://en.wikipedia.org/wiki/Denial-of-service_attack) situation.

{<1>}![](/content/images/2014/10/12617680335_ce4c067a3b_z.jpg)
<small>CC BY 2.0 by [Raido](https://www.flickr.com/photos/raidokaldma/)</small>

Large numbers of incoming packets usually cause either CPU exhaustion or network congestion. This means that unless you are prepared to deal with attacks you probably shouldn't run your own DNS server. It's surprisingly easy to successfully DoS a small DNS server.

CloudFlare provides authoritative DNS for our customers and we have to deal with packet floods all the time. In this article I'll explain what we do during a flood and what you can expect if your DNS server is being targeted.

When we see a flood
--------------

Most packet floods are relatively unsophisticated and are composed of large number of valid DNS queries targeted to a single name server. One of the floods we see pretty often consists of DNS queries going to `<randomprefix>.www.<targeted domain>.com`. [This presentation from UKNOF](https://indico.uknof.org.uk/getFile.py/access?contribId=15&resId=1&materialId=slides&con...) gives more details, here's an example:

    avytafkjad.www.23us.com
    
Of course this name doesn't exist and the server is supposed to answer with the NXDOMAIN DNS response. As the prefix in the query is random on every request the response can't be cached. With millions of requests the server becomes very busy just preparing the NXDOMAIN responses and may run out of resources to answer any remaining legitimate requests.

First, do nothing
------------

When the flood is small, typically we just ignore it. Our DNS servers are able to handle pretty large traffic volume without degrading service.

{<2>}![](/content/images/2014/10/Screen-Shot-2014-10-08-at-12-43-17.png)

Automatic rate limits kick in
-------------------------

Our server supports a number of automatic rate limits. They may kick in for a number of reasons, for example to avoid overwhelming the database, to reduce CPU footprint or network footprint of the server. When automatic rate limits kick in they only affect very specific traffic. Most often the story of a flood ends here.


It may be possible that the automatic rate limits misfire or misbehave for some reason. If that happens we have tools to amend them and create specific rate limits manually. We don't do that very often though.

The DNS server melts
------------------

Usually the floods are absorbed by our network and we may not even notice. But when the floods get bigger we first notice excessive CPU usage. At some point even counting the rate limits may cause noticeable load.

At this moment we usually see the DNS server not being able to keep up with the speed of incoming requests and kernel starts to drop received packets. The `netstat` metric "packet receive errors" will be growing:

    $ netstat --stat --udp|grep "packet receive errors"
    1776 packet receive errors

This is the time to take a deeper look into the traffic.

Our 24/7 Site Reliability Team keeps a constant eye on our worldwide network of servers and can quickly spot any problems. On the real time dashboard they observe floods and are presented with various mitigation options.

First, they inspect the target of the flood - the IP's of the servers affected. Floods can often be mitigated by `iptables` rules created with help of our [bpftools](https://github.com/cloudflare/bpftools) library. For the previous example we would deploy the rule:

    killdns *.www.23us.com

This will ensure that the majority of DNS packets created by the flood won't hit our DNS server. We have more ways of blocking packets, but the gist is that it's all done at the firewall layer.

Note on FINTing
----------

We do our best to avoid drastic actions until the flood starts affecting other customers. When it does happen we check if the customer being the target of the flood is covered by our full DDoS protection. This is a feature for our Business and Enterprise tier customers.

If the flood is targeted against a customer without a full DDoS protection we sometimes decide to terminate our service. That usually entails redirecting the http traffic directly to the customer's origin server, skipping the CloudFlare http proxy. Internally we call that FINTing. We're able to revert the FINT within seconds if a customer wishes so.

Although disabling CloudFlare's http proxying may sound harsh, it's the tough reality. We just don't have enough man power to offer full support for more than two million free DNS zones. Finally, please note that the flood must be pretty significant for us to take this action and it doesn't happen too often. Our long term goal is to offer full protection for everybody, it's a big task but we hope to get there eventually.

The server melts
---------------

At some point during a flood our servers start melting down due to a symptom known as an [interrupt storm](https://en.wikipedia.org/wiki/Interrupt_storm). This happens when the rate of incoming packets exceeds the CPU available on the server and the operating system is completely swamped by just receiving packets from the network.

To mitigate we are able to spread the traffic across more servers. This is a straightforward measure for us, but we need to be careful: as the traffic spreads across more servers so does the load. Whether we chose to do it or not depends on many things like the amount of spare capacity we have, the type of the flood and the size of it.

Another mitigation we can use is to enable rate limits on our router. This limits can be fairly specific affecting only certain kind of traffic going to a single name server IP. Rate limiting traffic is a pretty rough measure, as it may affect other customers using targeted name server. In practice though, it's not as bad, as it affects:

 - _only certain packets_: We make the rate limit very specific to particular flood.
 - _only a single name server_: All our customers have at least two name servers. The other one will continue uninterrupted service.
 - _only specific locations_: Most of the floods come from a single source and affect only a single geographic region.


At the same time we are engaging the customer in a conversation how we can help. We usually offer to migrate targeted domains to a set of dedicated nameservers. This is beneficial to the customer and allows us to better mitigate the flood and limit the impact dealt to our other users.

{<3>}![](/content/images/2014/10/2593475733_8a7ed3c697_z.jpg)
<small>CC BY 2.0 by [Usgeologicalsurvey](https://www.flickr.com/photos/usgeologicalsurvey/)</small>

The network melts
----------------

As a CDN we have spare inbound network capacity, but even that sometimes isn't enough.

At some scale of the floods our cables gets red hot. The vast bandwidth of packets incoming to the router saturate the links and cause congestion for all our incoming traffic, not just the DNS.

For that scale of the flood, unfortunately, we have only one weapon - we contact our upstream internet providers and ask to [Black Hole](https://en.wikipedia.org/wiki/Black_hole_(networking)) all traffic coming to a particular IP address. At this stage the target web site usually has a dedicated a set of name servers so this action affects only the targeted domain.

There are many tricks we can use to try to get the web site back online, by shifting BGP routes or disabling specific locations. But there is no template and all we will engage with the affected customer to find acceptable mitigation.

In order to improve our resilience to these gigantic floods we are constantly improving our network. We have almost 30 data centers around the globe and ever increasing network capacity.

We're constantly learning
------------------

At CloudFlare we totally understand that as a CDN we are a critical part of our customers infrastructure. Every day we are trying to find the balance between offering a reliable service for everyone and a decent DDoS protection for those few unlucky.
 
It's a tough game, but with every packet flood we see we're learning and constantly trying to find better ways of dealing with all the different DoS attack vectors. Some day if you become the unlucky one we hope to be able to give you a hand.



</%block>
