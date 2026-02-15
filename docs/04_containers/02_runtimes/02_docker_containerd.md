---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 04_containers/01_fundamentals/02_union_filesystems.md
  - 04_containers/02_runtimes/01_runtime_landscape.md
next_recommended:
  - 04_containers/02_runtimes/03_kata_gvisor.md
tags: [containers, docker, containerd, runc, architecture, evolution]
---

# Docker, containerd, and runc: Architecture Deep Dive

**Learning Objectives:**
- Understand Docker's evolution from monolith to modular architecture
- Explain containerd's role as standalone runtime
- Trace the path from `docker run` to running container
- Compare Docker Engine to containerd-only deployments
- Recognize when to use Docker vs containerd directly

---

## Introduction: Docker's Evolution

**2013:** Docker launches as revolutionary all-in-one tool
**2016:** Extracts containerd as separate component
**2017:** containerd donated to CNCF
**2020:** Kubernetes deprecates dockershim
**2024:** containerd is industry standard

**Why the evolution?** Docker was too monolithic for cloud-native ecosystems.

---

## Part 1: Docker Architecture (Modern)

### The Complete Docker Stack

```
┌─────────────────────────────────────────────────────┐
│ USER INTERACTION                                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  $ docker run -d -p 80:80 nginx                     │
│                    ↓                                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ Docker CLI (docker)                          │  │
│  │ - Parses commands                            │  │
│  │ - Sends REST API requests                    │  │
│  └─────────────────┬────────────────────────────┘  │
│                    │ HTTP REST API                  │
│                    │ (unix:///var/run/docker.sock)  │
├────────────────────┼────────────────────────────────┤
│ DOCKER ENGINE      │                                │
│  ┌─────────────────▼────────────────────────────┐  │
│  │ Docker Daemon (dockerd)                      │  │
│  │ ┌──────────────────────────────────────────┐ │  │
│  │ │ API Server                               │ │  │
│  │ │ - Handles REST requests                  │ │  │
│  │ └──────────────────────────────────────────┘ │  │
│  │ ┌──────────────────────────────────────────┐ │  │
│  │ │ Image Management                         │ │  │
│  │ │ - Pull/push                              │ │  │
│  │ │ - Build (BuildKit)                       │ │  │
│  │ │ - Tag, save                              │ │  │
│  │ └──────────────────────────────────────────┘ │  │
│  │ ┌──────────────────────────────────────────┐ │  │
│  │ │ Volume Management                        │ │  │
│  │ │ - Create volumes                         │ │  │
│  │ │ - Bind mounts                            │ │  │
│  │ └──────────────────────────────────────────┘ │  │
│  │ ┌──────────────────────────────────────────┐ │  │
│  │ │ Network Management                       │ │  │
│  │ │ - bridge, host, overlay networks         │ │  │
│  │ │ - DNS, port mapping                      │ │  │
│  │ └──────────────────────────────────────────┘ │  │
│  └─────────────────┬────────────────────────────┘  │
│                    │ containerd gRPC API            │
├────────────────────┼────────────────────────────────┤
│ CONTAINER RUNTIME  │                                │
│  ┌─────────────────▼────────────────────────────┐  │
│  │ containerd                                   │  │
│  │ - Container lifecycle                        │  │
│  │ - Image storage                              │  │
│  │ - Snapshot management (OverlayFS)            │  │
│  └─────────────────┬────────────────────────────┘  │
│                    │ containerd-shim                │
│  ┌─────────────────▼────────────────────────────┐  │
│  │ runc                                         │  │
│  │ - Creates namespaces                         │  │
│  │ - Sets up cgroups                            │  │
│  │ - Executes process                           │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Key insight:** Docker Engine is a **wrapper** around containerd with additional features.

---

## Part 2: From `docker run` to Running Container

### Step-by-Step Execution

**Command:**
```bash
$ docker run -d --name web -p 80:80 nginx:latest
```

**What happens:**

#### Step 1: CLI Parsing
```
Docker CLI:
1. Parse command arguments
   - Image: nginx:latest
   - Port mapping: 80:80
   - Name: web
   - Detached mode: -d
