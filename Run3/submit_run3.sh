#!/bin/bash
# Submit N Run 3 DY-filter CRAB tasks for one era.
#
#   ./submit_run3.sh [--dest <xrootd-url>] <era> <n_tasks> <your_tag> [first_index]
#
#   era         2022preEE | 2022postEE | 2023preBPix | 2023postBPix | 2024_2E | 2024_2Mu
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
    # Jobs per task (default 10000, the CRAB limit). For small acceptance
    # runs, so the test goes through the real submission path -- including
    # the SeedBase allocation -- instead of a hand-written config.
    --units) UNITS=$2; shift 2 ;;
    --units=*) UNITS=${1#--units=}; shift ;;
    *) break ;;
  esac
done

ERA=$1; N=$2; TAG=$3; START=${4:-1}
[ -z "$TAG" ] && {
  echo "usage: $0 [--dest <xrootd-url>] [--units N] <era> <n_tasks> <your_tag> [first_index]"
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
  DEST_BASE="$PROJECT/${U}/HZg/root_DYfilter/phase1"
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

# One generated config per task. They are throw-away -- kept only so a failed
# submission can be inspected -- so they go in their own directory instead of
# burying the six templates under a hundred generated files.
# Paths INSIDE the config (psetName, scriptExe, inputFiles, workArea) are
# resolved against the CWD of `crab submit`, not against the config's location,
# so this move is safe as long as you submit from this directory.

# --- LHE seed base (2026-09-13) ---------------------------------------------
# The payload used to set initialSeed to the ProcId, and every task runs
# ProcId 1..totalUnits, so the same-numbered jobs of different tasks shared an
# LHE seed and generated the same hard-process events. Measured across 13
# tasks: only 29.9% of the accumulated events were distinct.
#
# A registry, rather than a hard-coded tag->index table: any tag works without
# collisions, and resubmitting a task returns the SeedBase it already had
# (idempotent). Plain text, so it can be read and audited by hand.
SEED_REGISTRY=seed_registry.txt
SEED_BLOCKS=seed_blocks.txt
SEED_BLOCK_SIZE=10000000 # one block per submitter, 500 tasks each
SEED_STRIDE=20000        # >= totalUnits (10000), with a factor of two to spare
SEED_RESERVED=800000000  # block 80 and up: hand-written / test configs only
touch "$SEED_REGISTRY"

# Which block this submitter owns. Failing here rather than guessing a block is
# deliberate: a guessed block is the silent collision the scheme exists to stop.
seed_block() {
  local b
  b=$(awk -v u="$USER" '$1 == u {print $2; exit}' "$SEED_BLOCKS" 2>/dev/null)
  case "$b" in
    ''|*[!0-9]*)
      echo "ERROR: no seed block for '$USER' in $SEED_BLOCKS." >&2
      echo "       Append a line '<username> <next free block>', then submit" >&2
      echo "       again. Blocks in use:" >&2
      awk '!/^#/ && NF==2 {printf "         %-12s %s\n", $1, $2}' "$SEED_BLOCKS" >&2
      return 1 ;;
  esac
  [ "$b" -ge 1 ] && [ "$b" -lt 80 ] || {
    echo "ERROR: block $b is out of range (1..79)." >&2; return 1; }
  echo "$b"
}

# Allocate inside this submitter's block. Blocks do not overlap, so two people
# submitting at the same moment from their own clones cannot collide, with no
# pull and no shared file needed. The registry records what was issued.
alloc_seedbase() {       # $1 = key, e.g. 2022postEE/p1_1
  local key=$1 lock=.seed_registry.lock existing next lo hi blk tries=0
  blk=$(seed_block) || return 1
  lo=$((blk * SEED_BLOCK_SIZE))
  hi=$((lo + SEED_BLOCK_SIZE))
  while ! mkdir "$lock" 2>/dev/null; do
    tries=$((tries + 1))
    [ $tries -gt 60 ] && { echo "ERROR: seed registry locked for over 60 s" >&2; return 1; }
    sleep 1
  done
  # Same key twice returns the same value, so resubmitting a task is safe.
  # The key must be matched together with the submitter: <era>/<tag> is not
  # unique between people, and matching on it alone hands the second person the
  # first person's SeedBase -- which is the collision this is here to prevent.
  existing=$(awk -v k="$key" -v u="$USER" '$2 == k && $3 == u {print $1; exit}' "$SEED_REGISTRY")
  if [ -n "$existing" ]; then rmdir "$lock"; echo "$existing"; return 0; fi
  # Only values inside this block matter; everyone else's are irrelevant here.
  next=$(awk -v lo=$lo -v hi=$hi 'BEGIN{m=0} $1+0>=lo && $1+0<hi {if ($1+0 > m) m=$1+0} END{print m}' "$SEED_REGISTRY")
  [ "$next" -eq 0 ] && next=$lo
  next=$((next + SEED_STRIDE))
  if [ $((next + 10000)) -ge $hi ]; then
    rmdir "$lock"
    echo "ERROR: block $blk is full ($next). Take a second block." >&2; return 1; fi
  printf '%d %s %s %s\n' "$next" "$key" "$USER" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SEED_REGISTRY"
  rmdir "$lock"; echo "$next"
}
# ----------------------------------------------------------------------------

mkdir -p crab_configs

for i in $(seq "$START" $((START + N - 1))); do
  T=${TAG}_${i}
  WORK=crab_configs/crabConfig_${ERA}_${T}.py
  cp "$CFG" "$WORK"

  sed -i "s@\(config.General.requestName = \).*@\1'DY${ERA}_${T}'@" "$WORK"
  ARGS="'Nevents=10000', 'Tag=${T}', 'DIR=${DIR}', 'DEST=${OUT_BASE}/${DIR}'"
  [ -n "$FLAV" ] && ARGS="$ARGS, 'FLAV=${FLAV}'"
  # SeedBase goes last, so the existing positional arguments are untouched
  # ($2..$5 stay Nevents/Tag/DIR/DEST, and $6 stays FLAV for 2024). The
  # payload looks it up by name, so the position does not matter.
  SEEDBASE=$(alloc_seedbase "${ERA}/${T}") || exit 1
  ARGS="$ARGS, 'SeedBase=${SEEDBASE}'"
  echo "  seed base $SEEDBASE  (seeds $((SEEDBASE + 1))..$((SEEDBASE + 10000)))"
  sed -i "s@\(config.JobType.scriptArgs = \).*@\1[${ARGS}]@" "$WORK"
  if [ -n "$UNITS" ]; then
    sed -i "s@\(config.Data.totalUnits *= *\).*@\1${UNITS}@" "$WORK"
    echo "  totalUnits -> $UNITS"
  fi

  # 2024 spreads the load over 15 premix slices; everything else has one list
  if [ "$DIR" = 2024 ]; then
    S=$(printf "%02d" $(( (i - 1) % 15 )))
    sed -i "s@premix_ondisk_2024_slice[0-9]*\.txt@premix_ondisk_2024_slice${S}.txt@" "$WORK"
  fi

  echo "submitting $WORK"
  crab submit -c "$WORK"
done
echo "submitted $N task(s) for $ERA, tag $TAG, index $START..$((START + N - 1))"
