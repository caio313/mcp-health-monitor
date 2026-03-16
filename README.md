# MCP Health Server

Integrity monitor for MCP server ecosystems.
Any AI agent can use these tools to know
the real state of its ecosystem in real time.

---

## The problem it solves

AI agents fail silently when their tools fail.

```
Agent calls tool → tool responds slowly or incorrectly → agent makes wrong decision
                                                        → nobody knows why
```

MCP Health Server gives any agent full visibility
into the state of its ecosystem — before things break.

---

## Available tools

### check_health
Verifies the state of an MCP server in real time.
Detects latency, availability, and exposed tools.
Compatible with streamable-http and SSE.

```json
check_health("https://my-server.com/mcp")

→ {
    "status": "healthy",
    "latency_ms": 226,
    "tools_available": ["ping", "get_time", "get_random_metric"],
    "uptime_24h": 99.5
  }
```

---

### get_summary
State of multiple MCP servers in a single call.
Runs all checks in parallel.

```json
get_summary([
  "https://server-a.com/mcp",
  "https://server-b.com/mcp"
])

→ {
    "total": 2,
    "healthy": 1,
    "degraded": 1,
    "unhealthy": 0,
    "ecosystem_health_score": 50.0
  }
```

---

### check_drift
Detects whether a server's behavior has changed
compared to its historical baseline.

Finds gradual degradation that traditional
uptime alerts never catch.

```json
check_drift("https://my-server.com/mcp", baseline_days=7)

→ {
    "drift_detected": false,
    "baseline_avg_latency_ms": 93.7,
    "current_latency_ms": 93.9,
    "overall_severity": "NONE"
  }
```

---

### calculate_blast_radius
Calculates the cascade impact if a specific service goes down.
Shows which other services are affected directly
and indirectly.

```json
calculate_blast_radius(
  "auth-mcp",
  ["data-mcp", "trading-mcp", "report-mcp"]
)

→ {
    "directly_affected": ["data-mcp", "trading-mcp"],
    "cascade_affected": ["report-mcp"],
    "ecosystem_impact_percent": 100.0,
    "severity": "CRITICAL"
  }
```

---

## Connect to your agent

```json
{
  "mcpServers": {
    "mcp-health": {
      "url": "https://mcp-health-server.onrender.com/mcp"
    }
  }
}
```

---

## Local setup

```bash
# 1. Clone the repository
git clone https://github.com/caio313/mcp-health-server
cd mcp-health-server

# 2. Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL

# 4. Initialize the database
python -c "import asyncio; from core.db import init_db; asyncio.run(init_db())"

# 5. Run the server
python main.py
# Available at: http://localhost:8000/mcp
```

---

## Protocol compatibility

Supports both MCP transports with no additional configuration:
- `streamable-http` — current standard
- `SSE` — Server-Sent Events

---

## Skill for AI agents

Includes an optimized SKILL.md for Claude and OpenCode
that orchestrates tools automatically based on context.

To activate it in OpenCode, copy SKILL.md to:
`~/.config/opencode/skills/mcp-health.md`

---

## Pricing

| Plan | Price | Limit |
|---|---|---|
| **Free** | $0 | 100 checks/day |
| **Builder** | $19/mo | 10,000 checks/day |
| **Team** | $49/mo | Unlimited + email alerts |
