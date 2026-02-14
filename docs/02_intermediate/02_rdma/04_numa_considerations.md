---
level: intermediate
estimated_time: 40 min
prerequisites:
  - 02_intermediate/02_rdma/03_converged_ethernet.md
next_recommended:
  - 03_specialized/01_storage/01_pfc_dcb_storage.md
  - 02_intermediate/03_complete_virtualization/04_device_passthrough.md
tags: [networking, rdma, numa, pcie, performance, tlb]
---

# TLB Scaling, NUMA, and RDMA

## Part 1: TLB is Per-Core (Scales with Cores)

### TLB Scaling

**You're absolutely right - TLB is NOT shared between cores!**

```
Single-Core System:
┌──────────────────┐
│  Core 0          │
│  ┌────────────┐  │
│  │ TLB: 1536  │  │
│  │ entries    │  │
│  └────────────┘  │
└──────────────────┘
Total TLB: 1536 entries

Dual-Core System:
┌──────────────────┐  ┌──────────────────┐
│  Core 0          │  │  Core 1          │
│  ┌────────────┐  │  │  ┌────────────┐  │
│  │ TLB: 1536  │  │  │  │ TLB: 1536  │  │
│  │ entries    │  │  │  │ entries    │  │
│  └────────────┘  │  │  └────────────┘  │
└──────────────────┘  └──────────────────┘
Total TLB: 3072 entries

64-Core System:
Total TLB: 64 × 1536 = 98,304 entries!

Linear scaling!
```

---

### Implications for VM Density

```
Single core:
  8 VMs → 48% TLB miss rate (from earlier)
  
8 cores (each handling 1 VM):
  8 VMs → ~2% TLB miss rate per VM
  Much better!

This is why multi-core helps VM density:
  Not just more CPU cycles
  Also more TLB capacity!
```

---

### Cache Hierarchy (Per-Core)

```
Modern CPU (Intel/AMD):
┌────────────────────────────────────────┐
│            Per-Core Resources          │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ L1 Cache: 32-64 KB               │ │
│  │   - Data: 32 KB                  │ │
│  │   - Instruction: 32 KB           │ │
│  │   - Private to this core         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ L1 TLB: 64-128 entries           │ │
│  │   - Private to this core         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ L2 Cache: 256-512 KB             │ │
│  │   - Unified (data + instruction) │ │
│  │   - Private to this core         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ L2 TLB: 1536 entries             │ │
│  │   - Private to this core         │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
         ↓ Shared between cores
┌────────────────────────────────────────┐
│         Shared Resources               │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ L3 Cache: 2-64 MB                │ │
│  │   - Shared by all cores          │ │
│  │   - Inclusive or non-inclusive   │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘

Key point: L1/L2 TLB are per-core
           L3 cache is shared, but NO L3 TLB!
```

---

## Part 2: NUMA (Non-Uniform Memory Access)

### What is NUMA?

**NUMA exists because memory can't scale infinitely on a single memory controller.**

```
Problem: Single memory controller bottleneck

Old UMA (Uniform Memory Access):
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│Core0│  │Core1│  │Core2│  │Core3│
└──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘
   │        │        │        │
   └────────┴────────┴────────┘
            │
    ┌───────▼────────┐
    │ Memory         │
    │ Controller     │  ← Bottleneck!
    └───────┬────────┘
            │
    ┌───────▼────────┐
    │  All Memory    │
    │   (128 GB)     │
    └────────────────┘

Problem:
  - All cores share one memory controller
  - Limited bandwidth (~50 GB/s typical)
  - Contention increases with core count
  - Doesn't scale beyond ~8-16 cores
```

---

### NUMA Architecture

**Solution: Multiple memory controllers, each with local memory**

