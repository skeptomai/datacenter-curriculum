---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 04_containers/01_fundamentals/03_container_vs_vm.md
  - 04_containers/02_runtimes/01_runtime_landscape.md
next_recommended:
  - 04_containers/02_runtimes/04_runtime_comparison.md
  - 05_specialized/03_serverless/02_firecracker_deep_dive.md
tags: [containers, kata, gvisor, security, isolation, vm, userspace-kernel]
---

# Kata Containers and gVisor: Secure Container Runtimes

**Learning Objectives:**
- Understand why standard containers have security limitations
- Explain how Kata Containers provides VM-level isolation
- Describe gVisor's userspace kernel approach
- Compare security vs performance tradeoffs
- Determine when to use secure runtimes

---

## Introduction: The Container Security Problem

From [Container vs VM comparison](../01_fundamentals/03_container_vs_vm.md), we learned:

**Standard containers share the kernel:**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Container 1 │  │ Container 2 │  │ Container 3 │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       └─────────────────┼─────────────────┘
              ┌──────────▼──────────┐
              │  Shared Kernel      │ ← Single attack surface!
              └─────────────────────┘
```

**Problem:**
- Kernel vulnerability affects **all** containers
- Container escape = host compromise
- Not suitable for untrusted/multi-tenant workloads

**Question:** Can we get container speed + VM security?

**Answer:** Yes! Two approaches:
1. **Kata Containers** - Run each container in a lightweight VM
2. **gVisor** - Intercept syscalls with userspace kernel

---

## Part 1: Kata Containers

### What is Kata Containers?

**Concept:** Each "container" is actually a lightweight VM

```
Traditional Container:
┌─────────────────────────────────────────────────────┐
│ Host Kernel                                         │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Container 1  │  │ Container 2  │                │
│  │ (namespace)  │  │ (namespace)  │                │
│  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────┘

Kata Container:
┌─────────────────────────────────────────────────────┐
│ Host                                                │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ Micro VM 1     │  │ Micro VM 2     │            │
│  │ ┌────────────┐ │  │ ┌────────────┐ │            │
│  │ │ Container  │ │  │ │ Container  │ │            │
│  │ │ Guest      │ │  │ │ Guest      │ │  ← Separate kernels!
│  │ │ Kernel     │ │  │ │ Kernel     │ │            │
│  │ └────────────┘ │  │ └────────────┘ │            │
│  └────────────────┘  └────────────────┘            │
│         Hypervisor (KVM/Firecracker)                │
└─────────────────────────────────────────────────────┘
```

**Key insight:** Kata provides **VM isolation** with **container UX** (Docker/Kubernetes compatibility).

---

### Kata Architecture

```
┌─────────────────────────────────────────────────────┐
│ Container Orchestrator (Kubernetes, Docker)         │
└─────────────────┬───────────────────────────────────┘
                  │ CRI / OCI
┌─────────────────▼───────────────────────────────────┐
│ Kata Runtime (kata-runtime)                         │
│ - OCI-compatible interface                          │
│ - Translates container → VM                         │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┴──────────────┐
    │                            │
┌───▼─────────────┐   ┌──────────▼──────────┐
│ Kata Shim       │   │ VMM (Hypervisor)    │
└───┬─────────────┘   │ - QEMU              │
    │                 │ - Firecracker       │
    │                 │ - Cloud Hypervisor  │
    │                 │ - ACRN              │
    │                 └──────────┬──────────┘
    │                            │
┌───▼────────────────────────────▼──────────┐
│ Kata Micro VM                             │
│ ┌───────────────────────────────────────┐ │
│ │ Kata Agent                            │ │ ← Guest component
│ │ - Manages container lifecycle         │ │
│ │ - Communicates with shim (virtio-vsock)│ │
│ └───────────────────────────────────────┘ │
│ ┌───────────────────────────────────────┐ │
│ │ Guest Kernel (optimized)              │ │
│ │ - Minimal kernel (~4.19+ or 5.x)      │ │
│ │ - Fast boot (<1 second)               │ │
│ └───────────────────────────────────────┘ │
│ ┌───────────────────────────────────────┐ │
│ │ Container Process                     │ │
│ │ (your application)                    │ │
│ └───────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

