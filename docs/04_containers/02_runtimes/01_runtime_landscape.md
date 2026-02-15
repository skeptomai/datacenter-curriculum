---
level: intermediate
estimated_time: 35 min
prerequisites:
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
  - 04_containers/01_fundamentals/03_container_vs_vm.md
next_recommended:
  - 04_containers/02_runtimes/02_docker_containerd.md
tags: [containers, runtime, oci, cri, containerd, docker, runc]
---

# Container Runtime Landscape

**Learning Objectives:**
- Understand the container runtime hierarchy (CRI → high-level → low-level)
- Explain the OCI (Open Container Initiative) specifications
- Identify the role of each runtime layer
- Recognize how Kubernetes interacts with container runtimes
- Navigate the runtime ecosystem

---

## Introduction: What is a Container Runtime?

We know [containers use cgroups and namespaces](../01_fundamentals/01_cgroups_namespaces.md) for isolation. But **who creates those namespaces?** Who sets up the cgroups? Who mounts the filesystem?

**Answer:** The container runtime.

**But it's not one thing - it's a stack of components:**

```
┌─────────────────────────────────────────────────────┐
│ Container Orchestrator (Kubernetes)                 │
│ "Run this container image"                          │
└─────────────────┬───────────────────────────────────┘
                  │ CRI (Container Runtime Interface)
┌─────────────────▼───────────────────────────────────┐
│ High-level Runtime (containerd, CRI-O)              │
│ - Image management (pull, store, build)             │
│ - Image unpacking (layers → filesystem)             │
│ - Container lifecycle (create, start, stop)         │
└─────────────────┬───────────────────────────────────┘
                  │ OCI Runtime Spec
┌─────────────────▼───────────────────────────────────┐
│ Low-level Runtime (runc, crun)                      │
│ - Create namespaces                                 │
│ - Set up cgroups                                    │
│ - Execute container process                         │
└─────────────────────────────────────────────────────┘
```

**Three layers:**
1. **Orchestrator** (Kubernetes) - Decides what to run
2. **High-level runtime** (containerd) - Manages images and lifecycle
3. **Low-level runtime** (runc) - Actually creates the container

---

## Part 1: The OCI Specifications

### What is OCI?

**Open Container Initiative (OCI)** - Industry standards for container formats and runtimes.

**Founded:** 2015 (by Docker, CoreOS, Google, and others)
**Goal:** Prevent fragmentation, ensure interoperability

**Three specifications:**

```
┌──────────────────────────────────────────────────────┐
│ OCI SPECIFICATION │ DEFINES                          │
├───────────────────┼──────────────────────────────────┤
│ Runtime Spec      │ How to run a container           │
│                   │ (config.json format)             │
├───────────────────┼──────────────────────────────────┤
│ Image Spec        │ Container image format           │
│                   │ (layers, manifest, config)       │
├───────────────────┼──────────────────────────────────┤
│ Distribution Spec │ How to push/pull images          │
│                   │ (registry API)                   │
└───────────────────┴──────────────────────────────────┘
```

---

### OCI Runtime Specification

**Defines:** How to run a container from a filesystem bundle

**Core concept: "Bundle"**
```
bundle/
├── config.json     ← Runtime configuration
└── rootfs/         ← Container root filesystem
    ├── bin/
    ├── etc/
    └── lib/
```

**config.json example:**
```json
{
  "ociVersion": "1.0.0",
  "process": {
    "terminal": true,
    "user": {"uid": 0, "gid": 0},
    "args": ["/bin/sh"],
    "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
    "cwd": "/"
  },
  "root": {
    "path": "rootfs",
    "readonly": false
  },
  "hostname": "mycontainer",
  "mounts": [...],
  "linux": {
    "namespaces": [
      {"type": "pid"},
      {"type": "network"},
      {"type": "ipc"},
      {"type": "uts"},
      {"type": "mount"}
    ],
    "resources": {
      "memory": {"limit": 536870912},
      "cpu": {"quota": 100000, "period": 100000}
    }
  }
}
```

**What this describes:**
- Run `/bin/sh` as UID 0
- Create pid, network, ipc, uts, mount namespaces
- Limit to 512 MB RAM, 1 CPU core
- Use `rootfs/` as root filesystem

**Any OCI-compliant runtime can run this bundle.**

---

### OCI Image Specification

**Defines:** Container image format (how layers are stored)

**Image structure:**
```
image/
├── manifest.json       ← Points to config and layers
├── config.json         ← Image metadata
└── blobs/              ← Content-addressable storage
    ├── sha256:abc123   ← Layer 1 (tar.gz)
    ├── sha256:def456   ← Layer 2 (tar.gz)
    └── sha256:ghi789   ← Layer 3 (tar.gz)
```

