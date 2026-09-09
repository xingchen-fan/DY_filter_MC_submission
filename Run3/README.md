# Run 3 DY filter MC — job submission

Private DY production with a GEN-level π⁰/η filter, so that only events that can
enter the DY + fake photon selection are simulated, saving most of the
SIM/DIGI/RECO CPU. Full chain per job: LHE+GEN → SIM → DIGI+DATAMIX+HLT →
RECO → MINIAOD → NANOAOD → stage-out. Only the NanoAOD is kept.

This directory is self-contained: the job script, the filter source, the
fragments and the premix file lists all travel with the job.

## What changed in the current round (from 2026-09-06)

The sample definition changed, so output from before this date is a **different
sample** and must not be mixed in. Two changes:

**1. A tighter gen filter** (`gen_filter/MatchDYFilter.cc`) — the π⁰/η photon
now also has to have cluster `pT > 10 GeV`, and the event has to have a gen Z
in `75 < m_ll < 105 GeV`. Measured on a 10-job validation batch:

| | old filter | new filter |
|---|---|---|
| 2022postEE | 976 events/job (9.76%) | 303 events/job (3.03%) |
| 2024_2E | — | 145 events/job (1.45%) |

so 3.22x more jobs are needed for the same number of **gen-filtered events**.

That is not the number to plan with. What matters is how many events survive
the analysis baseline, and the two do not scale together -- the new filter
mostly removes events that would have failed the baseline anyway. Measured on
the full 2022postEE productions, per CRAB job, on SR + Sideband with the same
corrections and the same overlap removal on both sides:

| | baseline events | CRAB jobs | per job |
|---|---|---|---|
| old filter | 9,499 | 30,261 | 0.3139 +- 0.0032 |
| new filter | 3,717 | 12,604 | 0.2949 +- 0.0048 |

The ratio is 0.939 +- 0.018: the new filter costs about **6% +- 2%** of the
analysis statistics per job, not a factor of three. Plan with ~1.06x.

Compare like with like if you repeat this. The old production had the control
regions enabled and the new one did not, so summing every `*__inclusive` tree
gives 12,119 vs 3,717 and a spurious 22% deficit. SR + Sideband is the common
basis.

**2. A second gen-particle keep rule** in the cmsDriver steps of `job/*.sh`:

```python
process.prunedGenParticles.select.append('keep status == 1 && pt > 0.5')
#   ... and the same on process.finalGenParticles for the NANOAOD step
```

The first rule (`keep++ ... π⁰/η`) was already there. The new one keeps the
hadrons, which is what lets the AN-22-027 photon-origin classification be
reproduced **from NanoAOD** — the production deletes MiniAOD, so without it the
classification cannot be redone on the output at all. Validated at 93.4%
per-photon agreement against MiniAOD; see `scripts_plot/README.md`.

It costs disk: 12.0 kB/event against 4.5 kB/event before, because status-1
hadrons now dominate the `GenPart` record (π± alone is 44% of it).

`tools/sync_keep_rules.py` is what put the rule into all six payloads — run it
again if you add an era, rather than editing six files by hand.

## Do I need a particular CMSSW?

**No, and there is no shared CMSSW path.** Make your own, anywhere you like.

* **On the worker node** the job builds every release it needs itself, straight
  from cvmfs (`scram p CMSSW ...`): 2022 uses `CMSSW_12_4_11_patch3` +
  `CMSSW_13_0_13`, 2023 uses `CMSSW_13_0_14`, 2024 uses `CMSSW_14_0_19` +
  `CMSSW_14_0_21`. **You do not prepare any of these.**
* **On the submission side** CRAB only needs *some* CMSSW area to build its
  sandbox — `ConfigDY8.py` is a stub pset that never really runs, so the
  version is not important.

⚠️ **The architecture is important.** Every production release above is
`el8_amd64_gcc1x`, and the arch of the release you submit from decides which
container the grid job runs in. So submit from an **el8** release inside
`cmssw-el8`. `CMSSW_13_0_14` is a fine choice; anything el8 works.

