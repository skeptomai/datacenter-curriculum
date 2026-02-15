---
level: foundational
estimated_time: 40 min
prerequisites:
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
next_recommended:
  - 04_containers/01_fundamentals/03_container_vs_vm.md
tags: [containers, filesystem, overlayfs, images, layers, copy-on-write]
---

# Union Filesystems and Container Images

**Learning Objectives:**
- Understand how container images are built from layers
- Explain copy-on-write (CoW) filesystems
- Describe how OverlayFS combines multiple directories
- Recognize the performance and storage implications
- Apply layering concepts to optimize container images

---

## Introduction: The Image Problem

You have a container that needs:
- Ubuntu base system (~200 MB)
- Python runtime (~100 MB)
- Your application code (~10 MB)

**Naive approach:**
```
Container 1: Ubuntu + Python + App1 = 310 MB
Container 2: Ubuntu + Python + App2 = 310 MB
Container 3: Ubuntu + Python + App3 = 310 MB

Total storage: 930 MB  ← Wasteful! Ubuntu+Python duplicated 3x
```

**Smart approach (layering):**
```
Layer 1: Ubuntu (200 MB)         ← Shared!
Layer 2: Python (100 MB)         ← Shared!
Layer 3: App1   (10 MB)          ← Unique
Layer 4: App2   (10 MB)          ← Unique
Layer 5: App3   (10 MB)          ← Unique

Total storage: 330 MB  ← 3x more efficient!
```

**The question:** How do you make it **look like** each container has its own complete filesystem, while actually **sharing** the common parts?

**Answer:** Union filesystems!

---

## Part 1: Copy-on-Write Filesystems

### What is Copy-on-Write (CoW)?

**Traditional file copy:**
```
Original file: "Hello World" (1 MB on disk)
Copy file:     "Hello World" (1 MB on disk)
Total: 2 MB written
```

**Copy-on-Write:**
```
Original file: "Hello World" (1 MB on disk)
CoW "copy":    → pointer to original  (0 MB!)
Total: 1 MB (until you modify the copy)

When you modify the copy:
 ↓
Write happens now:
Original file: "Hello World" (1 MB)
Modified copy: "Hello World!" (1 MB)  ← Only now does it take space
Total: 2 MB
```

**Key principle:** Don't duplicate data until it changes.

### Why CoW Matters for Containers

**Scenario:** 10 containers from the same base image

**Without CoW:**
```
Container 1: Ubuntu base (200 MB)
Container 2: Ubuntu base (200 MB)  ← Duplicate!
...
Container 10: Ubuntu base (200 MB) ← Duplicate!
Total: 2 GB
```

**With CoW:**
```
Ubuntu base layer (200 MB) ← Stored once
Container 1: → points to base + unique changes
Container 2: → points to base + unique changes
...
Container 10: → points to base + unique changes
Total: 200 MB + (unique changes only)
```

---

## Part 2: Union Filesystems Explained

### What is a Union Filesystem?

A union filesystem **combines multiple directories** into a single view, where:
- Lower directories (read-only) provide base content
- Upper directory (read-write) captures changes
- Merged view combines both

**Visual:**
```
┌─────────────────────────────────────────────────────┐
│ User sees: Merged View                              │
│ /                                                   │
│ ├─ /bin/bash        ← from lower (read-only)       │
│ ├─ /etc/config      ← from upper (modified!)       │
│ ├─ /app/mycode.py   ← from upper (new file!)       │
│ └─ /lib/library.so  ← from lower (read-only)       │
└─────────────────────────────────────────────────────┘
         ↑ Union FS combines these ↑
┌──────────────────────┐  ┌──────────────────────────┐
│ Lower (read-only)    │  │ Upper (read-write)       │
│ /bin/bash            │  │ /etc/config (modified)   │
│ /lib/library.so      │  │ /app/mycode.py (new)     │
│ /etc/config (orig)   │  │                          │
└──────────────────────┘  └──────────────────────────┘
```

**Operations:**
- **Read**: Lower layers provide data (if not in upper)
- **Write**: Goes to upper layer only
- **Modify**: File copied from lower to upper (CoW!), then modified
- **Delete**: Whiteout file created in upper (hides lower file)

