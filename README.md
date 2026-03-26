# Forktrace

A Linux tool that traces and visualizes `fork()` calls when running a command, producing an ASCII timeline of the process tree.

## How It Works

Forktrace uses `LD_PRELOAD` to inject a small C shared library (`libforktrace.so`) into the target process. This library intercepts `fork()` calls and reports parent/child PID pairs back to a Python server over a Unix domain socket. The server builds a process tree and renders it as an ASCII graph when the command finishes.

## Building the C shared library

```bash
cd c && make
```

Requires GCC and Python 3. Linux only (relies on `LD_PRELOAD` and `/proc`).

## Usage

```bash
python py/forktrace.py [OPTIONS] <command>
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-s, --graph-step` | Time step per graph row (seconds) | auto |
| `-i, --poll-interval` | Process polling interval (seconds) | 0.5 |
| `-h, --max-graph-height` | Maximum graph height (rows) | 20 |
| `-t, --timeout` | Kill traced command after N seconds | — |

### Example

```bash
python py/forktrace.py -s 1 test/basic
```

Output:

```
Socket created at /run/user/1000/forktrace-17839.sock
Server started, waiting for client connections...
2.0013s | Fork event - parent PID=17841, child PID=17854
3.0018s | Fork event - parent PID=17841, child PID=17862
4.0023s | Fork event - parent PID=17841, child PID=17863
5.0021s | Process 17854 ended
5.0025s | Fork event - parent PID=17841, child PID=17864
6.0024s | Process 17862 ended
6.0028s | Fork event - parent PID=17841, child PID=17865
7.0029s | Process 17863 ended
7.0032s | Fork event - parent PID=17864, child PID=17882
Process 17841 is no longer active, ending branch
7.0033s | Process 17841 ended
7.0033s | Process 17841 ended
9.0035s | Process 17864 ended
9.0036s | Process 17865 ended
9.0036s | Process 17882 ended
All traced processes have terminated.

    PID | 17841   17865   17864   17882   17863   17862   17854   
  0.00s | ┬                                                       
  1.00s | │                                                       
  2.00s | ├───────────────────────────────────────────────┐       
  3.00s | ├───────────────────────────────────────┐       │       
  4.00s | ├───────────────────────────────┐       │       │       
  5.00s | ├───────────────┐               │       │       ┴       
  6.00s | ├───────┐       │               │       ┴               
  7.00s | ┴       │       ├───────┐       ┴                       
  8.00s |         │       │       │                               
  9.00s |         ┴       ┴       ┴                               
 10.00s | 
```
