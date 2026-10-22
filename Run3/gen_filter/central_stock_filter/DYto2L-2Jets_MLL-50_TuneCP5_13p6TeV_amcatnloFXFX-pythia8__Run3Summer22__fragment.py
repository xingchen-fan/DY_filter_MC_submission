# Central production fragment, retrieved from McM
#   https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/GEN-Run3Summer22wmLHEGS-00067
# with the gridpack set to the RunIII2024Summer24 one (same gridpack, per ppd-auto-bkg)
# and the DY + fake photon generator filter appended (stock CMSSW modules only).

import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer('ExternalLHEProducer',
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/PdmV/RunIII2024Summer24/MadGraph5_aMCatNLO/DY/DYto2L-2Jets_Bin-MLL-50_amcatnloFXFX-pythia8_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh'),
    generateConcurrently = cms.untracked.bool(False),
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
            'JetMatching:qCutME = 10',
            'JetMatching:nJetMax = 2',
            'TimeShower:mMaxGamma = 4.0',
            'JetMatching:nQmatch = 5',
            'BeamRemnants:primordialKThard=2.48',
            'TauDecays:externalMode = 2.0'
            ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'pythia8CP5Settings',
            'pythia8aMCatNLOSettings',
            'processParameters',
            'pythia8PSweightsSettings',
        )
    ),
    comEnergy = cms.double(13600),
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    pythiaPylistVerbosity = cms.untracked.int32(1),
)

# ---------------------------------------------------------------------------
# DY + fake photon generator filter, built only from modules in the release.
# An event is kept if it has
#   (1) a status-1 photon with pT > 5 GeV whose mother is a pi0 or an eta,
#   (2) an opposite-sign e/mu pair (any status) with 75 < m(ll) < 105 GeV,
#   (3) such a photon that, alone or combined with one other status-1 photon
#       within dR < 0.1, has pT > 6 GeV.
# Kinematic definitions follow the analysis' photon-fake region, where the
# photon candidate is a pi0/eta -> gamma gamma cluster with pT > 10 GeV.
# ---------------------------------------------------------------------------
dyGenParticles = cms.EDProducer("GenParticleProducer",
    saveBarCodes = cms.untracked.bool(True),
    src = cms.InputTag("generator", "unsmeared"),
    abortOnUnknownPDGCode = cms.untracked.bool(False)
)

dyPi0EtaPhotons = cms.EDFilter("GenParticleSelector",
    src = cms.InputTag("dyGenParticles"),
    cut = cms.string("pdgId == 22 && status == 1 && pt > 5 && numberOfMothers > 0 && "
                     "(abs(mother(0).pdgId) == 111 || abs(mother(0).pdgId) == 221)"),
    filter = cms.bool(True)
)

dyZToLLFilter = cms.EDFilter("MCParticlePairFilter",
    ParticleID1 = cms.untracked.vint32(11, 13),
    ParticleID2 = cms.untracked.vint32(11, 13),
    ParticleCharge = cms.untracked.int32(-1),
    Status = cms.untracked.vint32(0, 0),
    MinPt = cms.untracked.vdouble(0., 0.),
    MinEta = cms.untracked.vdouble(-1e6, -1e6),
    MaxEta = cms.untracked.vdouble(1e6, 1e6),
    MinInvMass = cms.untracked.double(75.),
    MaxInvMass = cms.untracked.double(105.)
)

dyStablePhotons = cms.EDFilter("GenParticleSelector",
    src = cms.InputTag("dyGenParticles"),
    cut = cms.string("pdgId == 22 && status == 1"),
    filter = cms.bool(False)
)

dyPhotonPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    decay = cms.string("dyPi0EtaPhotons dyStablePhotons"),
    cut = cms.string("deltaR(daughter(0).eta, daughter(0).phi, daughter(1).eta, daughter(1).phi) < 0.1 && "
                     "deltaR(daughter(0).eta, daughter(0).phi, daughter(1).eta, daughter(1).phi) > 1e-6 && "
                     "pt > 6"),
    checkCharge = cms.bool(False)
)

dyPhotonSingles = cms.EDFilter("GenParticleSelector",
    src = cms.InputTag("dyPi0EtaPhotons"),
    cut = cms.string("pt > 6"),
    filter = cms.bool(False)
)

dyPhotonCands = cms.EDProducer("CandViewMerger",
    src = cms.VInputTag("dyPhotonPairs", "dyPhotonSingles")
)

dyPhotonClusterFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("dyPhotonCands"),
    minNumber = cms.uint32(1)
)

dyFakePhotonFilterSequence = cms.Sequence(
    dyGenParticles * dyPi0EtaPhotons * dyZToLLFilter * dyStablePhotons
    * dyPhotonPairs * dyPhotonSingles * dyPhotonCands * dyPhotonClusterFilter
)

ProductionFilterSequence = cms.Sequence(generator * dyFakePhotonFilterSequence)
