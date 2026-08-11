# DY_filter_MC_submission

This repository is merely for job submissions of Run3 filter MC sample generation. Run2 job submission scripts are stored in `Run2` for testing and reference.
Filters and CMSSW are set up already in our CERN box at `/eos/project/h/htozg-dy-privatemc/`. 
Different eras should use different CMSSW and environments on lxplus.

## Guidance for the number of jobs

According to my rough estimation, 50k events requested will give us one event after the baseline and truth matching. I have this table for 1 fold of statistics:
|Era|Existing events after baseline|Number of jobs (10k events/job)|
|-|-|-|
|2016|5128|26000|
|2016APV|6439|33000|
|2017|13045|70000|
|2018|14056|80000|

For Run3, assuming jet photon events makes up 55% of total DY after baseline
|Era|Existing events after baseline|Number of jobs (10k events/job)|
|-|-|-|
|2022|13500|68000|
|2022EE|43700|219000|
|2023|15000|75000|
|2023BPix|10000|50000|
|2024|141000|707000|

## CRAB Job Guide

**IMPORTANT:** You need to have your grid certificate installed, please go to this [page](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid) and follow the steps. 
**NOTICE:** Another [repo](https://github.com/xingchen-fan/DY_stat_boost/tree/main) is created just for Run3 MC job submission. Please go there!

Take a 2017 submission as an example:

1. Login to LXPLUS
2. git clone this repo.
3. Run `cmssw-el7`
4. `cd` to the prepared CMSSW dir in our CERNBOX and run `cmsenv`
5. Initialize grid certificate `voms-proxy-init --voms cms`
6. Create your own folder in our CERNBOX. Then create one folder per submission in your folder, i.e. `YOURDIR/2017`.
7. Back to the `DY_filter_MC_submission/` of your local repo dir and run `submitter.sh`:
   ```
   ./submitter.sh crabConfig2017.py n DY2017 YOURDIR/2017 MYTAG
   ```
   where there are 5 arguments:
   * The CRAB config file you want to use.
   * The number of submissions you want to submit. `n` means **n*10k** jobs submitted here.
   * The name of the submission for monitoring. In each submission, a number will be added at the end of it so that the names are different.
   * The subdirectory in our CERNBOX where you want to download the output files to.
   * The tag at the end of the output root files. In each submission, a number will be added at the end of it so that the tags are different.
   

Now, you successfully submit **n** submissions of jobs and there will eventually be about **n***9500 output files (5% failure rate) in `/YOURDIR/2017` if everything goes as intended.

Three useful CRAB commands are
```
crab status -d crab_projects/crab_DY2017_1
```
which is to monitor the jobs. This command will provide some URL that you can open in your broswer such that you can monitor the jobs in a more intuitive way. If you keep that URL open, you don't need to log in to LXPLUS to monitor the jobs.
```
crab kill -d crab_projects/crab_DY2017_1
```
which is to kill a submission.

```
crab resubmit -d crab_projects/crab_DY2017_1
```
which is to resubmit failed jobs in a submission.


As I list in the table previously, we need 7 submissions (10k jobs each) to have one fold of 2017 DY statistics. Likewise, 3 submissions for 2016, 4 submissions for 2016APV and 7 submissions for 2018. DO NOT submit all these jobs together and you will lose your priority! Finish one year at a time and move on to the next year. 

If you finish all the years, congratulations! You help us increase the statistics by 1 fold! And you can create a sub
