#!/bin/bash
# This script is a utility for the BeeWare team to publish packages to the
# https://anaconda.org/beeware repository. It won't be any use to you unless
# you have write permissions to the `beeware` repo.
#
# It attempts to publish any package in the `dist` folder, moving it to the
# `published` folder when the upload is successful
#
# Usage:
#
#   $ source ~/opt/anaconda3/bin/activate
#   (base) $ anaconda login
#   (base) $ ./publish.sh
#

for f in $(find dist -name "*.whl"); do
   echo "***** PUBLISH $f ***********************************"
   anaconda upload -u beeware $f
   if [[ $? == 0 ]]; then
	   mv $f published
   fi
done
