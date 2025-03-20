# Chatbot with Real-time Updates

A full-stack chatbot application featuring a FastAPI backend with agent-based architecture and a Next.js frontend with real-time updates.

## Project Overview

This project consists of:
1. A FastAPI backend that implements an agent-based conversational AI
2. A Next.js frontend that provides a real-time chat interface
3. WebSocket communication for streaming updates during agent operations

## Features

- Real-time status updates during chat processing:
  - Thinking states
  - Plan generation and display
  - Step-by-step execution tracking
  - Tool usage indicators (web search, browser automation)
  - Computer Use Agent (CUA) real-time browser actions
- Session persistence with Redis
- Shareable conversation links
- Responsive UI with dark mode support

## Backend Architecture

The backend is structured as follows:

- `app/agents/agent_loop.py`: Core agent orchestration logic
- `app/agents/cua/`: Computer Use Agent for browser automation
- `app/memory/redis_memory.py`: Session persistence with Redis
- `api.py`: FastAPI endpoints and WebSocket handlers

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 18+
- Redis server (for session storage)

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configurations
```

3. Start the FastAPI server:
```bash
uvicorn api:app --reload
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the Next.js development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Deployment

For production deployment:

1. Build the frontend:
```bash
cd frontend
npm run build
```

2. Use Gunicorn with Uvicorn workers for the backend:
```bash
gunicorn -k uvicorn.workers.UvicornWorker api:app
```

3. Set up Redis for production (see redis-docker.sh)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for the GPT models
- Computer Use Agent (CUA) for browser automation capabilities

# general-ai

## Docker Setup with Redis

This project includes Docker configuration to run Redis in a container.

### Using the Redis Management Script

For your convenience, a management script is provided to simplify Redis Docker operations:

```bash
# Make it executable (first time only)
chmod +x redis-docker.sh

# Start Redis
./redis-docker.sh start

# Check Redis status
./redis-docker.sh status

# Connect to Redis CLI
./redis-docker.sh cli

# View Redis logs
./redis-docker.sh logs

# Stop Redis (preserves data)
./redis-docker.sh stop

# Stop Redis and remove data volumes
./redis-docker.sh clean
```

### Running Redis with Docker Compose

If you prefer to use Docker Compose commands directly:

1. Start Redis:
   ```bash
   docker-compose up -d
   ```

2. The Redis instance will be available at:
   - Host: `localhost` (from your local machine)
   - Port: `6379`
   - URL: `redis://localhost:6379/0`

3. To stop Redis:
   ```bash
   docker-compose down
   ```

4. To stop and remove the Redis data volume:
   ```bash
   docker-compose down -v
   ```

### Running Redis with Docker Run

If you prefer using the `docker run` command directly:

```bash
docker run -d --name redis -p 6379:6379 redis:7.2-alpine redis-server --appendonly yes
```

This will start a Redis container with data persistence enabled and expose port 6379.

To stop and remove this container:
```bash
docker stop redis && docker rm redis
```

### Redis CLI Access

To access the Redis CLI in the container:

```bash
docker exec -it redis redis-cli
```

### Configuration

The application connects to Redis using the `REDIS_URL` environment variable configured in the `.env` file.

For local development with Docker Redis, use:
```
REDIS_URL=redis://localhost:6379/0
```
