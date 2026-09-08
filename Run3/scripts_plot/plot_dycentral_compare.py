"""Shape comparisons in the BDT training variables.

Three comparisons, all normalized to unit area because what matters is whether
the shapes agree, not the yields (the yields are pinned by construction):

  classes  DYcentral pile-up vs jet vs other -- what the three photon origins
           actually look like.
  mix      DYcentral pile-up vs DYmix -- does event mixing reproduce the
           population it stands in for?
  filter   DYcentral jet vs DYfilter -- does the gen-filter production reproduce
           the jet-photon population it boosts?

The variable list, binning and axis titles are read from
plot_dataVmc_root_disjoint.py's CATEGORY_CONFIG at run time, so these plots and
the dataVmc decks cannot drift apart.

DYmix error bars are NOT sqrt(sum w^2). Every mixed event sharing a photon is
correlated -- a photon is reused ~150 times -- so the naive error understates
the uncertainty by roughly sqrt(reuse) and would make the mixed sample look far
more precise than it is. The error is summed per photon donor instead:
    err^2 = sum_over_donors ( sum_of_weights_from_that_donor_in_this_bin )^2

    python3 plot_dycentral_compare.py --mode classes --era 2018 --outdir <dir>
"""
from __future__ import print_function
import argparse
import os
import re
import sys

import numpy as np
import uproot
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)

# The three paths below point into a HiggsDNA checkout and the shared project
# space. They are the author's defaults; override them with the environment
# variables if your checkout lives elsewhere -- nothing else in this script is
# site-specific.
#
#   HZG_HIGGSDNA   root of a higgsdna-hzg-run3 checkout (supplies both the
#                  dataVmc plotter and the lumi constants)
#   HZG_ROOT_BASE  directory holding root_DYcentral/ root_DYfilter*/ root_*mix/
HIGGSDNA = os.environ.get(
    "HZG_HIGGSDNA", "/afs/cern.ch/work/p/pelai/HZgamma/higgsdna-hzg-run3")
CONVERTER_PLOT = os.path.join(
    HIGGSDNA, "plot/scripts/plot_dataVmc_root_disjoint.py")
BASE = os.environ.get(
    "HZG_ROOT_BASE", "/eos/project/h/htozg-dy-privatemc/pelai/HZg")
# v3 (stratified pairing + two-stage pinning). HZG_DYMIX_DIR=DYmix goes back
# to the old --pair random product for comparison.
DYMIX_DIR = os.environ.get("HZG_DYMIX_DIR", "root_stratcell3/DYmix")
LW = 3
LEFT, RIGHT, TOP = 0.17, 0.04, 0.09
# Pad-2 bottom margin. 0.34 clipped the x-axis title off the canvas.
BOT2 = 0.42
# Gap between the two pads. Without it they touch, and pad 1's lowest y
# label sits on top of pad 2's highest one -- both are drawn, so the
# collision is only visible once the figure is rendered.
GAP = 0.010
TITLE_SIZE, LABEL_SIZE = 0.055, 0.050
LEGEND_SIZE, CMS_SIZE, LUMI_SIZE = 0.045, 0.055, 0.045
# Pad heights. EVERY text size set inside a pad -- axis titles, axis labels,
# TLegend, TLatex -- is relative to THAT PAD, not to the canvas. So a convention
# value has to be divided by the pad height to render at the intended size.
# Getting this right for the axes but not the legend (the first version here)
# silently rendered the legend and the CMS label 30% too small, and nothing in
# the code looked wrong: both said 0.045.
P1_H, P2_H = 0.70, 0.30

CME = {"2016preVFP": "13 TeV", "2016postVFP": "13 TeV", "2017": "13 TeV",
       "2018": "13 TeV"}

