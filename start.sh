#!/bin/bash
# RAG Chatbot Server Control Script

PORT=${1:-7860}
HOST=${2:-localhost}

echo "Stopping any existing RAG chatbot processes..."
pkill -f "python -m rag_chatbot" 2>/dev/null
lsof -ti:$PORT | xargs kill -9 2>/dev/null
sleep 1

echo "Starting RAG Chatbot on http://localhost:$PORT"
source venv/bin/activate
python -m rag_chatbot --host $HOST --port $PORT
