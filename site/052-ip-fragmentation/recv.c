


#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netinet/in.h>
#include <netinet/ip.h> /* superset of previous */
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>
       #include <linux/errqueue.h>

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

#define NSEC_TIMEVAL(ns)                                                       \
	(struct timeval)                                                       \
	{                                                                      \
		(ns) / 1000000000ULL, ((ns) % 1000000000ULL) / 1000ULL         \
	}
#define MSEC_NSEC(ms) ((ms)*1000000ULL)

struct net_addr
{
	int ipver;
	struct sockaddr_in sin4;
	struct sockaddr_in6 sin6;
	struct sockaddr *sockaddr;
	int sockaddr_len;
};

void net_gethostbyname(struct net_addr *shost, const char *host, int port)
{
	memset(shost, 0, sizeof(struct net_addr));

	struct in_addr in_addr;
	struct in6_addr in6_addr;

	/* Try ipv4 address first */
	if (inet_pton(AF_INET, host, &in_addr) == 1) {
		goto got_ipv4;
	}

	/* Then ipv6 */
	if (inet_pton(AF_INET6, host, &in6_addr) == 1) {
		goto got_ipv6;
	}

	FATAL("inet_pton(%s)", host);
	return;

got_ipv4:
	shost->ipver = 4;
	shost->sockaddr = (struct sockaddr *)&shost->sin4;
	shost->sockaddr_len = sizeof(shost->sin4);
	shost->sin4.sin_family = AF_INET;
	shost->sin4.sin_port = htons(port);
	shost->sin4.sin_addr = in_addr;
	return;

got_ipv6:
	shost->ipver = 6;
	shost->sockaddr = (struct sockaddr *)&shost->sin6;
	shost->sockaddr_len = sizeof(shost->sin6);
	shost->sin6.sin6_family = AF_INET6;
	shost->sin6.sin6_port = htons(port);
	shost->sin6.sin6_addr = in6_addr;
	return;
}

struct net_addr *net_parse_addr(const char *addr)
{
	struct net_addr *netaddr = calloc(1, sizeof(struct net_addr));
	char *colon = strrchr(addr, ':');
	int port = atoi(colon + 1);
	if (port < 0 || port > 65535) {
		FATAL("Invalid port number %d", port);
	}
	char host[255];
	int addr_len = colon - addr > 254 ? 254 : colon - addr;
	strncpy(host, addr, addr_len);
	host[addr_len] = '\0';
	net_gethostbyname(netaddr, host, port);
	return netaddr;
}

int net_connect_udp(struct net_addr *shost)
{
	int sd = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (sd < 0) {
		PFATAL("socket()");
	}

	int one = 1;
	int r = setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, (char *)&one,
			   sizeof(one));
	if (r < 0) {
		PFATAL("setsockopt(SO_REUSEADDR)");
	}

	/* one =  1; */
	/* r = setsockopt(sd, IPPROTO_IP, IP_RECVERR, &one, sizeof(one)); */
	/* if (r != 0) { */
	/* 	perror("setsockopt(SOL_IP, IP_RECVERR)"); */
	/* } */

	/* socklen_t l = sizeof(one); */
	/* r = getsockopt(sd, IPPROTO_IP, IP_RECVERR, &one, &l); */
	/* if (r != 0) { */
	/* 	perror("setsockopt(SOL_IP, IP_RECVERR)"); */
	/* } */

	/* struct net_addr *bb = net_parse_addr("0.0.0.0:0"); */

        /* r = bind(sd, bb->sockaddr, bb->sockaddr_len); */
	/* if (r != 0) { */
	/* 	perror("bind()"); */
	/* } */

	if (-1 == connect(sd, shost->sockaddr, shost->sockaddr_len)) {
		/* is non-blocking, so we don't get error at that point yet */
		if (EINPROGRESS != errno) {
			PFATAL("connect()");
			return -1;
		}
	}

	return sd;
}

