# Virtualization Technologies: From Paravirtualization to Modern Hypervisors

## Part 1: The Fundamental Problem

### What is Virtualization Trying to Achieve?

**Goal:** Run multiple operating systems on a single physical machine, each thinking it has exclusive access to hardware.

**The Challenge:**

```
Physical Machine:
┌────────────────────────────────────────┐
│         Operating System               │
│  - Controls CPU (privileged ops)      │
│  - Controls Memory (page tables)      │
│  - Controls Devices (I/O ports)       │
└────────────────────────────────────────┘
         │ Direct hardware access
┌────────▼────────────────────────────────┐
│         Hardware                        │
│  - CPU (ring 0 for kernel)             │
│  - Memory                               │
│  - Devices (disk, network)             │
└─────────────────────────────────────────┘

Problem: How do you run TWO operating systems,
both wanting ring 0 access, on ONE CPU?
```

---

## Part 2: CPU Privilege Levels - The Core Issue

### x86 Privilege Rings

```
┌──────────────────────────────────────┐
│  Ring 0 (Kernel Mode)                │  ← Privileged instructions
│  - Modify page tables                │  ← I/O instructions
│  - Halt CPU                           │  ← Interrupt handling
│  - Access all memory                  │
└──────────────────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  Ring 3 (User Mode)                  │  ← Can't execute privileged
│  - Normal applications               │     instructions
│  - Limited memory access             │  ← Causes fault if tried
└──────────────────────────────────────┘
```

**The Problem for Virtualization:**

```
Guest OS expects to run in Ring 0:
  mov cr3, eax        ; Set page table base (privileged!)
  
But if Guest OS is in Ring 0:
  - Can modify hypervisor's memory
  - Can access other VMs
  - Can crash entire system
  
If Guest OS is in Ring 3:
  - Privileged instructions FAULT
  - Can't function as OS
  
Dilemma: Need isolation but OS needs privileges!
```

---

## Part 3: Early Solution - Software-Based Full Virtualization

### Binary Translation (VMware's Approach)

**Idea:** Dynamically rewrite guest code to replace privileged instructions.

```
Guest OS Code (original):
  mov eax, cr3        ; Read page table register (privileged)
  cli                 ; Disable interrupts (privileged)
  mov [0x1000], ebx   ; Write to memory
  
     ↓ Binary translator scans and rewrites
     
Translated Code:
  call vmware_read_cr3     ; Call hypervisor function
  call vmware_cli          ; Call hypervisor function
  mov [shadow_mem], ebx    ; Write to safe shadow memory
```

**How it works:**

```
┌─────────────────────────────────────────┐
│         VMware Hypervisor               │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Binary Translator                │ │
│  │  - Scan guest code                │ │
│  │  - Detect privileged instructions │ │
│  │  - Replace with safe calls        │ │
│  │  - Cache translated code          │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘

Pros:
  ✓ Guest OS runs unmodified
  ✓ Works on any x86 CPU
  
Cons:
  ✗ Complex (scan entire code)
  ✗ Performance overhead (10-30%)
  ✗ Translation cache bloat
```

---

## Part 4: Paravirtualization - The Elegant Solution

### The Xen Approach (2003)

**Idea:** If we can't make the hardware pretend to be real hardware efficiently, change the guest OS to *know* it's virtualized.

**Paravirtualization = "Para" (beside) + Virtualization**

Guest OS is modified to use **hypercalls** instead of privileged instructions.

---

### Hypercalls - The Paravirt API

```
Traditional OS:
  mov cr3, eax              ; Direct hardware manipulation
  
Paravirtualized OS:
  mov eax, new_page_table
  call xen_update_cr3       ; Hypercall to hypervisor
  
  ; Xen does the actual CR3 update safely
```

**Hypercall is like a system call, but to the hypervisor:**

```
User Application:
  syscall()  ──→  Kernel
  
Guest OS Kernel:
  hypercall() ──→  Hypervisor
```

---

### Xen Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Physical Hardware                    │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                 Xen Hypervisor (Ring 0)                 │
│                                                         │
│  Responsibilities:                                      │
│  - CPU scheduling                                       │
│  - Memory management (real page tables)                │
│  - Interrupt routing                                    │
│  - Minimal device drivers (just enough to boot)        │
│                                                         │
│  Size: ~150KB (tiny!)                                  │
└─────────────┬──────────────────┬────────────────────────┘
              │                  │
    ┌─────────▼──────┐    ┌─────▼──────────┐
    │   Domain 0     │    │   Guest VMs    │
    │  (Dom0)        │    │  (DomU)        │
    │                │    │                │
    │  Privileged    │    │  Unprivileged  │
    │  Linux         │    │  Linux/Windows │
    │                │    │                │
    │  Runs:         │    │  Run in:       │
    │  - Device      │    │  Ring 1        │
    │    drivers     │    │  (not Ring 0!) │
    │  - QEMU        │    │                │
    │  - Management  │    │  Use:          │
    │                │    │  - Hypercalls  │
    │  Ring 0 access │    │  - Para drivers│
    │  (trusted)     │    │                │
    └────────────────┘    └────────────────┘
