#!/bin/bash

config=$1
nsub=$2
logname=$3
outdir=$4
tag=$5

count=1
while [ $count -le $((nsub)) ]
do
    sed -i "s@\(config.General.requestName = \).*@\1\'$logname\_$count\'@g" $config
    sed -i "s@\(config.JobType.scriptArgs = \).*@\1[\'Nevents=10000\', \'Tag=$tag\_$count\', \'DIR=$outdir\']@g" $config
    crab submit -c $config
    echo Submission $count is submitted.
    ((count++))
done
echo All submitted.