---

### How Kata Works

**Step 1: Create VM instead of namespace**
```
Standard runc:
  unshare(CLONE_NEWPID | CLONE_NEWNET | ...)  ← Create namespaces

Kata:
  launch_vm(kernel, rootfs, resources)         ← Create micro VM
```

**Step 2: Boot guest kernel**
```
Kata VM boot sequence:
1. VMM starts (QEMU/Firecracker)
2. Load minimal kernel
3. Mount root filesystem (9p or virtio-fs)
4. Start kata-agent in guest
5. Connect shim ↔ agent (via virtio-vsock)

Boot time: ~500ms - 1 second
```

**Step 3: Run container in VM**
```
Inside Kata VM:
┌────────────────────────────────────┐
│ Guest Kernel                       │
│  ┌──────────────┐                  │
│  │ Container    │  ← Still uses    │
│  │ (namespace)  │     namespaces!  │
│  └──────────────┘                  │
└────────────────────────────────────┘
```

**Why namespaces inside VM?**
- Kata can run **multiple containers per VM** (Kubernetes pod)
- Containers in same pod share VM, isolated by namespaces
- Containers in different pods get different VMs

---

### Kata Components

**1. kata-runtime**
- OCI-compatible runtime
- Decides which VMM to use
- Orchestrates VM lifecycle

**2. kata-shim**
- Bridges host ↔ VM communication
- Forwards stdin/stdout
- Reports container status

**3. kata-agent**
- Runs inside guest VM
- Creates containers (using namespaces)
- Manages processes

**4. VMM (choose one):**
- **QEMU** - Full-featured, mature
- **Firecracker** - AWS's microVM (see [Firecracker deep dive](../../05_specialized/03_serverless/02_firecracker_deep_dive.md))
- **Cloud Hypervisor** - Rust-based, modern
- **ACRN** - Embedded/IoT focused

---

### Kata Performance Characteristics

```
┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ METRIC           │ runc         │ Kata (QEMU)  │ Kata (FC)    │
├──────────────────┼──────────────┼──────────────┼──────────────┤
│ Cold start       │ 100 ms       │ ~1 second    │ ~500 ms      │
│ Memory overhead  │ ~5 MB        │ ~120 MB      │ ~20 MB       │
│ Disk overhead    │ Shared       │ +kernel/VM   │ +kernel/VM   │
│ CPU overhead     │ <1%          │ 2-3%         │ 1-2%         │
│ I/O performance  │ Near-native  │ Good (90%)   │ Good (90%)   │
│ Network latency  │ Minimal      │ +0.1-0.5 ms  │ +0.1-0.3 ms  │
└──────────────────┴──────────────┴──────────────┴──────────────┘
```

**Key tradeoffs:**
- ✅ **Security**: VM-level isolation
- ⚠️ **Memory**: ~100 MB per pod (vs ~10 MB for runc)
- ⚠️ **Startup**: ~10x slower than runc
- ⚠️ **Density**: Fewer pods per node

---

### When to Use Kata

✅ **Multi-tenant Kubernetes**
```
Example: Public cloud Kubernetes-as-a-Service
- Customer A and Customer B on same node
- Need strong isolation (different VMs)
- Kata prevents tenant-to-tenant attacks
```

✅ **Untrusted workloads**
```
Example: CI/CD running user code
- Users submit arbitrary code
- Code runs in Kata VM
- Even if code exploits kernel, only affects that VM
```

✅ **Compliance/regulatory**
```
Example: Financial services, healthcare
- Regulations require hardware isolation
- Kata provides VM boundary
- Meets audit requirements
```

❌ **NOT for:**
- Trusted internal workloads (unnecessary overhead)
- Development laptops (complexity, resources)
- High-density requirements (100s of containers per node)

---

## Part 2: gVisor

### What is gVisor?

**Concept:** Intercept syscalls with userspace "kernel"

