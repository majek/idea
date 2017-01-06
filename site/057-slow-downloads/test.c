#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#define ERRORF(x...) fprintf(stderr, x)

#define FATAL(x...)                                                            \
	do {                                                                   \
		ERRORF("[-] PROGRAM ABORT : " x);                              \
		ERRORF("\n\tLocation : %s(), %s:%u\n\n", __FUNCTION__,         \
		       __FILE__, __LINE__);                                    \
		exit(EXIT_FAILURE);                                            \
	} while (0)

#define PFATAL(x...)                                                           \
	do {                                                                   \
		ERRORF("[-] SYSTEM ERROR : " x);                               \
		ERRORF("\n\tLocation : %s(), %s:%u\n", __FUNCTION__, __FILE__, \
		       __LINE__);                                              \
		perror("      OS message ");                                   \
		ERRORF("\n");                                                  \
		exit(EXIT_FAILURE);                                            \
	} while (0)

static void set_nonblocking(int fd, int nonblock)
{
	int flags, ret;
	flags = fcntl(fd, F_GETFL, 0);
	if (-1 == flags) {
		flags = 0;
	}
	if (nonblock) {
		flags |= O_NONBLOCK;
	} else {
		flags &= ~O_NONBLOCK;
	}
	ret = fcntl(fd, F_SETFL, flags);
	if (-1 == ret) {
		PFATAL("fcntl()");
	}
}

int main() {
	int port = 4444;

	int sd = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (sd < 0) {
		PFATAL("socket()");
	}

	int one = 1;
	int r = setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, (char *)&one,
			   sizeof(one));
	if (r < 0) {
		PFATAL("setsockopt(SO_REUSEADDR)");
	}

	struct sockaddr_in sin4;
	memset(&sin4, 0, sizeof(struct sockaddr_in));
	sin4.sin_family = AF_INET;
	sin4.sin_port = htons(port);

	r = bind(sd, (struct sockaddr*)&sin4, sizeof(struct sockaddr_in));
	if (r < 0) {
		PFATAL("bind()");
		return -1;
	}

	r = listen(sd, 128);
	if (r < 0) {
		PFATAL("listen()");
	}

	int cd = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (cd < 0) {
		PFATAL("socket()");
	}

	set_nonblocking(cd, 1);
	r = connect(cd, (struct sockaddr*)&sin4, sizeof(struct sockaddr_in));
	if (r < 0) {
		if (EINPROGRESS != errno) {
			PFATAL("connect()");
		}
	}

	set_nonblocking(cd, 0);

	int cd2 = accept(sd, NULL, 0);
	if (cd2 < 0) {
		FATAL("accept()");
	}

	int size = 0;
	setsockopt(cd2, SOL_SOCKET, SO_RCVBUF, &size, sizeof(size));

//	set_nonblocking(cd, 1);


#define BUFSZ 1024*4

	char buf[BUFSZ] = {0};

	int tot = 0;
	r = BUFSZ;
	while (r == BUFSZ) {
		fd_set wfds;
		FD_ZERO(&wfds);
		FD_SET(cd, &wfds);

		struct timeval tv = {0,0};
		int rv = select(cd+1, NULL, &wfds, NULL, &tv);

		r = write(cd, buf, BUFSZ);
		if (r >= 0) {
			tot += r;
		}

		printf("wrote=%i total=%i writeable=%i\n",
		       r, tot, FD_ISSET(cd, &wfds));
	}

	return 0;
}
