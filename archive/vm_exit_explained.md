# VM Exit: The Core Mechanism of Virtualization

## The Simple Definition

**VM Exit = Guest does something that requires the hypervisor's attention**

When this happens:
1. CPU **stops** executing guest code
2. CPU **saves** guest state
3. CPU **switches** to hypervisor
4. Hypervisor **handles** the situation
5. Hypervisor **resumes** guest

Think of it like an **interrupt** - the guest is interrupted, hypervisor takes control.

---

## The Fundamental Problem

**Why do VM exits exist at all?**

```
Guest OS wants to:
  - Change page tables (CR3 register)
  - Access I/O ports (disk, network)
  - Execute privileged instructions
  - Handle interrupts
  
But:
  - Guest can't be allowed unrestricted access
  - Guest might affect other VMs
  - Guest might crash the host
  - Hypervisor needs to maintain isolation
  
Solution:
  Certain operations → VM exit
  Hypervisor validates/emulates
  Safe to continue
```

---

## The Hardware Mechanics (Intel VT-x)

### Two Execution Modes

```
┌─────────────────────────────────────────┐
│     VMX Root Mode (Hypervisor)          │
│     - Ring 0 of the "real" system      │
│     - Full control of hardware          │
│     - Can execute anything              │
└─────────────────────────────────────────┘
                    ↕
              VM Entry / VM Exit
                    ↕
┌─────────────────────────────────────────┐
│   VMX Non-Root Mode (Guest)             │
│   - Guest thinks it's in Ring 0         │
│   - Actually running in restricted mode │
│   - Certain operations cause exit       │
└─────────────────────────────────────────┘
```

---

### What Happens During VM Exit (CPU Level)

**Automatic hardware sequence:**

```
Step 1: Guest executes sensitive operation
────────────────────────────────────────────
Guest code:
  mov eax, 0x1000
  mov cr3, eax        ← Try to change page table base
  
CPU detects: "CR3 write in VMX non-root mode"
  → Configured to cause VM exit
  → Automatic sequence begins

Step 2: CPU saves guest state to VMCS
──────────────────────────────────────
VMCS (Virtual Machine Control Structure) updated:
  
  Guest State Area:
    RIP = 0x401234           ← Where guest was executing
    RAX = 0x1000             ← All registers
    RBX = ...
    ...
    CR3 = 0x5000             ← Current page table (unchanged)
    RFLAGS = ...
    
  Exit Information:
    Exit Reason = 28         ← CR_ACCESS (CR3 write)
    Exit Qualification = 3   ← Which CR register (CR3)
    Guest Linear Address = N/A
    Guest Physical Address = N/A

Step 3: CPU loads host state from VMCS
───────────────────────────────────────
VMCS Host State Area:
  RIP = 0xffffffff81234567  ← Hypervisor exit handler address
  RSP = 0xffffffff82000000  ← Hypervisor stack
  CR3 = 0x9000              ← Hypervisor page table
  ...

CPU switches to VMX root mode:
  - Now executing hypervisor code
  - Using hypervisor page tables
  - Full privileges

Step 4: Jump to exit handler
─────────────────────────────
CPU jumps to RIP (0xffffffff81234567)
  
This is KVM's exit handler in Linux kernel:
  vmx_vcpu_run() returns
  kvm_arch_vcpu_ioctl_run() continues
  Reads exit reason from VMCS
  Dispatches to appropriate handler

Step 5: Hypervisor handles the exit
────────────────────────────────────
KVM exit handler:
  exit_reason = vmcs_read32(VM_EXIT_REASON);
  
  switch (exit_reason) {
    case EXIT_REASON_CR_ACCESS:
      handle_cr_access(vcpu);
      break;
    case EXIT_REASON_IO_INSTRUCTION:
      handle_io(vcpu);
      break;
    // ... many more cases
  }

handle_cr_access():
  qualification = vmcs_read64(EXIT_QUALIFICATION);
  cr_num = (qualification >> 4) & 15;  // = 3 (CR3)
  
  if (cr_num == 3) {
    // Guest wants to change CR3
    u64 new_cr3 = get_guest_reg(RAX);
    
    // Update guest's page table
    kvm_mmu_load(vcpu, new_cr3);
    
    // Update EPT mappings if needed
    // ...
  }

Step 6: Resume guest (VM Entry)
────────────────────────────────
Hypervisor finished handling
  
Execute: VMRESUME instruction
  
CPU:
  1. Load guest state from VMCS
  2. Switch to VMX non-root mode
  3. Jump to guest RIP (next instruction after mov cr3)
  
Guest continues executing (unaware it was interrupted)
```

---

## VM Exit Causes

