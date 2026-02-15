---
level: foundational
estimated_time: 50 min
prerequisites:
  - 01_foundations/01_virtualization_basics/01_the_ring0_problem.md
next_recommended:
  - 04_containers/01_fundamentals/02_union_filesystems.md
tags: [containers, linux, cgroups, namespaces, isolation, kernel]
---

# Linux Container Primitives: cgroups and Namespaces

**Learning Objectives:**
- Understand how Linux provides process isolation without hardware virtualization
- Explain the role of cgroups in resource limiting
- Identify the seven namespace types and their isolation boundaries
- Compare container isolation to VM isolation
- Recognize the security implications and limitations

---

## Introduction: Isolation Without Virtualization

In [The Ring-0 Problem](../../01_foundations/01_virtualization_basics/01_the_ring0_problem.md), we learned that **virtualization requires hardware support** because you can't run two operating systems in Ring 0 simultaneously. Virtual machines solve this with VT-x/AMD-V, creating two Ring-0 environments.

But what if you don't need **complete** isolation? What if you're okay with processes sharing the same kernel, as long as they:
- Can't see each other's processes
- Can't access each other's filesystems
- Can't exceed their allocated CPU/memory
- Can't interfere with each other's network

This is **container isolation**: using Linux kernel features to create isolated execution environments **without hardware virtualization**.

**The Two Pillars:**
1. **Namespaces** - Isolation (what you can see)
2. **cgroups** - Resource limits (what you can use)

---

## Part 1: Namespaces - Isolation

### What is a Namespace?

A namespace **wraps a global system resource** so that processes inside the namespace have their own isolated instance of that resource.

**Simple analogy:**
- **VM**: Separate house with its own kitchen, bedrooms, utilities
- **Namespace**: Separate apartment in the same building - own rooms, but shared building infrastructure

Processes in different namespaces **can't see** each other's resources, even though they're running on the same kernel.

### The Seven Namespace Types

Linux provides seven types of namespaces (as of kernel 5.6+):

```
┌──────────────────────────────────────────────────────────┐
│ NAMESPACE TYPE │ ISOLATES                  │ SINCE       │
├────────────────┼───────────────────────────┼─────────────┤
│ PID            │ Process IDs               │ Linux 2.6.24│
│ NET            │ Network devices, stacks   │ Linux 2.6.29│
│ MNT            │ Mount points              │ Linux 2.4.19│
│ UTS*           │ Hostname & domain name    │ Linux 2.6.19│
│ IPC            │ Inter-process comm        │ Linux 2.6.19│
│ USER           │ User and group IDs        │ Linux 3.8   │
│ CGROUP         │ Cgroup hierarchy view     │ Linux 4.6   │
└────────────────┴───────────────────────────┴─────────────┘

* UTS = UNIX Time-Sharing (historical name from UNIX Time-Sharing System)
```

Let's examine each in detail.

---

### PID Namespace: Process Isolation

**What it isolates:** Process ID numbers

```
Host System:
PID 1:    systemd (init)
PID 100:  sshd
PID 500:  containerized_app  ← Inside PID namespace

Inside Container's View (PID namespace):
PID 1:    containerized_app  ← Appears as PID 1!
PID 2:    child_process
```

**Key properties:**
- **First process in namespace gets PID 1** (appears as "init")
- Processes inside **cannot see** processes outside
- Processes outside **can see** processes inside (with different PIDs)
- Parent namespace has a "view" into child namespace

**Why this matters:**
- Container's main process thinks it's PID 1 (like in a VM)
- If PID 1 dies, all processes in namespace are killed
- Container can't see or signal host processes

**Example:**
```bash
# On host
$ ps aux | grep nginx
root     500  0.0  0.1  nginx: master

# Inside container
$ ps aux
PID   USER     COMMAND
1     root     nginx: master    ← Same process, different PID!
2     root     nginx: worker
```

---

### NET Namespace: Network Isolation

**What it isolates:** Network devices, IP addresses, routing tables, firewall rules

