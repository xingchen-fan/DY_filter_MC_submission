# Central production fragment, retrieved from McM
#   https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/GEN-Run3Summer23BPixwmLHEGS-00325
# with the DY + fake photon generator filter appended.

import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer('ExternalLHEProducer',
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/PdmV/Run3Summer22/MadGraph5_aMCatNLO/DY/DYto2L-2Jets_MLL-50_amcatnloFXFX-pythia8_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh'),
    generateConcurrently = cms.untracked.bool(False)
)

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunesRun3ECM13p6TeV.PythiaCP5Settings_cfi import *
from Configuration.Generator.Pythia8aMCatNLOSettings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *

generator = cms.EDFilter("Pythia8ConcurrentHadronizerFilter",
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CP5SettingsBlock,
        pythia8aMCatNLOSettingsBlock,
        pythia8PSweightsSettingsBlock,
        processParameters = cms.vstring(
            'JetMatching:setMad = off',
            'JetMatching:scheme = 1',
            'JetMatching:merge = on',
            'JetMatching:jetAlgorithm = 2',
            'JetMatching:etaJetMax = 999.',
            'JetMatching:coneRadius = 1.',
            'JetMatching:slowJetPower = 1',
            'JetMatching:doFxFx = on',
            'JetMatching:qCut = 30.',
            'JetMatching:qCutME = 10.',
            'JetMatching:nQmatch = 5',
            'JetMatching:nJetMax = 2',
            'TimeShower:mMaxGamma = 4.0',
            'BeamRemnants:primordialKThard=2.48',
            'TauDecays:externalMode = 2.0'
            ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'pythia8CP5Settings',
            'pythia8aMCatNLOSettings',
            'processParameters',
            'pythia8PSweightsSettings'
        )
    ),
    comEnergy = cms.double(13600),
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    pythiaPylistVerbosity = cms.untracked.int32(1),
)

# ---------------------------------------------------------------------------
# Generator level filter, see gen_filter/genFilterFiles_run3/MatchDYFilter.cc
# Keep only events with a pi0/eta -> gamma above 5 GeV plus an OSSF lepton pair,
# so that the expensive SIM/DIGI/RECO steps only run on events that can end up
# in the DY + fake photon selection.
# ---------------------------------------------------------------------------
testFilter = cms.EDFilter("MatchDYFilter",
                          pdgID = cms.untracked.int32(22),
                          minPt = cms.untracked.double(5.),
                          motherPdgID = cms.untracked.vint32(111, 221)
)

ProductionFilterSequence = cms.Sequence(generator*testFilter)
