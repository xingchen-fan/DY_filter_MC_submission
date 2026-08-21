echo "this is not a test"

echo $(pwd)

ARG=$2
ARGTAG=$3
ARGDIR=$4
DIR=${ARGDIR#*=}
NEVENTS=${ARG#*=}
NJOB=$1
OUTTAG=${ARGTAG#*=}
# Where the finished NanoAOD is written. $DIR is appended to OUT_BASE, so
# DIR=<era> lands in .../pelai/HZg/root_DYmix/<era>. An optional 5th
# scriptArg DEST=<full xrootd URL> overrides the whole thing.
# Fallback only: submit_run3.sh always passes DEST=. Your own subdirectory of
# the shared project space, so a manual run never writes into somebody
# else's area.
OUT_BASE="root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/${USER}/HZg/root_DYmix"
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
TAG="DY2023preBPix"

# All conditions below are taken from the central production chain on McM:
#   GEN-SIM     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_v14)
#   DIGI+HLT    CMSSW_13_0_14 (130X_mcRun3_2023_realistic_v14), HLT:2023v12
#   MINIAOD     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_v14)
#   NANOAOD     CMSSW_13_0_14 (130X_mcRun3_2023_realistic_v14)

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

Fragment_filename=DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23__fragment.py
NANOAOD_NAME="DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v14-v2__privateProduction"

# premix pileup 清單：透過 config.JobType.inputFiles 隨 job 送來，只會有一份。
# 用 filelist: 而非 dbs:，可確保只讀「確定在 disk 上」的檔案 —— 直接用 dbs: 會讓
# 全域 redirector 選到沒有複本的站點，job 在 DIGIPREMIX 以 FallbackFileOpenError 死掉。
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
    --conditions 130X_mcRun3_2023_realistic_v14 --beamspot Realistic25ns13p6TeVEarly2023Collision \
    --customise_commands "from IOMC.RandomEngine.RandomServiceHelper import RandomNumberServiceHelper ; randSvc = RandomNumberServiceHelper(process.RandomNumberGeneratorService) ; randSvc.populate() ; process.RandomNumberGeneratorService.externalLHEProducer.initialSeed = int($NJOB)\nprocess.source.numberEventsInLuminosityBlock = cms.untracked.uint32(100)" \
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
    --conditions 130X_mcRun3_2023_realistic_v14 --step DIGI,DATAMIX,L1,DIGI2RAW,HLT:2023v12 \
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
    --conditions 130X_mcRun3_2023_realistic_v14 --step RAW2DIGI,L1Reco,RECO,RECOSIM \
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
    --customise_commands "process.prunedGenParticles.select.append('keep++ (abs(pdgId) == 111 || abs(pdgId) == 221) && pt > 5')" \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier MINIAODSIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_v14 --step PAT --geometry DB:Extended \
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
    --customise_commands "process.finalGenParticles.select.append('keep++ (abs(pdgId) == 111 || abs(pdgId) == 221) && pt > 5')" \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --datatier NANOAODSIM --fileout file:$Output_filename \
    --conditions 130X_mcRun3_2023_realistic_v14 --step NANO --scenario pp \
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