void handle_read(int fd) {
	char bufx[16];
	int r = recv(fd, bufx, sizeof(bufx), MSG_DONTWAIT);
	printf("recv=%d\n",r);

	uint8_t buf[2048];

	struct iovec iovec = {
		.iov_base = buf, .iov_len = sizeof(buf),
	};

	uint8_t control[2048];

	struct sockaddr_in remote;
	memset(&remote, 0, sizeof(remote));

	struct msghdr msg = {
		.msg_name = &remote,
		.msg_namelen = sizeof(remote),
		.msg_iov = &iovec,
		.msg_iovlen = 1,
		.msg_control = &control,
		.msg_controllen = sizeof(control),
		.msg_flags = 0,
	};

	r = recvmsg(fd, &msg, MSG_ERRQUEUE | MSG_DONTWAIT);
	if (r < 0) {
		perror("recvmsg(MSG_ERRQUEUE)");
	} else {
		if (r == 0) {
			fprintf(stderr, "no MSG_ERRQUEUE data\n");
		} else {
			printf("MSG_ERRQUEUE something %d!\n", r);
		}
		if (msg.msg_flags & MSG_ERRQUEUE) {
			struct cmsghdr *c;

			for (c = CMSG_FIRSTHDR(&msg); c; c = CMSG_NXTHDR(&msg, c)) {
				if (c->cmsg_level == IPPROTO_IP && c->cmsg_type == IP_RECVERR) {
					struct sock_extended_err *ee = (struct sock_extended_err *)CMSG_DATA(c);
					//struct sockaddr_in *from = (struct sockaddr_in *)SO_EE_OFFENDER(ee);
					if (ee->ee_origin == SO_EE_ORIGIN_ICMP) {
						printf("ICMP type=%u code=%u\n",
						       ee->ee_type, ee->ee_code);
					} else {
						printf("not icmp\n");
					}
				} else {
					printf("not error?\n");
				}
			}
		} else {
			printf("not MSG_ERRQUEUE msg\n");
		}

	}
}



int main(int argc, char **argv)
{
	if (argc != 2){
		fprintf(stderr, "%s target_ip:port\n", argv[0]);
		return -1;
	}

	char buf[600-44+48];
	memset(buf, 'B', sizeof(buf));

	struct net_addr *target = net_parse_addr(argv[1]);
	int fd = net_connect_udp(target);

	int r;
	int on = 1;
	/* on = 1; */
	/* r = setsockopt(fd, IPPROTO_IP, IP_RECVERR, &on, sizeof(on)); */
	/* if (r != 0) { */
	/* 	perror("setsockopt(SOL_IP, IP_RECVERR)"); */
	/* } */

	on = IP_PMTUDISC_DONT;
	r = setsockopt(fd, IPPROTO_IP, IP_MTU_DISCOVER, &on, sizeof(on));
	if (r != 0) {
		perror("setsockopt(SOL_IP, IP_MTU_DISCOVER");
	}

	while (1) {
		int v = 0;
		unsigned vl = sizeof(v);
		int r = getsockopt(fd, SOL_IP, IP_MTU, &v, &vl);
		if (r != 0) {
			perror("getsockopt(MTU)");
		}
		printf("MTU: %d\n", v);

		/* r = sendto(fd, buf, sizeof(buf), MSG_DONTWAIT, target->sockaddr, target->sockaddr_len); */
		r = send(fd, buf, sizeof(buf), 0);
		if (r < 0) {
			perror("send()");
		}

		fd_set efds;
		FD_ZERO(&efds);
		//FD_SET(fd, &efds);

		struct timeval timeout = NSEC_TIMEVAL(MSEC_NSEC(1000));

		while (1) {
			r = select(fd+1, &efds, NULL, NULL, &timeout);

			char bb[16];
			recv(fd, &bb, sizeof(bb), MSG_DONTWAIT);

			if (r < 0) {
				perror("select()");
			} else if (r == 0) {
				break;
				// pass
			} else {
				handle_read(fd);
			}
		}
	}

	return 0;
}
