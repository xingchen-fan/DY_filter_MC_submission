# Submitting DY filter jobs — a walkthrough

`README.md` is the reference. This file is a linear walkthrough for a first
submission, from `git clone` to a full era, with a check after every step.
Every check exists because skipping it has cost somebody a production.

---

## 0. Before you start

You need a **grid certificate** in your browser and on lxplus. If you have
none, or it has expired, do [GRID_CERTIFICATE.md](GRID_CERTIFICATE.md) first
(an hour, once a year). Nothing below works without it, and the failure does
not mention the certificate.

You also need to be in the e-group
**`cernbox-project-htozg-dy-privatemc-writers`** to write the output. Ask
before you start; `submit_run3.sh` only tells you after everything else is set
up.

---

## 1. Clone

```bash
ssh lxplus
cd <YOUR_WORK_DIR>
git clone https://github.com/xingchen-fan/DY_filter_MC_submission.git
cd DY_filter_MC_submission/Run3
```

The repository is public; no GitHub account or SSH key is needed.

Run everything below from this `Run3` directory: the paths inside the configs
are resolved against where you run `crab submit`, not where the config sits.

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

`SCRAM_ARCH` decides which container the grid job runs in. Submitting from an
el9 shell gives jobs that fail hours later on the worker node.

---

## 3. Your first submission is 10 jobs, not 10,000

`submit_run3.sh` defaults to 10,000 jobs per task. For a first run, one of:

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
* `2023preBPix` — the era
* `1` — number of tasks
* `test` — the tag. It names the production, not the person (`fold1`, `fold2`);
  the output is already under your `$USER` directory. Use `test` for a trial
* `1` — first index; the task is named `<tag>_1`

You should see, per task:

```
output base: root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/<user>/HZg/root_DYfilter/phase1  (exists)
  totalUnits -> 10
submitting crab_configs/crabConfig_2023preBPix_<tag>_1.py
Task name: <date>_<time>:<user>_crab_DY2023preBPix_<tag>_1
```

No seed is printed: the payload derives it on the worker node (section 5).

---

## 4. Check what was actually submitted

Read the generated config back rather than trusting the script:

```bash
grep -E "Submitter|totalUnits|numCores|maxMemoryMB|requestName" \
  crab_configs/crabConfig_2023preBPix_<tag>_1.py
```

Expect your username in `Submitter`, your `totalUnits`, and the era's
resources. Without `Submitter` every job exits 65 (section 5).
`tools/check_submitter.py` does the same for hand-written configs.

---

## 5. Where the seed comes from, and why it matters

Each job seeds the LHE generator with a hash of the submitter, the era
directory, the tag and the ProcId. `2024_2E` and `2024_2Mu` share the directory
`2024`, so one person running both must use different tags or index ranges.

The ProcId alone is not enough: with `initialSeed = ProcId`, the same-numbered
jobs of different tasks generated **the same events** -- across 13 tasks of one
era only 29.9% were distinct. Event counts, file counts and `run:lumi:event`
all look normal when that happens.

* You never set a seed by hand, and nothing has to be coordinated: different
  usernames give different seeds.
* A retry regenerates the same seed, so it produces the same events.
* A job with no `Submitter` **exits 65** rather than falling back to a default.
* Repeats are rare, not impossible (~0.04% of jobs); section 7 checks the
  output.

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

`crab status --long` adds per-job memory, runtime and CPU efficiency.

---

## 7. Check the output, not just the job states

```bash
eos root://eosuser.cern.ch ls <DEST>/2023preBPix/<tag>_1 | wc -l   # one file per finished job
```

Use `eos ls`, not `ls` or `find`: on 10,000 files the FUSE mount returns
nothing and no error.

Once two tasks of the same era have output, check that they are independent:

```bash
python3 tools/check_seed_uniqueness.py --dir <DEST>/2023preBPix
```

Run it in the section 2 environment (it needs `uproot`). It compares
`Generator_x1` between same-numbered jobs of different tasks: a shared seed
shows up as ~40%, independent tasks as 0-1%, and the threshold is 5%. It must
end with

```
OK: no shared seeds across tasks
```

Do not use `run:lumi:event` instead: every job numbers its events `1..N`, so
40 jobs of a single task already share 43.5% of their triples.

---

## 8. Scale up — the command for every era

Only after the trial has passed section 7, and one era at a time (section 9).

**One fold** doubles the DY statistics: its events after the baseline selection
match the existing central sample. It costs **five jobs per event after
baseline**, so an era's job count is five times the "existing events after
baseline" column in `README.md`.

