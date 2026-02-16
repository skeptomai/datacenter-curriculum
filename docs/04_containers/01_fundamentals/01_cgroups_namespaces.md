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

**The Three Pillars:**
1. **Namespaces** - Isolation (what you can see)
2. **cgroups** - Resource limits (what you can use)
3. **Capabilities** - Privilege control (what you can do)

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

**What is a veth pair?**

A **veth (virtual ethernet) pair** acts like a virtual network cable connecting two network namespaces:
- Creates two connected network interfaces (both are kernel devices)
- One end typically placed in the container's namespace
- Other end stays in the host's namespace (attached to a bridge)
- Packets sent to one end immediately appear at the other end

**veth vs TAP/TUN (used for VMs):**
- **TAP/TUN**: Bridges kernel and userspace process
  - One end is a file descriptor that userspace programs (like QEMU) read/write
  - Used for VMs: hypervisor reads packets from TAP device
- **veth**: Connects two kernel network namespaces
  - Both ends are kernel devices (no userspace involved)
  - Used for containers: kernel-to-kernel forwarding
  - Lower overhead than TAP/TUN

**Why this matters:**
- Each container gets its own network stack
- No IP address conflicts between containers
- Container networking isolated from host
- Veth pairs provide the "bridge" between isolated container and host network

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

**But wait... how DO containers communicate then?**

Good question! IPC namespace isolation is the **secure default**, but real-world containers need communication. Here are the safe methods:

#### 1. Network Communication (Most Common)

Containers communicate over TCP/IP, even on the same host:

```
Container A (10.0.0.2:8080)
    ↓ TCP socket
Container B (10.0.0.3:3000)
```

**Why this is secure:**
- ✅ Network stack has access controls (firewall rules, network policies)
- ✅ Works across hosts (scalable to distributed systems)
- ✅ Well-understood security model (TLS, authentication)
- ✅ Can be monitored and logged

**When to use:** Default choice, especially for microservices

#### 2. Shared Volumes (Very Common)

Containers mount the same volume for file-based communication:

```
Container A writes → /shared/data.json
Container B reads  ← /shared/data.json
```

**Why this is secure:**
- ✅ Filesystem permissions control access
- ✅ Explicit configuration required (no accidents)
- ✅ Can be read-only for consumers

**When to use:**
- Sidecar patterns (log shippers reading app logs)
- Configuration sharing
- Data processing pipelines

#### 3. Unix Domain Sockets via Shared Volumes (Efficient)

More efficient than TCP for same-host communication:

```
Container A creates socket → /shared/app.sock
Container B connects to    ← /shared/app.sock
```

**Why this is secure:**
- ✅ Filesystem permissions control access
- ✅ Lower overhead than TCP (no network stack)
- ✅ Can't be accessed remotely (host-local only)

**When to use:**
- High-performance local communication
- Docker daemon communication (Docker socket)
- Database connections

#### 4. Explicitly Shared IPC Namespace (Trusted Containers)

Containers CAN share IPC namespace when needed:

```bash
# Docker: Share IPC namespace between containers
docker run --name app1 myapp
docker run --ipc=container:app1 myapp-sidecar

# Kubernetes: All containers in a Pod share IPC namespace
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
  - name: sidecar  # Shares IPC with app!
```

**Why this is secure:**
- ✅ Explicit opt-in (not accidental)
- ✅ Only between trusted containers
- ✅ Kubernetes pods use this by design

**When to use:**
- Tightly coupled containers (Kubernetes pods)
- Shared memory for performance-critical paths
- Legacy apps requiring System V IPC

#### Security Comparison

```
┌──────────────────────┬──────────┬────────────────────────┐
│ METHOD               │ OVERHEAD │ SECURITY ISOLATION     │
├──────────────────────┼──────────┼────────────────────────┤
│ Network (TCP/IP)     │ Medium   │ ✅ High (firewalls)    │
│ Unix domain socket   │ Low      │ ✅ High (permissions)  │
│ Shared volume        │ Low      │ ✅ High (permissions)  │
│ Shared IPC namespace │ Lowest   │ ⚠️  Trusted only       │
└──────────────────────┴──────────┴────────────────────────┘
```

