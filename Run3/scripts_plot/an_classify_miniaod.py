"""Classify DY events into pile-up / jet-photon / other-particle, per AN-22-027.

Everything here follows AN-22-027 Appendix "Drell-Yan MC sample extension"
(HiggsZGammaAna_Note/AN-22-027/App-DYSampleExtension.tex), so that the result
can be compared with its Table (2017 UL: pile-up ~49%, photon ~45%, rest ~6%).

Matching, quoted from the AN:

    "The truth particle which has the minimum dR with the reco photon is
     considered as the truth particle of the reco photon. ... If the minimum dR
     of the recon photon is larger than 0.1, the photon is regarded as a pileup
     photon ... In the first class, the reco photons either have no matched
     truth particle or are matched to truth particles that fail the pT cut."

so the order matters and is NOT the same as "nearest particle above 5 GeV":

    1. take the nearest truth particle of any kind, whatever its pT
    2. pile-up      if that nearest particle is farther than dR = 0.1
                    OR if it fails pT > 5 GeV
    3. jet photon   if it is a photon
    4. other        otherwise

Run on MINIAOD rather than AOD: packedGenParticles is the complete status-1
record (which is all this classification needs -- no ancestry is required), and
pat objects carry the analysis IDs, so the real HZg baseline can be applied
instead of a hand-rolled approximation.

Baseline thresholds read from higgs_dna/workflows/hzg_processor.py and
higgs_dna/selections/object_selections_hzg.py.

Run inside CMSSW (FWLite):
    python an_classify_miniaod.py --filelist <txt> --tag <label> [--nmax N]

Shards print a RESULT_JSON line so parallel runs can be summed with
an_merge_shards.py.
"""
from __future__ import print_function
import argparse
import json
import math
import sys
import time
from collections import Counter

import ROOT
from DataFormats.FWLite import Events, Handle

MZ = 91.1876
GEN_PT = 5.0
DR_MATCH = 0.1

# Resolved from the embedded ID list of the first object seen, because the
# names differ between Run 2 (RunIIFall17-v2) and Run 3 (RunIIIWinter22-v1).
PHO_ID = None
ELE_ID = None


# MiniAOD embeds several vintages of the same working point -- a Run 3 file
# still carries the Fall17 and Spring16 trainings -- so the vintage has to be
# chosen explicitly, most recent first. These are the ones the analysis uses,
# i.e. what NanoAOD's Photon_mvaID_WP80 / Electron_mvaIso_WP90 (Run 3) and
# Electron_mvaFall17V2Iso_WP90 (Run 2) map to.
ID_PREFERENCE = ("RunIIIWinter22", "RunIIFall17-v2", "Fall17-iso-V2")


def pick_id(obj, wanted, forbidden=()):
    """Return the embedded ID name containing every `wanted` substring."""
    names = [str(pair.first) for pair in
             (obj.photonIDs() if hasattr(obj, "photonIDs") else obj.electronIDs())]
    hits = [n for n in names
            if all(w in n for w in wanted) and not any(f in n for f in forbidden)]
    for pref in ID_PREFERENCE:                 # ordered: newest vintage wins
        narrowed = [n for n in hits if pref in n]
        if len(narrowed) == 1:
            return narrowed[0]
        if narrowed:
            break
    if len(hits) != 1:
        sys.exit("ID resolution failed for %s: wanted=%s, candidates=%s, all=%s"
                 % (type(obj).__name__, wanted, hits, names))
    return hits[0]


def dr(e1, p1, e2, p2):
    de = e1 - e2
    dp = math.fmod(p1 - p2 + 3.0 * math.pi, 2.0 * math.pi) - math.pi
    return math.sqrt(de * de + dp * dp)


def classify_an(photon, packed):
    """AN-22-027: nearest truth particle first, pT cut second.

    Returns (category, matched particle or None).
    """
    best, best_dr = None, 999.0
    for g in packed:
        d = dr(g.eta(), g.phi(), photon.eta(), photon.phi())
        if d < best_dr:
            best, best_dr = g, d
    if best is None or best_dr > DR_MATCH or best.pt() <= GEN_PT:
        return "pileup", best
    return ("jet" if best.pdgId() == 22 else "other"), best


