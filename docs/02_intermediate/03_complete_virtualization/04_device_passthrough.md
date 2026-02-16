---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 02_intermediate/03_complete_virtualization/01_evolution_complete.md
  - 02_intermediate/03_complete_virtualization/03_hardware_optimizations.md
next_recommended:
  - 05_specialized/04_cpu_memory/01_tlb_ept_explained.md
  - 05_specialized/03_serverless/01_firecracker_relationship.md
tags: [virtualization, sr-iov, vfio, iommu, passthrough, performance]
---

# SR-IOV, Device Passthrough, and IOMMU Deep Dive

## Part 1: The Problem - Direct Device Access Without Isolation

### Why Can't We Just Give Devices to VMs?

**The fundamental security issue:**

```
Without protection:
───────────────────

VM wants to access disk
  ↓
Device uses DMA (Direct Memory Access)
  ↓
Device can read/write ANY physical memory!
  ↓
VM could program device to access:
  - Other VMs' memory
  - Hypervisor memory
  - Host kernel memory
  
DISASTER! Complete security breach!
```

**The DMA problem:**

```
Traditional DMA (no virtualization):
────────────────────────────────────

Device driver (in kernel):
  buffer = malloc(4096);
  physical_addr = virt_to_phys(buffer);
  
  Tell device: "DMA to physical address 0x12345000"
  
Device:
  Receives command: DMA to 0x12345000
  Places data directly at that physical address
  No CPU involvement
  
This works because:
  - Only kernel can program device
  - Kernel is trusted
  - Single address space

With VMs:
─────────

VM1 driver thinks it has physical address 0x12345000
  But that's Guest Physical Address (GPA)
  Real host physical address (HPA) is 0x98765000
  
If device DMAs to 0x12345000 (what VM told it):
  → Wrong memory!
  → Might be VM2's memory
  → Might be hypervisor memory
  
Security disaster!
```

---

## Part 2: IOMMU - The Solution

### What is IOMMU?

**IOMMU = I/O Memory Management Unit**

```
Intel calls it: VT-d (Virtualization Technology for Directed I/O)
AMD calls it: AMD-Vi (AMD I/O Virtualization)

Just like MMU translates virtual addresses for CPU:
  CPU MMU: Virtual Address → Physical Address
  
IOMMU translates DMA addresses for devices:
  IOMMU: Device Virtual Address (IOVA) → Host Physical Address (HPA)
```

---

### IOMMU Architecture

```
Without IOMMU:
──────────────

┌─────────┐
│   CPU   │─────────────────┐
└─────────┘                 │
                            ▼
┌─────────────────────────────────┐
│         Memory Bus              │
└──────────┬──────────────────────┘
           │
           ├──────→ Memory (RAM)
           │
           └──────→ PCIe Bus
                        ↓
                   ┌─────────┐
                   │ NIC     │ ← Device can DMA anywhere!
                   └─────────┘

Device issues DMA:
  "Write to address 0x12345000"
  → Goes directly to that physical address
  → No translation, no protection


With IOMMU:
───────────

┌─────────┐
│   CPU   │─────────────────┐
└─────────┘                 │
                            ▼
                     ┌─────────────┐
                     │   IOMMU     │ ← Intercepts device DMA!
                     └──────┬──────┘
                            │
┌───────────────────────────▼───────────┐
│            Memory Bus                 │
└──────────┬────────────────────────────┘
           │
           ├──────→ Memory (RAM)
           │
           └──────→ PCIe Bus
                        ↓
                   ┌─────────┐
                   │ NIC     │
                   └─────────┘

Device issues DMA:
  "Write to IOVA 0x12345000"
  → IOMMU intercepts
  → Looks up in page table for THIS device
  → Translates to HPA 0x98765000
  → Writes to correct physical address
  → Protection enforced!
```

---

### IOMMU Page Tables

**Per-device address spaces:**