---

## Part 3: OverlayFS - The Modern Standard

### What is OverlayFS?

**OverlayFS** is the current standard union filesystem in Linux kernel (since 3.18).

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│ Merged directory (what container sees)              │
│ /var/lib/docker/overlay2/abc123/merged/             │
└─────────────────┬───────────────────────────────────┘
                  │ OverlayFS combines:
    ┌─────────────┴─────────────┐
    │                           │
┌───▼─────────────┐  ┌──────────▼──────────┐
│ Lower dirs      │  │ Upper dir + Work    │
│ (read-only)     │  │ (read-write)        │
│                 │  │                     │
│ Layer 1: Ubuntu │  │ Container changes   │
│ Layer 2: Python │  │ /upper/             │
│ Layer 3: Libs   │  │ /work/ (temp)       │
└─────────────────┘  └─────────────────────┘
```

**Three directories:**
1. **lower**: Read-only base layers (stacked)
2. **upper**: Read-write changes specific to this container
3. **work**: Temporary directory used by OverlayFS internals
4. **merged**: The combined view (what container sees)

### OverlayFS Example

**Setup:**
```bash
# Create directories
mkdir -p /tmp/overlay-demo/{lower,upper,work,merged}

# Lower layer (base Ubuntu files)
echo "Original /etc/hosts" > /tmp/overlay-demo/lower/hosts

# Mount OverlayFS
mount -t overlay overlay \
  -o lowerdir=/tmp/overlay-demo/lower,\
     upperdir=/tmp/overlay-demo/upper,\
     workdir=/tmp/overlay-demo/work \
  /tmp/overlay-demo/merged
```

**Now:**
```bash
# Container sees merged view
$ cat /tmp/overlay-demo/merged/hosts
Original /etc/hosts

# Modify file (triggers CoW)
$ echo "127.0.0.1 localhost" > /tmp/overlay-demo/merged/hosts

# Check what happened:
$ cat /tmp/overlay-demo/lower/hosts
Original /etc/hosts        ← Unchanged!

$ cat /tmp/overlay-demo/upper/hosts
127.0.0.1 localhost        ← New version here!

$ cat /tmp/overlay-demo/merged/hosts
127.0.0.1 localhost        ← Container sees upper version
```

**What happened:**
1. File read from `lower` initially
2. Write triggered copy to `upper`
3. Modified version written to `upper`
4. `merged` view shows `upper` version (masks `lower`)

---

## Part 4: Container Image Layers

### How Docker Images Use Layers

**Dockerfile:**
```dockerfile
FROM ubuntu:20.04          # Layer 1 (base)
RUN apt-get update         # Layer 2
RUN apt-get install python3 # Layer 3
COPY app.py /app/          # Layer 4
CMD ["python3", "/app/app.py"]
```

**Resulting layers:**
```
┌─────────────────────────────────────────────────────┐
│ Container filesystem (merged view)                  │
└─────────────────────────────────────────────────────┘
         OverlayFS combines ↓
┌─────────────────────────────────────────────────────┐
│ Layer 4: app.py                     (10 MB)         │ ← Writeable
├─────────────────────────────────────────────────────┤
│ Layer 3: Python3 binaries           (100 MB)        │ ← Read-only
├─────────────────────────────────────────────────────┤
│ Layer 2: apt-get update             (50 MB)         │ ← Read-only
├─────────────────────────────────────────────────────┤
│ Layer 1: Ubuntu base                (200 MB)        │ ← Read-only
└─────────────────────────────────────────────────────┘
```

**When container runs:**
```
Container's view = Layer 1 + Layer 2 + Layer 3 + Layer 4
                   + upper (runtime changes)
```

**When you modify /etc/hosts in container:**
```
/etc/hosts originally from Layer 1 (Ubuntu)
  ↓ modification
Copied to upper layer (CoW)
  ↓
Container sees modified version
Layer 1 unchanged (read-only)
```

---

### Layer Sharing

**Multiple containers from same image:**
```
Image: ubuntu:20.04 (200 MB)
  ├─ Container 1: upper layer (5 MB unique changes)
  ├─ Container 2: upper layer (3 MB unique changes)
  └─ Container 3: upper layer (8 MB unique changes)

