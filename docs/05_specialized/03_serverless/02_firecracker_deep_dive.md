---
level: specialized
estimated_time: 70 min
prerequisites:
  - 05_specialized/03_serverless/01_firecracker_relationship.md
next_recommended:
  - 05_specialized/03_serverless/03_firecracker_virtio.md
tags: [virtualization, firecracker, microvms, serverless, aws-lambda]
---

# Firecracker: MicroVMs and the Serverless Sweet Spot

## What is Firecracker?

**Firecracker is a minimalist Virtual Machine Monitor (VMM) built specifically for serverless workloads.**

Created by AWS (2018), powers Lambda and Fargate.

**Core philosophy:** Strip away EVERYTHING not needed for running a single Linux kernel and application.

---

## Traditional VM (QEMU/KVM) vs Firecracker

### Traditional VM Stack

```
┌─────────────────────────────────────────────────┐
│              Guest OS + App                     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│                   QEMU                          │
│                                                 │
│  Device Emulation:                              │
│  ✓ BIOS (SeaBIOS/OVMF)         - Boot firmware │
│  ✓ VGA graphics                - Display       │
│  ✓ PS/2 keyboard/mouse         - Input         │
│  ✓ IDE/SATA/SCSI controllers   - Disk          │
│  ✓ E1000/RTL8139 NICs          - Network       │
│  ✓ USB controllers             - USB devices   │
│  ✓ Sound card                  - Audio         │
│  ✓ PCI bus                     - Device tree   │
│  ✓ RTC, PIT timers             - Timekeeping   │
│  ✓ ACPI                        - Power mgmt    │
│                                                 │
│  Code size: ~1.5 million lines                 │
│  Memory: 100-200 MB overhead                   │
│  Boot time: 2-5 seconds                        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│                    KVM                          │
└─────────────────────────────────────────────────┘
```

---

### Firecracker Stack

```
┌─────────────────────────────────────────────────┐
│         Guest Linux Kernel + App                │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│                Firecracker VMM                  │
│                                                 │
│  Device Support (ONLY):                         │
│  ✓ virtio-block          - Disk (minimal)      │
│  ✓ virtio-net            - Network (minimal)   │
│  ✓ Serial console        - Logging             │
│  ✓ 1-button keyboard     - Shutdown only       │
│                                                 │
│  NO BIOS:                                       │
│  ✗ Direct kernel boot (Linux boot protocol)    │
│                                                 │
│  Code size: ~50,000 lines (Rust)               │
│  Memory: ~5 MB overhead                        │
│  Boot time: <125 milliseconds                  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│                    KVM                          │
└─────────────────────────────────────────────────┘
```

---

## Key Architectural Differences

### 1. No BIOS - Direct Kernel Boot

**Traditional VM:**
```
Power on
  → BIOS/UEFI firmware loads (1-2 seconds)
  → Firmware initializes devices
  → Firmware reads bootloader from disk
  → Bootloader (GRUB) loads kernel
  → Kernel starts
  
Total: 2-5 seconds
```

**Firecracker:**
```
Power on
  → Firecracker loads kernel image directly into memory
  → Sets up boot parameters (kernel command line)
  → Jumps to kernel entry point
  → Kernel starts immediately
  
Total: 125 milliseconds
```

**How it works:**

```
Traditional:
  QEMU → BIOS → Disk → Bootloader → Kernel

Firecracker:
  Firecracker → Kernel (direct)

No firmware, no bootloader, no disk I/O for boot!
```

**Setup:**

```bash
# Firecracker config
{
  "boot-source": {
    "kernel_image_path": "/path/to/vmlinux",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [{
    "drive_id": "rootfs",
    "path_on_host": "/path/to/rootfs.ext4",
    "is_root_device": true,
    "is_read_only": false
  }]
}

# Kernel is uncompressed ELF (vmlinux, not bzImage)
# Firecracker parses ELF, loads segments, starts execution
```

---

### 2. Minimal Device Model

**What's missing from Firecracker:**

