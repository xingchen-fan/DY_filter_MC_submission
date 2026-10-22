# Central-production fragments with a stock-module filter

The fragments in the parent directory use `MatchDYFilter`, which is not part of any
CMSSW release, so they only run where the plugin is compiled (the private production).
The fragments here are for central (McM) production: the filter is rebuilt from modules
that already exist in the official releases, so nothing needs to be compiled.

Each fragment is the McM fragment of the corresponding DY request, followed by the
filter block and a new `ProductionFilterSequence`.

| Campaign | Release |
|---|---|
| Run3Summer22, Run3Summer22EE | CMSSW_12_4_11_patch3 |
| Run3Summer23, Run3Summer23BPix | CMSSW_13_0_14 |
| RunIII2024Summer24 (2E, 2Mu) | CMSSW_14_0_19 |

## Selection

An event is kept if it has

1. a status-1 photon with pT > 5 GeV whose mother is a pi0 or an eta,
2. an opposite-sign e/mu pair (any status) with 75 < m(ll) < 105 GeV,
3. such a photon that, alone or combined with one other status-1 photon within
   dR < 0.1, has pT > 6 GeV.

Modules: `GenParticleProducer`, `GenParticleSelector`, `MCParticlePairFilter`,
`CandViewShallowCloneCombiner`, `CandViewMerger`, `CandViewCountFilter`.

## Relation to `MatchDYFilter`

`MatchDYFilter` requires a photon cluster (the pi0/eta photon plus all status-1 photons
within dR < 0.1) with pT > 10 GeV and a same-flavor lepton pair in the Z window. Neither
can be written exactly with stock modules, so conditions 2 and 3 are looser. In an
event-by-event GEN-only comparison (300k LHE events each for 2022EE, 2024 ee and
2024 mumu), every event kept by `MatchDYFilter` is also kept here; the number of kept
events is about 1.5 times larger.

Because the two filters differ, central and private samples must each be normalized with
their own filter efficiency.
