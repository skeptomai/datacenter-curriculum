---
level: specialized
estimated_time: 50 min
prerequisites:
  - 05_specialized/05_compatibility/01_kvm_compat.md
next_recommended:
  - 05_specialized/05_compatibility/03_compat_examples.md
tags: [virtualization, kvm, compatibility, kernel-config, compat]
---

# CONFIG_COMPAT vs CONFIG_KVM_COMPAT: The Distinction

## Your Question is Spot On!

**Yes! There are two separate concepts:**

1. **CONFIG_COMPAT** - Architecture supports compat tasks (32-bit on 64-bit) in general
2. **CONFIG_KVM_COMPAT** - KVM specifically supports compat tasks

**They are NOT the same thing!**

---

## The Hierarchy

```
CONFIG_COMPAT (general kernel support)
    ↓
    Does the architecture support running 32-bit binaries
    on a 64-bit kernel AT ALL?
    
    ↓
    
CONFIG_KVM_COMPAT (KVM-specific)
    ↓
    Did someone implement the KVM compat ioctl handlers
    for this architecture?
```

---

## Three Scenarios

### Scenario 1: Both Enabled (Most Common)

```
CONFIG_COMPAT=y
CONFIG_KVM_COMPAT=y

Examples: x86_64, ARM64

What this means:
  ✓ Architecture supports compat tasks (32-bit on 64-bit)
  ✓ KVM also supports compat tasks
  ✓ 32-bit QEMU can use KVM
  ✓ Everything works!

Example:
  $ uname -m
  x86_64
  
  $ file /usr/bin/qemu-system-x86_64
  /usr/bin/qemu-system-x86_64: ELF 32-bit LSB executable, Intel 80386
  # ↑ This is a 32-bit binary!
  
  $ /usr/bin/qemu-system-x86_64 -enable-kvm ...
  # Works perfectly! Uses KVM compat infrastructure
```

---

### Scenario 2: CONFIG_COMPAT=y, CONFIG_KVM_COMPAT=n

```
CONFIG_COMPAT=y        ← Architecture supports compat tasks
CONFIG_KVM_COMPAT=n    ← But KVM doesn't!

This can happen when:
  - Architecture has compat support
  - But nobody implemented KVM compat handlers yet
  - Or it was deemed unnecessary/too complex

What this means:
  ✓ 32-bit binaries CAN run on the system generally
  ✓ They can use most kernel features
  ✗ But 32-bit binaries CANNOT use KVM!
  ✗ kvm_no_compat_ioctl() returns -EINVAL

Example situation:
  $ uname -m
  some_arch_64
  
  $ file /bin/ls
  /bin/ls: ELF 32-bit LSB executable
  # 32-bit binaries work fine!
  
  $ ls -la
  # Works! Regular syscalls have compat support
  
  $ file my-qemu
  my-qemu: ELF 32-bit LSB executable
  
  $ ./my-qemu -enable-kvm ...
  # ERROR: KVM ioctls return -EINVAL
  # Because CONFIG_KVM_COMPAT=n
```

---

### Scenario 3: Both Disabled

```
CONFIG_COMPAT=n        ← No compat support at all
CONFIG_KVM_COMPAT=n    ← KVM compat also disabled

Pure 64-bit architecture:
  - Only 64-bit binaries can run
  - No 32-bit support anywhere
  - Obviously KVM compat also unavailable

What this means:
  ✗ 32-bit binaries won't even execute
  ✗ Kernel rejects them at exec time
  ✗ No compat syscalls
  ✗ No KVM compat

Example:
  $ uname -m
  pure_64bit_arch
  
  $ file my-32bit-program
  my-32bit-program: ELF 32-bit LSB executable
  
  $ ./my-32bit-program
  bash: ./my-32bit-program: cannot execute binary file: Exec format error
  # Rejected by kernel immediately
```

---

## Real-World Examples

### x86_64 (Both Enabled)

```bash
# Check kernel config
grep CONFIG_COMPAT /boot/config-$(uname -r)
# CONFIG_COMPAT=y

grep CONFIG_KVM_COMPAT /boot/config-$(uname -r)  
# CONFIG_KVM_COMPAT=y

# This means:
# ✓ Can run 32-bit x86 (i386) binaries
# ✓ 32-bit binaries can use KVM
```

**Why both are enabled:**
- x86_64 has long-standing 32-bit support (since forever)
- KVM compat was implemented early on
- Lots of 32-bit software still exists
- Backwards compatibility is important

---

### ARM64/aarch64 (Both Enabled)

