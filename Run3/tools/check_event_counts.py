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

How it stays fast
-----------------
Opening a NanoAOD costs about 1.1 s, and nearly all of it is uproot parsing
~1,500 branch descriptions in Python -- CPU, not I/O. So neither the transport
nor threads help. Measured on 2026-09-29, 40 files of one 2024 task:

    FUSE, serial          1.12 s/file    10,000 files: 3.1 h
    xrootd, serial        1.19 s/file    (the mount was never the bottleneck)
    xrootd, 8-32 threads  1.48-1.57 s/file   slower: the threads fight over
                                             the interpreter lock
    6 processes           0.26 s/file    10,000 files: 42 min

Opening every file of a 10,000-job task is therefore 42 minutes at best, and it
was 4 hours as shipped -- long enough that people stopped running it.

The default mode avoids opening almost anything. File size tracks the event
count tightly: on 60 files of that task, size = 2.65 MB + 4,250 bytes/event,
r = 0.98, largest residual 0.67% (about 5 events). A fixed overhead makes up
81% of a normal file, which is why a stunted one is only ~18% smaller and slips
past a size check done by eye -- but it still separates cleanly. A file at the
flagging threshold (half the median, 74 events) is predicted at 2.97 MB; the
smallest of all 10,000 real files in that task is 3.09 MB.

So by default: read every file's size (a directory listing, seconds), open a
spread sample to find the median event count, then sort all files by size and
open them from the smallest up, stopping once 30 in a row hold a clearly normal
count. A stunted file is small, so it sits at the bottom of that order; nothing
above a run of normal files can be below the flag. Every file is screened; only
the small end is opened, and no slope is extrapolated, so a calibration sample
spanning a narrow range of counts cannot shift the cut. If size and events look
unrelated altogether (r < 0.5), the script says so and opens everything.

    --full        open every file (6 processes); to enumerate, or to double-check
    --sample N    open N files spread across the directory, nothing else