```

---

### Key Xen Innovations

**1. Ring Deprivileging:**

```
x86 has 4 rings:
  Ring 0: Most privileged
  Ring 1: (historically unused)
  Ring 2: (historically unused)
  Ring 3: User mode

Xen's usage:
  Ring 0: Xen hypervisor only
  Ring 1: Guest OS kernels  ← Novel use!
  Ring 3: Guest user processes
```

**Guest OS runs in Ring 1:**
- Can execute *some* privileged instructions
- Critical ones (CR3, I/O) fault → hypervisor
- Less overhead than Ring 3

---

**2. Split Driver Model:**

```
Traditional:
  Guest OS → Device Driver → Hardware

Xen:
  Guest OS → Frontend Driver ─┐
                              │
                              ├─→ Shared Memory Ring
                              │
  Dom0 → Backend Driver ──────┘
           │
           └──→ Real Hardware
```

**Example: Network Packet TX**

```
Guest VM (DomU):
  1. Application does write() to socket
  2. TCP/IP stack processes
  3. netfront driver (paravirt frontend):
     - Allocates buffer in shared memory
     - Writes packet data
     - Writes descriptor to ring buffer
     - Kicks event channel (notify Dom0)
     
  ┌───────────────────────┐
  │  Shared Memory Ring   │
  │  ┌─────────────────┐  │
  │  │ Descriptor 0    │  │
  │  │ buf=0x1000      │  │
  │  │ len=1500        │  │
  │  ├─────────────────┤  │
  │  │ Descriptor 1    │  │
  │  │ ...             │  │
  │  └─────────────────┘  │
  └───────────────────────┘
  
Dom0:
  4. Event channel notification
  5. netback driver wakes up
  6. Reads descriptor from ring
  7. Maps guest memory (grant tables)
  8. Copies packet to Dom0 buffer
  9. Sends via real NIC driver
```

**Advantages:**
- Device drivers in Dom0 (not hypervisor)
- Hypervisor stays tiny and simple
- Easy to update drivers (just reboot Dom0)

**Disadvantages:**
- Memory copy (guest → Dom0 → hardware)
- Context switches (guest → Dom0)
- ~5-10% overhead

---

**3. Grant Tables (Safe Memory Sharing):**

```
Problem:
  Guest wants to share memory with Dom0
  But can't just give physical addresses (don't know them!)
  
Solution: Grant Tables

Guest (DomU):
  1. Allocate buffer at guest-physical 0x1000
  2. Create grant reference:
       gnttab_grant_access(dom0, gfn=0x1, writable)
     Returns: grant_ref = 42
  3. Pass grant_ref to Dom0 via ring

Dom0:
  4. Receives grant_ref = 42
  5. Maps grant:
       gnttab_map_grant_ref(domU_id, ref=42)
     Returns: pointer to buffer
  6. Can now read/write guest's memory safely

Hypervisor:
  - Validates all grants
  - Enforces permissions
  - Ensures isolation
```

---

### Modified Guest OS Requirements

**Kernel changes needed:**

```c
// Original Linux code:
void update_page_table(pte_t *new_pt) {
    asm("mov %0, %%cr3" : : "r" (new_pt));  // Direct hardware access
}

// Paravirtualized Linux code:
void update_page_table(pte_t *new_pt) {
    struct mmuext_op op;
    op.cmd = MMUEXT_NEW_BASEPTR;
    op.arg1.mfn = virt_to_mfn(new_pt);
    
    HYPERVISOR_mmuext_op(&op, 1, NULL, DOMID_SELF);  // Hypercall
}
```

**Other modifications:**
- Page table management (all updates via hypercalls)
- Interrupt handling (virtual interrupts from Xen)
- Time (paravirt clock source)
- Boot process (launched by Xen, not BIOS)

**Result:** ~3000 lines of code changes in Linux kernel

---

### Xen Performance (vs Full Virtualization)

```
Benchmark: Linux compilation

Bare metal:           100 seconds
Xen paravirt:         102 seconds  (2% overhead)
VMware full virt:     130 seconds  (30% overhead)

Why paravirt wins:
  - No binary translation
  - Direct hypercalls (fast trap)
  - Efficient I/O (shared memory)
