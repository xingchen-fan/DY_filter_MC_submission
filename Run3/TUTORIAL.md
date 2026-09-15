# Submitting DY filter jobs — a walkthrough

`README.md` is the reference: what the sample is, how many jobs each era needs,
why the numbers are what they are. This file is the other thing — a linear
walkthrough for someone submitting for the first time, from `git clone` to a
full era, with a check after every step.

The order matters. Every check here exists because skipping it has cost
somebody a production.

---

## 0. Before you start

You need a **grid certificate** installed in your browser and on lxplus:
[WorkBookStartingGrid](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid).
Nothing below works without it, and the failure it gives is not obvious.

You also need write access to wherever the output goes. The default is your own
subdirectory of the shared project space, so you are not writing into anybody
else's area.

---

## 1. Clone

```bash
ssh lxplus
cd <YOUR_WORK_DIR>
git clone git@github.com:xingchen-fan/DY_filter_MC_submission.git
cd DY_filter_MC_submission/Run3
```

Everything below is run from this `Run3` directory. Paths inside the configs
(`psetName`, `scriptExe`, `inputFiles`) are resolved against the directory you
run `crab submit` from, not against where the config file sits.

---

## 2. Set up the environment

Once ever:

```bash
cmssw-el8                       # el8, to match the production releases
cd <YOUR_WORK_DIR>
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el8_amd64_gcc11
scram p CMSSW CMSSW_13_0_14
```

Once per session:

```bash
cmssw-el8
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el8_amd64_gcc11
cd <YOUR_WORK_DIR>/CMSSW_13_0_14/src && eval `scram runtime -sh` && cd -
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init --rfc --voms cms -valid 192:00
cd <YOUR_WORK_DIR>/DY_filter_MC_submission/Run3
```

**Check before going on:**

```bash
echo $SCRAM_ARCH                # must start with el8_
command -v crab                 # must print a path
voms-proxy-info -timeleft       # must be more than a few hours
```

`SCRAM_ARCH` is not cosmetic: the architecture you submit **from** decides which
container the grid job runs in. Submitting from an el9 shell gives jobs that
cannot build the el8 releases they need, and the failure appears hours later on
the worker node.

---

## 3. Your first submission is 10 jobs, not 10,000

`submit_run3.sh` defaults to 10,000 jobs per task. For a first run, override it:

```bash
./submit_run3.sh --units 10 2023preBPix 1 p1 1
```

* `--units 10` — 10 jobs instead of 10,000
* `2023preBPix` — the era; one of
  `2022preEE` `2022postEE` `2023preBPix` `2023postBPix` `2024_2E` `2024_2Mu`
* `1` — number of tasks
* `<tag>` — the production round, not your name. Use `p1` for phase 1, `p2`
  for phase 2, and so on; a task then comes out as `p1_7`. The output already
  lives under your own `$USER` directory, so two people cannot collide, and a
  tag that says which round the files belong to is far more useful later than
  one that says who submitted them.
* `1` — first index; the task is named `<tag>_1`

You should see, per task:

```
  seed base 220000  (seeds 220001..230000)
  totalUnits -> 10
submitting crab_configs/crabConfig_2023preBPix_<tag>_1.py
Task name: 2609xx_xxxxxx:<user>_crab_DY2023preBPix_<tag>_1
```

That `seed base` line is the important one — see section 5.

---

## 4. Check what was actually submitted

The `.sub`-equivalent for CRAB is the generated config. Read it back rather than
trusting the script:

```bash
grep -E "SeedBase|totalUnits|numCores|maxMemoryMB|requestName" \
  crab_configs/crabConfig_2023preBPix_<tag>_1.py
```

Expect a unique `SeedBase`, your `totalUnits`, and the era's resources.

Then check the whole repository at once:

```bash
python3 tools/check_seed_bases.py
```

This must end with

```
OK: all SeedBase values unique, ranges disjoint, within CMSSW limits
```

If it does not, **do not submit more** until it does.

---

## 5. What SeedBase is, and why you cannot skip it

Each job seeds the LHE generator with `SeedBase + ProcId`.

`ProcId` alone is not enough, and this is not hypothetical. Until 2026-09-13 the
payload used `initialSeed = ProcId`, and since every task runs ProcId
`1..totalUnits`, **the same-numbered jobs of different tasks generated the same
hard-process events**. Measured across 13 tasks of one era: only 29.9% of the
accumulated events were distinct, and the 13th task added a tenth as many new
events as the first.

