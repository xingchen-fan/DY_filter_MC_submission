# Run 3 DY filter MC — job submission

📈 **[Production status spreadsheet](https://docs.google.com/spreadsheets/d/16R7L_nycmKkWsSV0h6ay0dWHEchZTC1nOp2i6Gal0G8/edit?gid=329992653#gid=329992653)**
— who is submitting what, and how far along it is. Update your row as you go.

**Submitting for the first time?** Start with [`TUTORIAL.md`](TUTORIAL.md).
This file is the reference: what the sample is and how many jobs it needs.

Private DY production with a GEN-level π⁰/η filter, so that only events that can
enter the DY + fake photon selection are simulated. Full chain per job: LHE+GEN
→ SIM → DIGI+DATAMIX+HLT → RECO → MINIAOD → NANOAOD → stage-out. Only the
NanoAOD is kept. The job script, filter source, fragments and premix file lists
all travel with the job.

## The sample definition

Output made with an earlier version of the filter or keep rules is a
**different sample** and must not be mixed in. The current definition differs
from it in two ways.

**1. A tighter gen filter** (`gen_filter/MatchDYFilter.cc`): the π⁰/η photon
must have cluster `pT > 10 GeV`, and the event a gen Z with `75 < m_ll < 105 GeV`.
On a 10-job validation batch:

| | old filter | new filter |
|---|---|---|
| 2022postEE | 976 events/job (9.76%) | 303 events/job (3.03%) |
| 2024_2E | — | 145 events/job (1.45%) |

That is 3.22x fewer gen-filtered events per job, but not 3.22x fewer analysis
events: the new filter mostly removes events that would fail the baseline
anyway. On the full 2022postEE productions (SR + Sideband, same corrections and
overlap removal):

| | baseline events | CRAB jobs | per job |
|---|---|---|---|
| old filter | 9,499 | 30,261 | 0.3139 +- 0.0032 |
| new filter | 3,717 | 12,604 | 0.2949 +- 0.0048 |

The ratio is 0.939 +- 0.018, so **plan with ~1.06x** the old job counts. Compare
SR + Sideband only: the old production also had control regions, and summing
every `*__inclusive` tree gives a spurious 22% deficit.

1.06x is not the truth-matching number. A `dR < 0.1` truth-matching requirement
removes 11.1% +- 4.3% of the filter sample at full baseline, at most 15.0%
(the non-jet-photon fraction). The two are unrelated.

**2. A second gen-particle keep rule** in the cmsDriver steps of `job/*.sh`:

```python
process.prunedGenParticles.select.append('keep status == 1 && pt > 0.5')
#   ... and the same on process.finalGenParticles for the NANOAOD step
```

It keeps the hadrons, so the AN-22-027 photon-origin classification can be
redone **from NanoAOD** (93.4% per-photon agreement with MiniAOD; see
`scripts_plot/README.md`). It costs disk: 12.0 kB/event instead of 4.5.
`tools/sync_keep_rules.py` puts the rule into all six payloads; rerun it if you
add an era.

## Do I need a particular CMSSW?

**No, and there is no shared CMSSW path.** The worker node builds every release
it needs from cvmfs (2022: `CMSSW_12_4_11_patch3` + `CMSSW_13_0_13`; 2023:
`CMSSW_13_0_14`; 2024: `CMSSW_14_0_19` + `CMSSW_14_0_21`). On the submission
side CRAB only needs some CMSSW area for its sandbox; `ConfigDY8.py` is a stub.

⚠️ **The architecture matters.** The arch you submit from decides which
container the grid job runs in, so submit from an **el8** release inside
`cmssw-el8`. `CMSSW_13_0_14` works.

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

You need a grid certificate first:
[WorkBookStartingGrid](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid).

## Submit

```bash
./submit_run3.sh [--dest <xrootd-url>] [--units N] <era> <n_tasks> <your_tag> [first_index]
```

* `era` — `2022preEE` | `2022postEE` | `2023preBPix` | `2023postBPix` | `2024_2E` | `2024_2Mu`
* `n_tasks` — each task is 10,000 jobs (CRAB's per-task limit)
* `your_tag` — the production, not your name: `fold1`, `fold2`; a task comes
  out as `fold1_7`. The output is already under your `$USER` directory
* `first_index` — start of the numbering, default 1; use it to continue a series
* `--dest` — output base; see below
* `--units` — jobs per task, default 10,000. Use a small value for a first run

Example — 3 tasks (30,000 jobs) of 2022postEE:

```bash
./submit_run3.sh 2022postEE 3 fold1
```

**Submit one era at a time.** Sending everything at once spends your grid
priority and slows everyone down.

### Where the output goes

**Your own subdirectory of the shared project space**, derived from `$USER`,
created on first use:

```
/eos/project/h/htozg-dy-privatemc/<user>/HZg/root_DYfilter/phase1/<era>/<tag>/
```

This needs the `cernbox-project-htozg-dy-privatemc-writers` e-group — ask
Pei-Zhu to add you. Without it the script stops immediately.

`--dest <xrootd-url>` writes somewhere else, e.g. your own CERNBox; that output
does not count toward the fold until it is copied into the project space.

```bash
./submit_run3.sh --dest root://eosuser.cern.ch//eos/user/x/xxx/HZg/root_DYfilter \
                 2022postEE 3 pz
```

## How many jobs

For Run 3, assuming jet photon events make up 55% of total DY after baseline,
one fold of statistics (five jobs per baseline event) needs, with the **old**
filter:

| Era | `era` argument | Existing events after baseline | Number of jobs (10k events/job) |
|-|-|-|-|
| 2022 | `2022preEE` | 13500 | 68000 |
| 2022EE | `2022postEE` | 43700 | 219000 |
| 2023 | `2023preBPix` | 15000 | 75000 |
| 2023BPix | `2023postBPix` | 10000 | 50000 |
| 2024 | `2024_2E`, `2024_2Mu` | 141000 | 707000 |

For the new filter multiply by ~1.06 (measured on 2022postEE, above). One job is
one output file, and a task is 10,000 jobs, so 2022EE is about 22 tasks.

⚠️ **2024's 707,000 is the total, not the number for each flavor.** A
`2024_2E` job makes only ee, at roughly twice the rate of an inclusive job, so
`2024_2E` and `2024_2Mu` take about half each, ~36 tasks apiece.

⚠️ **2024 has not been measured on the baseline.** Its gen-filter efficiency is
lower (1.45%), and whether that costs baseline statistics is what the
efficiency ratio cannot tell you. Measure it on a trial before sending a fold.

`crab status`'s `finished` agrees with the file count on EOS, but a fresh task
can report 0 finished while files are already appearing, because the jobs stage
out themselves.

## Monitor

```bash
crab status -d crab_projects/crab_DY2022postEE_fold1_1
crab resubmit -d crab_projects/crab_DY2022postEE_fold1_1   # retry failed jobs
crab kill     -d crab_projects/crab_DY2022postEE_fold1_1
```

Each task gets its own output subdirectory; a single EOS directory stops
listing past ~120k files, so do not flatten this. Count with `eos ls`:

```bash
eos root://eosproject.cern.ch ls <dir> | grep -c '\.root$'
```

`find`/`ls` return **0 with exit code 0** on a directory that large, and
`eos find` silently **truncates at exactly 100,000**.

For failed jobs and stunted files, run `recover.sh` (TUTORIAL section 10).

## What is in here

Tracked — this is the production:

| | |
|---|---|
| `submit_run3.sh` | writes one CRAB config per task and submits |
| `recover.sh` | retries failed jobs; finds and removes files that exited 0 with almost no events |
| `GRID_CERTIFICATE.md` | getting and installing the grid certificate everything else needs |
| `crabConfig_<era>.py` | the six templates; `submit_run3.sh` rewrites name/tag/output |
| `job/<era>DY.sh` | the actual job: cmsDriver chain + stage-out |
| `gen_filter/MatchDYFilter.cc` | the GEN filter, compiled on the worker node |
| `gen_filter/*fragment.py` | generator fragments, one per era |
| `premix_lists/` | premix pileup files known to be on disk |
| `ConfigDY8.py` | CRAB PSet stub (8 threads; must match `numCores`) |
| `tools/` | helpers: keep-rule sync, MiniAOD-preserving payload, validation-batch check, `check_submitter.py` for hand-written configs |
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

**Run a 10-job validation batch and check it with `check_test_batch.py` before
submitting tasks** on any new era or filter change: it reports events/job,
MB/event and the `GenPart` composition against the old production, and the
efficiency decides the job count.

Easy to break:

* **`numCores` in the CRAB config must equal `numberOfThreads` in the PSet.**
  `ConfigDY8.py` is the 8-thread one.
* **Premix must be given as `filelist:`, not `dbs:`.** With `dbs:` the global
  redirector picks sites with no replica and DIGI dies with
  `FallbackFileOpenError` (33% failure). The lists here are the on-disk subsets.
* **Jobs run anywhere.** `Data.ignoreLocality = True` lets jobs overflow past
  the whitelist (`T2_CH_CERN`, `T1_US_FNAL`, the two sites with premix; CRAB
  requires one). Without it the jobs ran at CERN alone, which is not enough for
  the people sharing a fold. Off-site jobs read premix over the WAN, take about
  twice as long, and 0.01% to 0.70% of their files hold ~3 events instead of
  ~300 while the job still exits 0. `recover.sh` screens every file for that;
  see TUTORIAL section 10.

Method and production notes: `doc/HZgamma/extended_dy_method.md` and
`doc/HZgamma/extended_dy_job_log.md`. Run 2 scripts are in `../Run2` for
reference.