```
Each device (or group) has its own IOMMU page table:

VM1's NIC:
┌─────────────────────────────────────┐
│ IOMMU Page Table for NIC-VM1        │
├──────────────┬──────────────────────┤
│ IOVA         │ HPA                  │
├──────────────┼──────────────────────┤
│ 0x00000000   │ 0x80000000 (VM1 RAM) │
│ 0x00001000   │ 0x80001000           │
│ 0x00002000   │ 0x80002000           │
│ ...          │ ...                  │
│ 0x10000000   │ Invalid (protect!)   │
└──────────────┴──────────────────────┘

Device can only DMA to addresses in its table
Cannot access VM2 or hypervisor memory!


VM2's NIC:
┌─────────────────────────────────────┐
│ IOMMU Page Table for NIC-VM2        │
├──────────────┬──────────────────────┤
│ IOVA         │ HPA                  │
├──────────────┼──────────────────────┤
│ 0x00000000   │ 0x90000000 (VM2 RAM) │
│ 0x00001000   │ 0x90001000           │
│ ...          │ ...                  │
└──────────────┴──────────────────────┘

Completely isolated!
Each device sees only its VM's memory
```

---

### IOMMU Translation Process

```
Device performs DMA:
────────────────────

1. NIC-VM1 wants to DMA packet to address 0x12345000 (IOVA)

2. NIC issues memory write on PCIe bus:
   Write: data=<packet>, address=0x12345000

3. IOMMU intercepts (sitting on memory bus):
   - Identifies source device (PCIe bus:dev:func)
   - Looks up which page table to use
   - Finds: "NIC-VM1 uses page table at 0xABCD0000"

4. IOMMU walks page table (similar to CPU page walk):
   - Read page table base: 0xABCD0000
   - Extract indices from IOVA 0x12345000
   - PML4 index, PDPT index, PD index, PT index
   - Walk 4 levels
   - Find final entry: IOVA 0x12345000 → HPA 0x80345000

5. IOMMU checks permissions:
   - Is mapping valid? Yes
   - Is write allowed? Yes
   - Is device allowed? Yes

6. IOMMU issues real memory write:
   Write: data=<packet>, address=0x80345000 (HPA)

7. Memory controller writes to RAM at 0x80345000

8. Done! VM1 receives packet in correct memory location

Time: ~100-200 ns overhead (vs no IOMMU)
But provides complete isolation!
```

---

## Part 3: Device Passthrough (VFIO)

### What is VFIO?

**VFIO = Virtual Function I/O**

```
VFIO is the Linux framework for safely passing devices to VMs

Key components:
  1. IOMMU driver (enables translation)
  2. VFIO driver (manages device assignment)
  3. User space API (QEMU/KVM uses this)
  4. Device groups (isolation boundaries)
```

---

### Passthrough Setup

**Step-by-step device assignment:**

```
Step 1: Enable IOMMU in BIOS/UEFI
──────────────────────────────────
Intel: Enable "VT-d"
AMD: Enable "AMD-Vi" or "IOMMU"


Step 2: Enable IOMMU in kernel
───────────────────────────────
Boot parameter: intel_iommu=on (Intel)
                amd_iommu=on (AMD)

Kernel loads:
  - iommu driver
  - vfio-pci driver


Step 3: Identify device
────────────────────────
lspci -nn | grep Ethernet

Output:
  01:00.0 Ethernet controller [0200]: Intel Corporation 82599ES [8086:10fb]
  
PCIe address: 01:00.0 (bus:device.function)
Vendor:Device: 8086:10fb


Step 4: Unbind from host driver
────────────────────────────────
echo "0000:01:00.0" > /sys/bus/pci/drivers/ixgbe/unbind

Device no longer usable by host


Step 5: Bind to VFIO
─────────────────────
echo "8086 10fb" > /sys/bus/pci/drivers/vfio-pci/new_id
echo "0000:01:00.0" > /sys/bus/pci/drivers/vfio-pci/bind

Device now managed by VFIO


Step 6: Configure IOMMU page tables
────────────────────────────────────
(Done by VFIO driver automatically)

Create IOMMU context for this device
Set up page tables mapping GPA → HPA
Map VM's memory into IOMMU tables


Step 7: Pass to VM
──────────────────
qemu-system-x86_64 \
  -device vfio-pci,host=01:00.0 \
  ...

VM boots, sees real NIC as PCIe device
Loads native driver (ixgbe in this case)
Full speed, direct access!
```

---

### What the Guest Sees

```
Inside the VM:
──────────────

lspci

Output:
  00:05.0 Ethernet controller: Intel Corporation 82599ES
  
Guest sees a REAL PCIe device!
Not emulated, not paravirtualized
Actual hardware

Guest loads native driver:
  modprobe ixgbe
  
Driver works normally:
  - Programs device registers
  - Sets up DMA rings
  - Enables interrupts
  - Full hardware features

From guest perspective:
  It's bare metal!
  No difference from physical server
```

---

### DMA Flow with Passthrough

