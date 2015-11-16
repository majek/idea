<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">

I attempted to write my own OS. Not really. I just tried to figure out
how can I mock a few basic syscalls. File access is pretty simple to
emulate. Basic network functions - not hard either. But with network
sockets comes socket multiplexing - select(2) is the simplest variant.

Implementing select() is pretty tricky.

Actually, the problem is not in the select() semantics. It lies much
deeper in the Unix architecture, which assumes everything is a file
descriptor.


What I want to express:
 - when an a packet arrives on this particular socket, please tell me about it.

What unix gives me is:
 - My process is in Runnable state. Don't tell me nothing.
 - Oh, I'm done, here's a select(). Now, do you have anything for me on each of these N file descriptors?

The difference in performance is gigantic. 

Four states:
 1) drained producer, no consumer
 2) producer has data, no consumer
 3) drained producer, consumer waiting
 4) producer has data, consumer waiting

In unix the file descriptor constantly flips between 1. and
3. states. First state is when no poll is waiting, and 3rd is when the
program hooks the select().

This


</%block>
