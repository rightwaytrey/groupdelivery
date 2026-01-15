# Debugging with Claude: Tight Iteration Loop

This document describes how Claude can access the production server directly to debug issues with a much tighter feedback loop.

## Overview

Instead of the traditional debugging cycle where you report issues → Claude suggests fixes → you deploy and test → repeat, Claude can now:

1. SSH into the server
2. Check logs directly
3. Identify the root cause
4. Fix the code locally
5. Deploy the fix via git
6. Verify the fix by checking logs and testing endpoints
7. Report back with confirmation

## Prerequisites

### SSH Configuration

The local machine must have SSH access to the production server configured in `~/.ssh/config`:

```ssh-config
Host more
    Hostname 172.236.114.77
    User rwt
```

Key-based authentication must be set up (no password prompts).

### Server Setup

- **Server location**: `morefood.duckdns.org` (172.236.114.77)
- **Project directory**: `/home/rwt/groupdelivery`
- **Deployment method**: Git-based (push to GitHub, pull on server)
- **Container orchestration**: Docker Compose with `docker-compose.prod.yml`

## What Claude CAN Do

### 1. View Logs in Real-Time

```bash
# View recent backend logs
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml logs backend --tail 100"

# Follow logs in real-time (with timeout to avoid hanging)
ssh more "cd /home/rwt/groupdelivery && timeout 60 docker compose -f docker-compose.prod.yml logs -f backend"

# Filter logs for specific patterns
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml logs backend --tail 200 | grep -i error"

# Check all services
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml logs --tail 50"
```

### 2. Check Container Status

```bash
# Check if containers are running and healthy
ssh more "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Check specific container
ssh more "docker inspect groupdelivery-backend --format '{{.State.Status}}'"
```

### 3. Test API Endpoints

```bash
# Test internal endpoint
ssh more "curl -s http://localhost:8000/api/health"

# Test public endpoint
curl -s https://morefood.duckdns.org/api/health

# Test with authentication
curl -s -H "Authorization: Bearer $TOKEN" https://morefood.duckdns.org/api/some-endpoint
```

### 4. Restart Services

```bash
# Restart backend container
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml restart backend"

# Restart all services
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml restart"
```

### 5. Deploy Code Changes

Full deployment cycle:

```bash
# 1. Make changes locally (edit files)

# 2. Commit changes
git add <files>
git commit -m "Fix: description of fix"

# 3. Push to GitHub
git push

# 4. Pull and rebuild on server
ssh more "cd /home/rwt/groupdelivery && git pull origin master && docker compose -f docker-compose.prod.yml up -d --build backend"

# 5. Verify deployment
ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml logs backend --tail 20"
```

### 6. Access Database (SQLite)

```bash
# List tables
ssh more 'docker exec groupdelivery-backend python3 -c "import sqlite3; conn = sqlite3.connect(\"/app/data/delivery.db\"); cursor = conn.cursor(); cursor.execute(\"SELECT name FROM sqlite_master WHERE type=\\\"table\\\"\"); print([row[0] for row in cursor.fetchall()]); conn.close()"'

# Query data
ssh more 'docker exec groupdelivery-backend python3 << "PYEOF"
import sqlite3
conn = sqlite3.connect("/app/data/delivery.db")
cursor = conn.cursor()
cursor.execute("SELECT id, name, home_address FROM drivers")
for row in cursor.fetchall():
    print(row)
conn.close()
PYEOF
'
```

## Limitations

### What Claude CANNOT Do

1. **Visual Testing**: Cannot see the UI or browser console errors
2. **Continuous Monitoring**: Works in request/response cycles, not continuous observation
3. **Interactive Prompts**: SSH commands requiring keyboard input (y/n confirmations) won't work
4. **Long-Running Commands**: Commands timeout after ~2 minutes by default
5. **Browser Testing**: Cannot interact with JavaScript or test client-side behavior
6. **Performance Profiling**: Cannot easily test race conditions or timing-dependent bugs

### Workarounds

- **For UI issues**: Test API endpoints directly, check browser console in person
- **For long builds**: Use background jobs or check status in follow-up
- **For interactive prompts**: Use `-y` flags or non-interactive mode
- **For continuous monitoring**: Grab log snapshots at intervals
- **For large log volumes**: Use grep to filter for specific errors

## Example Debugging Session

### Scenario: Route optimization crashes with segfault