```

---

## Part 5: Hardware-Assisted Virtualization

### The x86 Virtualization Extensions

**Intel VT-x (2005) and AMD-V (2006):**

New CPU feature: **VMX (Virtual Machine Extensions)**

```
Before (4 rings):
  Ring 0: Kernel
  Ring 1: (unused)
  Ring 2: (unused)
  Ring 3: User

After (VMX adds new modes):
  VMX Root Mode:
    Ring 0: Hypervisor  ← Host runs here
    Ring 3: Host user
    
  VMX Non-Root Mode:
    Ring 0: Guest OS    ← Guest OS runs in REAL Ring 0!
    Ring 3: Guest user
```

**Key idea:** Two complete privilege hierarchies!

---

### How Hardware Virtualization Works

```
┌─────────────────────────────────────────────────┐
│          VMX Root Mode (Host)                   │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │       Hypervisor (KVM)                    │ │
│  │  - Handles VM exits                       │ │
│  │  - Manages EPT (page tables)              │ │
│  │  - Schedules VMs                          │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                      │
                      │ VMLAUNCH / VMRESUME
                      ↓
┌─────────────────────────────────────────────────┐
│        VMX Non-Root Mode (Guest)                │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │    Guest OS (Ring 0)                      │ │
│  │  - Runs native code                       │ │
│  │  - No translation needed                  │ │
│  │  - Direct CPU execution                   │ │
│  │                                            │ │
│  │  mov cr3, eax  ← Actually works!          │ │
│  │  cli           ← Actually works!          │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │    Guest Applications (Ring 3)            │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                      │
                      │ Sensitive operation
                      │ (VM Exit)
                      ↓
              Back to VMX Root
```

---

### VMCS (Virtual Machine Control Structure)

**Per-VM data structure in memory:**

```
VMCS for VM1:
┌────────────────────────────────────────┐
│  Guest State:                          │
│    - CPU registers (RAX, RBX, ...)    │
│    - CR0, CR3, CR4                     │
│    - GDTR, IDTR                        │
│    - Segment registers                 │
│                                        │
│  Host State:                           │
│    - Where to return on VM exit       │
│    - Host CR3, RSP, RIP                │
│                                        │
│  Execution Controls:                   │
│    - Which instructions cause VM exit  │
│    - Exception bitmap                  │
│    - I/O bitmap                        │
│    - MSR bitmap                        │
│                                        │
│  Exit Information:                     │
│    - Why did VM exit?                  │
│    - Exit qualification                │
│    - Guest linear/physical address     │
└────────────────────────────────────────┘
```

---

### VM Entry and Exit

**VM Entry (VMLAUNCH/VMRESUME):**

```
Hypervisor:
  1. Prepare VMCS
  2. Set guest state (RIP, RSP, CR3, ...)
  3. Execute: VMLAUNCH
  
CPU:
  4. Save host state to VMCS
  5. Load guest state from VMCS
  6. Switch to VMX non-root mode
  7. Jump to guest RIP
  
Guest starts executing!
```

**VM Exit (Automatic):**

```
Guest executes sensitive operation:
  mov cr3, eax    ; Try to change page table
  
CPU:
  1. Detect this should cause VM exit (configured in VMCS)
  2. Save guest state to VMCS
  3. Load host state from VMCS
  4. Switch to VMX root mode
  5. Jump to host exit handler
  6. Record exit reason in VMCS
  
Hypervisor:
  7. Read VMCS exit reason
  8. Emulate the operation
  9. Update guest state in VMCS
  10. VMRESUME to continue guest
```

**Exit reasons:**
- CR3 access (page table change)
- I/O port access
- CPUID instruction
- Exception (page fault, etc.)
- Interrupt window
- EPT violation (memory access)

---

### EPT (Extended Page Tables) / NPT (Nested Page Tables)

**The Two-Level Translation:**

```
Without EPT:
  Guest Virtual Address
       ↓ Guest page tables (CR3)
  Guest Physical Address
       ↓ Shadow page tables (hypervisor maintains)
  Host Physical Address

Hypervisor must:
  - Intercept all guest page table updates
  - Maintain shadow page tables
  - Complex, slow

With EPT:
  Guest Virtual Address
       ↓ Guest page tables (managed by guest)
  Guest Physical Address
       ↓ EPT tables (managed by hypervisor) ← Hardware!
  Host Physical Address

Hardware does both translations!
Hypervisor just sets up EPT
Guest can freely modify its own page tables
```

**EPT Structure:**

```
┌──────────────────────────────────────┐
│  Guest Page Tables (Guest OS owns)  │
│  GVA → GPA                           │
└──────────────────┬───────────────────┘
                   │
                   ↓ GPA
