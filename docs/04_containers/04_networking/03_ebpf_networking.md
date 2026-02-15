---
level: specialized
estimated_time: 65 min
prerequisites:
  - 04_containers/04_networking/02_calico_vs_cilium.md
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
next_recommended:
  - 04_containers/04_networking/04_service_mesh.md
tags: [ebpf, networking, kernel, xdp, tc, cilium, performance]
---

# eBPF Networking: Programmable Kernel Data Path

## Learning Objectives

After reading this document, you will understand:
- What eBPF is and why it's revolutionary
- How eBPF programs are loaded and executed in the kernel
- eBPF hook points for networking (XDP, TC, sockops, sockmap)
- eBPF maps and their role in shared state
- How Cilium uses eBPF for networking
- Writing and loading a simple eBPF program
- Performance benefits and limitations

## Prerequisites

Before reading this, you should understand:
- Linux kernel basics
- Networking fundamentals (packets, TCP/IP)
- Container networking (CNI)
- C programming basics (helpful but not required)

---

## 1. What is eBPF (extended Berkeley Packet Filter)?

### Extended Berkeley Packet Filter

**Original BPF (Berkeley Packet Filter)** (1992):
```
Purpose: Filter packets in tcpdump
Example: "Show me only TCP packets to port 80"

Implementation:
  - Simple virtual machine in kernel
  - Limited instruction set (load, compare, jump, return)
  - Read-only access to packet data

tcpdump 'tcp port 80' → Compiles to BPF bytecode → Runs in kernel
```

**eBPF** (2013+):
```
Extended BPF: Much more powerful

Additions:
  - 64-bit registers (vs 32-bit)
  - More instructions (maps, tail calls, helpers)
  - Can modify packets, not just filter
  - Multiple hook points (not just packet filter)
  - Can attach to: network, tracing, security

Result: General-purpose in-kernel virtual machine
```

### Why eBPF is Revolutionary

**Traditional approach** (kernel modules):
```
Want new kernel functionality?
  → Write kernel module (.ko file)
  → Load with insmod/modprobe

Problems:
  - Kernel crash if bug exists
  - Needs kernel recompile for API changes
  - Security risk (full kernel access)
  - Hard to update (reboot often required)
```

**eBPF approach**:
```
Want new kernel functionality?
  → Write eBPF program
  → Compile to eBPF bytecode
  → Load with bpf() syscall

Benefits:
  - Verified by kernel (can't crash)
  - Sandboxed (limited operations)
  - Dynamic (no reboot)
  - Safe to run untrusted code (after verification)
```

**eBPF verifier** (ensures safety):
```
Before loading, kernel verifies:
  ✓ All paths terminate (no infinite loops)
  ✓ No out-of-bounds memory access
  ✓ All registers initialized before use
  ✓ Only allowed helpers called
  ✓ Bounded loops (kernel 5.3+)

If verification passes → Load into kernel
If verification fails → Reject, no kernel impact
```

---

## 2. eBPF Architecture

### Components

```
┌─────────────────────────────────────────────────┐
│ User Space                                       │
│                                                  │
│  ┌──────────────────┐                           │
│  │ eBPF Program     │                           │
│  │ (C code)         │                           │
│  └────────┬─────────┘                           │
│           ↓                                      │
│  ┌──────────────────┐                           │
│  │ Clang/LLVM       │                           │
│  │ (Compiler)       │                           │
│  └────────┬─────────┘                           │
│           ↓                                      │
│  ┌──────────────────┐       ┌─────────────────┐│
│  │ eBPF Bytecode    │       │ Userspace Loader││
│  │ (.o file)        │ ────→ │ (bpftool, cilium)││
│  └──────────────────┘       └────────┬────────┘│
└─────────────────────────────────────┼──────────┘
                                       │ bpf() syscall
══════════════════════════════════════┼══════════
                                       ↓
┌─────────────────────────────────────────────────┐
│ Kernel Space                                     │
│                                                  │
│  ┌──────────────────┐                           │
│  │ eBPF Verifier    │                           │
│  │ (Safety check)   │                           │
│  └────────┬─────────┘                           │
│           ↓                                      │
│  ┌──────────────────┐                           │
│  │ JIT Compiler     │                           │
│  │ (Bytecode→Native)│                           │
│  └────────┬─────────┘                           │
│           ↓                                      │
│  ┌──────────────────────────────────────────┐  │
│  │ eBPF Programs (Attached to hooks)        │  │
│  │ - XDP (network card)                     │  │
│  │ - TC (traffic control)                   │  │
│  │ - sockops (socket operations)            │  │
│  │ - kprobes (kernel function tracing)      │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │ eBPF Maps (Shared data structures)      │  │
│  │ - Hash maps                              │  │
│  │ - Arrays                                 │  │
│  │ - Queues/Stacks                          │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### eBPF Maps

**Purpose**: Share data between eBPF programs and userspace.

**Map types**:

```c
// Hash table (key-value store)
BPF_MAP_TYPE_HASH
  → Lookup: O(1)
  → Use: IP → Pod mapping, connection tracking