**Key insight:** Networking isn't the ONLY secure method—it's just the most universal and scalable. For same-host communication, Unix sockets and shared volumes are equally secure and often more efficient.

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

## Part 3: Linux Capabilities - Privilege Control

### The Root Problem

Traditional UNIX had only two privilege levels:
- **UID 0 (root)**: Can do EVERYTHING (kill any process, load kernel modules, change network config, etc.)
- **UID != 0 (non-root)**: Restricted access

**Problem for containers:** Many containers run as root (UID 0) inside the namespace, but we don't want them to have ALL root powers.

### What are Linux Capabilities?

**Linux capabilities divide root privileges into 40+ fine-grained permissions.**

Instead of "all or nothing," processes can have specific capabilities:

```
Traditional UNIX:
┌──────────────────────────────────────┐
│ Root (UID 0): ALL PRIVILEGES         │
│ - Change network config              │
│ - Load kernel modules                │
│ - Kill any process                   │
│ - Bypass file permissions            │
│ - Change system time                 │
│ - ... (everything)                   │
└──────────────────────────────────────┘
        vs
┌──────────────────────────────────────┐
│ Non-root: NO PRIVILEGES              │
└──────────────────────────────────────┘

Linux Capabilities:
┌──────────────────────────────────────┐
│ Process with CAP_NET_ADMIN only:     │
│ ✅ Change network config             │
│ ❌ Load kernel modules               │
│ ❌ Kill processes                    │
│ ❌ Bypass file permissions           │
└──────────────────────────────────────┘
```

**Key insight:** A process can be root (UID 0) but have limited capabilities!

---

### Important Capabilities

```
┌─────────────────┬──────────────────────────────────────────┐
│ CAPABILITY      │ ALLOWS                                   │
├─────────────────┼──────────────────────────────────────────┤
│ CAP_CHOWN       │ Change file ownership                    │
│ CAP_DAC_OVERRIDE│ Bypass file read/write/execute checks    │
│ CAP_FOWNER      │ Bypass permission checks on operations   │
│ CAP_KILL        │ Send signals to any process              │
│ CAP_SETUID      │ Change UID (e.g., drop privileges)       │
│ CAP_SETGID      │ Change GID                               │
│ CAP_NET_BIND_SVC│ Bind to ports < 1024                     │
│ CAP_NET_RAW     │ Use RAW and PACKET sockets (ping)        │
│ CAP_NET_ADMIN   │ Network config (routes, firewall, IPs)   │
│ CAP_SYS_CHROOT  │ Use chroot()                             │
│ CAP_SYS_PTRACE  │ Trace/debug any process (strace, gdb)    │
│ CAP_SYS_ADMIN   │ Many admin operations (DANGEROUS)        │
│ CAP_SYS_MODULE  │ Load/unload kernel modules               │
│ CAP_SYS_TIME    │ Change system clock                      │
└─────────────────┴──────────────────────────────────────────┘
```

**See all 40+ capabilities:** `man capabilities`

---

### Default Container Capabilities

**Docker/containerd default set (14 capabilities):**

```
✅ Containers GET by default:
  CAP_CHOWN           - Change file ownership
  CAP_DAC_OVERRIDE    - Bypass file permissions
  CAP_FOWNER          - File operations as owner
  CAP_FSETID          - Set file capabilities
  CAP_KILL            - Send signals
  CAP_SETGID          - Change GID
  CAP_SETUID          - Change UID
  CAP_SETPCAP         - Modify process capabilities
  CAP_NET_BIND_SERVICE- Bind ports < 1024
  CAP_NET_RAW         - Use raw sockets (ping works!)
  CAP_SYS_CHROOT      - Use chroot
  CAP_MKNOD           - Create special files
  CAP_AUDIT_WRITE     - Write to audit log
  CAP_SETFCAP         - Set file capabilities

❌ Containers DON'T GET by default:
  CAP_NET_ADMIN       - Network configuration
  CAP_SYS_ADMIN       - System administration (VERY POWERFUL)
  CAP_SYS_MODULE      - Kernel modules
  CAP_SYS_PTRACE      - Process tracing
  CAP_SYS_TIME        - Change system time
  CAP_SYS_BOOT        - Reboot system
  ... (26+ more dangerous capabilities)
```

