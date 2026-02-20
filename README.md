# Media Bot Stack

Real-time torrent automation system with:

- Tool 1: Crawler
- Tool 2: Queue Builder
- Tool 3: Agent Sync
- Tool 4: Real-time qBittorrent Worker

## Services

- media-bot (batch runner)
- media-bot-worker (real-time torrent worker)
- movie-agent

## Deployment

```bash
docker compose build
docker compose up -d
