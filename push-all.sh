#!/usr/bin/env bash
# push-all.sh — Push to both repos in one command
#
# Usage:
#   ./push-all.sh              (pushes current branch to main + frontend)
#   ./push-all.sh "my message" (commits all changes first, then pushes)

set -e

# If a commit message is passed, commit everything first
if [ -n "$1" ]; then
    echo ">> Committing changes..."
    git add -A
    git commit -m "$1"
fi

echo ""
echo ">> [1/2] Pushing to main repo (Campus-Voice)..."
git push origin main

echo ""
echo ">> [2/2] Pushing frontend to campus-voice-frontend..."
git subtree push --prefix=Campus-Voice-SREC-main frontend main

echo ""
echo "Done. Both repos are up to date."
echo "  Main     -> https://github.com/MSudharsh110305/Campus-Voice"
echo "  Frontend -> https://github.com/MSudharsh110305/campus-voice-frontend"