// Array (index-based)
BPF_MAP_TYPE_ARRAY
  → Lookup: O(1)
  → Use: Statistics counters, configuration

// LRU Hash (evicts least recently used)
BPF_MAP_TYPE_LRU_HASH
  → Lookup: O(1), auto-eviction
  → Use: NAT connection tracking (limited size)

// Program array (tail calls)
BPF_MAP_TYPE_PROG_ARRAY
  → Stores eBPF program FDs
  → Use: Chain multiple eBPF programs

// Socket map
BPF_MAP_TYPE_SOCKMAP
  → Stores socket references
  → Use: Socket redirection (bypass TCP/IP stack)
```

**Example map definition**:
```c
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, __u32);    // Key: IP address
    __type(value, struct endpoint_info);
} endpoint_map SEC(".maps");
```

**Userspace interaction**:
```c
// Userspace can read/write maps
int map_fd = bpf_obj_get("/sys/fs/bpf/cilium_endpoint_map");

__u32 key = 0x0a0a0a05;  // 10.10.10.5
struct endpoint_info value;

// Lookup
bpf_map_lookup_elem(map_fd, &key, &value);

// Update
value.node_id = 123;
bpf_map_update_elem(map_fd, &key, &value, BPF_ANY);
```

---

## 3. eBPF Networking Hook Points

### XDP (eXpress Data Path)

**Earliest hook point** (right after NIC receives packet). XDP is eXpress Data Path:

```
Packet flow:
  1. NIC receives packet
  2. XDP program runs ← EARLIEST HOOK
  3. If XDP_PASS: Continue to kernel network stack
  4. If XDP_DROP: Drop packet (no kernel processing)
  5. If XDP_TX: Send packet back out same NIC
  6. If XDP_REDIRECT: Send to another NIC/CPU

Advantage: Minimal CPU cycles consumed before decision
```

**Example use cases**:
- DDoS mitigation (drop attack traffic early)
- Load balancing (redirect to backend)
- Fast packet filtering

**XDP program** (minimal example):
```c
SEC("xdp")
int xdp_drop_tcp_80(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    if (ip->protocol != IPPROTO_TCP)
        return XDP_PASS;

    struct tcphdr *tcp = (void *)(ip + 1);
    if ((void *)(tcp + 1) > data_end)
        return XDP_PASS;

    // Drop all traffic to TCP port 80
    if (tcp->dest == htons(80))
        return XDP_DROP;

    return XDP_PASS;
}
```

**Performance**:
```
Without XDP:
  Packet → NIC → Kernel network stack → iptables → DROP
  Cost: ~5-10µs per packet

With XDP:
  Packet → NIC → XDP program → DROP
  Cost: ~0.5µs per packet

10x faster (useful for DDoS defense: millions of packets/sec)
```

### TC (Traffic Control)

**Hook point**: After routing decision, before/after network device. TC is Traffic Control.

```
Packet flow (ingress):
  1. NIC receives packet
  2. XDP (if attached)
  3. Kernel network stack (routing, firewall)
  4. TC ingress program ← TC HOOK
  5. Delivered to application/container