def has_me_photon(pruned, photon_pt, nearby_pt=5.0, dr_cut=0.05):
    """HiggsDNA's DY/Zgamma overlap-removal criterion.

    From higgs_dna/selections/mc_overlap_removal_hzg.py: the event has a
    matrix-element photon if some gen photon with pt > photon_pt that is
    isPrompt or isHardProcess has NO hard-process non-photon with pt >
    nearby_pt within dR < dr_cut. DYJetsToLL is removed when this is true
    (those events are covered by the Zgamma sample instead).

    Uses prunedGenParticles because packedGenParticles carries no statusFlags.
    """
    photons, hard_others = [], []
    for g in pruned:
        fl = g.statusFlags()
        if g.pdgId() == 22:
            if g.pt() > photon_pt and (fl.isPrompt() or fl.isHardProcess()):
                photons.append(g)
        elif fl.isHardProcess() and g.pt() > nearby_pt:
            hard_others.append(g)
    for p in photons:
        if not any(dr(p.eta(), p.phi(), q.eta(), q.phi()) < dr_cut
                   for q in hard_others):
            return True
    return False


def p4(o):
    v = ROOT.TLorentzVector()
    v.SetPtEtaPhiM(o.pt(), o.eta(), o.phi(), o.mass() if hasattr(o, "mass") else 0.0)
    return v


