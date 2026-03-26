import shutil
from session import TraceSession
import math

def build_ordered_branches(branch):
    ordered = [branch]
    for child in sorted(branch.children, key=lambda b: -b.start_time):
        ordered.extend(build_ordered_branches(child))
    return ordered

def count_coincident_forks(session: TraceSession, step: float):
    # Count the number of forks that fall within the same row as at least one other fork
    # and the number of branches that start and end within the same row
    time_buckets = {}
    num_coincidents = 0

    for branch in session.branches.values():
        if branch.start_time is not None:
            bucket = int(branch.start_time // step)
            if bucket in time_buckets:
                time_buckets[bucket].append(branch)
                if len(time_buckets[bucket]) == 2:  # Count only when we have at least 2 forks in the same bucket
                    num_coincidents += 1
            else:
                time_buckets[bucket] = [branch]

            if branch.end_time is not None and branch.start_time // step == branch.end_time // step:
                num_coincidents += 1

    return num_coincidents

def auto_step_size(session: TraceSession, min_height, max_height, min_coincidents=None):
    # Base case
    if min_height >= max_height or max_height - min_height < 2:
        return session.get_duration() / max_height

    if min_coincidents is None:
        min_coincidents = count_coincident_forks(session, step=session.get_duration() / math.ceil(max_height))
    
    mid_height = (min_height + max_height) // 2
    num_coincidents = count_coincident_forks(session, step=session.get_duration() / math.ceil(mid_height))

    if num_coincidents > min_coincidents:
        return auto_step_size(session, mid_height, max_height, min_coincidents)
    else:
        return auto_step_size(session, min_height, mid_height, min_coincidents)

def print_graph(session: TraceSession, step, max_height):
    width = shutil.get_terminal_size((80, 20)).columns
    lpad = 8 # Space on the left reserved for time labels
    graph_width = width - lpad
    duration = session.get_duration()

    if step is None and max_height is None:
        raise ValueError("At least one of step or max_height must be provided")

    if step is None:
        time_step = auto_step_size(session, min_height=4, max_height=max_height)
    else:
        time_step = step

    total_rows = int(duration / time_step) + 2
    if max_height is not None:
        total_rows = min(total_rows, max_height)

    ordered_branches = build_ordered_branches(session.root)
    branch_width = min(8, graph_width // max(1, len(ordered_branches)))


    def get_branch_state(branch, current_time):
        just_spawned = branch.start_time >= current_time and branch.start_time < current_time + time_step
        just_died = branch.end_time is not None and branch.end_time >= current_time and branch.end_time < current_time + time_step
        running = (just_spawned and not just_died) or (branch.start_time <= current_time and (branch.end_time is None or branch.end_time >= current_time))
        
        return just_spawned, just_died, running

    print(f"\n{'PID':>7} | " + "".join(str(b.pid).ljust(branch_width) for b in ordered_branches))


    for row in range(0, total_rows):
        current_time = row * time_step
        line = f"{current_time:6.2f}s | "
        for index, branch in enumerate(ordered_branches):
            branch_char = ""
            fill_char = " "
            just_spawned, just_died, running = get_branch_state(branch, current_time)
            has_bridge = False

            if not running:
                # Check if any branches are starting further to the right
                # and draw horizontal line if the parent is to the left
                for other_branch in ordered_branches[index+1:]:
                    other_just_spawned, _, _ = get_branch_state(other_branch, current_time)
                    if other_just_spawned and ordered_branches.index(other_branch.parent) < index:
                        has_bridge = True
                        break

            any_forks = any(
                branch.start_time >= current_time and branch.start_time < current_time + time_step and branch.parent in ordered_branches[:index+1]
                for branch in ordered_branches[index+1:]
            )

            if has_bridge:
                branch_char = fill_char = "─"
            elif just_spawned:
                branch_char = "┬" if branch.parent is None or any_forks else "┐"

                if any_forks:
                    fill_char = "─"
            elif just_died:
                branch_char = "┴"
            elif running:
                if any_forks:
                    branch_char = "├"
                    fill_char = "─"
                else:
                    branch_char = "│"
            else:
                branch_char += " "

            line += branch_char.ljust(branch_width, fill_char)

        print(line)