**Why this matters:**
- Container runs as root (UID 0) inside
- But can't change network config (no CAP_NET_ADMIN)
- Can't load kernel modules (no CAP_SYS_MODULE)
- Can't debug host processes (no CAP_SYS_PTRACE)
- **This is a key security boundary!**

---

### Checking Container Capabilities

```bash
# Docker: See capabilities of running container
docker inspect <container> | grep -A 20 "CapAdd"

# Inside container: Check current process capabilities
capsh --print

# Or decode capability bitmask
grep Cap /proc/self/status
# CapEff: 00000000a80425fb  ← Bitmask of effective capabilities

# Decode with capsh
capsh --decode=00000000a80425fb
```

**Example output:**
```
Current: cap_chown,cap_dac_override,cap_fowner,cap_fsetid,
         cap_kill,cap_setgid,cap_setuid,cap_setpcap,
         cap_net_bind_service,cap_net_raw,cap_sys_chroot,
         cap_mknod,cap_audit_write,cap_setfcap=eip
```

---

### Common Scenarios Requiring Additional Capabilities

#### Scenario 1: Network Tools (traceroute, tcpdump, VPN)

```bash
# Problem: Network tool needs to configure network
docker run alpine ip link set eth0 mtu 1400
# Error: Operation not permitted

# Solution: Add CAP_NET_ADMIN
docker run --cap-add=NET_ADMIN alpine ip link set eth0 mtu 1400
# Success!
```

**Use cases:**
- VPN containers (OpenVPN, WireGuard)
- Network monitoring (tcpdump, Wireshark)
- Custom routing (multi-homed containers)
- Network debugging tools

#### Scenario 2: Debugging Tools (strace, gdb)

```bash
# Problem: Can't trace processes
docker run alpine strace -p 1
# Error: Operation not permitted

# Solution: Add CAP_SYS_PTRACE
docker run --cap-add=SYS_PTRACE alpine strace -p 1
```

**Use cases:**
- Debugging containers (strace, gdb, perf)
- Profiling tools
- Security analysis

#### Scenario 3: Time Synchronization (NTP servers)

```bash
# Problem: Can't change system time
docker run alpine date -s "2024-01-01 12:00:00"
# Error: Operation not permitted

# Solution: Add CAP_SYS_TIME
docker run --cap-add=SYS_TIME alpine date -s "2024-01-01 12:00:00"
```

**Use cases:**
- NTP server containers
- Time virtualization for testing

#### Scenario 4: Ping (already works!)

```bash
# This WORKS without extra capabilities (CAP_NET_RAW is default)
docker run alpine ping -c 1 8.8.8.8
# 64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=10.2 ms
```

---

### How to Modify Capabilities

#### Docker

```bash
# Add specific capability
docker run --cap-add=NET_ADMIN myimage

# Add multiple capabilities
docker run --cap-add=NET_ADMIN --cap-add=SYS_PTRACE myimage

# Drop specific capability (from defaults)
docker run --cap-drop=CHOWN myimage

# Drop all, add only what's needed (most secure)
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage

# DANGER: All capabilities (equivalent to --privileged for caps)
docker run --cap-add=ALL myimage

# DANGER: Privileged mode (disables ALL security)
docker run --privileged myimage
# ⚠️ Gives full access to host! Use only when absolutely necessary
```

#### Docker Compose

```yaml
services:
  vpn:
    image: openvpn
    cap_add:
      - NET_ADMIN
      - NET_RAW
    cap_drop:
      - ALL
```

#### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: network-tool
spec:
  containers:
  - name: nettools
    image: nicolaka/netshoot
    securityContext:
      capabilities:
        add:
          - NET_ADMIN
          - NET_RAW
        drop:
          - ALL
```

**Kubernetes defaults:** Same as Docker (14 capabilities)

---

### Security Best Practices

#### 1. Principle of Least Privilege

```bash
# ❌ BAD: Give all capabilities
docker run --cap-add=ALL myapp

# ✅ GOOD: Give only what's needed
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp
```

#### 2. Avoid CAP_SYS_ADMIN

**CAP_SYS_ADMIN is extremely powerful** (allows mounting filesystems, loading modules, and more).

```bash
# ❌ AVOID: CAP_SYS_ADMIN is almost as dangerous as --privileged
docker run --cap-add=SYS_ADMIN myapp