```
✗ No VGA/graphics
✗ No PS/2 keyboard/mouse
✗ No USB
✗ No sound
✗ No legacy IDE/SATA (only virtio-block)
✗ No legacy network cards (only virtio-net)
✗ No PCI discovery (devices are MMIO)
✗ No ACPI
✗ No multiple VCPUs initially (added later)

What's included:
✓ virtio-block (disk)
✓ virtio-net (network)
✓ Serial console (for logs)
✓ Minimal "keyboard" (just for shutdown signal)
```

**Why this matters:**

```
Emulated PCI bus scan:
  - Guest OS probes each PCI slot
  - Reads config space (4KB per device)
  - Multiple VM exits per device
  - 10-100ms overhead
  
Firecracker MMIO:
  - Fixed device addresses in memory
  - No discovery needed
  - Guest kernel configured to expect devices at fixed locations
  - 0ms overhead
```

---

### 3. Rate Limiting (Multi-Tenancy Focus)

**Critical for serverless:** Prevent noisy neighbor problems.

**Built-in rate limiters:**

```json
{
  "network-interfaces": [{
    "iface_id": "eth0",
    "host_dev_name": "tap0",
    "rx_rate_limiter": {
      "bandwidth": {
        "size": 125000000,      // 1 Gbps in bytes/sec
        "refill_time": 100      // Refill every 100ms
      },
      "ops": {
        "size": 10000,          // Max 10K packets
        "refill_time": 100      // per 100ms
      }
    },
    "tx_rate_limiter": { /* ... */ }
  }]
}
```

**Token bucket algorithm:**

```
Each microVM has network/disk rate limit:

Token Bucket:
  - Starts with N tokens
  - Each byte/operation costs 1 token
  - Tokens refill at configured rate
  - If no tokens: operation is delayed/throttled
  
Example:
  Bucket size: 1 MB
  Refill rate: 10 MB/s
  
  Burst: Can send 1 MB immediately
  Sustained: 10 MB/s average
  Over limit: Delayed until tokens available
```

**Why this matters:**

```
AWS Lambda:
  - 1000s of functions on one host
  - One malicious function shouldn't affect others
  - Rate limiting at VMM level (not guest OS)
  - Guest can't bypass (enforced by host)
  
Traditional VMs:
  - Rate limiting via tc/qdisc (guest can see)
  - Or external firewall
  - Not integrated into VMM
```

---

### 4. Security - Written in Rust

**QEMU is C:**
```
Lines of code: ~1.5 million
Memory safety: Manual (buffer overflows, use-after-free)
CVEs: Hundreds over the years
Attack surface: Huge (all device emulations)
```

**Firecracker is Rust:**
```
Lines of code: ~50,000
Memory safety: Compiler enforced
CVEs: Very few
Attack surface: Minimal (4 devices total)
```

**Additional hardening - Jailer:**

```
┌─────────────────────────────────────────────────┐
│              Jailer Process                     │
│                                                 │
│  Sets up security:                              │
│  ✓ New PID namespace (isolated)                │
│  ✓ New network namespace                       │
│  ✓ New mount namespace                         │
│  ✓ Chroot to minimal jail                      │
│  ✓ Drop all capabilities                       │
│  ✓ Seccomp filter (allow only ~20 syscalls)   │
│  ✓ cgroup limits (CPU, memory)                 │
│                                                 │
│  Then exec() Firecracker VMM                   │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│         Firecracker VMM (restricted)            │
│                                                 │
│  Can ONLY:                                      │
│  - ioctl() to /dev/kvm                         │
│  - read/write to guest memory                  │
│  - access TAP device for network               │
│  - write logs to stdout                        │
│                                                 │
│  Cannot:                                        │
│  - Access host filesystem                      │
│  - Open network sockets                        │
│  - Fork processes                              │
│  - Most syscalls blocked by seccomp            │
└─────────────────────────────────────────────────┘
```

**Seccomp profile (only ~20 syscalls allowed):**

```
Allowed:
  read, write, close
  epoll_wait, epoll_ctl
  ioctl (for /dev/kvm only)
  mmap, munmap, madvise
  futex
  exit, exit_group
  
Blocked:
  Everything else (1000+ syscalls)
  
If Firecracker is compromised:
  Attacker has minimal syscalls available
  Can't open files, can't exec, can't fork
  Limited blast radius
```

---

### 5. Memory Footprint

**Traditional VM:**