```
Dual-Socket NUMA System:
┌──────────────────────────────────────────┐
│           Socket 0 (NUMA Node 0)         │
│                                          │
│  ┌─────┐ ┌─────┐ ... ┌─────┐           │
│  │Core0│ │Core1│     │Core7│           │
│  └──┬──┘ └──┬──┘     └──┬──┘           │
│     └────────┴───────────┘              │
│              │                           │
│      ┌───────▼────────┐                 │
│      │   Memory       │                 │
│      │  Controller 0  │                 │
│      └───────┬────────┘                 │
│              │                           │
│      ┌───────▼────────┐                 │
│      │  Local Memory  │  ← "Local"     │
│      │    (64 GB)     │     Fast!       │
│      └────────────────┘                 │
└──────────────┬───────────────────────────┘
               │
               │ Interconnect (QPI/UPI/Infinity Fabric)
               │ (Slower than local!)
               │
┌──────────────▼───────────────────────────┐
│           Socket 1 (NUMA Node 1)         │
│                                          │
│  ┌─────┐ ┌─────┐ ... ┌─────┐           │
│  │Core8│ │Core9│     │Cor15│           │
│  └──┬──┘ └──┬──┘     └──┬──┘           │
│     └────────┴───────────┘              │
│              │                           │
│      ┌───────▼────────┐                 │
│      │   Memory       │                 │
│      │  Controller 1  │                 │
│      └───────┬────────┘                 │
│              │                           │
│      ┌───────▼────────┐                 │
│      │  Local Memory  │  ← "Remote"    │
│      │    (64 GB)     │     for Node 0  │
│      └────────────────┘                 │
└──────────────────────────────────────────┘

Total Memory: 128 GB
  - 64 GB "local" to Socket 0
  - 64 GB "local" to Socket 1
  - Each socket can access both
  - But local is MUCH faster than remote
```

---

### NUMA Distances

**Memory access latency depends on location:**

```
Typical NUMA Latencies:

Core 0 (Node 0) accessing:
  Local memory (Node 0):  ~80 ns    ← Fast!
  Remote memory (Node 1): ~140 ns   ← 1.75x slower

Core 8 (Node 1) accessing:
  Local memory (Node 1):  ~80 ns    ← Fast!
  Remote memory (Node 0): ~140 ns   ← 1.75x slower

Why slower?
  - Must cross inter-socket link (QPI/UPI)
  - Additional hops
  - Contention on interconnect
  - Longer physical distance
```

---

### Viewing NUMA on Linux

```bash
# Show NUMA topology
numactl --hardware

Output:
available: 2 nodes (0-1)
node 0 cpus: 0 1 2 3 4 5 6 7
node 0 size: 65536 MB
node 0 free: 32768 MB
node 1 cpus: 8 9 10 11 12 13 14 15
node 1 size: 65536 MB
node 1 free: 28672 MB

node distances:
node   0   1 
  0:  10  21    ← Distance 10 = local, 21 = remote
  1:  21  10

# These are relative costs, not absolute times
# 10 = 1.0x, 21 = 2.1x slower
```

---

### NUMA and Performance

**Best case: Thread runs on Node 0, accesses Node 0 memory**

```
Process on Core 0:
  malloc(1GB) → Allocated on Node 0 (local)
  
  Memory accesses:
    All ~80ns (local)
    Bandwidth: ~50 GB/s
    
  Performance: Excellent!
```

**Worst case: Thread runs on Node 1, accesses Node 0 memory**

```
Process pinned to Core 8 (Node 1):
  But memory allocated on Node 0
  
  Memory accesses:
    Core 8 → Interconnect → Node 0 → Memory
    ~140ns per access
    Bandwidth: ~25 GB/s (interconnect bottleneck)
    
  Performance: 40-50% slower!
```

---

### NUMA in Virtualization

**VM memory placement is critical:**

```
Bad: VM memory scattered across nodes
─────────────────────────────────────
VM with 32 GB RAM:
  16 GB on Node 0
  16 GB on Node 1
  
vCPUs running on Node 0:
  50% of accesses local (fast)
  50% of accesses remote (slow)
  
Average performance: Degraded

Good: VM memory on single node
───────────────────────────────
VM with 32 GB RAM:
  32 GB on Node 0
  
vCPUs pinned to Node 0 cores:
  100% of accesses local (fast)
  
Performance: Optimal
```

---

### NUMA-Aware VM Placement

**Modern hypervisors understand NUMA:**

```
KVM/QEMU NUMA configuration:

# Pin VM to NUMA node 0
qemu-system-x86_64 \
  -m 32G \
  -smp 8 \
  -object memory-backend-ram,id=mem0,size=32G \
  -numa node,nodeid=0,cpus=0-7,memdev=mem0

This ensures:
  - All vCPUs run on Node 0 cores
  - All VM memory allocated on Node 0
  - No cross-node traffic
  - Optimal performance
```