**Why it matters:** Docker images, containerd images, Podman images all use this format → interoperable!

---

## Part 2: Low-Level Runtimes

### What is a Low-Level Runtime?

**Responsibility:** Actually create the container (namespaces, cgroups, filesystem)

**Input:** OCI bundle (config.json + rootfs)
**Output:** Running container process

**Does NOT:**
- ❌ Pull images from registry
- ❌ Manage image layers
- ❌ Build images
- ❌ Provide networking beyond basic setup

**ONLY:**
- ✅ Create namespaces
- ✅ Set up cgroups
- ✅ Configure seccomp/AppArmor
- ✅ Execute container process

---

### runc - The Reference Implementation

**What it is:** Reference OCI runtime, written in Go

**Created by:** Docker (donated to OCI in 2015)

**Usage:**
```bash
# Create OCI bundle
mkdir -p mycontainer/rootfs
tar -C mycontainer/rootfs -xf alpine-rootfs.tar

# Generate config.json
cd mycontainer
runc spec  # Creates default config.json

# Run container
runc run mycontainer
```

**Under the hood (simplified):**
```go
// What runc does:
1. Read config.json
2. Create namespaces:
   unshare(CLONE_NEWPID | CLONE_NEWNET | CLONE_NEWNS | ...)
3. Set up cgroups:
   mkdir /sys/fs/cgroup/mycontainer
   echo $$ > /sys/fs/cgroup/mycontainer/cgroup.procs
   echo "536870912" > /sys/fs/cgroup/mycontainer/memory.max
4. Mount rootfs:
   pivot_root("rootfs", "old_root")
5. Apply security:
   - Drop capabilities
   - Apply seccomp filter
   - Set UID/GID
6. Execute process:
   execve("/bin/sh", ...)
```

**Key point:** runc is **single-purpose** - run one container from OCI bundle.

---

### Alternative Low-Level Runtimes

**crun** (written in C)
- **Faster** than runc (~50% faster startup)
- **Smaller** binary (~1 MB vs ~10 MB)
- **Lower memory** usage
- Used by: Podman (default), some Kubernetes setups

**youki** (written in Rust)
- Experimental, focused on performance
- Memory-safe (Rust benefits)

**kata-runtime** (see [Kata Containers](03_kata_gvisor.md))
- Uses VMs instead of namespaces
- OCI-compatible interface

**Why alternatives?** Performance, memory safety, specific features.

---

## Part 3: High-Level Runtimes

### What is a High-Level Runtime?

**Responsibility:** Image management + container lifecycle

```
┌──────────────────────────────────────────────────────┐
│ High-Level Runtime Responsibilities:                 │
│                                                       │
│ 1. Image operations:                                 │
│    - Pull from registry (docker.io, gcr.io, etc.)    │
│    - Store images locally                            │
│    - Unpack layers (OverlayFS)                       │
│    - Build images (optional)                         │
│                                                       │
│ 2. Container lifecycle:                              │
│    - Create (prepare OCI bundle)                     │
│    - Start (call low-level runtime)                  │
│    - Stop, pause, resume                             │
│    - Delete (cleanup)                                │
│                                                       │
│ 3. Networking:                                       │
│    - Set up network namespace                        │
│    - Call CNI plugins                                │
│    - Configure container network                     │
│                                                       │
│ 4. Storage:                                          │
│    - Manage volumes                                  │
│    - Set up mounts                                   │
└──────────────────────────────────────────────────────┘
```

**Examples:** containerd, CRI-O, Docker Engine (includes high + low level)

---

### containerd

**What it is:** Industry-standard high-level container runtime

**Created by:** Docker (donated to CNCF in 2017)
**Used by:** Kubernetes, Docker Desktop, AWS Fargate, Google Cloud Run

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│ containerd                                          │
│                                                      │
│ ┌────────────────┐  ┌────────────────┐             │
│ │ Image Service  │  │ Container Svc  │             │
│ │ - Pull images  │  │ - Create       │             │
│ │ - Store images │  │ - Start        │             │
│ │ - Unpack       │  │ - Stop         │             │
│ └────────────────┘  └───────┬────────┘             │
│                             │                        │
│ ┌────────────────┐          │                       │
│ │ Snapshot Svc   │          │                       │
│ │ - OverlayFS    │          │                       │
│ └────────────────┘          │                       │
│                             ▼                        │
│                     ┌───────────────┐               │
│                     │ Task Service  │               │
│                     │ - Exec        │               │
│                     └───────┬───────┘               │
└─────────────────────────────┼───────────────────────┘
                              │ shim API
                      ┌───────▼────────┐
                      │ containerd-shim│
                      └───────┬────────┘
                              │
                      ┌───────▼────────┐
                      │     runc       │
                      └────────────────┘
