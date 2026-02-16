---
level: specialized
estimated_time: 40 min
prerequisites:
  - 02_intermediate/03_complete_virtualization/01_evolution_complete.md
next_recommended:
  - 05_specialized/03_serverless/02_firecracker_deep_dive.md
tags: [virtualization, firecracker, kvm, microvms, serverless]
---

# Firecracker and KVM: The Relationship Explained

## The Direct Answer

**YES - Firecracker REQUIRES KVM and /dev/kvm**

Firecracker is built on top of KVM. It cannot function without KVM.

---

## What Firecracker Actually Is

**Firecracker = KVM + Minimal Device Emulation (replacing QEMU)**

```
Traditional KVM/QEMU Stack:
┌─────────────────────────────────────┐
│         Guest OS (VM)               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Linux Kernel                 │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  KVM Module (kvm.ko)         │  │
│  │  - CPU virtualization        │  │
│  │  - Memory virtualization     │  │
│  │  - /dev/kvm interface        │  │
│  └──────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │ ioctl()
┌──────────────▼──────────────────────┐
│        QEMU (User Space)            │
│  - Device emulation                 │
│  - BIOS                             │
│  - 1000s of devices                 │
│  - ~200,000 lines of C              │
│  - Large memory footprint           │
└─────────────────────────────────────┘


Firecracker Stack:
┌─────────────────────────────────────┐
│         Guest OS (microVM)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Linux Kernel                 │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  KVM Module (kvm.ko)         │  │ ← SAME KVM!
│  │  - CPU virtualization        │  │
│  │  - Memory virtualization     │  │
│  │  - /dev/kvm interface        │  │
│  └──────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │ ioctl()
┌──────────────▼──────────────────────┐
│    Firecracker (User Space, Rust)  │
│  - Minimal device emulation         │
│  - ONLY virtio devices:             │
│    * virtio-net                     │
│    * virtio-block                   │
│    * virtio-vsock                   │
│  - No BIOS (direct kernel boot)     │
│  - ~50,000 lines of Rust            │
│  - 5 MB memory footprint            │
└─────────────────────────────────────┘
```

---

## What Firecracker Uses from KVM

**Everything for CPU and Memory:**

```rust
// Firecracker Rust code uses /dev/kvm exactly like QEMU does

// 1. Open KVM
let kvm = Kvm::new().unwrap();  // Opens /dev/kvm

// 2. Create VM
let vm = kvm.create_vm().unwrap();  // ioctl(KVM_CREATE_VM)

// 3. Create vCPU
let vcpu = vm.create_vcpu(0).unwrap();  // ioctl(KVM_CREATE_VCPU)

// 4. Setup memory
vm.set_user_memory_region(
    kvm_userspace_memory_region {
        slot: 0,
        guest_phys_addr: 0,
        memory_size: 128 * 1024 * 1024,  // 128 MB
        userspace_addr: mem_addr,
    }
).unwrap();  // ioctl(KVM_SET_USER_MEMORY_REGION)

// 5. Run vCPU
loop {
    match vcpu.run().unwrap() {  // ioctl(KVM_RUN)
        VcpuExit::IoOut(port, data) => {
            // Handle device I/O
            handle_io_out(port, data);
        }
        VcpuExit::MmioWrite(addr, data) => {
            // Handle MMIO
            handle_mmio_write(addr, data);
        }
        VcpuExit::Hlt => {
            // VM halted
            break;
        }
        _ => {}
    }
}
```

**This is IDENTICAL to what QEMU does!**

Same ioctls, same /dev/kvm, same KVM kernel module.

---

## What Firecracker REPLACES

**Firecracker replaces QEMU** - specifically the device emulation part.

### QEMU Device Emulation (What Firecracker Removes)

```
QEMU emulates 1000+ devices:
  - Legacy BIOS (SeaBIOS)
  - VGA graphics
  - PS/2 keyboard/mouse
  - Serial ports (16550 UART)
  - Parallel ports
  - Floppy drives
  - IDE/SATA controllers
  - Many network cards (e1000, rtl8139, ne2k, ...)
  - Many sound cards
  - USB controllers (UHCI, EHCI, xHCI)
  - PCI chipset emulation
  - ACPI tables
  - And hundreds more...

Why? For compatibility with any OS/software

Size: ~200,000 lines of C code
Memory: 100-200 MB per VM
Startup: 1-2 seconds
```

### Firecracker Device Emulation (Minimal)

```
Firecracker emulates 3 device types:
  - virtio-net (network)
  - virtio-block (disk)
  - virtio-vsock (host-guest communication)

That's it. Nothing else.

Why? Only what's needed for serverless workloads

Size: ~50,000 lines of Rust code
Memory: 5 MB per microVM
Startup: <125 milliseconds
```

---

## The Firecracker Architecture in Detail

