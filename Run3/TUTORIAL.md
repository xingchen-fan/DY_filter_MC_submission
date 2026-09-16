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

**One fold** is the unit these numbers are in: enough jobs that the events
surviving the analysis baseline selection match what the existing central DY
sample already has. One fold doubles the DY statistics.

The budget is **five jobs per baseline event** — a job generates 10,000 events
and about 0.2 of one (20%) is still standing after baseline. So every job count
below is 5x the era's "existing events after baseline" column in `README.md`,
and one fifth of a fold is the point where you have produced one job per event
you are trying to match.

Try ten jobs first, then the era. Both commands, per era:

| era | trial (10 jobs) | one full fold |
|---|---|---|
| `2022preEE` | `./submit_run3.sh --units 10 2022preEE 1 test 1` | **7 tasks**, 68,000 jobs |
| `2022postEE` | `./submit_run3.sh --units 10 2022postEE 1 test 1` | **22 tasks**, 219,000 jobs |
| `2023preBPix` | `./submit_run3.sh --units 10 2023preBPix 1 test 1` | **8 tasks**, 75,000 jobs |
| `2023postBPix` | `./submit_run3.sh --units 10 2023postBPix 1 test 1` | **5 tasks**, 50,000 jobs |
| `2024_2E` | `./submit_run3.sh --units 10 2024_2E 1 test 1` | **36 tasks**, 353,500 jobs † |
| `2024_2Mu` | `./submit_run3.sh --units 10 2024_2Mu 1 test 1` | **36 tasks**, 353,500 jobs † |

Each line below is one person's whole share. Run yours, once.

Nobody has to coordinate with anybody to do this safely. Your output goes under
your own `$USER` directory, your seed is derived from your username, and no two
people can land on the same events. The index ranges are disjoint for a
different reason: every job names its file after the tag and index, so
non-overlapping ranges are what keeps the filenames unique once all of this is
merged into one place.

```bash
# 2022preEE -- 7 tasks
./submit_run3.sh 2022preEE     7  p1 1    # p1_1 .. p1_7    Jookang

# 2022postEE -- 22 tasks
./submit_run3.sh 2022postEE    6  p1 1    # p1_1 .. p1_6    Junhyeok  (1 of 2)
./submit_run3.sh 2022postEE    5  p1 7    # p1_7 .. p1_11   Junhyeok  (2 of 2)
./submit_run3.sh 2022postEE    6  p1 12   # p1_12 .. p1_17  Junwon  (1 of 2)
./submit_run3.sh 2022postEE    5  p1 18   # p1_18 .. p1_22  Junwon  (2 of 2)

# 2023preBPix -- 8 tasks
./submit_run3.sh 2023preBPix   8  p1 1    # p1_1 .. p1_8    Joseph

# 2023postBPix -- 5 tasks
./submit_run3.sh 2023postBPix  5  p1 1    # p1_1 .. p1_5    Peike

# 2024_2E -- 36 tasks
./submit_run3.sh 2024_2E       5  p1 1    # p1_1 .. p1_5    Pei-Zhu  (1 of 2)
./submit_run3.sh 2024_2E       4  p1 6    # p1_6 .. p1_9    Pei-Zhu  (2 of 2)
./submit_run3.sh 2024_2E       5  p1 10   # p1_10 .. p1_14  Amrutha  (1 of 2)
./submit_run3.sh 2024_2E       4  p1 15   # p1_15 .. p1_18  Amrutha  (2 of 2)
./submit_run3.sh 2024_2E       5  p1 19   # p1_19 .. p1_23  Mingxu  (1 of 2)
./submit_run3.sh 2024_2E       4  p1 24   # p1_24 .. p1_27  Mingxu  (2 of 2)
./submit_run3.sh 2024_2E       5  p1 28   # p1_28 .. p1_32  Mingtao  (1 of 2)
./submit_run3.sh 2024_2E       4  p1 33   # p1_33 .. p1_36  Mingtao  (2 of 2)

# 2024_2Mu -- 36 tasks
./submit_run3.sh 2024_2Mu      5  p1 1    # p1_1 .. p1_5    Yue Pan  (1 of 2)
./submit_run3.sh 2024_2Mu      4  p1 6    # p1_6 .. p1_9    Yue Pan  (2 of 2)
./submit_run3.sh 2024_2Mu      5  p1 10   # p1_10 .. p1_14  Junhyuk Lee  (1 of 2)
./submit_run3.sh 2024_2Mu      4  p1 15   # p1_15 .. p1_18  Junhyuk Lee  (2 of 2)
./submit_run3.sh 2024_2Mu      5  p1 19   # p1_19 .. p1_23  Xingchen  (1 of 2)
./submit_run3.sh 2024_2Mu      4  p1 24   # p1_24 .. p1_27  Xingchen  (2 of 2)
./submit_run3.sh 2024_2Mu      5  p1 28   # p1_28 .. p1_32  Sungbeom  (1 of 2)
./submit_run3.sh 2024_2Mu      4  p1 33   # p1_33 .. p1_36  Sungbeom  (2 of 2)
```

What that adds up to:

| era | tasks | people | each |
|---|---|---|---|
| `2022preEE` | 7 | 1 | 7 |
| `2022postEE` | 22 | 2 | 11 |
| `2023preBPix` | 8 | 1 | 8 |
| `2023postBPix` | 5 | 1 | 5 |
| `2024_2E` | 36 | 4 | 9 |
| `2024_2Mu` | 36 | 4 | 9 |

Thirteen people, 5 to 11 tasks each. **Nobody appears under two eras**, and that
is deliberate: grid priority is charged per user, so a person split across two
eras divides their own share between them and finishes neither sooner. It is
also why the shares cannot be made perfectly equal -- the eras come in sizes of
5, 7, 8, 22, 36, 36, and a person has to fit inside one of them.

Where somebody's share is more than 8 tasks it is written as two lines, because
one person should not have more than about 8 tasks queued at once. **Send the
first line, and the second only when the first has largely landed.**

Splitting the work across people is not the same as one person sending more
tasks. Grid priority is charged per user, so thirteen people each submitting
their share draw on thirteen separate shares — that is the reason to organize
it this way rather than have one person send all 114 tasks. Within one person,
the old limit still holds: no more than about **8 tasks queued at a time**, and
one era at a time. A task only puts about 1,000 of its jobs into the global
pool, so 8 tasks already keep the queue full, and on 2023preBPix that queue
returned about 60 finished jobs an hour.

2024 needs 72 of the 114 tasks, which is why eight of the thirteen are on it.
It is also the one number here that has never been measured -- see the footnote
below.

---

## 9. Two rules that are not optional

**One era at a time, per person.** On 2026-09-06, 77 tasks (770,000 jobs) went
in at once from a single account. The next day produced 19,226 files; the day
after that, 1,552 — a factor of 12, with identical settings. That was one
person's fair share being spent. Submitting more tasks does not buy more slots;
each task only puts about 1,000 jobs into the pool anyway.

More people does buy slots, because priority is charged per user. The thirteen
submitters in section 8 draw on thirteen separate shares, which is why six eras
can be in flight at once there without contradicting this rule — and why one of
those thirteen running two eras at once would contradict it, dividing their own
share between two things instead of finishing one.

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