# Era groups. Combining eras REQUIRES luminosity weighting: every sample here is
# normalized per pb^-1, so an unweighted sum would let 2016preVFP count as much
# as 2018 and the "combined" shape would be an average of eras rather than of
# the data. 2025/2026 have no DY MC, so Run 3 stops at 2024.
ERA_GROUPS = {
    "Run2": ["2016preVFP", "2016postVFP", "2017", "2018"],
    "Run3": ["2022preEE", "2022postEE", "2023preBPix", "2023postBPix", "2024"],
    "full": ["2016preVFP", "2016postVFP", "2017", "2018",
             "2022preEE", "2022postEE", "2023preBPix", "2023postBPix", "2024"],
}
GROUP_CME = {"Run2": "13 TeV", "Run3": "13.6 TeV", "full": "13 + 13.6 TeV"}
GROUP_LABEL = {"Run2": "Run 2", "Run3": "Run 3", "full": "Run 2 + Run 3"}


LUMI_CONSTANTS = os.path.join(
    HIGGSDNA, "higgs_dna/metaconditions/corrections/constants.py")


def load_lumi():
    """LUMI[fb^-1] per era, parsed from constants.py -- the authority.

    This used to scrape `LUMI = {` out of the p2root converter. On 2026-08-27
    the converter was changed to `LUMI = _load_lumi_from_constants()`, so the
    scrape raised ValueError -- and because it only fires for the era GROUPS,
    the per-era plots still rendered while Run2/Run3/full silently kept their
    previous versions. A deck built afterwards embedded those stale figures and
    looked completely normal (its mtime was newer than the plots').

    Parsed with ast, not imported: constants.py's ERA dict uses set literals as
    keys, so importing it raises. Failure here is fatal on purpose.
    """
    import ast as _ast
    with open(LUMI_CONSTANTS) as fh:
        tree = _ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, _ast.Assign) and any(
                getattr(t, "id", None) == "LUMI" for t in node.targets):
            return _ast.literal_eval(node.value)
    raise SystemExit("no LUMI dict in %s" % LUMI_CONSTANTS)


def load_category_config():
    """CATEGORY_CONFIG straight out of the dataVmc plotter."""
    src = open(CONVERTER_PLOT).read()
    i = src.index("CATEGORY_CONFIG = {")
    depth, j = 0, i
    while True:
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    ns = {}
    exec(src[i:j + 1], ns)
    return ns["CATEGORY_CONFIG"]


def unit_from_title(title):
    """The unit inside the axis title's brackets, if it has one.

    CATEGORY_CONFIG carries the unit in the title itself ("p_{T}(#gamma) [GeV]"),
    so the y-axis bin width can be labelled without a second table to keep in
    sync.
    """
    m = re.search(r"\[([^\]]+)\]\s*$", title)
    return m.group(1) if m else ""


def fmt_bin_width(w):
    """Bin width as a short human-readable number (2, 0.05, 2.5, 1e-3)."""
    if w <= 0:
        return ""
    if w >= 1:
        return ("%.0f" % w) if abs(w - round(w)) < 1e-9 else ("%.3g" % w)
    return "%.3g" % w