```
┌─────────────────────────────────────────────────────────┐
│ Host Network Namespace                                  │
│ ├─ eth0 (192.168.1.100)                                │
│ ├─ lo (127.0.0.1)                                      │
│ └─ Routing table, iptables rules                       │
└─────────────────────────────────────────────────────────┘
         │
         │ veth pair (virtual ethernet cable)
         │
┌─────────────────────────────────────────────────────────┐
│ Container Network Namespace                             │
│ ├─ eth0 (10.0.0.5) ← Different IP!                     │
│ ├─ lo (127.0.0.1)                                      │
│ └─ Own routing table, iptables                         │
└─────────────────────────────────────────────────────────┘
```

**Key properties:**
- Each namespace has its own:
  - Network interfaces (no `eth0` conflict)
  - IP addresses (can reuse 10.0.0.1 in multiple containers)
  - Routing tables
  - Firewall rules (iptables/nftables)
- Namespaces connected via **veth pairs** (virtual ethernet cables)

**Why this matters:**
- Each container gets its own network stack
- No IP address conflicts between containers
- Container networking isolated from host

---

### MNT Namespace: Filesystem Isolation

**What it isolates:** Mount points (what filesystems are mounted where)

```
Host Filesystem:
/
├─ /bin
├─ /etc
├─ /home
└─ /var

Container Filesystem (MNT namespace):
/  ← Container's root (actually /var/lib/containers/xyz on host)
├─ /bin
├─ /etc  ← Container's own /etc!
├─ /app
└─ /tmp
```

**Key properties:**
- Container has its own **mount table**
- Mounting a filesystem inside container doesn't affect host
- Container's "/" is actually a subdirectory on host
- Enables **chroot** on steroids

**Why this matters:**
- Container sees only its own files
- Can't access host's /etc, /home, etc. (unless explicitly mounted)
- Basis for container image filesystem isolation

---

### UTS Namespace: Hostname Isolation

**UTS** = **UNIX Time-Sharing** (historical name from early UNIX systems)

**What it isolates:** Hostname and domain name

```
Host:
$ hostname
datacenter-node-01.example.com

Container:
$ hostname
web-container-abc123
```

**Key properties:**
- Simple but important: each container can have its own hostname
- Useful for distributed systems (service discovery uses hostname)

---

### IPC Namespace: Inter-Process Communication Isolation

**What it isolates:** System V IPC objects, POSIX message queues

**IPC mechanisms isolated:**
- Shared memory segments
- Semaphores
- Message queues

**Why this matters:**
- Prevents processes in different containers from communicating via IPC
- Security: container can't spy on host's shared memory

---

### USER Namespace: User ID Mapping

**What it isolates:** User IDs and group IDs (UIDs/GIDs)

**The magic:** Root inside container is **not** root outside!

```
Outside Container (host):
UID 0:     root (god mode)
UID 1000:  alice
UID 100000: (mapped to container's UID 0)

Inside Container:
UID 0:     root  ← Appears as root! (actually UID 100000 on host)
UID 1:     nginx
```

**Key properties:**
- **UID mapping**: Container's UID 0 maps to unprivileged UID on host
- Even if container process thinks it's root, it's not root on host
- Critical security feature

**Why this matters:**
- Container escape: even if attacker becomes root in container, they're not root on host
- **Rootless containers** rely on this (run containers as non-root user)

---

### CGROUP Namespace: Control Group View Isolation

**What it isolates:** View of the cgroup hierarchy

**Purpose:** Container sees itself at root of cgroup tree

```
Host's view:
/sys/fs/cgroup/
├─ cpu/
│  ├─ docker/
│  │  └─ container123/  ← Container's cgroup
│  └─ system.slice/

Container's view:
/sys/fs/cgroup/
└─ cpu/  ← Appears as root!
```

**Why this matters:**
- Container can't see or modify other containers' cgroups
- Security: prevents container from adjusting resource limits of others

---

## Part 2: cgroups - Resource Control

### What are cgroups?

**Control Groups (cgroups)** limit and account for resource usage of process groups.