| era | trial (10 jobs) | one full fold |
|---|---|---|
| `2022preEE` | `./submit_run3.sh --units 10 2022preEE 1 test 1` | **7 tasks**, 68,000 jobs |
| `2022postEE` | `./submit_run3.sh --units 10 2022postEE 1 test 1` | **22 tasks**, 219,000 jobs |
| `2023preBPix` | `./submit_run3.sh --units 10 2023preBPix 1 test 1` | **8 tasks**, 75,000 jobs |
| `2023postBPix` | `./submit_run3.sh --units 10 2023postBPix 1 test 1` | **5 tasks**, 50,000 jobs |
| `2024_2E` | `./submit_run3.sh --units 10 2024_2E 1 test 1` | **36 tasks**, 353,500 jobs † |
| `2024_2Mu` | `./submit_run3.sh --units 10 2024_2Mu 1 test 1` | **36 tasks**, 353,500 jobs † |

† 2024's events after baseline per job have not been measured; see README,
"How many jobs".

Each block below is one person's share. The index ranges are disjoint because
the filename carries only the tag and index, and the files are merged into one
place later.

```bash
# 2022preEE -- 7 tasks
./submit_run3.sh 2022preEE     3  fold1 1    # fold1_1 .. fold1_3    Jookang  (1 of 3)
./submit_run3.sh 2022preEE     2  fold1 4    # fold1_4 .. fold1_5    Jookang  (2 of 3)
./submit_run3.sh 2022preEE     2  fold1 6    # fold1_6 .. fold1_7    Jookang  (3 of 3)

# 2022postEE -- 22 tasks
./submit_run3.sh 2022postEE    3  fold1 1    # fold1_1 .. fold1_3    Junhyeok Song  (1 of 4)
./submit_run3.sh 2022postEE    3  fold1 4    # fold1_4 .. fold1_6    Junhyeok Song  (2 of 4)
./submit_run3.sh 2022postEE    3  fold1 7    # fold1_7 .. fold1_9    Junhyeok Song  (3 of 4)
./submit_run3.sh 2022postEE    2  fold1 10   # fold1_10 .. fold1_11  Junhyeok Song  (4 of 4)
./submit_run3.sh 2022postEE    3  fold1 12   # fold1_12 .. fold1_14  Junwon  (1 of 4)
./submit_run3.sh 2022postEE    3  fold1 15   # fold1_15 .. fold1_17  Junwon  (2 of 4)
./submit_run3.sh 2022postEE    3  fold1 18   # fold1_18 .. fold1_20  Junwon  (3 of 4)
./submit_run3.sh 2022postEE    2  fold1 21   # fold1_21 .. fold1_22  Junwon  (4 of 4)

# 2023preBPix -- 8 tasks
./submit_run3.sh 2023preBPix   3  fold1 1    # fold1_1 .. fold1_3    Joseph  (1 of 3)
./submit_run3.sh 2023preBPix   3  fold1 4    # fold1_4 .. fold1_6    Joseph  (2 of 3)
./submit_run3.sh 2023preBPix   2  fold1 7    # fold1_7 .. fold1_8    Joseph  (3 of 3)

# 2023postBPix -- 5 tasks
./submit_run3.sh 2023postBPix  3  fold1 1    # fold1_1 .. fold1_3    Peike  (1 of 2)
./submit_run3.sh 2023postBPix  2  fold1 4    # fold1_4 .. fold1_5    Peike  (2 of 2)

# 2024_2E -- 36 tasks
./submit_run3.sh 2024_2E       3  fold1 1    # fold1_1 .. fold1_3    Pei-Zhu  (1 of 4)
./submit_run3.sh 2024_2E       3  fold1 4    # fold1_4 .. fold1_6    Pei-Zhu  (2 of 4)
./submit_run3.sh 2024_2E       3  fold1 7    # fold1_7 .. fold1_9    Pei-Zhu  (3 of 4)
./submit_run3.sh 2024_2E       3  fold1 10   # fold1_10 .. fold1_12  Pei-Zhu  (4 of 4)
./submit_run3.sh 2024_2E       3  fold1 13   # fold1_13 .. fold1_15  Mingxu  (1 of 4)
./submit_run3.sh 2024_2E       3  fold1 16   # fold1_16 .. fold1_18  Mingxu  (2 of 4)
./submit_run3.sh 2024_2E       3  fold1 19   # fold1_19 .. fold1_21  Mingxu  (3 of 4)
./submit_run3.sh 2024_2E       3  fold1 22   # fold1_22 .. fold1_24  Mingxu  (4 of 4)
./submit_run3.sh 2024_2E       3  fold1 25   # fold1_25 .. fold1_27  Mingtao  (1 of 4)
./submit_run3.sh 2024_2E       3  fold1 28   # fold1_28 .. fold1_30  Mingtao  (2 of 4)
./submit_run3.sh 2024_2E       3  fold1 31   # fold1_31 .. fold1_33  Mingtao  (3 of 4)
./submit_run3.sh 2024_2E       3  fold1 34   # fold1_34 .. fold1_36  Mingtao  (4 of 4)

# 2024_2Mu -- 36 tasks
./submit_run3.sh 2024_2Mu      3  fold1 1    # fold1_1 .. fold1_3    Yue Pan  (1 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 4    # fold1_4 .. fold1_6    Yue Pan  (2 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 7    # fold1_7 .. fold1_9    Yue Pan  (3 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 10   # fold1_10 .. fold1_12  Junhyuk Lee  (1 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 13   # fold1_13 .. fold1_15  Junhyuk Lee  (2 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 16   # fold1_16 .. fold1_18  Junhyuk Lee  (3 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 19   # fold1_19 .. fold1_21  Xingchen  (1 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 22   # fold1_22 .. fold1_24  Xingchen  (2 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 25   # fold1_25 .. fold1_27  Xingchen  (3 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 28   # fold1_28 .. fold1_30  Sungbeom  (1 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 31   # fold1_31 .. fold1_33  Sungbeom  (2 of 3)
./submit_run3.sh 2024_2Mu      3  fold1 34   # fold1_34 .. fold1_36  Sungbeom  (3 of 3)
```

