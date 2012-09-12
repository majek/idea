bMixed approach
--------------

We've exhausted the blocking queue algorithm, we've decided the `CAS`
queue is inpractical. But we can try a mixed approach.

As mentioned above, `CAS` is pretty bad when used to pick up the items
from the queue - they could be freed already. But `CAS` is good when
putting things onto the queue - when we don't need to dereference
anything.

Let's give it a try and let's not worry about the ordering put things
onto a stack, like this:

<dot>
digraph {
        node [shape="record"];
        
subgraph cluster_a{
        a [label="{value C|<1>next}"];
        b [label="{value B|<1>next}"];
        c [label="{value A|<1>next = NULL}"];
        
}
subgraph cluster_b{
        head [label="{head}"];
}

        head -> a:0;
        a:1 -> b;
        b:1 -> c;
}
</dot>

```
:::c
void msqueue_put(struct msqueue_head *new,
                 struct msqueue_root *root)
{
        while (1) {
                struct msqueue_head *tail = root->tail;
                new->next = tail;
                if (_cas(&root->tail, tail, new)) {
                        break;
                }
        }
}

```

The problem now, is how to pop things from the queue. First, instead
of getting a single item, let's just take the ownership of the whole
stack:

```
:::c
        while (1) {
                struct msqueue_head *tail = root->tail;
                if (!tail) { // Stack is empty
                        break;
                }
                if (_cas(&root->tail, tail, NULL)) {
                        ... we own the stack now ...
                        break;
                }
        }
```


| Algorithm | Lock                   | cost |  ABA?   |
|-----------|------------------------|------|---------|
| Lock      | CAS/MEM spinlock       | xxns |   no    |
| Mixed     | CAS + CAS/MEM spinlock | xxns | suffers |
