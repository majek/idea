<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

In [January 2009][1] I was thinking if it is possible to have a
real-time full-text search engine based a simple but scalable
architecture. Basically: is it possible to have:

* a full-text search engine
* able to update indexes in real-time
* horizontally scalalble
* based on simple architecture

After some thinking about the architecture, I came up with the problem
statement:

> Is it possible to build a full-text search engine on a simple
> distributed key-value store?

Let the experiment begin
------------------------

Writing the lexer and basic indexer
[wasn't all that hard](https://github.com/majek/ziutek/blob/e8d79833222953af3e73bd98a5e2d4108a9599ae/ziutek/rtftse.py#L2). But
even though the indexer was written in slow Python, it appeared not to
be the biggest bottleneck.

Building a database layer
-------------------------

After a series of experiments on this design and quickly found out,
that the weakest link was the database layer. Simple indexer was able
to saturate both Tokyo Cabinet and Berkeley DB. Neither behaved nicely
under significant load when the data grew larger then available
memory.

Being a true believer in "not invented here" religion, I decided to
write my own database, specially tuned for this use case. 

Underlying assumptions:

 * Accessed keys have uniform distribution. Probability of accessing
   a single key is equal to any other.
 * When retrieving a key at most a single disk seek should be
   necessary.
 * All writes should be sequential - therefore saving data would
   essentially be free. That implies an append-only log design.
 * Stored data will be significantly larger then available memory.


My first attempt was a rather dumb append-only log database, with an
rb-tree in-memory data structure, of course stolen from Linux kernel.





  [1]: http://www.lshift.net/blog/2009/01/20/my-thoughts-on-real-time-full-text-search


</%block>
</article>