```
Guest driver sends packet:
──────────────────────────

1. Guest driver (ixgbe):
   skb = alloc_skb(1500);
   // Fill with packet data
   
   guest_virt_addr = skb->data;       // 0xffff888012345000
   guest_phys_addr = virt_to_phys();  // 0x12345000 (GPA)
   
   // Program NIC descriptor:
   tx_desc->buffer_addr = 0x12345000;  // GPA!
   tx_desc->length = 1500;
   
   // Kick NIC (write to tail register)
   writel(tail_idx, NIC_TDT_REG);

2. NIC reads descriptor:
   DMA read from descriptor ring
   IOMMU translates descriptor address
   Gets buffer_addr = 0x12345000 (IOVA from guest's perspective)

3. NIC DMAs packet data:
   DMA read from 0x12345000
   → IOMMU intercepts
   → Looks up in VM1-NIC page table
   → Translates: 0x12345000 (GPA) → 0x80345000 (HPA)
   → Real DMA from 0x80345000
   
4. NIC sends packet on wire

5. NIC writes completion:
   DMA write to completion ring
   IOMMU translates
   Guest receives completion

No hypervisor involvement!
No VM exits for DMA!
```

---

## Part 4: SR-IOV (Single Root I/O Virtualization)

### The Problem with Basic Passthrough

```
Without SR-IOV:
───────────────

One physical NIC = One VM

┌─────────┐
│  Host   │
│         │
│  ┌───┐  │
│  │VM1│  │ ← Gets entire NIC (passthrough)
│  └───┘  │
│         │
│  ┌───┐  │
│  │VM2│  │ ← Needs another physical NIC!
│  └───┘  │
│         │
└─────────┘

Problem:
  - Need one NIC per VM
  - Expensive
  - Uses PCIe slots
  - Doesn't scale

Can't share one NIC between VMs
  (Each needs dedicated device)
```

---

### SR-IOV Solution

**Single physical NIC → Many virtual NICs**

```
SR-IOV NIC:
───────────

One physical device presents multiple PCIe functions:

┌──────────────────────────────────────────┐
│     Physical NIC (Intel X710)            │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ Physical Function (PF)             │ │ ← Full device
│  │ - Configuration                    │ │   Host manages
│  │ - Manages VFs                      │ │
│  │ - Has all features                 │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  VF 0   │ │  VF 1   │ │  VF 2   │  │ ← Virtual Functions
│  │ (Light) │ │ (Light) │ │ (Light) │  │   Pass to VMs
│  └─────────┘ └─────────┘ └─────────┘  │
│       ...                                │
│  ┌─────────┐ ┌─────────┐               │
│  │  VF 62  │ │  VF 63  │               │ ← Up to 64 VFs typical
│  └─────────┘ └─────────┘               │
└──────────────────────────────────────────┘

PCIe view:
  Bus 01:00.0 = PF (managed by host)
  Bus 01:00.1 = VF 0 (passed to VM1)
  Bus 01:00.2 = VF 1 (passed to VM2)
  Bus 01:00.3 = VF 2 (passed to VM3)
  ...
```

---

### How SR-IOV Works

**Hardware partitioning:**

```
Physical NIC resources:
───────────────────────

TX Queues: 128 total
RX Queues: 128 total
MAC addresses: 64 (one per VF)
VLAN filters: 64
Interrupts: 64 MSI-X vectors

SR-IOV divides these:

PF (host):
  TX queues: 2
  RX queues: 2
  Management only
  
VF 0 (VM1):
  TX queues: 2
  RX queues: 2
  MAC: aa:bb:cc:dd:ee:00
  Own MSI-X vectors
  
VF 1 (VM2):
  TX queues: 2
  RX queues: 2
  MAC: aa:bb:cc:dd:ee:01
  Own MSI-X vectors
  
... (repeat for all VFs)

Each VF is isolated:
  - Separate queues
  - Separate interrupts
  - Separate MAC
  - Separate IOMMU mapping
```

---

### VF as Seen by Guest

```
Guest (VM1) perspective:
────────────────────────

lspci:
  00:05.0 Ethernet controller: Intel Corporation X710 Virtual Function

Looks like a real NIC!
But lighter weight (VF not PF)

Guest loads VF driver:
  modprobe iavf (Intel Adaptive Virtual Function driver)
  
Driver sees:
  - 2 TX queues
  - 2 RX queues  
  - MAC address
  - Can send/receive
  - Full speed DMA

Guest doesn't know:
  - It's a VF not PF
  - Other VFs exist
  - Sharing physical hardware

Isolation via IOMMU:
  VF0 can only DMA to VM1's memory
  VF1 can only DMA to VM2's memory
  Complete separation
```

