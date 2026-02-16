---
level: specialized
estimated_time: 55 min
prerequisites:
  - 02_intermediate/02_rdma/03_converged_ethernet.md
  - 02_intermediate/02_rdma/04_numa_considerations.md
next_recommended:
  - 02_intermediate/03_complete_virtualization/04_device_passthrough.md
tags: [storage, rdma, pfc, dcb, nvme-of, distributed-storage]
---

# PFC, DCB, and RDMA in Storage

## Acronyms Expanded

**PFC = Priority Flow Control**
- IEEE 802.1Qbb standard
- Selective PAUSE mechanism
- Prevents packet loss for specific priority classes

**DCB = Data Center Bridging**
- Umbrella term for IEEE standards that enable lossless Ethernet
- Collection of protocols (PFC, ETS, ECN, DCBX)
- Makes Ethernet suitable for storage

---

## Part 1: PFC and the TCP Tradeoff

### The Nuance: It's Not Simply "TCP Loses"

**Your instinct is partially correct, but there's more to it:**

```
Scenario: RDMA traffic causes congestion

Option 1: No PFC (standard Ethernet)
───────────────────────────────────
Switch queue fills:
  → Drop packets (random drop)
  → Might drop RDMA packets (connection fails!)
  → Might drop TCP packets (TCP retransmits, works)
  
Result: RDMA broken, TCP works but slow

Option 2: With PFC (converged Ethernet)
────────────────────────────────────────
Switch queue fills (RDMA, priority 3):
  → Send PFC PAUSE for priority 3
  → Upstream stops sending RDMA (priority 3)
  → TCP (priority 0) continues!
  
Queue drains:
  → Send PFC RESUME
  → RDMA resumes
  
Result: Both work, but RDMA paused briefly
```

---

### The Actual Tradeoff

**PFC doesn't give RDMA more bandwidth - it prevents drops at cost of backpressure:**

```
Without PFC:
────────────
10 Gbps link, both trying to send:
  RDMA: 6 Gbps attempted
  TCP:  6 Gbps attempted
  Total: 12 Gbps (oversubscribed!)
  
  Switch queue fills → Drops packets
  TCP: Retransmits, slows down (congestion control)
  RDMA: Lost packet = connection broken!
  
  Result: TCP: 8 Gbps (recovered)
          RDMA: 0 Gbps (failed)

With PFC:
─────────
10 Gbps link, both trying to send:
  RDMA: 6 Gbps attempted
  TCP:  6 Gbps attempted
  Total: 12 Gbps (oversubscribed!)
  
  Switch queue fills (RDMA priority 3)
  → PFC PAUSE priority 3
  → RDMA sender stops transmitting
  → TCP (priority 0) gets bandwidth
  → Queue drains
  → PFC RESUME
  → RDMA resumes
  
  Result: TCP: 5 Gbps (consistent)
          RDMA: 5 Gbps (with pauses, but works!)
          
Both work! But RDMA has "stuttering" problem
```

---

### The PFC Problem: Head-of-Line Blocking

**PFC can create cascading issues:**

```
Problem Scenario:

Host A ──→ Switch 1 ──→ Switch 2 ──→ Host B
                           ↑
                     Queue full!
                     
1. Switch 2 queue full (congested to Host B)
2. Switch 2 sends PFC PAUSE to Switch 1
3. Switch 1 stops forwarding to Switch 2
4. Switch 1 queue fills up
5. Switch 1 sends PFC PAUSE to Host A
6. Host A stops transmitting

This is fine, BUT:

Host C ──→ Switch 1 ──→ Switch 3 ──→ Host D
                ↑
           Also paused!
           (because Switch 1 paused)

Host C → Host D path is blocked
Even though Switch 3 has capacity!

This is "head-of-line blocking"
Congestion in one path affects unrelated paths
```

---

### Modern Solution: ECN + PFC

**Use ECN to prevent PFC from triggering:**