┌──────────────────────────────────────┐
│  EPT Tables (Hypervisor owns)        │
│  GPA → HPA                           │
│                                      │
│  Similar structure to normal PTs:   │
│  - EPT PML4                          │
│  - EPT PDPT                          │
│  - EPT PD                            │
│  - EPT PT                            │
│                                      │
│  Hardware walks both!               │
└──────────────────┬───────────────────┘
                   │
                   ↓ HPA
┌──────────────────────────────────────┐
│         Physical Memory              │
└──────────────────────────────────────┘
```

**Performance impact:**
- Without EPT: 20-30% overhead (shadow paging)
- With EPT: 2-5% overhead

---

## Part 6: KVM (Kernel-based Virtual Machine)

### KVM Architecture

**Key insight:** Linux kernel IS a hypervisor - just add VM scheduling!

```
┌─────────────────────────────────────────────┐
│            Linux Kernel                     │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  KVM Module (kvm.ko)                  │ │
│  │                                        │ │
│  │  - /dev/kvm device                    │ │
│  │  - VM creation/management             │ │
│  │  - vCPU thread scheduling             │ │
│  │  - Memory management                  │ │
│  │                                        │ │
│  │  Functions:                           │ │
│  │  - KVM_CREATE_VM                      │ │
│  │  - KVM_CREATE_VCPU                    │ │
│  │  - KVM_RUN                            │ │
│  │  - KVM_GET/SET_REGS                   │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  Arch-specific (kvm-intel.ko)         │ │
│  │  - VMX/SVM support                    │ │
│  │  - VMCS management                    │ │
│  │  - EPT/NPT management                 │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                    ↕ ioctl()
┌─────────────────────────────────────────────┐
│         User Space                          │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │         QEMU Process                   │ │
│  │                                        │ │
│  │  - Device emulation                   │ │
│  │  - BIOS                                │ │
│  │  - VGA                                 │ │
│  │  - Disk, Network (if not virtio)     │ │
│  │  - PCI bus                             │ │
│  │                                        │ │
│  │  Main loop:                           │ │
│  │    while (1) {                        │ │
│  │      ioctl(vcpu_fd, KVM_RUN);        │ │
│  │      handle_exit();                   │ │
│  │    }                                   │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

### How KVM Works

**1. VM Creation:**

```c
// User space (QEMU):
int kvm_fd = open("/dev/kvm", O_RDWR);
int vm_fd = ioctl(kvm_fd, KVM_CREATE_VM, 0);

// Kernel (KVM):
struct kvm *kvm = kzalloc(sizeof(*kvm));
kvm->mm = current->mm;
// Allocate EPT/NPT root
// Initialize IOMMU
return fd;
```

**2. vCPU Creation:**

```c
// User space:
int vcpu_fd = ioctl(vm_fd, KVM_CREATE_VCPU, 0);

// Kernel:
struct kvm_vcpu *vcpu = kmem_cache_zalloc(kvm_vcpu_cache);
vcpu->kvm = kvm;
vcpu->vcpu_id = 0;

// Allocate VMCS
vcpu->arch.vmcs = alloc_vmcs();
vmcs_load(vcpu->arch.vmcs);

// Initialize guest state
setup_vmcs_config();

return vcpu_fd;
```

**3. Memory Setup:**

```c
// User space allocates memory:
void *mem = mmap(NULL, 1GB, PROT_READ|PROT_WRITE, 
                 MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);

// Tell KVM about it:
struct kvm_userspace_memory_region region = {
    .slot = 0,
    .guest_phys_addr = 0,       // GPA
    .memory_size = 1GB,
    .userspace_addr = (u64)mem  // HVA (host virtual)
};
ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION, &region);

// Kernel sets up EPT:
// GPA 0 → HVA mem → HPA (via kernel page tables)
```

**4. vCPU Execution:**

```c
// User space main loop:
while (1) {
    ret = ioctl(vcpu_fd, KVM_RUN, 0);
    
    // VM exited, handle reason
    struct kvm_run *run = vcpu->run;  // Shared memory
    
    switch (run->exit_reason) {
    case KVM_EXIT_IO:
        handle_io(run->io.port, run->io.data);
        break;
    case KVM_EXIT_MMIO:
        handle_mmio(run->mmio.phys_addr, run->mmio.data);
        break;
    case KVM_EXIT_HLT:
        vcpu_idle();
        break;
    }
}

// Kernel (KVM_RUN ioctl):
static long kvm_vcpu_ioctl(struct file *filp, unsigned int ioctl, ...) {
    case KVM_RUN:
        return kvm_arch_vcpu_ioctl_run(vcpu);
}

static int kvm_arch_vcpu_ioctl_run(struct kvm_vcpu *vcpu) {
    // Load guest state into VMCS
    vmx_vcpu_load(vcpu);
    
    // Enter guest (VMLAUNCH/VMRESUME)
    vmx_vcpu_run(vcpu);
    
    // VM exited
    // Save exit info to shared kvm_run structure
    vcpu->run->exit_reason = vmcs_read32(VM_EXIT_REASON);
    
    return 0;
}
```

