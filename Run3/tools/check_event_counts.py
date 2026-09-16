"""Find output files that succeeded and produced almost nothing.

A job that dies partway through the chain can still exit 0, stage out, and
leave a NanoAOD with a handful of events in it. Measured at T2_US_MIT and
T2_US_UCSD on 2026-09-16: one job in ten wrote 7 events where the others wrote
about 300, and CRAB reported all ten as finished. None of the usual checks see
it -- the job succeeded, the file is there, the size is within a factor of two
of a good one, the tree opens. Only the event count is wrong.

    python3 tools/check_event_counts.py --dir <output>/<era>/<tag>
    python3 tools/check_event_counts.py --dir <output>/<era>     # every tag

Run it before merging. Exit 0 = nothing stunted, 1 = at least one file is.

The threshold is relative, because a normal file holds ~300 events for the
2022/2023 eras and ~150 for 2024: anything below --min-frac (default 0.5) of
the median counts as stunted. Real spread is far narrower than that -- 200 CERN
files of one task ranged 266 to 361 against a median of 314, and the stunted
file was at 2% of its median.

Needs uproot: run it inside the CMSSW environment from TUTORIAL section 2, not
against the system python3 on lxplus.
"""
from __future__ import print_function
import argparse
import os
import sys

try:
    import uproot
except ImportError:
    sys.exit("uproot not found -- set up the CMSSW environment first "
             "(TUTORIAL section 2); the system python3 on lxplus has no uproot.")


def files_under(root):
    out = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.endswith(".root"):
                out.append(os.path.join(dirpath, n))
    return sorted(out)


def main(root, min_frac, sample, quiet, list_bad=False):
    paths = files_under(root)
    if not paths:
        print("no .root files under %s" % root)
        return 1
    if sample and sample < len(paths):
        step = len(paths) // sample
        paths = paths[::step][:sample]
        print("sampling %d of the files" % len(paths))

    counts, unreadable = [], []
    for p in paths:
        try:
            with uproot.open(p) as f:
                counts.append((f["Events"].num_entries, p))
        except Exception as exc:
            unreadable.append((p, type(exc).__name__))

    if not counts:
        print("could not read any file")
        return 1
    ordered = sorted(c for c, _ in counts)
    median = ordered[len(ordered) // 2]
    floor = max(1, int(median * min_frac))
    stunted = [(c, p) for c, p in counts if c < floor]

    if list_bad:
        for _, p in sorted(stunted):
            print(p)
        return 1 if stunted else 0

    print("%d files, median %d events, range %d-%d"
          % (len(counts), median, ordered[0], ordered[-1]))
    print("threshold: %d events (%.0f%% of the median)" % (floor, 100 * min_frac))
    for p, why in unreadable:
        print("  UNREADABLE  %s  (%s)" % (os.path.basename(p), why))
    if stunted:
        print("\n%d stunted file(s) -- these exited 0 and are wrong anyway:"
              % len(stunted))
        for c, p in sorted(stunted):
            print("  %6d events  %s" % (c, os.path.basename(p)))
        print("\nThese cannot be retried: CRAB answers \"Only jobs in status"
              " failed can be resubmitted\".\nDelete them and produce the"
              " missing count under a new tag -- see recover.sh.")
    elif not quiet:
        print("OK: no stunted files")
    return 1 if (stunted or unreadable) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="directory to scan, recursively")
    ap.add_argument("--min-frac", type=float, default=0.5,
                    help="flag files below this fraction of the median (default 0.5)")
    ap.add_argument("--sample", type=int, default=0,
                    help="check only this many files, spread evenly; 0 = all")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--list-bad", action="store_true",
                    help="print only the paths of stunted files, one per line, "
                         "for a script to consume")
    a = ap.parse_args()
    sys.exit(main(a.dir, a.min_frac, a.sample, a.quiet, a.list_bad))