```
Better approach:
────────────────

1. Switch queue reaching 70% full:
   → Mark packets with ECN (don't pause yet!)
   
2. Receiver gets ECN-marked packets:
   → Sends CNP (Congestion Notification Packet)
   
3. Sender receives CNP:
   → Reduces rate using DCQCN algorithm
   → Avoids filling queue
   
4. Queue stays below PFC threshold:
   → No PAUSE needed
   → No head-of-line blocking
   
5. If sudden burst overwhelms ECN:
   → PFC acts as emergency brake
   → Prevents packet drop
   
Result: ECN handles normal congestion
        PFC only for emergencies
        TCP mostly unaffected
```

---

### Bandwidth Allocation: ETS

**ETS (Enhanced Transmission Selection) provides fairness:**

```
Configuration:
──────────────
Priority 0 (TCP):  50% minimum, can borrow
Priority 3 (RDMA): 50% minimum, can borrow

Scenario 1: Only RDMA active
─────────────────────────────
RDMA gets 100% (borrows TCP's 50%)

Scenario 2: Only TCP active
────────────────────────────
TCP gets 100% (borrows RDMA's 50%)

Scenario 3: Both active, neither saturated
───────────────────────────────────────────
RDMA: 3 Gbps (under 50%)
TCP:  4 Gbps (under 50%)
Both happy!

Scenario 4: Both want more than 50%
────────────────────────────────────
RDMA wants 8 Gbps
TCP wants 7 Gbps
Total: 15 Gbps > 10 Gbps link

ETS allocates:
  RDMA: 5 Gbps (50% minimum)
  TCP:  5 Gbps (50% minimum)
  
Fair sharing!

With PFC:
  If RDMA queue fills → PFC pauses RDMA
  → TCP can temporarily use more
  → But RDMA's 50% guaranteed long-term
```

---

## Part 2: RDMA's Role in Storage

### Why Storage Needs RDMA

**Storage has unique requirements:**

```
Storage Characteristics:
────────────────────────
✓ High bandwidth (GB/s per server)
✓ Low latency (<100 μs for NVMe)
✓ High IOPS (millions per second)
✓ Predictable performance
✓ CPU efficiency (can't waste cycles on I/O)

Traditional TCP/IP problems:
────────────────────────────
✗ High CPU overhead (10-20% for 10 Gbps)
✗ High latency (10-50 μs just in stack)
✗ Memory copies (4 per I/O)
✗ Unpredictable (congestion → retransmits)

RDMA solves all of these!
```

---

### Storage Protocols Using RDMA

#### 1. NVMe-oF (NVMe over Fabrics)

**Modern flash storage protocol:**

```
Traditional: NVMe over PCIe (local only)
────────────────────────────────────────
┌──────────────────┐
│      Server      │
│                  │
│  ┌────────────┐  │
│  │ NVMe SSD   │  │ ← Directly attached via PCIe
│  │ (local)    │  │   ~10 μs latency
│  └────────────┘  │
└──────────────────┘

Problem: Can't share across network
         Each server needs its own SSDs
         Storage can't be pooled

Modern: NVMe-oF over RDMA
──────────────────────────
┌──────────────────┐               ┌──────────────────┐
│  Compute Server  │               │ Storage Server   │
│                  │               │                  │
│  ┌────────────┐  │  RDMA/RoCE   │  ┌────────────┐  │
│  │ NVMe-oF    │──┼───────────────┼──│ NVMe SSD   │  │
│  │ Initiator  │  │  <20 μs      │  │ (shared)   │  │
│  └────────────┘  │               │  └────────────┘  │
└──────────────────┘               └──────────────────┘

Benefits:
  ✓ Disaggregated storage (share SSDs)
  ✓ Near-local latency (<20 μs network)
  ✓ Full NVMe performance over network
  ✓ Storage pooling, better utilization
```

---

**NVMe-oF I/O Path with RDMA:**

```
Read request (4 KB block):

Application:
  1. read(fd, buffer, 4096)
  
NVMe-oF Initiator (client):
  2. Build NVMe command
  3. Post RDMA Send (command to storage)
     → 1 μs (zero-copy)
  
Network:
  4. RDMA packet transmission
     → 5 μs (100 Gbps, low latency)
  
NVMe-oF Target (storage server):
  5. Receive command (DMA to memory)
     → 1 μs
  6. Read from local NVMe SSD
     → 10 μs (flash access)
  7. RDMA Write data to client buffer
     → 1 μs (zero-copy)
  
Network:
  8. Data transmission (4 KB)
     → 5 μs
  
Client:
  9. Completion (DMA done)
     → Application continues
  
Total: ~23 μs

Compare to iSCSI/TCP:
  Same operation: 150-200 μs
  8x slower!
```

