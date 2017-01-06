#include <arpa/inet.h>
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

#define PFATAL(x...)                                                           \
	do {                                                                   \
		ERRORF("[-] SYSTEM ERROR : " x);                               \
		ERRORF("\n\tLocation : %s(), %s:%u\n", __FUNCTION__, __FILE__, \
		       __LINE__);                                              \
		perror("      OS message ");                                   \
		ERRORF("\n");                                                  \
		exit(EXIT_FAILURE);                                            \
	} while (0)

static int do_bind(const char *addr, int port) {
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

	struct in_addr in_addr;
	r = inet_pton(AF_INET, addr, &in_addr);
	if (r != 1){
		PFATAL("pton()");
	}

	struct sockaddr_in sin4;
	memset(&sin4, 0, sizeof(struct sockaddr_in));
	sin4.sin_family = AF_INET;
	sin4.sin_port = htons(port);
	sin4.sin_addr = in_addr;

	r = bind(sd, (struct sockaddr*)&sin4, sizeof(struct sockaddr_in));
	if (r < 0) {
		PFATAL("bind()");
		return -1;
	}

	r = listen(sd, 128);
	if (r < 0) {
		PFATAL("listen()");
	}

	return sd;
}

#define LIMIT 14000
int main() {
	int port = 10064;

	printf("[*] Binding %d sockets on port %d\n", LIMIT, port);
	int count = 0;
	int a;
	int b;
	for (a = 0; a < 255; a++) {
		for (b = 1; b < 255; b++) {
			char addr[32];
			snprintf(addr, sizeof(addr),
				 "127.0.%d.%d", a, b);
			do_bind(addr, port);

			count += 1;
			if (count > LIMIT) {
				break;
			}
		}
	}

	printf("[*] Bound. Waiting\n");
	while (1) {
		sleep(100);
	}

	return 0;
}