**Namespaces answer:** "What can you see?"
**cgroups answer:** "How much can you use?"

### cgroups Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ cgroup Hierarchy                                        │
│                                                          │
│ Root cgroup                                             │
│  ├─ /system.slice (system services)                    │
│  ├─ /user.slice (user sessions)                        │
│  └─ /docker                                             │
│      ├─ /container1  ← 2 CPU cores, 4GB RAM max       │
│      └─ /container2  ← 1 CPU core, 2GB RAM max        │
└─────────────────────────────────────────────────────────┘
```

**Each cgroup can limit:**

```
┌──────────────────┬─────────────────────────────────────┐
│ RESOURCE         │ WHAT IT CONTROLS                    │
├──────────────────┼─────────────────────────────────────┤
│ cpu              │ CPU time (shares, quotas)           │
│ memory           │ RAM usage (limits, OOM behavior)    │
│ blkio            │ Block device I/O (disk bandwidth)   │
│ cpuset           │ CPU/NUMA node pinning               │
│ devices          │ Device access (which devices)       │
│ freezer          │ Suspend/resume processes            │
│ net_cls/net_prio │ Network traffic classification      │
│ pids             │ Number of processes (fork bomb)     │
└──────────────────┴─────────────────────────────────────┘
```

---

### cgroups v1 vs v2

**cgroups v1** (legacy):
- Multiple hierarchies (one per resource type)
- Complex to manage
- Inconsistent semantics across controllers

**cgroups v2** (modern, default since systemd 226):
- **Single unified hierarchy**
- Consistent semantics
- Better resource distribution
- **Preferred for new deployments**

```
cgroups v1 (multiple hierarchies):
/sys/fs/cgroup/cpu/docker/container1
/sys/fs/cgroup/memory/docker/container1
/sys/fs/cgroup/blkio/docker/container1

cgroups v2 (unified hierarchy):
/sys/fs/cgroup/docker/container1
  ├─ cpu.max (CPU limit)
  ├─ memory.max (RAM limit)
  └─ io.max (I/O limit)
```

---

### CPU Limiting Example

**Scenario:** Limit container to 50% of one CPU core

**cgroups v2:**
```bash
# Create cgroup
mkdir /sys/fs/cgroup/mycontainer

# Set CPU quota: 50000 microseconds out of every 100000 (50%)
echo "50000 100000" > /sys/fs/cgroup/mycontainer/cpu.max

# Add process to cgroup
echo $PID > /sys/fs/cgroup/mycontainer/cgroup.procs
```

**What happens:**
- Process runs normally until it uses 50% of a core
- Kernel **throttles** the process for remainder of 100ms period
- Next period (100ms later), process can run again

**Visible effect:**
```bash
# Without cgroup
$ stress --cpu 1
# CPU usage: 100%

# With cgroup (50% limit)
$ stress --cpu 1
# CPU usage: 50%  ← Throttled!
```

---

### Memory Limiting Example

**Scenario:** Limit container to 512MB RAM

```bash
# Set memory limit
echo "512M" > /sys/fs/cgroup/mycontainer/memory.max

# What happens when limit is exceeded?
# Depends on memory.oom.group setting:
# - Kill the process (OOM kill)
# - Or throttle by forcing disk swapping (if swap enabled)
```

**OOM Kill behavior:**
```bash
# Container tries to allocate 600MB when limited to 512MB
# Kernel log:
[ 1234.567] Memory cgroup out of memory: Killed process 5678 (myapp)
[ 1234.568] Task in /docker/container1 killed as a result of limit
```

**Critical for containers:** Prevents one container from consuming all RAM and starving others.

---

## Part 3: How Containers Use These Primitives

### Container = Namespaces + cgroups

```
Container Creation:
┌────────────────────────────────────────────────────────┐
│ 1. Create namespaces:                                 │
│    - PID namespace   (process isolation)              │
│    - NET namespace   (network isolation)              │
│    - MNT namespace   (filesystem isolation)           │
│    - UTS namespace   (hostname)                       │
│    - IPC namespace   (IPC isolation)                  │
│    - USER namespace  (UID mapping) - optional         │
│    - CGROUP namespace (cgroup view isolation)         │
│                                                        │
│ 2. Create cgroup:                                     │
│    /sys/fs/cgroup/docker/container_xyz                │
│                                                        │
│ 3. Set resource limits in cgroup:                     │
│    - cpu.max = 200000 100000  (2 cores)              │
│    - memory.max = 4G                                  │
│    - pids.max = 512                                   │
│                                                        │
│ 4. Place processes in:                                │
│    - Namespaces (unshare() syscall)                   │
│    - cgroup (echo $PID > cgroup.procs)                │
└────────────────────────────────────────────────────────┘
```

### Simple Container (Conceptually)

```bash
#!/bin/bash
# Simplified container creation (pseudo-code)

