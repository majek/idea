
${ "###" } Lock #1: pthread_mutex

The first common suspect is a mutex from pthread library. It's not lightweight
and not fast for uncontended cases, but at least it's solid.

```
:::c
static inline void _lock(pthread_mutex_t *lock) {
	pthread_mutex_lock(lock);
}
```

${ "###" } Lock #2: pthread_spinlock

We can notice that our queue algorithm is pretty simple and operations
should finish pretty quickly. Instead of using a heavy mutex, we can
try lightweight spinlocks. But beware, this is good only for
relatively non-contended scenarios, otherwise we may end up spinning a
lot.

```
:::c
static inline void _lock(pthread_spinlock_t *lock) {
	pthread_spin_lock(lock);
}
```

${ "###" } Lock #3: CAS/CAS spinlock

Pthread spinlock's are good, but we can do better! Let's implement
simplest possible spinlocks using previusly mentioned `CAS`
instruction. Locking requires, well, some spinning:

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
```

Unlocking is straightforward:
```
:::c
static inline void _unlock(unsigned int *lock) {
	__sync_bool_compare_and_swap(lock, 1, 0);
}
```

${ "###" } Lock #4: CAS/MEM spinlock

You might have noticed that for unlocking I also used CAS. In fact
that's not neccesarry - we can assert that lock has value `1` and we
can just overwrite it with `0`. For sanity, let's make sure the caches
are synchronized afterwards:

```
:::c
static inline void _unlock(unsigned int *lock) {
	*lock = 0;
	__sync_synchronize();
}
```

That tweak is the last I can tell about optimizing spinlocks. But we
still can do better - by modifying our Queue algorithm.

${ "###" } Lock #4: MEM+CAS/MEM spinlock


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
```



Benchmark
-----------

To benchmark implementations a basic test was created. It's works as
follows:

1. First, we create a queue with `preload` elements enqueued.
* Next, we spawn a number of worker `threads`.
* Every thread repeats in a loop:
    * Enqueue a single element.
    * Dequeue a single element.
* Every thread periodically (around 10HZ) reports the speed of the loop.
* The main program sums up the reports and prints them on the screen
  every second.

First, let's start benchmarking a simplest cases: single thread with a
mostly empty queue and a full queue:

<gnuplot>
size: 500x350
data: |
  0 a 100 10
  1 b 120 14
--
set border 3;
set xtics nomirror;
set ytics nomirror;

set boxwidth 0.5;
set style fill solid;
set yrange [0:140];

unset surface;
unset contour;
set bars 3 front;

plot \
  "data.dat" using 1:3:xtic(2) with boxes title "Rate", \
  "data.dat" using 1:3:4       with yerrorbar title "Error" linewidth 1.2 linetype 7;
</gnuplot>

Let's repeat the benchmark with two threads:

And with four threads (benchmark box has four cores):

| Lock                   | cost |  ABA?   |
|------------------------|------|---------|
| pthread mutex          | xxns |   no    |
| pthread spinlock       | xxns |   no    |
| CAS/CAS spinlock       | xxns |   no    |
| CAS/MEM spinlock       | xxns |   no    |
| MEM + CAS/MEM spinlock | xxns |   no    

Next, 
As a result of all this we get an average:


| Lock                   | cost |  ABA?   | cost     |
|------------------------|------|---------|----------|
| MEM + CAS/MEM spinlock | xxns |   no    | constant |
| mixed                  | xxns |   no    | varies   |

First, header boilerplate:

```
:::c
#define MSQUEUE_POISON1 ((void*)0xCAFEBAB5)

#ifndef _cas
# define _cas(ptr, oldval, newval) ${ "\\" }
         __sync_bool_compare_and_swap(ptr, oldval, newval)
#endif

struct msqueue_head {
	struct msqueue_head *next;
};

struct msqueue_root {
	struct msqueue_head *head;
	struct msqueue_head *tail;

	struct msqueue_head divider;
};

void INIT_MSQUEUE_ROOT(struct msqueue_root *root)
{
	root->divider.next = NULL;
	root->head = &root->divider;
	root->tail = &root->divider;
}
```

So far the code is self-explanatory, only `divider` structure requires
a comment. 

It is added to the queue and behaves as a placeholder in
order to simplify the algorithm by reassuring that the queue will
never be empty.`


Now the interesting part - an `enqueue` function:

```
:::c
void msqueue_put(struct msqueue_head *new,
                 struct msqueue_root *root) {
    struct msqueue_head *tail, *next;
    new->next = NULL;
        
    while (1) {
        tail = root->tail;
        next = tail->next;
        if (tail != root->tail) {
            continue;
        }
        if (next == NULL) {
            if (_cas(&tail->next, next, new)) {
                break;
            }
        } else {
            _cas(&root->tail, tail, next);
        }
    }
    _cas(&root->tail, tail, new);
}
```

And the `dequeue`:
```
:::c
struct msqueue_head *msqueue_get(struct msqueue_root *root){
    struct msqueue_head *head, *tail, *next;
    
    while (1) {
        head = root->head;
        tail = root->tail;
        next = head->next;
        if (head != root->head) {
            continue;
        }
        if (head == tail) {
            if (next == NULL) {
                return NULL;
            }
            _cas(&root->tail, tail, next);
        } else {
            if (_cas(&root->head, head, next)) {
                if (head == &root->divider) {
                    msqueue_put(&root->divider, root);
                    continue;
                }
                head->next = MSQUEUE_POISON1;
                return head;
            }
        }
    }
}

```
https://github.com/majek/libmsock/blob/master/src/msqueue.h


#set key inside right top vertical Right noreverse enhanced autotitles box linetype -1 linewidth 1.000
#set samples 50, 50
#set title "Bragg reflection -- Peak only" 
#set xlabel "Angle (deg)" 
#set ylabel "Amplitude" 
