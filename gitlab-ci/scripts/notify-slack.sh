#!/bin/bash
# Slack Notification Helper Script for GitLab CI
#
# Usage: ./notify-slack.sh "message" [channel]
#
# Environment variables required:
#   SLACK_WEBHOOK_URL - Slack incoming webhook URL
#
# Optional environment variables:
#   CI_PROJECT_NAME - Project name
#   CI_PIPELINE_URL - Pipeline URL
#   CI_COMMIT_SHORT_SHA - Commit SHA
#   GITLAB_USER_LOGIN - User who triggered

set -e

MESSAGE="${1:-Pipeline notification}"
CHANNEL="${2:-}"

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "Warning: SLACK_WEBHOOK_URL not set, skipping notification"
    exit 0
fi

# Build payload
PAYLOAD=$(cat <<EOF
{
    "text": "${MESSAGE}",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "${MESSAGE}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*Project:* ${CI_PROJECT_NAME:-Unknown} | *Commit:* ${CI_COMMIT_SHORT_SHA:-N/A} | *User:* ${GITLAB_USER_LOGIN:-System}"
                }
            ]
        }
    ]
}
EOF
)

# Add channel if specified
if [ -n "$CHANNEL" ]; then
    PAYLOAD=$(echo "$PAYLOAD" | jq --arg channel "$CHANNEL" '. + {channel: $channel}')
fi

# Send notification
curl -s -X POST \
    -H 'Content-type: application/json' \
    --data "$PAYLOAD" \
    "$SLACK_WEBHOOK_URL"

echo "Slack notification sent"