# 1. Create namespaces
unshare --pid --net --mount --uts --ipc \
  # 2. Set up cgroup
  cgcreate -g cpu,memory:mycontainer && \
  cgset -r cpu.max="100000 100000" mycontainer && \
  cgset -r memory.max=512M mycontainer && \

  # 3. Run process in namespace + cgroup
  cgexec -g cpu,memory:mycontainer \
    chroot /var/lib/containers/myapp /bin/bash
```

**What just happened:**
- `unshare`: Created isolated namespaces
- `cgcreate/cgset`: Set up resource limits
- `chroot`: Changed root filesystem
- Process now runs in its own world with resource limits!

---

## Part 4: Security Boundaries and Limitations

### What Containers DO Isolate

✅ **Process visibility** - Can't see other containers' processes
✅ **Filesystem** - Can't access other containers' files
✅ **Network** - Own IP addresses, ports, routing
✅ **Resource usage** - CPU/memory limits enforced
✅ **Hostname** - Own hostname/domain name

### What Containers DON'T Isolate

❌ **Kernel** - All containers share the same Linux kernel!
❌ **System calls** - Containers can make any syscall (unless restricted)
❌ **Kernel vulnerabilities** - Kernel exploit affects ALL containers
❌ **Hardware** - No hardware isolation (no EPT, no VMX)
❌ **Side channels** - Spectre/Meltdown affect all containers

### Critical Security Implications

**Container escape is easier than VM escape:**

```
VM Escape:
├─ Must break out of VMX non-root mode
├─ EPT protects memory
├─ IOMMU protects devices
└─ Extremely difficult (hardware barriers)

Container Escape:
├─ Just need kernel vulnerability
├─ Or misconfigured capability/seccomp
├─ Shared kernel = shared attack surface
└─ Much easier (software barriers only)
```

**Example vulnerabilities that don't affect VMs:**
- **Dirty COW** (CVE-2016-5195) - Kernel memory corruption
- **runc escape** (CVE-2019-5736) - Container runtime exploit
- **Kubernetes privilege escalation** - Misconfiguration attacks

**When VMs are better:**
- **Multi-tenant systems** (untrusted code)
- **Strong isolation required** (financial, healthcare)
- **Different kernel versions needed** (legacy apps)

**When containers are acceptable:**
- **Trusted code** (your own microservices)
- **Same trust domain** (internal apps)
- **Orchestration/density matters** (Kubernetes)

---

## Part 5: Comparison to Virtual Machine Isolation

### Architecture Comparison

```
VIRTUAL MACHINE ISOLATION:
┌───────────────────────────────────────────┐
│ VM 1                  VM 2                │
│ ┌─────────────┐      ┌─────────────┐     │
│ │ App         │      │ App         │     │
│ │ Guest OS    │      │ Guest OS    │     │ ← Separate kernels
│ └─────────────┘      └─────────────┘     │
│          VMX non-root mode                │
├───────────────────────────────────────────┤
│          Hypervisor (VMX root)            │ ← Hardware boundary
├───────────────────────────────────────────┤
│          Hardware (CPU, RAM, NIC)         │
└───────────────────────────────────────────┘