# ✅ BETTER: Find specific capability you need
# (Often you need CAP_NET_ADMIN, not CAP_SYS_ADMIN)
```

#### 3. Never use --privileged in Production

```bash
# ❌ NEVER IN PRODUCTION
docker run --privileged myapp
# Disables namespaces, capabilities, seccomp, AppArmor
# Container has full host access!
```

**When --privileged might be acceptable:**
- Local development/testing only
- Container needs direct hardware access (Docker-in-Docker, hardware drivers)
- Even then, prefer specific capabilities instead

---

### The Three Pillars of Container Security

```
Container Isolation:
┌────────────────────────────────────────────────┐
│ 1. NAMESPACES                                  │
│    "What can you see?"                         │
│    - Process isolation (PID)                   │
│    - Network isolation (NET)                   │
│    - Filesystem isolation (MNT)                │
├────────────────────────────────────────────────┤
│ 2. CGROUPS                                     │
│    "How much can you use?"                     │
│    - CPU limits                                │
│    - Memory limits                             │
│    - I/O limits                                │
├────────────────────────────────────────────────┤
│ 3. CAPABILITIES                                │
│    "What can you do?"                          │
│    - Network configuration                     │
│    - File operations                           │
│    - Process control                           │
└────────────────────────────────────────────────┘

Plus: seccomp (syscall filtering), AppArmor/SELinux
```

**All three work together:**
- **Namespaces** isolate resources
- **cgroups** limit resources
- **Capabilities** restrict privileges
- Even if container is root, it can't escape without all three being misconfigured!

---

## Part 4: How Containers Use These Primitives

### Container = Namespaces + cgroups + Capabilities

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
│ 4. Set capabilities:                                  │
│    - Start with default 14 capabilities               │
│    - Add: CAP_NET_ADMIN (if needed)                   │
│    - Drop: CAP_CHOWN (if not needed)                  │
│                                                        │
│ 5. Place processes in:                                │
│    - Namespaces (unshare() syscall)                   │
│    - cgroup (echo $PID > cgroup.procs)                │
│    - Apply capabilities (capset() syscall)            │
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

## Part 5: Hands-On with `unshare`

### What is `unshare`?

**`unshare`** is a Linux utility that runs a program with some **namespaces unshared** from the parent process. It's a wrapper around the `unshare()` system call—the same syscall container runtimes use to create isolated environments.

**The concept:**
```
Normal process (fork):
Parent process (PID ns 1, NET ns 1)
  └─ Child process (PID ns 1, NET ns 1) ← Inherits all namespaces

With unshare:
Parent process (PID ns 1, NET ns 1)
  └─ Child process (PID ns 2, NET ns 2) ← New namespaces!
```

**Why learn unshare?**
- Understand how containers really work under the hood
- Create isolated environments without Docker
- Debug namespace issues
- Build custom isolation solutions

---

### The `unshare()` System Call

**C API:**
```c
#include <sched.h>

int unshare(int flags);

// Flags specify which namespaces to unshare:
CLONE_NEWPID    // PID namespace
CLONE_NEWNET    // Network namespace
CLONE_NEWNS     // Mount namespace
CLONE_NEWUTS    // UTS (hostname) namespace
CLONE_NEWIPC    // IPC namespace
CLONE_NEWUSER   // User namespace
CLONE_NEWCGROUP // Cgroup namespace
```

**Command-line wrapper:**
```bash
unshare [options] [program [arguments]]

Options map to flags:
--pid       → CLONE_NEWPID
--net       → CLONE_NEWNET
--mount     → CLONE_NEWNS
--uts       → CLONE_NEWUTS
--ipc       → CLONE_NEWIPC
--user      → CLONE_NEWUSER
--cgroup    → CLONE_NEWCGROUP

Special options:
--fork              # Fork before executing (required for PID!)
--map-root-user     # Map current user to root in user namespace
```

---

### Example 1: PID Namespace Isolation

**See all processes normally:**
```bash
$ ps aux | wc -l
247  # See all 247 processes on system
```

**Create isolated PID namespace:**
```bash
$ sudo unshare --pid --fork bash

# Inside new PID namespace (need to remount /proc)
$ mount -t proc proc /proc