Packet flow (egress):
  1. Application sends packet
  2. Kernel network stack
  3. TC egress program ← TC HOOK
  4. NIC transmits packet
```

**TC vs XDP**:
```
XDP:
  + Fastest (before kernel stack)
  - Limited context (only raw packet data)
  - Can't access kernel routing

TC:
  + Full packet context (routing tables, conntrack)
  - Slower (after kernel processing)
  + Can modify packets easily
```

**Example**: Cilium uses TC for policy enforcement:
```c
SEC("tc")
int tc_ingress(struct __sk_buff *skb) {
    // Lookup destination pod
    struct endpoint_info *ep;
    ep = bpf_map_lookup_elem(&endpoint_map, &skb->remote_ip4);
    if (!ep)
        return TC_ACT_SHOT;  // Drop

    // Check policy
    struct policy_key key = {
        .src_id = ep->security_id,
        .dst_port = skb->remote_port,
    };

    struct policy_entry *policy;
    policy = bpf_map_lookup_elem(&policy_map, &key);
    if (!policy || policy->action != ALLOW)
        return TC_ACT_SHOT;  // Drop

    return TC_ACT_OK;  // Allow
}
```

### sockops (Socket Operations)

**Hook point**: TCP socket events (connect, accept, send, recv).

```
Purpose: Intercept and modify socket behavior

Events:
  - BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB: Socket accepted
  - BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB: Socket connected
  - BPF_SOCK_OPS_DATA_SEND_CB: Data sent
  - BPF_SOCK_OPS_DATA_RECV_CB: Data received
```

**Example use case**: Automatically set TCP parameters per connection.

```c
SEC("sockops")
int bpf_sockops(struct bpf_sock_ops *skops) {
    switch (skops->op) {
    case BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB:
    case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
        // Set TCP congestion control to BBR
        bpf_setsockopt(skops, SOL_TCP, TCP_CONGESTION,
                       "bbr", sizeof("bbr"));

        // Increase TCP buffer sizes
        int buf_size = 1048576;  // 1 MB
        bpf_setsockopt(skops, SOL_SOCKET, SO_SNDBUF,
                       &buf_size, sizeof(buf_size));

        break;
    }
    return 1;
}
```

### sockmap (Socket Redirection)

**Purpose**: Bypass TCP/IP stack for pod-to-pod communication on same node.

```
Without sockmap:
  Pod A → veth → TC → Kernel IP stack → TC → veth → Pod B
  Cost: ~10µs

With sockmap:
  Pod A → sockmap eBPF → Pod B socket (direct copy)
  Cost: ~1µs

10x faster for same-node traffic!
```

**How it works**:
```c
// 1. Create sockmap (stores socket references)
struct {
    __uint(type, BPF_MAP_TYPE_SOCKMAP);
    __uint(max_entries, 65535);
    __type(key, __u32);
    __type(value, __u64);  // Socket FD
} sock_map SEC(".maps");

// 2. sockops program populates sockmap
SEC("sockops")
int bpf_sockops(struct bpf_sock_ops *skops) {
    if (skops->op == BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB) {
        __u32 key = skops->remote_ip4;
        bpf_sock_map_update(skops, &sock_map, &key, BPF_NOEXIST);
    }
    return 1;
}

// 3. sk_msg program redirects data
SEC("sk_msg")
int bpf_sk_msg(struct sk_msg_md *msg) {
    __u32 key = msg->remote_ip4;
    return bpf_msg_redirect_map(msg, &sock_map, key, BPF_F_INGRESS);
}
```

**Result**:
```
Pod A sends data to Pod B (same node):
  1. Data enters sockmap eBPF program
  2. Lookup dst IP in sockmap
  3. Find Pod B socket reference
  4. Copy data directly to Pod B socket buffer
  5. Bypass: veth, TC, kernel routing, kernel TCP/IP

Huge performance gain!
```

---

## 4. How Cilium Uses eBPF

### Cilium eBPF Architecture

```
┌─────────────────────────────────────────────────┐
│ Pod Network Namespace                            │
│  ┌────────────┐                                 │
│  │ Container  │                                 │
│  │ eth0       │                                 │
│  └──────┬─────┘                                 │
└─────────┼───────────────────────────────────────┘
          │ veth pair