CONTAINER ISOLATION:
┌───────────────────────────────────────────┐
│ Container 1       Container 2             │
│ ┌─────────────┐  ┌─────────────┐         │
│ │ App         │  │ App         │         │
│ │ (namespace) │  │ (namespace) │         │ ← Namespace boundary
│ └─────────────┘  └─────────────┘         │
├───────────────────────────────────────────┤
│     Shared Linux Kernel                   │ ← Software boundary only!
├───────────────────────────────────────────┤
│     Hardware (CPU, RAM, NIC)              │
└───────────────────────────────────────────┘
```

### Performance Comparison

```
┌────────────────────┬──────────────┬──────────────┐
│ METRIC             │ CONTAINER    │ VM           │
├────────────────────┼──────────────┼──────────────┤
│ Startup time       │ Milliseconds │ Seconds      │
│ Memory overhead    │ ~10 MB       │ ~100 MB+     │
│ Disk overhead      │ ~50 MB       │ ~1 GB+       │
│ CPU overhead       │ <1%          │ 2-5%         │
│ I/O performance    │ Near-native  │ Good (90-95%)│
│ Density (per host) │ 100s-1000s   │ 10s-100s     │
└────────────────────┴──────────────┴──────────────┘
```

### Security Comparison

```
┌────────────────────────┬──────────────┬──────────────┐
│ SECURITY ASPECT        │ CONTAINER    │ VM           │
├────────────────────────┼──────────────┼──────────────┤
│ Kernel isolation       │ ❌ Shared    │ ✅ Separate  │
│ Hardware isolation     │ ❌ None      │ ✅ EPT/IOMMU │
│ Escape difficulty      │ Medium       │ Very Hard    │
│ Multi-tenancy safe?    │ ⚠️  With care│ ✅ Yes       │
│ Trust boundary         │ Software     │ Hardware     │
└────────────────────────┴──────────────┴──────────────┘
```

---

## Quick Reference

### Namespace Types

| Namespace | Isolates | Created With |
|-----------|----------|--------------|
| PID | Process IDs | `unshare --pid` |
| NET | Network stack | `unshare --net` |
| MNT | Mount points | `unshare --mount` |
| UTS | Hostname | `unshare --uts` |
| IPC | IPC resources | `unshare --ipc` |
| USER | UID/GID mapping | `unshare --user` |
| CGROUP | cgroup view | `unshare --cgroup` |

### cgroups v2 Limits

| Resource | Control File | Example |
|----------|--------------|---------|
| CPU | `cpu.max` | `100000 100000` (1 core) |
| Memory | `memory.max` | `512M` |
| I/O | `io.max` | Device-specific |
| PIDs | `pids.max` | `512` |

### Key Commands

```bash
# List namespaces for process
ls -la /proc/$PID/ns/

# Create all namespaces
unshare --pid --net --mount --uts --ipc --user --fork /bin/bash

# View cgroup membership
cat /proc/$PID/cgroup

# Show cgroup resource usage
cat /sys/fs/cgroup/docker/container1/cpu.stat
```

---

## What You've Learned

✅ **Namespaces provide isolation** - 7 types isolating different resources
✅ **cgroups provide resource limits** - CPU, memory, I/O, PIDs
✅ **Containers = namespaces + cgroups** - Software-based isolation
✅ **Shared kernel** - All containers run on same kernel
✅ **Security tradeoffs** - Faster and lighter than VMs, but weaker isolation
✅ **Use case alignment** - Containers for trusted code, VMs for strong isolation

---

## Next Steps

**Continue learning:**
→ [Union Filesystems](02_union_filesystems.md) - How container images work with layers
→ [Container vs VM Deep Dive](03_container_vs_vm.md) - When to use each

**Related topics:**
→ [The Ring-0 Problem](../../01_foundations/01_virtualization_basics/01_the_ring0_problem.md) - Why VMs need hardware support
→ [VM Exit Basics](../../01_foundations/01_virtualization_basics/03_vm_exit_basics.md) - Compare to container syscall overhead
