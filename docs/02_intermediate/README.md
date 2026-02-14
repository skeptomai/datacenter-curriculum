# Part 2: Intermediate Concepts

**Build on your foundational knowledge with deeper technical understanding.**

This section assumes you've completed [Part 1: Foundations](../01_foundations/) or have equivalent background knowledge.

---

## What's Here

### [2.1: Advanced Networking](01_advanced_networking/)
**Time:** ~1.5 hours | **Prerequisites:** Foundation networking

- VLAN vs VXLAN comparison
- Overlay network mechanics (VXLAN/Geneve encapsulation)

**When to read:** After understanding datacenter topology basics

---

### [2.2: RDMA - High-Performance Networking](02_rdma/)
**Time:** ~2.5 hours | **Prerequisites:** Foundation networking

- Why RDMA is a HOST optimization (not network)
- RoCEv2, InfiniBand, iWARP protocol variants
- How to make Ethernet lossless (DCB, PFC, ECN)
- NUMA considerations for RDMA performance

**When to read:** Before storage deep-dives or SR-IOV

---

### [2.3: Complete Virtualization Understanding](03_complete_virtualization/)
**Time:** ~3.5 hours | **Prerequisites:** Foundation virtualization

Complete evolution story:
- Software-based (VMware binary translation)
- Paravirtualization (Xen hypercalls)
- Hardware-assisted (KVM + VT-x)
- Device virtualization (virtio, vhost)
- Direct assignment (VFIO, SR-IOV)

Plus: Exit minimization strategies and hardware optimizations

**When to read:** After virtualization fundamentals for the complete picture

---

## Learning Paths Through Intermediate

**Path A: Virtualization Engineer** 🎯
1. Complete 2.3 (all 4 documents)
2. Optional: 2.2 for RDMA context
3. Skip 2.1 (come back if needed)

**Path B: Network Engineer**
1. Complete 2.1 → 2.2 (networking stack)
2. Optional: 2.3 for VM context
3. Continue to specialized overlay networking

**Path C: Storage Engineer**
1. Complete 2.2 (RDMA essential for modern storage)
2. Then 2.3.4 (device passthrough)
3. Continue to specialized storage

---

**⏱️ Total Intermediate Time:** 7-9 hours (if reading all)
**📊 Progress:** Complete your chosen path before specialized topics