**Automatic NUMA balancing:**

```
Linux kernel can automatically:
  1. Detect when process accesses remote memory
  2. Migrate pages to local node
  3. Migrate process to node with most pages
  
Enable:
  echo 1 > /proc/sys/kernel/numa_balancing

But for VMs, static pinning is often better
(more predictable)
```

---

### Multi-Node NUMA

**Large systems can have 4, 8, or more NUMA nodes:**

```
4-Socket System:
┌────────┐   ┌────────┐
│ Node 0 │───│ Node 1 │
│ 32 GB  │   │ 32 GB  │
└────┬───┘   └───┬────┘
     │           │
     │    ┌──────┘
     │    │
┌────▼────▼──┐   ┌────────┐
│  Node 2    │───│ Node 3 │
│  32 GB     │   │ 32 GB  │
└────────────┘   └────────┘

NUMA distances:
     0   1   2   3
0:  10  21  21  32
1:  21  10  32  21
2:  21  32  10  21
3:  32  21  21  10

Notice: Node 0 ↔ Node 3 = distance 32 (3.2x slower!)
Multiple hops required
```

---

## Part 3: RDMA (Remote Direct Memory Access)

### What is RDMA?

**RDMA allows network cards to read/write memory without CPU involvement.**

```
Traditional Networking (TCP/IP):
───────────────────────────────

Application wants to send data:
  1. Application: write() syscall
  2. Kernel: Copy to socket buffer
  3. TCP/IP stack: Build headers
  4. Copy to NIC TX queue
  5. NIC: DMA from TX queue
  6. NIC: Send on network
  
Receive:
  7. NIC: Receive packet
  8. NIC: DMA to RX queue
  9. Interrupt: Wake kernel
  10. Kernel: Process packet
  11. Copy to socket buffer
  12. Application: read() syscall
  13. Copy to application buffer
  
Total: 4 copies! (app→kernel, kernel→NIC, NIC→kernel, kernel→app)
       Multiple CPU cycles
       Context switches
```

---

### RDMA Architecture

```
RDMA:
─────

Application wants to send:
  1. Application: Post send request
  2. NIC: DMA directly from application buffer
  3. NIC: Send on network
  
Receive:
  4. NIC: Receive packet  
  5. NIC: DMA directly to application buffer
  6. NIC: Update completion queue
  7. Application: Poll completion (optional interrupt)
  
Total: 0 copies!
       Minimal CPU involvement
       No context switches
       No kernel TCP/IP stack
```

---

### RDMA Components

```
┌────────────────────────────────────────┐
│         Application                    │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ RDMA Verbs API                   │ │
│  │ - ibv_post_send()                │ │
│  │ - ibv_post_recv()                │ │
│  │ - ibv_poll_cq()                  │ │
│  └──────────────────────────────────┘ │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│      User Space RDMA Library           │
│      (libibverbs)                      │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│         Kernel RDMA Stack              │
│         (rdma-core)                    │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│         RDMA NIC (RNIC)                │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Queue Pairs (QP)                 │ │
│  │ - Send Queue                     │ │
│  │ - Receive Queue                  │ │
│  │ - Completion Queue               │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Memory Registration Table        │ │
│  │ - Pins pages in memory           │ │
│  │ - Maps virtual → physical        │ │
│  │ - Generates R_Key/L_Key          │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ DMA Engine                       │ │
│  │ - Direct memory access           │ │
│  │ - No CPU involvement             │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

### RDMA Operations

**1. RDMA Write (One-Sided)**

```
Server A wants to write to Server B's memory:

Server A:
  1. Register memory region (MR)
     buf = malloc(4096);
     mr = ibv_reg_mr(pd, buf, 4096, IBV_ACCESS_RDMA_WRITE);
  
  2. Get Server B's address and R_Key (out of band)
     remote_addr = 0x12345678;  // From Server B
     r_key = 0xABCDEF;           // From Server B
  
  3. Post RDMA Write:
     ibv_post_send(qp, &wr, ...);
     where wr specifies:
       - Operation: IBV_WR_RDMA_WRITE
       - Local buffer: buf
       - Remote address: remote_addr
       - R_Key: r_key
  
