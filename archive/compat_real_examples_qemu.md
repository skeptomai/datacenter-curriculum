# Real-World Examples and QEMU 64-bit

## Honest Answer About Current Examples

**Let me be upfront:** Finding a clear current example is tricky because most mature architectures with KVM have implemented both CONFIG_COMPAT and CONFIG_KVM_COMPAT.

However, here are the most likely candidates:

---

## Candidate 1: RISC-V (Most Likely Example)

### The Timeline

```
RISC-V development timeline:

2021: RISC-V hypervisor extension spec frozen
2021 (Linux 5.16): KVM support added for RISC-V
2022 (Linux 5.17): RV32 compat support added for RV64
  - Can run 32-bit RISC-V binaries on 64-bit kernel
  - CONFIG_COMPAT=y now available

2024: Current status
  - CONFIG_COMPAT: ✓ Available
  - CONFIG_KVM: ✓ Available
  - CONFIG_KVM_COMPAT: ? Unclear/possibly not implemented
```

---

### The Situation

```c
RISC-V 64-bit (RV64) can now:
  ✓ Run 32-bit RISC-V binaries (RV32) via CONFIG_COMPAT
  ✓ Provide KVM virtualization via CONFIG_KVM
  
But does KVM work with 32-bit processes?
  
Likely scenario:
  CONFIG_COMPAT=y        ← General 32-bit support exists
  CONFIG_KVM_COMPAT=n    ← KVM compat handlers not implemented yet
  
Why?
  - RISC-V is new, still maturing
  - RV32 userspace is rare (most use RV64)
  - KVM compat might not be priority yet
  - Could be added in future kernels
```

---

### How to Check (if you have RISC-V hardware)

```bash
# On RISC-V 64-bit system
grep CONFIG_COMPAT /boot/config-$(uname -r)
# Likely: CONFIG_COMPAT=y

grep CONFIG_KVM /boot/config-$(uname -r)
# Likely: CONFIG_KVM=y

grep CONFIG_KVM_COMPAT /boot/config-$(uname -r)
# Possibly: CONFIG_KVM_COMPAT is not set
# Or might not even appear (not implemented)

# Test with 32-bit binary (if available)
file /path/to/rv32/qemu
# RISC-V 32-bit executable

./qemu -enable-kvm
# Might get: "Invalid argument" on KVM ioctls
```

---

## Candidate 2: MIPS64 (Historical/Possible)

### The Situation

```
MIPS64 has:
  ✓ CONFIG_COMPAT support (can run MIPS32 on MIPS64)
  ✓ CONFIG_KVM support
  
Status of CONFIG_KVM_COMPAT:
  - Implemented for some MIPS variants
  - But MIPS support in general is being deprecated
  - Less actively maintained
  - Might have CONFIG_COMPAT without full KVM_COMPAT on some configs
```

**Note:** MIPS is being phased out of the kernel, so this is more historical.

---

## Why This is Hard to Find

### The Reality

```
Most architectures that have BOTH features implement BOTH configs:

┌──────────────┬────────────┬──────────┬──────────────┐
│ Architecture │ COMPAT     │ KVM      │ KVM_COMPAT   │
├──────────────┼────────────┼──────────┼──────────────┤
│ x86_64       │ ✓ (i386)   │ ✓        │ ✓ Implemented│
│ ARM64        │ ✓ (aarch32)│ ✓        │ ✓ Implemented│
│ PowerPC64    │ ✓ (ppc32)  │ ✓        │ ✓ Implemented│
│ s390x        │ ✓ (s390)   │ ✓        │ ✓ Implemented│
│ RISC-V       │ ✓ (rv32)   │ ✓        │ ? Unknown    │
│ MIPS64       │ ✓ (mips32) │ ✓ (legacy│ ? Varies     │
└──────────────┴────────────┴──────────┴──────────────┘

Why all have KVM_COMPAT?
  - If you implement KVM for an arch with compat support
  - You probably want 32-bit QEMU to work
  - So KVM_COMPAT gets implemented too
  - It's just part of "making KVM work properly"
```

---

## The Theoretical vs Practical

### Theoretical Scenario

```c
CONFIG_COMPAT=y        // 32-bit support exists
CONFIG_KVM=y           // KVM exists  
CONFIG_KVM_COMPAT=n    // KVM compat NOT implemented

Example workflow:
  1. 32-bit QEMU executable exists
  2. open("/dev/kvm") → Success (file open works)
  3. ioctl(kvm_fd, KVM_CREATE_VM) → -EINVAL
     (kvm_no_compat_ioctl returns error)
  4. QEMU fails with "Could not access KVM kernel module"
```