```
QEMU process overhead:
  - QEMU binary: ~20 MB
  - Device emulation state: ~50 MB
  - BIOS/UEFI firmware: ~10 MB
  - VGA framebuffer: ~16 MB
  - Other buffers: ~20 MB
  
Total: ~100-120 MB per VM (before guest OS!)

Guest OS:
  - Linux kernel: ~50 MB
  - initrd/initramfs: ~20 MB
  - User space: varies
  
Total VM: ~200+ MB minimum
```

**Firecracker:**

```
Firecracker VMM overhead:
  - Binary: ~1 MB
  - virtio queues: ~1 MB
  - Other state: ~3 MB
  
Total: ~5 MB per microVM

Guest OS:
  - Minimal kernel: ~10 MB
  - No initrd needed
  - Minimal rootfs: ~10 MB
  
Total microVM: ~25 MB for minimal function

Density: 40 microVMs per GB (vs 5 traditional VMs per GB)
```

---

## Firecracker Architecture Deep Dive

### Boot Process

```
1. API call to create microVM:
   curl -X PUT http://localhost:8080/boot-source \
     -d '{
       "kernel_image_path": "/vmlinux",
       "boot_args": "console=ttyS0"
     }'

2. Firecracker:
   - Opens /dev/kvm
   - Creates VM (KVM_CREATE_VM)
   - Creates vCPU (KVM_CREATE_VCPU)
   - Allocates guest memory (mmap)
   - Sets up EPT (guest physical → host physical)

3. Load kernel:
   - Read vmlinux ELF file
   - Parse ELF headers
   - Load segments into guest memory:
       Segment 0: .text at GPA 0x1000000
       Segment 1: .data at GPA 0x2000000
       ...
   
4. Set up boot parameters:
   - Command line at GPA 0x20000
   - Boot parameters struct (setup_header)
   - Set vCPU registers:
       RIP = kernel entry point (from ELF)
       RSI = boot params address
       
5. Set up devices:
   - virtio-block: MMIO region at 0xd0000000
   - virtio-net: MMIO region at 0xd0001000
   - Register with KVM
   
6. KVM_RUN:
   - vCPU starts executing kernel
   - Kernel initializes
   - Mounts root filesystem
   - Runs init process
   
Total time: <125ms
```

---

### Device Model

**virtio-block (minimal):**

```rust
// Simplified Firecracker virtio-block implementation

struct VirtioBlock {
    queue: Queue,          // Single virtqueue
    disk_image: File,      // Host file (rootfs.ext4)
    rate_limiter: RateLimiter,
}

fn handle_queue(&mut self) {
    while let Some(desc_chain) = self.queue.pop() {
        // Check rate limiter
        if !self.rate_limiter.consume(1, desc_chain.len()) {
            // Over limit, requeue for later
            self.queue.push_back(desc_chain);
            break;
        }
        
        // Read request from guest memory
        let req: BlockRequest = read_from_guest(desc_chain.addr);
        
        match req.type {
            READ => {
                let data = self.disk_image.read_at(req.sector * 512, req.len);
                write_to_guest(desc_chain.data_addr, data);
            }
            WRITE => {
                let data = read_from_guest(desc_chain.data_addr, req.len);
                self.disk_image.write_at(req.sector * 512, data);
            }
        }
        
        // Mark complete
        self.queue.add_used(desc_chain.index);
        
        // Inject interrupt
        self.inject_interrupt();
    }
}
```

**No support for:**
- Multiple queues
- Discard/TRIM
- Write-back caching
- Barriers
- Flush commands

Just: Read sector, Write sector. That's it.

---

### Snapshot and Restore (Key Feature!)

**Use case:** Pre-warm functions for faster cold starts.

```
Boot baseline microVM:
  - Linux kernel
  - Runtime (Python, Node.js, etc.)
  - Common libraries
  
Time: 125ms

Take snapshot:
  - Save guest memory to file
  - Save device state
  - Save vCPU registers
  
Store snapshot (compressed): ~10-50 MB

On function invocation:
  - Restore snapshot
  - Load customer code
  - Execute
  
Restore time: 5-10ms (from snapshot, not cold boot!)

Result: <20ms to running code
```

**Implementation:**

