import CRABClient
from CRABClient.UserUtilities import config

config = config()

config.General.requestName = 'DY2023postBPix_1'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2023postBPixDY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=pmx1w', 'DIR=2023postBPix']
# The generator filter sources travel with the job and are compiled into the
# GEN-SIM release on the worker node.
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2023postBPix.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23BPix__fragment.py',
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

config.Site.whitelist = ['T2_CH_CERN', 'T1_US_FNAL']
config.Site.storageSite = 'T3_CH_CERNBOX'