---

### Practical Reality

```
Why it's rare:
  1. If an architecture supports both 32 and 64-bit
  2. And implements KVM
  3. Developers usually implement KVM_COMPAT too
     (otherwise people complain: "32-bit QEMU doesn't work!")
  
When it MIGHT not be implemented:
  1. Very new architecture (RISC-V early days)
  2. Low priority (nobody uses 32-bit anymore)
  3. Architecture being deprecated (MIPS)
  4. Embedded-only arch (no demand for virtualization)
```

---

## About QEMU 64-bit Support

### The Key Point: QEMU Bitness ≠ Guest Bitness

**This is crucial to understand:**

```
QEMU Bitness (the program):
  - 32-bit QEMU binary (runs on 32-bit or 64-bit OS with compat)
  - 64-bit QEMU binary (runs on 64-bit OS only)
  
Guest Bitness (what QEMU emulates):
  - Can emulate 32-bit guests (i386, ARM32, etc.)
  - Can emulate 64-bit guests (x86_64, ARM64, etc.)
  
THESE ARE INDEPENDENT!

Examples:
  64-bit QEMU → emulate 32-bit i386 guest ✓
  64-bit QEMU → emulate 64-bit x86_64 guest ✓
  32-bit QEMU → emulate 32-bit i386 guest ✓
  32-bit QEMU → emulate 64-bit x86_64 guest ✓ (if arch supports)
```

---

### Why 64-bit QEMU is Standard Now

**Reason 1: Memory Limitations**

```
32-bit process limitations:
  - Maximum 4 GB address space (2^32)
  - Typically ~3 GB usable (1 GB for kernel)
  - Guest VM memory comes from QEMU's address space
  
Example with 32-bit QEMU:
  Guest VM with 4 GB RAM:
    32-bit QEMU address space: 3 GB usable
    Guest needs: 4 GB
    Result: CAN'T ALLOCATE! Fails!
  
Example with 64-bit QEMU:
  Guest VM with 64 GB RAM:
    64-bit QEMU address space: 128 TB (theoretical)
    Guest needs: 64 GB
    Result: Works fine!

Modern VMs often have:
  - 8 GB, 16 GB, 32 GB+ RAM
  - Impossible with 32-bit QEMU
  - MUST use 64-bit QEMU
```

---

**Reason 2: Performance**

```
64-bit code advantages:
  - More registers (x86_64 has 16 vs x86's 8)
  - Better compiler optimizations
  - Modern CPU features (SSE, AVX)
  - Better memory performance
  
32-bit QEMU on 64-bit host:
  - Needs compat layer (syscall translation)
  - Pointer translation overhead
  - Suboptimal code generation
  
64-bit QEMU on 64-bit host:
  - Native execution
  - No compat layer
  - Optimal performance
```

---

**Reason 3: Distribution Trends**

```
Modern Linux distributions:

2010s:
  - Default: 32-bit + 64-bit packages
  - QEMU available in both versions
  
2020s:
  - Default: 64-bit only
  - 32-bit packages deprecated/removed
  - Ubuntu dropped 32-bit support (mostly)
  - Fedora dropped 32-bit support
  - Debian: 64-bit primary, 32-bit secondary
  
Example (Ubuntu 22.04):
  apt search qemu-system-x86
  → qemu-system-x86 (64-bit binary only)
  → No 32-bit version in repos
```

---

**Reason 4: Nobody Needs 32-bit QEMU Anymore**

```
Use cases for 32-bit QEMU:
  ❌ Running on 32-bit only system
     (32-bit systems are obsolete)
  
  ❌ Saving memory
     (64-bit QEMU uses ~same memory as 32-bit)
     (guest RAM is separate, mapped)
  
  ❌ Better performance
     (64-bit is faster, not slower)
  
  ❌ Compatibility
     (64-bit can emulate anything 32-bit can)

Conclusion: Zero good reasons to use 32-bit QEMU!
```

---

### What QEMU Version Do You Use?

```bash
# Check your QEMU
file /usr/bin/qemu-system-x86_64

# On modern system (2020+):
/usr/bin/qemu-system-x86_64: ELF 64-bit LSB executable, x86-64

# NOT:
/usr/bin/qemu-system-x86_64: ELF 32-bit LSB executable, Intel 80386
# ↑ This would be very unusual today!


# Even when emulating 32-bit guests:
qemu-system-i386 --version  # The guest type
file /usr/bin/qemu-system-i386

Output: ELF 64-bit LSB executable
# ↑ QEMU binary is 64-bit
# ↓ But it emulates i386 (32-bit) guests
```