```bash
# Create snapshot
curl -X PUT http://localhost:8080/snapshot/create \
  -d '{
    "snapshot_path": "/snapshots/baseline.snap",
    "mem_file_path": "/snapshots/baseline.mem"
  }'

# Later, restore
firecracker --config-file restore.json \
  --snapshot-path /snapshots/baseline.snap \
  --mem-file-path /snapshots/baseline.mem

# microVM resumes EXACTLY where snapshot was taken
# All memory, registers, device state preserved
```

---

## The Sweet Spot - Serverless/FaaS

### AWS Lambda Use Case

**Requirements:**
```
✓ Strong isolation (per-customer code)
✓ Fast cold start (<200ms to running code)
✓ High density (1000s per host)
✓ Minimal overhead (cost efficiency)
✓ Rate limiting (prevent abuse)
✓ Short-lived (seconds to minutes)
✓ Simple workload (run function, no USB/GUI)
```

**Why Firecracker wins:**

```
┌──────────────────────────┬──────────────┬──────────────┐
│ Metric                   │ Container    │ Firecracker  │
├──────────────────────────┼──────────────┼──────────────┤
│ Isolation                │ Weak (kernel)│ Strong (VM)  │
│ Cold start               │ ~10ms        │ ~125ms       │
│ Memory overhead          │ ~1 MB        │ ~5 MB        │
│ Density (per host)       │ 10,000+      │ 2,000-4,000  │
│ Security                 │ Shared kernel│ Isolated     │
│ Noisy neighbor           │ Risk         │ Rate limited │
│                          │              │              │
│ Lambda requirements      │ ✗ (too weak) │ ✓ Perfect!   │
└──────────────────────────┴──────────────┴──────────────┘

Traditional VM:
  ✗ 2-5 second cold start (too slow)
  ✗ 100+ MB overhead (too expensive)
  ✗ 10-50 per host (too sparse)
```

---

### AWS Fargate Use Case

**Long-running containers with VM isolation:**

```
Customer wants to run containers:
  - But with VM-level isolation
  - Per-customer kernel
  - No shared kernel vulnerabilities
  
Firecracker + container runtime:
  - Each Fargate task = 1 microVM
  - Container runtime inside microVM
  - Customer containers run inside
  
Result:
  - VM isolation
  - Container UX
  - Firecracker density and speed
```

---

## Where Firecracker Doesn't Fit

### 1. Desktop/Workstation VMs

```
User wants:
  ✗ GUI (VGA, keyboard, mouse)
  ✗ USB devices (cameras, printers)
  ✗ Sound
  ✗ PCI passthrough for GPU
  ✗ Multiple displays
  
Firecracker has:
  ✓ Serial console only
  ✗ No graphics
  ✗ No USB
  ✗ No sound
  
Verdict: Use QEMU or VirtualBox
```

---

### 2. Development VMs

```
Developer wants:
  ✗ Shared folders (9p, virtio-fs)
  ✗ Copy/paste
  ✗ Multiple CPUs for compilation
  ✗ Debugging tools
  ✗ Resize window dynamically
  
Firecracker:
  ✓ Basic block device
  ✗ Limited CPU count initially
  ✗ No guest additions
  
Verdict: Use QEMU, Vagrant, or containers
```

---

### 3. Windows VMs

```
Windows needs:
  ✗ UEFI firmware (Firecracker has none)
  ✗ ACPI (Firecracker minimal)
  ✗ VGA BIOS
  ✗ Legacy device support
  
Firecracker:
  ✓ Linux kernel only
  ✗ No firmware
  ✗ No ACPI
  
Verdict: Use QEMU/KVM or Hyper-V
```

---

### 4. Legacy Applications

```
Application needs:
  ✗ Specific hardware (serial port, parallel port)
  ✗ PCI devices
  ✗ ISA bus devices
  ✗ BIOS interrupts
  
Firecracker:
  ✓ virtio only
  ✗ No legacy hardware
  
Verdict: Use full QEMU
```

---

## Firecracker Sweet Spot Summary

### Perfect For:

**1. Serverless Functions (Lambda)**
```
✓ Ephemeral (seconds to minutes)
✓ Stateless
✓ Small memory footprint
✓ Need strong isolation
✓ High density required
✓ Fast cold start critical
```