```
┌──────────────────────────────────────────────────────┐
│                  microVM (Guest)                     │
│                                                      │
│  Linux Kernel (minimal, no drivers for legacy hw)   │
│                                                      │
│  virtio drivers:                                     │
│    - virtio-net   (network)                         │
│    - virtio-blk   (disk)                            │
│    - virtio-vsock (communication)                   │
└────────────────────┬─────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │  virtqueues │ (shared memory rings)
              └──────┬──────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│              Linux Host Kernel                       │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  KVM (kvm.ko, kvm-intel.ko / kvm-amd.ko)      │ │
│  │                                                │ │
│  │  Provides:                                     │ │
│  │  - /dev/kvm                                    │ │
│  │  - VMX/SVM (hardware virt)                    │ │
│  │  - EPT/NPT (nested paging)                    │ │
│  │  - vCPU scheduling                            │ │
│  │  - Memory management                          │ │
│  └────────────────────────────────────────────────┘ │
└────────────────────┬─────────────────────────────────┘
                     │ ioctl(/dev/kvm)
┌────────────────────▼─────────────────────────────────┐
│         Firecracker Process (Rust)                   │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  VMM (Virtual Machine Monitor)                 │ │
│  │                                                │ │
│  │  - Opens /dev/kvm                              │ │
│  │  - Creates VM via KVM_CREATE_VM               │ │
│  │  - Sets up memory via KVM_SET_USER_MEMORY_... │ │
│  │  - Creates vCPUs via KVM_CREATE_VCPU          │ │
│  │  - Runs vCPU loop: ioctl(KVM_RUN)             │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  Device Emulation (Minimal!)                   │ │
│  │                                                │ │
│  │  virtio-net backend:                          │ │
│  │    - Poll virtqueue                           │ │
│  │    - Read packet descriptors                  │ │
│  │    - Write to TAP device                      │ │
│  │    - Inject interrupts                        │ │
│  │                                                │ │
│  │  virtio-block backend:                        │ │
│  │    - Poll virtqueue                           │ │
│  │    - Read block I/O requests                  │ │
│  │    - Read/write to backing file               │ │
│  │    - Mark complete                            │ │
│  │                                                │ │
│  │  virtio-vsock backend:                        │ │
│  │    - Host-guest communication                 │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  API Server                                    │ │
│  │    - REST API to control VM                   │ │
│  │    - PUT /boot-source (kernel image)          │ │
│  │    - PUT /drives (disk config)                │ │
│  │    - PUT /network-interfaces                  │ │
│  │    - PUT /actions (start/stop)                │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## Key Point: KVM is REQUIRED

```
Firecracker cannot run without KVM because:

1. CPU Virtualization:
   - Needs VMX/SVM instructions (VT-x/AMD-V)
   - Needs VMCS management
   - Needs VM entry/exit handling
   → All provided by KVM

2. Memory Virtualization:
   - Needs EPT/NPT setup
   - Needs guest physical → host physical mapping
   - Needs memory protection
   → All provided by KVM

3. Scheduling:
   - vCPU threads need to run
   - Need preemption, fairness
   - Need integration with Linux scheduler
   → All provided by KVM

Firecracker ONLY replaces QEMU's device emulation
Firecracker USES KVM for everything else
```

---

## Why Firecracker Was Created

### The Problem with QEMU

**AWS Lambda needs:**
- Boot 100s of VMs per second
- Minimal memory overhead (run 1000s per host)
- Fast startup (<100ms)
- Strong isolation

**QEMU problems:**
- Too large (200MB RAM per VM)
- Too slow (1-2 second startup)
- Too many features (attack surface)
- Too complex (hard to audit for security)

### Firecracker Solution

```
Remove everything not needed for serverless:
  ✗ BIOS → Direct kernel boot (PVH)
  ✗ VGA → No graphics needed
  ✗ Legacy devices → Only virtio
  ✗ Multiple device types → Just 3 virtio devices
  ✗ C codebase → Rewrite in safe Rust
  
Result:
  ✓ 5 MB RAM per microVM (vs 200 MB QEMU)
  ✓ <125ms startup (vs 1-2 sec QEMU)
  ✓ 50,000 lines Rust (vs 200,000 lines C)
  ✓ Easier security audit
  ✓ Memory safe (Rust benefits)
```

---

## Firecracker Boot Process

**Traditional KVM/QEMU Boot:**

```
1. QEMU starts
2. Sets up virtual BIOS
3. BIOS initializes (1 second)
4. BIOS loads bootloader from disk
5. Bootloader loads kernel
6. Kernel boots
7. Init system starts
8. Application ready

Total: 1-3 seconds
```

**Firecracker Boot:**

```
1. Firecracker starts
2. Loads kernel directly into memory (no BIOS!)
3. Sets guest RIP to kernel entry point
4. Kernel boots (minimal kernel, fast)
5. Application ready