```

**Key features:**
- **Daemon-less containers** - shim keeps containers running even if containerd restarts
- **Pluggable snapshotter** - OverlayFS, btrfs, ZFS
- **Namespace isolation** - Multiple tenants in one containerd
- **CRI support** - Native Kubernetes integration

---

### CRI-O

**What it is:** OCI-based Kubernetes runtime (CRI-only, no general purpose)

**Created by:** Red Hat (for OpenShift/Kubernetes)
**Philosophy:** Minimal, purpose-built for Kubernetes

**Differences from containerd:**
```
┌──────────────────┬──────────────────┬──────────────────┐
│ FEATURE          │ containerd       │ CRI-O            │
├──────────────────┼──────────────────┼──────────────────┤
│ Scope            │ General purpose  │ Kubernetes only  │
│ CLI tool         │ ctr, nerdctl     │ None (CRI only)  │
│ Image build      │ Via BuildKit     │ Via Buildah      │
│ Kubernetes       │ Primary runtime  │ Only runtime     │
│ Footprint        │ Larger           │ Smaller          │
└──────────────────┴──────────────────┴──────────────────┘
```

**When to use CRI-O:** Kubernetes-only environments, want minimal footprint.

---

## Part 4: The CRI (Container Runtime Interface)

### What is CRI?

**Problem:** Kubernetes needs to work with different runtimes (Docker, containerd, CRI-O, etc.)

**Solution:** Standardized API between Kubernetes and runtimes

```
┌─────────────────────────────────────────────────────┐
│ Kubernetes (kubelet)                                │
│ "I need to run this pod with these containers"      │
└─────────────────┬───────────────────────────────────┘
                  │
        CRI (gRPC API)
                  │
    ┌─────────────┴──────────────┬─────────────────┐
    │                            │                 │
┌───▼──────────┐      ┌──────────▼───┐   ┌────────▼────┐
│ containerd   │      │ CRI-O        │   │ Docker      │
│ (via CRI     │      │ (native CRI) │   │ (via        │
│  plugin)     │      │              │   │  dockershim)│
└──────────────┘      └──────────────┘   └─────────────┘
```

**CRI defines two services:**

1. **ImageService** - Manage images
   - PullImage
   - ListImages
   - RemoveImage

2. **RuntimeService** - Manage containers
   - RunPodSandbox (create pod)
   - CreateContainer
   - StartContainer
   - StopContainer
   - RemoveContainer

---

### CRI in Practice

**Kubernetes pod creation:**
```
1. kubelet → CRI: RunPodSandbox
   ↓
   containerd creates:
   - Network namespace
   - IPC namespace
   - PID namespace
   Returns: sandbox ID

2. kubelet → CRI: PullImage("nginx:latest")
   ↓
   containerd pulls image from registry

3. kubelet → CRI: CreateContainer(sandbox_id, nginx_config)
   ↓
   containerd prepares OCI bundle

4. kubelet → CRI: StartContainer(container_id)
   ↓
   containerd → runc → container starts!
```

**Why CRI matters:**
- Kubernetes doesn't know about containerd internals
- Can swap runtimes without changing Kubernetes
- Multiple runtimes can coexist

---

## Part 5: The Complete Stack

### Docker Engine (Historical Context)

**Traditional Docker stack:**
```
┌─────────────────────────────────────────────────────┐
│ Docker CLI (docker run, docker build, ...)         │
└─────────────────┬───────────────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────────────┐
│ Docker Engine (dockerd)                             │
│ - Image management                                  │
│ - Volume management                                 │
│ - Network management                                │
│ - Build (BuildKit)                                  │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│ containerd                                          │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│ runc                                                │
└─────────────────────────────────────────────────────┘
```

**Evolution:**
- **2014-2016**: Docker = monolithic (all-in-one)
- **2016**: Extracted containerd
- **2019**: containerd graduates CNCF
- **2020**: Kubernetes deprecates dockershim
- **2022**: dockershim removed from Kubernetes

---

### Modern Kubernetes Stack

```
┌─────────────────────────────────────────────────────┐
│ Kubernetes Control Plane                            │
│ (API Server, Scheduler, Controllers)                │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│ kubelet (on each node)                              │
└─────────────────┬───────────────────────────────────┘
                  │ CRI gRPC