2. Build REST API request
3. Send to dockerd (via Unix socket)
```

#### Step 2: Image Check
```
dockerd:
1. Check if image exists locally
   $ ls /var/lib/docker/image/overlay2/imagedb/content/sha256/
   └─ abc123... (nginx:latest)

2. If not found → Pull from registry
   a. Contact registry (docker.io)
   b. Download manifest
   c. Download layers (only missing ones)
   d. Verify checksums
   e. Store in /var/lib/docker/image/
```

#### Step 3: Network Setup
```
dockerd:
1. Create network namespace
2. Set up bridge network
   - Create veth pair
   - Attach one end to docker0 bridge
   - Put other end in container namespace
3. Configure iptables rules for port 80:80
   iptables -t nat -A DOCKER -p tcp --dport 80 -j DNAT \
     --to-destination 172.17.0.2:80
```

#### Step 4: Delegate to containerd
```
dockerd → containerd (gRPC call):

CreateContainer(
  id: "web",
  image: "docker.io/library/nginx:latest",
  spec: {
    process: {args: ["nginx", "-g", "daemon off;"]},
    mounts: [...],
    linux: {
      namespaces: [pid, net, ipc, uts, mount],
      resources: {memory: {...}, cpu: {...}}
    }
  }
)
```

#### Step 5: containerd Prepares Bundle
```
containerd:
1. Create working directory
   /run/containerd/io.containerd.runtime.v2.task/moby/web/

2. Unpack image layers
   - Use overlay2 snapshotter
   - Stack layers:
     Layer 1: Base Debian
     Layer 2: Nginx install
     Layer 3: Config files
   - Create merged view in:
     /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/

3. Generate OCI config.json
   {
     "ociVersion": "1.0.0",
     "process": {"args": ["nginx", "-g", "daemon off;"]},
     "root": {"path": "rootfs"},
     "mounts": [...],
     "linux": {
       "namespaces": [...],
       "resources": {...}
     }
   }
```

#### Step 6: containerd-shim Spawns runc
```
containerd:
1. Start containerd-shim
   Purpose: Keep container running even if containerd restarts

2. shim forks and execs runc:
   $ runc create --bundle /path/to/bundle web

3. shim monitors container process
   - Captures stdout/stderr
   - Reports container status
   - Handles container exit
```

#### Step 7: runc Creates Container
```
runc:
1. Create namespaces
   - PID namespace (new)
   - NET namespace (from dockerd)
   - Mount namespace (new)
   - UTS namespace (new)
   - IPC namespace (new)

2. Set up cgroups
   /sys/fs/cgroup/docker/web/
   ├─ cpu.max = "100000 100000"
   ├─ memory.max = "unlimited"
   └─ pids.max = "unlimited"

3. Mount rootfs
   mount -t overlay overlay \
     -o lowerdir=/lower1:/lower2:/lower3,\
        upperdir=/upper,workdir=/work \
     /merged

4. Apply security
   - Drop capabilities (keep only CAP_NET_BIND_SERVICE, etc.)
   - Apply seccomp filter
   - Set AppArmor/SELinux profile

5. Execute nginx process
   execve("/usr/sbin/nginx", ["nginx", "-g", "daemon off;"], env)
```

#### Step 8: Container Runs
```
Container process tree:

PID 1 (in host):    systemd
PID 1234 (in host): containerd
PID 1235 (in host): containerd-shim
PID 1236 (in host): nginx (master)  ← Container's PID 1
PID 1237 (in host): nginx (worker)  ← Container's PID 2