$ ps aux
PID   USER     COMMAND
1     root     bash        ← This is PID 1 in our namespace!
15    root     ps aux
```

**What happened:**
1. `--pid` created new PID namespace
2. `--fork` forked so bash becomes PID 1 (required!)
3. Processes outside namespace are **invisible**
4. `/proc` shows only namespace processes

**Why `--fork` is required:**

```bash
# ❌ WITHOUT --fork:
$ sudo unshare --pid bash
$ echo $$
15432  # Still has parent namespace PID!

# ✅ WITH --fork:
$ sudo unshare --pid --fork bash
$ echo $$
1      # PID 1 in new namespace!
```

The process calling `unshare()` doesn't get a new PID. Only forked children get PIDs starting from 1.

---

### Example 2: Network Namespace Isolation

**Create isolated network:**
```bash
$ sudo unshare --net bash

# Inside network namespace
$ ip addr
1: lo: <LOOPBACK> state DOWN
    # Only loopback exists, no eth0!

$ ip link
1: lo: <LOOPBACK> state DOWN
    # No network interfaces!

$ ping 8.8.8.8
connect: Network is unreachable

# Exit back to parent namespace
$ exit

$ ip addr
1: lo: <LOOPBACK,UP> state UP
2: eth0: <BROADCAST,UP> state UP
    inet 192.168.1.100/24
    # Parent's interfaces back!
```

**Practical use case - test isolation:**
```bash
# Ensure tests don't make real network calls
sudo unshare --net pytest tests/network/

# Only localhost (127.0.0.1) available
# Any attempt to reach internet fails
```

---

### Example 3: Mount Namespace (Filesystem Isolation)

**Isolate filesystem mounts:**
```bash
$ sudo unshare --mount bash

# Inside mount namespace
$ mount -t tmpfs tmpfs /mnt
$ echo "namespace-only data" > /mnt/test.txt
$ ls /mnt/
test.txt

# Exit namespace
$ exit

# Back in parent
$ ls /mnt/
# Empty! Mount was isolated
```

**Practical example - safe script testing:**
```bash
# Test installation script without affecting host
sudo unshare --mount bash -c '
  # Make mounts private (prevent propagation)
  mount --make-rprivate /

  # Create fake root
  mount -t tmpfs tmpfs /tmp/fake-root

  # Test install script
  ./dangerous-install.sh

  # Changes only affect this namespace!
'
# Host filesystem untouched
```

---

### Example 4: Hostname Isolation (UTS Namespace)

**Change hostname without affecting host:**
```bash
$ hostname
my-laptop

$ sudo unshare --uts bash

# Inside UTS namespace
$ hostname my-container
$ hostname
my-container

# Exit
$ exit

$ hostname
my-laptop  # Parent hostname unchanged!
```

---

### Example 5: Creating a "Mini Container"

**Combine all namespaces:**
```bash
sudo unshare \
  --pid --fork \
  --net \
  --mount \
  --uts \
  --ipc \
  bash -c '
    # Set hostname
    hostname mini-container

    # Mount /proc for new PID namespace
    mount -t proc proc /proc

    # Bring up loopback
    ip link set lo up

    # Show isolation
    echo "=== Hostname ==="
    hostname

    echo "=== Processes ==="
    ps aux

    echo "=== Network ==="
    ip addr

    # Interactive shell
    bash
'
```

**This is essentially what Docker does!** (Plus cgroups, capabilities, seccomp, AppArmor, OverlayFS, and more orchestration)

---

### Example 6: Rootless Isolation with User Namespace

**Run as unprivileged user:**
```bash
$ id
uid=1000(alice) gid=1000(alice)

$ unshare --user --map-root-user bash

# Inside user namespace
$ id
uid=0(root) gid=0(root)  ← Appear as root!

$ whoami
root

