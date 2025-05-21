#!/usr/bin/env bash
rm -rf cdk.out/
cd ..
./build.sh
cd cdk
cdk synth
cdk deploy PylaformAmazonQStack --parameters AmazonQApplicationId=6acc65fb-390b-4d8d-a10b-05bea5265fd8
cdk deploy MonitoringStack