Total storage:
  200 MB (shared base) + 5 MB + 3 MB + 8 MB = 216 MB

Without layering:
  200 MB + 200 MB + 200 MB = 600 MB ← 3x larger!
```

**Storage savings scale:**
- 10 containers: 200 MB + 10×(unique changes)
- 100 containers: 200 MB + 100×(unique changes)
- Base image stored once, shared by all!

---

## Part 5: Storage Drivers Comparison

### Available Storage Drivers

```
┌──────────────┬─────────────┬───────────────┬──────────────┐
│ DRIVER       │ TYPE        │ PERFORMANCE   │ STATUS       │
├──────────────┼─────────────┼───────────────┼──────────────┤
│ overlay2     │ OverlayFS   │ Excellent     │ PREFERRED    │
│ btrfs        │ Native CoW  │ Good          │ Specialized  │
│ zfs          │ Native CoW  │ Good          │ Specialized  │
│ devicemapper │ Block-level │ OK (thin LVM) │ Legacy       │
│ aufs         │ Union FS    │ OK            │ Deprecated   │
│ vfs          │ None (copy) │ Terrible      │ Testing only │
└──────────────┴─────────────┴───────────────┴──────────────┘
```

### overlay2 (Recommended)

**Why it's best:**
- ✅ **Fast**: Native kernel support
- ✅ **Efficient**: True CoW, minimal overhead
- ✅ **Stable**: Mainline kernel since 3.18
- ✅ **Simple**: Easy to understand and debug

**Requirements:**
- Linux kernel 4.0+ (5.11+ for rootless)
- XFS or ext4 filesystem on host

**Check your driver:**
```bash
$ docker info | grep "Storage Driver"
Storage Driver: overlay2
```

### devicemapper (Legacy)

**How it works:**
- Block-level CoW using LVM thin provisioning
- More complex than filesystem-level

**Why avoid:**
- ❌ Performance overhead
- ❌ Complex configuration
- ❌ Deprecated in favor of overlay2

---

## Part 6: Performance Implications

### Read Performance

```
┌──────────────────────────────────────────────────────┐
│ SCENARIO             │ OPERATIONS                    │
├──────────────────────┼───────────────────────────────┤
│ File in lower layer  │ 1. Check upper (miss)         │
│ (most common)        │ 2. Check lower (hit)          │
│                      │ ✅ Fast, direct read          │
├──────────────────────┼───────────────────────────────┤
│ File in upper layer  │ 1. Check upper (hit)          │
│ (modified/new)       │ ✅ Fastest, no layer search   │
└──────────────────────┴───────────────────────────────┘
```

**Impact:** Reads are very fast (near-native performance).

### Write Performance

```
┌──────────────────────────────────────────────────────┐
│ OPERATION            │ COST                          │
├──────────────────────┼───────────────────────────────┤
│ New file             │ ✅ Fast (write to upper)      │
├──────────────────────┼───────────────────────────────┤
│ Modify existing file │ ⚠️  CoW overhead:             │
│ (first write)        │ 1. Copy from lower to upper   │
│                      │ 2. Modify in upper            │
│                      │ (slower for large files)      │
├──────────────────────┼───────────────────────────────┤
│ Modify again         │ ✅ Fast (already in upper)    │
│ (subsequent)         │                               │
└──────────────────────┴───────────────────────────────┘
```

**First-write penalty:**
```
Small file (1 KB):   Negligible
Medium file (1 MB):  Noticeable
Large file (1 GB):   Significant! (entire file copied)
```

**Best practice:** Don't modify large files in containers.

---

### Layer Count Impact

**More layers = slower startup:**
```
5 layers:    Fast startup
10 layers:   OK
50 layers:   Slow startup
100+ layers: Very slow ← Avoid!
```

**Why:**
- Each layer = filesystem mount
- More layers = more directories to search
- Docker recommends < 20 layers

**Optimization:**
```dockerfile
# BAD: Creates 3 layers
RUN apt-get update
RUN apt-get install python3
RUN apt-get install curl

