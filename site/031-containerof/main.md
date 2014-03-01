
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

Golang ships with a linked list[^1] data structure:
[`container/list`](http://golang.org/pkg/container/list/).

[The implementation](http://golang.org/src/pkg/container/list/list.go)
is great and simple but it suffers an interesting problem: adding a
value to a list requires a memory allocation.

Let me explain.


[^1]: What programming languages don't ship with an implementation of
a linked list?

Broadly speaking a linked list can be implemented in one of two ways:

1. The list can hold a reference to the item. Let's call that an "external"
 implementation.  The item ("Alice von Wonderland" in our
 example) doesn't have any knowledge of the list.  <dot> digraph { node
 [shape="record"];

subgraph cluster_a{
       a [label="{<2>*value|<1>*next}"];
       b [label="{<2>*value|<1>NULL}"];
       first [label="*head"];
}

aa [label="{{<1>Alice|von Wonderland}}"];
bb [label="{{<1>Rabbit|the White}}"];

first -> a:0;
a:1 -> b;
a:2 -> aa:1
b:2 -> bb:1
}
</dot>

2. Or the item can hold all data required for list bookkeeping. Let's
 call this an "internal" implementation, as the list specific data is
 embedded within the item.  <dot> digraph { node [shape="record"];

subgraph cluster_a{
        aa [label="{{<1>*next|Alice|von Wonderland}}"];
        bb [label="{{<1>NULL|Rabbit|the White}}"];
        first [label="*head"];
}

first -> aa:1;
aa:1 -> bb:1;
}
</dot>




Subtle difference
---

Golang uses the first "external" method. It naturally expresses
encapsulation as the item doesn't need to have any knowledge of the
container.

Traversing a list feels natural, it just requires casting an
abstract interface to a specific item type, for example:

```.go
type Item struct {
	...
}
a := &Item{}
list.PushFront(a)

for el := list.Front(); el != nil; el = el.Next(){
    item := el.Value.(ItemType) // a simple cast
    ...
}
```

But, as you can see on the diagram above, that method requires
allocating an additional "list element" object for every item present
in the list.


The second "internal" method avoids that but compromises on
encapsulation: all fields required for list bookkeeping need to be
stored as a part of the item.

Traversing such a list a bit more complex - given a pointer to
"element", which is a field on the item structure, it's not trivial to
recover a pointer to the item. Linux Kernel uses a `container_of`
macro for that, you can often see code like this:

```.c
struct itemtype {
    struct list_head in_list;
    ...
}

struct list_head *element;
list_for_each(element, &list) {
    struct itemtype *item = ${"\\"}
        container_of(element, struct itemtype, in_list);
    ...
}
```

Greg Kroah-Hartman wrote
[an explanation of the `container_of` macro](http://www.kroah.com/log/linux/container_of.html).

The unsafe hack
----

It is possible to achieve a similar thing in Golang. The `unsafe`
module can be used to emulate the `container_of`
trick. [Here's a rough example](http://play.golang.org/p/8cs0Wu2PdG):

```.golang
type Item struct {
    el linkedListElement
    ...
}

a := &Item{value: "Alice"}
el := &a.el

recoveredA := (*Item)(unsafe.Pointer(
    uintptr(unsafe.Pointer(el)) - unsafe.Offsetof(tmpItem.el)))
```

Adapting container/list
----

This is a pretty complex and an error prone technique. It's simpler to
avoid using the `unsafe` package and adapt the standard
`container/list` code.

Normally the `container/list` always allocates a fresh "element"
object when an item is added to a list. This is fairly easy to fix,
it's enough to add a method that can recycle an "element"
object. These three lines do the trick:

```.golang
func (l *list) PushElementFront(e *element) *element {
	return l.insert(e, &l.root)
}
```

Having that method you can embed a `list.Element` structure in the
item, and use code like this to traverse a list:

```.go
type Item struct {
	element list.Element
	...
}

a := &Item{}
a.element.Value = a

list.PushElementFront(&a.element)

for el := list.Front(); el != nil; el = el.Next(){
    item := el.Value.(Item)
    ...
}
```

Although it's a bit wasteful, as every item holds a full
`list.Element` structure, this method is fairly simple and doesn't
require the additional memory allocation.

To avoid using the `unsafe` module `item.element.Value` needs to point
to `item` itself, which is a bit weird:

<dot>
digraph {
        node [shape="record"];
subgraph cluster_a{
        aa [label="{{{{<1>*next|<2>*Value}}|Alice|von Wonderland}}"];
}
aa:2 -> aa:1
}
</dot>



Measuring the problem
------

The additional memory allocation as done by default `container/list` is
not a big problem if the list doesn't have many entries. It starts to
be painful if your program is storing a high number of elements in a
linked list, for example if you have a large LRU cache used in your
program.

Keep in mind that in a garbage collected language allocating more
objects can increase the cost of a GC run.


Let me back this claim with some
evidence. [I wrote](https://github.com/majek/dump/blob/master/containerlist)
two implementations of an LRU cache in Go:

 - ["external"](https://github.com/majek/dump/blob/master/containerlist/external.go) is using off-the-shelf `container/list` package
 - ["internal"](https://github.com/majek/dump/blob/master/containerlist/internal.go) using modified implementation on the list package, as shown above

I executed the code like this:
```.bash
$ go build .
$ sort /usr/share/dict/*-english | ./containerlist
```

Here you can see the value of
[`runtime.HeapObjects`](http://golang.org/pkg/runtime/#MemStats)
metric on Y axis and the runs of the program main loop as the X
axis. Drop in the value of HeapObjects indicates a GC cycle. As
expected "internal" code allocates less objects.

<gnuplot>
size: 600x550
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;

set xlabel "Input lines"
set ylabel "HeapObjects"

set xrange [0:2000];


unset surface;
unset contour;
set bars 3 front;
plot \
    "loge.tsv" using 1:4 with dots title "external (red)",\
    "logi.tsv" using 1:4 with dots title "interal (green)"
</gnuplot>

Next metric is the `runtime.NumGC`. It shows the count of garbage
colection cycles. Over long time the "external" code will trigger
lower number of garbage collection runs.

<gnuplot>
size: 600x550
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;

set xlabel "Input lines"
set ylabel "NumGC"

set xrange [0:20000];
;# set yrange [660000:820000];

delta_v1(x) = ( vD = x - old_v1, old_v1 = x, vD)
old_v1 = NaN

delta_v2(x) = ( vD = x - old_v2, old_v2 = x, vD)
old_v2 = NaN

inms(x) = ( x / 1000000000000000.0)


unset surface;
unset contour;
set bars 3 front;

<%
#plot \
#    "logi.tsv"  using 1:(delta_v1($8)) with lines title "interal", \
#    "loge.tsv"  using 1:(delta_v2($8)) with lines title "external";
%>

plot \
    "loge.tsv"  using 1:8 with lines title "external (red)",\
    "logi.tsv"  using 1:8 with lines title "interal (green)";
</gnuplot>

The next chart below shows the `runtime.PauseTotalNs` metric, a
cumulative duration of all GC runs. Although "external" code triggers
lower number of GC cycles, it still spends more time in the GC
cumulatively than the "internal" code.

<gnuplot>
size: 600x550
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;

set xlabel "Input lines"
set ylabel "PauseTotal (ms)"

set xrange [0:20000];
;#set yrange [660000:820000];

delta_v1(x) = ( vD = x - old_v1, old_v1 = x, vD)
old_v1 = NaN

delta_v2(x) = ( vD = x - old_v2, old_v2 = x, vD)
old_v2 = NaN


inms(x) = ( x / 1000000.0)


unset surface;
unset contour;
set bars 3 front;

<%
#plot \
#    "logi.tsv"  using 1:(delta_v1($8)) with lines title "interal", \
#    "loge.tsv"  using 1:(delta_v2($8)) with lines title "external";
%>

plot \
    "loge.tsv"  using 1:(inms($15)) with lines title "external (red)",\
    "logi.tsv"  using 1:(inms($15)) with lines title "interal (green)";
</gnuplot>


Wrap up
---

In a garbage collected language it's important keep the allocated
objects count as low as possible. It's a pity Golang doesn't support
the "internal" linked lists by default. We've shown how this can be
worked around and how to measure the gains.


</%block>