---

### KVM vs Xen Comparison

```
┌────────────────────────┬──────────────────┬─────────────────┐
│ Aspect                 │ Xen              │ KVM             │
├────────────────────────┼──────────────────┼─────────────────┤
│ Architecture           │ Microkernel      │ Integrated      │
│                        │ (tiny hypervisor)│ (Linux module)  │
│                        │                  │                 │
│ Device Drivers         │ Dom0 (separate)  │ Linux kernel    │
│                        │                  │                 │
│ Scheduling             │ Custom scheduler │ Linux CFS       │
│                        │                  │                 │
│ Memory Management      │ Custom           │ Linux MM        │
│                        │                  │                 │
│ Code Size              │ 150KB hypervisor │ ~50KB KVM       │
│                        │ + Dom0 kernel    │ + full kernel   │
│                        │                  │                 │
│ Hardware Requirements  │ Can paravirt     │ Requires VT-x/  │
│                        │ (no VT-x needed) │ AMD-V           │
│                        │                  │                 │
│ Guest Modifications    │ Paravirt: Yes    │ No (HVM)        │
│                        │ HVM: No          │                 │
│                        │                  │                 │
│ Overhead               │ 2% (paravirt)    │ 2-5% (hardware) │
│                        │ 5-10% (HVM)      │                 │
│                        │                  │                 │
│ Maturity               │ Very mature      │ Very mature     │
│                        │ (2003)           │ (2007)          │
│                        │                  │                 │
│ Use Cases              │ Cloud (AWS,      │ OpenStack, KVM, │
│                        │  Rackspace)      │ most Linux VMs  │
└────────────────────────┴──────────────────┴─────────────────┘
```

---

## Part 7: Device Virtualization - The Hard Part

### Why Device Virtualization is Hard

**CPU virtualization:** VMX handles it (mostly)  
**Memory virtualization:** EPT handles it (mostly)  
**Device virtualization:** No hardware help! Must emulate in software.

---

### The Problem

```
Guest OS wants to use disk:
  1. Guest writes to I/O port 0x1F0 (IDE controller)
  2. This causes VM exit
  3. Hypervisor must:
     - Decode what operation
     - Emulate device behavior
     - Update device state
     - Trigger interrupts
     - Resume guest
  
For EVERY I/O operation!
Thousands of exits per second
```

---

### QEMU - The Device Emulator

**QEMU = Quick Emulator**

Originally a full system emulator (CPU + devices), now used with KVM just for devices.

```
┌─────────────────────────────────────────────┐
│              QEMU Process                   │
│                                             │
│  ┌────────────────────────────────────────┐│
│  │        CPU Emulation (TCG)             ││ ← Not used with KVM
│  │        (Dynamic binary translation)    ││
│  └────────────────────────────────────────┘│
│                                             │
│  ┌────────────────────────────────────────┐│
│  │        Device Emulation                ││ ← This is used!
│  │                                        ││
│  │  - PCI bus                             ││
│  │  - IDE/SATA/SCSI controllers          ││
│  │  - E1000 network card                  ││
│  │  - VGA adapter                         ││
│  │  - USB controllers                     ││
│  │  - PS/2 keyboard/mouse                 ││
│  │  - RTC, PIT timers                     ││
│  │  - BIOS (SeaBIOS)                      ││
│  │                                        ││
│  │  Each device:                          ││
│  │  - State machine                       ││
│  │  - Register I/O handlers               ││
│  │  - Emulate hardware behavior           ││
│  └────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

### Example: Emulated E1000 Network Card

**When guest accesses E1000:**

```
Guest driver:
  outl(E1000_CTRL, 0x1000);  // Write to control register
  
↓ VM Exit (I/O port access)

KVM kernel:
  exit_reason = KVM_EXIT_IO
  io_port = E1000_CTRL
  data = 0x1000
  
  Return to QEMU

QEMU e1000_io_write():
  switch (port) {
    case E1000_CTRL:
      e1000->ctrl_reg = data;
      
      if (data & E1000_CTRL_RST) {
        // Reset requested
        e1000_reset();
      }
      
      if (data & E1000_CTRL_SLU) {
        // Link up
        e1000->link_status = UP;
        // Inject interrupt into guest
        pci_set_irq(&e1000->pci_dev, 1);
      }
      break;
  }
  