Server A's NIC:
  4. Read from local buffer (DMA)
  5. Send packet to Server B
  6. Packet contains: data + remote_addr + r_key
  
Server B's NIC:
  7. Receive packet
  8. Validate R_Key
  9. DMA data to remote_addr
  10. Done! (no CPU involvement on Server B!)
  
Server B's CPU: Never interrupted!
                Doesn't even know the write happened!
```

---

**2. RDMA Read (One-Sided)**

```
Server A wants to read from Server B's memory:

Similar to Write, but:
  - Server A posts IBV_WR_RDMA_READ
  - Server B's NIC reads memory
  - Sends data back to Server A
  - Server A's NIC DMAs to local buffer
  
Again: Server B's CPU never involved!
```

---

**3. Send/Receive (Two-Sided)**

```
More traditional message passing:

Server A (sender):
  ibv_post_send(qp, &send_wr, ...);
  
Server B (receiver):
  Must have pre-posted receive:
    ibv_post_recv(qp, &recv_wr, ...);
    
Both CPUs involved (but minimal)
Still zero-copy!
```

---

### RDMA Performance

```
TCP/IP over 100 Gbps Ethernet:
  Latency: 10-50 μs
  Bandwidth: 50-80 Gbps (CPU bottleneck)
  CPU usage: 100% of one core at line rate
  Copies: 4 per message

RDMA over InfiniBand (100 Gbps):
  Latency: 1-2 μs
  Bandwidth: 95-98 Gbps (near line rate)
  CPU usage: <5% of one core
  Copies: 0

10x lower latency
Near-zero CPU overhead
```

---

### RDMA Technologies

```
┌────────────────────┬──────────────┬─────────────────┐
│ Technology         │ Network      │ Use Case        │
├────────────────────┼──────────────┼─────────────────┤
│ InfiniBand         │ InfiniBand   │ HPC, Storage    │
│                    │ (proprietary)│ Lowest latency  │
│                    │              │                 │
│ RoCE (RDMA over    │ Ethernet     │ Datacenters     │
│ Converged Ethernet)│ (standard)   │ Commodity NICs  │
│                    │              │                 │
│ iWARP (Internet    │ Ethernet     │ WANs            │
│ Wide Area RDMA)    │ (TCP/IP)     │ Works over IP   │
└────────────────────┴──────────────┴─────────────────┘
```

---

## Part 4: How NUMA and RDMA Relate

### They're About Different Things

```
NUMA:
  Scope: Within a single server
  Problem: Memory access latency
  Solution: Local memory per socket
  
RDMA:
  Scope: Between servers (network)
  Problem: Network I/O overhead
  Solution: Zero-copy DMA
  
Different layers!
```

---

### But They Interact

**NUMA-aware RDMA:**

```
Bad: RDMA NIC on Node 0, Application on Node 1
─────────────────────────────────────────────

Application (Node 1):
  buf = malloc(1GB);  // Allocated on Node 1
  ibv_reg_mr(buf);    // Register with RDMA NIC
  
RDMA NIC (Node 0):
  DMA read buf → Must cross interconnect!
  
  Node 0 NIC → Interconnect → Node 1 Memory
  
Performance hit: Remote memory access

Good: RDMA NIC on Node 0, Application on Node 0
────────────────────────────────────────────

Application (Node 0):
  buf = malloc(1GB);  // Allocated on Node 0
  ibv_reg_mr(buf);
  
RDMA NIC (Node 0):
  DMA read buf → Local memory!
  
  Node 0 NIC → Local memory controller → Memory
  
Performance: Optimal
```

---

### Real-World RDMA + NUMA

```
Datacenter server (dual-socket):
┌──────────────────────────────────────────┐
│           Node 0                         │
│  Cores: 0-15                             │
│  Memory: 64 GB                           │
│  PCIe: Slot 1                            │
│    └─ RDMA NIC 0 (100 Gbps)             │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│           Node 1                         │
│  Cores: 16-31                            │
│  Memory: 64 GB                           │
│  PCIe: Slot 2                            │
│    └─ RDMA NIC 1 (100 Gbps)             │
└──────────────────────────────────────────┘