---

#### 2. Distributed Storage Systems

**Examples: Ceph, GlusterFS, distributed databases**

```
Typical Architecture:

┌──────────┐  ┌──────────┐  ┌──────────┐
│ Client 1 │  │ Client 2 │  │ Client 3 │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┴─────────────┘
                   │ RDMA network
     ┌─────────────┴─────────────┐
     │             │             │
┌────▼─────┐  ┌───▼──────┐  ┌───▼──────┐
│Storage   │  │Storage   │  │Storage   │
│Node 1    │  │Node 2    │  │Node 3    │
│          │  │          │  │          │
│ 10 SSDs  │  │ 10 SSDs  │  │ 10 SSDs  │
└──────────┘  └──────────┘  └──────────┘

Write operation (1 MB, 3x replication):
───────────────────────────────────────

With TCP/IP:
  1. Client → Node 1: 1 MB (50 μs network + 80 μs CPU)
  2. Node 1 → Node 2: 1 MB (50 μs + 80 μs)
  3. Node 1 → Node 3: 1 MB (50 μs + 80 μs)
  4. Disk writes: 3 × 100 μs = 300 μs
  
  Total: ~400 μs
  CPU: 240 μs (60% of time in TCP/IP!)

With RDMA:
  1. Client → Node 1: 1 MB (50 μs network + 2 μs CPU)
  2. Node 1 → Node 2: 1 MB (50 μs + 2 μs)
  3. Node 1 → Node 3: 1 MB (50 μs + 2 μs)
  4. Disk writes: 3 × 100 μs = 300 μs
  
  Total: ~360 μs
  CPU: 6 μs (almost all time in disk!)
  
  12% faster, but 97% less CPU!
  Can serve 40x more IOPS per CPU core
```

---

#### 3. Remote Block Storage

**Like network-attached SAN, but over Ethernet:**

```
Traditional SAN (Fibre Channel):
─────────────────────────────────
Expensive FC switches
Dedicated FC infrastructure
Complex zoning

RDMA Block Storage:
───────────────────
Standard Ethernet switches (with DCB)
Converged infrastructure
Simpler management

Example: VM storage
───────────────────

┌──────────────────────────────────┐
│  Hypervisor                      │
│                                  │
│  ┌────────┐  ┌────────┐         │
│  │  VM1   │  │  VM2   │         │
│  │        │  │        │         │
│  │ Virtual│  │ Virtual│         │
│  │ Disk   │  │ Disk   │         │
│  └───┬────┘  └───┬────┘         │
│      │           │              │
│      └─────┬─────┘              │
│            │                    │
│    ┌───────▼────────┐           │
│    │ RDMA Initiator │           │
│    │ (iSER/NVMe-oF) │           │
│    └───────┬────────┘           │
└────────────┼─────────────────────┘
             │ RDMA
             ↓
    ┌────────────────┐
    │ Storage Array  │
    │                │
    │ RDMA Target    │
    │ Serves blocks  │
    │                │
    │ ┌──────────┐   │
    │ │ SSD Pool │   │
    │ └──────────┘   │
    └────────────────┘

Performance:
  Latency: <50 μs (vs 200 μs iSCSI)
  IOPS: 1M+ per server (vs 100K iSCSI)
  CPU: <5% (vs 20-30% iSCSI)
```

---

### Why RDMA is Essential for Storage

#### Problem 1: The CPU Bottleneck

```
Modern NVMe SSDs:
─────────────────
Performance: 7 GB/s read, 1M IOPS
Latency: 10-20 μs

Network over TCP/IP:
────────────────────
10 Gbps = 1.25 GB/s
But CPU overhead: 10-20% per core
At 7 GB/s: ~70% CPU just for networking!

Can't scale!

Network over RDMA:
──────────────────
100 Gbps = 12.5 GB/s
CPU overhead: <1% per core
At 7 GB/s: ~5% CPU for networking

Can scale to 10+ NVMe SSDs per server!
```