## Setup (once per session)

```bash
ssh lxplus
cmssw-el8                       # el8, to match the production releases

# your own CMSSW area, once ever -- any el8 release, any location
cd <YOUR_WORK_DIR>
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el8_amd64_gcc11
scram p CMSSW CMSSW_13_0_14     # skip if you already have one
cd CMSSW_13_0_14/src && eval `scram runtime -sh` && cd -

source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init --rfc --voms cms -valid 192:00

cd <YOUR_COPY_OF>/DY_filter_MC_submission/Run3
```

Replace `<YOUR_WORK_DIR>` and `<YOUR_COPY_OF>` with your own paths — nothing
here depends on where this directory lives, only on being run from inside it.

You need a grid certificate installed first:
[WorkBookStartingGrid](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid).

## Submit

```bash
./submit_run3.sh [--dest <xrootd-url>] <era> <n_tasks> <your_tag> [first_index]
```

* `era` — `2022postEE` | `2023preBPix` | `2023postBPix` | `2024_2E` | `2024_2Mu`
* `n_tasks` — each task is 10,000 jobs (CRAB's per-task limit)
* `your_tag` — **use your initials.** It goes into the request name and the
  output file names, so two people submitting the same era never collide.
* `first_index` — start of the numbering, default 1; use it to continue a series
* `--dest` — output base; see below

Example — 3 tasks (30,000 jobs) of 2022postEE:

```bash
./submit_run3.sh 2022postEE 3 pz
```

### Where the output goes

**Your own subdirectory of the shared project space**, derived from `$USER`:

```
/eos/project/h/htozg-dy-privatemc/<user>/HZg/root_DYfilter/phase1/<era>/<tag>/
```

Everybody contributes to the same project, but nobody ever writes inside
somebody else's directory. The base is created on first use if it is not there
yet (and left alone if it is), so there is nothing to set up.

This needs you to be in the `cernbox-project-htozg-dy-privatemc-writers`
e-group — ask Pei-Zhu to add you. Without it the script stops immediately with
a clear message rather than failing later on the grid.

Use `--dest <xrootd-url>` to write somewhere else entirely, e.g. your own
CERNBox:

```bash
./submit_run3.sh --dest root://eosuser.cern.ch//eos/user/x/xxx/HZg/root_DYfilter \
                 2022postEE 3 pz
```

The progress table below counts what is under the project space, so output
written outside it has to be copied in before it counts.

**Submit one era at a time.** Sending everything at once destroys your grid
priority and slows everyone down.

## How many jobs

The table below is for the OLD filter. For 2022postEE the new filter needs
about **1.06x** these numbers, not 3.22x -- see "What changed in the current
round". 3.22 is the gen-filter efficiency ratio and it does not carry through
to the baseline.

2024 has not been measured this way. Its gen-filter efficiency is much lower
(1.45%), but whether that costs baseline statistics is exactly what the
efficiency ratio cannot tell you -- measure it before scaling the 2024 rows.

For Run 3, assuming jet photon events make up 55% of total DY after baseline,
one fold of statistics needs:

| Era | `era` argument | Existing events after baseline | Number of jobs (10k events/job) |
|-|-|-|-|
| 2022 | `2022preEE` | 13500 | 68000 |
| 2022EE | `2022postEE` | 43700 | 219000 |
| 2023 | `2023preBPix` | 15000 | 75000 |
| 2023BPix | `2023postBPix` | 10000 | 50000 |
| 2024 | `2024_2E`, `2024_2Mu` | 141000 | 707000 |

One job ≈ one output file, and one task = 10,000 jobs, so e.g. 2022EE needs
about 22 tasks for a full fold.

⚠️ **2024 counts double.** It is split by lepton flavor at the LHE level, so
`2024_2E` and `2024_2Mu` are separate productions and the 707,000 above applies
to each — 1,414,000 jobs for a full fold of 2024. (Its gen-filter efficiency is
also only ~2.5%, a quarter of the other eras, so a 2024 job yields ~255 events
instead of ~970.)

**Do not submit a whole fold at once.** Finish one era at a time; flooding the
queue costs everyone their grid priority.

Current progress is tracked in `doc/HZgamma/extended_dy_job_log.md`, counted
from the files actually on EOS. `crab status`'s `finished` agrees with that
count (measured: 1481 finished, 1481 files), so either is fine — but a freshly
submitted task can report 0 finished for a while even though files are already
appearing, because the jobs stage out themselves rather than through CRAB.

## Monitor

```bash
crab status -d crab_projects/crab_DY2022postEE_pz_1
crab resubmit -d crab_projects/crab_DY2022postEE_pz_1   # retry failed jobs
crab kill     -d crab_projects/crab_DY2022postEE_pz_1
```

Output goes to
`/eos/project/h/htozg-dy-privatemc/<user>/HZg/root_DYfilter/phase1/<era>/<tag>/`.
Each task gets its own subdirectory — a single EOS directory starts failing to
list past ~120k files, so do not flatten this.

To count what you produced, use `eos ls`, not `find` or `ls`:

```bash
eos root://eosproject.cern.ch ls <dir> | grep -c '\.root$'
```

`find`/`ls` return **0 with exit code 0** on a directory that large, and
`eos find` silently **truncates at exactly 100,000** — a count of `100000` is a
truncation, not a result.

## What is in here

Tracked — this is the production:

| | |
|---|---|
| `submit_run3.sh` | writes one CRAB config per task and submits |
| `crabConfig_<era>.py` | the six templates; `submit_run3.sh` rewrites name/tag/output |
| `job/<era>DY.sh` | the actual job: cmsDriver chain + stage-out |
| `gen_filter/MatchDYFilter.cc` | the GEN filter, compiled on the worker node |
| `gen_filter/*fragment.py` | generator fragments, one per era |
| `premix_lists/` | premix pileup files known to be on disk |
| `ConfigDY8.py` | CRAB PSet stub (8 threads; must match `numCores`) |
| `tools/` | helpers: keep-rule sync, MiniAOD-preserving payload, validation-batch check |
| `scripts_plot/` | photon-origin truth matching and the DYcentral comparison plots — see its own README |

Not tracked (in `.gitignore`) — machine-local, regenerated, or personal:

| | |
|---|---|
| `crab_projects/` | CRAB task state; `crab status`/`resubmit` read it |
| `crab_configs/` | the per-task configs `submit_run3.sh` generates from the templates |
| `local/` | your logs, watchdogs and one-off submission scripts. Nothing in the pipeline reads it — the author's are left in place as worked examples |

## Tools

```bash
python3 tools/sync_keep_rules.py          # put the gen keep rules into job/*.sh
python3 tools/make_keepmini_payload.py    # build a payload that KEEPS the MiniAOD
python3 tools/check_test_batch.py         # filter efficiency, file size, GenPart content
```

`check_test_batch.py` is the one to run first on any new era or filter change:
it reports events/job, MB/event and the `GenPart` composition, and compares
them against the old production. **Run a 10-job validation batch and check it
before submitting tasks** — the efficiency decides the job count, and getting
it wrong by 3× is the difference between one fold and a third of one.

Two things that are easy to break:

* **`numCores` in the CRAB config must equal `numberOfThreads` in the PSet.**
  `ConfigDY8.py` is the 8-thread one.
* **Premix must be given as `filelist:`, not `dbs:`.** With `dbs:` the global
  redirector picks sites that hold no replica and the DIGI step dies with
  `FallbackFileOpenError` (measured 33% failure). The lists here are the
  on-disk subsets, and the configs whitelist `T2_CH_CERN` and `T1_US_FNAL`.

Method and production notes: `doc/HZgamma/extended_dy_method.md` and
`doc/HZgamma/extended_dy_job_log.md`. Run 2 scripts are in `../Run2` for
reference.