### Common Exit Reasons

**1. Control Register Access:**
```
mov cr3, eax        → EXIT_REASON_CR_ACCESS
mov eax, cr0        → EXIT_REASON_CR_ACCESS
mov cr4, ebx        → EXIT_REASON_CR_ACCESS

Why: Page table changes, mode changes
Handler: Update guest page tables, EPT mappings
```

**2. I/O Port Access:**
```
in al, 0x60         → EXIT_REASON_IO_INSTRUCTION
out 0x3F8, al       → EXIT_REASON_IO_INSTRUCTION

Why: Guest accessing hardware (keyboard, serial port, disk)
Handler: Emulate device behavior or forward to real device
```

**3. CPUID Instruction:**
```
cpuid               → EXIT_REASON_CPUID

Why: Query CPU features
Handler: Return virtualized CPU info (hide/expose features)
```

**4. Memory-Mapped I/O (MMIO):**
```
mov eax, [0xFEE00000]  → EXIT_REASON_EPT_VIOLATION
                          (if address is MMIO region)

Why: Guest accessing device memory (PCI BARs, APIC, etc.)
Handler: Emulate device register read/write
```

**5. MSR Access:**
```
rdmsr               → EXIT_REASON_MSR_READ
wrmsr               → EXIT_REASON_MSR_WRITE

Why: Model-Specific Registers (performance counters, features)
Handler: Emulate or passthrough
```

**6. HLT Instruction:**
```
hlt                 → EXIT_REASON_HLT

Why: Guest CPU going idle
Handler: Schedule other vCPUs, sleep until interrupt
```

**7. VMCALL (Hypercall):**
```
vmcall              → EXIT_REASON_VMCALL

Why: Explicit guest → hypervisor call (paravirtualization)
Handler: Execute requested hypervisor function
```

**8. Exception/Interrupt:**
```
Page fault          → EXIT_REASON_EXCEPTION_NMI
                       (if configured)

Why: Need hypervisor involvement (e.g., nested page fault)
Handler: Handle EPT violation, inject exception to guest
```

**9. External Interrupt:**
```
Physical interrupt  → EXIT_REASON_EXTERNAL_INTERRUPT
  arrives

Why: Interrupt window, preemption
Handler: Handle interrupt, potentially schedule different vCPU
```

**10. PAUSE Instruction:**
```
pause               → EXIT_REASON_PAUSE
                       (in spin-wait loops)

Why: Detect CPU spinning, scheduler hint
Handler: Yield to other vCPUs/processes
```

---

## The VMCS (Virtual Machine Control Structure)

**Per-vCPU data structure that controls exits:**

```
VMCS for vCPU 0:
┌────────────────────────────────────────────────┐
│  Guest State Area                              │
│  ─────────────────                             │
│  All registers when guest running:             │
│    RIP, RSP, RAX, RBX, ... R15                │
│    CR0, CR3, CR4                               │
│    CS, DS, ES, SS, FS, GS                      │
│    GDTR, IDTR, LDTR, TR                        │
│    DR7 (debug register)                        │
│    RFLAGS                                      │
│    MSRs (various)                              │
├────────────────────────────────────────────────┤
│  Host State Area                               │
│  ─────────────────                             │
│  Where to go on VM exit:                       │
│    RIP = exit_handler_address                  │
│    RSP = hypervisor_stack                      │
│    CR3 = hypervisor_page_table                 │
│    CS, DS, ES, SS                              │
│    FS, GS bases                                │
├────────────────────────────────────────────────┤
│  VM-Execution Control Fields                   │
│  ────────────────────────────                  │
│  What causes VM exits:                         │
│                                                │
│  Pin-Based Controls:                           │
│    External-interrupt exiting: 1               │
│    NMI exiting: 1                              │
│                                                │
│  Processor-Based Controls:                     │
│    HLT exiting: 1                              │
│    INVLPG exiting: 0                           │
│    MWAIT exiting: 1                            │
│    RDPMC exiting: 0                            │
│    RDTSC exiting: 0                            │
│    CR3-load exiting: 0  ← With EPT, not needed│
│    CR3-store exiting: 0                        │
│    CR8-load exiting: 1                         │
│    CR8-store exiting: 1                        │
│    Use TPR shadow: 1                           │
│    Activate secondary controls: 1              │
│                                                │
│  Secondary Processor-Based Controls:           │
│    Enable EPT: 1                               │
│    Enable VPID: 1                              │
│    PAUSE-loop exiting: 1                       │
│    INVPCID exiting: 0                          │
│                                                │
│  Exception Bitmap (which exceptions exit):     │
│    Page Fault (14): 0   ← EPT handles it      │
│    General Protection (13): 1                  │
│                                                │
│  I/O-Bitmap Addresses:                         │
│    I/O-Bitmap A: 0xXXXX  ← Bits for ports 0-7FFF│
│    I/O-Bitmap B: 0xYYYY  ← Bits for ports 8000-FFFF│
│    (1 = cause exit, 0 = passthrough)           │
│                                                │
│  MSR-Bitmap Address:                           │
│    MSR-Bitmap: 0xZZZZ                          │
│    (Bitmap of which MSRs cause exit)           │
├────────────────────────────────────────────────┤
│  VM-Exit Control Fields                        │
│  ──────────────────────                        │
│  Save/load host/guest state on exit           │
├────────────────────────────────────────────────┤
│  VM-Exit Information Fields                    │
│  ──────────────────────────                    │
│  Why did we exit:                              │
│    Exit Reason: 28 (CR_ACCESS)                 │
│    Exit Qualification: 0x3 (CR3)               │
│    Guest Linear Address: 0xXXXX                │
│    Guest Physical Address: 0xYYYY              │
│    VM-Exit Instruction Length: 3               │
│    VM-Exit Instruction Info: ...               │
├────────────────────────────────────────────────┤
│  VM-Entry Control Fields                       │
│  ───────────────────────                       │
│  How to enter guest                            │
└────────────────────────────────────────────────┘
```

