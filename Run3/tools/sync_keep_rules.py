#!/usr/bin/env python3
"""Add the second gen-particle keep rule to the Run 3 CRAB payloads in job/.

job/*.sh are separate copies from DY_stat_boost/CRAB_script/*.sh -- editing the
latter does NOT reach the jobs, because crabConfig points at job/. The only two
differences are this keep rule and OUT_BASE (job/ uses ${USER}, which is the
better version), so patch the rule in place instead of copying the file over.

Input / output: DY_filter_MC_submission/Run3/job/*.sh (backed up to
.bak_before_keepstatus1 before the first change).
"""
import glob
import os
import shutil
import sys

# tools/ 在 Run3/ 底下一層, job/ 在上一層
JOBDIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job")

PI0 = ("select.append('keep++ (abs(pdgId) == 111 || abs(pdgId) == 221) "
       "&& pt > 5')")
STATUS1 = "select.append('keep status == 1 && pt > 0.5')"

# (collection used by that cmsDriver step)
COLLECTIONS = ["prunedGenParticles", "finalGenParticles"]


def patch(path):
    with open(path) as fh:
        text = fh.read()

    if STATUS1 in text:
        return "already patched"

    new = text
    for coll in COLLECTIONS:
        old_str = "process.%s.%s\"" % (coll, PI0)
        new_str = "process.%s.%s\\nprocess.%s.%s\"" % (coll, PI0, coll, STATUS1)
        if old_str not in new:
            return "PATTERN NOT FOUND for %s" % coll
        if new.count(old_str) != 1:
            return "pattern for %s appears %d times" % (coll, new.count(old_str))
        new = new.replace(old_str, new_str)

    shutil.copy2(path, path + ".bak_before_keepstatus1")
    with open(path, "w") as fh:
        fh.write(new)
    return "patched"


def main():
    files = sorted(glob.glob(os.path.join(JOBDIR, "*.sh")))
    if not files:
        sys.exit("no payloads found in %s" % JOBDIR)
    rc = 0
    for f in files:
        res = patch(f)
        print("%-22s %s" % (os.path.basename(f), res))
        if res not in ("patched", "already patched"):
            rc = 1
    # verify
    print()
    for f in files:
        with open(f) as fh:
            t = fh.read()
        n_pi0 = t.count(PI0)
        n_s1 = t.count(STATUS1)
        flag = "OK" if (n_pi0 == 2 and n_s1 == 2) else "CHECK"
        print("%-22s pi0=%d status1=%d  %s" % (os.path.basename(f), n_pi0, n_s1, flag))
        if flag == "CHECK":
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
