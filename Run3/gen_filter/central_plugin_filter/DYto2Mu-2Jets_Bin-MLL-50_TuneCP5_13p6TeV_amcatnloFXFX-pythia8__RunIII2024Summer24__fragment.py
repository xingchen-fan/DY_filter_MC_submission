# Central production fragment, retrieved from McM
#   https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/GEN-RunIII2024Summer24wmLHEGS-00055
# with the DY + fake photon generator filter appended (MCZllMesonPhotonFilter).

import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer('ExternalLHEProducer',
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/PdmV/RunIII2024Summer24/MadGraph5_aMCatNLO/DY/DYto2L-2Jets_Bin-MLL-50_amcatnloFXFX-pythia8_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'),
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

lheGenericFilter = cms.EDFilter("LHEGenericFilter",
    src = cms.InputTag("externalLHEProducer"),
    NumRequired = cms.int32(0),
    ParticleID = cms.vint32(13),
    AcceptLogic = cms.string("GT") 
)

# ---------------------------------------------------------------------------
# DY + fake photon generator filter (MCZllMesonPhotonFilter, available from
# CMSSW_12_4_26_patch1, CMSSW_13_0_25_patch1 and CMSSW_14_0_25_patch1).
# An event is kept if it has
#   (1) a status-1 photon with pT > 5 GeV whose mother is a pi0 or an eta,
#   (2) a cluster with pT > 10 GeV, made of the highest-pT such photon (the seed)
#       and all other status-1 photons within dR < 0.1 of the seed,
#   (3) the leading e-/e+ or mu-/mu+ pair (any status) with 75 < m(ll) < 105 GeV.
# Kinematic definitions follow the analysis' photon-fake region, where the
# photon candidate is a pi0/eta -> gamma gamma cluster with pT > 10 GeV.
# ---------------------------------------------------------------------------
dyFakePhotonFilter = cms.EDFilter("MCZllMesonPhotonFilter",
    src = cms.InputTag("generator", "unsmeared"),
    particleID = cms.int32(22),
    motherIDs = cms.vint32(111, 221),
    minPt = cms.double(5.),
    clusterDeltaR = cms.double(0.1),
    minClusterPt = cms.double(10.),
    minDileptonMass = cms.double(75.),
    maxDileptonMass = cms.double(105.)
)

ProductionFilterSequence = cms.Sequence(lheGenericFilter + generator * dyFakePhotonFilter)