```bash
# On ARM64 system
grep CONFIG_COMPAT /boot/config-$(uname -r)
# CONFIG_COMPAT=y  (can run aarch32/ARM 32-bit)

grep CONFIG_KVM_COMPAT /boot/config-$(uname -r)
# CONFIG_KVM_COMPAT=y  (KVM supports it too)

# This means:
# ✓ Can run 32-bit ARM binaries (aarch32)
# ✓ 32-bit binaries can use KVM
```

**Why both are enabled:**
- ARM64 supports running ARM 32-bit code natively (AARCH32 execution state)
- KVM compat was implemented
- Important for Android, embedded systems

---

### RISC-V 64-bit (Both Disabled, or COMPAT=y but KVM_COMPAT=n)

```bash
# On RISC-V system (hypothetical)
grep CONFIG_COMPAT /boot/config-$(uname -r)
# CONFIG_COMPAT=n  (or =y if RV32 support added)

grep CONFIG_KVM_COMPAT /boot/config-$(uname -r)
# CONFIG_KVM_COMPAT=n  (not implemented yet)

# This means:
# ✗ Might not support 32-bit RISC-V binaries at all
# ✗ Even if it does, KVM won't work with them
```

**Why:**
- RISC-V is newer
- RV64 (64-bit) is primary focus
- RV32 (32-bit) compat support might not be complete
- KVM compat for RISC-V not implemented yet (as of my knowledge)

---

## The Kernel Configuration Dependency

```makefile
# In arch/x86/kvm/Kconfig (example)

config KVM_COMPAT
    def_bool y
    depends on KVM && COMPAT
    #                  ^^^^^^
    #                  Must have general compat support first!

This means:
  - You can't have CONFIG_KVM_COMPAT=y without CONFIG_COMPAT=y
  - But you CAN have CONFIG_COMPAT=y without CONFIG_KVM_COMPAT=y
```

**Dependency chain:**
```
Architecture supports 64-bit mode?
  └─> yes
      └─> CONFIG_64BIT=y
          └─> Architecture supports 32-bit compat mode?
              ├─> yes: CONFIG_COMPAT=y
              │   └─> Did someone implement KVM compat handlers?
              │       ├─> yes: CONFIG_KVM_COMPAT=y (both enabled!)
              │       └─> no:  CONFIG_KVM_COMPAT=n (compat exists, but not for KVM)
              │
              └─> no: CONFIG_COMPAT=n
                  └─> CONFIG_KVM_COMPAT=n (can't enable without COMPAT)
```

---

## What Happens in Each Scenario

### Scenario 1: CONFIG_COMPAT=y, CONFIG_KVM_COMPAT=y

```c
// 32-bit process makes syscall
syscall(SYS_read, fd, buf, count);
→ Kernel has compat_sys_read() handler
→ Translates and works ✓

// 32-bit process opens /dev/kvm
open("/dev/kvm", O_RDWR);
→ Works ✓

// 32-bit process calls KVM ioctl
ioctl(kvm_fd, KVM_CREATE_VM, 0);
→ Kernel has kvm_vcpu_compat_ioctl() handler
→ Translates and works ✓

Result: Everything works!
```

---

### Scenario 2: CONFIG_COMPAT=y, CONFIG_KVM_COMPAT=n

```c
// 32-bit process makes syscall
syscall(SYS_read, fd, buf, count);
→ Kernel has compat_sys_read() handler
→ Works ✓

// 32-bit process opens /dev/kvm
open("/dev/kvm", O_RDWR);
→ Works ✓ (no special compat needed for open)

// 32-bit process calls KVM ioctl
ioctl(kvm_fd, KVM_CREATE_VM, 0);
→ Kernel routes to kvm_no_compat_ioctl()
→ Returns -EINVAL ✗

Result: Regular programs work, but KVM doesn't!
```

---

### Scenario 3: CONFIG_COMPAT=n, CONFIG_KVM_COMPAT=n

```c
// 32-bit process tries to execute
execve("/path/to/32bit/program", ...);
→ Kernel: "I don't understand 32-bit ELF format"
→ Returns -ENOEXEC ✗

// Process never runs at all!

Result: 32-bit binaries rejected immediately
```

---

## Why Would CONFIG_COMPAT=y but CONFIG_KVM_COMPAT=n?

**Reasons this might happen:**

### 1. **Work in Progress**

```
Architecture just added compat support:
  - General compat syscall handlers implemented ✓
  - KVM compat handlers not implemented yet ✗
  - Will be added in future kernel version
```

### 2. **Deemed Unnecessary**

