<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


-------------

I've published an article on the CloudFlare blog:

 * [https://blog.cloudflare.com/the-curious-case-of-slow-downloads/](https://blog.cloudflare.com/the-curious-case-of-slow-downloads/)

-------------

<% a = """



The curious case of slow downloads

Some time ago a customer contacted us complaining about a problem with failing slow downloads. Apparently some users were unable to download a few megabyte `mp3` file. The story was simple - the download connection was abruptly closed by our server with an RST packet. After a brief investigation we confirmed the problem. Indeed, somewhere in our stack there was a bug. While describing the problem was simple, fixing it took surprising amount of effort.

In this article I'll describe the problem symptoms, how we reproduced and how we fixed it. Hopefully, by sharing our experiences we will save others from the tedious debugging we had to go through.

Failing downloads
=================

Two things caught our attention in the bug report. First, only users on mobile phones were experiencing the problem. Second, the asset causing issues - an `mp3` file - was pretty large, at around 30 megabytes.

After a fruitful session with `tcpdump` one of our engineers was able to prepare a test case that reproduces the problem. Here you are, reproducing is pretty simple once you know what to look for:

```
$ curl -v http://testcf.com/large.mp3 --limit-rate 10k > /dev/null
* Closing connection #0
curl: (56) Recv failure: Connection reset by peer
```

Poking with `tcpdump` showed there was RST packet coming from our server exactly 60 seconds after the connection was established:

```
$ tcpdump -tttttni eth0 port 80
00:00:00 IP 192.168.1.10.50112 > 1.2.3.4.80: Flags [S], seq 3193165162, win 43690, options [mss 65495,sackOK,TS val 143660119 ecr 0,nop,wscale 7], length 0
...
00:01:00 IP 1.2.3.4.80 > 192.168.1.10.50112: Flags [R.], seq 1579198, ack 88, win 342, options [nop,nop,TS val 143675137 ecr 143675135], length 0

```

Clearly our server is doing something wrong. The RST packet from CloudFlare is just bad. The client behaves, sends ACK packets politely, consumes the data at his own pace, and then we just abruptly cut the conversation.


Not our problem
================

At CloudFlare we are a heavy users of nginx. In order to isolate the problem we set up a basic off-the-shelf nginx server. The issue was easily [reproducible locally](https://github.com/cloudflare/cloudflare-blog/blob/master/2016-03-slow-downloads/nginx.conf):

```
$ curl --limit-rate 10k  localhost:8080/large.mp3 > /dev/null
* Closing connection #0
curl: (56) Recv failure: Connection reset by peer
```

That gets interesting. The problem is not specific to our setup - it is a broader nginx issue!

After some further poking we found two culprits. First, we have been using [`reset_timedout_connection` setting](http://nginx.org/en/docs/http/ngx_http_core_module.html#reset_timedout_connection). This causes nginx to close connections abruptly. It's done by setting `SO_LINGER` without a timeout on a socket, followed by a `close()`. This triggers the RST packet, instead of a usual graceful TCP finalization. Here's an `strace` log from nginx:

```
[pid 127997] 04:50:22 setsockopt(5, SOL_SOCKET, SO_LINGER, {onoff=1, linger=0}, 8) = 0
[pid 127997] 04:50:22 close(5)          = 0
```

We could just disable the `reset_timedout_connection` setting, but that won't solve the underlying problem. Why nginx is closing the connection in the first place?

After further investigation we found [the `send_timeout` configuration option](http://nginx.org/en/docs/http/ngx_http_core_module.html#send_timeout). The default value is 60 seconds, exactly the timeout we saw before.

```
http {
     send_timeout 60s;
     ...
```

The `send_timeout` option is used by nginx to ensure that all connections will eventually drain. It controls the allowed time between successive send/sendfile calls on each connection. Generally speaking it's not fine for a single connection to use precious server resources for too long. If the download is going to too long or is plain stuck, it's okay for the HTTP server to be upset.

But there's more to it.


Not nginx problem either
========================

Armed with `strace` we investigated what nginx actually did:

```
04:54:05 accept4(4, ...) = 5
04:54:05 sendfile(5, 9, [0], 51773484) = 5325752
04:55:05 close(5)          = 0
```

In the config we ordered nginx to use `sendfile` to transmit the data. The call to `sendfile` succeeds and pushes 5MiB of data to the send buffer. This value is interesting - it's about the amount of space we have in our default write buffer setting:

```
$ sysctl net.ipv4.tcp_wmem
net.ipv4.tcp_wmem = 4096        5242880 33554432
```

A minute after the first long `sendfile` the socket is closed. Let's see what happens when we increase the `send_timeout` value to some big value (like 600 seconds):

```
08:21:37 accept4(4, ...) = 5
08:21:37 sendfile(5, 9, [0], 51773484) = 6024754
08:24:21 sendfile(5, 9, [6024754], 45748730) = 1768041
08:27:09 sendfile(5, 9, [7792795], 43980689) = 1768041
08:30:07 sendfile(5, 9, [9560836], 42212648) = 1768041
...
```

After the first large push of data, `sendfile` is called more times. In each of successive runs it transfers about 1.7 MiB. Between these syscalls, during about 180 seconds, the socket was constantly being drained by the slow curl, so why nginx haven't refilled it constantly?

The asymmetry
==============

A motto of Unix design is "everything is a file". I prefer to think about this as: "in Unix everything can be readable and writeable when given to `poll`". But what exactly "being readable" mean? Let's discuss the behavior of network sockets on Linux.

The semantics of reading from a socket are simple:

- Calling `read()` will return the data that is available on the socket, until it's empty.
- `poll` reports the socket as readable when any data is available on it.

One might think this is symmetrical and similar conditions hold for writing to a socket, like this:

- Calling write() will copy data to the write buffer of a socket, up until "send buffer" memory is exhausted.
- `poll` reports the socket is writeable if there is any space available in the send buffer.

Surprisingly, the last point is _not_ true.


Different code paths
==================

It's very important to realize that in Linux Kernel, there are two separate code paths: one for sending data and another one for checking if socket is writeable.

In order for [`send()`](http://lxr.free-electrons.com/source/net/ipv4/tcp.c?v=4.5#L1167) to succeed two conditions must be met:

- There must be [some space available in the send buffer](http://lxr.free-electrons.com/source/include/net/sock.h?v=4.5#L1070).
- The amount of enqueued, not sent, data [must be lower than the LOWAT setting](http://lxr.free-electrons.com/source/include/net/tcp.h?v=4.5#L1691). We will ignore the [LOWAT setting](https://lwn.net/Articles/560082/) in this blog post.

On the other hand, the conditions for socket to reported ["writeable" by `poll`](http://lxr.free-electrons.com/source/net/ipv4/tcp.c?v=4.5#L519) are slightly narrower:

- There must be some space available in the send buffer.
- The amount of enqueued, not sent, data must be lower than  LOWAT setting.
- The amount of [free buffer space](http://lxr.free-electrons.com/source/include/net/sock.h?v4.5#L1079) in the send buffer must be greater than [half of used send buffer space](http://lxr.free-electrons.com/source/include/net/sock.h?v.4.5#L785).

The last condition is critical. This means that after you fill the socket send buffer to 100%, the socket will become writeable again only when it's drained below 66% of send buffer size.

Going back to our nginx, the second `sendfile` we saw:

```
08:24:21 sendfile(5, 9, [6024754], 45748730) = 1768041
```

The call succeeded in sending 1.7 MiB of data. This is close to 33% of 5 MiB, our default `wmem` send buffer size.


I presume this threshold was implemented in Linux in order to avoid refilling the buffers too often. It is undesirable to wake up the sending program after each byte of the data was acknowledged by the client.


The solution
============

With full understanding of the problem we can decisively say what happened:

- In a situation when we filled the send buffer quickly - for example the requested asset was already cached.
- And, the kernel chose the a pretty large send buffer size (like 5 MiB).
- And the customer download speed was slower than 33% of send buffer / 60 seconds.
- Then there was a real chance of nginx resetting the connection.

There are a couple of ways to fix the problem.

One option is to increase the `send_timeout` to, say, 280 seconds. This would ensure that given the default send buffer size, the consumers faster than 50Kibps will never time out.

Another choice is to reduce the `tcp_wmem` send buffers sizes.

Final option is to patch the nginx to react differently on timeout. Instead of closing the connection, we could be inspecting the amount of data remaining in the send buffer. We can do that with `ioctl(TIOCOUTQ)`. With this information we know exactly how quickly the connection is being drained. If it's above some arbitrary threshold, we could decide to grant the connection some more time.


Summary
=======

Linux networking stack is very complex piece of code. While usually it works well, sometimes, it requires some tuning. Even the very experienced programmers don't fully understand all the corner cases. During debugging of this bug we learned that setting timeouts in the "write" path of the code, requires special attention. You can't just treat the "write" timeouts in the same way as "read" time outs.

It was a surprise to me that the semantics of a socket being "writeable" are not symmetrical to the "readable" state. In past [we found that raising receive buffers](https://blog.cloudflare.com/the-story-of-one-latency-spike/) can have unexpected consequences. Now we know tweaking `wmem` values can affect nginx write timeouts.

Tuning a CDN to work well for all the users takes a lot of work. This write up is a result of serious work done by four engineers (special thanks to Chris Branch for working on the Kernel debugging). If this sounds interesting, [consider applying](https://www.cloudflare.com/join-our-team/)!




""" %>

</%block>
