"""Production check: do different CRAB tasks share an LHE seed?

Before 2026-09-13 the payload set initialSeed to the ProcId, and every task
runs ProcId 1..totalUnits, so the same-numbered jobs of different tasks
generated the same hard-process events. The fix gives each task a unique
SeedBase (see tools/check_seed_bases.py); this script verifies on the OUTPUT
that the fix actually took effect.

    python3 tools/check_seed_uniqueness.py --dir <era output dir> [--jobs 5,7,11] [--max-tasks 6]

Do NOT use run:lumi:event as the fingerprint. Every job numbers its events in
the same 1..N range, so 40 jobs of a single task already share 43.5% of their
run:lumi:event triples -- that is slot occupancy (pigeonhole), unrelated to the
seed, and it would fire on every healthy production. Measured on one task:
43.52% and 43.37%.

Use Generator_x1, the hard-process momentum fraction: continuous and
high-precision, so
  * independent jobs   -> 0.0% overlap (measured)
  * a shared seed      -> ~40% overlap (measured on the bug)
which leaves plenty of room for a threshold.
"""
from __future__ import print_function
import argparse
import collections
import glob
import os
import re
import sys

import numpy as np
import uproot

THRESHOLD = 5.0     # overlap above this means a shared seed (independent: 0.0)


def load(path, key="Generator_x1"):
    return uproot.open(path)["Events"][key].array(library="np")


def files_by_job(taskdir):
    out = {}
    for f in glob.glob(os.path.join(taskdir, "*.root")):
        m = re.search(r"__job-(\d+)_", os.path.basename(f))
        if m:
            out[int(m.group(1))] = f
    return out


def overlap(a, b):
    ca = collections.Counter(np.round(a, 9))
    cb = collections.Counter(np.round(b, 9))
    return sum((ca & cb).values())


def main(a):
    tasks = sorted([d for d in glob.glob(os.path.join(a.dir, "*")) if os.path.isdir(d)])
    if a.tasks:
        want = set(a.tasks.split(","))
        tasks = [t for t in tasks if os.path.basename(t) in want]
    tasks = tasks[:a.max_tasks]
    if len(tasks) < 2:
        print("Only %d task(s); the cross-task check does not apply "
              "(seeds differ within a task by construction)" % len(tasks))
        return 0
    idx = {os.path.basename(t): files_by_job(t) for t in tasks}
    jobs = [int(x) for x in a.jobs.split(",")]
    worst, checked, bad = 0.0, 0, []
    print("Checking %d tasks: %s" % (len(tasks), ", ".join(os.path.basename(t) for t in tasks)))
    for j in jobs:
        have = [(t, idx[t][j]) for t in idx if j in idx[t]]
        if len(have) < 2:
            continue
        base_t, base_f = have[0]
        try:
            va = load(base_f)
        except Exception as e:
            print("  job-%d: cannot read %s: %s" % (j, base_t, e)); continue
        for t, f in have[1:]:
            try:
                vb = load(f)
            except Exception as e:
                print("  job-%d: cannot read %s: %s" % (j, t, e)); continue
            n = overlap(va, vb)
            pct = 100.0 * n / max(min(len(va), len(vb)), 1)
            checked += 1
            worst = max(worst, pct)
            flag = "!!" if pct > THRESHOLD else "  "
            print("  %s job-%-5d %s vs %-10s overlap %4d / %4d = %5.1f%%"
                  % (flag, j, base_t, t, n, min(len(va), len(vb)), pct))
            if pct > THRESHOLD:
                bad.append((j, base_t, t, pct))
            sys.stdout.flush()
    if checked == 0:
        print("No job index exists in two or more tasks -- nothing to compare")
        return 0
    print("\nCompared %d pairs, largest overlap %.1f%% (threshold %.1f%%)" % (checked, worst, THRESHOLD))
    if bad:
        print("ERROR: %d pairs share an LHE seed -- those tasks generate the same "
              "hard-process events." % len(bad))
        print("       Check the SeedBase values: python3 tools/check_seed_bases.py")
        
        return 1
    print("OK: no shared seeds across tasks")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True,
                    help="era output directory; one subdirectory per task")
    ap.add_argument("--jobs", default="5,7,11,23,41", help="job indices to sample")
    ap.add_argument("--max-tasks", type=int, default=6)
    ap.add_argument("--tasks", default="",
                    help="comma-separated task subdirectory names to restrict to. "
                         "Use it to check one production round on its own: a "
                         "directory that also holds rounds produced before the "
                         "seed fix will otherwise report their known collisions.")
    sys.exit(main(ap.parse_args()))