---

#### Problem 2: The Latency Mismatch

```
Storage Latency Budget:
───────────────────────

Target: 100 μs end-to-end

Breakdown with TCP/IP:
  Client TCP/IP stack:     15 μs
  Network transit:          5 μs
  Server TCP/IP stack:     15 μs
  Disk I/O:                50 μs
  Return path TCP:         15 μs
  
  Total: 100 μs
  But 60% is software overhead!

Breakdown with RDMA:
  Client RDMA post:         1 μs
  Network transit:          5 μs
  Server RDMA DMA:          1 μs
  Disk I/O:                50 μs
  Return RDMA:              1 μs
  
  Total: 58 μs
  Only 8% is software overhead
  42% faster!
```

---

#### Problem 3: Predictability

```
TCP/IP variability:
───────────────────
P50 latency: 150 μs  ← Median
P99 latency: 800 μs  ← Tail (retransmits!)
P99.9 latency: 5 ms  ← Bad!

Why? Packet loss → retransmit → timeout
Random, unpredictable

RDMA (with lossless):
─────────────────────
P50 latency:  45 μs
P99 latency:  55 μs  ← Consistent!
P99.9 latency: 65 μs

Why? No packet loss → no retransmits
Predictable, consistent
```

---

## Part 3: Storage Use Cases

### Object Storage (S3-compatible)

```
Example: MinIO with RDMA

Traditional S3 backend:
───────────────────────
  PUT 10 MB object:
    - Split into chunks
    - Replicate 3x
    - Total: 30 MB network transfer
    - TCP/IP: 800 μs latency + 30% CPU
    - Throughput: 500 MB/s per server

With RDMA:
──────────
  PUT 10 MB object:
    - Split into chunks
    - Replicate 3x
    - Total: 30 MB network transfer
    - RDMA: 300 μs latency + 3% CPU
    - Throughput: 2 GB/s per server
    
  4x throughput, 10x less CPU
```

---

### Database Replication

```
Example: PostgreSQL replication

Without RDMA:
─────────────
Primary:
  Write to WAL (Write-Ahead Log)
  Send WAL over TCP to replica
  Wait for replica ACK
  
  Replication lag: 5-10 ms typical
  During failover: data loss possible

With RDMA:
──────────
Primary:
  Write to WAL
  RDMA Write to replica memory
  Immediate completion
  
  Replication lag: <1 ms
  During failover: minimal data loss
  
  10x faster replication
  Better consistency
```

---

### Distributed File Systems

```
Example: NFS over RDMA (NFSoRDMA)

Traditional NFS:
────────────────
  Read 1 MB file:
    1. NFS client → RPC call (TCP)
    2. NFS server → Read from disk
    3. NFS server → Copy to network buffer
    4. TCP send to client
    5. Client TCP → Copy to user buffer
    
    Latency: 2 ms
    CPU: High (copies + TCP)
    Throughput: 200 MB/s

NFSoRDMA:
─────────
  Read 1 MB file:
    1. NFS client → RPC call (RDMA Send)
    2. NFS server → Read from disk
    3. NFS server → RDMA Write to client
       (DMA directly from disk cache)
    
    Latency: 500 μs
    CPU: Low (zero-copy)
    Throughput: 1.5 GB/s
    
  4x faster, 10x less CPU
```

---

## Part 4: Why "Shuttling Large Blocks"?

### Yes, But More Nuanced

**RDMA benefits different workloads differently:**

```
Small I/O (4 KB):
─────────────────
RDMA benefit: Latency
  TCP: 150 μs
  RDMA: 50 μs
  
  3x faster
  Benefit: Latency-sensitive apps (databases)

Large I/O (1 MB):
─────────────────
RDMA benefit: Throughput + CPU
  TCP: 400 μs, 20% CPU
  RDMA: 200 μs, 2% CPU
  
  2x faster, 10x less CPU
  Benefit: Bandwidth-intensive apps (backup, analytics)

Mixed workload:
───────────────
RDMA benefit: Both
  Can serve 10x more small I/Os per CPU
  AND maintain high throughput for large I/Os
  
  Benefit: Everything!
```

