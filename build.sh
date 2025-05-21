#!/usr/bin/env bash

set -e

rm -rf lambda_build
mkdir -p lambda_build

cp cdk/lambda/lambda_handler.py lambda_build/
cp -r pylaform lambda_build/
cp app.py lambda_build/pylaform/
cp -r scripts lambda_build/
cp -r pylaform/templates lambda_build/pylaform/
cp -r pylaform/static lambda_build/pylaform/


# Remove unnecessary files from the build (optional but recommended)
find lambda_build/pylaform -name '__pycache__' -type d -exec rm -rf {} +
find lambda_build/pylaform -name '*.pyc' -delete
find lambda_build/pylaform -name '*.db' -delete
find lambda_build/pylaform -name '*.db.bak' -delete

echo "Build complete. Lambda source is in lambda_build/"