# But try to do something privileged:
$ mount /dev/sda1 /mnt
mount: /mnt: permission denied.
# Not real root! Just mapped UID
```

**Check from parent namespace:**
```bash
# From another terminal:
$ ps aux | grep bash
alice  12345  ... bash    ← Still shows as 'alice', not root
```

**This is how rootless Docker works!**

---

### Common Gotchas and Solutions

#### Gotcha 1: `/proc` Shows Wrong Processes

**Problem:**
```bash
$ sudo unshare --pid --fork bash
$ ps aux
# Shows parent namespace processes! Wrong!
```

**Solution:** Remount `/proc`
```bash
$ sudo unshare --pid --fork bash
$ mount -t proc proc /proc
$ ps aux
# Now shows only namespace processes ✓
```

#### Gotcha 2: Mount Propagation

**Problem:** Mounts leak to parent namespace

```bash
$ sudo unshare --mount bash
$ mount /dev/sdb1 /mnt
# This might affect parent due to mount propagation!
```

**Solution:** Make mounts private
```bash
$ sudo unshare --mount bash
$ mount --make-rprivate /
$ mount /dev/sdb1 /mnt
# Now isolated ✓
```

#### Gotcha 3: User Namespace Without Mapping

**Problem:**
```bash
$ unshare --user bash
$ id
uid=65534(nobody) gid=65534(nogroup)
# You're "nobody"!
```

**Solution:** Use `--map-root-user`
```bash
$ unshare --user --map-root-user bash
$ id
uid=0(root) gid=0(root)  ✓
```

---

### Building a Manual Container Script

**Complete example - `manual-container.sh`:**

```bash
#!/bin/bash
# Create a minimal container using only unshare

set -e

CONTAINER_ROOT="/tmp/container-$(date +%s)"

echo "Creating container with root: $CONTAINER_ROOT"

# Create container root filesystem
mkdir -p "$CONTAINER_ROOT"/{bin,proc,sys,dev,tmp,etc}

# Copy essential binaries (simplified - real containers use full rootfs)
cp /bin/bash "$CONTAINER_ROOT/bin/"
cp /bin/ls "$CONTAINER_ROOT/bin/"
cp /bin/ps "$CONTAINER_ROOT/bin/"

# Copy required libraries
mkdir -p "$CONTAINER_ROOT/lib/x86_64-linux-gnu"
for lib in $(ldd /bin/bash | grep -o '/lib.*\s' | tr -d ' '); do
  cp "$lib" "$CONTAINER_ROOT/lib/x86_64-linux-gnu/" 2>/dev/null || true
done

# Create minimal /etc/passwd
echo "root:x:0:0:root:/:/bin/bash" > "$CONTAINER_ROOT/etc/passwd"

# Launch container with all namespaces
sudo unshare \
  --pid --fork \
  --net \
  --mount \
  --uts \
  --ipc \
  bash -c "
    # Set hostname
    hostname mini-container

    # Mount proc, sys, dev
    mount -t proc proc $CONTAINER_ROOT/proc
    mount -t sysfs sys $CONTAINER_ROOT/sys
    mount -t tmpfs tmpfs $CONTAINER_ROOT/dev

    # Create essential /dev nodes
    mknod -m 666 $CONTAINER_ROOT/dev/null c 1 3
    mknod -m 666 $CONTAINER_ROOT/dev/zero c 1 5
    mknod -m 666 $CONTAINER_ROOT/dev/random c 1 8

    # Setup network
    ip link set lo up

    # Change root filesystem
    chroot $CONTAINER_ROOT /bin/bash -c '
      export PATH=/bin
      export PS1=\"[container] \$ \"

      echo \"=== Welcome to Mini Container ===\"
      echo \"Hostname: \$(hostname)\"
      echo \"Processes:\"
      ps aux
      echo \"\"
      echo \"Network:\"
      ip addr 2>/dev/null || echo \"(ip command not available)\"
      echo \"\"

      /bin/bash
    '
"

echo "Container exited. Cleaning up..."
sudo rm -rf "$CONTAINER_ROOT"
```

**Run it:**
```bash
$ chmod +x manual-container.sh
$ ./manual-container.sh
Creating container with root: /tmp/container-1704812345
=== Welcome to Mini Container ===
Hostname: mini-container
Processes:
PID   USER     COMMAND
1     root     bash
8     root     ps aux

[container] $ pwd
/
[container] $ ls
bin  dev  etc  proc  sys  tmp
[container] $ exit
Container exited. Cleaning up...
```

---

### Related Tools

#### `nsenter` - Enter Existing Namespace

**unshare vs nsenter:**
```bash
# unshare: CREATE new namespace
unshare --net bash

