
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

In recent years Linux distributions started treating security more
seriously. Out of many security features two are directly affecting C
programmers: `-fstack-protector` and `-D_FORTIFY_SOURCE=2` GCC options
are enabled by default on
[Ubuntu](https://wiki.ubuntu.com/Security/Features) and
[Fedora](https://fedoraproject.org/wiki/Security_Features?rd=Security/Features).

What these options do?


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
with `-fno-stack-protector` option yields:


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

On the other hand here's the assembly with `-fstack-protector`:

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

[GCC's Stack protector](https://en.wikipedia.org/wiki/Buffer_overflow_protection#GCC_Stack-Smashing_Protector_.28ProPolice.29)
can protect against certain buffer overflow vulnerabilities. It does
incur some
[performance penalty](http://www.research.ibm.com/trl/projects/security/ssp/node5.html)
but it seems to be worth the benefit.


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

As you can see, instead of calling `strcpy(dst, src)` GCC
automatically calls `__strcpy_chk(dst, src, dstlen)`. This makes
perfect sense and again, prevents some buffer overflow attacks. Of
course you should avoid `strcpy` and always use `strncpy`, but it's
worth noting that FORTIFY_SOURCE can also help with `strncpy`. For
example:

```c
void fun(char *s, int l) {
	char buf[0x100];
	strncpy(buf, s, l);
	asm volatile("" :: "m" (buf[0]));
}
```

In this case GCC instead of calling `strncpy(dst, src, l)` will call
`__strncpy_chk(dst, src, l, 0x100)`. Basically - with FORTIFY_SOURCE
enabled if GCC knows the size of the buffer, it'll try to make sure
you don't run over.



</%block>
