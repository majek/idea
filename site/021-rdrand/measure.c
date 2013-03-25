#include <stdio.h>
#include <stdint.h>

#ifdef __i386__
#  define RDTSC_DIRTY "%eax", "%ebx", "%ecx", "%edx"
#elif __x86_64__
#  define RDTSC_DIRTY "%rax", "%rbx", "%rcx", "%rdx"
#else
# error unknown platform
#endif

#define RDTSC_START(cycles)						\
	do {								\
		register unsigned cyc_high, cyc_low;			\
		asm volatile("CPUID\n\t"				\
			     "RDTSC\n\t"				\
			     "mov %%edx, %0\n\t"			\
			     "mov %%eax, %1\n\t"			\
			     : "=r" (cyc_high), "=r" (cyc_low)		\
			     :: RDTSC_DIRTY);				\
		(cycles) = ((uint64_t)cyc_high << 32) | cyc_low;	\
	} while (0)

#define RDTSC_STOP(cycles)						\
	do {								\
		register unsigned cyc_high, cyc_low;			\
		asm volatile("RDTSCP\n\t"				\
			     "mov %%edx, %0\n\t"			\
			     "mov %%eax, %1\n\t"			\
			     "CPUID\n\t"				\
			     : "=r" (cyc_high), "=r" (cyc_low)		\
			     :: RDTSC_DIRTY);				\
		(cycles) = ((uint64_t)cyc_high << 32) | cyc_low;	\
	} while(0)

int main() {
	int i;
	unsigned min = 0xffffffff;
	for (i=0; i< 10000; i++) {
		uint64_t c0, c1;
		RDTSC_START(c0);
		RDTSC_STOP(c1);
		if (min > c1-c0)
			min = c1-c0;
	}
	printf("%u\n", min);
	return 0;
}