---

### Historical Context

**Why CONFIG_KVM_COMPAT Was Important (2000s-2010s):**

```
Scenario in 2008:

Many systems:
  - Transitioning from 32-bit to 64-bit
  - Mixed environments common
  - 32-bit QEMU still widely used
  - Need KVM acceleration

Without KVM_COMPAT:
  User: "I upgraded to 64-bit kernel"
  User: "Now my 32-bit QEMU doesn't work with KVM!"
  User: "It's slow without KVM!"
  Maintainer: "Compile 64-bit QEMU"
  User: "But my build system is 32-bit..."
  
With KVM_COMPAT:
  32-bit QEMU + 64-bit kernel = Works!
  Smooth transition period
  Users happy
```

---

**Why It's Less Important Now (2020s):**

```
Modern reality:

✓ Everyone uses 64-bit kernels
✓ Everyone uses 64-bit QEMU
✓ Nobody distributes 32-bit QEMU anymore
✓ No performance reason to use 32-bit

If CONFIG_KVM_COMPAT was disabled today:
  Impact: Almost zero
  Affected users: Maybe 0.001%?
  
So for new architectures (like RISC-V):
  Developers might think:
  "Does anyone actually need 32-bit QEMU to work?"
  "Probably not, let's not bother implementing it"
  "Focus on more important features"
```

---

## Practical Example: RISC-V Today

### Hypothetical Scenario

```bash
# On RISC-V 64-bit system with CONFIG_COMPAT

# 64-bit QEMU (standard):
file /usr/bin/qemu-system-riscv64
# Output: ELF 64-bit LSB executable

qemu-system-riscv64 -enable-kvm -m 2G ...
# Works perfectly! ✓

# 32-bit QEMU (unusual):
file ~/rv32/qemu-system-riscv64  
# Output: ELF 32-bit LSB executable

~/rv32/qemu-system-riscv64 -enable-kvm -m 2G ...
# Error: Could not access KVM kernel module: Invalid argument
# (If CONFIG_KVM_COMPAT not implemented)

# But why would you even have 32-bit QEMU?
# Nobody distributes it!
# You'd have to compile it yourself on 32-bit system
# Which nobody has anymore!
```

---

## Summary

### Real-World Example

**Most likely: RISC-V**
```
CONFIG_COMPAT=y        ← Can run RV32 on RV64
CONFIG_KVM=y           ← KVM virtualization works
CONFIG_KVM_COMPAT=?    ← Possibly not implemented yet
```

**Why it might not matter:**
- Nobody uses 32-bit QEMU on RISC-V
- RISC-V is new, RV32 is rare
- Everyone uses 64-bit QEMU

---

### About 64-bit QEMU

**Key points:**
1. **Modern QEMU is always 64-bit** (the program itself)
2. **64-bit QEMU can emulate 32-bit or 64-bit guests** (independent!)
3. **32-bit QEMU is obsolete** (can't allocate enough memory, worse performance)
4. **No reason to use 32-bit QEMU anymore** (distributions don't even package it)
5. **CONFIG_KVM_COMPAT is less critical** in modern times because everyone uses 64-bit QEMU

**The practical reality:**
```
Year 2024:
  % of users running 32-bit QEMU: ~0%
  % of users running 64-bit QEMU: ~100%
  
Impact of CONFIG_KVM_COMPAT=n: Negligible
  (Because nobody uses 32-bit QEMU!)
```

**So when I said "everyone uses 64-bit QEMU now":**
- I meant: The QEMU binary itself is 64-bit
- NOT: People only emulate 64-bit guests
- 64-bit QEMU can and does emulate both 32-bit and 64-bit guests
- This is why CONFIG_KVM_COMPAT is becoming less important

---

## The Irony

```
The code exists to support 32-bit QEMU:
  #ifdef CONFIG_KVM_COMPAT
    .compat_ioctl = kvm_vcpu_compat_ioctl
  #else
    .compat_ioctl = kvm_no_compat_ioctl  // Returns -EINVAL
  #endif

But in practice:
  - Almost nobody uses 32-bit QEMU anymore
  - The code is "defensive programming"
  - Handles an edge case that rarely happens
  - But good to have for completeness
  
New architectures might skip it:
  - "Nobody will use 32-bit QEMU on RISC-V"
  - "Not worth the implementation effort"
  - "Can always add later if needed"
```

This is a classic example of code that was essential 15 years ago but is now mostly historical!
