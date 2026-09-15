#!/usr/bin/env python3
"""Build job/2022postEEDY_keepmini.sh from job/2022postEEDY.sh.

The validation batch needs the MiniAOD kept, so the AN photon-origin
classification can be run on `packedGenParticles` (MiniAOD, the complete
status-1 collection the AN actually uses) and on NanoAOD `GenPart` for the SAME
events. Without a same-event comparison there is no way to say whether the new
keep rules let NanoAOD reproduce the MiniAOD-based table.

MiniAOD is ~18 MB per job at the new filter's ~303 events/job, so 5 jobs cost
about 90 MB.

Input : job/2022postEEDY.sh
Output: job/2022postEEDY_keepmini.sh
"""
import os
import sys

# tools/ sits one level below Run3/; job/ is one level up from here
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "job", "2022postEEDY.sh")
DST = os.path.join(HERE, "job", "2022postEEDY_keepmini.sh")

DROP_RM = 'rm -f $TAG"_"$NJOB"__MINIAOD.root"\n'
KEEP_NOTE = (
    "# keepmini variant: the MiniAOD is not deleted, it is staged out alongside the\n"
    "# NanoAOD, so that GenPart and packedGenParticles can be compared on the same\n"
    "# events.\n")

ANCHOR = "rm -rf CMSSW_12_4_11_patch3 CMSSW_13_0_13\n"
MINI_STAGEOUT = '''
echo ---------------------------STAGEOUT-MINIAOD-------------------------
MINIFILE=$TAG"_"$NJOB"__MINIAOD.root"
xrdfs $DEST_REDIR mkdir -p $DEST_PATH/mini
MINI_COPIED=0
for attempt in 1 2 3
do
    xrdcp -f $MINIFILE $DEST/mini/. && MINI_COPIED=1 && break
    echo "mini xrdcp attempt $attempt to $DEST/mini failed, retrying in 60 s"
    sleep 60
done
if [ $MINI_COPIED -eq 1 ]
then
    echo "MINIAOD STAGEOUT Successful: $DEST/mini/$MINIFILE"
else
    echo "MINIAOD STAGEOUT FAILED after 3 attempts"
fi
rm -f $MINIFILE

'''


def main():
    with open(SRC) as fh:
        text = fh.read()

    if text.count(DROP_RM) != 1:
        sys.exit("expected exactly one MiniAOD rm line, found %d" % text.count(DROP_RM))
    if text.count(ANCHOR) != 1:
        sys.exit("expected exactly one CMSSW cleanup line, found %d" % text.count(ANCHOR))

    text = text.replace(DROP_RM, KEEP_NOTE)
    text = text.replace(ANCHOR, MINI_STAGEOUT + ANCHOR)

    with open(DST, "w") as fh:
        fh.write(text)
    os.chmod(DST, 0o755)

    # verify
    checks = [
        ("MiniAOD kept", DROP_RM not in text),
        ("mini stage-out present", "STAGEOUT-MINIAOD" in text),
        ("mini directory created", "mkdir -p $DEST_PATH/mini" in text),
        ("NanoAOD stage-out intact", "STAGEOUT Successful: $DEST/$OUTFILE" in text),
        ("new keep rules intact", text.count("keep status == 1 && pt > 0.5") == 2),
    ]
    ok = True
    for name, res in checks:
        print("  %-24s %s" % (name, "OK" if res else "FAIL"))
        ok = ok and res
    print("\nwrote %s" % DST)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
