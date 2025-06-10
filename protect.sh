#!/bin/bash
# Quick Protection Commands

case "$1" in
    start)
        echo "Starting file protection..."
        python protect.py start
        ;;
    stop)
        echo "Stopping file protection..."
        python protect.py stop
        ;;
    status)
        echo "Checking status..."
        python protect.py status
        ;;
    commit)
        echo "Committing changes safely..."
        python protect.py commit "${@:2}"
        ;;
    *)
        echo "Usage: ./protect.sh [start|stop|status|commit]"
        echo ""
        echo "  ./protect.sh start    - Start monitoring files"
        echo "  ./protect.sh stop     - Stop monitoring"
        echo "  ./protect.sh status   - Show current status"
        echo "  ./protect.sh commit   - Safely commit changes"
        ;;
esac
