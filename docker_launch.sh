#!/usr/bin/env bash

set -u

if [ ! -f /config.json ]; then
	echo "No config.json specified; please mount it to docker container via: "
	echo "	docker run -ti -v \$(pwd)/config.json:/config.json pokecli -i <id>"
	exit 1
fi

python web.py &
python pokecli.py $1 $2
