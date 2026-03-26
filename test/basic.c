#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <wait.h>

int main(int argc, char **argv) {
	sleep(1);
	for (int i = 0; i < 5; i++) {
		sleep(1);
		pid_t pid = fork();
		if (pid == 0) {
			sleep(2);

			if (i == 3) {
				fork();
				sleep(2);
				return 0;
			}
			
			sleep(1);

			return 0;
		}
	}
	
	sleep(1);

	return 0;
}
