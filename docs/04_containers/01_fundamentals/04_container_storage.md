---
level: foundational
estimated_time: 45 min
prerequisites:
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
  - 04_containers/01_fundamentals/02_union_filesystems.md
next_recommended:
  - 04_containers/01_fundamentals/03_container_vs_vm.md
tags: [containers, storage, volumes, bind-mounts, tmpfs, persistent-storage, stateful]
---

# Container Storage: Volumes, Mounts, and Persistent Data

**Learning Objectives:**
- Understand why container filesystem data is ephemeral
- Distinguish between named volumes, bind mounts, and tmpfs
- Choose the appropriate storage type for different use cases
- Implement persistent storage for stateful applications
- Recognize security implications of different mount types
- Apply best practices for container storage in production

---

## Introduction: The Ephemeral Problem

In [Union Filesystems](02_union_filesystems.md), we learned how container images use OverlayFS with **read-only base layers** and a **writable container layer**.

**But there's a problem:**

```
Container lifecycle:
1. docker run myapp
   └─ Creates writable layer for container changes

2. Application writes data:
   - Database creates /var/lib/postgresql/data/
   - Logs written to /var/log/app.log
   - User uploads saved to /uploads/

3. docker stop myapp
   └─ Container stops (data still exists)

4. docker rm myapp
   └─ Container deleted
   └─ ❌ ALL DATA IN WRITABLE LAYER IS GONE!
```

**The ephemeral nature of containers:**
- Container layer exists only while container exists
- `docker rm` deletes all data written to container filesystem
- Starting a new container creates a fresh, empty writable layer

**This is a problem for:**
- Databases (PostgreSQL, MySQL, MongoDB)
- Application state (sessions, caches)
- User-generated content (uploads, files)
- Logs and metrics
- Configuration that changes at runtime

**Solution:** Use storage that lives **outside the container lifecycle**.

---

## Part 1: Three Storage Types

Linux containers support three types of storage that persist beyond container deletion:

```
┌──────────────────────────────────────────────────────────────┐
│                    Container View                            │
│  /                                                           │
│  ├─ /app/           ← Image layers (OverlayFS)              │
│  ├─ /data/          ← Named volume (Docker-managed)         │
│  ├─ /config/        ← Bind mount (host directory)           │
│  └─ /tmp/           ← tmpfs (in-memory)                     │
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Image Layers    │  │ Named Volume │  │ Bind Mount       │
│ (OverlayFS)     │  │ (managed)    │  │ (host path)      │
│                 │  │              │  │                  │
│ /var/lib/docker/│  │ /var/lib/    │  │ /home/user/      │
│ overlay2/xyz/   │  │ docker/      │  │ app-config/      │
│                 │  │ volumes/abc/ │  │                  │
└─────────────────┘  └──────────────┘  └──────────────────┘
     Ephemeral          Persistent        Persistent
     (deleted with      (survives         (survives
      container)         container)        container)
```

---

### Type 1: Named Volumes (Docker-Managed)

**What:** Docker creates and manages directory on host, mounts into container.

**Storage location:** `/var/lib/docker/volumes/<volume-name>/`

**Example:**
```bash
# Create named volume
docker volume create pgdata

# Use in container
docker run -d \
  --name postgres \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16

# Volume persists after container deletion
docker rm -f postgres
docker volume ls
# DRIVER    VOLUME NAME
# local     pgdata        ← Still exists!

# Start new container with same data
docker run -d \
  --name postgres-new \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
# ✅ All database data preserved!
```

**Characteristics:**
- ✅ **Docker-managed** - Docker handles creation, lifecycle
- ✅ **Portable** - No host path dependencies
- ✅ **Survives container deletion** - Explicit deletion required
- ✅ **Shareable** - Multiple containers can mount same volume
- ✅ **Best practice for production** - Recommended for databases
- ⚠️ **Opaque location** - Data at `/var/lib/docker/volumes/`, harder to access directly

**When to use:**
- Production databases (PostgreSQL, MySQL, MongoDB)
- Application state that must persist
- Shared data between containers
- Any data you want to survive container recreation

---

### Type 2: Bind Mounts (Host Directories)

**What:** Mount a specific host directory or file into container.

**Storage location:** Arbitrary path on host (e.g., `/home/user/app-data/`)

**Example:**
```bash
# Mount host directory into container
docker run -d \
  --name nginx \
  -v /home/user/website:/usr/share/nginx/html:ro \
  nginx

# Changes on host immediately visible in container
echo "<h1>Hello</h1>" > /home/user/website/index.html
# ✅ Nginx serves updated content immediately!
```

