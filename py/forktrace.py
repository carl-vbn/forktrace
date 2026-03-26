import argparse
import os
import asyncio
import pathlib
import signal
import struct

from graph import print_graph
from session import TraceSession

LIBPATH = "/home/carl-vbn/dev/forktrace/c/libforktrace.so"

session = None

async def handle_client(reader, writer):
    while True:
        data = await reader.read(8)
        if not data:
            break
        pid, cpid = struct.unpack("ii", data)

        if cpid == -1:
            session.end_branch(pid)
        else:
            session.add_fork(pid, cpid)
    writer.close()
    await writer.wait_closed()

async def create_socket():
    if 'XDG_RUNTIME_DIR' in os.environ:
        path = pathlib.Path(os.environ['XDG_RUNTIME_DIR']) / f"forktrace-{os.getpid()}.sock"
    else:
        path = pathlib.Path(f"/tmp/forktrace-{os.getpid()}.sock")

    server = await asyncio.start_unix_server(handle_client, path=str(path))
    return server, path

async def run_command(command, sock_path):
    env = os.environ.copy()
    env["LD_PRELOAD"] = LIBPATH
    env["FT_SOCK"] = str(sock_path)
    process = await asyncio.create_subprocess_exec(*command, env=env)
    return process

async def main():
    global session

    parser = argparse.ArgumentParser(
        description="Trace fork calls when running a command",
        add_help=False
    )
    parser.add_argument("--help", action="help", help="Show this help message and exit")
    parser.add_argument("-s", "--graph-step", type=float, default=None, help="Time step in seconds for graph rows")
    parser.add_argument("-i", "--poll-interval", type=float, default=0.5, help="Interval in seconds for polling active processes")
    parser.add_argument("-h", "--max-graph-height", type=int, default=None, help="Maximum height of the graph in rows")
    parser.add_argument("-t", "--timeout", type=float, default=None, help="Timeout in seconds before forcefully terminating the traced command")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The command to run and trace")
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    server, sock_path = await create_socket()
    print(f"Socket created at {sock_path}")

    process = await run_command(args.command, sock_path)
    session = TraceSession(process.pid, poll_interval=args.poll_interval)

    # Handle SIGINT: the child is in the same process group and already receives
    # SIGINT from the terminal, so we just ignore it in the parent to stay alive
    # long enough to print the graph after the child exits.
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: None)

    async with server:
        await server.start_serving()
        print("Server started, waiting for client connections...")

        if args.timeout is not None:
            try:
                await asyncio.wait_for(
                    asyncio.gather(session.wait(), process.wait()),
                    timeout=args.timeout
                )
            except asyncio.TimeoutError:
                print(f"Timeout after {args.timeout}s, terminating traced command")
                process.kill()
                await process.wait()
                await session.wait()
        else:
            await asyncio.gather(
                session.wait(),
                process.wait()
            )

        server.close()
        await server.wait_closed()
        print("All traced processes have terminated.")

    max_graph_height = args.max_graph_height
    if max_graph_height is None and args.graph_step is None:
        max_graph_height = 20

    print_graph(session, step=args.graph_step, max_height=max_graph_height)

    # Cleanup
    try:
        os.remove(sock_path)
    except OSError:
        pass

if __name__ == "__main__":
    asyncio.run(main())
