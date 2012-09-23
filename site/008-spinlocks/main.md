<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

In the previous article I was playing with
[the implementation of the concurrent Queue in C](/2012-09-11-concurrent-queue-in-c/).

During the experiments I tried to outsmart `pthread` library and beat
the speed of their spinlock implementation.

CAS/CAS
-------

My first attempt was to use compare-and-swap `CAS` instruction for the
spinlock. Here's the code, basically we spin till the lock is acquired:

```
:::c
static inline void _lock(unsigned int *lock) {
    while (1) {
        int i;
        for (i=0; i < 10000; i++) {
            if (__sync_bool_compare_and_swap(lock, 0, 1)) {
                return;
            }
        }
        sched_yield();
    }
}

static inline void _unlock(unsigned int *lock) {
        __sync_bool_compare_and_swap(lock, 1, 0);
}
```

This approach works well, but we can still do better.

([full code](https://github.com/majek/dump/blob/master/msqueue/queue_lock_myspinlock1.c))

CAS/store
---------

It's easy to notice that the `unlock` doesn't actually need the heavy
`CAS` write. We know that the value in the lock must be 1 and we can
just unconditionally write 0.

```
:::c
static inline void _unlock(unsigned int *lock) {
	__asm__ __volatile__ ("" ::: "memory");
	*lock = 0;
}
```

The asm line is required to prevent GCC from reordering the
write. Additionally, in x86 the stores aren't reordered, but in other
architectures a write barrier might be required above the assignment.


([full code](https://github.com/majek/dump/blob/master/msqueue/queue_lock_myspinlock2.c))

Benchmark
---------

I used the
[benchmark](https://github.com/majek/dump/blob/master/msqueue/main.c)
from [previous blog post](/2012-09-11-concurrent-queue-in-c/) to get
the numbers. Beware, the locks are only a fraction of the measured
complexity in these benchmarks.

The numbers for four threads spinning on four cores (ie: contended case):

<gnuplot>
size: 500x350
data: |
 0 0     799 883 838 816
 1 2     727 825 806 780 
 2 8     694 790 785 758
 3 16    693 783 756 733
 4 256   679 755 731 686
 5 4096  641 760 708 696
 6 65536 660 754 752 719
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;
set yrange [0:1000];
set xrange [-0.5:6.5];

set xlabel "queue size"
set ylabel "ns"

unset surface;
unset contour;
set bars 3 front;

plot \
  "data.dat" using 1:3:xtic(2) with lines title "spinlock", \
  "data.dat" using 1:4:xtic(2) with lines title "cas/cas", \
  "data.dat" using 1:5:xtic(2) with lines title "cas/store";
</gnuplot>

And a single thread (uncontended case):
<gnuplot>
size: 500x350
data: |
 0 0     50 80 47
 1 2     34 55 32
 2 8     29 47 27
 3 16    28 45 26
 4 256   26 43 25
 5 4096  26 43 24
 6 65536 38.9 48 43 41
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;
set yrange [0:100];
set xrange [-0.5:6.5];

set xlabel "queue size"
set ylabel "ns"

unset surface;
unset contour;
set bars 3 front;

plot \
  "data.dat" using 1:3:xtic(2) with lines title "spinlock", \
  "data.dat" using 1:4:xtic(2) with lines title "cas/cas", \
  "data.dat" using 1:5:xtic(2) with lines title "cas/store";
</gnuplot>

The `CAS/store` method is as fast as pthread implementation of
spinlocks. That's nothing really surprising considering that pthread
also uses the same approach
([source](https://github.com/lattera/glibc/blob/master/nptl/sysdeps/x86_64/pthread_spin_trylock.S)).

So now you know how to implement reasonable spinlocks. This may come
handy for example when you're writing for a platform with glibc that
doesn't have `pthread_spin_lock`, like Mac OS X. Here's the shim for
that case:

```
:::c
int pthread_spin_init(pthread_spinlock_t *lock, int pshared) {
    __asm__ __volatile__ ("" ::: "memory");
    *lock = 0;
    return 0;
}

int pthread_spin_destroy(pthread_spinlock_t *lock) {
    return 0;
}

int pthread_spin_lock(pthread_spinlock_t *lock) {
    while (1) {
        int i;
        for (i=0; i < 10000; i++) {
            if (__sync_bool_compare_and_swap(lock, 0, 1)) {
                return 0;
            }
        }
        sched_yield();
    }
}

int pthread_spin_trylock(pthread_spinlock_t *lock) {
    if (__sync_bool_compare_and_swap(lock, 0, 1)) {
        return 0;
    }
    return EBUSY;
}

int pthread_spin_unlock(pthread_spinlock_t *lock) {
    __asm__ __volatile__ ("" ::: "memory");
    *lock = 0;
    return 0;
}
```
([full source](https://github.com/majek/dump/blob/master/msqueue/pthread_spin_lock_shim.h))

Alternatively, [ConcurrencyKit](http://concurrencykit.org) is a high-quality library that provides loads of concurrency primitives, including spinlocks:

* [http://concurrencykit.org/doc/ck_spinlock.html](http://concurrencykit.org/doc/ck_spinlock.html)

</%block>
</article>