```
Standard Container:
Application → syscall → Host Kernel

gVisor:
Application → syscall → gVisor Sentry → limited syscalls → Host Kernel
                         └─ Userspace "kernel" in Go
```

**Key insight:** Most syscalls never reach host kernel!

---

### gVisor Architecture

```
┌─────────────────────────────────────────────────────┐
│ Container (Sandbox)                                 │
│  ┌───────────────────────────────────────────────┐ │
│  │ Application Process                           │ │
│  │ (your code)                                   │ │
│  └─────────────────┬─────────────────────────────┘ │
│                    │ syscall (open, read, etc.)    │
│  ┌─────────────────▼─────────────────────────────┐ │
│  │ gVisor Sentry                                 │ │
│  │ - Userspace kernel written in Go              │ │
│  │ - Implements Linux syscalls                   │ │
│  │ - Has own network stack, filesystem           │ │
│  └─────────────────┬─────────────────────────────┘ │
│                    │ safe syscalls only            │
└────────────────────┼───────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │ Host Linux Kernel     │
         │ (minimal exposure)    │
         └───────────────────────┘
```

**Two components:**

1. **Sentry** - Userspace kernel
2. **Gofer** - Filesystem access proxy

---

### How gVisor Works

**Platform modes:**

**ptrace (default):**
```
1. Application makes syscall (e.g., open("/etc/passwd", ...))
   ↓
2. Kernel delivers PTRACE_SYSCALL trap to Sentry
   ↓
3. Sentry intercepts syscall
   ↓
4. Sentry implements syscall in userspace
   - open() → Sentry's virtual filesystem
   - read() → Sentry's VFS
   - write() → Sentry's VFS
   ↓
5. Sentry returns result to application
```

**KVM mode (faster):**
```
Uses VM-based syscall interception (similar concept to Kata but different approach)
- Guest code runs in KVM
- Syscalls trapped to Sentry (VMM mode)
- ~30% faster than ptrace
```

---

### Syscall Filtering

**gVisor implements ~200 of ~300+ Linux syscalls**

**Implemented syscalls (safe):**
```
open, close, read, write, stat, mmap, clone, execve, etc.
↓
Handled in Sentry's Go code
```

**Not implemented (rare/dangerous):**
```
mount, reboot, kexec_load, create_module, etc.
↓
Return ENOSYS (not supported)
```

**Result:** Reduced attack surface

```
┌──────────────────────────────────────────────────────┐
│ SYSCALL EXPOSURE │ Standard Container │ gVisor       │
├──────────────────┼────────────────────┼──────────────┤
│ Syscalls exposed │ ~300+              │ ~50-100      │
│ to host kernel   │                    │ (filtered)   │
└──────────────────┴────────────────────┴──────────────┘
```

---

### gVisor Components

**1. runsc (runtime)**
```
OCI-compatible runtime (like runc)
$ runsc run mycontainer
```

**2. Sentry**
```
The "kernel"
- Written in Go
- Implements syscalls
- Own network stack (netstack)
- Own virtual filesystem
- Signal handling
- Process management
```

**3. Gofer**
```
Filesystem access proxy
- Runs as separate process
- Handles actual file I/O
- Sandboxed with seccomp
```

**Architecture diagram:**
```
┌────────────────────────────────────┐
│ App container                      │
│   ↓ syscalls                       │
│ Sentry (userspace kernel)          │
│   ↓ filtered syscalls              │
└───┬───────────────────┬────────────┘
    │                   │
    │ safe syscalls     │ 9P protocol
    │                   │
┌───▼───────────┐  ┌────▼───────────┐
│ Host Kernel   │  │ Gofer          │
│ (minimal)     │  │ (file access)  │
└───────────────┘  └────┬───────────┘
                        │ actual file I/O
                   ┌────▼───────────┐
                   │ Host Kernel    │
                   └────────────────┘
```

---

### gVisor Performance

