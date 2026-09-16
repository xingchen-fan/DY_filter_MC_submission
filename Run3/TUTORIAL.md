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
git clone https://github.com/xingchen-fan/DY_filter_MC_submission.git
cd DY_filter_MC_submission/Run3
```

The repository is public, so this needs no GitHub account and no SSH key. Use
the `git@github.com:` form instead only if you already have a key on lxplus and
intend to push back; submitting jobs never requires that.

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

`submit_run3.sh` defaults to 10,000 jobs per task. For a first run, override it.
One of these, for the era you are producing:

```bash
./submit_run3.sh --units 10 2022preEE    1 test 1
./submit_run3.sh --units 10 2022postEE   1 test 1
./submit_run3.sh --units 10 2023preBPix  1 test 1
./submit_run3.sh --units 10 2023postBPix 1 test 1
./submit_run3.sh --units 10 2024_2E      1 test 1
./submit_run3.sh --units 10 2024_2Mu     1 test 1
```

The arguments, taking the 2023preBPix line apart:

* `--units 10` — 10 jobs instead of 10,000
* `2023preBPix` — the era, one of the six above. Section 8 pairs each with the
  full-fold command
* `1` — number of tasks
* `<tag>` — the production round, not your name. Use `p1` for phase 1, `p2`
  for phase 2, and so on; a task then comes out as `p1_7`. The output already
  lives under your own `$USER` directory, so two people cannot collide, and a
  tag that says which round the files belong to is far more useful later than
  one that says who submitted them. A trial run is not a round, so give it
  `test` and leave `p1_1` for the production that follows
* `1` — first index; the task is named `<tag>_1`

You should see, per task:

```
output base: root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/<user>/HZg/root_DYfilter/phase1  (exists)
  totalUnits -> 10
submitting crab_configs/crabConfig_2023preBPix_<tag>_1.py
Task name: <date>_<time>:<user>_crab_DY2023preBPix_<tag>_1
```

No seed is printed here, and none is chosen here — the payload derives it on
the worker node. Section 5 says from what.

---

## 4. Check what was actually submitted

The `.sub`-equivalent for CRAB is the generated config. Read it back rather than
trusting the script:

```bash
grep -E "Submitter|totalUnits|numCores|maxMemoryMB|requestName" \
  crab_configs/crabConfig_2023preBPix_<tag>_1.py
```

Expect your username in `Submitter`, your `totalUnits`, and the era's resources.

`Submitter` is the one to look at. Without it every job of the task exits 65,
on purpose — see section 5. `submit_run3.sh` always writes it, so on this path
it is there; the grep is how you see it rather than assume it.

(There is a `tools/check_submitter.py` that scans every config at once. It is
for hand-written configs, which is not what you are doing here, and it cannot
fail for a config this script generated.)

---

## 5. Where the seed comes from, and why it matters

Each job seeds the LHE generator with a hash of four things: who submitted, the
era, the tag, and the job's ProcId. Change any one of them and the events
change.

The job index alone is not enough, and this is not hypothetical. Until
2026-09-13 the payload used `initialSeed = ProcId`, and since every task runs
ProcId `1..totalUnits`, **the same-numbered jobs of different tasks generated
the same hard-process events**. Measured across 13 tasks of one era: only 29.9%
of the accumulated events were distinct, and the 13th task added a tenth as
many new events as the first.

None of the usual checks see this. Event counts, file counts, tree entries and
`run:lumi:event` all look normal, because what is wrong is the *independence* of
the events, not their number.

So:

* You never set a seed by hand. `submit_run3.sh` passes `Submitter=$USER` and
  the payload derives the rest.
* Nothing is shared or coordinated. Two people at different institutions, each
  in their own clone or fork, get different seeds because their usernames
  differ -- no table to keep in step, no file to pull first.
* Resubmitting a job regenerates the same seed, so a retry produces the same
  events rather than new ones.
* A job with no `Submitter` **exits 65** rather than falling back to a default.
  A silent default is how the original bug produced two weeks of output that
  looked correct.
* Hashing makes repeats rare rather than impossible: roughly 0.04% of jobs in a
  full non-2024 campaign, against the 0.4% contamination the analysis already
  carries. Section 7 measures it on the output.

## 6. Watch it

```bash
crab status -d crab_projects/crab_DY2023preBPix_<tag>_1
```

What the states mean here:

| state | meaning |
|---|---|
| `unsubmitted` at 80-90% | normal. Only about 1,000 jobs of a task enter the global pool at a time |
| everything `idle` for hours | usually fair-share, not a bug. See section 9 |
| `failed` with exit code 65 | `Submitter` did not reach the payload. Check the config, do not resubmit blindly |

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

## 8. Scale up — the command for every era

Only after the small run has landed output and passed section 7, and one era
at a time. Section 9 says why that last part is not a preference.

Try ten jobs first, then the era. Both commands, per era:

| era | trial (10 jobs) | one full fold |
|---|---|---|
| `2022preEE` | `./submit_run3.sh --units 10 2022preEE 1 test 1` | **7 tasks**, 68,000 jobs |
| `2022postEE` | `./submit_run3.sh --units 10 2022postEE 1 test 1` | **22 tasks**, 219,000 jobs |
| `2023preBPix` | `./submit_run3.sh --units 10 2023preBPix 1 test 1` | **8 tasks**, 75,000 jobs |
| `2023postBPix` | `./submit_run3.sh --units 10 2023postBPix 1 test 1` | **5 tasks**, 50,000 jobs |
| `2024_2E` | `./submit_run3.sh --units 10 2024_2E 1 test 1` | **36 tasks**, 353,500 jobs † |
| `2024_2Mu` | `./submit_run3.sh --units 10 2024_2Mu 1 test 1` | **36 tasks**, 353,500 jobs † |

A fold is not one command. Send about **8 tasks at a time** and add the next
batch when the previous one has mostly landed — `first_index` is what continues
the numbering, and reusing an index would write a second production into the
first one's directory:

```bash
# 2022preEE -- 7 tasks
./submit_run3.sh 2022preEE     7  p1 1    # p1_1 .. p1_7