┌─────────────────▼───────────────────────────────────┐
│ containerd (with CRI plugin)                        │
│ - Implements ImageService                           │
│ - Implements RuntimeService                         │
└─────────────────┬───────────────────────────────────┘
                  │ OCI Runtime Spec
┌─────────────────▼───────────────────────────────────┐
│ runc (or crun, kata-runtime, etc.)                  │
│ - Creates namespaces                                │
│ - Sets up cgroups                                   │
│ - Executes container process                        │
└─────────────────────────────────────────────────────┘
```

**Clean separation of concerns:**
- **Kubernetes**: Orchestration
- **containerd**: Container lifecycle + images
- **runc**: Low-level container creation

---

## Part 6: Runtime Ecosystem Map

### Current Landscape (2024+)

```
┌─────────────────────────────────────────────────────┐
│ LAYER         │ OPTIONS                             │
├───────────────┼─────────────────────────────────────┤
│ Orchestrator  │ - Kubernetes (dominant)             │
│               │ - Docker Swarm (legacy)             │
│               │ - Nomad                             │
├───────────────┼─────────────────────────────────────┤
│ CRI Interface │ Standard gRPC API                   │
├───────────────┼─────────────────────────────────────┤
│ High-level    │ - containerd (most common)          │
│ Runtime       │ - CRI-O (Kubernetes-focused)        │
│               │ - Docker Engine (includes low-level)│
├───────────────┼─────────────────────────────────────┤
│ OCI Runtime   │ Standard (runtime-spec)             │
│ Spec          │                                     │
├───────────────┼─────────────────────────────────────┤
│ Low-level     │ - runc (reference, most common)     │
│ Runtime       │ - crun (faster, C implementation)   │
│               │ - kata-runtime (VM-isolated)        │
│               │ - runsc/gVisor (userspace kernel)   │
└───────────────┴─────────────────────────────────────┘
```

### Choosing a Runtime Stack

**For Kubernetes:**
```
Most common:
  kubelet → containerd (CRI) → runc

Red Hat/OpenShift:
  kubelet → CRI-O → runc/crun

High security:
  kubelet → containerd → kata-runtime (VMs)

Google Cloud (GKE Sandbox):
  kubelet → containerd → runsc (gVisor)
```

**For local development:**
```
Docker Desktop:
  docker CLI → Docker Engine → containerd → runc

Podman:
  podman CLI → (no daemon) → crun

nerdctl:
  nerdctl CLI → containerd → runc
```

---

## Quick Reference

### Runtime Layers

| Layer | Examples | Responsibility |
|-------|----------|----------------|
| **Orchestrator** | Kubernetes | Decide what/where to run |
| **CRI** | gRPC API | Standard interface |
| **High-level** | containerd, CRI-O | Images + lifecycle |
| **OCI Spec** | runtime-spec | Standard format |
| **Low-level** | runc, crun | Create container |

### Common Commands

```bash
# containerd (via ctr)
ctr images pull docker.io/library/nginx:latest
ctr run --rm docker.io/library/nginx:latest nginx

# containerd (via nerdctl - Docker-compatible)
nerdctl run -d nginx:latest

# runc (low-level)
runc run mycontainer

# Check runtime
kubectl get nodes -o wide  # Shows container runtime
crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps
```

### Key Specifications

- **OCI Runtime Spec**: https://github.com/opencontainers/runtime-spec
- **OCI Image Spec**: https://github.com/opencontainers/image-spec
- **CRI**: https://github.com/kubernetes/cri-api

---

## What You've Learned

✅ **Runtime hierarchy** - Orchestrator → High-level → Low-level
✅ **OCI specifications** - Runtime, Image, Distribution specs
✅ **Low-level runtimes** - runc creates containers from OCI bundles
✅ **High-level runtimes** - containerd/CRI-O manage images and lifecycle
✅ **CRI interface** - Standard API between Kubernetes and runtimes
✅ **Runtime ecosystem** - How Docker, containerd, Kubernetes fit together

---

## Next Steps

**Continue learning:**
→ [Docker & containerd](02_docker_containerd.md) - Architecture and evolution in detail
→ [Kata Containers & gVisor](03_kata_gvisor.md) - Secure runtime alternatives

**Related topics:**
→ [Container Fundamentals](../01_fundamentals/01_cgroups_namespaces.md) - What runtimes actually create
→ [Kubernetes Architecture](../03_orchestration/01_kubernetes_architecture.md) - How orchestration uses runtimes
