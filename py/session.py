from collections import namedtuple
import asyncio
import os
import time

ForkEvent = namedtuple('ForkEvent', ['time', 'parent_pid', 'child_pid'])

class Branch:
    def __init__(self, parent, pid, start_time, end_time):
        self.parent = parent
        self.pid = pid
        self.start_time = start_time
        self.end_time = end_time
        self.children = []

class TraceSession:
    def __init__(self, root_pid, poll_interval=0.5):
        self.root = Branch(None, root_pid, 0, None)
        self.time_offset = time.time()
        self.branches = {root_pid: self.root}
        self.active_pids = set([root_pid])
        self.poll_interval = poll_interval

        self.started = False
        self._check_task = None
    
    def add_fork(self, parent_pid, child_pid):
        fork_time = time.time() - self.time_offset
        parent_branch = self.branches.get(parent_pid)

        if parent_branch is None:
            print(f"Warning: Parent PID {parent_pid} not found in branches")
            return
        
        self.active_pids.add(child_pid)
        branch = Branch(parent_branch, child_pid, fork_time, None)
        parent_branch.children.append(branch)
        self.branches[child_pid] = branch

        print(f"{fork_time:.4f}s | Fork event - parent PID={parent_pid}, child PID={child_pid}")

        self._check_active()

    def end_branch(self, pid):
        branch = self.branches.get(pid)
        if branch:
            branch.end_time = time.time() - self.time_offset
            self.active_pids.discard(pid)
            print(f"{branch.end_time:.4f}s | Process {pid} ended")

    def get_duration(self):
        if self.active_pids:
            return time.time() - self.time_offset
        else:
            return max(branch.end_time for branch in self.branches.values() if branch.end_time is not None)

    def _check_active(self):
        # Loop through a copy of active PIDs and check
        # that the processes are still running
        # If not, end their branches
        for active_pid in list(self.active_pids):
            if not os.path.exists(f"/proc/{active_pid}"):
                print(f"Process {active_pid} is no longer active, ending branch")
                self.end_branch(active_pid)

    async def _periodic_check(self):
        while self.active_pids:
            self._check_active()
            await asyncio.sleep(self.poll_interval)
    
    async def wait(self):
        self._check_task = asyncio.create_task(self._periodic_check())
        try:
            await self._check_task
        except asyncio.CancelledError:
            pass