---

## Example: I/O Port Exit (Detailed)

**Scenario: Guest writes to serial port**

```
┌────────────────────────────────────────────────┐
│ Guest code (Linux serial driver):             │
│                                                │
│   void serial_putchar(char c) {               │
│     outb(c, 0x3F8);  ← Write to serial port   │
│   }                                            │
└────────────────────────────────────────────────┘
     ↓
Assembly:
  mov al, 'H'           ; Character to send
  mov dx, 0x3F8         ; Serial port base
  out dx, al            ; ← This causes VM exit
     ↓

CPU detects: OUT instruction to port 0x3F8
  Check I/O Bitmap in VMCS:
    Bit for port 0x3F8 = 1 (cause exit)
  → VM Exit!

───────────────────────────────────────────────────
VM Exit Sequence (hardware):

1. Save guest state to VMCS:
   RIP = address of next instruction (after OUT)
   RAX = 'H'
   RDX = 0x3F8
   ... all other registers ...

2. Record exit info:
   Exit Reason = EXIT_REASON_IO_INSTRUCTION (30)
   Exit Qualification:
     Bits 0-2: Size (0=1 byte, 1=2 bytes, 3=4 bytes) = 0
     Bit 3: Direction (0=OUT, 1=IN) = 0
     Bit 4: String instruction = 0
     Bit 5: REP prefixed = 0
     Bits 16-31: Port number = 0x3F8
   
3. Load host state:
   RIP = kvm_exit_handler
   CR3 = host_page_table
   → Switch to VMX root mode

4. Jump to kvm_exit_handler
───────────────────────────────────────────────────
Hypervisor handling (KVM):

kvm_exit_handler() {
  u32 exit_reason = vmcs_read32(VM_EXIT_REASON);
  
  switch (exit_reason) {
    case EXIT_REASON_IO_INSTRUCTION:
      return handle_io(vcpu);
  }
}

handle_io(vcpu) {
  u64 qual = vmcs_read64(EXIT_QUALIFICATION);
  
  int port = (qual >> 16) & 0xFFFF;  // 0x3F8
  int size = (qual & 7) + 1;          // 1 byte
  bool is_in = (qual >> 3) & 1;       // false (OUT)
  
  if (is_in) {
    // IN instruction - read from port
    data = emulate_io_read(port, size);
    set_guest_register(RAX, data);
  } else {
    // OUT instruction - write to port
    data = get_guest_register(RAX);  // 'H'
    emulate_io_write(port, size, data);
  }
  
  // Advance RIP past the OUT instruction
  skip_emulated_instruction(vcpu);
  
  return 1; // Continue guest
}

emulate_io_write(0x3F8, 1, 'H') {
  // Port 0x3F8 is COM1 serial port
  // In QEMU/Firecracker: forward to emulated serial device
  
  if (port >= 0x3F8 && port <= 0x3FF) {
    // Serial port - exit to user space (QEMU/Firecracker)
    vcpu->run->exit_reason = KVM_EXIT_IO;
    vcpu->run->io.direction = KVM_EXIT_IO_OUT;
    vcpu->run->io.port = port;
    vcpu->run->io.size = size;
    vcpu->run->io.count = 1;
    vcpu->run->io.data_offset = ...;
    *(u8*)(vcpu->run + data_offset) = 'H';
    
    return 0; // Exit to user space
  }
}
───────────────────────────────────────────────────
Return to QEMU/Firecracker:

ioctl(vcpu_fd, KVM_RUN) returns

QEMU:
  run = vcpu->run;
  
  if (run->exit_reason == KVM_EXIT_IO) {
    port = run->io.port;     // 0x3F8
    data = run->io.data;     // 'H'
    
    serial_device_write(port, data);
    // Actually outputs 'H' to host terminal
  }

Resume guest:
  ioctl(vcpu_fd, KVM_RUN);
  
───────────────────────────────────────────────────
VM Entry (resume guest):

CPU:
  1. Load guest state from VMCS
  2. Guest RIP now points to instruction after OUT
  3. Switch to VMX non-root
  4. Continue execution

Guest continues (never knew it was interrupted)
```