# GOOD: Creates 1 layer
RUN apt-get update && \
    apt-get install -y python3 curl && \
    rm -rf /var/lib/apt/lists/*
```

---

## Part 7: Practical Optimizations

### Minimize Layer Size

**BAD:**
```dockerfile
FROM ubuntu:20.04
RUN apt-get update
RUN apt-get install -y build-tools  # 500 MB
RUN build-my-app
RUN apt-get remove build-tools      # Doesn't reduce image size!
```

**Why bad:** Each RUN creates a layer. Removing files in later layer doesn't reduce earlier layer size!

**GOOD (multi-stage build):**
```dockerfile
# Build stage
FROM ubuntu:20.04 AS builder
RUN apt-get update && apt-get install -y build-tools
RUN build-my-app

# Final stage
FROM ubuntu:20.04
COPY --from=builder /app/binary /app/  # Only copy what's needed
CMD ["/app/binary"]
```

**Result:** Final image doesn't include build-tools (500 MB saved).

---

### Leverage Layer Caching

**Docker reuses layers if nothing changed:**

```dockerfile
FROM ubuntu:20.04

# This rarely changes → cached layer reused
RUN apt-get update && apt-get install -y python3

# This changes frequently → rebuilt
COPY app.py /app/

CMD ["python3", "/app/app.py"]
```

**Optimization:** Put frequently-changing content (app code) in later layers.

**BAD order:**
```dockerfile
COPY app.py /app/           # Changes often
RUN apt-get install python3 # Rebuilt every time app changes!
```

**GOOD order:**
```dockerfile
RUN apt-get install python3 # Cached!
COPY app.py /app/           # Only this layer rebuilt
```

---

### Use .dockerignore

**Problem:** COPY sends entire build context to Docker daemon.

```
Project directory:
├─ app.py (1 MB)
├─ .git/ (500 MB)          ← Don't need!
├─ node_modules/ (1 GB)    ← Don't need!
└─ data/ (10 GB)           ← Don't need!
```

**Solution:** `.dockerignore`
```
.git
node_modules
data/
*.log
```

**Result:** Faster builds, smaller images.

---

## Quick Reference

### OverlayFS Directories

| Directory | Purpose | Writable? |
|-----------|---------|-----------|
| `lowerdir` | Base image layers | No (read-only) |
| `upperdir` | Container changes | Yes |
| `workdir` | OverlayFS internals | N/A |
| `merged` | Combined view | Yes (writes go to upper) |

### Storage Driver Commands

```bash
# Check storage driver
docker info | grep "Storage Driver"

# Inspect image layers
docker history ubuntu:20.04

# Show layer details
docker inspect ubuntu:20.04

# Disk usage
docker system df
```

### Best Practices

```dockerfile
# ✅ Combine RUN commands (fewer layers)
RUN apt-get update && \
    apt-get install -y pkg1 pkg2 && \
    rm -rf /var/lib/apt/lists/*

# ✅ Order by change frequency (cache efficiency)
RUN apt-get install deps  # Rarely changes
COPY requirements.txt .   # Changes sometimes
RUN pip install -r requirements.txt
COPY app.py .             # Changes often

# ✅ Use multi-stage builds (smaller final image)
FROM golang:1.20 AS builder
RUN go build -o app .

FROM alpine:3.18
COPY --from=builder /app /app
```

---

## What You've Learned

✅ **Copy-on-Write** - Avoids duplicating data until it changes
✅ **Union filesystems** - Combine multiple layers into single view
✅ **OverlayFS** - Modern standard with excellent performance
✅ **Image layers** - Built from Dockerfile, shared across containers
✅ **Storage efficiency** - Base layers shared, only unique changes stored
✅ **Performance tradeoffs** - Fast reads, first-write CoW penalty for large files
✅ **Optimization techniques** - Multi-stage builds, layer ordering, minimizing layer count

---

## Next Steps

**Continue learning:**
→ [Container vs VM Comparison](03_container_vs_vm.md) - When to use each isolation approach

**Related topics:**
→ [cgroups and Namespaces](01_cgroups_namespaces.md) - Container isolation primitives
→ [Container Runtimes](../02_runtimes/01_runtime_landscape.md) - How runtimes manage images

**Practical next step:**
→ Build your first optimized Dockerfile using techniques learned here
