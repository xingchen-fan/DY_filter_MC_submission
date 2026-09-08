// Run 3 port of Xingchen's updated MatchDYFilter (gen_filter/genFilterFiles/,
// commit 7ea0290 "New filter", 2026-08-28).
//
// Packaging only: the physics selection is copied verbatim from the Run 2
// version. It is repackaged as a self-contained plugin so that it builds
// against CMSSW_12_4_X / 13_0_X / 14_0_X / 15_0_X without checking out
// GeneratorInterface/GenFilters -- that package's BuildFile pulls in
// GeneratorInterface/Pythia6Interface, which no longer exists in these
// releases.
//
// Selection (all three required):
//   * found_ph    : a stable (status 1) particle with |pdgId| == pdgID,
//                   pT > minPt, whose mother is one of motherPdgID (pi0 / eta);
//   * cluster_pt  : take the highest-pT such photon, add every other status-1
//                   photon within dR < 0.1 of it, require the resulting
//                   cluster to have pT > 10 GeV;
//   * z_mass_good : the leading e-/e+ or mu-/mu+ pair has 75 < m < 105 GeV.
//
// Differences from the previous Run 3 port (which mirrored the older Run 2
// filter): the photon clustering and the Z mass window are new, and the
// lepton requirement is no longer a plain opposite-sign same-flavour count.
// Both new requirements are tighter, so the filter efficiency drops.
//
// Two deliberate departures from the Run 2 source, neither of which changes
// the selection:
//   * beam particles have no production vertex; the Run 2 version dereferences
//     it unconditionally, which is only safe while the generator always
//     provides one. The guard below skips those particles (beam protons match
//     none of the branches anyway).
//   * the class is declared here instead of in MatchDYFilter.h.
//
// Note kept on purpose: the lepton branches do NOT require status == 1, so
// hard-process leptons can be picked as the leading candidate. That is the
// Run 2 behavior and is preserved verbatim.

#include <memory>
#include <vector>

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "SimDataFormats/GeneratorProducts/interface/HepMCProduct.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "DataFormats/Math/interface/deltaR.h"

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
  int mother_pdgid = 0;

  using namespace edm;
  Handle<HepMCProduct> evt;
  iEvent.getByToken(token_, evt);

  std::vector<math::XYZTLorentzVector> photons;
  std::vector<math::XYZTLorentzVector> el_m;
  std::vector<math::XYZTLorentzVector> el_p;
  std::vector<math::XYZTLorentzVector> mu_m;
  std::vector<math::XYZTLorentzVector> mu_p;
  math::XYZTLorentzVector max_photon;
  unsigned int max_photon_ind = 0;
  int index = 0;
  float maxpT_ph = -1.0;
  float maxpT_el_p = -1.0, maxpT_el_m = -1.0, maxpT_mu_p = -1.0, maxpT_mu_m = -1.0;
  int max_el_p_index = -1, max_el_m_index = -1, max_mu_p_index = -1, max_mu_m_index = -1;

  const HepMC::GenEvent* myGenEvent = evt->GetEvent();
  for (HepMC::GenEvent::particle_const_iterator p = myGenEvent->particles_begin(); p != myGenEvent->particles_end();
       ++p) {
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
    }

    if (abs((*p)->pdg_id()) == pdgID && (*p)->status() == 1) {
      math::XYZTLorentzVector ph_(
          (*p)->momentum().px(), (*p)->momentum().py(), (*p)->momentum().pz(), (*p)->momentum().e());
      mother_pdgid = abs(mother->pdg_id());
      bool main_ph = false;
      for (unsigned int i = 0; i < motherPdgID.size(); i++) {
        if (mother_pdgid == motherPdgID[i])
          main_ph = true;
      }
      if (main_ph) {
        if ((*p)->momentum().perp() > maxpT_ph) {
          maxpT_ph = (*p)->momentum().perp();
          max_photon = ph_;
          max_photon_ind = index;
        }
      }
      photons.push_back(ph_);
      index += 1;
    } else if ((*p)->pdg_id() == 11) {
      math::XYZTLorentzVector el_(
          (*p)->momentum().px(), (*p)->momentum().py(), (*p)->momentum().pz(), (*p)->momentum().e());
      if ((*p)->momentum().perp() > maxpT_el_m) {
        maxpT_el_m = (*p)->momentum().perp();
        max_el_m_index = el_m.size();
      }
      el_m.push_back(el_);
    } else if ((*p)->pdg_id() == -11) {
      math::XYZTLorentzVector el_(
          (*p)->momentum().px(), (*p)->momentum().py(), (*p)->momentum().pz(), (*p)->momentum().e());
      if ((*p)->momentum().perp() > maxpT_el_p) {
        maxpT_el_p = (*p)->momentum().perp();
        max_el_p_index = el_p.size();
      }
      el_p.push_back(el_);
    } else if ((*p)->pdg_id() == 13) {
      math::XYZTLorentzVector mu_(
          (*p)->momentum().px(), (*p)->momentum().py(), (*p)->momentum().pz(), (*p)->momentum().e());
      if ((*p)->momentum().perp() > maxpT_mu_m) {
        maxpT_mu_m = (*p)->momentum().perp();
        max_mu_m_index = mu_m.size();
      }
      mu_m.push_back(mu_);
    } else if ((*p)->pdg_id() == -13) {
      math::XYZTLorentzVector mu_(
          (*p)->momentum().px(), (*p)->momentum().py(), (*p)->momentum().pz(), (*p)->momentum().e());
      if ((*p)->momentum().perp() > maxpT_mu_p) {
        maxpT_mu_p = (*p)->momentum().perp();
        max_mu_p_index = mu_p.size();
      }
      mu_p.push_back(mu_);
    }
  }

  bool z_mass_good = false;
  if (photons.size() > 0) {
    for (unsigned int j = 0; j < photons.size(); j++) {
      if (j != max_photon_ind && reco::deltaR(max_photon, photons[j]) < 0.1)
        max_photon += photons[j];
    }
  }
  if (el_m.size() > 0 && el_p.size() > 0) {
    float z_mass = (el_m[max_el_m_index] + el_p[max_el_p_index]).mass();
    if (z_mass > 75 && z_mass < 105)
      z_mass_good = true;
  }
  if (mu_m.size() > 0 && mu_p.size() > 0) {
    float z_mass = (mu_m[max_mu_m_index] + mu_p[max_mu_p_index]).mass();
    if (z_mass > 75 && z_mass < 105)
      z_mass_good = true;
  }
  bool cluster_pt = max_photon.pt() > 10;
  return cluster_pt && found_ph && z_mass_good;
}

DEFINE_FWK_MODULE(MatchDYFilter);
