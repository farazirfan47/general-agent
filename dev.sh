#!/bin/bash

# Start frontend server
cd frontend && npm run dev &
FRONTEND_PID=$!

# Start backend server (uncomment if needed)
# cd backend && python -m uvicorn main:app --reload &
# BACKEND_PID=$!

# Handle exit signals
trap "kill $FRONTEND_PID; exit" INT TERM EXIT

# Keep script running
wait 