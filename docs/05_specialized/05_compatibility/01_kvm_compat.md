---
level: specialized
estimated_time: 70 min
prerequisites:
  - 02_intermediate/03_complete_virtualization/01_evolution_complete.md
next_recommended:
  - 05_specialized/05_compatibility/02_compat_vs_kvm_compat.md
tags: [virtualization, kvm, compatibility, 32-bit, 64-bit, ioctl]
---

# KVM Compat Infrastructure Explained

## What is a "Compat" Task?

**A compat task = 32-bit process running on a 64-bit kernel**

```
┌─────────────────────────────────────────────┐
│        64-bit Linux Kernel                  │
│                                             │
│  ┌──────────────┐      ┌──────────────┐   │
│  │   64-bit     │      │   32-bit     │   │
│  │   Process    │      │   Process    │   │
│  │   (native)   │      │  (compat!)   │   │
│  └──────────────┘      └──────────────┘   │
│         │                      │           │
│         │                      │           │
│         ↓                      ↓           │
│    Normal path          Compat path        │
└─────────────────────────────────────────────┘

Examples:
  - Running old 32-bit QEMU on 64-bit Linux
  - 32-bit userspace with 64-bit kernel
  - x86 (i386) binary on x86_64 kernel
  - ARM 32-bit (aarch32) on ARM 64-bit (aarch64)
```

---

## Why Compat Infrastructure Exists

### Problem 1: Different Pointer Sizes

```c
32-bit process:
───────────────
void *ptr;           // 4 bytes
unsigned long addr;  // 4 bytes

struct kvm_regs {
    void *data;      // 4 bytes
    unsigned long x; // 4 bytes
};
// Total: 8 bytes


64-bit kernel:
──────────────
void *ptr;           // 8 bytes!
unsigned long addr;  // 8 bytes!

struct kvm_regs {
    void *data;      // 8 bytes!
    unsigned long x; // 8 bytes!
};
// Total: 16 bytes!

Same structure, different sizes!
32-bit process passes 8 bytes
64-bit kernel expects 16 bytes
→ CORRUPTION!
```

---

### Problem 2: Structure Padding/Alignment

```c
32-bit layout:
──────────────
struct example {
    int a;           // offset 0, 4 bytes
    void *ptr;       // offset 4, 4 bytes (32-bit pointer)
    char b;          // offset 8, 1 byte
    // padding: 3 bytes
};
// Total: 12 bytes


64-bit layout:
──────────────
struct example {
    int a;           // offset 0, 4 bytes
    // padding: 4 bytes (alignment for 8-byte pointer)
    void *ptr;       // offset 8, 8 bytes (64-bit pointer)
    char b;          // offset 16, 1 byte
    // padding: 7 bytes
};
// Total: 24 bytes!

Same struct, different layout!
Fields at different offsets!
```

---

### Problem 3: ioctl Numbers

```c
ioctl numbers encode structure size:

#define _IOC(dir,type,nr,size) \
    (((dir)  << _IOC_DIRSHIFT) | \
     ((type) << _IOC_TYPESHIFT) | \
     ((nr)   << _IOC_NRSHIFT) | \
     ((size) << _IOC_SIZESHIFT))

32-bit process:
───────────────
struct kvm_regs regs;  // 8 bytes
ioctl_num = _IOR('K', 0x81, sizeof(struct kvm_regs));
// Encodes size = 8

64-bit kernel:
──────────────
struct kvm_regs regs;  // 16 bytes
Expected size = 16

ioctl_num from 32-bit != ioctl_num kernel expects!
→ ioctl not recognized!
→ Returns -ENOTTY
```

---

## The KVM Compat Code Explained

### Location in Source

```c
// File: virt/kvm/kvm_main.c (or similar)

#ifdef CONFIG_KVM_COMPAT
static long kvm_vcpu_compat_ioctl(struct file *file, unsigned int ioctl,
                                  unsigned long arg);
#define KVM_COMPAT(c)	.compat_ioctl	= (c)
#else
/*
 * For architectures that don't implement a compat infrastructure,
 * adopt a double line of defense:
 * - Prevent a compat task from opening /dev/kvm
 * - If the open has been done by a 64bit task, and the KVM fd
 *   passed to a compat task, let the ioctls fail.
 */
static long kvm_no_compat_ioctl(struct file *file, unsigned int ioctl,
                                unsigned long arg) { return -EINVAL; }
#endif
```

