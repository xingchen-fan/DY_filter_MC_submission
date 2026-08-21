// Run 3 port of the Run 2 MatchDYFilter (gen_filter/genFilterFiles/).
//
// Same selection, but packaged as a self-contained plugin so that it builds
// against CMSSW_12_4_X / 13_0_X / 14_0_X / 15_0_X without checking out
// GeneratorInterface/GenFilters. The Run 2 version lived in that release
// package and its BuildFile pulled in GeneratorInterface/Pythia6Interface,
// which no longer exists in these releases.
//
// Selection: keep the event if it contains
//   * a stable (status 1) particle with |pdgId| == pdgID, pT > minPt, whose
//     mother is one of motherPdgID (default pi0 / eta), and
//   * an opposite sign same flavour lepton pair (ee or mumu).

#include <memory>
#include <vector>

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "SimDataFormats/GeneratorProducts/interface/HepMCProduct.h"

class MatchDYFilter : public edm::global::EDFilter<> {
public:
  explicit MatchDYFilter(const edm::ParameterSet&);
  ~MatchDYFilter() override {};

  bool filter(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  const edm::EDGetTokenT<edm::HepMCProduct> token_;
  const int pdgID;
  const std::vector<int> motherPdgID;
  const float minPt;
};

MatchDYFilter::MatchDYFilter(const edm::ParameterSet& iConfig)
    : token_(consumes<edm::HepMCProduct>(
          edm::InputTag(iConfig.getUntrackedParameter("moduleLabel", std::string("generator")), "unsmeared"))),
      pdgID(iConfig.getUntrackedParameter<int>("pdgID")),
      motherPdgID(iConfig.getUntrackedParameter<std::vector<int>>("motherPdgID")),
      minPt((float)iConfig.getUntrackedParameter<double>("minPt")) {}

bool MatchDYFilter::filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const {
  bool found_ph = false;
  bool found_lep = false;
  int el_counter = 0;
  int mu_counter = 0;
  int el_pdg = 0;
  int mu_pdg = 0;

  using namespace edm;
  Handle<HepMCProduct> evt;
  iEvent.getByToken(token_, evt);

  const HepMC::GenEvent* myGenEvent = evt->GetEvent();
  for (HepMC::GenEvent::particle_const_iterator p = myGenEvent->particles_begin(); p != myGenEvent->particles_end();
       ++p) {
    // Beam particles have no production vertex. The Run 2 version dereferenced
    // this unconditionally, which is only safe as long as the generator always
    // provides one.
    if ((*p)->production_vertex() == nullptr)
      continue;
    HepMC::GenParticle* mother = (*((*p)->production_vertex()->particles_in_const_begin()));
    if (mother == nullptr)
      continue;

    if (abs((*p)->pdg_id()) == pdgID && (*p)->status() == 1 && (*p)->momentum().perp() > minPt) {
      for (unsigned int i = 0; i < motherPdgID.size(); i++) {
        if (abs(mother->pdg_id()) == motherPdgID[i]) {
          found_ph = true;
        }
      }
    } else if (el_counter == 0 && abs((*p)->pdg_id()) == 11) {
      el_counter++;
      el_pdg = (*p)->pdg_id();
    } else if (el_counter == 1 && (*p)->pdg_id() == -el_pdg) {
      el_counter++;
    } else if (mu_counter == 0 && abs((*p)->pdg_id()) == 13) {
      mu_counter++;
      mu_pdg = (*p)->pdg_id();
    } else if (mu_counter == 1 && (*p)->pdg_id() == -mu_pdg) {
      mu_counter++;
    }
  }
  found_lep = el_counter == 2 || mu_counter == 2;
  return found_lep && found_ph;
}

DEFINE_FWK_MODULE(MatchDYFilter);