**Traditional Approach** (slow):
1. User: "Route optimization is crashing"
2. Claude: "Can you check the logs?"
3. User: *checks logs* "It says segfault"
4. Claude: "Try this fix..." *suggests code*
5. User: *deploys and tests* "Still broken, different error"
6. Repeat...

**New Approach** (fast):
1. User: "Route optimization is crashing"
2. Claude: *SSHs to server, checks logs, sees segfault*
3. Claude: *Identifies OR-Tools per-vehicle endpoints causing crash*
4. Claude: *Implements alternative approach using mandatory stops*
5. Claude: *Commits, pushes, deploys to server*
6. Claude: *Checks logs, confirms fix works*
7. Claude: "Fixed and verified - segfault resolved by using mandatory stops instead of per-vehicle endpoints"

**Time saved**: From potentially hours/days to minutes.

## Best Practices

### When to Use This Workflow

✅ **Use for:**
- Backend crashes or errors
- API endpoint failures
- Database issues
- Route optimization problems
- Container health issues
- Configuration errors

❌ **Don't use for:**
- UI/UX issues (needs visual inspection)
- Frontend JavaScript errors (use browser console)
- User experience testing
- Performance optimization (needs profiling tools)

### Debugging Tips

1. **Start with logs**: Always check logs first to understand what's happening
2. **Reproduce the issue**: Have the user trigger the problem while watching logs
3. **Test incrementally**: Make small changes, deploy, verify immediately
4. **Add debug logging**: Add print/logger statements to track execution flow
5. **Verify after deployment**: Always check logs and test endpoints after deploying

### Adding Debug Logging

Example of adding helpful debug output:

```python
# Before making changes
logger.info(f"Processing request with params: {params}")
print(f"Debug: Processing request", flush=True)

# After OR-Tools operation
logger.info(f"VRP solution: {solution['num_routes']} routes found")
print(f"Routes: {[route['stops'] for route in solution['routes']]}", flush=True)
```

The `flush=True` ensures output appears immediately in docker logs.

## Common Commands Reference

```bash
# Quick health check
ssh more "docker ps && curl -s http://localhost:8000/api/health"

# Full deployment
git push && ssh more "cd /home/rwt/groupdelivery && git pull origin master && docker compose -f docker-compose.prod.yml up -d --build backend"

# Watch logs for specific pattern
ssh more "cd /home/rwt/groupdelivery && timeout 120 docker compose -f docker-compose.prod.yml logs -f backend 2>&1 | grep -A 5 -B 5 'ERROR\|Exception\|Traceback'"

# Check container resource usage
ssh more "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'"

# View environment variables
ssh more "docker exec groupdelivery-backend env | grep -E 'DEBUG|DATABASE|SECRET'"
```

## Security Considerations

- Claude has SSH access but cannot run sudo commands
- All operations are logged
- Only read access to production data via Python/SQL queries
- Can restart containers and rebuild services
- Cannot modify system-level configuration
- Cannot force push to git or modify git history

## Troubleshooting the Troubleshooting

If SSH access stops working:

1. **Check SSH config**: `cat ~/.ssh/config | grep -A 3 "Host more"`
2. **Test connection**: `ssh more "echo 'Connection works'"`
3. **Check SSH keys**: `ssh-add -l`
4. **Verify server is up**: `ping 172.236.114.77`
5. **Check Docker on server**: `ssh more "docker ps"`

If deployment fails:

1. **Check git status**: `git status`
2. **Verify remote**: `git remote -v`
3. **Check server git state**: `ssh more "cd /home/rwt/groupdelivery && git status"`
4. **Check for merge conflicts**: `ssh more "cd /home/rwt/groupdelivery && git log -1"`
5. **Check Docker build logs**: `ssh more "cd /home/rwt/groupdelivery && docker compose -f docker-compose.prod.yml logs --tail 100"`

## Future Improvements

Potential enhancements to the debugging workflow:

1. **Structured logging**: Use JSON logs with request IDs for easier searching
2. **Log aggregation**: Set up centralized logging (ELK, Loki, etc.)
3. **Monitoring**: Add Prometheus/Grafana for real-time metrics
4. **Automated testing**: Run smoke tests after deployment
5. **Rollback mechanism**: Quick rollback if deployment causes issues
6. **Staging environment**: Test changes in staging before production

---

**Document Version**: 1.0
**Last Updated**: 2026-01-15
**Effective Since**: Discovery of home endpoint bug fix workflow
