
#!/bin/bash

# Kill existing instance if running on port 7860
PID=$(lsof -ti :7860 2>/dev/null)
if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null && echo "Stopped existing server (PID: $PID)" && sleep 2
fi

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source ./venv/bin/activate

# Define the usage function
usage() {
    echo "Usage: $0 [--ngrok]"
    exit 1
}

# Initialize NGROK variable
NGROK=""

# Loop through command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ngrok)
            NGROK=true
            shift
            ;;
        *)
            usage
            ;;
    esac
done

# Run the Python app
if [[ -n $NGROK ]]; then
    python -m rag_chatbot --host localhost --port 7860 & ngrok http 7860
else
    python -m rag_chatbot --host localhost --port 7860
fi