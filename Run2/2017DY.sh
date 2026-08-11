echo "this is not a test"

echo $(pwd)

ARG=$2
ARGTAG=$3
ARGDIR=$4
DIR=${ARGDIR#*=}
NEVENTS=${ARG#*=}
NJOB=$1 #$(($1+${INDEX#*=}))
OUTTAG=${ARGTAG#*=}
TAG="DY2017"

NANOAOD_NAME="DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8__RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v8-v1__privateProduction"
Fragment_filename=DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8__RunIISummer20UL17__fragment.py

echo ---------------------------GEN-------------------------
Output_filename=$TAG"_"$NJOB"__LHE.root"
cmsDriver.py Configuration/GenProduction/python/$Fragment_filename --python_filename $TAG"__LHE__cfg_"$NJOB".py" --eventcontent RAWSIM,LHE --customise Configuration/DataProcessing/Utils.addMonitoring --datatier GEN,LHE --fileout file:$Output_filename --conditions 106X_mc2017_realistic_v6 --beamspot Realistic25ns13TeVEarly2017Collision --customise_commands "from IOMC.RandomEngine.RandomServiceHelper import RandomNumberServiceHelper ; randSvc = RandomNumberServiceHelper(process.RandomNumberGeneratorService) ; randSvc.populate()\n process.source.numberEventsInLuminosityBlock = cms.untracked.uint32(100)" --step LHE,GEN --geometry DB:Extended --era Run2_2017 --no_exec --mc -n $NEVENTS
cmsRun $TAG"__LHE__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "GEN Successful"
else
    exit 1
fi

echo ---------------------------SIM-------------------------
Input_filename=$TAG"_"$NJOB"__LHE.root"
Output_filename=$TAG"_"$NJOB"__SIM.root"
cmsDriver.py --python_filename $TAG"__SIM__cfg_"$NJOB".py" --eventcontent RAWSIM --customise Configuration/DataProcessing/Utils.addMonitoring --datatier GEN-SIM --fileout file:$Output_filename --conditions 106X_mc2017_realistic_v6 --beamspot Realistic25ns13TeVEarly2017Collision --step SIM --geometry DB:Extended --filein file:$Input_filename --era Run2_2017 --runUnscheduled --no_exec --mc -n -1
cmsRun $TAG"__SIM__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "SIM Successful"
else
    exit 1
fi

echo ---------------------------DIGIPREMIX-------------------------
Input_filename=$TAG"_"$NJOB"__SIM.root"
Output_filename=$TAG"_"$NJOB"__DIGIPREMIX.root"
cmsDriver.py --python_filename $TAG"__DIGIPREMIX__cfg_"$NJOB".py" --eventcontent PREMIXRAW --customise Configuration/DataProcessing/Utils.addMonitoring --datatier GEN-SIM-DIGI --fileout file:$Output_filename --pileup_input "filelist:2017_degipremix_files_disk.txt" --conditions 106X_mc2017_realistic_v6 --step DIGI,DATAMIX,L1,DIGI2RAW --procModifiers premix_stage2 --geometry DB:Extended --filein file:$Input_filename --datamix PreMix --era Run2_2017 --runUnscheduled --no_exec --mc -n -1
cmsRun $TAG"__DIGIPREMIX__cfg_"$NJOB".py"
#dbs:/Neutrino_E-10_gun/RunIISummer20ULPrePremix-UL17_106X_mc2017_realistic_v6-v3/PREMIX

if [ -e $Output_filename ]
then
    echo "DIGIPREMIX Successful"
else
    exit 1
fi

echo ---------------------------HLT-------------------------
Input_filename=$TAG"_"$NJOB"__DIGIPREMIX.root"
Output_filename=$TAG"_"$NJOB"__HLT.root"
scram p CMSSW CMSSW_9_4_14_UL_patch1
cd CMSSW_9_4_14_UL_patch1/src
cmsenv
cd ../..
cmsDriver.py --python_filename $TAG"__HLT__cfg_"$NJOB".py" --eventcontent RAWSIM --customise Configuration/DataProcessing/Utils.addMonitoring --datatier GEN-SIM-RAW --fileout file:$Output_filename --conditions 94X_mc2017_realistic_v15 --customise_commands 'process.source.bypassVersionCheck = cms.untracked.bool(True)' --step HLT:2e34v40 --geometry DB:Extended --filein file:$Input_filename --era Run2_2017 --no_exec --mc -n -1
cmsRun $TAG"__HLT__cfg_"$NJOB".py"
rm -rf CMSSW_9_4_14_UL_patch1

if [ -e $Output_filename ]
then
    echo "HLT Successful"
else
    exit 1
fi

echo ---------------------------AOD-------------------------
Input_filename=$TAG"_"$NJOB"__HLT.root"
Output_filename=$TAG"_"$NJOB"__AOD.root"
scram p CMSSW CMSSW_10_6_40
cd CMSSW_10_6_40/src
cmsenv
cd ../..
cmsDriver.py --python_filename $TAG"__AOD__cfg_"$NJOB".py" --eventcontent AODSIM --customise Configuration/DataProcessing/Utils.addMonitoring --datatier AODSIM --fileout file:$Output_filename --conditions 106X_mc2017_realistic_v6 --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended --filein file:$Input_filename --era Run2_2017 --runUnscheduled --no_exec --mc -n -1
cmsRun $TAG"__AOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "AOD Successful"
else
    exit 1
fi

echo ---------------------------MINIAOD-------------------------
Input_filename=$TAG"_"$NJOB"__AOD.root"
Output_filename=$TAG"_"$NJOB"__MINIAOD.root"
cmsDriver.py  --python_filename $TAG"__MINIAOD__cfg_"$NJOB".py" --eventcontent MINIAODSIM --customise Configuration/DataProcessing/Utils.addMonitoring --datatier MINIAODSIM --fileout file:$Output_filename --conditions 106X_mc2017_realistic_v9 --step PAT --procModifiers run2_miniAOD_UL --geometry DB:Extended --filein file:$Input_filename --era Run2_2017 --runUnscheduled --no_exec --mc -n -1
cmsRun $TAG"__MINIAOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "MINIAOD Successful"
else
    exit 1
fi

echo ---------------------------NANOAOD-------------------------
Input_filename=$TAG"_"$NJOB"__MINIAOD.root"
Output_filename=$NANOAOD_NAME"__job-"$NJOB"_"$OUTTAG".root"
cmsDriver.py --python_filename $TAG"__NANOAOD__cfg_"$NJOB".py" --eventcontent NANOAODSIM --customise Configuration/DataProcessing/Utils.addMonitoring --datatier NANOAODSIM --fileout file:$Output_filename --conditions 106X_mc2017_realistic_v9 --step NANO --filein file:$Input_filename --era Run2_2017,run2_nanoAOD_106Xv2 --no_exec --mc -n -1
cmsRun $TAG"__NANOAOD__cfg_"$NJOB".py"

if [ -e $Output_filename ]
then
    echo "NANOAOD Successful"
else
    exit 1
fi

rm -f $TAG"_"$NJOB"__LHE.root"
rm -f *inLHE.root
rm -f $TAG"_"$NJOB"__SIM.root"
rm -f $TAG"_"$NJOB"__DIGIPREMIX.root"
rm -f $TAG"_"$NJOB"__HLT.root"
rm -f $TAG"_"$NJOB"__AOD.root"
rm -f $TAG"_"$NJOB"__MINIAOD.root"

xrdcp  $NANOAOD_NAME"__job-"$NJOB"_"$OUTTAG".root" root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc/$DIR/.
rm -f $NANOAOD_NAME"__job-"$NJOB"_"$OUTTAG".root"
rm -rf CMSSW_10_6_40