Resume guest via KVM_RUN
```

**For packet transmission:**

```
Guest:
  1. Allocate TX descriptor in memory
  2. Fill in packet buffer address
  3. Write to E1000_TDT (tail pointer) register
  
↓ VM Exit

QEMU:
  4. Read TX descriptor from guest memory
  5. Read packet data from guest memory
  6. Copy to host buffer
  7. Write to TAP device (host network)
  8. Update descriptor (mark complete)
  9. Inject TX complete interrupt
  
↓ Resume guest

Guest:
  10. Interrupt handler runs
  11. Frees buffer
```

**Problem:** Every packet = 2 VM exits + memory copies!

---

## Part 8: Paravirtualized Devices - virtio

### The virtio Revolution

**Idea:** Instead of emulating real hardware (e.g., E1000), create a virtualization-optimized device interface.

**Design goals:**
- Minimize VM exits
- Batch operations
- Shared memory for data
- Standard cross-hypervisor

---

### virtio Architecture

```
┌─────────────────────────────────────────────┐
│            Guest OS                         │
│                                             │
│  ┌────────────────────────────────────────┐│
│  │   virtio Front-end Driver              ││
│  │   (virtio-net, virtio-blk, etc.)       ││
│  │                                        ││
│  │   - Minimal code                       ││
│  │   - Just queue operations              ││
│  │   - No hardware emulation              ││
│  └──────────────┬─────────────────────────┘│
└─────────────────┼──────────────────────────┘
                  │
         ┌────────▼─────────┐
         │  Virtqueue       │  ← Shared memory ring
         │  (vring)         │
         └────────┬─────────┘
                  │
┌─────────────────▼──────────────────────────┐
│           Host (QEMU/KVM)                  │
│                                            │
│  ┌────────────────────────────────────────┐│
│  │   virtio Back-end                      ││
│  │                                        ││
│  │   - Poll virtqueue                     ││
│  │   - Process descriptors                ││
│  │   - Access guest memory directly       ││
│  │   - No device emulation overhead       ││
│  └────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

### The virtqueue (vring) Data Structure

**Core of virtio:** A ring buffer in shared memory.

