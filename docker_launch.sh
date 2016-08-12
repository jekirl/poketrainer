#!/usr/bin/env bash

set -u

if [ ! -f /config.json ]; then
	echo "No config.json specified; please mount it to docker container via: "
	echo "	docker run -ti -v \$(pwd)/config.json:/config.json pokecli -i <id>"
	exit 1
fi
if [ -n $WEBNAME ]; then
	echo "WEBNAME SPECIFIED, replacing webpyusername1 in CLSniper.py"
	sed -i s/webpyusername1/"$WEBNAME"/g CLSniper.py
	sed -i /webpyusername[2-3]/d CLSniper.py
fi
python web.py &
python pokecli.py $1 $2