---

### SR-IOV Packet Flow

```
VM1 sends packet via VF0:
─────────────────────────

1. Guest driver (iavf in VM1):
   skb = alloc_skb(1500);
   guest_phys = virt_to_phys(skb->data);  // 0x12345000 (GPA)
   
   // Program VF0 TX descriptor
   vf0_tx_desc[0].addr = 0x12345000;
   vf0_tx_desc[0].len = 1500;
   
   // Kick VF0 queue
   writel(1, VF0_TX_TAIL);

2. NIC hardware (VF0 context):
   - Read descriptor from VF0 TX queue
   - See buffer address: 0x12345000 (IOVA)
   - DMA read packet data
   
3. IOMMU for VF0:
   - IOVA 0x12345000 → HPA 0x80345000 (VM1's memory)
   - DMA from 0x80345000
   
4. NIC hardware:
   - Get packet data
   - Add Ethernet header (src MAC = VF0's MAC)
   - Send on wire
   
5. NIC writes completion to VF0 TX completion queue
   - IOMMU translates
   - VM1 gets completion


VM2 receives packet via VF1:
────────────────────────────

1. Packet arrives at physical NIC

2. NIC hardware:
   - Look at destination MAC
   - Match to VF1's MAC address
   - Route to VF1 RX queue

3. NIC DMAs packet to VF1 RX buffer:
   - VF1 RX descriptor has buffer address (IOVA)
   - IOMMU for VF1 translates
   - IOVA 0x22000000 → HPA 0x90100000 (VM2's memory)
   - DMA write to 0x90100000

4. NIC sends MSI-X interrupt to VF1
   - Injected into VM2
   
5. VM2 guest driver processes packet:
   - Sees packet in RX buffer
   - Processes normally

Isolation:
  VF0 can't access VF1's buffers
  Different IOMMU page tables
  Hardware enforced
```

---

## Part 5: Performance Comparison

### Benchmark: 10 Gbps Network

```
┌────────────────────┬──────────┬──────────┬───────────┐
│ Method             │ Throughput│ Latency  │ CPU Usage │
├────────────────────┼──────────┼──────────┼───────────┤
│ Emulated e1000     │ 2 Gbps   │ 100 μs   │ 80%       │
│ (full emulation)   │          │          │           │
│                    │          │          │           │
│ virtio-net         │ 9.5 Gbps │ 15 μs    │ 20%       │
│ (paravirt)         │          │          │           │
│                    │          │          │           │
│ vhost-net          │ 9.8 Gbps │ 10 μs    │ 10%       │
│ (kernel virtio)    │          │          │           │
│                    │          │          │           │
│ SR-IOV VF          │ 9.95 Gbps│ 5 μs     │ 2%        │
│ (passthrough)      │          │          │           │
│                    │          │          │           │
│ Bare metal         │ 10 Gbps  │ 4 μs     │ 1%        │
│ (no virtualization)│          │          │           │
└────────────────────┴──────────┴──────────┴───────────┘

SR-IOV is 98-99% of bare metal!
```

---

### Why SR-IOV is Fastest

```
virtio-net:
───────────
Guest → virtqueue → VM exit → KVM → vhost → NIC
  Overhead:
    - virtqueue management
    - VM exit (even with vhost)
    - Shared memory coordination
    - Batching helps but not perfect

SR-IOV:
───────
Guest → VF → NIC (direct!)
  Overhead:
    - IOMMU translation (~100 ns)
    - That's it!
  
No VM exits for data path!
No hypervisor involvement!
Direct hardware access!
```

---

### IOMMU Performance Impact

```
Without IOMMU (unsafe):
───────────────────────
Device DMA: 50 ns
  Straight to memory
  
With IOMMU:
───────────
Device DMA: 150 ns
  - Device issues DMA (10 ns)
  - IOMMU intercepts (20 ns)
  - Page table walk (80 ns, can be cached)
  - Memory access (40 ns)
  
3x slower than no protection

BUT:
  - Still faster than virtio (no VM exits)
  - Caching helps (IOMMU TLB)
  - Modern IOMMUs are fast
  - Security worth the cost

Real world: <5% performance impact
```

---

## Part 6: IOMMU Groups and Isolation

