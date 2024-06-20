#!/usr/bin/env bash

# shellcheck disable=SC2068
docker exec -it flang /root/host/proxy.sh "${PWD}" ${@}
cp -rf inbox/* "${PWD}" &> /dev/null
rm -rf inbox/* &> /dev/null