None of the usual checks see this. Event counts, file counts, tree entries and
`run:lumi:event` all look normal, because what is wrong is the *independence* of
the events, not their number.

So:

* `submit_run3.sh` allocates it for you. You never set it by hand.
* Each submitter has a block in `seed_blocks.txt`, and allocation happens inside
  it, so two people cannot collide even submitting at the same moment from their
  own clones. Add yourself a line there the first time; without one, submission
  stops rather than guessing a block.
* Resubmitting the same task returns the same value, so re-running is safe.
* A job with no `SeedBase` **exits 65** rather than falling back to a default.
  A silent default is how the original bug produced two weeks of output that
  looked correct.
* Hand-written configs set `SeedBase` themselves, above `800000000`, and then
  pass `tools/check_seed_bases.py`.

---

## 6. Watch it

```bash
crab status -d crab_projects/crab_DY2023preBPix_<tag>_1
```

What the states mean here:

| state | meaning |
|---|---|
| `unsubmitted` at 80-90% | normal. Only about 1,000 jobs of a task enter the global pool at a time |
| everything `idle` for hours | usually fair-share, not a bug. See section 9 |
| `failed` with exit code 65 | `SeedBase` did not reach the payload. Check the config, do not resubmit blindly |

`crab status --long` adds a per-job table with memory, runtime and CPU
efficiency, which is what you want when deciding resources.

---

## 7. Check the output, not just the job states

Jobs reporting success is not the same as output being correct.

```bash
ls <DEST>/2023preBPix/<tag>_1/ | wc -l      # one file per finished job
```

Once at least two tasks of the same era have output, check that they are really
independent:

```bash
python3 tools/check_seed_uniqueness.py --dir <DEST>/2023preBPix
```

It compares `Generator_x1` — the hard-process momentum fraction — as a multiset
between same-numbered jobs of different tasks. Independent jobs overlap by 0.0%;
a shared seed shows up as roughly 40%. It must end with

```
OK: no shared seeds across tasks
```

**Do not substitute `run:lumi:event` for this.** Every job numbers its events in
the same `1..N` range, so 40 jobs of a *single* task already share 43.5% of
their `run:lumi:event` triples with no shared seed involved. That is slot
occupancy, and using it as a fingerprint gives a number that looks alarming and
means nothing.

---

## 8. Scale up

Only after the small run has landed output and passed section 7:

```bash
./submit_run3.sh 2023preBPix 8 p1 2
```

8 tasks of 10,000 jobs, numbered `<tag>_2 ... <tag>_9`.

`README.md` has the job counts each era needs. Do not derive them from the
gen-filter efficiency ratio — see the `1.06x` section there for why that
overestimates by a factor of three.

---

## 9. Two rules that are not optional

**One era at a time.** On 2026-09-06, 77 tasks (770,000 jobs) went in at once.
The next day produced 19,226 files; the day after that, 1,552 — a factor of 12,
with identical settings. That is the fair-share share being spent. Submitting
more tasks does not buy more slots; each task only puts about 1,000 jobs into
the pool anyway.

**Never reuse a tag for a new production.** The tag is the output subdirectory.
Reusing one mixes two productions in one place, and after the fact there is no
way to tell which file came from which.

---

## 10. When something goes wrong

| symptom | first thing to check |
|---|---|
| jobs `failed`, exit code 65 | `SeedBase` missing from the config — `grep SeedBase crab_configs/<config>` |
| everything `idle` for many hours | `maxMemoryMB`. 8-core jobs are capped at 20,000 MB (2.5 GB/core) and asking for the ceiling matches badly. 16,000 is measured-safe for this payload |
| jobs vanish: not in the queue, no logs, no output | walltime. CRAB removes them, and because they never exited normally, stdout is never returned |
| task exists on disk but nothing ever ran | `crab status` and read **"Status on the CRAB server"**. A `SUBMITFAILED` task still leaves a project directory, so any check based on directories existing will pass |

That last one is worth repeating: a directory-counting reconciliation reported
26/26 tasks submitted while one of them had failed at submission and never ran.
Only `crab status` shows it.