What that adds up to:

| era | tasks | people | each | days |
|---|---|---|---|---|
| `2022preEE` | 7 | 1 | 7 | ~7 |
| `2022postEE` | 22 | 2 | 11 | ~11 |
| `2023preBPix` | 8 | 1 | 8 | ~8 |
| `2023postBPix` | 5 | 1 | 5 | ~5 |
| `2024_2E` | 36 | 3 | 12 | ~12 |
| `2024_2Mu` | 36 | 4 | 9 | ~9 |

One person gets through about **10,000 jobs (one task) a day**, so the days
column is your task count; the fold takes about 12 days, set by `2024_2E`.
Treat it as the optimistic end: the rate drops as your priority is spent.

Grid priority is charged per user, so holding more tasks does not return more
jobs a day, while more people does. That is why the work is split across
twelve people and nobody holds two eras. Junhyeok Song and Junhyuk Lee are two
different people.

**Send one line (at most 3 tasks, 30,000 jobs) at a time**, the next only when
it has largely landed, and run `./recover.sh <era> fold1` before each new line
(section 10).

---

## 9. Two rules that are not optional

**One era at a time, per person.** 77 tasks sent at once from one account
returned 19,226 files on the first day and 1,552 on the second: the share was
spent, and more tasks do not buy more slots.

**Never reuse a tag for a new production.** Two productions in one directory
cannot be told apart afterwards.

---

## 10. Recovery, which is routine, and the rest of what goes wrong

From the `Run3` directory, inside the section 2 environment:

```bash
./recover.sh 2024_2E fold1            # report only
./recover.sh 2024_2E fold1 --apply    # act
```

Run it **before each new line**. It handles two failures:

* **Jobs CRAB reports as failed**, about 10%; they stay failed once their
  retries run out. `--apply` runs `crab resubmit`, which regenerates the same
  events.
* **Stunted files**: the job exited 0 but wrote ~3 events instead of ~300,
  0.01-0.70% of a task, from sites reading premix over the WAN. CRAB cannot
  retry them. `--apply` deletes them and prints how many jobs to produce again
  under a **new tag** (a new seed); never top up under the original tag.

| symptom | first thing to check |
|---|---|
| jobs `failed`, exit code 65 | `Submitter` missing from the config — `grep Submitter crab_configs/<config>` |
| everything `idle` for many hours | `maxMemoryMB`. 8-core jobs are capped at 20,000 MB (2.5 GB/core) and asking for the ceiling matches badly. 16,000 is measured-safe for this payload |
| jobs vanish: not in the queue, no logs, no output | walltime. CRAB removes them, and because they never exited normally, stdout is never returned |
| task exists on disk but nothing ever ran | `crab status` and read **"Status on the CRAB server"**. A `SUBMITFAILED` task still leaves a project directory, so any check based on directories existing will pass |
