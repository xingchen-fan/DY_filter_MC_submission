# Central-production fragments with `MCZllMesonPhotonFilter`

These fragments are for central (McM) production. The filter is
`MCZllMesonPhotonFilter` (`GeneratorInterface/GenFilters`), which is our private
`MatchDYFilter` added to CMSSW with the fixed cluster axis. Nothing needs to be compiled.

Each fragment is the McM fragment of the corresponding DY request, followed by the
filter and a new `ProductionFilterSequence`. Apart from the filter block, the fragments
are identical to those in `../central_stock_filter/`.

| Campaign | Release used by the campaign | First release with the filter |
|---|---|---|
| Run3Summer22, Run3Summer22EE | CMSSW_12_4_11_patch3 | CMSSW_12_4_26_patch1 |
| Run3Summer23, Run3Summer23BPix | CMSSW_13_0_14 | CMSSW_13_0_25_patch1 |
| RunIII2024Summer24 (2E, 2Mu) | CMSSW_14_0_19 | CMSSW_14_0_25_patch1 |

The campaigns must move to a release that contains the filter.

## Selection

An event is kept if it has

1. a status-1 photon with pT > 5 GeV whose mother is a pi0 or an eta,
2. a cluster with pT > 10 GeV, made of the highest-pT such photon (the seed) and all
   other status-1 photons within dR < 0.1 of the seed,
3. the leading e- and e+, or the leading mu- and mu+ (any status), with
   75 < m(ll) < 105 GeV.

All parameters are written out in the fragments; their values are the defaults of the
module (`mcZllMesonPhotonFilter_cfi`).

## Relation to the other filters

* `../fixed_axis/MatchDYFilter.cc` (private production from fold3): same selection,
  event by event.
* `../MatchDYFilter.cc` (private folds 1 and 2): the cluster axis moves as photons are
  added, so the result depends on the order of the HepMC record. About 1% of the kept
  events differ; the total number of kept events agrees within 0.2%.
* `../central_stock_filter/`: looser (cluster of at most two photons above 6 GeV, any
  opposite-sign e/mu pair). It keeps every event kept here and about 1.5 times as many
  in total.

## Test

Each fragment was run as in the McM test command, in a fresh area of the release listed
above with only the fragment in `src/` (no compiled code), 5000 LHE events. The same
seed was also run with the `central_stock_filter` fragment in the same release:

| Campaign | Kept here | Kept by stock filter | Kept here but not by stock filter |
|---|---|---|---|
| Run3Summer22 | 147 | 227 | 0 |
| Run3Summer22EE | 132 | 220 | 0 |
| Run3Summer23 | 161 | 236 | 0 |
| Run3Summer23BPix | 146 | 226 | 0 |
| RunIII2024Summer24, 2E | 68 | 95 | 0 |
| RunIII2024Summer24, 2Mu | 86 | 118 | 0 |