**Characteristics:**
- ✅ **Direct host access** - Specify exact host path
- ✅ **Live updates** - Changes on host reflected immediately
- ✅ **Great for development** - Edit code on host, runs in container
- ⚠️ **Host-dependent** - Breaks if host path doesn't exist
- ⚠️ **Security risk** - Container can read/write host filesystem
- ⚠️ **Less portable** - Tied to specific host paths

**When to use:**
- Development (mount source code for live reload)
- Configuration files that change frequently
- Sharing specific host resources (Docker socket, system files)
- Debugging (mount host tools into container)

**Security note:** With write access, container can modify host files!

```bash
# ⚠️ DANGER: Container can modify host
docker run -v /etc:/host-etc busybox \
  sh -c "echo 'pwned' > /host-etc/passwd"
# This could break your host system!
```

---

### Type 3: tmpfs Mounts (In-Memory)

**What:** Mount temporary filesystem in RAM (not persisted to disk).

**Storage location:** Host memory (RAM)

**Example:**
```bash
# Mount tmpfs at /tmp (common pattern)
docker run -d \
  --name app \
  --tmpfs /tmp:rw,size=100m,mode=1777 \
  myapp

# Data written to /tmp lives in RAM
# Extremely fast, but limited by available memory
# Automatically cleared when container stops
```

**Characteristics:**
- ✅ **Very fast** - RAM speed (no disk I/O)
- ✅ **Secure** - Data never written to disk
- ✅ **Auto-cleanup** - Cleared on container stop
- ⚠️ **Limited by RAM** - Must specify size limit
- ⚠️ **Not persistent** - Data lost on stop/crash
- ⚠️ **Counts toward container memory limit**

**When to use:**
- Temporary files that don't need persistence
- Sensitive data (passwords, tokens) that shouldn't touch disk
- Build artifacts during compilation
- High-performance caching
- `/tmp` directories (Linux best practice)

**Example use cases:**
```bash
# Secure: Store secrets in memory only
docker run --tmpfs /secrets:ro,mode=0700 \
  myapp

# Performance: Fast temp storage for builds
docker run --tmpfs /tmp:size=1g \
  golang-build-container

# Security: Prevent temp file snooping
docker run --tmpfs /tmp --tmpfs /var/tmp \
  webapp
```

---

## Part 2: Comparison and Decision Matrix

### Feature Comparison

```
┌───────────────────┬─────────────┬─────────────┬─────────────┐
│ FEATURE           │ VOLUME      │ BIND MOUNT  │ TMPFS       │
├───────────────────┼─────────────┼─────────────┼─────────────┤
│ Managed by        │ Docker      │ User        │ Docker      │
│ Survives deletion │ Yes         │ Yes         │ No          │
│ Storage location  │ Docker dir  │ Host path   │ RAM         │
│ Portability       │ ✅ High     │ ⚠️ Low      │ ✅ High     │
│ Performance       │ Good        │ Good        │ Excellent   │
│ Security risk     │ Low         │ ⚠️ High     │ Low         │
│ Size limit        │ Disk space  │ Disk space  │ RAM         │
│ Multi-container   │ ✅ Yes      │ ✅ Yes      │ No          │
│ Backup easy?      │ Yes         │ Very easy   │ N/A         │
│ Best for          │ Production  │ Development │ Temp data   │
└───────────────────┴─────────────┴─────────────┴─────────────┘
```

### Decision Matrix

```
USE CASE                           → STORAGE TYPE
─────────────────────────────────────────────────────────────
Production database                → Named volume
Development source code            → Bind mount
Secrets/credentials                → tmpfs (+ secrets mgmt)
Logs (persistent)                  → Named volume
Logs (debugging only)              → Bind mount or tmpfs
User uploads                       → Named volume
Configuration (prod)               → Named volume
Configuration (dev)                → Bind mount
Build cache                        → tmpfs or named volume
Session data                       → Named volume or tmpfs
Shared data between containers     → Named volume
Docker socket (/var/run/docker.sock) → Bind mount
System debugging                   → Bind mount (read-only!)
```

---

## Part 3: Named Volumes in Detail

### Volume Lifecycle

**Create:**
```bash
# Explicit creation
docker volume create mydata

# Or automatic on first use
docker run -v mydata:/data busybox
# Volume "mydata" created if doesn't exist
```

**Inspect:**
```bash
# List volumes
docker volume ls

# Detailed info
docker volume inspect mydata
# [
#   {
#     "CreatedAt": "2024-01-15T10:30:00Z",
#     "Driver": "local",
#     "Mountpoint": "/var/lib/docker/volumes/mydata/_data",
#     "Name": "mydata",
#     "Options": {},
#     "Scope": "local"
#   }
# ]
```

