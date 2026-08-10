import CRABClient
from CRABClient.UserUtilities import config 

config = config()

config.General.requestName = 'DY2018_5_sec_10'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

#config.JobType.pluginName = 'Analysis'
config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY.py'
config.JobType.scriptExe  = '2018DY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=fanx_sec_10', 'DIR=fanx5/2018']
config.JobType.inputFiles = ['FrameworkJobReport.xml', '2018_degipremix_files_disk.txt']
config.JobType.numCores = 4
config.JobType.maxMemoryMB = 6300
config.JobType.maxJobRuntimeMin = 1400

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 10000

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

config.Site.storageSite = 'T3_CH_CERNBOX'