### What is an IOMMU Group?

**Isolation boundary:**

```
Problem: PCIe topology matters

┌────────────┐
│    CPU     │
└─────┬──────┘
      │
┌─────▼──────────┐
│  PCIe Root     │
└──┬──────────┬──┘
   │          │
   │     ┌────▼──────┐
   │     │PCIe Bridge│
   │     └─┬─────┬───┘
   ↓       ↓     ↓
┌──────┐ ┌────┐┌────┐
│ NIC1 │ │NIC2││NIC3│
└──────┘ └────┘└────┘

IOMMU groups:
  Group 0: NIC1 (isolated)
  Group 1: Bridge + NIC2 + NIC3 (shared)

Why?
  NIC2 and NIC3 share a bridge
  Bridge can forward transactions
  NIC2 could potentially access NIC3's DMA
  Must be in same group!

If passing NIC2 to VM:
  - Must pass entire group
  - NIC3 also assigned
  - Or leave both in host
```

---

### Viewing IOMMU Groups

```bash
#!/bin/bash
# Show IOMMU groups

for d in /sys/kernel/iommu_groups/*/devices/*; do
    n=${d#*/iommu_groups/*}
    n=${n%%/*}
    printf 'IOMMU Group %s ' "$n"
    lspci -nns "${d##*/}"
done

Output:
──────
IOMMU Group 0: 00:00.0 Host bridge [0600]: Intel
IOMMU Group 1: 00:01.0 PCI bridge [0604]: Intel
IOMMU Group 2: 01:00.0 Ethernet [0200]: Intel 82599ES [8086:10fb]
IOMMU Group 2: 01:00.1 Ethernet [0200]: Intel 82599ES [8086:10fb]
IOMMU Group 3: 02:00.0 NVMe [0108]: Samsung 970 EVO

Group 2 has 2 ports: Must assign both or neither
```

---

## Part 7: SR-IOV with RDMA

**Perfect combination for storage:**

```
RoCE + SR-IOV:
──────────────

Physical NIC: Mellanox ConnectX-5 (100 Gbps)
  - Supports RDMA (RoCE)
  - Supports SR-IOV (64 VFs)
  
Create VFs:
  echo 64 > /sys/class/net/eth0/device/sriov_numvfs
  
Assign to VMs:
  VM1: VF0 (100 Gbps RDMA)
  VM2: VF1 (100 Gbps RDMA)
  VM3: VF2 (100 Gbps RDMA)
  ...

Each VM gets:
  - Full RDMA capabilities
  - 100 Gbps bandwidth
  - <5 μs latency
  - Zero-copy DMA
  - Direct to hardware
  
Perfect for:
  - NVMe-oF storage servers
  - Distributed databases
  - High-performance computing
  
Near bare-metal performance!
```

---

## Part 8: Tradeoffs and Limitations

### Advantages of SR-IOV

```
✓ Near-native performance (98%+)
✓ Low latency (<5 μs)
✓ Low CPU overhead (2%)
✓ Hardware offloads work (checksums, TSO, RSS)
✓ No hypervisor in data path
✓ Scales to many VMs per NIC
```

---

### Disadvantages of SR-IOV

```
✗ Limited VFs (typically 64 max)
  Can't do 1000 VMs with one NIC

✗ No live migration
  Can't move VM to another host (device tied to hardware)
  Workaround: Bond with virtio, switch on migration

✗ Hardware dependent
  Need SR-IOV capable NIC
  Need IOMMU support
  Guest needs VF driver

✗ Less flexible
  Can't inspect traffic in hypervisor
  Can't apply policies easily
  Can't do QoS in software

✗ Management complexity
  Must configure VFs
  Must handle IOMMU groups
  Must update VF firmware

✗ No VF-to-VF optimization
  Two VMs on same host with VFs
  Traffic must go through physical switch
  (virtio can stay in host memory)
```

---

### When to Use What?