**Access data:**
```bash
# Data stored at Mountpoint
sudo ls -la /var/lib/docker/volumes/mydata/_data/

# Or access via temporary container
docker run --rm -v mydata:/data busybox ls /data
```

**Backup:**
```bash
# Create tarball of volume contents
docker run --rm \
  -v mydata:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/mydata-backup.tar.gz /data

# Restore from backup
docker run --rm \
  -v mydata:/data \
  -v $(pwd):/backup \
  busybox tar xzf /backup/mydata-backup.tar.gz -C /
```

**Delete:**
```bash
# Remove unused volumes
docker volume prune

# Remove specific volume
docker volume rm mydata
# Error: volume in use (if container using it)

# Force remove (stop containers first)
docker rm -f $(docker ps -aq)
docker volume rm mydata
```

---

### Sharing Volumes Between Containers

**Scenario:** App container generates data, backup container reads it.

```bash
# Create shared volume
docker volume create shared-data

# Container 1: Writer
docker run -d \
  --name app \
  -v shared-data:/app/data \
  myapp

# Container 2: Reader
docker run -d \
  --name backup \
  -v shared-data:/backup-source:ro \
  backup-tool
```

**Common patterns:**

1. **Application + Sidecar Logger**
```bash
# App writes logs
docker run -d \
  --name app \
  -v logs:/var/log/app \
  myapp

# Sidecar ships logs
docker run -d \
  --name log-shipper \
  -v logs:/logs:ro \
  fluentd
```

2. **Multi-Stage Processing**
```bash
# Stage 1: Generate data
docker run --rm \
  -v pipeline:/output \
  data-generator

# Stage 2: Process data
docker run --rm \
  -v pipeline:/input:ro \
  data-processor
```

---

### Volume Drivers and Plugins

**Local driver (default):**
- Stores data on Docker host
- Good for single-host deployments

**Network storage drivers:**
```bash
# NFS volume
docker volume create \
  --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw \
  --opt device=:/shared \
  nfs-volume

# AWS EBS (requires plugin)
docker volume create \
  --driver rexray/ebs \
  --opt size=100 \
  aws-ebs-volume

# GlusterFS
docker volume create \
  --driver glusterfs \
  gluster-volume
```

**When to use:**
- Multi-host container orchestration (Kubernetes, Swarm)
- Shared storage across cluster
- Cloud-native storage (EBS, Azure Disk)
- High-availability databases

---

## Part 4: Bind Mounts in Detail

### Syntax and Options

**Docker CLI:**
```bash
# Basic bind mount
docker run -v /host/path:/container/path image

# Read-only mount
docker run -v /host/path:/container/path:ro image

# With specific bind options
docker run --mount type=bind,source=/host/path,target=/container/path,readonly image
```

**Docker Compose:**
```yaml
services:
  app:
    image: myapp
    volumes:
      # Short syntax
      - /host/path:/container/path

      # Long syntax (more control)
      - type: bind
        source: /host/path
        target: /container/path
        read_only: true
```

---

### Development Workflow Example

**Problem:** Want to edit code on host, see changes in container immediately.

```bash
# Project structure
~/my-app/
├── app.py
├── requirements.txt
└── Dockerfile

# Mount source code into container
docker run -it --rm \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  python app.py

# Edit app.py on host
vim app.py

# Restart container (or use auto-reload)
# Changes immediately visible!
```

**With Docker Compose:**
```yaml
version: '3.8'
services:
  web:
    build: .
    volumes:
      - ./app:/app        # Bind mount source code
      - /app/node_modules # Anonymous volume for deps
    environment:
      - NODE_ENV=development
    command: npm run dev  # Auto-reload on changes
```

---

### Security Considerations

**Bind mounts can expose host filesystem:**

```bash
# ⚠️ DANGER: Full filesystem access
docker run -v /:/host busybox

# Inside container:
ls /host/etc/passwd  # Can read
echo "bad" > /host/etc/passwd  # Can write!
```

**Best practices:**

1. **Use read-only when possible:**
```bash
docker run -v /host/config:/config:ro myapp
```

2. **Limit scope:**
```bash
# ❌ BAD: Mount entire home directory
docker run -v ~:/home ubuntu

# ✅ GOOD: Mount only what's needed
docker run -v ~/project/config:/config ubuntu
```

3. **Avoid sensitive directories:**
```bash
# ❌ NEVER MOUNT THESE (unless you know what you're doing):
-v /:/host
-v /etc:/etc
-v /var/run/docker.sock:/var/run/docker.sock
-v ~/.ssh:/root/.ssh
```