---

### Network Attached Storage (NAS) Evolution

```
Traditional NAS (NFS/CIFS over TCP):
────────────────────────────────────
┌──────────┐                 ┌──────────┐
│ Clients  │ ─── Ethernet ───│ NAS Box  │
│          │   (TCP/IP)      │          │
│          │                 │ ┌──────┐ │
│          │                 │ │Disks │ │
└──────────┘                 │ └──────┘ │
                             └──────────┘

Performance:
  Throughput: 100-500 MB/s per client
  Latency: 1-5 ms
  CPU: 30-50% (protocol overhead)
  Scalability: Limited (CPU bottleneck)

Modern NAS (NFS/SMB over RDMA):
────────────────────────────────
┌──────────┐                 ┌──────────┐
│ Clients  │ ─── RDMA/RoCE ──│ NAS Box  │
│          │   (lossless)    │          │
│          │                 │ ┌──────┐ │
│          │                 │ │NVMe  │ │
└──────────┘                 │ └──────┘ │
                             └──────────┘

Performance:
  Throughput: 1-5 GB/s per client
  Latency: 50-200 μs
  CPU: 5-10% (minimal overhead)
  Scalability: High (storage bottleneck now!)

10x improvement across the board!
```

---

## Summary: Your Questions Answered

### 1. PFC and TCP Tradeoff

**Not quite "at the detriment" - more nuanced:**

✓ PFC prevents RDMA packet drops (connection failures)  
✓ Can cause brief pauses in RDMA traffic  
✓ TCP mostly unaffected (different priority)  
✓ Modern systems use ECN to minimize PFC activation  
✓ ETS ensures fair bandwidth allocation

**Better framing:** PFC protects RDMA from drops while allowing TCP to coexist. Both can achieve high performance.

---

### 2. Acronyms

**PFC = Priority Flow Control** (IEEE 802.1Qbb)  
- Selective PAUSE for specific priorities
- Prevents packet loss for lossless traffic

**DCB = Data Center Bridging**  
- Umbrella term for lossless Ethernet standards
- Includes PFC, ETS, ECN, DCBX

---

### 3. RDMA in Storage

**Yes, it's about efficient data movement, but much more:**

✓ **Latency:** 50 μs vs 150 μs (3x faster)  
✓ **CPU efficiency:** 2% vs 20% (10x better)  
✓ **Throughput:** 10 GB/s vs 2 GB/s (5x better)  
✓ **Predictability:** Consistent (no retransmit variance)  
✓ **Scalability:** Can serve 10x more IOPS per core

**Use cases:**
- NVMe-oF (disaggregated flash storage)
- Distributed storage (Ceph, S3)
- Block storage (SAN replacement)
- Database replication
- File systems (NFS, SMB)

**The key insight:** Modern NVMe SSDs are SO fast (10 μs latency) that TCP/IP overhead (30 μs) dominates. RDMA eliminates this overhead, making network storage feel "almost local."

**Network attached storage becomes viable for latency-sensitive workloads only with RDMA!**

---

## Hands-On Resources

> Want more? This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all networking and storage topics, see:
> **→ [Complete Networking & Storage Learning Resources](../../02_intermediate/00_NETWORKING_RESOURCES.md)**

**NVMe over Fabrics (NVMe-oF):**
- [NVMe-oF Specification](https://nvmexpress.org/specifications/) - Official NVMe over Fabrics specification
- [NVMe-oF Configuration Guide](https://www.kernel.org/doc/html/latest/nvme/nvme-fc.html) - Linux kernel NVMe-oF documentation

**RDMA for Storage:**
- [RDMA Storage White Papers](https://www.mellanox.com/related-docs/whitepapers/WP_RDMA_for_Storage.pdf) - Comprehensive guide to RDMA in storage systems
- [NVMe-oF over RoCE Best Practices](https://community.mellanox.com/s/article/howto-configure-nvme-over-fabrics) - Practical deployment guide
