import CRABClient
from CRABClient.UserUtilities import config

config = config()

config.General.requestName = 'DY2022preEE_1'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2022preEEDY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=pmx1w', 'DIR=2022preEE']
# The generator filter sources travel with the job and are compiled into the
# GEN-SIM release on the worker node.
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2022preEE.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer22__fragment.py',
                             'gen_filter/MatchDYFilter.cc',
                             'gen_filter/BuildFile.xml']
config.JobType.numCores = 8
config.JobType.maxMemoryMB = 20000
config.JobType.maxJobRuntimeMin = 600

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 10000

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

# Run anywhere the pool will take us, not only where the premix library has a
# replica. Until 2026-09-16 this was Site.whitelist = ['T2_CH_CERN',
# 'T1_US_FNAL'], which in practice meant CERN alone: FNAL never appears in the
# site list CRAB derives for a generation task, so every job of every era ran
# at T2_CH_CERN. With thirteen people submitting one fold, one site is the
# ceiling, and 8,884 of our jobs sat idle there while 131 ran.
#
# ignoreLocality stops CRAB deriving sites from where data lives -- there is no
# input dataset here, only an invented block -- and lets the job match anywhere.
# Measured on 10 jobs at T2_US_MIT and T2_US_UCSD, neither of which holds
# premix: 10/10 exited 0, runtime 1h16-1h35 against 44 min at CERN, because the
# premix is read over the WAN.
#
# 🔴 One of those ten produced a file with 7 events instead of ~300, and still
# exited 0. Nothing downstream notices that: the job succeeds, the file exists,
# the size looks plausible. Only the event count shows it. Run
# tools/check_event_counts.py over the output before merging -- see TUTORIAL
# section 7.
config.Data.ignoreLocality = True
config.Site.storageSite = 'T3_CH_CERNBOX'
