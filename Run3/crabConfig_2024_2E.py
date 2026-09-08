import CRABClient
from CRABClient.UserUtilities import config

config = config()

config.General.requestName = 'DY2024_2E_1'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2024DY.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=pmx2E_1w', 'DIR=2024', 'DEST=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYmix/2024', 'FLAV=2E']
# The generator filter sources travel with the job and are compiled into the
# GEN-SIM release on the worker node.
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2024_slice00.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2E-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__RunIII2024Summer24__fragment.py',
                             'gen_filter/DYto2Mu-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__RunIII2024Summer24__fragment.py',
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
