#!/usr/bin/env python3
"""Verify the DYfilter validation batch: filter efficiency, file size, GenPart content.

Run this once the test task's NanoAOD has landed. It answers the three questions
the test exists to answer, and compares each against the old production.

  1. filter efficiency  -- events written per job. Old production (2022postEE,
     Nevents=10000 per job) averaged 976 events/job = 9.76%. The new filter adds
     a photon-cluster pT > 10 GeV cut and a 75 < m_ll < 105 GeV gen Z window, so
     this number must drop; by how much decides how many jobs the full
     production needs.

  2. file size -- drives the storage estimate. Old files were ~4.3 MB for ~976
     events. `keep status == 1 && pt > 0.5` inflates GenPart, so per-event size
     will grow.

  3. GenPart hadron content -- the premise of the whole approach. The AN photon
     origin classification needs the nearest status-1 gen particle to a reco
     photon. In the old NanoAOD that collection was pruned down to photons and
     leptons (measured: 8258 photons, 1188 leptons, 3 charged pions), which is
     why the classification could not be reproduced. If the new keep rule works,
     charged hadrons must now appear in quantity.

Usage:
  python3 check_test_batch.py [new_glob] [old_glob]
"""
import glob
import math
import os
import sys
from collections import Counter

import uproot

OLD_EVENTS_PER_JOB = 976.0
NEVENTS_PER_JOB = 10000.0

NEW_DEFAULT = ("/eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYfilter/"
               "test_newfilter/2022postEE/testnew/*.root")
OLD_DEFAULT = ("/eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYfilter/"
               "phase2/2022postEE/p2_1/*.root")

HADRONS = {211: "pi+-", 321: "K+-", 2212: "p", 130: "K0L", 310: "K0S",
           2112: "n", 3122: "Lambda", 3222: "Sigma+", 3112: "Sigma-",
           3322: "Xi0", 3312: "Xi-", 3334: "Omega-"}
LEPTONS = {11: "e", 13: "mu"}

GEN_BR = ["GenPart_pdgId", "GenPart_status", "GenPart_pt", "GenPart_eta", "GenPart_phi"]
PHO_BR = ["Photon_pt", "Photon_eta", "Photon_phi"]


def summarize(files, label, do_match=True, max_files=10, max_events=2000):
    files = files[:max_files]
    if not files:
        print("  %s: no files" % label)
        return None

    n_ev = 0
    n_bytes = 0
    counts = Counter()
    near_pdg = Counter()
    n_pho = 0

    for fn in files:
        n_bytes += os.path.getsize(fn)
        f = uproot.open(fn)
        tree = f["Events"]
        want = GEN_BR + (PHO_BR if do_match else [])
        have = [b for b in want if b in tree.keys()]
        arrs = tree.arrays(have, library="np", entry_stop=max_events)
        n_this = tree.num_entries
        n_ev += n_this

        nread = len(arrs["GenPart_pdgId"])
        for i in range(nread):
            pdg = arrs["GenPart_pdgId"][i]
            sta = arrs["GenPart_status"][i]
            for j in range(len(pdg)):
                if int(sta[j]) != 1:
                    continue
                a = abs(int(pdg[j]))
                if a in HADRONS:
                    counts[HADRONS[a]] += 1
                elif a == 22:
                    counts["gamma"] += 1
                elif a in LEPTONS:
                    counts[LEPTONS[a]] += 1
                elif a in (12, 14, 16):
                    counts["nu"] += 1
                else:
                    counts["other"] += 1

            if not do_match or "Photon_pt" not in arrs:
                continue
            geta, gphi, gpt = (arrs["GenPart_eta"][i], arrs["GenPart_phi"][i],
                               arrs["GenPart_pt"][i])
            for k in range(len(arrs["Photon_pt"][i])):
                pe, pp = arrs["Photon_eta"][i][k], arrs["Photon_phi"][i][k]
                best, best_j = 1e9, -1
                for j in range(len(pdg)):
                    if int(sta[j]) != 1:
                        continue
                    dphi = abs(float(gphi[j]) - float(pp))
                    while dphi > math.pi:
                        dphi = abs(dphi - 2 * math.pi)
                    dr = math.hypot(float(geta[j]) - float(pe), dphi)
                    if dr < best:
                        best, best_j = dr, j
                n_pho += 1
                if best_j < 0 or best > 0.1 or float(gpt[best_j]) <= 5.0:
                    near_pdg["pile-up (dR>0.1 or pT<=5)"] += 1
                else:
                    a = abs(int(pdg[best_j]))
                    if a == 22:
                        near_pdg["gamma (-> jet)"] += 1
                    elif a in HADRONS:
                        near_pdg["%s (-> other)" % HADRONS[a]] += 1
                    elif a in LEPTONS:
                        near_pdg["%s (-> other)" % LEPTONS[a]] += 1
                    else:
                        near_pdg["pdg %d (-> other)" % a] += 1

    per_job = n_ev / float(len(files))
    print("  %s" % label)
    print("    檔案 %d 個, 事件 %d, 平均 %.1f 事件/job" % (len(files), n_ev, per_job))
    print("    filter 效率 %.2f%%" % (100.0 * per_job / NEVENTS_PER_JOB))
    print("    平均檔案大小 %.2f MB, 每事件 %.1f kB"
          % (n_bytes / len(files) / 1e6, n_bytes / max(n_ev, 1) / 1e3))
    tot = sum(counts.values())
    print("    status-1 GenPart 組成 (前 8 類, 共 %d):" % tot)
    for k, v in counts.most_common(8):
        print("      %-10s %8d  (%.1f%%)" % (k, v, 100.0 * v / max(tot, 1)))
    if near_pdg:
        print("    reco photon 最近 status-1 gen 粒子 (%d 個 photon):" % n_pho)
        for k, v in near_pdg.most_common(8):
            print("      %-28s %6d  (%.1f%%)" % (k, v, 100.0 * v / max(n_pho, 1)))
    return per_job


def main():
    new_glob = sys.argv[1] if len(sys.argv) > 1 else NEW_DEFAULT
    old_glob = sys.argv[2] if len(sys.argv) > 2 else OLD_DEFAULT

    print("=" * 62)
    print("新版 (新 filter + 新 keep 規則)")
    print("=" * 62)
    new_per_job = summarize(sorted(glob.glob(new_glob)), new_glob)

    print()
    print("=" * 62)
    print("舊版 (對照)")
    print("=" * 62)
    old_per_job = summarize(sorted(glob.glob(old_glob)), old_glob)

    if new_per_job and old_per_job:
        print()
        print("=" * 62)
        print("結論")
        print("=" * 62)
        print("  效率比 新/舊 = %.3f" % (new_per_job / old_per_job))
        print("  => 相同統計量所需 job 數 = 原本的 %.2f 倍"
              % (old_per_job / new_per_job))


if __name__ == "__main__":
    main()