---

### Case 1: Architecture WITH Compat Support

```c
#ifdef CONFIG_KVM_COMPAT
static long kvm_vcpu_compat_ioctl(struct file *file, unsigned int ioctl,
                                  unsigned long arg);
#define KVM_COMPAT(c)	.compat_ioctl	= (c)
```

**What this means:**

```
Architectures that SUPPORT 32-bit compat:
  - x86_64 (can run i386 binaries)
  - ARM64/aarch64 (can run ARM32/aarch32 binaries)
  - PowerPC 64-bit (can run 32-bit)
  - s390x (can run s390)

CONFIG_KVM_COMPAT is defined for these.

What happens:
  1. 32-bit QEMU opens /dev/kvm → Allowed!
  2. 32-bit QEMU calls ioctl()
  3. Kernel sees it's a compat task
  4. Routes to kvm_vcpu_compat_ioctl() instead of normal ioctl
  5. compat_ioctl translates 32-bit → 64-bit
  6. Calls real 64-bit handler
  7. Translates result back 64-bit → 32-bit
  8. Returns to 32-bit process

Flow:
  32-bit process
       ↓
  ioctl(fd, cmd, arg)  // 32-bit arg
       ↓
  syscall entry (kernel)
       ↓
  Kernel detects: "This is compat task"
       ↓
  Calls .compat_ioctl handler
       ↓
  kvm_vcpu_compat_ioctl()
       ↓
  Translate 32-bit struct → 64-bit struct
       ↓
  Call real kvm_vcpu_ioctl() with 64-bit data
       ↓
  Translate result back
       ↓
  Return to 32-bit process
```

---

### Case 2: Architecture WITHOUT Compat Support

```c
#else
/*
 * For architectures that don't implement a compat infrastructure,
 * adopt a double line of defense:
 * - Prevent a compat task from opening /dev/kvm
 * - If the open has been done by a 64bit task, and the KVM fd
 *   passed to a compat task, let the ioctls fail.
 */
static long kvm_no_compat_ioctl(struct file *file, unsigned int ioctl,
                                unsigned long arg) { return -EINVAL; }
#endif
```

**What this means:**

```
Architectures that DON'T support 32-bit compat:
  - Pure 64-bit only architectures
  - Or architectures where compat wasn't implemented yet

CONFIG_KVM_COMPAT is NOT defined.

What happens:
  1. 32-bit process tries to open /dev/kvm
     → open() succeeds (can't prevent at open time reliably)
  
  2. 32-bit process calls ioctl()
     → Routed to kvm_no_compat_ioctl()
     → Returns -EINVAL (always fails!)
  
  3. OR: 64-bit process opens /dev/kvm, passes fd to 32-bit process
     → 32-bit process calls ioctl()
     → kvm_no_compat_ioctl() returns -EINVAL

"Double line of defense":
  - Try to prevent compat tasks from opening /dev/kvm
  - If that fails, make all ioctls fail with -EINVAL

This prevents corruption from 32-bit processes trying to
use KVM on architectures where it's not supported.
```

---

## How the File Operations Table Uses This

```c
// File: virt/kvm/kvm_main.c

static struct file_operations kvm_vcpu_fops = {
    .release        = kvm_vcpu_release,
    .unlocked_ioctl = kvm_vcpu_ioctl,
    
#ifdef CONFIG_KVM_COMPAT
    .compat_ioctl   = kvm_vcpu_compat_ioctl,  // Use real compat handler
#else
    .compat_ioctl   = kvm_no_compat_ioctl,    // Always return -EINVAL
#endif
    
    .mmap           = kvm_vcpu_mmap,
    .llseek         = noop_llseek,
};

How kernel uses this:
─────────────────────
When userspace calls ioctl(fd, cmd, arg):

1. Kernel checks: "Is this a compat task?"
   
2. If YES (32-bit process):
   - Look for .compat_ioctl in file_operations
   - If found: call it
   - If not found: try to handle automatically (limited)

3. If NO (64-bit process):
   - Call .unlocked_ioctl (normal path)
```