┌─────────┼───────────────────────────────────────┐
│ Host Net│ork Namespace                          │
│  ┌──────┴──────┐                                │
│  │ lxc123      │ ← veth end, TC eBPF attached   │
│  └──────┬──────┘                                │
│         ↓                                        │
│  ┌─────────────────────────────────────────┐   │
│  │ TC Ingress eBPF Program                 │   │
│  │ - Check endpoint map                    │   │
│  │ - Check policy map                      │   │
│  │ - Redirect or drop                      │   │
│  └─────────────────────────────────────────┘   │
│         ↓                                        │
│  ┌─────────────────────────────────────────┐   │
│  │ eBPF Maps                               │   │
│  │ - cilium_lxc (endpoints)                │   │
│  │ - cilium_policy_v2 (policies)           │   │
│  │ - cilium_lb4_services_v2 (load balance) │   │
│  │ - cilium_ct4_global (conntrack)         │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### eBPF Maps in Cilium

**1. Endpoint Map** (`cilium_lxc`):
```
Key: IP address
Value: {
  endpoint_id: 1234,
  security_id: 5678,
  ifindex: 42,  // veth interface index
  ...
}

Purpose: Map pod IP → metadata
```

**2. Policy Map** (`cilium_policy_v2`):
```
Key: {
  endpoint_id: 1234,
  identity: 5678,  // Source security identity
  proto: 6,        // TCP
  port: 8080,
}
Value: {
  action: ALLOW/DROP,
  ...
}

Purpose: Enforce NetworkPolicy
```

**3. Service Map** (`cilium_lb4_services_v2`):
```
Key: {
  address: 10.96.0.10,  // Service ClusterIP
  port: 80,
}
Value: {
  backend_slot: 3,  // Number of backends
  ...
}

Purpose: Service load balancing (replaces kube-proxy)
```

**4. Connection Tracking** (`cilium_ct4_global`):
```
Key: {
  src_ip, dst_ip, src_port, dst_port, proto
}
Value: {
  packets, bytes, timestamp, ...
}

Purpose: Track connections (NAT, reverse path)
```

### Example: Pod-to-Pod Flow with Cilium eBPF

```
Pod A (10.244.0.5) → Pod B (10.244.1.10) with NetworkPolicy

1. Pod A sends packet: dst=10.244.1.10
2. Packet leaves Pod A veth, enters host netns
3. TC eBPF program (attached to lxc_A) runs:

   a. Lookup src IP (10.244.0.5) in cilium_lxc map
      → endpoint_id: 100, security_id: 200

   b. Lookup dst IP (10.244.1.10) in cilium_lxc map
      → endpoint_id: 101, security_id: 201

   c. Build policy key:
      {endpoint_id: 101, identity: 200, proto: TCP, port: 8080}

   d. Lookup in cilium_policy_v2 map
      → action: ALLOW

   e. If same node: bpf_redirect to lxc_B interface
      If different node: Continue to routing

4. Packet delivered to Pod B

All in eBPF (no iptables, no kernel routing for same-node)
```

---

## 5. Writing and Loading eBPF Programs

### Simple Example: Packet Counter

**Source code** (packet_counter.c):
```c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>

// Map to store packet count
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} packet_count SEC(".maps");

// XDP program
SEC("xdp")
int count_packets(struct xdp_md *ctx) {
    __u32 key = 0;
    __u64 *count;

    // Lookup counter
    count = bpf_map_lookup_elem(&packet_count, &key);
    if (count)
        __sync_fetch_and_add(count, 1);  // Atomic increment

    return XDP_PASS;  // Pass packet to kernel
}

char _license[] SEC("license") = "GPL";
```

**Compile**:
```bash
clang -O2 -target bpf -c packet_counter.c -o packet_counter.o
```