def main(files, nmax, tag, dump=None, pho_id=True, muon_only=False,
         overlap_pt=0.0):
    events = Events(files)
    h_pk = Handle("std::vector<pat::PackedGenParticle>")
    h_pr = Handle("std::vector<reco::GenParticle>")   # prunedGenParticles
    h_ph = Handle("std::vector<pat::Photon>")
    h_el = Handle("std::vector<pat::Electron>")
    h_mu = Handle("std::vector<pat::Muon>")
    h_gj = Handle("std::vector<reco::GenJet>")

    n_ev = n_sel = 0
    cf = Counter()          # cutflow, to tell a broken selection from a rare one
    cat = Counter()
    cat_h3 = Counter()      # additionally inside 90 < m_llg < 180 (hzg_h3_mass_*)
    n_h3 = 0
    cat_or = Counter()      # additionally surviving DY/Zgamma overlap removal
    n_or = 0
    cat_ch = Counter()      # (channel, category), to match the AN's two columns
    pdg_of_other = Counter()
    # per-photon record of the match, to reproduce the AN's Figure "generator
    # level photon pT of the matched truth particle" and see whether our sample
    # has its spike at 0 GeV at all
    dump_fh = open(dump, "w") if dump else None
    if dump_fh:
        dump_fh.write("# pho_pt pho_eta near_dr near_pt near_pdg cat channel "
                      "m_ll pt_ll m_llg pt_llg or_pass "
                      "n_genjet gj_mindr gj_pt\n")
    t0 = time.time()

    for ev in events:
        if nmax and n_ev >= nmax:
            break
        n_ev += 1
        if n_ev % 20000 == 0:
            # heartbeat: the summary only prints at the end, so without this a
            # multi-hour shard is indistinguishable from a hung one
            print("  ... %d events, %d selected, %.0f Hz"
                  % (n_ev, n_sel, n_ev / max(time.time() - t0, 1e-9)))
            sys.stdout.flush()

        # Only ~2.5% of events have a photon that survives ID + electron veto,
        # so read that collection first and skip the rest of the I/O otherwise.
        # packedGenParticles in particular is large and is needed only for the
        # handful of events that pass everything.
        ev.getByLabel("slimmedPhotons", h_ph)
        global PHO_ID, ELE_ID
        if PHO_ID is None or ELE_ID is None:
            # keep trying until an event has both a photon and an electron to
            # read the names off; those events are not counted as analyzed
            if PHO_ID is None and h_ph.product().size():
                PHO_ID = pick_id(h_ph.product()[0], ("mvaPhoID", "wp80"))
            if ELE_ID is None:
                ev.getByLabel("slimmedElectrons", h_el)
                if h_el.product().size():
                    ELE_ID = pick_id(h_el.product()[0],
                                     ("mvaEleID", "iso", "wp90"),
                                     forbidden=("noIso",))
            if PHO_ID is None or ELE_ID is None:
                n_ev -= 1
                continue
            print("resolved IDs: photon=%s  electron=%s" % (PHO_ID, ELE_ID))

        raw_phos = []
        for p in h_ph.product():
            ae = abs(p.superCluster().eta())
            if p.pt() <= 15 or not (ae < 1.4442 or 1.566 < ae < 2.5):
                continue
            cf['pho_kin'] += 1
            # --no-pho-id drops the mvaID and the conversion-safe electron veto,
            # to test whether the photon identification is what separates our
            # composition from the AN's
            if pho_id:
                if not p.photonID(PHO_ID):
                    continue
                cf['pho_id'] += 1
                if p.passElectronVeto() <= 0.5:
                    continue
                cf['pho_eveto'] += 1
            raw_phos.append(p)
        if not raw_phos:
            continue

        ev.getByLabel("slimmedElectrons", h_el)
        ev.getByLabel("slimmedMuons", h_mu)

        # --muon-only drops the electron channel entirely, to match the AOD
        # cross-check where reco::GsfElectron carries no MVA ID
        eles = [] if muon_only else [e for e in h_el.product()
                if e.pt() > 7 and abs(e.eta()) < 2.5 and e.electronID(ELE_ID)]
        mus = []
        for m in h_mu.product():
            if m.pt() <= 5 or abs(m.eta()) >= 2.4 or not m.passed(ROOT.reco.Muon.CutBasedIdMedium):
                continue
            iso = m.pfIsolationR03()
            rel = (iso.sumChargedHadronPt
                   + max(0.0, iso.sumNeutralHadronEt + iso.sumPhotonEt
                         - 0.5 * iso.sumPUPt)) / m.pt()
            if rel < 0.35:
                mus.append(m)
        leps = eles + mus
        if len(eles) >= 2:
            cf['2e'] += 1
        if len(mus) >= 2:
            cf['2mu'] += 1

        # Z candidate: OSSF, lead pt > 25, sublead pt > 15, 80 < m_ll < 100.
        # Built before the photon block so the two legs are counted independently.
        best_z, best_d, best_ch = None, 1e9, None
        for ch, coll in (("ele", eles), ("mu", mus)):
            for i in range(len(coll)):
                for j in range(i + 1, len(coll)):
                    a, b = coll[i], coll[j]
                    if a.charge() + b.charge() != 0:
                        continue
                    if max(a.pt(), b.pt()) <= 25 or min(a.pt(), b.pt()) <= 15:
                        continue
                    z = p4(a) + p4(b)
                    if not (80.0 < z.M() < 100.0):
                        continue
                    if abs(z.M() - MZ) < best_d:
                        best_z, best_d, best_ch = z, abs(z.M() - MZ), ch
        if best_z is not None:
            cf['has_Z'] += 1

        # dR > 0.3 against every signal lepton, not just the two forming the Z
        phos = [p for p in raw_phos
                if not any(dr(p.eta(), p.phi(), l.eta(), l.phi()) <= 0.3
                           for l in leps)]
        if phos:
            cf['has_photon'] += 1
        if not phos or best_z is None:
            continue

        ev.getByLabel("packedGenParticles", h_pk)
        packed = h_pk.product()
        g = max(phos, key=lambda x: x.pt())
        h = best_z + p4(g)
        cf['pho+Z'] += 1
        if best_z.M() + h.M() <= 185.0:
            continue
        cf['m_sum>185'] += 1
        if g.pt() / h.M() < 15.0 / 110.0:
            continue

        n_sel += 1
        c, matched = classify_an(g, packed)
        cat[c] += 1
        if 90.0 < h.M() < 180.0:
            n_h3 += 1
            cat_h3[c] += 1
        or_pass = -1                    # -1 = overlap removal not requested
        if overlap_pt > 0:
            ev.getByLabel("prunedGenParticles", h_pr)
            or_pass = 0 if has_me_photon(h_pr.product(), overlap_pt) else 1
            if or_pass:
                n_or += 1
                cat_or[c] += 1
        if dump_fh:
            d = dr(matched.eta(), matched.phi(), g.eta(), g.phi()) if matched else -1
            # ak4 gen jets, to test the claim that they could replace gen
            # photons in the matching: their count, and the dR and pT of the
            # one nearest the reco photon.
            ev.getByLabel("slimmedGenJets", h_gj)
            gj = h_gj.product()
            gj_dr, gj_pt = -1.0, -1.0
            for j in gj:
                dj = dr(j.eta(), j.phi(), g.eta(), g.phi())
                if gj_dr < 0 or dj < gj_dr:
                    gj_dr, gj_pt = dj, j.pt()
            # everything from m_ll onward is appended at the end, so files
            # written before these columns existed still parse.
            dump_fh.write("%.3f %.3f %.4f %.3f %d %s %s %.4f %.4f %.4f %.4f %d "
                          "%d %.4f %.3f\n"
                          % (g.pt(), g.eta(), d,
                             matched.pt() if matched else -1,
                             matched.pdgId() if matched else 0, c, best_ch,
                             best_z.M(), best_z.Pt(), h.M(), h.Pt(), or_pass,
                             gj.size(), gj_dr, gj_pt))
        cat_ch[best_ch + "_" + c] += 1
        if c == "other" and matched is not None:
            pdg_of_other[abs(matched.pdgId())] += 1

    if dump_fh:
        dump_fh.close()
    dt = time.time() - t0
    print("files  : %d,  tag: %s" % (len(files), tag))
    print("events read : %d in %.0f s (%.1f Hz),  passing full HZg baseline: %d"
          % (n_ev, dt, n_ev / max(dt, 1e-9), n_sel))
    # 2e/2mu/has_Z are counted only for events that already have an ID'd photon
    print("  cutflow (events): " + ", ".join("%s=%d" % (k, cf[k]) for k in
          ("2e", "2mu", "has_Z", "has_photon", "pho+Z", "m_sum>185")))
    print("  cutflow (photons): " + ", ".join("%s=%d" % (k, cf[k]) for k in
          ("pho_kin", "pho_id", "pho_eveto")))

    # machine-readable, so parallel shards can simply be summed
    out = {"tag": tag, "pho_id": pho_id, "files": len(files), "n_ev": n_ev, "n_sel": n_sel,
           "cutflow": dict(cf), "cat": dict(cat), "cat_ch": dict(cat_ch),
           "n_h3": n_h3, "cat_h3": dict(cat_h3),
           "n_or": n_or, "cat_or": dict(cat_or), "overlap_pt": overlap_pt,
           "pdg_of_other": dict((str(k), v) for k, v in pdg_of_other.items())}
    print("RESULT_JSON " + json.dumps(out, sort_keys=True))

    if n_sel == 0:
        return
    print("\n--- AN-22-027 classification ---")
    for k, lab in (("pileup", "Pile-up photon"), ("jet", "Jet photon"),
                   ("other", "Other particle")):
        n = cat[k]
        err = 100.0 * math.sqrt(max(n, 1) * (1.0 - float(n) / n_sel)) / n_sel
        print("  %-15s %6d = %5.1f%% +- %.1f" % (lab, n, 100.0 * n / n_sel, err))
    if n_or:
        print("\n--- same, additionally after DY/Zgamma overlap removal (n=%d) ---"
              % n_or)
        for k, lab in (("pileup", "Pile-up photon"), ("jet", "Jet photon"),
                       ("other", "Other particle")):
            n = cat_or[k]
            err = 100.0 * math.sqrt(max(n, 1) * (1.0 - float(n) / n_or)) / n_or
            print("  %-15s %6d = %5.1f%% +- %.1f" % (lab, n, 100.0 * n / n_or, err))
    if n_h3:
        print("\n--- same, additionally inside 90 < m_llg < 180 (n=%d) ---" % n_h3)
        for k, lab in (("pileup", "Pile-up photon"), ("jet", "Jet photon"),
                       ("other", "Other particle")):
            n = cat_h3[k]
            err = 100.0 * math.sqrt(max(n, 1) * (1.0 - float(n) / n_h3)) / n_h3
            print("  %-15s %6d = %5.1f%% +- %.1f" % (lab, n, 100.0 * n / n_h3, err))
    print("\n  AN Table (2017 UL): pile-up 48.8/50.0%%, photon 45.5/44.6%%, rest ~6%%"
          "   (electron/muon channel)")
    if pdg_of_other:
        print("\n  matched-particle pdgId of the 'other' class:")
        for pid, n in pdg_of_other.most_common(8):
            print("    %6d : %d" % (pid, n))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--filelist", required=True,
                    help="text file with one input file (LFN or xrootd URL) per line")
    ap.add_argument("--nmax", type=int, default=0, help="0 = all")
    ap.add_argument("--tag", default="", help="label carried into RESULT_JSON")
    ap.add_argument("--redirector", default="root://cms-xrd-global.cern.ch/")
    ap.add_argument("--overlap-pt", type=float, default=0.0,
                    help="DY/Zgamma overlap-removal photon pT threshold "
                         "(9.0 for Run 2, 10.0 for Run 3; 0 disables)")
    ap.add_argument("--muon-only", action="store_true",
                    help="use only the muon channel for the Z")
    ap.add_argument("--no-pho-id", dest="pho_id", action="store_false",
                    help="skip the photon mvaID WP80 and electron veto")
    ap.add_argument("--dump", default=None,
                    help="write one line per selected photon with its match")
    a = ap.parse_args()

    flist = []
    with open(a.filelist) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            flist.append(a.redirector + line if line.startswith("/store/") else line)
    if not flist:
        sys.exit("empty file list: %s" % a.filelist)
    main(flist, a.nmax, a.tag, a.dump, a.pho_id, a.muon_only, a.overlap_pt)