---

## Example: x86_64 Compat ioctl Translation

```c
// Simplified example of what kvm_vcpu_compat_ioctl does

static long kvm_vcpu_compat_ioctl(struct file *file, unsigned int ioctl,
                                  unsigned long arg)
{
    struct kvm_vcpu *vcpu = file->private_data;
    void __user *argp = compat_ptr(arg);  // Convert 32-bit pointer
    
    // Check which ioctl
    switch (ioctl) {
    
    case KVM_GET_REGS: {
        // 32-bit version of struct
        struct kvm_regs_32 regs32;
        // 64-bit version
        struct kvm_regs regs64;
        
        // Get data from 32-bit process
        if (copy_from_user(&regs32, argp, sizeof(regs32)))
            return -EFAULT;
        
        // Convert 32-bit → 64-bit
        regs64.rax = regs32.eax;
        regs64.rbx = regs32.ebx;
        // ... etc for all registers
        
        // Call real 64-bit handler
        int ret = kvm_arch_vcpu_ioctl_get_regs(vcpu, &regs64);
        
        // Convert result back 64-bit → 32-bit
        regs32.eax = regs64.rax;
        regs32.ebx = regs64.rbx;
        // ... etc
        
        // Return to 32-bit process
        if (copy_to_user(argp, &regs32, sizeof(regs32)))
            return -EFAULT;
        
        return ret;
    }
    
    case KVM_RUN:
        // This one doesn't need translation (no struct)
        return kvm_vcpu_ioctl(file, ioctl, arg);
    
    default:
        return -EINVAL;
    }
}
```

---

## Why "Double Line of Defense"?

```c
/*
 * For architectures that don't implement a compat infrastructure,
 * adopt a double line of defense:
 * - Prevent a compat task from opening /dev/kvm
 * - If the open has been done by a 64bit task, and the KVM fd
 *   passed to a compat task, let the ioctls fail.
 */
```

**The two defenses:**

```
Defense 1: Prevent compat tasks from opening /dev/kvm
──────────────────────────────────────────────────────
Problem: Not always possible to detect at open() time

In kvm_dev_ioctl_create_vm() or kvm_dev_ioctl():
    if (is_compat_task())
        return -EINVAL;

This catches most cases.


Defense 2: Fail all ioctls from compat tasks
─────────────────────────────────────────────
Scenario: 64-bit process opens /dev/kvm, passes fd to 32-bit process

Example:
    // 64-bit parent process
    int kvm_fd = open("/dev/kvm", O_RDWR);  // Success!
    
    fork();
    exec("/path/to/32bit/program");  // Child is 32-bit
    
    // 32-bit child inherits fd
    ioctl(kvm_fd, KVM_CREATE_VM, 0);  // Try to use it
    // → kvm_no_compat_ioctl() → -EINVAL
    
Or via Unix domain socket:
    64-bit process: send fd over socket
    32-bit process: receive fd, try to use it
    → Fails with -EINVAL

This catches the edge cases!
```

---

## Real-World Example

### Scenario: Running 32-bit QEMU on 64-bit Kernel

**On x86_64 with CONFIG_KVM_COMPAT:**

```c
// 32-bit QEMU (i386 binary)
int kvm_fd = open("/dev/kvm", O_RDWR);
// → Success! Kernel allows it

int vm_fd = ioctl(kvm_fd, KVM_CREATE_VM, 0);
// → Kernel detects compat task
// → Calls kvm_vcpu_compat_ioctl()
// → Translates and works correctly
// → Returns vm_fd

// Continue using KVM normally
// All ioctls go through compat layer
// Everything works!
```

**On architecture without CONFIG_KVM_COMPAT:**

