#!/bin/sh
set -e
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb --ignore-existing local/e-room-rag-docs
mc mb --ignore-existing local/e-room-avatars
mc mb --ignore-existing local/e-room-tts
mc anonymous set download local/e-room-tts
