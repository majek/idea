<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

Starting from scratch is hard, it's much easier just to continue. With that
in mind, allow me to keep on writing, in the same fashion as
[my previous blog](http://blogger.popcnt.org/).

And what a blog that was.

My last post on ["Majek's technical blog"](http://blogger.popcnt.org/)
is two years old but surprisingly some content haven't aged that
much. Just to name a few:

 * [Predictions on Google future](http://blogger.popcnt.org/2007/09/die-google-future-search-engines.html)
 * [Thoughts on social networks](http://blogger.popcnt.org/2007/06/my-theory-about-future-of-web.html)
 * A lot of low-level network hacks: [icmp](http://blogger.popcnt.org/2007/07/is-it-possible-to-abuse-icmp.html), [URG Tcp/Ip flag](http://blogger.popcnt.org/2007/07/what-happened-to-tcp-flag-urgent-msgoob.html), [dirty Tcp/Ip tricks invented by Van Jacobsen's](http://blogger.popcnt.org/2007/04/magia-w-tcpip-linuxa-bug-czy-ficzer.html) or [detecting network cards in promiscous mode](http://blogger.popcnt.org/2007/07/pcap-support-for-nmap-script-engine.html).


</%block>
</article>