```
┌─────────────────────┬──────────────┬────────────────┐
│ Use Case            │ Recommended  │ Why            │
├─────────────────────┼──────────────┼────────────────┤
│ General VMs         │ virtio-net   │ Good enough,   │
│ (web, app servers)  │              │ more flexible  │
│                     │              │                │
│ High-performance    │ SR-IOV       │ Need <10 μs    │
│ storage (NVMe-oF)   │              │ latency        │
│                     │              │                │
│ RDMA applications   │ SR-IOV       │ Must be direct │
│                     │              │ hardware       │
│                     │              │                │
│ Network functions   │ virtio-net   │ Need traffic   │
│ (firewalls, LBs)    │              │ inspection     │
│                     │              │                │
│ High VM density     │ virtio-net   │ Limited VFs    │
│ (100s per host)     │              │                │
│                     │              │                │
│ Cloud public VMs    │ virtio-net   │ Live migration │
│                     │              │ required       │
│                     │              │                │
│ AI training         │ SR-IOV       │ Need max GPU   │
│ (GPU passthrough)   │              │ performance    │
└─────────────────────┴──────────────┴────────────────┘
```

---

## Part 9: Complete Example

### Setting Up SR-IOV for Storage VM

```bash
# 1. Check IOMMU support
dmesg | grep -i iommu

Output: DMAR: IOMMU enabled

# 2. List network devices
lspci | grep Ethernet

Output:
  01:00.0 Ethernet controller: Intel Corporation X710 (rev 02)
  01:00.1 Ethernet controller: Intel Corporation X710 (rev 02)

# 3. Enable SR-IOV on device
echo 8 > /sys/class/net/eth0/device/sriov_numvfs

# 4. Verify VFs created
lspci | grep Virtual

Output:
  01:02.0 Ethernet controller: Intel Corporation X710 Virtual Function
  01:02.1 Ethernet controller: Intel Corporation X710 Virtual Function
  01:02.2 Ethernet controller: Intel Corporation X710 Virtual Function
  ...

# 5. Unbind VF from host
echo "0000:01:02.0" > /sys/bus/pci/drivers/iavf/unbind

# 6. Bind to VFIO
echo "8086 154c" > /sys/bus/pci/drivers/vfio-pci/new_id
echo "0000:01:02.0" > /sys/bus/pci/drivers/vfio-pci/bind

# 7. Check IOMMU group
ls -l /sys/kernel/iommu_groups/*/devices/* | grep 01:02.0

Output: /sys/kernel/iommu_groups/10/devices/0000:01:02.0

# 8. Start VM with VF
qemu-system-x86_64 \
  -enable-kvm \
  -m 16G \
  -smp 8 \
  -device vfio-pci,host=01:02.0 \
  -drive file=storage.qcow2 \
  ...

# 9. In guest VM:
lspci
Output: 00:04.0 Ethernet controller: Intel Corporation X710 Virtual Function

ip link
Output: eth0: <BROADCAST,MULTICAST,UP> mtu 1500

# 10. Configure for RDMA/RoCE
modprobe rdma_rxe
rdma link add rxe0 type rxe netdev eth0

# 11. Test RDMA
ib_write_bw -d rxe0

Output: 9800 Mbps (near line rate!)

# Success! VM has direct RDMA access via SR-IOV VF
```

---

## Summary: The Complete Picture

```
Device Access Hierarchy:
════════════════════════

Slowest → Fastest:

1. Full Emulation (e1000)
   Guest → VM exit → QEMU emulates registers → NIC
   Speed: 20% of native
   
2. Paravirtualization (virtio-net)
   Guest → virtqueue → VM exit → KVM → vhost → NIC
   Speed: 95% of native
   
3. Passthrough (VFIO)
   Guest → VF → IOMMU → NIC (direct)
   Speed: 98-99% of native

IOMMU provides:
  ✓ Isolation (per-device page tables)
  ✓ Translation (GPA → HPA)
  ✓ Protection (device can't access arbitrary memory)
  
SR-IOV provides:
  ✓ Multiple virtual devices from one physical
  ✓ Hardware partitioning (queues, MACs, interrupts)
  ✓ Each VF isolated via IOMMU
  
Together:
  Near-native performance + Security + Scalability
  
Perfect for:
  - Storage (NVMe-oF, Ceph with RDMA)
  - AI/ML (GPU passthrough)
  - Network intensive workloads
  - Low-latency applications
```

**SR-IOV + IOMMU = How cloud providers achieve bare-metal performance for specialized workloads!**

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for device passthrough, SR-IOV, and IOMMU:**

- **[VFIO Kernel Documentation](https://www.kernel.org/doc/Documentation/vfio.txt)** - Complete guide to VFIO (Virtual Function I/O) for device assignment
- **[SR-IOV Specification (PCI-SIG)](https://pcisig.com/specifications/iov/single_root/)** - Official PCI-SIG specification for Single Root I/O Virtualization

---

## Next Steps

Continue exploring advanced virtualization topics or return to the main learning path.
