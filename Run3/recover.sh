#!/bin/bash
# Recover a submission: retry what failed, and remove what silently did not.
#
#   ./recover.sh <era> <tag>            # report only, changes nothing
#   ./recover.sh <era> <tag> --apply    # resubmit failed jobs, delete bad files
#
#   SAMPLE=500 ./recover.sh ...         # check more files per task (default 200)
#   FULL=1 ./recover.sh ...             # check every file; hours, not minutes
#
# Two things go wrong here and they need opposite treatment.
#
# 1. Jobs CRAB knows failed. `crab resubmit` retries them, and because the seed
#    is derived from submitter, era, tag and ProcId, the retry regenerates the
#    same events rather than new ones. Nothing is lost.
#
# 2. Jobs that exited 0 and wrote almost nothing. Measured at a site with no
#    premix replica: one job in ten wrote 7 events where the rest wrote ~300,
#    and CRAB called all of them finished. These cannot be retried --
#
#        Only jobs in status failed can be resubmitted.
#
#    -- so the only thing to do is delete the files and produce the missing
#    events somewhere else. That is a top-up with a NEW tag, not a retry: a new
#    tag means a new seed, so the events differ from the ones that were lost,
#    which is fine. What is needed is the count, not those particular events.
#
# Run it from the Run3 directory, inside the environment from TUTORIAL
# section 2.
set -o pipefail
ERA=$1; TAG=$2; APPLY=0; [ "$3" = "--apply" ] && APPLY=1
[ -z "$TAG" ] && { echo "usage: $0 <era> <tag> [--apply]"; exit 1; }

DEST_BASE=${DEST_BASE:-/eos/project/h/htozg-dy-privatemc/${USER}/HZg/root_DYfilter/phase1}
case $ERA in 2024_2E|2024_2Mu) DIR=2024 ;; *) DIR=$ERA ;; esac
PROJ=$(ls -d crab_projects/crab_DY${ERA}_${TAG}_* 2>/dev/null)
[ -z "$PROJ" ] && { echo "no crab_projects/crab_DY${ERA}_${TAG}_* here"; exit 1; }

# Get the credential question out of the way first, on its own, where you can
# actually answer it. CRAB renews its delegation on myproxy.cern.ch with
# `myproxy-init -C ~/.globus/usercert.pem -y ~/.globus/userkey.pem`, so it reads
# the passphrase-protected key and stops to ask for the passphrase. Asked from
# inside the loop below it is unanswerable: that call is wrapped in $( ) with a
# pipe, so its output is captured rather than shown, and `timeout` puts it in
# its own process group with no controlling terminal, so what you type never
# reaches it. You see the prompt and the characters go nowhere.
echo "checking the credential (you may be asked for your GRID pass phrase) ..."
crab status -d "$(echo "$PROJ" | head -1)" > /dev/null || {
  echo "crab cannot run. If it asked for a pass phrase, that is the PEM one you"
  echo "set when converting mycert.p12 -- see GRID_CERTIFICATE.md section 5."
  exit 1; }
echo "era $ERA, tag $TAG, $(echo "$PROJ" | wc -l) task(s)"
[ "$APPLY" -eq 0 ] && echo "REPORT ONLY -- nothing will be changed. Add --apply to act."
echo

# ---- 1. failed jobs -------------------------------------------------------
echo "=== jobs CRAB reports as failed ==="
tot=0
for p in $PROJ; do
  n=$(timeout --foreground 600 crab status -d "$p" 2>&1 \
      | awk '/^[[:space:]]+failed[[:space:]]/{s=$0; sub(/.*\(/,"",s); sub(/\/.*/,"",s);
             gsub(/[^0-9]/,"",s); print s+0}')
  n=${n:-0}; tot=$((tot+n))
  printf "  %-46s %5d failed\n" "$(basename "$p")" "$n"
  if [ "$n" -gt 0 ] && [ "$APPLY" -eq 1 ]; then
    timeout --foreground 600 crab resubmit -d "$p" 2>&1 | grep -iE "Success|Error" | head -1 | sed 's/^/      /'
  fi
done
echo "  total $tot"
[ "$tot" -gt 0 ] && [ "$APPLY" -eq 0 ] && echo "  -> --apply runs 'crab resubmit' on each task above"

# ---- 2. files that succeeded and are wrong anyway -------------------------
echo
echo "=== files that exited 0 with almost no events ==="
# Sampled, and once per task rather than twice.
#
# This step opens every file it checks to read its event count, over EOS, and
# that is slow enough to matter: a finished task holds 10,000 files, a share
# holds several tasks, and a full scan of all of them runs for hours with
# nothing printed meanwhile -- which is indistinguishable from a hang, and was
# taken for one on 2026-09-18.
#
# So it samples $SAMPLE files per task by default and says which task it is on
# while it works. Stunted files come from a site behaving badly, not from one
# unlucky job, so a sample finds the problem; it does not find every instance,
# which is what --full is for once you know you have one.
# 20 per task, not more: a file costs about 1.6 s to open on EOS, so 20 across
# nine tasks is five minutes and 200 would be the best part of an hour -- for
# something meant to run before every submission. Twenty is enough to *detect*
# the condition (a 10% rate hides from 20 files 12% of the time, and it would
# have to hide from every task at once), and detecting is this step's job. When
# it finds something, rerun with FULL=1 to enumerate and delete every instance;
# that scan is hours, but by then you know you need it.
SAMPLE=${SAMPLE:-20}
[ "$FULL" = "1" ] && SAMPLE=""
LIST=$(mktemp); trap 'rm -f "$LIST"' EXIT
for p in $PROJ; do
  t=$(basename "$p" | sed "s@crab_DY${ERA}_@@")
  d="$DEST_BASE/$DIR/$t"
  [ -d "$d" ] || continue
  printf "  %-14s " "$t"
  OUT=$(python3 tools/check_event_counts.py --dir "$d" \
          ${SAMPLE:+--sample $SAMPLE} 2>&1)
  echo "$OUT" | grep -E "^[0-9]+ files|^sampling" | tr '\n' ' '; echo
  echo "$OUT" | sed -n 's/^ *\([0-9]\+\) events  \(.*\)$/\2/p' \
    | sed "s@^@$d/@" >> "$LIST"
done
BAD=$(grep -c . "$LIST" 2>/dev/null || echo 0)
echo
echo "  $BAD stunted file(s)"
if [ "$BAD" -gt 0 ]; then
  if [ "$APPLY" -eq 1 ]; then
    while read -r f; do
      xrdfs eosuser.cern.ch rm "$f" && echo "    deleted $(basename "$f")"
    done < "$LIST"
  else
    echo "  -> --apply deletes them"
  fi
  echo
  echo "  Those events are gone and cannot be retried. Produce the missing"
  echo "  $BAD job(s) worth under a NEW tag, for example:"
  echo "      ./submit_run3.sh --units $BAD $ERA 1 ${TAG}fix 1"
  echo "  A new tag means a new seed, so the events differ from the ones lost."
fi
