# 2026-09-10 resubmission: maxMemoryMB 20000 -> 16000, numCores stays 8.
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# The payload already runs --nThreads 4, so the measured usage is for four
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
#
# (comment removed: see Run3/README.md)
# (comment removed: see Run3/README.md)
import CRABClient
from CRABClient.UserUtilities import config

config = config()

# MiniAOD-keeping validation batch (2026-09-08), 200 jobs.
#
# Purpose: decide whether NanoAOD with the new `keep status == 1 && pt > 0.5`
# rule can reproduce the AN-22-027 photon-origin table, which is defined on
# MiniAOD `packedGenParticles` (the complete status-1 collection). The only way
# to answer that is to classify the SAME events both ways, so this batch stages
# the MiniAOD out alongside the NanoAOD.
#
# MiniAOD is ~18 MB/job at the new filter's ~303 events/job, so 200 jobs is ~3.6 GB.
#
# Why 200 and not 5: the 5-job batch answered whether the two sides AGREE
# photon by photon (93.4%), but not whether NanoAOD truth matching DISTORTS
# the selected distribution. The disagreement is not flat in kinematics
# (95.9% at photon pT 15-20 GeV, 90.7% at 40-60; 94-95% barrel, 91% endcap),
# so a shape test is needed, and 5 jobs leave only 31 jet-photons in the
# analysis population -- far too few. 200 jobs give roughly 1,200.
#
# Differs from crabConfig_2022postEE_testnew.py only in requestName, scriptExe,
# Tag, DEST and totalUnits.

config.General.requestName = 'DY2022postEE_keepmini200b'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = 'ConfigDY8.py'
config.JobType.scriptExe  = 'job/2022postEEDY_keepmini.sh'
config.JobType.scriptArgs = ['Nevents=10000', 'Tag=keepmini200', 'DIR=2022postEE', 'DEST=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/pelai/HZg/root_DYfilter/test_newfilter_mini/2022postEE', 'SeedBase=800020000']
config.JobType.inputFiles = ['premix_lists/premix_ondisk_2022postEE.txt',
                             'FrameworkJobReport.xml',
                             'gen_filter/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer22EE__fragment.py',
                             'gen_filter/MatchDYFilter.cc',
                             'gen_filter/BuildFile.xml']
config.JobType.numCores = 8
config.JobType.maxMemoryMB = 16000
config.JobType.maxJobRuntimeMin = 600

config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 200

config.Data.outputPrimaryDataset = 'ShellTest'
config.Data.publication = True
config.Data.outputDatasetTag = 'test'

config.Site.whitelist = ['T2_CH_CERN', 'T1_US_FNAL']
config.Site.storageSite = 'T3_CH_CERNBOX'
