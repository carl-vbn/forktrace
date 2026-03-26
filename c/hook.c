// log_fork.c
#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>

int open_ft_socket() {
    const char *sock_path = getenv("FT_SOCK");
    if (!sock_path) {
        fprintf(stderr, "FTRACE_SOCK not set\n");
        return -1;
    }

    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return -1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(struct sockaddr_un));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, sock_path, sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(struct sockaddr_un)) < 0) {
        perror("connect");
        close(sock);
        return -1;
    }

    return sock;
}

int send_fork_event(pid_t cpid) {
    int sock = open_ft_socket();
    if (sock < 0) {
        return -1;
    }

    // Send current pid to the socket
    pid_t ppid = getpid();
    if (send(sock, &ppid, sizeof(ppid), 0) < 0) {
        perror("send");
        close(sock);
        return -1;
    }

    // Send the cpid to the socket
    if (send(sock, &cpid, sizeof(cpid), 0) < 0) {
        perror("send");
        close(sock);
        return -1;
    }

    // Close the socket
    close(sock);
    return 0;
}

// Detect program termination
__attribute__((destructor))
void cleanup() {
    int sock = open_ft_socket();
    if (sock < 0) {
        return;
    }

    // Send current pid
    pid_t ppid = getpid();
    if (send(sock, &ppid, sizeof(ppid), 0) < 0) {
        perror("send");
    }

    // Send termination event (cpid = -1)
    pid_t term_event = -1;
    if (send(sock, &term_event, sizeof(term_event), 0) < 0) {
        perror("send");
    }

    close(sock);
}

// Override fork function
pid_t fork(void) {
    static pid_t (*real_fork)(void) = NULL;
    if (!real_fork)
        real_fork = dlsym(RTLD_NEXT, "fork");

    pid_t result = real_fork();
    
    if (result > 0) {
        // Fork succeeded
        // Send the fork event to the socket
        if (send_fork_event(result) < 0) {
            fprintf(stderr, "[forktrace] Failed to send fork event\n");
        }
    }

    return result;
}