**2. Container Isolation (Fargate, Kata Containers)**
```
✓ Run containers with VM security
✓ Multi-tenant workloads
✓ Per-customer kernels
✓ Prevent container escapes
```

**3. CI/CD Runners**
```
✓ Isolated build environments
✓ Fast spin-up per job
✓ Clean slate each time
✓ Rate limit resource usage
```

**4. Edge Computing**
```
✓ Minimal resource footprint
✓ Fast initialization
✓ Simple workloads
✓ Deploy many per edge node
```

---

### Not Suitable For:

**1. Interactive VMs**
- Desktop Linux
- Windows VMs
- Development environments
- GUI applications

**2. Complex Workloads**
- Multi-CPU compilation
- Database servers (need I/O flexibility)
- Gaming
- Video encoding

**3. Legacy Systems**
- Windows NT/2000
- DOS applications
- Hardware-specific software
- BIOS-dependent systems

**4. Hardware Passthrough**
- GPU compute
- FPGA cards
- Specialized PCI devices
- USB devices

---

## The Architecture Decision Tree

```
Need VM isolation?
  NO → Use containers (Docker, Kubernetes)
  YES ↓

Running Linux only?
  NO → Use QEMU/ESXi/Hyper-V
  YES ↓

Need GUI/USB/complex devices?
  YES → Use QEMU/KVM
  NO ↓

Short-lived (<1 hour) workload?
  NO → Use QEMU/KVM
  YES ↓

Need high density (100s-1000s per host)?
  NO → Use QEMU/KVM
  YES ↓

Cold start time critical (<200ms)?
  NO → Use QEMU/KVM
  YES ↓

→ Use Firecracker!
```

---

## Performance Comparison

```
Benchmark: Start 1000 VMs on single host

QEMU/KVM:
  Memory: 100 GB (100 MB × 1000)
  Time: 30-60 minutes serial
  Time: 5-10 minutes parallel (limited by CPU)
  Result: Host OOM or swap thrashing

Firecracker:
  Memory: 5 GB (5 MB × 1000)
  Time: 2 minutes (125ms × 1000)
  Result: Fits in memory, all running
  
Density: 20x better
Speed: 5-15x faster
```

```
Benchmark: Cold start to running code

Traditional VM (QEMU):
  BIOS: 1000ms
  Bootloader: 500ms
  Kernel: 1000ms
  Init: 500ms
  Total: ~3000ms

Firecracker (cold):
  Kernel load: 50ms
  Kernel init: 75ms
  Total: ~125ms
  24x faster!

Firecracker (from snapshot):
  Restore: 5ms
  Init: 5ms
  Total: ~10ms
  300x faster!
```

---

## Real-World Numbers (AWS)

**AWS Lambda powered by Firecracker:**
```
Functions invoked per day: Trillions
MicroVMs per host: ~2000
Cold start P99: <200ms
Memory overhead: ~5 MB per function
Security incidents: Near zero
Cost savings: Billions (vs traditional VMs)
```

---

## Summary: Why Firecracker Exists

**The serverless dilemma:**
```
Containers: Fast + dense but weak isolation
VMs: Strong isolation but slow + expensive

Firecracker: Strong isolation + fast + dense
```

**Key innovations:**
1. **No BIOS** → Fast boot (125ms)
2. **Minimal devices** → Small footprint (5 MB)
3. **Rate limiting** → Multi-tenant safety
4. **Rust + Jailer** → Security
5. **Snapshots** → Even faster starts (10ms)

**The edge of usefulness:**
- Linux-only
- Minimal devices
- Short-lived workloads
- No legacy support

**Outside this edge:** Use QEMU/KVM.

**Inside this edge:** Firecracker is 10-20x better than alternatives.

That's the sweet spot: Serverless/FaaS where you need VM isolation but at container-like speed and density.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for Firecracker internals and microVMs:**

- **[Firecracker Source Code](https://github.com/firecracker-microvm/firecracker)** - Explore the Rust implementation of Firecracker's minimal VMM
- **["Firecracker: Lightweight Virtualization for Serverless Applications" (NSDI 2020)](https://www.usenix.org/conference/nsdi20/presentation/agache)** - Academic paper detailing Firecracker's design and performance
