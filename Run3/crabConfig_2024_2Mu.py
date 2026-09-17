import CRABClient
from CRABClient.UserUtilities import config

config = config()

config.General.requestName = 'DY2024_2Mu_1'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2024DY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=pmx2Mu_1w', 'DIR=2024', 'DEST=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYmix/2024', 'FLAV=2Mu']
# The generator filter sources travel with the job and are compiled into the
# GEN-SIM release on the worker node.
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2024_slice15.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2E-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__RunIII2024Summer24__fragment.py',
                             'gen_filter/DYto2Mu-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__RunIII2024Summer24__fragment.py',
                             'gen_filter/MatchDYFilter.cc',
                             'gen_filter/BuildFile.xml']
config.JobType.numCores = 8
# 16,000 and not 20,000. 20,000 is the ceiling for an 8-core job (2.5 GB/core)
# and asking for the ceiling matches badly -- it was why 2023preBPix queued so
# poorly, and that era was dropped to 16,000 on 2026-09-14 while the other five
# were left at the ceiling.
#
# Measured peak per era, every one of them at 8 cores, from crab status on the
# tasks of the previous round:
#
#     2022preEE     14,648 MB        2023preBPix   14,902 MB
#     2022postEE    14,648 MB        2024_2E       13,727 MB
#     2023postBPix  14,648 MB        2024_2Mu      13,741 MB
#
# 16,000 clears the worst of those by 7%. Nothing here is extrapolated: the
# numbers were already sitting in the project directories of tasks that ran
# weeks ago, which is where to look before guessing at a new measurement.
config.JobType.maxMemoryMB = 16000
config.JobType.maxJobRuntimeMin = 600

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 10000

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

# Run beyond CERN, not only where the premix library has a replica. Until
# 2026-09-16 this was the whitelist below WITHOUT ignoreLocality, which in
# practice meant CERN alone: FNAL never appears in the site list CRAB derives
# for a generation task, so every job of every era ran at T2_CH_CERN. With
# thirteen people submitting one fold, one site is the ceiling -- 8,884 of our
# jobs sat idle there while 131 ran.
#
# ignoreLocality stops CRAB deriving sites from where data lives (there is no
# input dataset here, only an invented block) and lets the job overflow past
# the whitelist. The whitelist still has to be here: CRAB refuses the config
# without one when ignoreLocality is set. It is kept at the two sites that
# actually hold premix, so that if the overflow ever stops happening the jobs
# fall back to where reading is local rather than to nowhere.
#
# Measured on 10 jobs that overflowed to T2_US_MIT and T2_US_UCSD, neither of
# which holds premix: 10/10 exited 0, runtime 1h16-1h35 against 44 min at CERN,
# the difference being premix read over the WAN.
#
# 🔴 One of those ten produced a file with 7 events instead of ~300, and still
# exited 0. Nothing downstream notices that: the job succeeds, the file exists,
# the size looks plausible. Only the event count shows it. Run
# tools/check_event_counts.py over the output before merging -- see TUTORIAL
# section 7.
config.Data.ignoreLocality = True
config.Site.whitelist = ['T2_CH_CERN', 'T1_US_FNAL']
config.Site.storageSite = 'T3_CH_CERNBOX'
