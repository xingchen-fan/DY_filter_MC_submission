#!/bin/bash
# Submit N Run 3 DY-filter CRAB tasks for one era.
#
#   ./submit_run3.sh [--dest <xrootd-url>] <era> <n_tasks> <your_tag> [first_index]
#
#   era         2022postEE | 2023preBPix | 2023postBPix | 2024_2E | 2024_2Mu
#   n_tasks     how many tasks; each is 10,000 jobs (CRAB's per-task limit)
#   your_tag    goes into the request name and the output file names, so two
#               people submitting the same era do not collide -- use your
#               initials, e.g. pz
#   first_index start of the numbering (default 1); use it to continue a series
#   --dest      output base. Defaults to YOUR OWN subdirectory of the shared
#               project space, derived from $USER, so everybody contributes to
#               the same place without ever writing into somebody else's area.
#               The directory is created if it does not exist yet.
#
# Every task writes to a subdirectory of its own under the output base, which
# is what keeps a single EOS directory from growing past the ~120k files where
# readdir starts failing.
set -eo pipefail

DEST_BASE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dest) DEST_BASE=$2; shift 2 ;;
    --dest=*) DEST_BASE=${1#--dest=}; shift ;;
    *) break ;;
  esac
done

ERA=$1; N=$2; TAG=$3; START=${4:-1}
[ -z "$TAG" ] && {
  echo "usage: $0 [--dest <xrootd-url>] <era> <n_tasks> <your_tag> [first_index]"
  exit 1; }

CFG=crabConfig_${ERA}.py
[ -f "$CFG" ] || { echo "no such era: $ERA (see $0 header)"; exit 1; }

# Fail here rather than on the worker node hours later.
[ -n "$CMSSW_BASE" ] || {
  echo "ERROR: no CMSSW environment. Make one (any el8 release) and run"
  echo "       'eval \`scram runtime -sh\`' in it -- see README, 'Setup'."; exit 1; }
case "$SCRAM_ARCH" in
  el8_*) ;;
  *) echo "ERROR: SCRAM_ARCH is '$SCRAM_ARCH', expected el8_*."
     echo "       Every production release is el8, and the arch you submit from"
     echo "       decides the grid job's container. Start with 'cmssw-el8'."; exit 1;;
esac
command -v crab >/dev/null || {
  echo "ERROR: crab not found -- source /cvmfs/cms.cern.ch/common/crab-setup.sh"; exit 1; }
voms-proxy-info -exists -valid 1:00 >/dev/null 2>&1 || {
  echo "ERROR: no valid grid proxy (need >1 h)."
  echo "       voms-proxy-init --rfc --voms cms -valid 192:00"; exit 1; }

# Default: your own subdirectory of the shared project space. Everybody's
# output lands under one project, but never inside somebody else's directory.
PROJECT=root://eosuser.cern.ch//eos/project/h/htozg-dy-privatemc
if [ -z "$DEST_BASE" ]; then
  U=${USER:?USER not set}
  DEST_BASE="$PROJECT/${U}/HZg/root_DYmix"
fi
OUT_BASE=$DEST_BASE

# Create the base if it is not there yet; xrdfs mkdir -p is idempotent, but
# stat first so the message says what actually happened.
REDIR=$(echo "$OUT_BASE" | sed 's@\(root://[^/]*\)//.*@\1@')
BPATH=$(echo "$OUT_BASE" | sed 's@root://[^/]*/@@')
if xrdfs "$REDIR" stat "$BPATH" >/dev/null 2>&1; then
  echo "output base: $OUT_BASE  (exists)"
else
  echo "output base: $OUT_BASE  (creating)"
  xrdfs "$REDIR" mkdir -p "$BPATH" || {
    echo "ERROR: cannot create $BPATH"
    echo "       You need write access to the project space -- ask to be added"
    echo "       to the cernbox-project-htozg-dy-privatemc-writers e-group."
    exit 1; }
fi
case $ERA in
  2024_2E)  DIR=2024; FLAV=2E  ;;
  2024_2Mu) DIR=2024; FLAV=2Mu ;;
  *)        DIR=$ERA; FLAV=""  ;;
esac

for i in $(seq "$START" $((START + N - 1))); do
  T=${TAG}_${i}
  WORK=crabConfig_${ERA}_${T}.py
  cp "$CFG" "$WORK"

  sed -i "s@\(config.General.requestName = \).*@\1'DY${ERA}_${T}'@" "$WORK"
  ARGS="'Nevents=10000', 'Tag=${T}', 'DIR=${DIR}', 'DEST=${OUT_BASE}/${DIR}'"
  [ -n "$FLAV" ] && ARGS="$ARGS, 'FLAV=${FLAV}'"
  sed -i "s@\(config.JobType.scriptArgs = \).*@\1[${ARGS}]@" "$WORK"

  # 2024 spreads the load over 15 premix slices; everything else has one list
  if [ "$DIR" = 2024 ]; then
    S=$(printf "%02d" $(( (i - 1) % 15 )))
    sed -i "s@premix_ondisk_2024_slice[0-9]*\.txt@premix_ondisk_2024_slice${S}.txt@" "$WORK"
  fi

  echo "submitting $WORK"
  crab submit -c "$WORK"
done
echo "submitted $N task(s) for $ERA, tag $TAG, index $START..$((START + N - 1))"
