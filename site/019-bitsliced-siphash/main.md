<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>


Few days ago
[I presented a Python and a C implementation of SipHash](/2013-01-24-siphash/). This
time for no reason whatsoever I implemented a bitsliced version of it.

[Bitslicing](https://en.wikipedia.org/wiki/Bit_slicing) a crypto
algorithm is usually done to speed it up when doing massively parallel
operations. For example when trying to find a collision with brute
force. Bitsliced implementation is only useful if you have a large
number of exactly the same mathematical operations to be computed in
parallel.

Let me try to describe how bitslicing works.

Intro to bitslicing
----

In essence to bitslice an algorithm is to rewrite it in a lowest
possible level, using simplest logical operations on every bit of the
input. The idea is to perform those simple computations on large
number of bits in parallel using long SIMD vectors.

For example, say we define a mathematical function that does a
bitwise `or` on two 4 bit variables. Our non-bitsliced function will
look like:

```c
u4 formula_raw(u4 a, u4 b) {
    return a | b;
}
```

Now, if we have 256 different inputs we'd need to call this function
256 times to generate all the results.

An simplistic illustration of two calls to our formula:

<dot>
digraph {
        node [shape="record"];

        d [label="{d3|d2|d1|d0}"];
        e [label="{e3|e2|e1|e0}"];
        f [label="{f3|f2|f1|f0}"];

        a [label="{a3|a2|a1|a0}"];
        b [label="{b3|b2|b1|b0}"];
        c [label="{c3|c2|c1|c0}"];


	a -> b [label="OR", color=transparent];
	b -> c [label="=", color=transparent];
	d -> e [label="OR", color=transparent];
	e -> f [label="=", color=transparent];
}
</dot>


On the other hand a bitsliced version will look like:

```c
void formula_bs(vec dst[4], vec a_bits[4], vec b_bits[4]) {
    unsigned bit_no;
    for (bit_no = 0; bit_no < 4; bit_no ++) {
        dst[bit_no] = a_bits[bit_no] | b_bits[bit_no];
    }
}
```

Where `a_bits[0]` is a vector (say an
[`avx` 256-bit wide](https://en.wikipedia.org/wiki/Advanced_Vector_Extensions)
register) that contains all zeroth bits of our 256 inputs `a`, `a_bits[1]`
contains all first bits, and so on.

To count all 256 outputs we need to call the function only once as it
operates on 256 bit vectors already.

Illustration of the bitsliced version of our formula:
<dot>
digraph {
        node [shape="record"];

	a3 [label="{a3|d3}"];
	b3 [label="{b3|e3}"];
	c3 [label="{c3|f3}"];
	a3 -> b3 [label="OR", color=transparent];
	b3 -> c3 [label="=", color=transparent];

	a2 [label="{a2|d2}"];
	b2 [label="{b2|e2}"];
	c2 [label="{c2|f2}"];
	a2 -> b2 [label="OR", color=transparent];
	b2 -> c2 [label="=", color=transparent];

	a1 [label="{a1|d1}"];
	b1 [label="{b1|e1}"];
	c1 [label="{c1|f1}"];
	a1 -> b1 [label="OR", color=transparent];
	b1 -> c1 [label="=", color=transparent];

	a0 [label="{a0|d0}"];
	b0 [label="{b0|e0}"];
	c0 [label="{c0|f0}"];
	a0 -> b0 [label="OR", color=transparent];
	b0 -> c0 [label="=", color=transparent];

}
</dot>

As you can see, we need a single `or` operation for every bit of
the input, which is constant.

To give you an approximation of the benefit - on my i7 CPU counting
our function on 256 inputs took 506 cycles for the normal
implementation and only 39 cycles for the bitsliced one (see
[the sources of the test](https://github.com/majek/dump/blob/master/bitslice/main.c)).

The hidden cost
----

There is a major cost in practical usage of bitslicing - it is
neccesary to pass bit vectors as the input, not the `a` and `b` the
end user cares about. This is not hard - all is needed is a bit matrix
transposition. Unfortunately, although SSE instruction
`PMOVMSKB`/`_mm_movemask_epi8` helps a lot, it's computationally
expensive.

To illustrate the transposition for our formula: two 4-bit inputs are
transposed into four 2-bit vectors, one for each bit:


<dot>
digraph {
        node [shape="record"];

subgraph cluster_a{
        a [label="{a3|a2|a1|a0}"];
        d [label="{d3|d2|d1|d0}"];
}

subgraph cluster_b{
	a0 [label="{a0|d0}"];
	a1 [label="{a1|d1}"];
	a2 [label="{a2|d2}"];
	a3 [label="{a3|d3}"];
}

a -> a1 [label="", color=transparent];
d -> a1 [label="transpose to", color=transparent];
}
</dot>


On my i7 CPU it takes around 1040 CPU cycles to transpose 8x256 bit
matrix. We need three transpositions for our `or` formula (two for
inputs, and one to decipher the output), that's 3120 cycles for
transpositions only. Bear in mind - I didn't optimise
[the transposition code, just borrowed it from Mischasan](http://mischasan.wordpress.com/2011/10/03/the-full-sse2-bit-matrix-transpose-routine/).

Rewriting SipHash
---

The whole fun in playing with bitslicing is to rewrite a non-trivial
algorithm in terms of bitwise operations.

Let's focus on the core of the SipHash - a single "round".

Here's a half-round of SipHash from [my non-bitsliced code](https://github.com/majek/csiphash/blob/master/csiphash.c):

```
#define ROTATE(x,b) ${ "\\" }
    (u64)( ((x) << (b)) | ( (x) >> (64 - (b))) )

#define HALF_ROUND(a,b,c,d,s,t)     ${ "\\" }
    a += b;                         ${ "\\" }
    b = ROTATE(b, s) ^ a;           ${ "\\" }
    a = ROTATE(a, 32);              ${ "\\" }
    c += d;                         ${ "\\" }
    d = ROTATE(d, t) ^ c;
```

Nothing fancy. Just some bit rotations, two additions and two `xor`
operations. It's worth noting that SipHash state is encapsulated in
four 64 bit variables `a` - `d`.

In the bitsliced implementation we'll be using
[`gcc` vector notation](http://gcc.gnu.org/onlinedocs/gcc/Vector-Extensions.html),
based on 256 bit vectors. Being an optimist I assume the compiler can
take advantage of `avx`.

First, let's define the vector type and constants:

```c
/* 32 bytes, that's 256 bits and 4*8 u64 values */
typedef uint64_t vec __attribute__ ((vector_size (32)));
const vec zero = {0ULL, 0ULL, 0ULL, 0ULL};
const vec one = {0xffffffffffffffffULL,
                 0xffffffffffffffffULL,
                 0xffffffffffffffffULL,
                 0xffffffffffffffffULL};
```

Now, let's define an addition operation bitwise. That takes three
inputs - `carry`, `a` and `b` and returns new `carry` and the result.

Following [the adder logic gate schema](http://en.wikipedia.org/wiki/Adder_(electronics)):

<div class="image" style="height:168px;"><img src="adder.svg" height="155px"></div>

our function requires 5 operations:

```
/* Add with carry */
#define ADD(a, b, out, carry_in, carry_out)
        do {
                vec __a = a, __b = b;
                vec _axb = __a ^ __b;
                out = carry_in ^ _axb;
                carry_out = (_axb & carry_in) | (__a & __b);
        } while (0)
```



Having that we can implement the half-round of SipHash:

```
#define M(e) (e) & 0x3f
#define HALF_ROUND(a,b,c,d, s,t, _a,_b,_c,_d)
        do {
                unsigned o;
                vec tmp, carry;
                carry = zero;
                for (o = 0; o < 64; o++) {
                        ADD(a[o], b[o], tmp, carry, carry);
                        _a[M(o-32)] = tmp;
                        _b[o] = b[M(o-s)] ^ tmp;
                }
                carry = zero;
                for (o = 0; o < 64; o++) {
                        ADD(c[o], d[o], tmp, carry, carry);
                        _c[o] = tmp;
                        _d[o] = d[M(o-t)] ^ tmp;
                }
        } while (0)
```

Where `a` - `d` vectors are inputs and `_a` - `_d` are used for
storing the results.

Notice we don't need rotate operations - instead we just address
different bit in a vector: `_a[M(o-32)]` instead of `_a[o]`.

Complexity
---

Normally a half-round of SipHash requires:

 * 2 additions
 * 2 xors
 * 3 bit rotations

That's 1792 operations to count 256 inputs.

The bitsliced code on the other hand does:

 * 64 * 2 additions, 5 operations each
 * 64 * 2 xors

That's 768 operations to count 256 inputs.

In order to compute a full SipHash function one needs to run at least
twelve half-rounds.


Results
---

Unfortunately in the end
[my bitsliced implementation](https://github.com/majek/bitsliced-siphash)
is slower:

* The cost of transposing inputs for the bitsliced algorithm is
  significant.
* Bitsliced algorithm uses two sets of four vectors 256x64
  bits. That's 16KiB of internal state! I'm afraid it may not fit
  into the CPU registers.


On my i7 CPU computing 256 SipHash hashes the normal implementation
requires about:

    computation:  9768 cycles

Compiled with `clang` and `avx` extensions the bitsliced code runs in:

    computation: 11278 cycles
    transpose:   13900 cycles

In other words - even if we ignore the cost of transposition the code
still runs a bit slower than the non-parallelised version. With hand
crafted assembler we should be able to do better.

Most crucially: first I need to work on reducing the cost of the bit
transposition!


The code used in this article:

 - [benchmarking bitsliced OR formula](https://github.com/majek/dump/tree/master/bitslice)
 - [bitsliced SipHash in C](https://github.com/majek/bitsliced-siphash)


</%block>
</article>