4. **Use user namespaces:**
```bash
# Map container root to unprivileged user on host
docker run --userns-remap=default \
  -v /host/data:/data \
  myapp
```

**Docker socket bind mount:**
```bash
# Common pattern: Docker-in-Docker
docker run -v /var/run/docker.sock:/var/run/docker.sock docker

# ⚠️ Security implication:
# Container can control Docker daemon = root on host!
# Only do this for trusted containers (CI/CD, management tools)
```

---

## Part 5: tmpfs Mounts in Detail

### Syntax and Options

```bash
# Basic tmpfs
docker run --tmpfs /tmp myapp

# With size limit (required for production!)
docker run --tmpfs /tmp:size=100m myapp

# With permissions
docker run --tmpfs /tmp:rw,size=100m,mode=1777 myapp

# Multiple tmpfs mounts
docker run \
  --tmpfs /tmp:size=100m \
  --tmpfs /var/cache:size=50m \
  myapp
```

**Docker Compose:**
```yaml
services:
  app:
    image: myapp
    tmpfs:
      - /tmp
      - /var/cache
    # Or with options:
    tmpfs:
      - type: tmpfs
        target: /tmp
        tmpfs:
          size: 100000000  # 100MB in bytes
```

---

### Common Use Cases

#### 1. Secure Credential Handling

**Problem:** Passwords/tokens in environment variables are visible in `docker inspect`.

**Solution:** Pass via tmpfs, read from file.

```bash
# Create secret file in tmpfs
docker run -d \
  --name app \
  --tmpfs /secrets:mode=0700 \
  myapp

# Write secret to tmpfs (not persistent)
docker exec app sh -c 'echo "secret_token" > /secrets/api_key'

# App reads from /secrets/api_key
# ✅ Never written to disk
# ✅ Auto-deleted on container stop
```

Better: Use Docker secrets (Swarm) or Kubernetes secrets.

#### 2. High-Performance Builds

```bash
# Fast build cache in RAM
docker run --rm \
  -v $(pwd):/src \
  --tmpfs /tmp:size=2g \
  golang:1.21 \
  sh -c "cd /src && GOTMPDIR=/tmp go build"

# 2-3x faster than disk-based /tmp
```

#### 3. Security-Sensitive Applications

```bash
# Financial application: No temp data on disk
docker run -d \
  --tmpfs /tmp \
  --tmpfs /var/tmp \
  --tmpfs /var/cache \
  --read-only \
  financial-app

# ✅ No persistent temp files
# ✅ Reduced forensic footprint
```

---

### Performance and Sizing

**Benchmarking tmpfs vs disk:**
```bash
# Write to tmpfs
docker run --rm --tmpfs /tmp busybox \
  sh -c "dd if=/dev/zero of=/tmp/test bs=1M count=100"
# 100 MB in 0.1 seconds (1 GB/s)

# Write to disk
docker run --rm -v $(pwd):/data busybox \
  sh -c "dd if=/dev/zero of=/data/test bs=1M count=100"
# 100 MB in 0.8 seconds (125 MB/s)

# 8x faster!
```

**Size considerations:**
```bash
# ❌ BAD: No size limit
docker run --tmpfs /tmp myapp
# Runaway process can exhaust memory!

# ✅ GOOD: Explicit size limit
docker run --tmpfs /tmp:size=100m myapp

# Check tmpfs usage
docker exec myapp df -h /tmp
# Filesystem      Size  Used Avail Use% Mounted on
# tmpfs           100M   10M   90M  10% /tmp
```

---

## Part 6: Rootless Containers and Storage

### What is Rootless?

**Traditional Docker:** Runs as root, creates containers as root.

**Rootless Docker:** Runs as unprivileged user, containers run as that user.

**Storage implications:**

```
Traditional Docker:
  /var/lib/docker/volumes/mydata/
  └─ owned by root:root

Rootless Docker:
  ~/.local/share/docker/volumes/mydata/
  └─ owned by user:user
```

---

### fuse-overlayfs

**Problem:** OverlayFS requires kernel privileges.

**Solution:** `fuse-overlayfs` - userspace implementation.

```bash
# Check storage driver
docker info | grep "Storage Driver"
# Storage Driver: fuse-overlayfs  ← Rootless!
```

**Performance:**
- Slightly slower than kernel OverlayFS (userspace overhead)
- Still much faster than old VFS driver
- Acceptable for most workloads

**When you need this:**
- Running Docker without root
- Shared systems where users can't get root
- Security-conscious environments
- Kubernetes user namespaces

---

## Part 7: Best Practices

### Production Guidelines