```c
// 32-bit process
int kvm_fd = open("/dev/kvm", O_RDWR);
// → Success (can't always prevent)

int vm_fd = ioctl(kvm_fd, KVM_CREATE_VM, 0);
// → Kernel detects compat task
// → Calls kvm_no_compat_ioctl()
// → Returns -EINVAL immediately
// → Error: "Invalid argument"

// Process gets error, can't use KVM
// Prevents corruption!
```

---

## How to Check if You're a Compat Task

```c
// In kernel code
#include <linux/compat.h>

if (is_compat_task()) {
    printk("This is a 32-bit process on 64-bit kernel\n");
}

// In userspace (check your own binary)
#include <stdio.h>

int main() {
    printf("sizeof(void*) = %zu\n", sizeof(void*));
    printf("sizeof(long) = %zu\n", sizeof(long));
    
    if (sizeof(void*) == 4)
        printf("I am 32-bit\n");
    else if (sizeof(void*) == 8)
        printf("I am 64-bit\n");
    
    return 0;
}
```

---

## Which Architectures Have KVM Compat?

```c
CONFIG_KVM_COMPAT is defined when:
──────────────────────────────────

✓ x86_64 (supports i386/x86)
  - Can run 32-bit x86 binaries
  - Most common case

✓ ARM64/aarch64 (supports aarch32/ARM)
  - Can run 32-bit ARM binaries
  - Used in many embedded/mobile

✓ PowerPC 64-bit (supports 32-bit PPC)
  - Server/embedded

✓ s390x (supports s390)
  - IBM mainframes

✗ RISC-V (no compat yet)
  - Pure 64-bit

✗ Some other pure 64-bit architectures
```

---

## KVM Structures That Need Compat Handling

```c
Examples of structures that differ:

struct kvm_regs {
    __u64 rax, rbx, rcx, ...;  // Always 64-bit values
    // This one is actually OK (fixed size)
};

struct kvm_run {
    // Large structure with various fields
    // Some pointer-sized fields
    // Needs careful handling
};

struct kvm_userspace_memory_region {
    __u32 slot;
    __u32 flags;
    __u64 guest_phys_addr;  // Always 64-bit (GPA)
    __u64 memory_size;      // Always 64-bit
    __u64 userspace_addr;   // THIS is the problem!
                            // 32-bit: 4 bytes
                            // 64-bit: 8 bytes
};

The userspace_addr needs translation:
  32-bit: userspace_addr is 32-bit pointer
  64-bit: userspace_addr is 64-bit pointer
  
Compat layer handles this with compat_ptr().
```

---

## Summary

```
Compat Task:
  32-bit process running on 64-bit kernel

Why it's complex:
  - Different pointer sizes (4 vs 8 bytes)
  - Different struct layouts
  - Different ioctl numbers
  
KVM's approach:
  
  If CONFIG_KVM_COMPAT defined (x86_64, ARM64, etc.):
    ✓ Allow 32-bit processes
    ✓ Translate all ioctls via kvm_vcpu_compat_ioctl()
    ✓ Full functionality
  
  If CONFIG_KVM_COMPAT not defined:
    ✗ Reject compat tasks (double defense)
    ✗ All ioctls return -EINVAL
    ✗ Prevents corruption

The code you saw:
  #ifdef CONFIG_KVM_COMPAT
    → Use real compat handler
  #else
    → Return -EINVAL always (safety)
```

---

## Finding This in the Source

```bash
# In Linux kernel source tree
cd linux/

# Find the compat infrastructure
grep -r "kvm_vcpu_compat_ioctl" virt/kvm/
grep -r "CONFIG_KVM_COMPAT" arch/x86/kvm/

# Look at file operations
vim virt/kvm/kvm_main.c
# Search for: kvm_vcpu_fops

# x86-specific compat handling
vim arch/x86/kvm/x86.c
# Search for: compat_ioctl

# Generic compat infrastructure
vim include/linux/compat.h
vim kernel/compat.c
```

This compat infrastructure is essential for backwards compatibility - allowing old 32-bit virtualization tools to work on modern 64-bit systems!
