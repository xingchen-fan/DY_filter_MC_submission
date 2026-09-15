import CRABClient
from CRABClient.UserUtilities import config

config = config()

# (comment removed: see Run3/README.md)
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
config.General.requestName = 'DY2022postEE_nt8test'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2022postEEDY_nt8.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=nt8test', 'DIR=2022postEE', 'DEST=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYfilter/nt8test/2022postEE', 'Submitter=pelai']
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2022postEE.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer22EE__fragment.py',
                             'gen_filter/MatchDYFilter.cc',
                             'gen_filter/BuildFile.xml']
config.JobType.numCores = 8
config.JobType.maxMemoryMB = 20000
config.JobType.maxJobRuntimeMin = 600

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 5

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

config.Site.whitelist = ['T2_CH_CERN', 'T1_US_FNAL']
config.Site.storageSite = 'T3_CH_CERNBOX'