```
┌──────────────────┬──────────────┬──────────────────┐
│ METRIC           │ runc         │ gVisor (ptrace)  │
├──────────────────┼──────────────┼──────────────────┤
│ Cold start       │ 100 ms       │ 150 ms           │
│ Memory overhead  │ ~5 MB        │ ~15-30 MB        │
│ CPU-bound        │ 100%         │ 95-98%           │
│ Syscall-heavy    │ 100%         │ 60-80%           │
│ Network          │ 100%         │ 70-90%           │
│ Disk I/O         │ 100%         │ 50-70%           │
└──────────────────┴──────────────┴──────────────────┘
```

**Overhead reasons:**
- **ptrace**: Context switches between app and Sentry
- **Netstack**: Userspace TCP/IP stack (slower than kernel)
- **File I/O**: Goes through Gofer (extra process)

**KVM mode improves performance:**
- ~30% faster than ptrace
- Still slower than runc, but better than ptrace

---

### When to Use gVisor

✅ **Serverless/FaaS**
```
Example: Google Cloud Run
- User functions potentially malicious
- gVisor limits kernel exposure
- Faster startup than Kata (~150ms vs ~500ms)
```

✅ **Untrusted code with high density**
```
Example: Multi-tenant SaaS
- Need isolation but high density
- gVisor lighter than Kata (~15 MB vs ~120 MB)
- Can run 100s per node
```

✅ **Defense-in-depth**
```
Example: Financial applications
- Even trusted code benefits from syscall filtering
- Reduces kernel attack surface
- Complements other security (AppArmor, SELinux)
```

❌ **NOT for:**
- I/O-intensive workloads (databases, caches)
- Network-heavy applications (proxies, load balancers)
- Applications needing unsupported syscalls
- Applications expecting full Linux compatibility

---

## Part 3: Kata vs gVisor Comparison

### Architecture Comparison

```
┌────────────────────┬──────────────────┬──────────────────┐
│ ASPECT             │ Kata Containers  │ gVisor           │
├────────────────────┼──────────────────┼──────────────────┤
│ Isolation method   │ Hardware (VM)    │ Software (ptrace)│
│ Kernel             │ Separate guest   │ Userspace (Go)   │
│ Hardware required  │ VT-x/AMD-V       │ None (ptrace)    │
│ Linux compatibility│ 100%             │ ~70-80%          │
│ Syscall support    │ Full             │ ~200/300         │
└────────────────────┴──────────────────┴──────────────────┘
```

### Security Comparison

```
┌────────────────────┬──────────────────┬──────────────────┐
│ SECURITY           │ Kata             │ gVisor           │
├────────────────────┼──────────────────┼──────────────────┤
│ Kernel isolation   │ ✅ Separate      │ ⚠️  Shared       │
│ Syscall filtering  │ ❌ All allowed   │ ✅ Filtered      │
│ Escape difficulty  │ ✅ Very hard (VM)│ ⚠️  Medium       │
│ Attack surface     │ ✅ Minimal       │ ✅ Reduced       │
│ Hardware isolation │ ✅ Yes (EPT)     │ ❌ No            │
└────────────────────┴──────────────────┴──────────────────┘
```

**Security verdict:**
- **Kata**: Stronger (VM boundary)
- **gVisor**: Good (syscall filtering), but shared kernel

---

### Performance Comparison

```
┌────────────────────┬──────────────────┬──────────────────┐
│ PERFORMANCE        │ Kata (Firecracker)│ gVisor (ptrace) │
├────────────────────┼──────────────────┼──────────────────┤
│ Cold start         │ ~500 ms          │ ~150 ms          │
│ Memory per pod     │ ~20-120 MB       │ ~15-30 MB        │
│ CPU overhead       │ 1-3%             │ 5-30%            │
│ I/O performance    │ 90%              │ 50-70%           │
│ Network throughput │ 90%              │ 70-90%           │
│ Density (per host) │ 10s-50s          │ 100s             │
└────────────────────┴──────────────────┴──────────────────┘
```

**Performance verdict:**
- **Kata**: Better I/O, more memory
- **gVisor**: Better density, slower I/O

---

### Use Case Matrix

