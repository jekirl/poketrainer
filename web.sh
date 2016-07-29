#!/usr/bin/env bash
if [ "$#" == "1" ]; then
PORT=$1
else
PORT=8080
fi

xdg-open http://127.0.0.1:$PORT
cd webserver && php -S 0.0.0.0:$PORT router.php