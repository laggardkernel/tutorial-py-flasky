#!/bin/sh
# vim: fdm=marker foldlevel=0 sw=2 ts=2 sts=2

source venv/bin/activate

while true; do
  flask deploy
  if [ "$?" == "0" ]; then
    break
  fi
  echo "Deploy command failed, retrying in 5 secs..."
  sleep 5
done

# start a server listening on 0.0.0.0, and output log into stdout
exec gunicorn -b :5000 --access-logfile - --error-logfile - flasky:app