**Load and attach**:
```bash
# Using ip command
sudo ip link set dev eth0 xdp obj packet_counter.o sec xdp

# Or using bpftool
sudo bpftool prog load packet_counter.o /sys/fs/bpf/count_packets
sudo bpftool net attach xdp id <prog_id> dev eth0
```

**Read map from userspace**:
```bash
# Get map ID
sudo bpftool map list

# Read counter
sudo bpftool map dump id <map_id>
```

**Python userspace loader** (using BCC):
```python
from bcc import BPF

# Load eBPF program
b = BPF(src_file="packet_counter.c")
fn = b.load_func("count_packets", BPF.XDP)

# Attach to interface
b.attach_xdp("eth0", fn, 0)

# Read counter periodically
import time
while True:
    count = b["packet_count"][0].value
    print(f"Packets: {count}")
    time.sleep(1)
```

---

## 6. Performance Analysis

### eBPF vs iptables

**Benchmark setup**: 1000 NetworkPolicies, 10 Gbps traffic.

| Operation             | iptables   | eBPF       |
|------------------------|------------|------------|
| Policy lookup          | 1.2 ms     | 0.015 ms   |
| Throughput (10 Gbps)   | 7.2 Gbps   | 9.6 Gbps   |
| Latency (p99)          | 1.5 ms     | 0.15 ms    |
| CPU usage              | 25%        | 10%        |
| Policy update time     | 10 sec     | 0.5 sec    |

**Why eBPF is faster**:
```
iptables:
  - Linear rule scan: O(N) for N rules
  - Context switches (userspace ↔ kernel)
  - Packet copied multiple times

eBPF:
  - Hash table lookup: O(1)
  - Runs in kernel (no context switch)
  - In-place packet modification
```

### XDP Performance

**Packet processing capacity**:

| Method              | Packets/sec  |
|---------------------|--------------|
| Kernel networking   | 1-2 Mpps     |
| iptables            | 1 Mpps       |
| TC eBPF             | 5-10 Mpps    |
| XDP eBPF            | 20-40 Mpps   |

**Use case**: DDoS mitigation.
```
Attack: 100 Gbps SYN flood
  → 148 million packets/sec (64-byte packets)

XDP can process 40 Mpps per core
  → Need ~4 CPU cores to handle attack
  → Drop attack packets in XDP (0.5µs per packet)

iptables would be overwhelmed (1 Mpps capacity)
```

---

## 7. Limitations and Challenges

### eBPF Verifier Restrictions

**1. No unbounded loops** (before kernel 5.3):
```c
// ✗ REJECTED: Unbounded loop
for (int i = 0; i < n; i++) {
    // ...
}

// ✓ ACCEPTED: Bounded loop (compile-time constant)
#pragma unroll
for (int i = 0; i < 10; i++) {
    // ...
}
```

**2. Limited stack size** (512 bytes):
```c
// ✗ REJECTED: Stack overflow
char buf[4096];  // Too large

// ✓ ACCEPTED: Use per-CPU array map instead
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, char[4096]);
} scratch_buf SEC(".maps");
```

**3. No function calls** (except helpers and tail calls):
```c
// ✗ REJECTED: Arbitrary function call
void my_function() { ... }
my_function();

// ✓ ACCEPTED: Always inline
static __always_inline void my_function() { ... }
my_function();  // Inlined by compiler
```

### Kernel Version Requirements

**eBPF features by kernel version**:

| Feature                | Kernel     |
|------------------------|------------|
| Basic eBPF             | 3.18+      |
| XDP                    | 4.8+       |
| sockmap                | 4.14+      |
| BPF-to-BPF calls       | 4.16+      |
| Bounded loops          | 5.3+       |
| BPF_LINK (pinning)     | 5.7+       |

**Production**: Kernel 4.19+ recommended (LTS), 5.10+ ideal.

### Debugging Challenges

**eBPF programs are hard to debug**:
```
Problems:
  - No printf() (can't print to console)
  - Limited error messages
  - Verifier errors cryptic

Debugging techniques:
  1. bpf_printk() → Writes to trace_pipe
     tail -f /sys/kernel/debug/tracing/trace_pipe

  2. bpf_trace_printk() → Same, with formatting
     bpf_trace_printk("Value: %d", value);

  3. Use eBPF maps to export debug data
     Update map with debug values, read from userspace

  4. bpftool for inspection
     bpftool prog dump xlated id <id>  # Disassemble
     bpftool map dump id <id>          # View map contents
```