```
┌──────────────────────────────────────────────┐
│              Virtqueue                       │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Descriptor Table                      │ │
│  │  (Guest allocates, both can read)      │ │
│  │                                        │ │
│  │  [0]: addr=0x10000, len=1500, next=1  │ │
│  │  [1]: addr=0x11000, len=64, next=-1   │ │
│  │  [2]: addr=0x12000, len=2048, next=-1 │ │
│  │  ...                                   │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Available Ring (Guest writes)         │ │
│  │  "Here are descriptors ready for you"  │ │
│  │                                        │ │
│  │  idx: 3                                │ │
│  │  ring[0]: 0  (desc #0 available)      │ │
│  │  ring[1]: 2  (desc #2 available)      │ │
│  │  ring[2]: 5  (desc #5 available)      │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Used Ring (Host writes)               │ │
│  │  "Here are completed descriptors"      │ │
│  │                                        │ │
│  │  idx: 2                                │ │
│  │  ring[0]: (id=0, len=1500) completed  │ │
│  │  ring[1]: (id=2, len=2048) completed  │ │
│  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

### virtio-net Packet Transmission

```
Guest (virtio-net driver):
  1. Allocate buffer for packet
  2. Fill descriptor:
       desc[5].addr = packet_buffer_gpa
       desc[5].len = 1500
       desc[5].flags = 0
  
  3. Add to available ring:
       avail.ring[avail.idx % QUEUE_SIZE] = 5
       avail.idx++
  
  4. Notify host (kick):
       - Modern: Write to PCI notification register
       - Old: I/O port write (causes VM exit)
  
  5. Continue (don't wait!)

Host (QEMU virtio-net backend):
  6. Notification received
  7. Read available ring:
       desc_idx = avail.ring[last_avail_idx % QUEUE_SIZE]
       last_avail_idx++
  
  8. Read descriptor:
       addr = desc[desc_idx].addr
       len = desc[desc_idx].len
  
  9. Map guest memory, read packet data
  10. Send via TAP device
  
  11. Mark complete in used ring:
       used.ring[used.idx % QUEUE_SIZE] = (id=desc_idx, len=1500)
       used.idx++
  
  12. Inject interrupt (if needed)

Guest interrupt handler:
  13. Read used ring
  14. Process completed descriptors
  15. Free buffers
```

**Key optimizations:**

1. **Batching:**
```
Instead of:
  Send packet 1 → exit → notify → process → interrupt
  Send packet 2 → exit → notify → process → interrupt
  
virtio:
  Send packet 1
  Send packet 2
  Send packet 3
  Notify once → process all 3 → interrupt once
  
3 packets = 1 exit instead of 3!
```

2. **Interrupt suppression:**
```
Guest can disable interrupts when polling:
  avail.flags = VRING_AVAIL_F_NO_INTERRUPT
  
  while (packets_to_send) {
    add_to_queue(packet);
  }
  
  avail.flags = 0;  // Re-enable
  
Reduces interrupt overhead
```

3. **Event indices (modern virtio):**
```
Instead of "notify on every packet"
Use: "notify when used.idx reaches X"

Adaptive notifications based on load
```

---

### virtio Performance

```
Benchmark: 10 Gbps network throughput

Emulated e1000:
  - Throughput: 2-3 Gbps
  - VM exits: 500,000/sec
  - CPU: 80% (emulation overhead)

virtio-net:
  - Throughput: 9-9.5 Gbps
  - VM exits: 50,000/sec (10x fewer!)
  - CPU: 20%
  
virtio-net with vhost:
  - Throughput: 9.8 Gbps (near line rate)
  - VM exits: minimal
  - CPU: 10%
```

---

### vhost - Moving virtio to Kernel

**Problem:** QEMU is user space, requires context switches.

**Solution:** vhost kernel module.

```
Traditional virtio:
  Guest → virtqueue → VM exit → QEMU (user) → TAP device
  
vhost:
  Guest → virtqueue → vhost.ko (kernel) → TAP device
  
No user-space involved!
```

**Architecture:**

```
┌─────────────────────────────────────────┐
│         Guest OS                        │
│  virtio-net driver                      │
└──────────────┬──────────────────────────┘
               │
       ┌───────▼────────┐
       │   virtqueue    │
       │  (shared mem)  │
       └───────┬────────┘
               │
┌──────────────▼──────────────────────────┐
│         Host Kernel                     │
│                                         │
│  ┌────────────────────────────────────┐│
│  │  vhost-net.ko                      ││
│  │                                    ││
│  │  - Kernel thread polls virtqueue  ││
│  │  - Direct memory access           ││
│  │  - No user-space overhead         ││
│  └──────────────┬─────────────────────┘│
└─────────────────┼───────────────────────┘
                  │
            ┌─────▼──────┐
            │ TAP device │
            └────────────┘
```

**Setup:**

```c
// QEMU sets up vhost:
int vhost_fd = open("/dev/vhost-net", O_RDWR);

// Give vhost the virtqueue memory
struct vhost_memory mem = {
    .nregions = 1,
    .regions[0] = {
        .guest_phys_addr = 0,
        .memory_size = vm_memory_size,
        .userspace_addr = (u64)vm_memory
    }
};
ioctl(vhost_fd, VHOST_SET_MEM_TABLE, &mem);

// Give vhost the virtqueue descriptor
struct vhost_vring_file file = {
    .index = 0,
    .fd = eventfd_fd  // For notifications
};
ioctl(vhost_fd, VHOST_SET_VRING_KICK, &file);

// Start vhost kernel thread
ioctl(vhost_fd, VHOST_NET_SET_BACKEND, &tap_fd);
```

---

## Part 9: Modern Device Virtualization

### VFIO (Virtual Function I/O)

**Goal:** Give VM *direct* access to physical device (no emulation at all!)

**Requirements:**
- IOMMU (Intel VT-d, AMD-Vi)
- Device supports isolation

```
Traditional:
  Guest → virtio → QEMU → Host driver → Device
  (all software, some overhead)

VFIO:
  Guest → PCI passthrough → Device
  (direct hardware access, zero overhead!)
```

---

### IOMMU - Hardware Isolation

```
Without IOMMU:
  Device uses physical addresses
  DMA to any memory (security risk!)
  Can access other VMs' memory
  
With IOMMU:
  Device uses "I/O virtual addresses" (IOVA)
  IOMMU translates: IOVA → Physical
  Per-device page tables
  Device confined to VM's memory
  
┌────────────────────────────────────────┐
│         Guest OS (VM1)                 │
│  IOVA: 0x1000 → GPA: 0x1000           │
└──────────────┬─────────────────────────┘
               │
        ┌──────▼───────┐
        │    IOMMU     │  ← Per-VM page tables
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │  HPA: 0x5000 │
        └──────────────┘
```

**VFIO workflow:**

```c
// Host setup:
// 1. Unbind device from host driver
echo "0000:01:00.0" > /sys/bus/pci/devices/0000:01:00.0/driver/unbind

// 2. Bind to vfio-pci
echo "8086 10d3" > /sys/bus/pci/drivers/vfio-pci/new_id

// 3. QEMU passes device to guest
qemu-system-x86_64 \
  -device vfio-pci,host=01:00.0 \
  ...

// Guest sees real PCI device!
// Native driver loads
// Direct hardware access
```

---

### SR-IOV (Single Root I/O Virtualization)

**Problem:** One physical NIC, want to give to multiple VMs.

**Solution:** NIC presents multiple "virtual functions" (VFs).

```
Physical NIC:
┌────────────────────────────────────────┐
│     Physical Function (PF)             │
│     - Full NIC functionality           │
│     - Host management                  │
└────────────────────────────────────────┘
         │
         ├─────────────┬──────────────┬────────────────┐
         │             │              │                │
┌────────▼──────┐┌────▼─────┐┌──────▼────┐┌─────────▼──────┐
│ VF 0          ││ VF 1     ││ VF 2      ││ VF 3           │
│ (lightweight) ││          ││           ││                │
└────────┬──────┘└────┬─────┘└──────┬────┘└─────────┬──────┘
         │            │              │               │
    ┌────▼───┐   ┌───▼────┐    ┌───▼────┐     ┌────▼───┐
    │  VM1   │   │  VM2   │    │  VM3   │     │  VM4   │
    └────────┘   └────────┘    └────────┘     └────────┘
```

**Each VF:**
- Appears as separate PCI device
- Has own MAC address, queues
- Direct hardware access (via IOMMU)
- Near bare-metal performance

**Setup:**

```bash
# Enable SR-IOV (create 4 VFs)
echo 4 > /sys/bus/pci/devices/0000:01:00.0/sriov_numvfs

# New devices appear:
# 0000:01:00.1 (VF 0)
# 0000:01:00.2 (VF 1)
# 0000:01:00.3 (VF 2)
# 0000:01:00.4 (VF 3)

# Pass VF to VM via VFIO:
qemu-system-x86_64 \
  -device vfio-pci,host=01:00.1 \
  ...
```

**Performance:**

```
Benchmark: Network throughput (10 Gbps NIC)

virtio-net:         9 Gbps       (10% overhead)
virtio-net + vhost: 9.5 Gbps     (5% overhead)
SR-IOV VF:          9.9 Gbps     (<1% overhead)
Bare metal:         10 Gbps      (baseline)
```

---

## Summary: The Evolution

```
┌──────────────────────────────────────────────────────────┐
│  2003: Xen + Paravirtualization                         │
│  - Modify guest OS                                       │
│  - Hypercalls instead of privileged instructions         │
│  - Ring deprivileging                                    │
│  - Split drivers (frontend/backend)                     │
│  - 2% overhead                                           │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  2005-2006: Hardware Virtualization (VT-x, AMD-V)       │
│  - VMX root/non-root modes                              │
│  - Guest runs unmodified in Ring 0                      │
│  - VMCS for VM state                                     │
│  - EPT/NPT for nested paging                            │
│  - 5% overhead (without EPT)                            │
│  - 2% overhead (with EPT)                               │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  2007: KVM                                               │
│  - Linux kernel IS the hypervisor                       │
│  - Leverage existing kernel: scheduling, MM, drivers    │
│  - QEMU for device emulation                            │
│  - /dev/kvm ioctl() interface                           │
│  - 2-5% overhead                                         │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  2008-2010: virtio                                       │
│  - Paravirtualized devices (not full paravirt)          │
│  - Virtqueue for batching                               │
│  - Minimize VM exits                                     │
│  - 5% overhead → 2% overhead for I/O                    │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  2010+: vhost                                            │
│  - Move virtio backend to kernel                        │
│  - Eliminate user-space overhead                         │
│  - <1% overhead for I/O                                 │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  2012+: VFIO + SR-IOV                                    │
│  - Direct device assignment                              │
│  - IOMMU for isolation                                   │
│  - Multiple VMs sharing one device                       │
│  - <1% overhead (near bare metal)                       │
└──────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

**CPU Virtualization:**
- Early: Paravirtualization (modify guest)
- Modern: Hardware assist (VT-x/AMD-V)
- Guest runs natively in Ring 0 (VMX non-root)

**Memory Virtualization:**
- Early: Shadow page tables (complex, slow)
- Modern: EPT/NPT (hardware two-level translation)

**Device Virtualization:**
- Worst: Full emulation (QEMU e1000)
- Better: Paravirt devices (virtio)
- Best: Direct assignment (VFIO/SR-IOV)

**The Pattern:**
1. Software emulation (slow but works anywhere)
2. Paravirtualization (fast but needs guest changes)
3. Hardware acceleration (fast and no guest changes)

Modern virtualization uses ALL three:
- VT-x for CPU (hardware)
- virtio for common devices (paravirt)
- SR-IOV for performance-critical devices (hardware)