Inside container's PID namespace:
PID 1:  nginx (master)
PID 2:  nginx (worker)
```

**Total time:** ~100-200 ms (if image already pulled)

---

## Part 3: containerd Architecture

### containerd as Standalone

**containerd can run without Docker!**

```
┌─────────────────────────────────────────────────────┐
│ containerd (daemon)                                 │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Content Store                                   │ │
│ │ - Content-addressable storage (blobs)           │ │
│ │ - Deduplicates layers                           │ │
│ │ /var/lib/containerd/io.containerd.content.v1/   │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Snapshot Service                                │ │
│ │ - Manages filesystem snapshots                  │ │
│ │ - Supports: overlayfs, btrfs, zfs, native       │ │
│ │ /var/lib/containerd/io.containerd.snapshotter/  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Metadata Store                                  │ │
│ │ - Container/image metadata                      │ │
│ │ - Uses bolt database                            │ │
│ │ /var/lib/containerd/io.containerd.metadata.v1/  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Runtime (shim v2)                               │ │
│ │ - Manages container processes                   │ │
│ │ - Keeps containers running independently        │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Services                                        │ │
│ │ ├─ Images                                       │ │
│ │ ├─ Containers                                   │ │
│ │ ├─ Tasks (running containers)                   │ │
│ │ ├─ Namespaces (multi-tenancy)                   │ │
│ │ └─ Events                                       │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

### Using containerd Directly

**CLI tools:**

1. **ctr** (basic, included with containerd)
```bash
# Pull image
ctr images pull docker.io/library/nginx:latest

# Run container
ctr run --rm -t docker.io/library/nginx:latest web

# List containers
ctr containers list
```

2. **nerdctl** (Docker-compatible, recommended)
```bash
# Same commands as Docker!
nerdctl run -d -p 80:80 nginx:latest
nerdctl ps
nerdctl logs web
nerdctl stop web
```

**Comparison:**
```
┌──────────────────┬──────────────────┬──────────────────┐
│ FEATURE          │ Docker CLI       │ nerdctl          │
├──────────────────┼──────────────────┼──────────────────┤
│ Syntax           │ docker run ...   │ nerdctl run ...  │
│ Backend          │ Docker Engine    │ containerd       │
│ Build support    │ ✅ Built-in      │ ✅ BuildKit      │
│ Compose support  │ ✅ Built-in      │ ✅ Via plugin    │
│ Kubernetes       │ ❌ Not directly  │ ✅ Native CRI    │
│ Rootless         │ ⚠️  Experimental │ ✅ Stable        │
└──────────────────┴──────────────────┴──────────────────┘
```

---

## Part 4: The containerd-shim

### Why Does the Shim Exist?

**Problem:** What if containerd crashes or restarts?

**Without shim:**
```
containerd (PID 100)
    └─ nginx container (PID 200)

containerd crashes → PID 100 dies → PID 200 orphaned/killed
```

**With shim:**
```
containerd (PID 100)
    └─ containerd-shim (PID 150)  ← Intermediary
           └─ nginx container (PID 200)

containerd crashes → PID 100 dies
    BUT PID 150 (shim) still running → PID 200 keeps running!
```

---

### Shim Responsibilities

```
┌──────────────────────────────────────────────────────┐
│ containerd-shim                                      │
│                                                       │
│ 1. Process management:                               │
│    - Fork/exec runc                                  │
│    - Monitor container process                       │
│    - Report exit codes                               │
│                                                       │
│ 2. I/O handling:                                     │
│    - Capture stdout/stderr                           │
│    - Forward to log drivers                          │
│    - Handle console (PTY) for interactive containers │
│                                                       │
│ 3. Daemonless containers:                            │
│    - Keep container running after containerd exits   │
│    - Reconnect when containerd restarts              │
│                                                       │
│ 4. Resource cleanup:                                 │
│    - Remove cgroups when container exits             │
│    - Unmount filesystems                             │
│    - Clean up network namespace                      │
└──────────────────────────────────────────────────────┘
```

**Per-container shim:**
```bash
$ ps aux | grep containerd-shim

root  1234  containerd
root  1500  containerd-shim ... -id web        ← Shim for "web" container
root  1600  containerd-shim ... -id db         ← Shim for "db" container
root  1700  containerd-shim ... -id cache      ← Shim for "cache" container
```

