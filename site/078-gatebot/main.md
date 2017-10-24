<%inherit file="basecomment.html"/>
<%block filter="filters.markdown">

-------------

I've published an article on the Cloudflare blog:

 * [https://blog.cloudflare.com/meet-gatebot-a-bot-that-allows-us-to-sleep/](https://blog.cloudflare.com/meet-gatebot-a-bot-that-allows-us-to-sleep/)

-------------

<%doc>
Meet Gatebot - a bot that allows us to sleep
=====================================


In past we spoke about Cloudflare resiliance to DDoS attacks. Our
service is architected to sustain the largest malicious traffic
surges. To avoid having a single choke point we split the traffic
across large number of servers - do that by employing Anycast and
ECMP.

We don't use scrubbing boxes or specialized hardware - each of our
edge servers can perform advanced traffic filtering if the need
arises. This allows us to scale up our DDoS capacity nicely. Each of
the new servers we add to our datacenters increases our max
theoretical DDoS scrubbing limits. It also scales down nicely - in
smaller dataceters we don't have to overinvest in expensive dedicated
hardware.

During normal operations our attitude to attacks is rather
pragmatic. Since all the inbound traffic is distributed across dozens
and dozens of servers we can survive periodic spikes and small attacks
without doing anything. Vanilla Linux is remarkably resilient against
unexpected network events. This is especially true since kernel 4.4
when the SYN cookies were greatly sped up.

At some point though we can't afford to burn excessive amount of CPU
power on processing attack packets in the default way. When the attack
size crosses a predefined threshold (which varies greatly depending on
specific attack type), we must intervene. Cloudflare operates
multi-tenant service and we must always be sure there is enough
processing power to serve the valid traffic. We can't afford to starve
our HTTP proxy (nginx + openresty) or custom DNS server (named RRDNS,
written in golang) out of CPU.


Mitigations
--------

The mitigations we employ, when the need arises, aren't overly
complex. We rely heavily on Linux built in firewall - iptables. Over
the years we mastered the most effective extensions:

 - xt_bpf
 - ipsets
 - hashlimits
 - connlimit

Using stock iptables gives us plenty of confidence. We really don't
want to do anything weird to the packets passing our servers.

Apart from iptables, we have a whole arsenal of mitigation techniques
across the whole stack, from DNS tricks to Captchas. Let's not get
distracted though, for this discussion let's focus on iptables.

When we realized the power of iptables, we've built a centralized
iptables deployment system. This isn't anything fancy - just a
glorified interface on top of iptables allowing us to quickly add and
remove rules across our server fleet. This fits our architecture
nicely: due to Anycast, an attack against a single IP may be delivered
to multiple locations. Deploying iptables rules against that IP on all
servers makes sense.

Furthermore, it's worth emphasizing that we don't treat our firewall
like most companies - it's not a static set of rules. We dynamically
add, tweak and remove rules, based on specific attack characteristics.

Early on the mitigations were applied by our tireless SRE's. We
realized that humans under stress... well, make mistakes. We learned
it the hard way - one of the most famous incidents happened in March
2013 when a simple typo brought our whole network down:

 - [https://blog.cloudflare.com/todays-outage-post-mortem-82515/](https://blog.cloudflare.com/todays-outage-post-mortem-82515/)


Meet Gatebot
------------

To aid or SRE's this we created an automatic mitigation system. We
call it Gatebot. (Fun fact, our other related projects are called:
gate-something, like: gatekeeper, gatesetter, floodgate, gatewatcher,
gateman.... Who said that naming things must be hard?)

The intention of Gatebot is to automate as much of the SRE mitigation
workflow as possible. This means - observing the network and anomalies
in it, understanding the targets of attacks, their metadata (like:
enterprise vs free customer), and performing appropriate mitigation
action. Each Gatebot pipeline has three parts:

 - signal - A dedicated system detects anomalies in network
   traffic. This is usually done by piping the sampled network packets
   into a hierarchy of heavy-hitter data structures. Employing
   streaming algorighms allows us to have a running view of the
   "current" status of the network.

 - business logic - For each anomaly (attack) we look who is the
   target, can we mitigate it, and if so which what
   parameters. Depending on specific pipeline the business logic may
   be anything from trivial to multi-step requiring number of database
   lookups and a human operator confirmation.

 - mitigation - The previous step feeds specific mitigation
   instructions into the centralized mitigation system. The
   mitigations are distributed across the world and applied on our
   servers.

While original Gatebot pipelines were created around automating
ipables mitigation deployment, we've proved that the general model
works for automating other issues equally well.  Today we have more
than 10 separate Gatebot instances doing everything from mitigating
Layer 7 attacks to informing our Customer Support colleagues of
misbehaving customer origin servers.


Sleeping at night
-----------------

Daily Gatebot engages iptables mitigations between 30 and 300 times. 


We learned greatly from the "signal/logic/mitigation" attitude, and
are reusing this model in our
[Automatic Network System](https://blog.cloudflare.com/the-internet-is-hostile-building-a-more-resilient-network/)
used to perform actions when abnormal network congestion is
detected. (This system arguably should be called Netbot).



</%doc>
</%block>