Best practice:
  - Application A on cores 0-15
    → Use RDMA NIC 0
    → Memory on Node 0
  
  - Application B on cores 16-31
    → Use RDMA NIC 1
    → Memory on Node 1
  
Avoid cross-node traffic!
```

---

### RDMA for Distributed Storage (NUMA-aware)

```
Distributed storage (like Ceph with RDMA):

Storage daemon on Node 0:
  - Data buffer: Allocated on Node 0
  - RDMA NIC: On Node 0
  - CPU threads: Pinned to Node 0
  
When remote server reads:
  1. Remote RDMA Read request arrives
  2. Node 0 NIC DMAs from local memory (fast!)
  3. Send to network
  
All local accesses, no NUMA penalty!

If misconfigured (daemon on Node 1, NIC on Node 0):
  Every RDMA operation crosses interconnect
  50% performance loss!
```

---

## Part 5: Virtualization with NUMA and RDMA

### VM NUMA Topology

**VMs can be NUMA-aware too:**

```
Physical: 2-socket system (Node 0, Node 1)

VM Configuration:
  64 GB RAM
  16 vCPUs
  
Option 1: Single NUMA node (VM sees UMA)
  ✓ Simple
  ✗ VM sees all memory as uniform
  ✗ Guest OS can't optimize for locality
  ✗ If VM spans nodes, bad performance

Option 2: Virtual NUMA (vNUMA)
  Present VM with 2 virtual NUMA nodes:
    vNode 0: 32 GB, vCPUs 0-7
    vNode 1: 32 GB, vCPUs 8-15
  
  Map to physical:
    vNode 0 → Physical Node 0
    vNode 1 → Physical Node 1
  
  ✓ Guest OS can optimize for locality
  ✓ Better performance for NUMA-aware apps
  ✗ More complex
```

---

### RDMA Passthrough for VMs

**SR-IOV + RDMA:**

```
Physical RDMA NIC with SR-IOV:
┌────────────────────────────────────────┐
│     Physical Function (PF)             │
│     - Full RDMA capabilities           │
└────────────────────────────────────────┘
         │
         ├─────────────┬──────────────┐
         │             │              │
┌────────▼──────┐┌────▼─────┐┌──────▼────┐
│ VF 0          ││ VF 1     ││ VF 2      │
│ (RDMA capable)││          ││           │
└────────┬──────┘└────┬─────┘└──────┬────┘
         │            │              │
    ┌────▼───┐   ┌───▼────┐    ┌───▼────┐
    │  VM1   │   │  VM2   │    │  VM3   │
    └────────┘   └────────┘    └────────┘

Each VM gets:
  - Direct RDMA access (via VF)
  - Near-native performance
  - Full RDMA verbs support
  
No hypervisor in data path!
```

---

## Summary

### TLB Scaling

```
✓ TLB is per-core (not shared)
✓ More cores = more total TLB capacity
✓ 64 cores = 64 × 1536 = 98K TLB entries
✓ Helps VM density significantly
```

### NUMA

```
What: Multiple memory controllers, each with local memory
Why: Memory bandwidth doesn't scale with single controller
Impact: Local access ~80ns, Remote ~140ns (1.75x slower)

For VMs:
  - Pin VM to single NUMA node
  - Avoid cross-node memory access
  - vNUMA for large VMs
```

### RDMA

```
What: Network cards DMA directly to/from application memory
Why: Eliminate TCP/IP overhead and copies
Impact: 1-2μs latency (vs 10-50μs), near-zero CPU

For VMs:
  - SR-IOV for direct RDMA access
  - NUMA-aware: NIC on same node as VM
  - Critical for low-latency workloads
```

### The Connection

```
All three are about **locality** and **avoiding overhead**:

TLB: Keep translations cached locally (per core)
NUMA: Keep memory local (per socket)
RDMA: Bypass kernel, zero-copy (per server)

Performance = Minimize distance data travels
```

**Modern datacenter:** Multi-socket NUMA servers with RDMA NICs, running dozens of VMs, each NUMA-pinned and potentially with RDMA passthrough. All optimized for maximum locality and minimum overhead!
