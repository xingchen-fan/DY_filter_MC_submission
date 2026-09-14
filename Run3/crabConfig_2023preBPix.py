import CRABClient
from CRABClient.UserUtilities import config

config = config()

config.General.requestName = 'DY2023preBPix_1'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2023preBPixDY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=pmx1w', 'DIR=2023preBPix']
# The generator filter sources travel with the job and are compiled into the
# GEN-SIM release on the worker node.
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2023preBPix.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23__fragment.py',
                             'gen_filter/MatchDYFilter.cc',
                             'gen_filter/BuildFile.xml']
config.JobType.numCores = 8
# 2026-09-14: 20000 is exactly the 2.5 GB/core ceiling for an 8-core job and
# matches badly -- a 5-job test sat idle for 12 h at 20000 and started within
# 2 h at 16000. Measured peak across 1,227 finished jobs is 13,722 MB at four
# threads and 13,646 MB at eight, so 16000 leaves ~17% headroom.
config.JobType.maxMemoryMB = 16000
config.JobType.maxJobRuntimeMin = 600

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 10000

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

config.Site.whitelist = ['T2_CH_CERN', 'T1_US_FNAL']
config.Site.storageSite = 'T3_CH_CERNBOX'