def correlated_error(bin_idx, weights, donor, n_bins):
    """Error per bin with events sharing a photon donor treated as one block."""
    err2 = np.zeros(n_bins)
    if len(bin_idx) == 0:
        return err2
    key = bin_idx.astype(np.int64) * (donor.max() + 2) + donor.astype(np.int64)
    uniq, inv = np.unique(key, return_inverse=True)
    block = np.bincount(inv, weights=weights, minlength=len(uniq))
    block_bin = (uniq // (donor.max() + 2)).astype(np.int64)
    np.add.at(err2, block_bin, block ** 2)
    return err2


def fill(path, tree, var, weight_br, lo, hi, nb, cut=None, donor_br=None,
         lumi_pb=1.0, donor_offset=0):
    """(sum of weights per bin, error^2 per bin, entries used).

    `lumi_pb` scales the per-pb^-1 weights up to that era's luminosity, which is
    what makes eras addable. `donor_offset` keeps photon-donor indices distinct
    across eras -- without it two eras' donor 0 would be treated as the same
    photon and their contributions merged into one correlated block.
    """
    with uproot.open(path) as f:
        keys = [k.split(";")[0] for k in f.keys()]
        if tree not in keys:
            return None
        # `cut` is either ("branch", value) for equality, or
        # (("br1", "br2", ...), fn) where fn(arrays) returns a boolean mask --
        # needed for cuts that are ranges rather than a single value.
        cut_brs = []
        if cut:
            cut_brs = [cut[0]] if isinstance(cut[0], str) else list(cut[0])
        need = [var, weight_br] + cut_brs + ([donor_br] if donor_br else [])
        arr = f[tree].arrays([n for n in dict.fromkeys(need)], library="np")
    v = arr[var].astype(np.float64)
    w = arr[weight_br].astype(np.float64)
    mask = np.isfinite(v) & (v > -998.0)
    if cut:
        mask &= ((arr[cut[0]] == cut[1]) if isinstance(cut[0], str)
                 else cut[1](arr))
    v, w = v[mask], w[mask]
    if not len(v):
        return None
    edges = np.linspace(lo, hi, nb + 1)
    b = np.digitize(v, edges) - 1
    keep = (b >= 0) & (b < nb)
    b, w2 = b[keep], w[keep]
    w2 = w2 * lumi_pb
    sums = np.bincount(b, weights=w2, minlength=nb)
    if donor_br:
        d = arr[donor_br][mask][keep].astype(np.int64) + donor_offset
        err2 = correlated_error(b, w2, d, nb)
    else:
        err2 = np.bincount(b, weights=w2 ** 2, minlength=nb)
    return sums, err2, int(keep.sum())


def trees_for(region, cat):
    """Tree names for a region spec. `SR+Sideband` means read both and add."""
    return ["%s__%s" % (r, cat) for r in region.split("+")]


def to_hist(name, sums, err2, lo, hi, nb, color):
    h = ROOT.TH1D(name, "", nb, lo, hi)
    h.Sumw2()
    tot = sums.sum()
    if tot > 0:
        for i in range(nb):
            h.SetBinContent(i + 1, sums[i] / tot)
            h.SetBinError(i + 1, np.sqrt(err2[i]) / tot)
    h.SetLineColor(color)
    h.SetLineWidth(LW)
    h.SetMarkerColor(color)
    return h


def draw(name, series, title, unit, lo, hi, nb, outdir, label, cme, ratio_of,
         errors=True, ratio_title="Ratio"):
    hs = [(t, to_hist("h%d_%s" % (i, name), s, e, lo, hi, nb, c), n)
          for i, (t, s, e, c, n) in enumerate(series)]
    c = ROOT.TCanvas("c_" + name, "", 800, 800)
    p1 = ROOT.TPad("p1", "", 0, P2_H + GAP, 1, 1)
    p2 = ROOT.TPad("p2", "", 0, 0.0, 1, P2_H)
    p1.SetLeftMargin(LEFT); p1.SetRightMargin(RIGHT)
    p1.SetTopMargin(TOP); p1.SetBottomMargin(0.03)
    p2.SetLeftMargin(LEFT); p2.SetRightMargin(RIGHT)
    p2.SetTopMargin(0.05); p2.SetBottomMargin(BOT2)
    p1.Draw(); p2.Draw()

    p1.cd()
    top = max(h.GetMaximum() for _, h, _ in hs)
    y_unit = unit_from_title(title)
    y_title = "A.U. / %s%s" % (fmt_bin_width((hi - lo) / float(nb)),
                               (" " + y_unit) if y_unit else "")
    for i, (_, h, _) in enumerate(hs):
        h.GetYaxis().SetTitle(y_title)
        h.GetYaxis().SetTitleSize(TITLE_SIZE / P1_H)
        h.GetYaxis().SetLabelSize(LABEL_SIZE / P1_H)
        h.GetYaxis().SetTitleOffset(1.15)
        # Fewer labels so none lands on the pad's bottom edge, where the
        # 0.02 margin clips it against pad 2.
        h.GetYaxis().SetNdivisions(505)
        h.GetXaxis().SetLabelSize(0)
        h.SetMaximum(1.55 * top)
        h.SetMinimum(0.0)
        h.Draw(("HIST E" if errors else "HIST") + (" SAME" if i else ""))

    row = 0.075 / P1_H   # convention is 0.075 per row on the canvas
    leg = ROOT.TLegend(0.34, 0.90 - row * (len(hs) + 1), 0.94, 0.90)
    leg.SetBorderSize(0); leg.SetFillStyle(0); leg.SetTextSize(LEGEND_SIZE / P1_H)
    leg.SetHeader("DY MC   %s" % label)
    for t, h, n in hs:
        leg.AddEntry(h, "%s  (%s)" % (t, format(n, ",")) if n else t, "l")
    leg.Draw()
    tex = ROOT.TLatex(); tex.SetNDC(); tex.SetTextFont(42)
    tex.SetTextSize(CMS_SIZE / P1_H)
    # 0.945 sat right at the canvas edge once TOP grew to 0.09.
    tex.DrawLatex(LEFT, 0.925, "#bf{CMS} #it{Simulation}")
    tex.SetTextSize(LUMI_SIZE / P1_H); tex.SetTextAlign(31)
    tex.DrawLatex(1.0 - RIGHT, 0.925, cme)

    p2.cd()
    ref = hs[ratio_of][1]
    # Kept in a list on purpose: a Clone() bound only to a loop variable is
    # garbage-collected by Python as soon as the next iteration rebinds it, and
    # ROOT then drops it from the pad -- only the last ratio would be drawn.
    ratios = []
    for i, (_, h, _) in enumerate(hs):
        if i == ratio_of:
            continue
        r = h.Clone("r%d_%s" % (i, name))
        r.Divide(ref)
        r.GetYaxis().SetTitle(ratio_title)
        r.GetXaxis().SetTitle(title + (" [%s]" % unit if unit else ""))
        # 0.85 of the convention: at full size the ratio pad's labels are
        # visually heavier than pad 1's, because the pad is 0.30 tall and
        # every size is divided by that.
        for ax, off in ((r.GetXaxis(), 1.0), (r.GetYaxis(), 0.52)):
            ax.SetTitleSize(TITLE_SIZE / P2_H * 0.85)
            ax.SetLabelSize(LABEL_SIZE / P2_H * 0.85)
            ax.SetTitleOffset(off)
        r.GetYaxis().SetNdivisions(505)
        # Push the tick labels down: the ratio pad is only 0.30 tall, so its
        # labels sit close under the frame and collide with the y labels.
        r.GetXaxis().SetLabelOffset(0.020)
        r.SetMinimum(0.0); r.SetMaximum(2.0)
        r.Draw(("E" if errors else "HIST") + ("" if not ratios else " SAME"))
        ratios.append(r)
    line = ROOT.TLine(lo, 1.0, hi, 1.0)
    line.SetLineStyle(2); line.SetLineColor(ROOT.kGray + 2); line.Draw()
    for r in ratios:
        r.Draw(("E SAME" if errors else "HIST SAME"))  # keep them above the guide line

    os.makedirs(outdir, exist_ok=True)
    for ext in ("pdf", "png"):
        c.SaveAs(os.path.join(outdir, "%s.%s" % (name, ext)))


def main(a):
    cfg = load_category_config()
    variables = {}
    for cat in ("ggF", "VBF"):
        for v, d in cfg[cat].items():
            variables.setdefault(v, (d, cat))

    cme = CME.get(a.era, "13.6 TeV")
    ratio_title = "Ratio"
    if a.mode == "classes":
        src = "%s/root_DYcentral/DYcentral_all/%s.root" % (BASE, a.era)
        spec = [("Pile-up #gamma", src, ("photon_origin", 0), None, ROOT.kRed + 1),
                ("Jet #gamma", src, ("photon_origin", 1), None, ROOT.kGreen + 2),
                ("Others", src, ("photon_origin", 2), None, ROOT.kAzure + 2)]
        ratio_of = 0
    elif a.mode == "mix":
        spec = [("DYcentral pile-up #gamma",
                 "%s/root_DYcentral/DYcentral_pileup/%s.root" % (BASE, a.era),
                 None, None, ROOT.kRed + 1),
                ("DYmix",
                 "%s/root_DYrealmix/%s/%s.root" % (BASE, DYMIX_DIR, a.era),
                 None, "photon_donor_index", ROOT.kBlack)]
        # ratio_of names the DENOMINATOR. Our constructed sample goes there so the
        # ratio is DYcentral/ours and the points inherit the coloured curve.
        ratio_of = 1
        ratio_title = "cent. / DYmix"
    elif a.mode == "pileupsplit":
        # AN-22-027 calls a photon "pile-up" when the nearest status-1 gen
        # particle is either OUTSIDE the dR < 0.1 cone, or inside it but below
        # 5 GeV. Those are two different statements, and the class is only
        # meaningful if they pick the same population. This mode draws them
        # against each other so that can be checked rather than assumed.
        pu = "%s/%s/DYcentral_pileup/%s.root" % (
            BASE, os.environ.get("HZG_DYCENTRAL_DIR", "root_DYcentral"),
            a.era)
        far = (("photon_near_dr",),
               lambda A: (A["photon_near_dr"] < 0) | (A["photon_near_dr"] > 0.1))
        soft = (("photon_near_dr", "photon_near_pt"),
                lambda A: (A["photon_near_dr"] >= 0) & (A["photon_near_dr"] <= 0.1)
                & (A["photon_near_pt"] <= 5.0))
        # Short labels: the entry also carries a 6-digit count, and the long
        # form ran past the frame.
        spec = [("#DeltaR > 0.1", pu, far, None, ROOT.kBlack),
                ("#DeltaR < 0.1, p_{T} < 5", pu, soft, None, ROOT.kRed + 1)]
        ratio_of = 0
    elif a.mode == "other":
        # `other` has no model of its own: AN-22-027 absorbs it into the pile-up
        # and jet classes at the KS-best ratio r. This mode draws that fit --
        # `other` against r x pile-up + (1-r) x jet -- so the absorption can be
        # judged instead of assumed. r is measured on m_llgamma, once per era,
        # and then used for every variable (the AN determines it on m_llgamma).
        #
        # The two ingredients are DYcentral's OWN classes, not DYmix/DYfilter:
        # that is the mixture the KS fit was performed on.
        # kAzure+2 is what `classes` uses for Others -- the same class should
        # not change colour between figures.
        spec = [("DYcentral other #gamma",
                 "%s/root_DYcentral/DYcentral_other/%s.root" % (BASE, a.era),
                 None, None, ROOT.kAzure + 2),
                ("_pileup",
                 "%s/root_DYcentral/DYcentral_pileup/%s.root" % (BASE, a.era),
                 None, None, ROOT.kRed + 1),
                ("_jet",
                 "%s/root_DYcentral/DYcentral_jet/%s.root" % (BASE, a.era),
                 None, None, ROOT.kRed + 1)]
        # ratio_of names the DENOMINATOR: `other` is the thing being modelled,
        # so it goes on the bottom and the panel reads fit / other -- how well
        # the absorbed mixture reproduces it.
        ratio_of = 0
        ratio_title = "fit / other"
    else:
        # --central-v2 switches the reference from the MiniAOD-scan DYcentral to
        # the HiggsDNA-processed central DY. That is the whole point of the v2
        # round: both sides then carry the SAME corrections (photon SaS, PU,
        # SF, JER), so a residual difference is physics and not framework.
        # The v2 product is one sample, not three, so the jet class is selected
        # by the AN-style cut on the gen-jet columns instead of by file.
        # ⚠️ `other` is NOT separable in NanoAOD (pruning removes the hadrons
        # that define it), so this cut selects jet+other -- see the doc. The
        # MiniAOD reference splits them; the two are compared on jet+other.
        if a.central_v2:
            # An absolute --central-dir is used as-is: the v2 central DY lives on
            # eoscms (condor cannot create directories under /eos/project), which
            # is a different root from BASE. Silently joining it to BASE produced
            # a path that never existed and the run still printed "wrote 0
            # variables ... DONE".
            _cd = a.central_dir
            _cen_path = ("%s/%s.root" % (_cd, a.era) if _cd.startswith("/")
                         else "%s/%s/%s.root" % (BASE, _cd, a.era))
            cen = ("central DY jet #gamma (v2)",
                   _cen_path,
                   # fill() calls cut[1](arr) with the WHOLE array dict, so the
                   # callable takes one argument and picks its own branches.
                   (("photon_near_genjet_dr", "photon_near_genjet_pt"),
                    lambda a: (a["photon_near_genjet_dr"] < 0.1)
                              & (a["photon_near_genjet_pt"] > 5.0)),
                   None, ROOT.kGreen + 2)
        else:
            cen = ("DYcentral jet #gamma",
                   "%s/root_DYcentral/DYcentral_jet/%s.root" % (BASE, a.era),
                   None, None, ROOT.kGreen + 2)
        spec = [cen,
                ("DYfilter" + (" (non-prompt)" if a.filter_genmatch
                                else ""),
                 "%s/%s/%s.root" % (BASE, a.filter_dir, a.era),
                 # The gen filter only guarantees a pi0/eta photon exists SOMEWHERE
                 # in the event; the photon the analysis actually selected may be a
                 # different, prompt one. Measured 2022postEE: 35.8% of DYfilter's
                 # selected photons are genPartFlav==1, i.e. real (FSR) photons that
                 # do not belong in the jet class at all. DYcentral_jet is a
                 # reco-level truth-matched class, so without this cut the two
                 # samples are different POPULATIONS and the comparison is not a
                 # closure test. Dropping them takes <n_jets> from 2.29x to 1.31x.
                 ("photon_genPartFlav", 0) if a.filter_genmatch else None,
                 None, ROOT.kBlack)]
        # ratio_of names the DENOMINATOR. Our constructed sample goes there so the
        # ratio is DYcentral/ours and the points inherit the coloured curve.
        ratio_of = 1
        ratio_title = "cent. / DYfilter"

    # An era group is summed over its member eras, each scaled to its own
    # luminosity. Missing eras are reported, never silently dropped -- a
    # "Run 3" plot that quietly excludes 2024 looks perfectly normal.
    if a.era in ERA_GROUPS:
        lumi = load_lumi()
        eras, missing = [], []
        for e in ERA_GROUPS[a.era]:
            paths = [p.replace("/%s.root" % a.era, "/%s.root" % e)
                     for _, p, _, _, _ in spec]
            (eras if all(os.path.exists(p) for p in paths) else missing).append(e)
        if missing:
            print("  WARNING %s excludes %s (sample not on disk)"
                  % (a.era, ", ".join(missing)))
        if not eras:
            sys.exit("no era of %s has both samples on disk" % a.era)
        total_lumi = sum(lumi.get(e, 0.0) for e in eras)
        label = "%s  %.1f fb^{-1}" % (GROUP_LABEL[a.era], total_lumi)
        cme = GROUP_CME[a.era]
        print("  %s = %s (%.1f fb^-1)" % (a.era, " + ".join(eras), total_lumi))
    else:
        eras, label = [a.era], a.era

    # --- KS-best pile-up fraction, measured once on m_llgamma -------------
    # Same routine build_composite.py uses, imported rather than copied: a second
    # implementation of the same fit would drift from the tables silently.
    ks_r = None
    if a.mode == "other":
        from build_composite import ks_best_ratio
        KSVAR = "m_llg_refit"
        if KSVAR not in variables:
            sys.exit("mode 'other' needs %r in the variable set" % KSVAR)
        dk, catk = variables[KSVAR]
        lok, hik = dk["range"]
        treesk = trees_for(a.region, catk)
        comp = []
        for _, path, cut, donor, _ in spec:
            acc = np.zeros(dk["bins"])
            for ei, e in enumerate(eras):
                p = path.replace("/%s.root" % a.era, "/%s.root" % e)
                if not os.path.exists(p):
                    continue
                wl = (load_lumi().get(e, 0.0) * 1000.0
                      if a.era in ERA_GROUPS else 1.0)
                for tk in treesk:
                    got = fill(p, tk, KSVAR, a.weight, lok, hik, dk["bins"],
                               cut, donor, lumi_pb=wl,
                               donor_offset=ei * 100000000)
                    if got is not None:
                        acc += got[0]
            comp.append(acc)
        ks_r, ks_d, _ = ks_best_ratio(comp[1], comp[2], comp[0])
        print("  KS-best on %s: r = %.2f pile-up : %.2f jet   (D = %.4f)"
              % (KSVAR, ks_r, 1.0 - ks_r, ks_d))
        if ks_d > 1.0:
            print("  WARNING D = %.2f is not a legal KS distance -- the `other` "
                  "histogram is negative-weight dominated here, so r is "
                  "meaningless" % ks_d)

    n_ok = 0
    for var, (d, cat) in sorted(variables.items()):
        trees = trees_for(a.region, cat)
        lo, hi = d["range"]
        series = []
        for si, (txt, path, cut, donor, color) in enumerate(spec):
            sums = np.zeros(d["bins"])
            err2 = np.zeros(d["bins"])
            n_ent = 0
            ok = True
            for ei, e in enumerate(eras):
                p = path.replace("/%s.root" % a.era, "/%s.root" % e)
                if not os.path.exists(p):
                    print("  missing %s" % p)
                    ok = False
                    break
                w_lumi = (load_lumi().get(e, 0.0) * 1000.0
                          if a.era in ERA_GROUPS else 1.0)
                got_any = False
                for tn in trees:
                    r = fill(p, tn, var, a.weight, lo, hi, d["bins"], cut, donor,
                             lumi_pb=w_lumi, donor_offset=ei * 100000000)
                    if r is None:
                        continue
                    got_any = True
                    sums += r[0]; err2 += r[1]; n_ent += r[2]
                if not got_any:
                    ok = False
                    break
            if not ok:
                series = []
                break
            series.append((txt, sums, err2, color, n_ent))
        if not series:
            continue
        if ks_r is not None and len(series) == 3:
            # Each ingredient is unit-normalized before mixing, exactly as
            # ks_best_ratio does -- mixing raw sums would weight by yield and
            # give a different curve from the one the fit minimized.
            (_, sp, ep, _, npu) = series[1]
            (_, sj, ej, _, njt) = series[2]
            tp, tj = sp.sum(), sj.sum()
            if tp <= 0 or tj <= 0:
                continue
            smix = ks_r * sp / tp + (1.0 - ks_r) * sj / tj
            emix = (ks_r / tp) ** 2 * ep + ((1.0 - ks_r) / tj) ** 2 * ej
            series = [series[0],
                      ("%.0f%% pile-up + %.0f%% jet #gamma"
                       % (100 * ks_r, 100 * (1.0 - ks_r)),
                       smix, emix, ROOT.kBlack, 0)]
        draw("%s_%s_%s" % (a.mode, a.era, var), series, d["title"],
             "", lo, hi, d["bins"], a.outdir, label, cme, ratio_of,
             errors=not a.no_errors, ratio_title=ratio_title)
        n_ok += 1
    print("%s / %s: wrote %d variables to %s" % (a.mode, a.era, n_ok, a.outdir))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True,
                    choices=("classes", "mix", "filter", "other",
                             "pileupsplit"))
    ap.add_argument("--era", required=True)
    ap.add_argument("--region", default="SR+Sideband",
                    help="tree(s) to read. These are MC-vs-MC comparisons, "
                         "so the default sums SR and Sideband: blinding "
                         "them only punched a hole at 120-130.")
    ap.add_argument("--weight", default="weight")
    # The production writes under Bkg_MC/; the old default pointed one level
    # up at a directory that does not exist, so every --mode filter run had
    # to pass --filter-dir or silently find nothing.
    ap.add_argument("--filter-dir",
                    default="root_DYfilter_hzg/Bkg_MC/DYfilter")
    ap.add_argument("--central-v2", action="store_true",
                    help="use the HiggsDNA-processed central DY as the jet "
                         "reference (same framework as DYfilter) instead of the "
                         "MiniAOD-scan DYcentral")
    ap.add_argument("--central-dir",
                    default="root_DYcentral_v2/Bkg_MC/DYJetsToLL",
                    help="path under BASE for --central-v2")
    ap.add_argument("--filter-genmatch", action="store_true",
                    help="keep only DYfilter photons with genPartFlav==0 "
                         "(non-prompt), so the sample is the same population as "
                         "DYcentral_jet rather than a superset of it")
    ap.add_argument("--no-errors", action="store_true",
                    help="draw lines only. Note the DYmix error bars are the "
                         "CORRELATED ones (photons are reused ~150x); hiding "
                         "them removes the only visible sign of that.")
    ap.add_argument("--outdir", required=True)
    main(ap.parse_args())
