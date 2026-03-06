#!/bin/sh
# Ensure mounted volumes are writable by appuser (host dirs often are root-owned)
chown -R appuser:appuser /app/data /app/jobs /app/outputs 2>/dev/null || true
exec gosu appuser "$@"
