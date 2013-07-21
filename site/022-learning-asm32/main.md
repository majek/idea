<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

It's a bit embarrassing but I never fully understood how the stack in
x86 works. Sure, I know the stack grows downwards, the top is saved in
`%esp` and `%ebp` points somewhere. But I didn't know exactly
why. During [Hacker School](https://www.hackerschool.com/) I wrote a
bit of assembly that finally gave me a better intuition, maybe it can
help you as well.

Prerequisites
---

I'm assuming you already know basic assembler instructions, you're
aware of registers and have a clue about the stack.

${ "###" } Syntax

There are two flavours of the assembler syntax:
[Intel](https://en.wikibooks.org/wiki/X86_Disassembly/Assemblers_and_Compilers#Intel_Syntax_Assemblers)
and
[AT&T](https://en.wikibooks.org/wiki/X86_Disassembly/Assemblers_and_Compilers#.28x86.29_AT.26T_Syntax_Assemblers). I'm
a Linux guy so I'll be using AT&T. This:

```
::text
    mov %eax, %edx
```

reads:

```
    move EAX to EDX
```

(the word "to" is the important part)


${ "###" } Calling convention

We'll be writing code for Unix and the
[calling convention is `cdecl`](http://en.wikipedia.org/wiki/X86_calling_conventions#cdecl).
A quick reminder how it works:

 * Callee can do whatever it wants with: `%eax`, `%ecx`, `%edx`,
   `eflags`, `%st0-7`, `%mm0-7`, `%xmm0-7`.
 * Callee must preserve other registers: `%ebx`, `%ebp`, `%esp`, `%esi`, `%edi`.

Remember, callee must restore stack pointers `%ebp` and `%esp`.

Simplest function
---

Let's start by writing a simplest possible function
([code](https://github.com/majek/baby-steps-in-assembly/blob/master/step1/asm.S)):

```.S
ENTRY(simplest_function)
        ret
```

ENTRY macro declares a global a symbol - a function symbol in our
case, and the function does only one thing - it exits.

Congratulations. We just created a valid x86 function in assembler!
It can now be called from a C code:

```.c
int main() {
	simplest_function();
	return 0;
}

```

Task for you: run it. You can follow the instructions:

```
$ git clone https://github.com/majek/baby-steps-in-assembly.git
$ cd baby-steps-in-assembly/step1
$ make
$ ./step1
[.] Calling simplest_function()
[.] It worked!
```

Disassembling
---

Instead of describing what happened, let me show you a a useful Linux
tool: [`objdump`](http://linuxcommand.org/man_pages/objdump1.html). You can use it as a disassembler and see how our
function looks in the compiled executable:

```
$ objdump  -d step1|awk '/simplest_function>:/,/ret/'
08048420 <_simplest_function>:
 8048420:       c3                      ret
```

There isn't anything surprising, exactly as we wrote it. Let's now see
the code in `main` that calls the `simplest_function`:

```
$ objdump  -d step1|awk '/main>:/,/ret/'
080483d4 <main>:
 80483d4: 55               push   %ebp
 80483d5: 89 e5            mov    %esp,%ebp
 80483da: 83 ec 10         sub    $0x10,%esp
 ...
 80483e9: e8 32 00 00 00   call 8048420 <_simplest_function>
 ...
 80483ff: c9               leave
 8048400: c3               ret
```

That's a bit more involved, fortunately now we're interested only in
this line:

```
 80483e9: e8 32 00 00 00   call 8048420 <_simplest_function>
```

This is the code that calls our function. It uses the `call`
instruction. Basic operation of `call` is quite simple, it calculates
the `%eip` of next instruction, puts it on the stack and jumps to the
function pointer from the parameter. It assumes the function will exit
using `ret`.

(I was asked to mention that neither
[`call`](http://pdos.csail.mit.edu/6.828/2008/readings/i386/CALL.htm)
nor
[`ret`](http://pdos.csail.mit.edu/6.828/2008/readings/i386/RET.htm)
are really "simple".)

Dissecting call and ret
---

Now time for something unusual. In order to understand what `call`
actually does, let's try to emulate it with simpler primitives ([code](https://github.com/majek/baby-steps-in-assembly/blob/master/step2/asm.S)):

```
::text
ENTRY(call_hack)
        push $_next_instruction # Push the address of the
                                # instruction following
                                # our emulated `call`
        jmp simplest_function   # Jump to the called function
_next_instruction:              # And we're back!
        ret
```

That's pretty much what `call` does.

How about `ret`? It pops a return address from the stack (that was put
there by a `call`) and jumps to it. We can "improve" our
`simplest_function` with the verbose version of `ret`:

```
ENTRY(simplest_function_ret_hack)
        pop %eax
        jmp *%eax
```

Don't you trust me it actually works? Try it yourself:

```
$ cd ../step2
$ make
$ ./step2
[.] Calling call_hack()
[.] It worked!
```

(Hint: try running `objdump` with options `-M intel` and `-S`.)

Function parameters
---

In cdecl function parameters are passed on the stack. Here's an
example function. Declaration in C:

```.c
int square_int(int v);
```

And implementation in assembler ([code](https://github.com/majek/baby-steps-in-assembly/blob/master/step3/asm.S)):

```.S
ENTRY(square_int)
    mov 4(%esp), %eax    # pick up the parameter
    imul %eax, %eax
    ret
```

Why 4? Well, 4 recent most bytes on the stack are the return
instruction pointer pushed there by the `call`, so the parameters is
4 bytes above that.

The return value is passed in `%eax`.

Building a stack frame
---

Who needs a stack frame anyway? Let's start simple - say we wanted to
use `%ebx` for our computation. But we can't just modify it - it needs
to be preserved. To save it we can push it on the stack:

```
ENTRY(square_int_ebx)
    push %ebx
    mov $0, %ebx         # say we need %ebx
    mov 8(%esp), %eax    # pick up the parameter with
                         # adjusted location
    imul %eax, %eax
    pop %ebx             # restore %ebx
    ret
```

Overwriting `%ebx` is a bit artificial here, but note that now the
parameter is no longer 4 bytes above `%esp`. In fact it's 8 bytes as
we pushed 4 more bytes on the stack. As the functions get more complex
there is no way to remember an offset of a particular
parameter. Fortunately there's a better method: we should keep the
initial stack frame address in `%ebp` and address the parameters
always in relatively to `%ebp`. That way we won't be affected by how
many bytes are allocated on stack at any time.

```
::text
ENTRY(square_int_stack_frame)
    push %ebp           # preserve %ebp
    mov %esp, %ebp      # top of the stack is now in %ebp
                        # now we can push as many things
                        # on the stack and still address the
                        # parameter as 8(%ebp)
    sub $16, %esp       # we can for reserve few bytes
                        # for the stack frame, and push
    push $0xDEADBEEF    # anything on the stack

    mov 8(%ebp), %eax   # a parameter relative to %ebp
    imul %eax, %eax

    mov %ebp, %esp      # we need to restore original %esp
    pop %ebp            # and %ebp
    ret
```

That's better. Now it we can grow and push and pop elements from the
stack, modify `%esp` and that won't change the way we address the
parameters as they will always be addressed relative to `%ebp`.

Prologue and epilogue
---

Code responsible for preparing a stack frame is called a
[function prologue](https://en.wikipedia.org/wiki/Function_prologue)
and for destroying it
[an epilogue](https://en.wikipedia.org/wiki/Function_epilogue#Epilogue).

Crafting a frame that way is so common that x86 has a shortcut
instructions: `enter` and `leave`.

```
ENTRY(square_int_enter)
    enter $16, $0

    mov 8(%ebp), %eax
    imul %eax, %eax

    leave
    ret
```

It's worth noting that `enter` is rarely used in practice
- it's slower than the `push/mov/sub` equivalent. `Leave` on the other
hand is used relatively often (see
[AMD Optimization Guide, p. 64](http://support.amd.com/us/Processor_TechDocs/40546.pdf)).

Finally, to run all four variants:

```
$ cd ../step3
$ make
$ ./step3
[.] Calling square_int()
[.] Calling square_int_ebx()
[.] Calling square_int_stack_frame()
[.] Calling square_int_enter()
[.] It worked!
```

</%block>
