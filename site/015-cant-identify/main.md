<%inherit file="basecomment.html"/>

<article>
<%block filter="filters.markdown">

[SockJS-node](https://github.com/sockjs/sockjs-node) users noticed
that the server seems to be leaking file descriptors when websockets
are enabled. The problem resulted in the usual `EMFILE - Too many open
files` crash.

Additionally, `lsof` was producing weird output, with `can't identify
protocol` line instead of a normal tcp/ip description.

Where it should say something like:

```
$ lsof -p <pid>
 PID  USER  FD  TYPE DEVICE SIZE/OFF   NODE NAME
25590 marek 11u IPv4 837984      0t0    TCP localhost:9918->localhost:53833 (CLOSE_WAIT)
```

it said:

```
 PID  USER  FD  TYPE DEVICE SIZE/OFF   NODE NAME
25548 marek 12u sock    0,7      0t0 837659 can't identify protocol
```

The issue was hard to track, but eventually
[Yury Michurin](https://github.com/yurynix)
[found a culprit](https://github.com/sockjs/sockjs-node/issues/99#issuecomment-11084738). It
was a
[`faye-websocket-node`](https://github.com/faye/faye-websocket-node)
library which seems to be leaking sockets in `CLOSED` state but didn't
close them.

Yury was able to notice this behaviour because `netstat` have reported
those forgotten sockets as `CLOSED` on Freebsd. On the other hand,
`netstat` on Linux just doesn't report the sockets at all, making it
impossible to debug the issue.

I was able to reproduce this `lsof` issue with this script - the socket needs to be in
a half-closed state:

```
::python
import socket
import os
import sys

PORT = 9918

sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sd.bind(('0.0.0.0', PORT))
sd.listen(5)

for i in range(10):
    if os.fork() == 0:
        sd.close()
        cd = socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM)
        cd.connect(('127.0.0.1', PORT))
        sys.exit()

print "Server process pid=%i" % (os.getpid(),)
sockets = []
for i in range(10):
    (cd, address) = sd.accept()
    sockets.append(cd)
    cd.shutdown(socket.SHUT_WR)

os.system("lsof -p %i" % (os.getpid(),))
#os.system("netstat -nt|grep :%i" % (PORT,))
```

On Ubuntu this script prints:

```
$ python lsof-issue.py 
Server process pid=26023
COMMAND   PID  USER   FD   TYPE DEVICE SIZE/OFF   NODE NAME
[...]
python  26023 marek    3u  IPv4 841027      0t0    TCP *:9918 (LISTEN)
python  26023 marek    4u  sock    0,7      0t0 841031 can't identify protocol
python  26023 marek    5u  sock    0,7      0t0 841032 can't identify protocol
python  26023 marek    6u  sock    0,7      0t0 841033 can't identify protocol
python  26023 marek    7u  sock    0,7      0t0 841034 can't identify protocol
python  26023 marek    9u  sock    0,7      0t0 841038 can't identify protocol
python  26023 marek   10u  sock    0,7      0t0 841039 can't identify protocol
python  26023 marek   11u  sock    0,7      0t0 841040 can't identify protocol
python  26023 marek   12u  sock    0,7      0t0 841042 can't identify protocol
python  26023 marek   13u  sock    0,7      0t0 841044 can't identify protocol
python  26023 marek   14u  sock    0,7      0t0 841046 can't identify protocol
```

Unfortunately, it looks like kernel removes all information about
these sockets from `/proc/net/*`, `lsof` is not able to get any
details about them and panics.


</%block>
</article>
