<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

I gave a talk at the
[Strange Loop 2016](http://www.thestrangeloop.com/2016/are-ddos-attacks-a-threat-to-the-decentralised-internet.html)
in St Louis.

Here are the slides:

  * [https://speakerdeck.com/majek04/ip-spoofing](https://speakerdeck.com/majek04/ip-spoofing)


Video:

  * [https://www.youtube.com/watch?v=79u7bURE6Ss](https://www.youtube.com/watch?v=79u7bURE6Ss)


Pardon the yellow slides! Flux was convinced it was a middle of a night.

${ '##' }Transcript

<div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.001.jpg"></div>

Good morning! This is the DDoS talk. It's always hard to speak about
DDoS. Many people mean very different things by it. Some say "DDoS"
when in fact the problem is that their Ruby app can't handle more than
five concurrent users.

Slow Ruby servers is not the subject of this talk. I'm going to talk
about one specific kind of DDoS attacks: the really big DDoS
attacks. The kind of attacks that made it into the news. If you heard
about things like "biggest DDoS threatening the internet", this
presentation will explain all the details.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.002.jpg"></div>

Before we start let me give you a roadmap of this talk. First I'll
explain the Distributed Denial Of Service, or DDoS, attacks. These are
the attacks where somebody uses many machines to attack, and to
attempt to deny access to some internet service. Basically try to take
someone off the internet.

Then I'll make a case that IP spoofing, which is faking IP address,
allows the most serious attacks. I'll explain why it's impossible to
trace the offender of such attacks. I'll show a couple of examples of
sophisticated attacks possible due to IP spoofing.

I'll conclude that the only way to defend such attacks is to invest in
beefy infrastructure, which is expensive. This is one of the forces
that leads to centralization in the internet, which is undesirable.

Finally I'll show how to untangle this mess and what can be done to
finally fix the problem.


Ok, let's start up, let's explain why DDoS attacks are a problem.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.003.jpg"></div>

But how should I know anything about that?

Well, let me introduce myself. My name is Marek and I'm an engineer at a performance and security company called CloudFlare.

At CloudFlare we operate a globally distributed reverse proxy service.

We own servers all around the world. I think we are present in 86
locations at last count. We see a big chunk of traffic crossing the
internet. Think about us as a part of internet infrastructure.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.004.jpg"></div>

We have plenty of customers from many different countries. We help
everyone, from dating portals through social media sites to government
agencies. But most importantly we are content neutral.

We try not to discriminate websites based on the content they provide.

<hr><div class="image" style=""><img style="height:336px;" src="strange-loop3-iwi-09-09.005.jpg"></div>

But operating a content neutral service in today's Internet is a tough
job. Some people think they can decide what should and what should not
be available online and if they dislike something they often try to
launch a DDoS attack to take down the website.

Being a middle man we see many of these attacks. This is not
scaremongering, the attacks happen all the time.

Here's a chart of last 90 days of attacks we saw. The X axis shows
time - in days, the Y axis shows number of DDoS events we saw on that
day. On many slower days we saw between 50 and 200 DDoS events per
day, on the busier days we saw over 1200 separate incidents.


<hr><div class="image" style=""><img style="height:336px;" src="strange-loop3-iwi-09-09.006.jpg"></div>

But fighting these attacks is not something we do because it's fun. In
order to survive in the internet we had to adapt and learn how to
withstand them.

Believe me, nobody at the enjoys attack handling. This is a huge
distraction and I'll much rather spend time on doing something
constructive. It would be awesome to fix the internet and solve them
for everyone.

As part of a wider effort to share our DDoS mitigation experience we
are trying to make as much of the details of attack handling possible.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.007.jpg"></div>

Over the years we published many stories of record breaking
attacks. In this presentation I'll focus on three specific big
attacks: Spamhaus DNS amplifications from 2013, the direct attacks we
dubbed "Winter of attacks" from earlier this year and a new type of
attacks we noticed only recently which I call a "direct subnet"
attack.

Don't worry if these names mean nothing to you, I'll explain the
attacks later in this talk.

It's very important to understand that these record breaking attacks
are not coming out from void. All of them had two things in common.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.008.jpg"></div>



(Almost)[^krebs] All of these big attacks share two important characteristics.

[^krebs]: Editor note: this presentation was prepared before the
[Krebs On Security](http://krebsonsecurity.com/2016/09/krebsonsecurity-hit-with-record-ddos)
DDoS attacks which had a different profile and did _not_ neccesairly
contain Spoofed IP addresses. This does not invalidate this
talk. Non-spoofed attacks are easier to block and since the source addresses are
known it's possible to report and eventually destroy the botnets.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.009.jpg"></div>

First all of these attacks are BIG. And for them to be large they must
be composed of a large, a very large number of packets. It's very hard
to generate substantial traffic with legitimate fully established TCP
connections, so instead, this record breaking attacks are composed of
just very large number of packets hitting the target.

It's not uncommon that only one in ten thousand packets hitting our
servers is legitimate. Very often the vast majority of received
packets belong to the attack.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.010.jpg"></div>

Second shared characteristic shared among the big attacks is that they
all begin with an attacker being able to perform IP Spoofing.

So what is IP spoofing?

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.011.jpg"></div>

It's a pretty simple thing. In the internet the data is chopped and
delivered in packets. Each internet packet contains a header in which
there are many of interesting fields, among them the source and
destination IP addresses.

But the packet is just a series of bytes and whoever sends it can
control it fully. If you transmit it over the wire, you can totally
put anything you want inside the packet and inside the headers.

IP spoofing is an idea of rewriting the Source IP address of the
packets. That's it.

It's pretty bad though.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.012.jpg"></div>

Because it enables impersonation. From the receiving end it's
impossible to determine if the received packet was really transmitted
by the real host or was maliciously injected into the internet by some
impostor.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.013.jpg"></div>

It was recognized pretty long time ago that this can lead to
significant problems. In May 2000 a famous document was published,
called BCP 38. BCP stands for Best Current Practices, it's like an
RFC document but a bit less formal.

BCP 38 said clearly - IP spoofing may allow attacks and the internet
community must proactively fight it.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.014.jpg"></div>

Over the last 16 years much progress had been done in this direction,
but it's still not fully solved. According to
[spoofer.caida.org](spoofer.caida.org) project, still about 27% of the
internet service providers do allow their customers to send spoofed IP
packets.

Unfortunately this number is not dropping these days. You may ask why,
what is so hard about not allowing spoofed packets to be transmitted.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.015.jpg"></div>

This is a long story, but to cut it short: basically the only way to
stop IP spoofing is to do filtering very close to the source, to the
party originating the packets. If you have a home DSL connection, the
filtering will be done on your modem. If you own a server it's the
closest switch or router that must filter out the packets with spoofed
source IP addresses.

This is not always simple. This requires the ISP's to have hardware
that can do filtering, then to maintain the configuration. It costs
money and expertise.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.016.jpg"></div>

Ok, this concludes the introduction to this talk. I explained that IP
spoofing allows the attacker to impersonate anyone on the internet.

Then I tried to convince you that the IP spoofing is still an unsolved
problem. The internet community is aware of it for two decades, but
still about 27% of networks allow IP spoofing.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.017.jpg"></div>

Let me focus now on the properties of the attacks caused by IP spoofing.

IP Spoofing is a problem. It's impossible to fight it because the attackers are fully anonymous and immune.

I'd like to show you that on a concrete example. Let me walk you
through the steps we do when we are hit by an attack and want to
identify who is behind it, where it is originated.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.018.jpg"></div>

Each process of tracing back the attack starts with, well, noticing
the attack in the first place. The most obvious way is to look the
inbound packet per second charts. Here you can see such a chart of
packets per second hitting one of our servers.

During normal operation it was receiving about 50 thousand packets per
second, and then the attack started hitting above 400 thousand pps. A
significant increase.

The first step in tracing back the attack is to figure out what is hitting us.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.019.jpg"></div>

To do that we log in to the attacked server, and run a `tcpdump` to
see what packets are delivered. In this case it was a SYN flood, that
is a flood composed of TCP packets with SYN bit set. If you look
carefully you might notice the source IP's look random - well, it's
because in this case they were spoofed.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.020.jpg"></div>

Now we know what hits us. The next question is to identify where it
came from. To do this we need to look at our router and figure our
just out of which interface the attack came from. Our routers have
very many interfaces, connected to multiple parties on the
internet. Which one sent us the attack?


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.021.jpg"></div>

To identify this we need to inspect our router charts. Here's an
example screen shot showing charts for four interfaces. In the bottom
left corner you can see two big, 10Gbps, spikes of inbound
traffic. This pattern usually indicates an attack. In this case the
attack was coming from that interface.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.022.jpg"></div>

So who is on the other side of this interface? We need to identify
where the physical cable leads to, just who is sending the malicious
traffic.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.023.jpg"></div>

Generally speaking there are three categories of connections coming to our routers.

First, there are a "Direct Peering" also called "PNI"
connections. These are the cables that go directly to some other big
internet entity, for example it could be Google, Amazon, Linode or
Digital Ocean.

Second category of cables are the cables that connect us to local
internet exchanges. An internet exchange is a local community of
mostly regional internet service providers. Internet exchanges are run
in major cities and hubs.

Finally, there is the connectivity that connects us to the
internet. We can't reach the public internet over direct peering nor
over local internet exchanges. To send traffic outside of the current
region we need to be connected to an internet carrier, sometimes
called internet transit or upstream. This is a paid service that
allows us to connect to the public internet.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.024.jpg"></div>

Ok, let's start with direct peering. What happens when we see a large
attack coming from the direct peering interface?

This is a simple story. We pick up a phone and call the other
party. There is no further investigation needed, in this case there is
no other internet entity involved. It's clear who sends us the
malicious traffic.

The good news is that in the direct peering case the story mostly
finishes here. It's in the interest of both parties to identify the
attack source and solve the problem. We are directly connected only to
competent internet players, and the communication is usually very
good. Any problems are quickly fixed.

This was easy. How about the other to remaining types of connections?

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.025.jpg"></div>

Unfortunately it's not that simple in the internet exchanges and
internet carriers case. The sad truth is that we can't do anything
about the attack. We have no way to report it and no way to fix it
long term. Let me explain.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.026.jpg"></div>

Let's start with internet exchanges. As I mentioned an internet
exchange is a community of regional ISP's. An exchange is pretty much
a big Layer 2, Ethernet switch. This is a photo of an exchange in
Seattle. As you can see it's a big switch with plenty of Ethernet
cables.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.027.jpg"></div>

These cables go to routers belonging to exchange participants. One of
the cables goes to our router. When we see an attack, from the router
point of view, it would be coming over the internet exchange
interface.

Sadly this is all the router can tell us. The router has no idea who
exactly over the exchange had sent the malicious packets. All we see
is that the packets are delivered via the exchange, no more details.

This is because routers are optimized to do routing packets and look
at IP header. The data on which other party transmitted the packet
over the switch is embedded in Layer 2, the Ethernet frame, but
mainstream routers can't really inspect that.

Unfortunately this means, that when we receive an attack coming from
exchange, there is nothing we can do. We don't know which of the local
ISP's is behind the attack and we don't know who is responsible for
the attack.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.028.jpg"></div>

Ok, how about internet carriers case. Maybe at least they can help us
to identify the attackers. Unfortunately no. Let me show that on a
concrete example.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.029.jpg"></div>

Earlier, in March this year we published a story about particularly
interesting attacks we saw launched against our network. We named the
story "The winter of attacks".

This is the chart we published. It shows inbound traffic on one of our
router interfaces. During the attack this particular router, over this
particular cable received about 80Gbps of attack traffic.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.030.jpg"></div>

The interface in question was connected to our internet carrier in Los
Angeles. We noticed an interesting characteristic of the attack
traffic. The source IP addresses of the packets were set to Hurricane
Electric IP ranges. Hurricane Electric is another big internet
provider.

Looks like Hurricane Electric attacking us, right?


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.031.jpg"></div>

Not in this case. This is because we actually had a direct connection
to Hurricane Electric in this very data center. If the attack was
really launched from HE, it would come over different interface.

While it is technically possible that the attack could have been
originated at HE network, and transmitted over a public internet, it
is highly unlikely. It would have cost them plenty of money and
indicate a fairly broken routing within their network.

What most likely happened, is that one of our internet carriers
customers was spoofing IP addresses and was impersonating HE.

We called up our carrier and explained the situation, but without much
success. They raised two reasons. First, they can't proactively know
that this traffic was indeed spoofed IP traffic. From their point of
view, they are unaware of our direct connectivity to HE and the
traffic might well have been legitimate flowing traffic. Second, they
don't have good insight into their network and they really,
technically, don't know just who of their customers is transmitting
this data.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.032.jpg"></div>

This all leads to a conclusion that in the majority of attacks using IP
spoofing it's impossible to trace back the attacker. It's impossible
to figure out just who sent the malicious traffic.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.033.jpg"></div>

Let's move up to second major argument: that the IP spoofing allows
sophisticated attacks.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.034.jpg"></div>

I'll try to show  three examples of attacks with gradually raising complexity.

Let's start with the details of the "Spamhaus" DNS amplification and
why IP spoofing allowed it.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.035.jpg"></div>

In order to explain amplification, we need to step back first. Let's
talk about a protocol design. Let's imagine a simple request-response
protocol using UDP as the transport layer. The client asks some query,
the server responds with an answer. This is for example how DNS and
NTP works.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.036.jpg"></div>

The idea of amplification comes from abusing this design. The attacker
first fakes the request packet, and tricks the server into treating it
as legitimate request. The server unaware of the real source of the
request, parses it and with all the good will sends the response to
the target. But target never really asked for this data!

This may not sound like something particularly dangerous, until you
realize that it's often the case that the response packet is much
larger than the request!

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.037.jpg"></div>

For example, it's pretty common in DNS protocol that the request is
trivial, consisting of only couple of bytes. While the answer is large
with hundreds of bytes of payload.

This is the idea of amplification. Instead of sending traffic directly
hassling the target it is possible to generate much larger bandwidth
by bouncing out of some server.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.038.jpg"></div>

Bouncing off one server won't generate much load, but in amplification
attacks it's often possible to scale up the attack and use an army of
exposed UDP servers to generate substantial load.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.039.jpg"></div>

And this is exactly what happened in March 2013. Back then we were hit
with very large attacks directed at Spamhaus domains. We estimate that
the attackers had access to three servers with 10Gbps connectivity. In
total they had 30Gbps of IP spoofing capacity. With this they were
able to bounce off the exposed DNS servers on the internet which
generated 300Gbps of traffic hitting our servers.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.040.jpg"></div>

But I'll claim that amplification is not the most sophisticated type
of attacks these days. First, it's fairly easy to block on
firewall. For the DNS amplification it's as simple as blocking
unwanted DNS answers by filtering packets coming from port 53.

Furthermore there are a number of initiatives in the internet that try
to clean up exposed servers that could be used for
amplification. There is `openresolverproject.org` that tracks exposed
DNS resolvers, then there is `openntpproject.org` that looks for
vulnerable NTP servers. And finally there is the `shodan.io` search
engine which scans the internet and is often helping the ISP's to find
servers that could be used for amplification.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.041.jpg"></div>

Let's move on to second attack example. Let's discuss the details of
the "Winter of attacks" that I mentioned before.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.042.jpg"></div>

This time the attacker didn't use any amplification servers, but
instead sent spoofed traffic directly against our servers. The attack
was pretty large.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.043.jpg"></div>

These are the charts we published. In the bottom one you can see
inbound bandwidth, topping at about 400Gbps hitting our servers. On
the top chart you can see the packets per second metric, topping at
150 million packets per second.

You can only imagine what would happen if your servers received 150M
pps. They would most likely boil.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.044.jpg"></div>

Since the attack was sent directly sent against us, the attacker could
choose whatever payload he wanted. The attacker wasn't limited to
crafting DNS or NTP packets.

In this case the attack was composed of SYN packets. SYN floods are
particularly nasty since you can't just block these packets on
firewall. SYN packets are part of the TCP handshake and blocking these
will mean that also valid incoming connections won't work.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.045.jpg"></div>

To be able to distinguish valid from attack packets we need to use
much more precise methods than usual firewalls. We found BPF bytecode
to be a very effective tool for that.

Here on the slide you can see an example Linux firewall `iptables`
rule using a BPF bytecode. BPF is this series of numbers.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.046.jpg"></div>

So what are these numbers? Well, you can decompile them and print them
out as a bytecode. Here's an example view. As you can see this looks
very much like assembler opcodes, it's because it is! With BPF we can
create simple programs and run them within the firewall. This allows
us to perform deep packet inspection and express a fairly
sophisticated filtering logic as the BPF program.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.047.jpg"></div>

We found this method very effective, and we created a couple of
scripts to help us generate BPF bytecodes. We open sourced them, and
you can find this in our "BPF Tools" Github repo.

We have scripts that generate defense BPF's for DNS requests and for
SYN floods. Maybe you will find these useful.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.048.jpg"></div>

Ok, but what about source IP addresses? We've already mentioned that
in this attack we saw packets to be spoofed with Hurricane Electric IP
ranges, but what about other attacks? Is there anything interesting in
the source IP address field?

Let me show you couple of examples of some other attacks we saw recently.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.049.jpg"></div>

Before we go deeper I owe you an explanation of what you will
see. This is a famous XKCD from 2006, when Randall drew a pretty map
of IP addresses. He tried to draw every netblock and name who it
belongs to in a very pretty way. Visualizing IP address space in two
dimensional way is not easy, so Randall didn't drew it
linearly. Instead he used something a Hilbert Curve, which is a fancy
way of drawing numbers, like IP addresses, in such a way that numbers
that seem close to each other in binary code will be drawn close to
each other on the two dimensional map.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.050.jpg"></div>

This is an example of what we saw during one of the attacks. Each
black pixel represents an unique source IP address we saw used in this
particular attack.

As you can see the attack was coming from a number of small "islands"
of IP addresses. Does it mean the IP addresses were spoofed? We can't
say that with confidence.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.051.jpg"></div>

But what we can say is that this is a map of IP ranges belonging to an
ISP called China Telecom.

Once again, previous chart shows IP's used in attack, this one shows
all IP's belonging to CT. What does it say? I don't know. There are
two ways of interpreting this.

One, is that someone has a very large botnet which seems to contain
only devices in China Telecom network, and furthermore it seems the
bots are evenly distributed across the CT IP ranges. This is possible
in theory.

Other interpretation is that someone looked up IP ranges belonging to
CT and spoofed their IP's with uniform probability.

Which one is correct - I can't tell.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.052.jpg"></div>

Let's move on to my favorite example. In this case the attacker was
generating source IP addresses uniformly from the whole IP address
space. From 0.0.0.0 to 255.255.255.255. Including the reserved IP
blocks.

For example in the middle there is a 127.0.0.1 block.

So if you ask us "do you see attacks from localhost?" the answer is:
absolutely! Every other day we see 127.0.0.1 attacking us!

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.053.jpg"></div>

Another one. This time the reserved /8 netblocks were not part of the
attack. But why? I don't know. Either the attacker was smart not to
generate obviously wrong IP addresses, or maybe their ISP just
filtered the invalid /8 blocks for them.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.054.jpg"></div>

Yet another profile, spoofing only bit IP addresses from upper
segment. I'm not sure why this pattern of source IP addresses was
used.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.055.jpg"></div>

And this is my favorite one. On first glance this might look like IP
addresses belonging to some real, potentially big ISP's.  This is how
non-spoofed traffic might have looked like.

But here, this is not the case. In fact, the completely opposite is
the case. What you see here is IP addresses that belong to ranges that
not routable on the public internet. Someone went through quite a bit
of trouble. He had to scrape the public routing tables, figure out
what net blocks are _not_ present in them and only spoof these
IP's. Fairly fancy idea.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.056.jpg"></div>

Let's move on to the last type of attacks I want to mention. The
"Direct subnet" attacks which we only mentioned in June this year.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.057.jpg"></div>

In order to explain the severity of this attacks I first need to
explain the usual mitigation strategy for big attacks.

In a situation that a big attack occurs the administrators of the
target website often have little choice but to remove the target IP
address from the internet.

This is possible via BGP Nullrouting also called Blackholing. BGP is the protocol that internet routers speak to each other.

The problem is that network congestion caused by the attack affects not only the targeted
IP addresses but the whole target network. Sometimes to save the body
you need to sacrifice the limb.

With BGP Null routing it is possible to pretty much remove target IP
address from the internet and therefore relieve the congestion. This
is the tool of last resource.


<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.058.jpg"></div>

In June we saw a very dangerous type of the attack. We saw a big flood
of packets directed against the whole subnet, not against a single
target IP address. This is highly unusual. Normally the attacks target
only a couple addresses.

This is also extremely dangerous. With 255 IP addresses attacked it is
not technically possible to perform null routing. This renders the
DDoS mitigation method of last resort useless.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.059.jpg"></div>

This leads us with a sad conclusion that the only way to survive big
DDoS attacks is to absorb the traffic.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.060.jpg"></div>

The only way to keep services online is to have enough network
capacity to receive the attack. And enough processing power to be able
to process and filter all the packets.

Unfortunately bandwidth and hardware are expensive. Furthermore this
resources will mostly stay idle being utilized only during big attacks.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.061.jpg"></div>

This is a force causing centralization in the internet. In order to
stay online serious websites must use some kind of DDoS mitigation
service. There are only a couple of big such providers on the
internet, and they have enormous leverage.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.062.jpg"></div>

This is not good and I believe it erodes the principles of the
internet. The internet was originally created as a collection of equal
connected peers. Everyone connected had equal rights, could consume
content, produce content.

It was normal to host DNS or HTTP services over your home land-line.

But this is not possible any more. It's just too easy to knock
unprotected websites off line.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.063.jpg"></div>

We described the problem, with a pretty grim look for current state of situation. Is there any way to solve it?

I believe there is.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.064.jpg"></div>

First we need to agree that the technical solutions to solve IP
spoofing had failed. The internet community created the BCP 38
document 16 years ago, and we still have 27% of network providers
allowing IP spoofing.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.065.jpg"></div>

The reality is that we must learn to live in a world where IP spoofing
is an unavoidable fact.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.066.jpg"></div>

I think the internet community tried to solve the wrong problem.

Instead of focusing the efforts on IP spoofing we should have focused
on the attribution. I really don't care what bits are in the source IP
field of the packet. What I want to know is just who is attacking me.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.067.jpg"></div>

I very much would like to get support of internet exchange operators
to help me out and identify which of the connected peers is
transmitting the majority of attack packets.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.068.jpg"></div>

The same goes to internet carriers. I'd like them to contribute and
help with identifying at which of their customers the attack originated.

But how to do this? We've already said that internet carriers often
don't have good insight into their network.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.070.jpg"></div>

Well, they should just use netflow.

Netflow is an awesome protocol supported by all major router vendors.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.071.jpg"></div>

It allows routers to sample the traffic and send sampled data to a
central place, called "collector". With properly configured netflow a
router will report every thousandth, or ten thousandth connection to
the collector.

This data will contain the router port numbers which is precisely what
we need and allow us to answer the question over which interface the
attack entered the carrier network.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.072.jpg"></div>

Netflow is well supported by open source tools. Installing the
collector is as simple as "apt-get install". Netflow scales up well,
it can support very many devices.

Proposing more logging may sound controversial from the privacy point
of view. This is a valid concern, but there are two caveats.

First, netflow allows to set a pretty high sampling rate, with the max
of only one in 64000 connections tracked. This is sampling rate is
absolutely sufficient for the large DDoS reporting use case. The big
attacks will be still clearly visible.

Secondly, there is no need to keep old logs available. For the DDoS
reporting, the logs could be rolled every coupe of days. We really
care only about recent attacks.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.073.jpg"></div>

Here's an example of an `nfdump` command used to query the
collector. Here we ask a question: what attacks were seen in last 5
minutes coming over a specific interface in Warsaw.

You can do much more with `nfdump`. This is just an example.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.074.jpg"></div>

Asking internet carriers to deploy netflow is only the first step. It
won't solve the attacks, they will still be there.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.075.jpg"></div>

But being able to attribute the attacks will at least allow us to
finally have an informed discussion. We can't have it now. We are in
total darkness. Who is behind the attacks? Is that rogue ISP? Is that
a script kiddie with access to couple of beefy hacked servers? Is that
a state actor? We just don't know.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.076.jpg"></div>

This concludes the talk. I hope it was informative.

A quick recap. I believe that the threat of DDoS attacks is one of the
forces causing centralization in the internet.  In order to fix this
we need to fix DDoS. In order to fix the big DDoS attacks we need to
be able to trace back the attacks and pinpoint who is behind them.

<hr><div class="image" style="height:364px"><img style="height:336px;" src="strange-loop3-iwi-09-09.077.jpg"></div>

Hopefully, once we solve the attribution we'll be able to step by step
tackle DDoS and the internet will be better for everyone.

</%block>