# nsenter: ENTER existing namespace
nsenter --target 12345 --net bash
         ↑ PID of process in target namespace
```

**Enter Docker container's namespace:**
```bash
# Get container PID
PID=$(docker inspect -f '{{.State.Pid}}' mycontainer)

# Enter all its namespaces
sudo nsenter --target $PID \
  --pid --net --mount --uts --ipc \
  bash
```

#### `ip netns` - Network Namespace Management

**High-level wrapper around unshare for network:**
```bash
# Create named network namespace
ip netns add testnet

# List namespaces
ip netns list

# Execute in namespace
ip netns exec testnet bash

# Delete namespace
ip netns delete testnet
```

Internally uses `unshare --net`, but manages namespace lifecycle and naming.

---

### How Container Runtimes Use `unshare()`

**Docker/containerd sequence:**

```
1. unshare(CLONE_NEWPID | CLONE_NEWNET | CLONE_NEWNS |
           CLONE_NEWUTS | CLONE_NEWIPC | CLONE_NEWUSER)
   └─ Create all namespaces

2. Setup cgroups
   └─ echo $PID > /sys/fs/cgroup/docker/container123/cgroup.procs

3. Drop capabilities
   └─ capset() to reduce privileges

4. Setup seccomp filter
   └─ prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ...)

5. Apply AppArmor/SELinux profile
   └─ aa_change_profile() or setexeccon()

6. Mount container filesystem (OverlayFS)
   └─ mount("overlay", ..., lowerdir=..., upperdir=...)

7. chroot to container root
   └─ chroot("/var/lib/docker/overlay2/xyz/merged")

8. exec() container process
   └─ execve("/app/myapp", ...)
```

**The `unshare()` call is just the first step** in container creation!

---

### Debugging Real Containers with `unshare` Knowledge

**See what namespaces a process is in:**
```bash
$ docker run -d --name test nginx
$ PID=$(docker inspect -f '{{.State.Pid}}' test)

# Check process namespaces
$ ls -la /proc/$PID/ns/
lrwxrwxrwx 1 root root 0 cgroup -> cgroup:[4026532198]
lrwxrwxrwx 1 root root 0 ipc -> ipc:[4026532196]
lrwxrwxrwx 1 root root 0 mnt -> mnt:[4026532194]
lrwxrwxrwx 1 root root 0 net -> net:[4026532199]
lrwxrwxrwx 1 root root 0 pid -> pid:[4026532197]
lrwxrwxrwx 1 root root 0 uts -> uts:[4026532195]

# Numbers are namespace IDs - different from host!
```

**Compare to host namespaces:**
```bash
$ ls -la /proc/self/ns/
# Different namespace IDs = isolated!
```

---

## Part 6: Security Boundaries and Limitations

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

## Part 7: Comparison to Virtual Machine Isolation

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
✅ **Capabilities provide privilege control** - Fine-grained root permissions
✅ **Containers = namespaces + cgroups + capabilities** - Software-based isolation
✅ **Container communication** - Network, shared volumes, Unix sockets, or shared IPC namespace
✅ **Shared kernel** - All containers run on same kernel
✅ **Security tradeoffs** - Faster and lighter than VMs, but weaker isolation
✅ **Use case alignment** - Containers for trusted code, VMs for strong isolation

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[Containers from Scratch](https://ericchiang.github.io/post/containers-from-scratch/)** - Build a minimal container runtime to understand namespaces and cgroups from first principles
- **[bocker](https://github.com/p8952/bocker)** - Docker implementation in ~100 lines of bash demonstrating the core primitives
- **[Linux Programmer's Manual](https://man7.org/linux/man-pages/man7/namespaces.7.html)** - Official documentation for namespaces and cgroups syscalls

---

## Next Steps

**Continue learning:**
→ [Union Filesystems](02_union_filesystems.md) - How container images work with layers
→ [Container vs VM Deep Dive](03_container_vs_vm.md) - When to use each

**Related topics:**
→ [The Ring-0 Problem](../../01_foundations/01_virtualization_basics/01_the_ring0_problem.md) - Why VMs need hardware support
→ [VM Exit Basics](../../01_foundations/01_virtualization_basics/03_vm_exit_basics.md) - Compare to container syscall overhead
