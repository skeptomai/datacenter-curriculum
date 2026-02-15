# Part 3: Specialized Topics

**Deep dives into specific areas - pick based on your needs.**

Order is flexible within each specialization. Prerequisites are listed in each document's frontmatter.

---

## Specializations

### [3.1: Storage & RDMA Applications](01_storage/)
**Time:** ~1 hour | **Prerequisites:** RDMA complete

Why RDMA is critical for:
- NVMe-oF (NVMe over Fabrics)
- Distributed storage systems
- Storage performance

**When to specialize:** Storage engineers, distributed systems

---

### [3.2: Overlay Networking Deep-Dives](02_overlay_networking/)
**Time:** ~6 hours | **Prerequisites:** Advanced networking

7 documents covering:
- VXLAN + BGP EVPN with route reflectors
- BGP communities and scaling strategies
- OVS (Open vSwitch) control vs data plane
- Cilium and eBPF data planes
- OpenFlow precompiled model
- Dynamic learning vs prepopulated rules

**When to specialize:** SDN engineers, Kubernetes networking

---

### [3.3: Microservices & Serverless](03_serverless/)
**Time:** ~3 hours | **Prerequisites:** Complete virtualization

Firecracker MicroVMs:
- Relationship to KVM (it's a specialized VMM, not hypervisor)
- Architecture and design decisions
- The three virtio devices (block, network, vsock)

**When to specialize:** Serverless platforms, AWS Lambda understanding

---

### [3.4: CPU & Memory Virtualization](04_cpu_memory/)
**Time:** ~2.5 hours | **Prerequisites:** Hardware optimizations

Deep dive into:
- TLB and EPT mechanics
- Page walk caching with nested paging
- TLB capacity limits and VM density
- VPID implementation details

**When to specialize:** Performance tuning, low-level optimization

---

### [3.5: Compatibility & Legacy Systems](05_compatibility/)
**Time:** ~2.5 hours | **Prerequisites:** KVM knowledge

KVM 32-bit/64-bit compatibility:
- compat_task and ioctl translation
- CONFIG_COMPAT vs CONFIG_KVM_COMPAT
- Historical context with QEMU

**When to specialize:** Kernel development, legacy support

---

## Navigation Tips

- **Don't read everything** - specialize based on your role
- **Prerequisites matter** - listed in each document's YAML frontmatter
- **Time estimates** - plan your learning sessions
- **Cross-references** - documents link to related topics

---

**⏱️ Total Specialized Time:** 15-20 hours (if reading all specializations)
**📊 Approach:** Choose 1-2 specializations, not all