**Each container gets its own shim!**

---

## Part 5: runc Deep Dive

### What runc Actually Does

**Input:** OCI bundle
```
/run/containerd/.../web/
├── config.json    ← OCI runtime spec
└── rootfs/        ← Container filesystem
    ├── bin/
    ├── etc/
    └── usr/
```

**Output:** Running container process

---

### runc Execution Flow

```
┌──────────────────────────────────────────────────────┐
│ runc create (detailed)                               │
│                                                       │
│ 1. Parse config.json                                 │
│    - Read namespace config                           │
│    - Read cgroup config                              │
│    - Read mount config                               │
│    - Read security config (seccomp, caps)            │
│                                                       │
│ 2. Create parent process                             │
│    - Fork()                                          │
│    - Set up parent-child communication pipe          │
│                                                       │
│ 3. Create namespaces (in child)                      │
│    unshare(CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET│
│            | CLONE_NEWUTS | CLONE_NEWIPC)            │
│                                                       │
│ 4. Set up cgroups                                    │
│    - Create cgroup hierarchy                         │
│    - Write PIDs to cgroup.procs                      │
│    - Apply resource limits                           │
│                                                       │
│ 5. Set up mounts                                     │
│    - Bind mount rootfs                               │
│    - Mount /proc, /sys, /dev                         │
│    - Apply mount flags (ro, nosuid, etc.)            │
│    - pivot_root to change root                       │
│                                                       │
│ 6. Apply security                                    │
│    - Drop capabilities (keep only needed)            │
│    - Apply seccomp filter (restrict syscalls)        │
│    - Set AppArmor/SELinux context                    │
│    - Set UID/GID mapping (user namespaces)           │
│                                                       │
│ 7. Execute container process                         │
│    execve("/bin/nginx", argv, envp)                  │
│                                                       │
│ Container now running!                               │
└──────────────────────────────────────────────────────┘
```

---

### runc Commands

```bash
# Create container (prepared, not started)
runc create --bundle /path/to/bundle mycontainer

# Start previously created container
runc start mycontainer

# OR: Create + start in one command
runc run --bundle /path/to/bundle mycontainer

# List running containers
runc list

# Get container state
runc state mycontainer

# Execute additional process in running container
runc exec mycontainer /bin/sh

# Kill container
runc kill mycontainer SIGTERM

# Delete container
runc delete mycontainer
```

---

## Part 6: Docker vs containerd

### When to Use Docker

**Use Docker when:**

✅ **Local development**
- Familiar `docker` commands
- Docker Compose for multi-container apps
- Wide tooling support

✅ **Build-focused workflows**
- Dockerfile builds
- Multi-stage builds
- BuildKit integration

✅ **Developer experience matters**
- Desktop GUI (Docker Desktop)
- Easy setup
- Good documentation

**Example use case:** Local laptop development

---

### When to Use containerd Directly

**Use containerd when:**

✅ **Kubernetes production**
- Native CRI support
- Lower overhead (no Docker daemon)
- Faster pod startup

✅ **Minimal footprint needed**
- Embedded systems
- Serverless runtimes (Firecracker uses containerd)
- IoT devices

✅ **Custom integrations**
- Building your own platform
- Need fine-grained control
- Don't need Docker-specific features

**Example use case:** Kubernetes cluster nodes

---

### Feature Comparison

