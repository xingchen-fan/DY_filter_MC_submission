"""Sum the RESULT_JSON lines emitted by parallel an_classify_miniaod.py shards.

    python3 an_merge_shards.py an_logs/an2022_*.log

Shards are statistically independent (disjoint input files), so the counters
add and the binomial errors are computed once on the total.
"""
from __future__ import print_function
import glob
import json
import math
import sys
from collections import Counter

# AN-22-027 Table (2017 UL) and the 2018 AOD numbers on slide 5 of
# Run3_2022DY_check.pdf, for reference in the printout.
REFERENCE = [
    ("AN-22-027 2017 UL, e channel", (48.84, 45.51, 5.65)),
    ("AN-22-027 2017 UL, mu channel", (50.04, 44.60, 5.36)),
    ("Run3_2022DY_check slide 5, 2018 AOD", (37.0, 52.0, 11.0)),
]


def main(patterns):
    files = []
    for p in patterns:
        files.extend(sorted(glob.glob(p)))
    if not files:
        sys.exit("no log files matched: %s" % patterns)

    n_ev = n_sel = n_h3 = 0
    cf, cat, pdg, cat_h3 = Counter(), Counter(), Counter(), Counter()
    used = missing = 0
    for f in files:
        payload = None
        with open(f) as fh:
            for line in fh:
                if line.startswith("RESULT_JSON "):
                    payload = json.loads(line[len("RESULT_JSON "):])
        if payload is None:
            missing += 1
            print("  no RESULT_JSON (still running or died): %s" % f)
            continue
        used += 1
        n_ev += payload["n_ev"]
        n_sel += payload["n_sel"]
        cf.update(payload["cutflow"])
        cat.update(payload["cat"])
        n_h3 += payload.get("n_h3", 0)
        cat_h3.update(payload.get("cat_h3", {}))
        pdg.update(payload["pdg_of_other"])

    print("\nshards used %d, incomplete %d" % (used, missing))
    print("events read %d, passing full HZg baseline %d  (rate %.2e)"
          % (n_ev, n_sel, float(n_sel) / max(n_ev, 1)))
    print("cutflow: " + ", ".join("%s=%d" % (k, cf[k]) for k in sorted(cf)))
    if n_sel == 0:
        return

    print("\n--- AN-22-027 classification ---")
    for k, lab in (("pileup", "Pile-up photon"), ("jet", "Jet photon"),
                   ("other", "Other particle")):
        n = cat[k]
        frac = float(n) / n_sel
        err = 100.0 * math.sqrt(max(frac * (1.0 - frac), 1.0 / n_sel) / n_sel)
        print("  %-15s %6d = %5.1f%% +- %.1f" % (lab, n, 100.0 * frac, err))
    if n_h3:
        print("\n--- additionally inside 90 < m_llg < 180  (n=%d) ---" % n_h3)
        for k, lab in (("pileup", "Pile-up photon"), ("jet", "Jet photon"),
                       ("other", "Other particle")):
            n = cat_h3[k]
            fr = float(n) / n_h3
            err = 100.0 * math.sqrt(max(fr * (1.0 - fr), 1.0 / n_h3) / n_h3)
            print("  %-15s %6d = %5.1f%% +- %.1f" % (lab, n, 100.0 * fr, err))
    print("\n  reference (pile-up / photon / other):")
    for lab, (a, b, c) in REFERENCE:
        print("    %-38s %5.1f / %5.1f / %5.1f" % (lab, a, b, c))
    if pdg:
        print("\n  matched-particle pdgId of the 'other' class:")
        for pid, n in pdg.most_common(10):
            print("    %6s : %d" % (pid, n))


if __name__ == "__main__":
    main(sys.argv[1:])
