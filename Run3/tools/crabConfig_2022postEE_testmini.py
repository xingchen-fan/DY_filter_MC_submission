import CRABClient
from CRABClient.UserUtilities import config

config = config()

# MiniAOD-keeping validation batch (2026-09-03), 5 jobs.
#
# Purpose: decide whether NanoAOD with the new `keep status == 1 && pt > 0.5`
# rule can reproduce the AN-22-027 photon-origin table, which is defined on
# MiniAOD `packedGenParticles` (the complete status-1 collection). The only way
# to answer that is to classify the SAME events both ways, so this batch stages
# the MiniAOD out alongside the NanoAOD.
#
# MiniAOD is ~18 MB/job at the new filter's ~303 events/job, so 5 jobs is ~90 MB.
#
# Differs from crabConfig_2022postEE_testnew.py only in requestName, scriptExe,
# Tag, DEST and totalUnits.

config.General.requestName = 'DY2022postEE_testmini'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2022postEEDY_keepmini.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=testmini', 'DIR=2022postEE', 'DEST=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYfilter/test_newfilter_mini/2022postEE']
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
