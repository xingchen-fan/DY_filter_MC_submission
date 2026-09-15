echo "this is not a test"

echo $(pwd)

ARG=$2
ARGTAG=$3
ARGDIR=$4
DIR=${ARGDIR#*=}
NEVENTS=${ARG#*=}
NJOB=$1
OUTTAG=${ARGTAG#*=}

# --- LHE seed ---------------------------------------------------------------
# The seed is derived, not allocated: it is a hash of who submitted, which era
# and round, and the job index. Two submissions differ as soon as any of those
# differ, so people at different institutions need no shared file, no table and
# no coordination -- and a fork works exactly like a clone.
#
# Until 2026-09-13 this was initialSeed = the job index alone. That index is
# the ProcId WITHIN a task and every task runs ProcId 1..totalUnits, so the
# same-numbered jobs of different tasks generated the SAME hard-process events.
# Measured across 13 tasks of one era: only 29.9% of the accumulated events
# were distinct. None of the usual checks see it -- event counts, file counts,
# tree entries and run:lumi:event all look normal, because what is wrong is the
# independence of the events, not their number.
#
# Hashing does not guarantee uniqueness, it makes repeats rare: about 0.04% of
# jobs in a full non-2024 campaign, against the 0.4% contamination the analysis
# already carries. Verify on the output with tools/check_seed_uniqueness.py.
#
# The submitter has to be passed in: $USER on a worker node is the pool account
# the job runs as, not the person who submitted it. Parse by NAME, not by
# position -- the 2024 eras pass an extra FLAV argument, which shifts what
# follows it.
SUBMITTER=""
for _a in "$@"; do
  case "$_a" in Submitter=*) SUBMITTER=${_a#Submitter=} ;; esac
done
if [ -z "$SUBMITTER" ]; then
  echo "FATAL: Submitter missing from scriptArgs."
  echo "       The LHE seed is derived from it, and without it every task would"
  echo "       reuse one series of seeds and generate duplicate events."
  echo "       submit_run3.sh passes it; a hand-written crabConfig must add"
  echo "       'Submitter=<your username>' to config.JobType.scriptArgs."
  exit 65
fi
# md5 so the value is the same on any machine: a resubmitted job has to
# regenerate the same events. 15 hex digits stay inside signed 64-bit.
SEED_HEX=$(printf '%s|%s|%s|%s' "$SUBMITTER" "$DIR" "$OUTTAG" "$NJOB" \
           | md5sum | cut -c1-15)
SEED=$(( (0x$SEED_HEX % 900000000) + 1 ))
echo "LHE seed: $SUBMITTER|$DIR|$OUTTAG|$NJOB -> $SEED"
# ----------------------------------------------------------------------------

# Where the finished NanoAOD is written. $DIR is appended to OUT_BASE, so
# DIR=<era> lands in .../pelai/HZg/root_DYfilter/phase1/<era>. An optional 5th
# scriptArg DEST=<full xrootd URL> overrides the whole thing.
# Fallback only: submit_run3.sh always passes DEST=. Your own subdirectory of
# the shared project space, so a manual run never writes into somebody
# else's area.
OUT_BASE="root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/${USER}/HZg/root_DYfilter/phase1"
ARGDEST=$5
DEST=${ARGDEST#*=}
if [ -z "$DEST" ]
then
    DEST="$OUT_BASE/$DIR"
fi
DEST=${DEST%/}
# One subdirectory per CRAB task. A task is capped at 10k jobs, so each
# directory stays far below the ~120k entries at which the EOS FUSE
# readdir starts failing (and, worse, failing with exit code 0).
DEST="$DEST/$OUTTAG"
TAG="DY2023postBPix"

# All conditions below are taken from the central production chain on McM:
#   GEN-SIM     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_postBPix_v2)
#   DIGI+HLT    CMSSW_13_0_14 (130X_mcRun3_2023_realistic_postBPix_v2), HLT:2023v12
#   MINIAOD     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_postBPix_v2)
#   NANOAOD     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_postBPix_v2)

# cmsenv is a shell alias and is not available in a non-interactive script,
# so switch release with scram runtime instead.
use_release () {
    rel=$1
    arch=$2
    export SCRAM_ARCH=$arch
    if [ ! -d $rel ]
    then
        scram p CMSSW $rel || exit 1
    fi
    cd $rel/src
    eval `scram runtime -sh`
    cd ../..
}

Fragment_filename=DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23BPix__fragment.py
NANOAOD_NAME="DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v4__privateProduction"

# The premix pileup list travels with the job through config.JobType.inputFiles,
# so there is exactly one copy of it. Use filelist: rather than dbs:, which
# restricts the job to files known to be on disk -- with dbs: the global
# redirector can pick a site holding no replica, and the job dies in DIGIPREMIX
# with FallbackFileOpenError.
PREMIX_LIST=$(ls premix_ondisk_*.txt 2>/dev/null | head -1)
if [ -z "$PREMIX_LIST" ]
then
    echo "premix filelist not found in job sandbox"
    exit 1
fi
echo "using premix filelist: $PREMIX_LIST ($(wc -l < $PREMIX_LIST) files)"

echo ---------------------------GEN-SIM-------------------------
# The generator filter is a private plugin, so it has to be compiled into the
# GEN-SIM release. The sources arrive through config.JobType.inputFiles.
use_release CMSSW_13_0_14 el8_amd64_gcc11
mkdir -p $CMSSW_BASE/src/Configuration/GenProduction/python
mkdir -p $CMSSW_BASE/src/HZgamma/DYGenFilter/plugins
cp $Fragment_filename $CMSSW_BASE/src/Configuration/GenProduction/python/
cp MatchDYFilter.cc BuildFile.xml $CMSSW_BASE/src/HZgamma/DYGenFilter/plugins/
cd $CMSSW_BASE/src
scram b -j 4 || exit 1
cd ../..

Output_filename=$TAG"_"$NJOB"__GS.root"
cmsDriver.py Configuration/GenProduction/python/$Fragment_filename \
    --python_filename $TAG"__GS__cfg_"$NJOB".py" --eventcontent RAWSIM \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier GEN-SIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_postBPix_v2 --beamspot Realistic25ns13p6TeVEarly2023Collision \
    --customise_commands "from IOMC.RandomEngine.RandomServiceHelper import RandomNumberServiceHelper ; randSvc = RandomNumberServiceHelper(process.RandomNumberGeneratorService) ; randSvc.populate() ; process.RandomNumberGeneratorService.externalLHEProducer.initialSeed = int($SEED)\nprocess.source.numberEventsInLuminosityBlock = cms.untracked.uint32(100)" \
    --step LHE,GEN,SIM --geometry DB:Extended --era Run3_2023 \
    --no_exec --mc -n $NEVENTS --nThreads 4
cmsRun $TAG"__GS__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "GEN-SIM Successful"
else
    exit 1
fi

echo ---------------------------DIGIPREMIX-HLT-------------------------
use_release CMSSW_13_0_14 el8_amd64_gcc11
Input_filename=$TAG"_"$NJOB"__GS.root"
Output_filename=$TAG"_"$NJOB"__DIGIPREMIX.root"
cmsDriver.py --python_filename $TAG"__DIGIPREMIX__cfg_"$NJOB".py" --eventcontent PREMIXRAW \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier GEN-SIM-RAW --fileout file:$Output_filename \
    --pileup_input "filelist:$PREMIX_LIST" \
    --conditions 130X_mcRun3_2023_realistic_postBPix_v2 --step DIGI,DATAMIX,L1,DIGI2RAW,HLT:2023v12 \
    --procModifiers premix_stage2 --geometry DB:Extended \
    --filein file:$Input_filename --datamix PreMix --era Run3_2023 \
    --no_exec --mc -n -1 --nThreads 4
cmsRun $TAG"__DIGIPREMIX__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "DIGIPREMIX Successful"
else
    exit 1
fi

echo ---------------------------AOD-------------------------
Input_filename=$TAG"_"$NJOB"__DIGIPREMIX.root"
Output_filename=$TAG"_"$NJOB"__AOD.root"
cmsDriver.py --python_filename $TAG"__AOD__cfg_"$NJOB".py" --eventcontent AODSIM \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier AODSIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_postBPix_v2 --step RAW2DIGI,L1Reco,RECO,RECOSIM \
    --geometry DB:Extended --filein file:$Input_filename --era Run3_2023 \
    --no_exec --mc -n -1 --nThreads 4
cmsRun $TAG"__AOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "AOD Successful"
else
    exit 1
fi

echo ---------------------------MINIAOD-------------------------
use_release CMSSW_13_0_14 el8_amd64_gcc11
Input_filename=$TAG"_"$NJOB"__AOD.root"
Output_filename=$TAG"_"$NJOB"__MINIAOD.root"
cmsDriver.py --python_filename $TAG"__MINIAOD__cfg_"$NJOB".py" --eventcontent MINIAODSIM \
    --customise_commands "process.prunedGenParticles.select.append('keep++ (abs(pdgId) == 111 || abs(pdgId) == 221) && pt > 5')\nprocess.prunedGenParticles.select.append('keep status == 1 && pt > 0.5')" \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier MINIAODSIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_postBPix_v2 --step PAT --geometry DB:Extended \
    --filein file:$Input_filename --era Run3_2023 \
    --no_exec --mc -n -1 --nThreads 4
cmsRun $TAG"__MINIAOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "MINIAOD Successful"
else
    exit 1
fi

echo ---------------------------NANOAOD-------------------------
use_release CMSSW_13_0_14 el8_amd64_gcc11
Input_filename=$TAG"_"$NJOB"__MINIAOD.root"
Output_filename=$NANOAOD_NAME"__job-"$NJOB"_"$OUTTAG".root"
cmsDriver.py --python_filename $TAG"__NANOAOD__cfg_"$NJOB".py" --eventcontent NANOAODSIM \
    --customise_commands "process.finalGenParticles.select.append('keep++ (abs(pdgId) == 111 || abs(pdgId) == 221) && pt > 5')\nprocess.finalGenParticles.select.append('keep status == 1 && pt > 0.5')" \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier NANOAODSIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_postBPix_v2 --step NANO --scenario pp \
    --filein file:$Input_filename --era Run3_2023 \
    --no_exec --mc -n -1 --nThreads 4
cmsRun $TAG"__NANOAOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "NANOAOD Successful"
else
    exit 1
fi

rm -f $TAG"_"$NJOB"__GS.root"
rm -f *inLHE.root
rm -f $TAG"_"$NJOB"__DIGIPREMIX.root"
rm -f $TAG"_"$NJOB"__AOD.root"
rm -f $TAG"_"$NJOB"__MINIAOD.root"

echo ---------------------------STAGEOUT-------------------------
OUTFILE=$NANOAOD_NAME"__job-"$NJOB"_"$OUTTAG".root"

# xrdcp does not create the target directory, so make sure it is there.
DEST_REDIR=$(echo $DEST | sed 's@\(root://[^/]*\)//.*@\1@')
DEST_PATH=$(echo $DEST | sed 's@root://[^/]*/@@')
xrdfs $DEST_REDIR mkdir -p $DEST_PATH

COPIED=0
for attempt in 1 2 3
do
    xrdcp -f $OUTFILE $DEST/. && COPIED=1 && break
    echo "xrdcp attempt $attempt to $DEST failed, retrying in 60 s"
    sleep 60
done

rm -rf CMSSW_13_0_14

if [ $COPIED -eq 1 ]
then
    echo "STAGEOUT Successful: $DEST/$OUTFILE"
    rm -f $OUTFILE
else
    echo "STAGEOUT FAILED after 3 attempts: $DEST/$OUTFILE"
    exit 1
fi
