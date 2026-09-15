"""Check that every crabConfig passes Submitter in scriptArgs.

The LHE seed is derived in the payload from Submitter, era, tag and ProcId. A
config that does not pass it makes every job exit 65 -- deliberately, since the
alternative is a silent fallback, which is how the original seed bug produced
two weeks of output that looked correct. This catches it before submission
rather than after.

    python3 tools/check_submitter.py [--dir <Run3 root>]

Exit code 0 = all good, 1 = at least one config would fail at runtime.
"""
from __future__ import print_function
import argparse
import glob
import os
import re
import sys

RE_ARGS = re.compile(r"scriptArgs\s*=\s*\[(.*?)\]", re.S)
RE_NAME = re.compile(r"requestName\s*=\s*['\"]([^'\"]+)")


def main(root):
    bad, ok, templates = [], 0, 0
    pats = ("crab_configs/crabConfig_*.py", "tools/crabConfig_*.py",
            "local/crabConfig_*.py", "crabConfig_*.py")
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(root, pat))):
            rel = os.path.relpath(f, root)
            # The six era templates get scriptArgs rewritten by submit_run3.sh,
            # so they legitimately carry none of their own.
            if re.match(r"crabConfig_[^_]+(_2E|_2Mu)?\.py$", os.path.basename(f)):
                templates += 1
                continue
            txt = open(f).read()
            m = RE_ARGS.search(txt)
            if m and "Submitter=" in m.group(1):
                ok += 1
            else:
                name = RE_NAME.search(txt)
                bad.append((rel, name.group(1) if name else "?"))

    # crab_configs/ holds throw-away output of submit_run3.sh, regenerated with
    # Submitter on the next submission. tools/ and local/ are hand-written, so a
    # missing Submitter there is a real defect.
    gen = [x for x in bad if x[0].startswith("crab_configs/")]
    hand = [x for x in bad if not x[0].startswith("crab_configs/")]
    if hand:
        print("ERROR: %d hand-written configs do not pass Submitter; "
              "their jobs exit 65:" % len(hand))
        for rel, name in hand:
            print("     %s  (%s)" % (rel, name))
        print("\n   Add 'Submitter=<your username>' to config.JobType.scriptArgs.")
    if gen:
        print("NOTE: %d generated configs under crab_configs/ predate this and"
              % len(gen))
        print("      carry no Submitter. They are throw-away; resubmitting")
        print("      regenerates them. Submitting one directly fails with"
              " exit 65, by design.")
    print("\nChecked %d configs (%d era templates excluded)" % (ok + len(bad), templates))
    if not hand:
        print("OK: every hand-written config passes Submitter")
    return 1 if hand else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    sys.exit(main(ap.parse_args().dir))