Needs uproot: run it inside the CMSSW environment from TUTORIAL section 2, not
against the system python3 on lxplus.
"""
from __future__ import print_function
import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

try:
    import uproot
except ImportError:
    sys.exit("uproot not found -- set up the CMSSW environment first "
             "(TUTORIAL section 2); the system python3 on lxplus has no uproot.")

CALIBRATE = 24      # files opened to find the median event count
SAFE_FRAC = 0.75    # a file at or above this fraction of the median is
                    # "clearly normal". The flag is at --min-frac (0.5); the
                    # 25-point gap is ~37 events for 2024, against a size-to-
                    # events noise of ~5-10 events.
SAFE_RUN = 30       # stop once this many consecutive files, in size order,
                    # are clearly normal
MIN_R = 0.5         # below this, size and event count look unrelated


def files_under(root):
    """(path, size) of every *.root, recursively.

    Skips names starting with a dot. CernBox keeps an overwritten file's old
    copy in a DIRECTORY named ".sys.v#.<original>.root" -- the name ends in
    .root -- so that has to be excluded by name, not by extension.
    """
    out = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            continue
        with it:
            for e in it:
                if e.name.startswith("."):
                    continue
                if e.is_dir(follow_symlinks=False):
                    stack.append(e.path)
                elif e.name.endswith(".root"):
                    try:
                        out.append((e.path, e.stat().st_size))
                    except OSError:
                        out.append((e.path, -1))
    return sorted(out)


def nevents(path):
    try:
        with uproot.open(path) as f:
            return path, f["Events"].num_entries, None
    except Exception as exc:
        return path, None, type(exc).__name__


def open_many(paths, workers):
    """Processes, not threads: the cost is CPU inside uproot, see the docstring."""
    if not paths:
        return []
    if workers <= 1 or len(paths) == 1:
        return [nevents(p) for p in paths]
    with ProcessPoolExecutor(min(workers, len(paths))) as ex:
        return list(ex.map(nevents, paths, chunksize=4))


def spread(items, n):
    if n >= len(items):
        return list(items)
    step = len(items) / float(n)
    return [items[int(i * step)] for i in range(n)]


def fit_line(xs, ys):
    """Least squares y = a + b x, and Pearson r."""
    n = float(len(xs))
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        return None, None, 0.0
    b = sxy / sxx
    return my - b * mx, b, sxy / (sxx * syy) ** 0.5


def main(root, min_frac, sample, full, workers, quiet, list_bad=False):
    listing = files_under(root)
    if not listing:
        print("no .root files under %s" % root)
        return 1
    sizes = dict(listing)
    allpaths = [p for p, _ in listing]
    note = ""

    if sample and sample < len(allpaths):
        # Old behavior, kept: open exactly N files, nothing else.
        opened = open_many(spread(allpaths, sample), workers)
        print("sampling %d of the files" % len(opened))
        median_src = opened
    elif full:
        opened = open_many(allpaths, workers)
        median_src = opened
        note = " (every file opened)"
    else:
        calib = open_many(spread(allpaths, CALIBRATE), workers)
        got = dict((p, (n, why)) for p, n, why in calib)
        pts = [(sizes[p], n) for p, n, _ in calib if n is not None and sizes[p] > 0]
        r = 0.0
        b = None
        if len(pts) >= 8:
            _, b, r = fit_line([n for _, n in pts], [s for s, _ in pts])
        # The only assumption left is that size grows with the event count.
        # This guard is loose on purpose: it rejects "size and events look
        # unrelated", not "the calibration sample is narrow". An r threshold of
        # 0.9 failed a healthy 2024 task at r = 0.892, because its 24 points
        # spanned only 137-169 events and a narrow range drags r down however
        # good the relation is. Healthy tasks measured 0.89-0.98.
        if b is None or b <= 0 or r < MIN_R:
            print("size does not track the event count here (r=%.2f over %d files);"
                  " opening every file instead" % (r, len(pts)))
            opened = open_many(allpaths, workers)
            median_src = opened
            note = " (every file opened)"
        else:
            counts = sorted(n for _, n in pts)
            med = counts[len(counts) // 2]
            safe = SAFE_FRAC * med
            # Walk up from the SMALLEST file. A stunted file is small, because
            # a file is a fixed overhead plus a per-event part; so every stunted
            # file sits at the bottom of the size order. Open from the bottom
            # until SAFE_RUN files in a row are clearly normal -- nothing larger
            # than that can be below the flag. No slope is extrapolated, so a
            # narrow calibration sample cannot move the cut. Unreadable sizes
            # (-1) sort first and are always opened.
            order = sorted(allpaths, key=lambda p: sizes[p])
            run, i, walked = 0, 0, 0
            batch = max(workers * 5, SAFE_RUN)
            while i < len(order) and run < SAFE_RUN:
                chunk = order[i:i + batch]
                need = [p for p in chunk if p not in got]
                for p, n, why in open_many(need, workers):
                    got[p] = (n, why)
                walked += len(need)
                for p in chunk:
                    n, _ = got[p]
                    run = run + 1 if (n is not None and n >= safe) else 0
                    i += 1
                    if run >= SAFE_RUN:
                        break
            opened = [(p, n, why) for p, (n, why) in got.items()]
            median_src = calib
            note = (" (all %d sizes screened; %d opened to calibrate,"
                    " %d opened from the small end)" % (len(allpaths), len(calib), walked))

    counts = [(n, p) for p, n, _ in opened if n is not None]
    unreadable = [(p, why) for p, n, why in opened if n is None]
    base = sorted(n for p, n, _ in median_src if n is not None)
    if not base:
        print("could not read any file")
        return 1
    median = base[len(base) // 2]
    floor = max(1, int(median * min_frac))
    stunted = [(c, p) for c, p in counts if c < floor]

    if list_bad:
        for _, p in sorted(stunted):
            print(p)
        return 1 if stunted else 0

    ordered = sorted(c for c, _ in counts)
    print("%d files, median %d events, range %d-%d%s"
          % (len(allpaths), median, ordered[0], ordered[-1], note))
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
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, help="directory to scan, recursively")
    ap.add_argument("--min-frac", type=float, default=0.5,
                    help="flag files below this fraction of the median (default 0.5)")
    ap.add_argument("--sample", type=int, default=0,
                    help="open only this many files, spread evenly, and nothing else")
    ap.add_argument("--full", action="store_true",
                    help="open every file instead of screening by size")
    ap.add_argument("--workers", type=int, default=6,
                    help="processes used to open files (default 6)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--list-bad", action="store_true",
                    help="print only the paths of stunted files, one per line, "
                         "for a script to consume")
    a = ap.parse_args()
    sys.exit(main(a.dir, a.min_frac, a.sample, a.full, a.workers, a.quiet, a.list_bad))