---

## The Performance Cost

**Why VM exits are expensive:**

```
VM Exit overhead:
┌────────────────────────────────────────┐
│ 1. Hardware state save                 │  ~500 cycles
│    - Save all guest registers          │
│    - Save control registers            │
│    - Update VMCS                       │
├────────────────────────────────────────┤
│ 2. Context switch                      │  ~200 cycles
│    - Load host page tables (CR3)       │
│    - TLB flush (if VPID not used)      │
│    - Switch to host stack              │
├────────────────────────────────────────┤
│ 3. Hypervisor handling                 │  ~1000+ cycles
│    - Determine exit reason             │
│    - Dispatch to handler               │
│    - Emulate operation                 │
│    - Update state                      │
├────────────────────────────────────────┤
│ 4. Hardware state restore              │  ~500 cycles
│    - Load all guest registers          │
│    - Restore control state             │
├────────────────────────────────────────┤
│ 5. Return to guest                     │  ~200 cycles
│    - VMRESUME instruction              │
│    - Switch page tables                │
│    - Continue guest                    │
└────────────────────────────────────────┘

Total: ~2400 cycles minimum
At 2 GHz: ~1.2 microseconds per exit

For comparison:
  - System call: ~100 cycles
  - VM exit: ~2400 cycles (24x slower!)
```

**Real-world measurements:**

```
Benchmark: 1,000,000 operations

System call (getpid):
  Time: 50 ms
  Per operation: 50 ns
  Cycles: ~100

VM exit + resume (no-op):
  Time: 1200 ms
  Per operation: 1200 ns
  Cycles: ~2400

VM exit + I/O emulation:
  Time: 3000 ms
  Per operation: 3000 ns
  Cycles: ~6000+
```

---

## Why Minimizing Exits Matters

**Example: Network packet transmission**

```
Emulated E1000 (every register write exits):

send_packet() {
  // 1. Write descriptor address
  outl(E1000_TDH, desc_addr);     → VM exit #1
  
  // 2. Write packet length
  outl(E1000_TDT, pkt_len);       → VM exit #2
  
  // 3. Write control register
  outl(E1000_CTRL, start_tx);     → VM exit #3
  
  // 4. Check status register
  status = inl(E1000_STATUS);     → VM exit #4
  while (!(status & TX_DONE)) {
    status = inl(E1000_STATUS);   → VM exit #5, #6, #7...
  }
}

One packet: 7+ VM exits
Time: ~8-10 microseconds
Throughput: ~100,000 packets/sec max
───────────────────────────────────────────────────

virtio-net (batch via queue):

send_packets(packets[], count) {
  for (i = 0; i < count; i++) {
    // All writes to shared memory (no exits!)
    desc[i].addr = packets[i].addr;
    desc[i].len = packets[i].len;
    avail_ring[i] = i;
  }
  avail_ring.idx += count;  // Still no exit
  
  // Single notification
  writel(0, notify_addr);   → VM exit (only one!)
  
  // Host processes all packets in batch
  // Single interrupt back
}

1000 packets: 2 VM exits total (notify + interrupt)
Time: ~3 microseconds total
Throughput: ~1,000,000 packets/sec

Speedup: 10x fewer exits → 10x throughput
```

---

## How Different Technologies Minimize Exits

### 1. Hardware Virtualization (VT-x)

**Before VT-x (binary translation):**
```
EVERY privileged instruction → emulation
mov cr3, eax → Scan, detect, translate, emulate
Result: Massive overhead
```

**With VT-x:**
```
MOST instructions execute natively
Only configured operations → VM exit
mov cr3, eax → Still exits (but fast hardware path)
Regular instructions → Native execution
```