**1. Use named volumes for stateful data:**
```yaml
# ✅ GOOD
services:
  postgres:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
    driver: local
```

**2. Never rely on container layer for important data:**
```bash
# ❌ BAD: Data lost on container deletion
docker run postgres  # No volume!

# ✅ GOOD: Data persists
docker run -v pgdata:/var/lib/postgresql/data postgres
```

**3. Separate code and data:**
```dockerfile
# ❌ BAD: Code and data mixed
VOLUME /app

# ✅ GOOD: Only data volumes
VOLUME /app/data
VOLUME /app/logs
```

**4. Use read-only mounts when possible:**
```bash
# Config files: read-only
docker run -v /config:/config:ro myapp

# Application code in production: read-only
docker run -v /app:/app:ro myapp
```

**5. Set resource limits on tmpfs:**
```bash
# ✅ Always specify size
docker run --tmpfs /tmp:size=100m myapp
```

---

### Backup Strategies

**Named volumes:**
```bash
# Automated backup script
#!/bin/bash
VOLUMES=$(docker volume ls -q)
for vol in $VOLUMES; do
  docker run --rm \
    -v $vol:/data \
    -v $(pwd)/backups:/backup \
    busybox tar czf /backup/${vol}_$(date +%Y%m%d).tar.gz /data
done
```

**Docker Compose backup:**
```yaml
services:
  backup:
    image: busybox
    volumes:
      - appdata:/source:ro
      - ./backups:/backup
    command: tar czf /backup/backup-$(date +%Y%m%d).tar.gz /source
```

---

### Development vs Production

```
Development:
✅ Bind mounts for live code reload
✅ Mount Docker socket (for Docker-in-Docker dev)
✅ Less strict security

Production:
✅ Named volumes only
✅ Read-only root filesystem where possible
✅ Minimal bind mounts (configuration only)
❌ No Docker socket mounts
✅ Explicit resource limits
```

---

## Quick Reference

### Volume Commands

```bash
# List volumes
docker volume ls

# Create volume
docker volume create mydata

# Inspect volume
docker volume inspect mydata

# Remove volume
docker volume rm mydata

# Remove all unused volumes
docker volume prune

# Show volume usage
docker system df -v
```

### Mount Syntax Comparison

```bash
# Named volume
-v mydata:/data
--mount type=volume,source=mydata,target=/data

# Bind mount
-v /host/path:/container/path
--mount type=bind,source=/host/path,target=/container/path

# tmpfs
--tmpfs /tmp
--mount type=tmpfs,target=/tmp,tmpfs-size=100000000

# Read-only
-v mydata:/data:ro
--mount type=volume,source=mydata,target=/data,readonly
```

### Decision Tree

```
Need persistent storage?
  ├─ YES → Need to access from host easily?
  │         ├─ YES → Bind mount
  │         └─ NO → Named volume (preferred)
  │
  └─ NO → Need high performance temp storage?
            ├─ YES → tmpfs
            └─ NO → Use container layer (ephemeral is OK)
```

---

## What You've Learned

✅ **Container layer is ephemeral** - Deleted with container
✅ **Named volumes** - Docker-managed, portable, best for production databases
✅ **Bind mounts** - Host directories, great for development, security risks
✅ **tmpfs** - In-memory storage, fast and secure for temporary data
✅ **Volume lifecycle** - Create, use, backup, delete
✅ **Sharing volumes** - Multiple containers accessing same data
✅ **Security practices** - Read-only mounts, limiting scope, avoiding sensitive paths
✅ **Production patterns** - Stateful applications, backups, resource limits

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[Docker Volumes Documentation](https://docs.docker.com/storage/volumes/)** - Official guide to Docker volume management
- **[Manage data in Docker](https://docs.docker.com/storage/)** - Comprehensive storage overview including volumes, bind mounts, and tmpfs
- **[Docker Storage Tutorial](https://www.youtube.com/watch?v=VOK06Q4QqvE)** - Visual walkthrough of different storage types

---

## Next Steps

**Continue learning:**
→ [Container vs VM Comparison](03_container_vs_vm.md) - Understanding when to use containers vs VMs
→ [Container Runtimes](../02_runtimes/01_runtime_landscape.md) - How runtimes manage storage

**Related topics:**
→ [Union Filesystems](02_union_filesystems.md) - Understanding image layers
→ [cgroups and Namespaces](01_cgroups_namespaces.md) - Container isolation primitives

**Practical exercises:**
1. Create a PostgreSQL container with persistent volume
2. Set up development workflow with bind mounts
3. Benchmark tmpfs vs disk performance
4. Implement automated volume backups