# 2022postEE -- 22 tasks, 3 batches
./submit_run3.sh 2022postEE    8  p1 1    # p1_1 .. p1_8
./submit_run3.sh 2022postEE    8  p1 9    # p1_9 .. p1_16
./submit_run3.sh 2022postEE    6  p1 17   # p1_17 .. p1_22

# 2023preBPix -- 8 tasks
./submit_run3.sh 2023preBPix   8  p1 1    # p1_1 .. p1_8

# 2023postBPix -- 5 tasks
./submit_run3.sh 2023postBPix  5  p1 1    # p1_1 .. p1_5

# 2024_2E -- 36 tasks, 5 batches
./submit_run3.sh 2024_2E       8  p1 1    # p1_1 .. p1_8
./submit_run3.sh 2024_2E       8  p1 9    # p1_9 .. p1_16
./submit_run3.sh 2024_2E       8  p1 17   # p1_17 .. p1_24
./submit_run3.sh 2024_2E       8  p1 25   # p1_25 .. p1_32
./submit_run3.sh 2024_2E       4  p1 33   # p1_33 .. p1_36

# 2024_2Mu -- 36 tasks, 5 batches
./submit_run3.sh 2024_2Mu      8  p1 1    # p1_1 .. p1_8
./submit_run3.sh 2024_2Mu      8  p1 9    # p1_9 .. p1_16
./submit_run3.sh 2024_2Mu      8  p1 17   # p1_17 .. p1_24
./submit_run3.sh 2024_2Mu      8  p1 25   # p1_25 .. p1_32
./submit_run3.sh 2024_2Mu      4  p1 33   # p1_33 .. p1_36
```

Eight is not a magic number, it is roughly what the queue absorbs: a task puts
only about 1,000 of its jobs into the global pool at a time, so eight tasks
already keep ~8,000 jobs queued. Measured on 2023preBPix, that queue delivered
about 60 finished jobs an hour, so a batch of eight is days of work, not hours.
Sending the next batch early does not make the first one faster — section 9.

† **2024 is one fold split in two, and the number itself is unmeasured.**
README's 707,000 is the total for 2024, not the figure for each flavor: every
row of that table is the same rule, five jobs per baseline event, and 2024's
input to it is an inclusive count like every other row. Splitting by lepton
flavor changes who generates the events, not how many are needed -- a
`2024_2E` job makes only ee, but makes it at roughly twice the rate an
inclusive job does -- so the two flavors take about half of the 707,000 each.
Roughly: ee and mumu do not contribute equally to the baseline.

The 707,000 is also the one number in the table that has never been checked
against a real job. It assumes 2024 yields what the other eras yield, and 2024
is known to be less efficient -- by how much is unclear, since README quotes
both 1.45% and ~2.5% for the same filter. Run the trial, count the baseline
events it actually yields, and derive the task count from that. Do not scale
the gen-filter efficiency: that is what overestimated 2022postEE by a factor
of three.

The other numbers come from `README.md`, which also explains the `1.06x` the
new filter costs. Do not re-derive any of them from the gen-filter efficiency.

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
| jobs `failed`, exit code 65 | `Submitter` missing from the config — `grep Submitter crab_configs/<config>` |
| everything `idle` for many hours | `maxMemoryMB`. 8-core jobs are capped at 20,000 MB (2.5 GB/core) and asking for the ceiling matches badly. 16,000 is measured-safe for this payload |
| jobs vanish: not in the queue, no logs, no output | walltime. CRAB removes them, and because they never exited normally, stdout is never returned |
| task exists on disk but nothing ever ran | `crab status` and read **"Status on the CRAB server"**. A `SUBMITFAILED` task still leaves a project directory, so any check based on directories existing will pass |

That last one is worth repeating: a directory-counting reconciliation reported
26/26 tasks submitted while one of them had failed at submission and never ran.
Only `crab status` shows it.
