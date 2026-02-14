# Part 1: Foundations

**Start here if you're new to datacenter infrastructure.**

This section covers the essential building blocks you need before diving into advanced topics. Read these documents **in order** for the best learning experience.

---

## What You'll Learn

By completing the foundations, you'll understand:
- ✅ **Why virtualization is hard** and how hardware solves it
- ✅ **How VM exits work** - the fundamental virtualization mechanism
- ✅ **Modern datacenter network topology** - where VMs actually run
- ✅ **Spine-leaf architecture** - the standard for modern datacenters
- ✅ **ECMP load balancing** - how traffic flows across multiple paths

---

## Learning Tracks

### Track 1: Virtualization Fundamentals 🎯 HIGHEST PRIORITY
**Time:** ~1.5 hours | **Directory:** [01_virtualization_basics/](01_virtualization_basics/)

**Essential for:** Everyone working with virtual machines

1. [The Ring-0 Problem](01_virtualization_basics/01_the_ring0_problem.md) (20 min)
   - Why you can't run two OSes in Ring 0 simultaneously
   - The core challenge virtualization solves

2. [Hardware Solution (VT-x/AMD-V)](01_virtualization_basics/02_hardware_solution.md) (30 min)
   - How Intel VT-x creates two Ring-0 environments
   - Why EPT eliminates most VM exits
   - 5 key hardware mechanisms

3. [VM Exit Basics](01_virtualization_basics/03_vm_exit_basics.md) (25 min)
   - The 6-step exit cycle
   - Common exit reasons
   - VMCS structure

**Outcome:** Understand how modern virtualization actually works

---

### Track 2: Datacenter Network Topology
**Time:** ~2 hours | **Directory:** [02_datacenter_topology/](02_datacenter_topology/)

**Essential for:** Network engineers and understanding where VMs connect

1. [Modern Datacenter Network Topology](02_datacenter_topology/01_modern_topology.md) (40 min)
   - Link speeds (25G, 100G, 400G)
   - Oversubscription ratios
   - East-West vs North-South traffic

2. [Spine-Leaf Server Hierarchy](02_datacenter_topology/02_server_hierarchy.md) (30 min)
   - Three layers: Servers → Leaf switches → Spine switches
   - Why every server is equidistant from every other

3. [3-Tier vs Spine-Leaf Differences](02_datacenter_topology/03_3tier_vs_spine_leaf.md) (30 min)
   - Why spine-leaf is fundamentally different
   - Scaling philosophy
   - RDMA enablement

4. [ECMP Load Balancing](02_datacenter_topology/04_ecmp_load_balancing.md) (50 min)
   - 5-tuple hashing
   - Per-flow vs per-packet load balancing
   - Statistical distribution across paths

**Outcome:** Understand modern datacenter physical infrastructure

---

##What's Next?

After completing foundations, proceed to:

**Virtualization Path:**
→ [Part 2.3: Complete Virtualization](../02_intermediate/03_complete_virtualization/) - Full evolution from Xen to SR-IOV

**Networking Path:**
→ [Part 2.1: Advanced Networking](../02_intermediate/01_advanced_networking/) - VLAN vs VXLAN, overlays
→ [Part 2.2: RDMA](../02_intermediate/02_rdma/) - High-performance networking

**Full Stack:**
→ Follow [all learning paths](../00_START_HERE.md) sequentially

---

**⏱️ Total Foundation Time:** ~3.5 hours
**📊 Progress:** Complete this to be ready for intermediate topics