```
┌──────────────────────────┬──────────────┬──────────────┐
│ USE CASE                 │ Kata         │ gVisor       │
├──────────────────────────┼──────────────┼──────────────┤
│ Multi-tenant K8s         │ ✅ Best      │ ✅ Good      │
│ Serverless/FaaS          │ ✅ Good      │ ✅ Best      │
│ CI/CD untrusted code     │ ✅ Best      │ ⚠️  OK       │
│ Database workloads       │ ✅ OK        │ ❌ Slow I/O  │
│ High density needed      │ ⚠️  Limited  │ ✅ Best      │
│ Legacy apps              │ ✅ Best      │ ⚠️  May break│
│ Network-heavy (proxy)    │ ✅ Good      │ ⚠️  Slower   │
│ Compliance/audit         │ ✅ Best      │ ⚠️  Depends  │
└──────────────────────────┴──────────────┴──────────────┘
```

---

## Part 4: Hybrid Deployments

### Runtime Classes in Kubernetes

**Kubernetes supports multiple runtimes per cluster:**

```yaml
# RuntimeClass definitions
---
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata
handler: kata

---
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc

---
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: runc
handler: runc
```

**Use in pods:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: trusted-app
spec:
  runtimeClassName: runc  # Standard runtime
  containers:
  - name: app
    image: myapp:latest

---
apiVersion: v1
kind: Pod
metadata:
  name: untrusted-job
spec:
  runtimeClassName: kata  # Isolated in VM
  containers:
  - name: job
    image: user-submitted-code:latest
```

**Best practice:** Mix runtimes based on trust level
- **Trusted** internal apps → runc (fast, lightweight)
- **Untrusted** user code → Kata/gVisor (isolated)

---

## Quick Reference

### Kata Installation

```bash
# Install Kata
curl -fsSL https://github.com/kata-containers/kata-containers/releases/download/3.0.0/kata-static-3.0.0-x86_64.tar.xz | sudo tar -xvJf - -C /

# Configure containerd
cat <<EOF | sudo tee /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.kata]
  runtime_type = "io.containerd.kata.v2"
EOF

# Restart containerd
sudo systemctl restart containerd

# Run with Kata
nerdctl run --runtime io.containerd.kata.v2 -it alpine sh
```

### gVisor Installation

```bash
# Install runsc
curl -fsSL https://storage.googleapis.com/gvisor/releases/release/latest/x86_64/runsc -o runsc
sudo install runsc /usr/local/bin

# Run with gVisor
docker run --runtime=runsc -it alpine sh
```

### Performance Tips

**Kata:**
- Use Firecracker for faster boot
- Share VMs for pods (not per-container)
- Pre-warm VMs for serverless

**gVisor:**
- Use KVM mode (not ptrace) for better performance
- Avoid for I/O-heavy workloads
- Good for CPU-bound, compute tasks

---

## What You've Learned

✅ **Kata Containers** - VM isolation with container UX
✅ **gVisor** - Syscall filtering with userspace kernel
✅ **Security tradeoffs** - Kata stronger, gVisor lighter
✅ **Performance tradeoffs** - Kata better I/O, gVisor better density
✅ **Use case alignment** - When to use each
✅ **Hybrid deployments** - Mix runtimes in Kubernetes

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[Kata Containers](https://github.com/kata-containers/kata-containers)** - Secure container runtime using lightweight VMs
- **[gVisor](https://github.com/google/gvisor)** - User-space kernel for containers with reduced syscall attack surface
- **[Security Comparison: Kata vs gVisor](https://gvisor.dev/docs/architecture_guide/security/)** - Deep dive into different approaches to container isolation

---

## Next Steps

**Continue learning:**
→ [Runtime Comparison Matrix](04_runtime_comparison.md) - Complete decision framework
→ [Firecracker Deep Dive](../../05_specialized/03_serverless/02_firecracker_deep_dive.md) - Kata's VMM option

**Related topics:**
→ [Container vs VM](../01_fundamentals/03_container_vs_vm.md) - Isolation approaches
→ [Kubernetes Security](../05_security/03_pod_security.md) - Pod security standards
