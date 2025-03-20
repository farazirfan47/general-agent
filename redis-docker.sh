#!/bin/bash

# Colors for prettier output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

case "$1" in
  start)
    echo -e "${GREEN}Starting Redis container...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Redis is running on localhost:6379${NC}"
    ;;
    
  stop)
    echo -e "${YELLOW}Stopping Redis container...${NC}"
    docker-compose down
    echo -e "${GREEN}Redis container stopped${NC}"
    ;;
    
  restart)
    echo -e "${YELLOW}Restarting Redis container...${NC}"
    docker-compose down
    docker-compose up -d
    echo -e "${GREEN}Redis is running on localhost:6379${NC}"
    ;;
    
  clean)
    echo -e "${RED}Stopping Redis and removing data volumes...${NC}"
    docker-compose down -v
    echo -e "${GREEN}Redis container and data volumes removed${NC}"
    ;;
    
  cli)
    echo -e "${GREEN}Connecting to Redis CLI...${NC}"
    docker exec -it redis redis-cli
    ;;
    
  logs)
    echo -e "${GREEN}Showing Redis logs...${NC}"
    docker-compose logs -f
    ;;
    
  status)
    echo -e "${GREEN}Redis container status:${NC}"
    docker ps -f name=redis
    ;;
    
  *)
    echo -e "Usage: $0 {start|stop|restart|clean|cli|logs|status}"
    echo
    echo -e "  ${GREEN}start${NC}   - Start Redis container"
    echo -e "  ${YELLOW}stop${NC}    - Stop Redis container (keeps data)"
    echo -e "  ${YELLOW}restart${NC} - Restart Redis container"
    echo -e "  ${RED}clean${NC}   - Stop Redis and remove data volumes"
    echo -e "  ${GREEN}cli${NC}     - Connect to Redis CLI"
    echo -e "  ${GREEN}logs${NC}    - Show Redis container logs"
    echo -e "  ${GREEN}status${NC}  - Show Redis container status"
    exit 1
    ;;
esac

exit 0 