```
Maintainers decided:
  - 64-bit KVM userspace is standard
  - Nobody uses 32-bit QEMU anymore
  - Not worth the maintenance burden
  - Disable KVM compat (save code size)
```

### 3. **Too Complex**

```
Some architectures:
  - General compat is straightforward
  - But KVM has too many arch-specific details
  - Too complex to maintain compat handlers
  - Leave it disabled
```

### 4. **Security Concerns**

```
Security-focused distribution might:
  - Allow 32-bit binaries for compatibility
  - But disable 32-bit KVM (reduce attack surface)
  - CONFIG_COMPAT=y, CONFIG_KVM_COMPAT=n
```

---

## How to Check Your System

```bash
# Check if general compat is enabled
zcat /proc/config.gz | grep CONFIG_COMPAT=
# or
grep CONFIG_COMPAT /boot/config-$(uname -r)

# Check if KVM compat is enabled
zcat /proc/config.gz | grep CONFIG_KVM_COMPAT=
# or
grep CONFIG_KVM_COMPAT /boot/config-$(uname -r)

# Test if 32-bit binaries work
file /bin/ls
# If it says "32-bit" and works, CONFIG_COMPAT=y

# Test if 32-bit can use KVM
# (if you have 32-bit QEMU)
./qemu-system-x86_64-32bit -enable-kvm ...
# If works: CONFIG_KVM_COMPAT=y
# If "Invalid argument": CONFIG_KVM_COMPAT=n
```

---

## Code That Checks This

```c
// In kernel source: virt/kvm/kvm_main.c

static const struct file_operations kvm_vcpu_fops = {
    .release        = kvm_vcpu_release,
    .unlocked_ioctl = kvm_vcpu_ioctl,    // Normal 64-bit path
    
#ifdef CONFIG_KVM_COMPAT
    .compat_ioctl   = kvm_vcpu_compat_ioctl,  // Real compat handler
#else
    // CONFIG_COMPAT might be 'y', but CONFIG_KVM_COMPAT is 'n'
    // So we still need to handle compat tasks trying to use KVM!
    .compat_ioctl   = kvm_no_compat_ioctl,    // Return -EINVAL
#endif
    
    .mmap           = kvm_vcpu_mmap,
    .llseek         = noop_llseek,
};

/*
 * If CONFIG_COMPAT=y but CONFIG_KVM_COMPAT=n:
 *   - 32-bit processes can run on the system
 *   - They can call ioctl() on KVM fds
 *   - Kernel routes to .compat_ioctl handler
 *   - We provide kvm_no_compat_ioctl()
 *   - Returns -EINVAL to reject them
 *
 * If CONFIG_COMPAT=n:
 *   - 32-bit processes can't even run
 *   - .compat_ioctl never gets called
 *   - But we still define it (defensive programming)
 */
```

---

## Summary: Answering Your Question

**Q: "On an arch without CONFIG_KVM_COMPAT, are there compat tasks but KVM doesn't support them?"**

**A: It depends on whether CONFIG_COMPAT is enabled!**

```
Case 1: CONFIG_COMPAT=y, CONFIG_KVM_COMPAT=n
────────────────────────────────────────────────
✓ Architecture supports compat tasks
✓ 32-bit binaries can run
✓ They can use most kernel features
✗ But 32-bit binaries CANNOT use KVM
✗ KVM ioctls return -EINVAL

Your understanding is CORRECT for this case!


Case 2: CONFIG_COMPAT=n, CONFIG_KVM_COMPAT=n
─────────────────────────────────────────────
✗ Architecture doesn't support compat tasks at all
✗ 32-bit binaries can't even run
✗ Obviously can't use KVM either

In this case, there are NO compat tasks period.
```

---

## The Key Insight

```
CONFIG_COMPAT = General 32-bit support in the kernel
                (for all subsystems: syscalls, filesystems, networking, etc.)

CONFIG_KVM_COMPAT = KVM-specific 32-bit support
                    (for KVM ioctls specifically)

They are SEPARATE!

You can have:
  - Both (x86_64, ARM64) ← 32-bit works everywhere
  - COMPAT only (some arches) ← 32-bit works, except KVM
  - Neither (pure 64-bit) ← No 32-bit support at all
```

**So yes, your understanding is spot-on! There can be architectures where compat tasks exist and work generally, but KVM specifically doesn't support them.**

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for kernel configuration and compatibility:**

- **[Kernel Configuration Documentation](https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html)** - Understanding CONFIG options and kernel build configuration
- **[KVM Kconfig Files](https://github.com/torvalds/linux/blob/master/arch/x86/kvm/Kconfig)** - Explore the actual Kconfig definitions for KVM options
