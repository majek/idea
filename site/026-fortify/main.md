
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

In recent years Linux distributions started treating security more
seriously. Out of many security features two are directly affecting C
programmers: `-fstack-protector` and `-D_FORTIFY_SOURCE=2`. These GCC
options are now enabled by default on
[Ubuntu](https://wiki.ubuntu.com/Security/Features) and
[Fedora](https://fedoraproject.org/wiki/Security_Features?rd=Security/Features).

What do these options do?


-fstack-protector
---

Consider the following C function:

```c
void fun() {
        char *buf = alloca(0x100);
        /* Don't allow gcc to optimise away the buf */
        asm volatile("" :: "m" (buf));
}
```

Compiled without the
[stack protector](http://www.research.ibm.com/trl/projects/security/ssp/),
with `-fno-stack-protector` option, GCC produces the following assembly:


```s
08048404 <fun>:
  push   %ebp              ; prologue
  mov    %esp,%ebp

  sub    $0x128,%esp       ; reserve 0x128B on the stack
  lea    0xf(%esp),%eax    ; eax = esp + 0xf
  and    $0xfffffff0,%eax  ; align eax
  mov    %eax,-0xc(%ebp)   ; save eax in the stack frame

  leave                    ; epilogue
  ret
```

On the other hand with
[`-fstack-protector`](https://en.wikipedia.org/wiki/Buffer_overflow_protection#GCC_Stack-Smashing_Protector_.28ProPolice.29)
option GCC adds protection code to your functions that use `alloca` or
have buffers larger than 8 bytes. Additional code ensures the stack
did not overflow. Here's the generated assembly:


```s
08048464 <fun>:
  push   %ebp              ; prologue
  mov    %esp,%ebp

  sub    $0x128,%esp       ; reserve 0x128B on the stack

  mov    %gs:0x14,%eax     ; load stack canary using gs
  mov    %eax,-0xc(%ebp)   ; save it in the stack frame
  xor    %eax,%eax         ; clear the register

  lea    0xf(%esp),%eax    ; eax = esp + 0xf
  and    $0xfffffff0,%eax  ; align eax
  mov    %eax,-0x10(%ebp)  ; save eax in the stack frame

  mov    -0xc(%ebp),%eax   ; load canary
  xor    %gs:0x14,%eax     ; compare against one in gs
  je     8048493 <fun+0x2f>
  call   8048340 <__stack_chk_fail@plt>

  leave                    ; epilogue
  ret
```

After a function prologue a canary is loaded and saved into the
stack. Later, just before the epilogue the canary is verified against the
original. If the values don't match the program exits with an appropriate
message.  This can protect against some buffer overflow
attacks. It incurs some
[performance penalty](http://www.research.ibm.com/trl/projects/security/ssp/node5.html)
but it seems to be worth the benefit.

When the stack is overwritten and `__stack_chk_fail` branch is taken
the program crashes with a message like this:


<div class="smallfont"></div>

```txt
*** stack smashing detected ***: ./protected terminated
======= Backtrace: =========
/lib/i386-linux-gnu/libc.so.6(__fortify_fail+0x45)[0xf76da0e5]
/lib/i386-linux-gnu/libc.so.6(+0x10409a)[0xf76da09a]
./protected[0x80484de]
./protected[0x80483d7]
/lib/i386-linux-gnu/libc.so.6(__libc_start_main+0xf3)[0xf75ef4d3]
./protected[0x8048411]
======= Memory map: ========
08048000-08049000 r-xp 00000000 00:13 4058      ./protected
08049000-0804a000 r--p 00000000 00:13 4058      ./protected
0804a000-0804b000 rw-p 00001000 00:13 4058      ./protected
092e5000-09306000 rw-p 00000000 00:00 0         [heap]
f759e000-f75ba000 r-xp 00000000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75ba000-f75bb000 r--p 0001b000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75bb000-f75bc000 rw-p 0001c000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75d5000-f75d6000 rw-p 00000000 00:00 0
f75d6000-f7779000 r-xp 00000000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f7779000-f777b000 r--p 001a3000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f777b000-f777c000 rw-p 001a5000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f777c000-f777f000 rw-p 00000000 00:00 0
f7796000-f779a000 rw-p 00000000 00:00 0
f779a000-f779b000 r-xp 00000000 00:00 0         [vdso]
f779b000-f77bb000 r-xp 00000000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
f77bb000-f77bc000 r--p 0001f000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
f77bc000-f77bd000 rw-p 00020000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
ffeb2000-ffed3000 rw-p 00000000 00:00 0         [stack]
Aborted
```



-D_FORTIFY_SOURCE=2
---

Sample C code:

```c
void fun(char *s) {
        char buf[0x100];
        strcpy(buf, s);
        /* Don't allow gcc to optimise away the buf */
        asm volatile("" :: "m" (buf));
}
```

Compiled without the code fortified, with `-U_FORTIFY_SOURCE` option:

```s
08048450 <fun>:
  push   %ebp               ; prologue
  mov    %esp,%ebp

  sub    $0x118,%esp        ; reserve 0x118B on the stack
  mov    0x8(%ebp),%eax     ; load parameter `s` to eax
  mov    %eax,0x4(%esp)     ; save parameter for strcpy
  lea    -0x108(%ebp),%eax  ; count `buf` in eax
  mov    %eax,(%esp)        ; save parameter for strcpy
  call   8048320 <strcpy@plt>

  leave                     ; epilogue
  ret
```

With `-D_FORTIFY_SOURCE=2`:

```s
08048470 <fun>:
  push   %ebp               ; prologue
  mov    %esp,%ebp

  sub    $0x118,%esp        ; reserve 0x118B on the stack
  movl   $0x100,0x8(%esp)   ; save value 0x100 as parameter
  mov    0x8(%ebp),%eax     ; load parameter `s` to eax
  mov    %eax,0x4(%esp)     ; save parameter for strcpy
  lea    -0x108(%ebp),%eax  ; count `buf` in eax
  mov    %eax,(%esp)        ; save parameter for strcpy
  call   8048370 <__strcpy_chk@plt>

  leave                      ; epilogue
  ret

```

You can see GCC generated some additional code. This time instead
of calling `strcpy(dst, src)` GCC automatically calls
`__strcpy_chk(dst, src, dstlen)`. With
[`FORTIFY_SOURCE`](http://gcc.gnu.org/ml/gcc-patches/2004-09/msg02055.html)
whenever possible GCC tries to uses buffer-length aware replacements
for functions like `strcpy`, `memcpy`, `memset`, etc.

Again, this prevents some buffer overflow attacks. Of course you should avoid
`strcpy` and always use `strncpy`, but it's worth noting that
FORTIFY_SOURCE can also help with `strncpy` when GCC knows the
destination buffer size. For example:

```c
void fun(char *s, int l) {
	char buf[0x100];
	strncpy(buf, s, l);
	asm volatile("" :: "m" (buf[0]));
}
```

Here GCC instead of calling `strncpy(dst, src, l)` will call
`__strncpy_chk(dst, src, l, 0x100)` as GCC is aware of the size of the
destination buffer.

When the buffer is overrun the program fails with a message very
similar to the one seen previously. Instead of "stack smashing
detected" you'll see "buffer overflow detected" headline:

<div class="smallfont"></div>
```txt
*** buffer overflow detected ***: ./fortified terminated
======= Backtrace: =========
/lib/i386-linux-gnu/libc.so.6(__fortify_fail+0x45)[0xf76d30e5]
/lib/i386-linux-gnu/libc.so.6(+0x102eba)[0xf76d1eba]
/lib/i386-linux-gnu/libc.so.6(+0x1021ed)[0xf76d11ed]
./fortified[0x8048488]
./fortified[0x80483a7]
/lib/i386-linux-gnu/libc.so.6(__libc_start_main+0xf3)[0xf75e84d3]
./fortified[0x80483e1]
======= Memory map: ========
08048000-08049000 r-xp 00000000 00:13 4208      ./fortified
08049000-0804a000 r--p 00000000 00:13 4208      ./fortified
0804a000-0804b000 rw-p 00001000 00:13 4208      ./fortified
08d6b000-08d8c000 rw-p 00000000 00:00 0         [heap]
f7597000-f75b3000 r-xp 00000000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75b3000-f75b4000 r--p 0001b000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75b4000-f75b5000 rw-p 0001c000 08:01 161528    /lib/i386-linux-gnu/libgcc_s.so.1
f75ce000-f75cf000 rw-p 00000000 00:00 0
f75cf000-f7772000 r-xp 00000000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f7772000-f7774000 r--p 001a3000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f7774000-f7775000 rw-p 001a5000 08:01 161530    /lib/i386-linux-gnu/libc-2.15.so
f7775000-f7778000 rw-p 00000000 00:00 0
f778f000-f7793000 rw-p 00000000 00:00 0
f7793000-f7794000 r-xp 00000000 00:00 0         [vdso]
f7794000-f77b4000 r-xp 00000000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
f77b4000-f77b5000 r--p 0001f000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
f77b5000-f77b6000 rw-p 00020000 08:01 161542    /lib/i386-linux-gnu/ld-2.15.so
fff8d000-fffae000 rw-p 00000000 00:00 0         [stack]
Aborted
```


</%block>