---

## Quick Reference

### eBPF Hook Points (Networking)

| Hook      | Location                  | Use Case                          |
|-----------|---------------------------|-----------------------------------|
| XDP       | NIC driver                | DDoS defense, load balancing      |
| TC        | Traffic control (qdisc)   | Policy, NAT, encapsulation        |
| sockops   | TCP socket events         | TCP tuning, monitoring            |
| sockmap   | Socket data               | Same-node fast path               |
| cgroup    | cgroup ingress/egress     | Per-container firewalling         |

### eBPF Map Types

| Type                  | Lookup    | Use Case                          |
|-----------------------|-----------|-----------------------------------|
| BPF_MAP_TYPE_HASH     | O(1)      | IP → endpoint mapping             |
| BPF_MAP_TYPE_ARRAY    | O(1)      | Statistics, configuration         |
| BPF_MAP_TYPE_LRU_HASH | O(1)      | Connection tracking (auto-evict)  |
| BPF_MAP_TYPE_PROG_ARRAY| O(1)     | Tail calls (program chaining)     |
| BPF_MAP_TYPE_SOCKMAP  | N/A       | Socket references                 |

### Common Commands

```bash
# List loaded eBPF programs
sudo bpftool prog list

# Show program details
sudo bpftool prog show id <id>

# Dump eBPF bytecode
sudo bpftool prog dump xlated id <id>

# List eBPF maps
sudo bpftool map list

# Dump map contents
sudo bpftool map dump id <id>

# Attach XDP program
sudo bpftool net attach xdp id <prog_id> dev eth0

# Detach XDP program
sudo bpftool net detach xdp dev eth0

# View eBPF printk output
sudo cat /sys/kernel/debug/tracing/trace_pipe
```

---

## Summary

**eBPF** is a revolutionary technology for programmable kernel functionality:
- Safe: Verified before loading (can't crash kernel)
- Fast: Runs in kernel, JIT-compiled to native code
- Flexible: Hooks into network, tracing, security subsystems

**Networking hook points**:
- **XDP**: Fastest, NIC-level (DDoS defense)
- **TC**: Full context, policy enforcement
- **sockops/sockmap**: Socket-level, same-node fast path

**eBPF maps**: Shared state between programs and userspace.
- Hash maps for lookups (O(1))
- Arrays for config/stats
- Sockmaps for socket redirection

**Cilium uses eBPF for**:
- NetworkPolicy enforcement (hash table, not iptables)
- Service load balancing (replaces kube-proxy)
- Socket acceleration (sockmap for same-node)
- Observability (Hubble flow logs)

**Performance**: 10-100x faster than iptables for complex policies.

**Limitations**:
- Verifier restrictions (stack size, loops)
- Kernel version requirements (4.19+ recommended)
- Debugging challenges (no printf, cryptic errors)

**Next**: Now that you understand eBPF, we'll explore how **service meshes** use eBPF and sidecars for advanced traffic management.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[eBPF.io Learning Resources](https://ebpf.io/)** - Comprehensive introduction to eBPF, tutorials, and use cases
- **[cilium/ebpf Go Library](https://github.com/cilium/ebpf)** - Pure Go library for loading and managing eBPF programs
- **[BPF Performance Tools Book](http://www.brendangregg.com/bpf-performance-tools-book.html)** - Definitive guide to using eBPF for performance analysis

---

## Related Documents

- **Previous**: `04_networking/02_calico_vs_cilium.md` - Cilium's eBPF usage
- **Next**: `04_networking/04_service_mesh.md` - Service mesh architectures
- **Foundation**: `01_fundamentals/01_cgroups_namespaces.md` - Kernel primitives
- **Related**: `05_specialized/03_advanced_networking/03_ovs_cilium_geneve_explained.md` - Cilium deep dive
