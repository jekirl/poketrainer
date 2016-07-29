#!/usr/bin/env bash
if [ "$#" == "1" ]; then
PORT=$1
else
PORT=8080
fi

php -S 0.0.0.0:$PORT router.php