# Photon-origin classification and the DYcentral comparison plots

These are the two things behind the `DYfilter vs DYcentral` shape comparison:
the truth matching that defines the three photon classes, and the plotter that
draws them.

They are **analysis-side** scripts, not part of the production. They live here
so the plots the production is judged by can be reproduced from this
repository rather than described in an e-mail.

## `an_classify_miniaod.py` — the truth matching

Classifies each reconstructed photon as **pile-up / jet photon / other**,
following AN-22-027 Appendix *Drell-Yan MC sample extension* literally:

```
1. take the nearest status-1 gen particle of ANY kind, whatever its pT
2. pile-up      if it is farther than dR = 0.1, OR fails pT > 5 GeV
3. jet photon   if it is a photon
4. other        otherwise
```

The order matters and is **not** the same as "nearest particle above 5 GeV" —
a soft particle sitting closer than a hard one makes the photon pile-up, it
does not fall through to the hard one. If you get a different table from the
same events, this is the first thing to compare.

It runs on **MiniAOD**, not AOD or NanoAOD, because `packedGenParticles` is the
complete status-1 record — which is all this classification needs, no ancestry
— and pat objects carry the analysis IDs, so the real baseline can be applied
instead of a hand-rolled approximation.

```bash
# inside CMSSW (FWLite) -- must be python3, not python
python3 an_classify_miniaod.py --filelist <txt> --tag <label> [--nmax N]
python3 an_merge_shards.py <shard logs>     # sums the RESULT_JSON lines
```

Each shard prints one `RESULT_JSON` line, so shards can be run in parallel and
summed afterwards with `an_merge_shards.py`.

### Doing this from NanoAOD instead

MiniAOD is deleted by the production (it would have cost ~8.8 TB), so the
classification cannot be run on the production output as it stands. Two gen
keep rules were added to the cmsDriver steps in `job/*.sh` to make NanoAOD
carry enough to reproduce it:

```python
process.prunedGenParticles.select.append(
    'keep++ (abs(pdgId)==111 || abs(pdgId)==221) && pt > 5')
process.prunedGenParticles.select.append('keep status == 1 && pt > 0.5')
#   ... and the same on process.finalGenParticles for the NANOAOD step
```

Validated on the same 1,649 photons of a MiniAOD-preserving batch: **93.4%
per-photon agreement**, `jet γ` fraction 27.0% (MiniAOD) vs 27.3% (NanoAOD).
Dropping the second rule takes agreement down to 86.8% and inflates `jet γ` to
32.2%.

That number is measured on a **loose** population (`pT > 15`, `|η| < 2.5`
only). On the analysis population (adding WP80 + electron veto) agreement is
96.3%, but only 82 photons survive — a ±5 point statistical error, which is
not enough to quote a bias. More MiniAOD-preserving jobs would fix that;
`../tools/make_keepmini_payload.py` builds the payload for them.

## `plot_dycentral_compare.py` — the comparison plots

Three comparisons, all normalized to unit area, because what is being tested is
whether the **shapes** agree — the yields are pinned by construction:

| `--mode` | what it draws |
|---|---|
| `classes` | DYcentral pile-up vs jet vs other — what the three origins look like |
| `mix` | DYcentral pile-up vs DYmix — does event mixing reproduce its target? |
| `filter` | DYcentral jet vs DYfilter — does the gen filter reproduce the jet-photon population it boosts? |

```bash
python3 plot_dycentral_compare.py --mode filter --era 2022postEE \
        --filter-dir root_DYfilter_hzg/Bkg_MC/DYfilter --outdir <dir>
```

Two things worth knowing before reading a plot from it:

* **The variable list, binning and axis titles are read at run time** from the
  dataVmc plotter's `CATEGORY_CONFIG`, so these plots cannot drift away from
  the analysis decks. That is also why it needs a HiggsDNA checkout (below).
* **`--filter-genmatch` is off by default.** Without it the *whole* filter
  sample is treated as jet-photon while the central side is truth matched —
  the two sides are then not the same object. The gen filter only guarantees a
  π⁰/η photon exists *somewhere* in the event; it does not guarantee the
  *selected* photon is that one. In 2022postEE, 35.8% of the photons the
  analysis selects in the filter sample are `genPartFlav == 1`, i.e. genuine
  photons that do not belong in the jet class.

### Paths it needs

Three defaults point at the author's area. Override them with environment
variables — nothing else in the script is site-specific:

| variable | what it must point at | default |
|---|---|---|
| `HZG_HIGGSDNA` | a `higgsdna-hzg-run3` checkout (supplies the dataVmc plotter and the lumi constants) | `/afs/cern.ch/work/p/pelai/HZgamma/higgsdna-hzg-run3` |
| `HZG_ROOT_BASE` | directory holding `root_DYcentral/`, `root_DYfilter*/`, `root_*mix/` | `/eos/project/h/htozg-dy-privatemc/pelai/HZg` |
| `HZG_DYMIX_DIR` | which DYmix version `--mode mix` reads | `root_stratcell3/DYmix` |

The classified central-DY ntuples are world-readable at

```
$HZG_ROOT_BASE/root_DYcentral/DYcentral_{jet,pileup,other}/<era>.root
```

so `--mode filter` and `--mode classes` can be run without redoing the
MiniAOD scan.

### Error bars in `--mode mix`

They are deliberately **not** `sqrt(sum w^2)`. Every mixed event that shares a
photon is correlated — a photon is reused ~150 times — so the naive error
understates the uncertainty by roughly `sqrt(reuse)` and would make the mixed
sample look far more precise than it is. The error is summed per photon donor
instead:

```
err^2 = sum_over_donors ( sum_of_weights_from_that_donor_in_this_bin )^2
```