**With VT-x + EPT:**
```
Guest page table modifications → No exit!
Guest can freely modify page tables
Hardware walks both guest PT and EPT
Only EPT violations exit

Before EPT: Every page table change → exit
With EPT: No exits for page table changes
```

---

### 2. Paravirtualization (Xen)

**Problem: Lots of exits for privileged operations**

**Solution: Replace with hypercalls**

```
Traditional (causes exits):
  mov cr3, eax       → VM exit → Hypervisor handles
  
Paravirtualized:
  call xen_set_cr3   → Hypercall (controlled exit)
  
Still exits, but:
  - Explicit (not trapping)
  - Can batch (update multiple things in one call)
  - More efficient path
```

---

### 3. virtio

**Problem: Device I/O causes many exits**

**Solution: Batch operations via queues**

```
Emulated device:
  For each packet:
    - Write descriptor → exit
    - Write length → exit
    - Start TX → exit
    - Check status → exit
  = 4 exits/packet

virtio:
  For N packets:
    - Write N descriptors (shared memory, no exit)
    - Notify once → 1 exit
    - Process all N
    - Interrupt once → back to guest
  = 2 exits total (amortized)
```

---

### 4. vhost

**Problem: Still exiting to user space (QEMU)**

**Solution: Handle in kernel**

```
virtio with QEMU:
  Guest → VM exit → KVM → User space (QEMU) → TAP
  (Kernel → User → Kernel transitions)

virtio with vhost:
  Guest → VM exit → KVM → vhost.ko → TAP
  (All in kernel!)
  
Eliminates context switches to user space
```

---

### 5. SR-IOV / Device Passthrough

**Problem: ALL device I/O exits to hypervisor**

**Solution: Let guest access device directly**

```
Emulated/virtio:
  Guest → VM exit → Hypervisor → Device
  Every I/O goes through hypervisor

SR-IOV:
  Guest → Device (direct!)
  No VM exits for normal I/O
  
IOMMU ensures isolation
Near-native performance
```

---

## Exit Reason Categories

```
┌────────────────────────┬──────────┬─────────────────┐
│ Category               │ Frequency│ Can Eliminate?  │
├────────────────────────┼──────────┼─────────────────┤
│ CR access (no EPT)     │ High     │ Yes (EPT)       │
│ CR access (with EPT)   │ Low      │ No (needed)     │
│                        │          │                 │
│ I/O ports (emulated)   │ Very High│ Yes (virtio)    │
│ I/O ports (virtio)     │ Low      │ Partial (batch) │
│ I/O ports (passthrough)│ None     │ Eliminated      │
│                        │          │                 │
│ MMIO (emulated)        │ Very High│ Yes (virtio)    │
│ MMIO (virtio notify)   │ Low      │ No (needed)     │
│                        │          │                 │
│ EPT violations         │ Medium   │ Partial (cache) │
│ Page faults            │ Low      │ No (needed)     │
│                        │          │                 │
│ CPUID                  │ Low      │ No (needed)     │
│ MSR access             │ Medium   │ Partial         │
│                        │          │                 │
│ HLT (idle)             │ Low      │ No (feature)    │
│ External interrupt     │ Medium   │ No (needed)     │
│                        │          │                 │
│ Hypercalls (paravirt)  │ Medium   │ No (by design)  │
└────────────────────────┴──────────┴─────────────────┘
```

---

## Summary: The Exit Hierarchy

**Most expensive (avoid):**
```
I/O port access for emulated devices
  → Every register read/write
  → 1000s of exits per second
  → Solution: virtio
```

**Moderate cost (minimize):**
```
virtio notifications
  → Once per batch
  → 100s of exits per second
  → Acceptable with batching
```

**Low cost (acceptable):**
```
Hypercalls (paravirt)
  Control plane operations
  → 10s of exits per second
  → Explicitly requested
```

**Zero cost (ideal):**
```
Direct device access (SR-IOV)
  → No exits for data path
  → Native performance
```

---

## The Big Picture

**VM Exit is the reason for everything we've discussed:**

1. **Hardware virtualization (VT-x)** exists to make exits fast and predictable

2. **EPT/NPT** exists to eliminate exits for page table changes

3. **Paravirtualization** exists to replace unintentional exits with intentional hypercalls

4. **virtio** exists to batch operations and minimize device I/O exits

5. **vhost** exists to handle exits in kernel (avoid user space)

6. **SR-IOV** exists to eliminate exits entirely for performance-critical devices

**The pattern:** The entire evolution of virtualization is about **minimizing VM exits**.

Every microsecond spent in a VM exit is a microsecond NOT running guest code. At millions of exits per second, this adds up to significant overhead.

**Goal:** Make the common case fast (no exit) and the uncommon case correct (proper exit handling).