Total: <125 milliseconds
```

**How direct kernel boot works:**

```rust
// Firecracker loads kernel
let kernel = fs::read("/path/to/vmlinux").unwrap();

// Write kernel to guest memory at 1MB
vm.write_memory(0x100000, &kernel).unwrap();

// Set vCPU registers for kernel entry
vcpu.set_regs(kvm_regs {
    rip: 0x100000,  // Kernel entry point
    rsi: boot_params_addr,  // Boot parameters
    ...
});

// Start VM - jumps directly to kernel!
vcpu.run().unwrap();

// No BIOS, no bootloader!
```

---

## Firecracker vs QEMU Comparison

```
┌────────────────────────┬─────────────────┬──────────────────┐
│ Aspect                 │ QEMU + KVM      │ Firecracker + KVM│
├────────────────────────┼─────────────────┼──────────────────┤
│ Uses /dev/kvm?         │ YES             │ YES              │
│ Uses KVM kernel module?│ YES             │ YES              │
│ CPU virtualization     │ KVM             │ KVM              │
│ Memory virtualization  │ KVM             │ KVM              │
│ EPT/NPT                │ KVM             │ KVM              │
│                        │                 │                  │
│ Device emulation       │ QEMU (C)        │ Firecracker(Rust)│
│ Emulated devices       │ 1000+           │ 3 (virtio only)  │
│ BIOS                   │ Yes (SeaBIOS)   │ No (direct boot) │
│ VGA                    │ Yes             │ No               │
│ Legacy devices         │ Yes             │ No               │
│                        │                 │                  │
│ Memory per VM          │ 100-200 MB      │ 5 MB             │
│ Startup time           │ 1-2 seconds     │ <125 ms          │
│ Code size              │ ~200K lines C   │ ~50K lines Rust  │
│ Memory safety          │ No (C)          │ Yes (Rust)       │
│                        │                 │                  │
│ Best for               │ General VMs     │ Serverless       │
│                        │ Desktop VMs     │ Containers++     │
│                        │ Any OS          │ AWS Lambda       │
│                        │                 │ AWS Fargate      │
└────────────────────────┴─────────────────┴──────────────────┘
```

---

## The Layering

**Both use the SAME KVM layer:**

```
┌────────────────────────────────────────┐
│         Hardware (CPU with VT-x)       │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│      Linux Kernel with KVM Module      │
│      (Handles CPU/Memory Virt)         │
└────────────────┬───────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼────┐      ┌───▼──────┐
    │  QEMU   │      │Firecracker│
    │         │      │           │
    │ Many    │      │ Minimal   │
    │ devices │      │ devices   │
    └─────────┘      └───────────┘
```

---

## Real-World Usage

**AWS Lambda:**
```
Each Lambda invocation:
  - Runs in a Firecracker microVM
  - Uses KVM for isolation
  - Boots in <125ms
  - 5MB overhead
  - Strong isolation between tenants
```

**AWS Fargate:**
```
Each container task:
  - Runs in Firecracker microVM
  - Uses KVM for isolation
  - Better isolation than regular containers
  - Nearly same performance
```

---

## Requirements

**To run Firecracker, you MUST have:**

```bash
# 1. Hardware virtualization support
grep -E 'vmx|svm' /proc/cpuinfo
# Must show vmx (Intel) or svm (AMD)

# 2. KVM kernel modules loaded
lsmod | grep kvm
# Must show:
#   kvm_intel (Intel) or kvm_amd (AMD)
#   kvm

# 3. /dev/kvm device
ls -l /dev/kvm
# Must exist: crw-rw---- 1 root kvm /dev/kvm

# 4. Permissions to access /dev/kvm
# Either:
#   - Run as root, OR
#   - Be in 'kvm' group
```

**Without these, Firecracker CANNOT work.**

---

## Summary

**Question: Does Firecracker rely on KVM?**

**Answer: ABSOLUTELY YES**

Firecracker:
- **Requires** /dev/kvm
- **Requires** KVM kernel module
- **Uses** KVM for 100% of CPU virtualization
- **Uses** KVM for 100% of memory virtualization
- **Uses** KVM's ioctl interface
- **Only replaces** QEMU's device emulation
- **Implements** minimal virtio device emulation in Rust

**Firecracker = Minimal QEMU replacement built on top of KVM**

The innovation isn't removing KVM - it's removing QEMU bloat while keeping KVM's solid CPU/memory virtualization.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for Firecracker and its relationship to KVM:**

- **[Firecracker GitHub Repository](https://github.com/firecracker-microvm/firecracker)** - Official Firecracker source code with examples and documentation
- **[Firecracker Design Document](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md)** - Detailed technical design explaining how Firecracker uses KVM
