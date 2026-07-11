#!/bin/sh
# Watchdog: startet Gunicorn, falls es nicht (mehr) laeuft.
# Fuer Cron gedacht (@reboot + alle paar Minuten) -> Umgebung heilt sich selbst
# nach Server-Neustart oder Prozess-Absturz.
#
# Aufruf:  keepalive.sh <PORT> <WORKERS> <APP_ENV>
PORT="$1"
WORKERS="${2:-1}"
ENVNAME="${3:-prod}"
APP="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$APP" || exit 0

# Laeuft schon und antwortet? -> nichts tun.
if curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    exit 0
fi

[ -x .venv/bin/gunicorn ] || exit 0
mkdir -p logs tmp

# evtl. toten Prozess aufraeumen
if [ -f tmp/gunicorn.pid ]; then
    kill "$(cat tmp/gunicorn.pid)" 2>/dev/null || true
fi

set -a
[ -f .env ] && . .env
set +a
export APP_ENV="$ENVNAME"

nohup .venv/bin/gunicorn run:app --bind "127.0.0.1:$PORT" --workers "$WORKERS" --timeout 120 \
    --access-logfile logs/access.log --error-logfile logs/error.log >/dev/null 2>&1 &
echo $! > tmp/gunicorn.pid