```
┌───────────────────┬──────────────┬──────────────────┐
│ FEATURE           │ Docker       │ containerd+nerdctl│
├───────────────────┼──────────────┼──────────────────┤
│ Image pull/push   │ ✅           │ ✅               │
│ Container run     │ ✅           │ ✅               │
│ Volume management │ ✅ Rich      │ ⚠️  Basic        │
│ Network types     │ ✅ Many      │ ⚠️  Fewer        │
│ Build images      │ ✅ Built-in  │ ✅ Via BuildKit  │
│ Compose           │ ✅ Built-in  │ ✅ Via plugin    │
│ Swarm mode        │ ✅ Built-in  │ ❌               │
│ CRI support       │ ⚠️  Via shim │ ✅ Native        │
│ Rootless          │ ⚠️  Beta     │ ✅ Production    │
│ Memory footprint  │ ~100 MB      │ ~50 MB           │
│ Startup time      │ Slower       │ Faster           │
└───────────────────┴──────────────┴──────────────────┘
```

---

## Part 7: Storage Locations

### Docker Directories

```
/var/lib/docker/
├── image/
│   └── overlay2/
│       ├── distribution/      ← Image metadata
│       ├── imagedb/           ← Image configs
│       └── layerdb/           ← Layer metadata
├── overlay2/                  ← Actual layer data
│   ├── abc123/                ← Layer 1
│   ├── def456/                ← Layer 2
│   └── l/                     ← Symlinks (short names)
├── containers/                ← Container configs
│   └── xyz789/
│       ├── config.v2.json
│       ├── hostconfig.json
│       └── hostname
├── volumes/                   ← Named volumes
│   └── myvolume/
│       └── _data/
└── network/                   ← Network configs
```

---

### containerd Directories

```
/var/lib/containerd/
├── io.containerd.content.v1.content/    ← Content store (blobs)
│   └── blobs/
│       └── sha256/
│           ├── abc123...
│           └── def456...
├── io.containerd.snapshotter.v1.overlayfs/ ← Filesystem snapshots
│   └── snapshots/
│       ├── 1/
│       ├── 2/
│       └── 3/
├── io.containerd.metadata.v1.bolt/      ← Metadata database
│   └── meta.db
└── tmpmounts/                            ← Temporary mounts
```

**Key difference:** containerd uses content-addressable storage (more efficient deduplication).

---

## Quick Reference

### Command Equivalents

| Docker | containerd (nerdctl) | containerd (ctr) |
|--------|----------------------|------------------|
| `docker run` | `nerdctl run` | `ctr run` |
| `docker ps` | `nerdctl ps` | `ctr containers list` |
| `docker images` | `nerdctl images` | `ctr images list` |
| `docker pull` | `nerdctl pull` | `ctr images pull` |
| `docker logs` | `nerdctl logs` | `ctr tasks logs` |
| `docker exec` | `nerdctl exec` | `ctr tasks exec` |

### Architecture Summary

```
Docker:
  CLI → Docker Engine (dockerd) → containerd → runc

containerd-only:
  nerdctl/ctr → containerd → runc

Kubernetes:
  kubelet (CRI) → containerd → runc
```

---

## What You've Learned

✅ **Docker evolution** - From monolith to modular architecture
✅ **Full execution path** - `docker run` through runc process creation
✅ **containerd architecture** - Content store, snapshots, metadata, shim
✅ **containerd-shim** - Enables daemonless containers
✅ **runc internals** - Namespace/cgroup creation, process execution
✅ **Docker vs containerd** - When to use each

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[containerd Source Code](https://github.com/containerd/containerd)** - Industry-standard container runtime with gRPC API
- **[Docker Architecture Documentation](https://docs.docker.com/get-started/overview/#docker-architecture)** - Official guide to Docker's modular design
- **[nerdctl](https://github.com/containerd/nerdctl)** - Docker-compatible CLI for containerd with enhanced features

---

## Next Steps

**Continue learning:**
→ [Kata Containers & gVisor](03_kata_gvisor.md) - Alternative runtimes with stronger isolation
→ [Runtime Comparison](04_runtime_comparison.md) - Decision matrix for choosing runtimes

**Related topics:**
→ [Union Filesystems](../01_fundamentals/02_union_filesystems.md) - How containerd stores layers
→ [Kubernetes Architecture](../03_orchestration/01_kubernetes_architecture.md) - How K8s uses containerd
