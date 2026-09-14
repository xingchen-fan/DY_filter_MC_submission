"""Check that every crabConfig has a unique SeedBase and that the seed ranges
they imply do not overlap.

Before 2026-09-13 the payload set initialSeed to the ProcId, and every task
runs ProcId 1..totalUnits, so the same-numbered jobs of different tasks shared
an LHE seed and produced the same hard-process events (measured: only 29.9% of
the accumulated events across 13 tasks were distinct). Each task now carries a
unique SeedBase and the real seed is SeedBase + ProcId. This script is the
auditable check that the guarantee holds -- rather than relying on memory.

    python3 tools/check_seed_bases.py [--dir <Run3 root>]

Exit code 0 = all good, 1 = a conflict was found.
"""
from __future__ import print_function
import argparse
import glob
import os
import re
import sys

CMSSW_MAX_SEED = 900000000
RE_ARGS = re.compile(r"scriptArgs\s*=\s*\[(.*?)\]", re.S)
RE_UNITS = re.compile(r"totalUnits\s*=\s*(\d+)")
RE_NAME = re.compile(r"requestName\s*=\s*['\"]([^'\"]+)")


def scan(root):
    out, templates = [], []
    pats = ("crab_configs/crabConfig_*.py", "tools/crabConfig_*.py",
            "local/crabConfig_*.py", "crabConfig_*.py")
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(root, pat))):
            txt = open(f).read()
            m = RE_ARGS.search(txt)
            args = m.group(1) if m else ""
            sb = re.search(r"SeedBase=(\d+)", args)
            units = RE_UNITS.search(txt)
            name = RE_NAME.search(txt)
            rec = dict(path=os.path.relpath(f, root),
                       seedbase=int(sb.group(1)) if sb else None,
                       units=int(units.group(1)) if units else None,
                       name=name.group(1) if name else "?")
            # The six era templates get their scriptArgs rewritten by submit_run3.sh,
            # so they legitimately have no SeedBase of their own.
            if re.match(r"crabConfig_[^_]+(_2E|_2Mu)?\.py$", os.path.basename(f)):
                templates.append(rec)
            else:
                out.append(rec)
    return out, templates


def main(root):
    cfgs, templates = scan(root)
    bad = 0
    missing = [c for c in cfgs if c["seedbase"] is None]
    # crab_configs/ holds throw-away output of submit_run3.sh; resubmitting
    # regenerates them with a SeedBase. tools/ and local/ are hand-written, so
    # a missing SeedBase there is a real defect.
    gen = [c for c in missing if c["path"].startswith("crab_configs/")]
    hand = [c for c in missing if not c["path"].startswith("crab_configs/")]
    if hand:
        bad += len(hand)
        print("ERROR: %d hand-written configs have no SeedBase (jobs exit 65):" % len(hand))
        for c in hand:
            print("     %s  (%s)" % (c["path"], c["name"]))
    if gen:
        print("NOTE: %d generated configs under crab_configs/ have no SeedBase."
              % len(gen))
        print("      They predate 2026-09-13 and are throw-away; resubmitting"
              " regenerates them.")
        print("      Submitting one directly fails with exit 65, by design.")

    have = [c for c in cfgs if c["seedbase"] is not None]
    seen = {}
    for c in have:
        seen.setdefault(c["seedbase"], []).append(c)
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        bad += len(dup)
        print("ERROR: duplicate SeedBase:")
        for k, v in sorted(dup.items()):
            print("     %d -> %s" % (k, ", ".join(x["path"] for x in v)))

    # The ranges [sb+1, sb+units] must not overlap.
    iv = sorted(((c["seedbase"] + 1, c["seedbase"] + (c["units"] or 10000), c)
                 for c in have), key=lambda t: t[0])
    for (a1, a2, ca), (b1, b2, cb) in zip(iv, iv[1:]):
        if b1 <= a2:
            bad += 1
            print("ERROR: seed ranges overlap: %s [%d,%d] and %s [%d,%d]"
                  % (ca["path"], a1, a2, cb["path"], b1, b2))

    over = [c for c in have if c["seedbase"] + (c["units"] or 10000) >= CMSSW_MAX_SEED]
    if over:
        bad += len(over)
        print("ERROR: above the CMSSW seed limit %d:" % CMSSW_MAX_SEED)
        for c in over:
            print("     %s  seedbase=%d" % (c["path"], c["seedbase"]))

    print("\nChecked %d configs (%d templates excluded)" % (len(cfgs), len(templates)))
    if bad == 0:
        print("OK: all SeedBase values unique, ranges disjoint, within CMSSW limits")
        if have:
            print("    range %d .. %d" % (min(c["seedbase"] for c in have),
                                       max(c["seedbase"] for c in have)))
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    sys.exit(main(ap.parse_args().dir))
