---
level: reference
estimated_time: 30 min
prerequisites: []
next_recommended:
  - 04_reference/setup_guides/02_external_drive_setup.md
tags: [setup, macos, kernel-development, case-sensitivity, howto]
---

# Linux Kernel on macOS: Case-Sensitivity Problem & Solutions

## The Problem

**macOS filesystems are case-insensitive by default:**

```
macOS (default):
  APFS: Case-insensitive (but case-preserving)
  HFS+: Case-insensitive

Linux kernel has files that differ ONLY in case:
  xt_MARK.h  vs  xt_mark.h
  xt_DSCP.c  vs  xt_dscp.c

macOS sees these as THE SAME FILE!
→ Git can only checkout one
→ Warning about collisions
```

**Why the kernel does this:**
- Legacy netfilter code has both uppercase (targets) and lowercase (matches)
- Linux filesystems (ext4, xfs, btrfs) are case-sensitive
- Never a problem on Linux

---

## Solution 1: Case-Sensitive APFS Volume (RECOMMENDED)

**Create a separate case-sensitive volume for kernel development:**

### Step 1: Create Case-Sensitive APFS Volume

```bash
# Option A: Create a sparse disk image (file-backed)
# ───────────────────────────────────────────────────
# Good for: Portability, can resize, can delete easily
# Size: Start with 50GB (sparse grows as needed)

hdiutil create -size 50g -type SPARSE -fs "Case-sensitive APFS" \
  -volname "LinuxKernel" ~/LinuxKernel.sparseimage

# This creates: ~/LinuxKernel.sparseimage
# Mounts as: /Volumes/LinuxKernel


# Option B: Create a new APFS volume on existing container
# ─────────────────────────────────────────────────────────
# Good for: Better performance, integrated with system
# Requires: Disk Utility or diskutil command

# 1. Open Disk Utility
# 2. Select your main disk
# 3. Click "+" to add APFS volume
# 4. Name: LinuxKernel
# 5. Format: APFS (Case-sensitive)
# 6. Size: Reserve 50GB or leave unreserved


# Option C: Using diskutil command line
# ──────────────────────────────────────

# List containers
diskutil list

# Add volume to container (find your container disk)
# Example: disk1 is your container
sudo diskutil apfs addVolume disk1 "Case-sensitive APFS" LinuxKernel

# This creates /Volumes/LinuxKernel
```

---

### Step 2: Mount and Use

```bash
# If using sparse image, mount it:
hdiutil attach ~/LinuxKernel.sparseimage

# Verify case-sensitivity:
cd /Volumes/LinuxKernel

# Test it works:
touch test.txt TEST.txt
ls -l
# Should show TWO files!

# Clean up test:
rm test.txt TEST.txt
```

---

### Step 3: Clone Kernel to Case-Sensitive Volume

```bash
cd /Volumes/LinuxKernel

# Clone kernel (this will work now!)
git clone https://github.com/torvalds/linux.git

# Or if you already have a broken clone:
cd /Volumes/LinuxKernel
git clone ~/path/to/existing/broken/repo linux
# OR just re-clone fresh
```

---

### Step 4: Auto-Mount on Login (Optional)

**For sparse image:**

```bash
# Create a script to mount on login
cat > ~/mount_kernel.sh << 'EOF'
#!/bin/bash
if [ ! -d "/Volumes/LinuxKernel" ]; then
    hdiutil attach ~/LinuxKernel.sparseimage
fi
EOF

chmod +x ~/mount_kernel.sh

# Add to Login Items:
# System Settings → Users & Groups → Login Items
# Click "+" and add ~/mount_kernel.sh
```

**For APFS volume:**
- Automatically mounts on boot (it's part of your disk)
- Just use `/Volumes/LinuxKernel` directly

---

### Advantages

```
✓ Native macOS solution
✓ Full kernel development possible
✓ git operations work correctly
✓ Can use macOS tools (VS Code, etc.)
✓ Good performance
✓ Can be deleted/resized easily (sparse image)

✗ Need to remember to work in /Volumes/LinuxKernel
✗ Sparse image needs mounting
```

---

## Solution 2: Sparse Checkout (LIMITED)

**Only checkout files you need (skip the problematic ones):**

```bash
# For READING the kernel (not full development)
# Skip netfilter collision files

cd ~/linux
git config core.sparseCheckout true

# Create sparse-checkout file
cat > .git/info/sparse-checkout << 'EOF'
# Include everything except problematic netfilter files
/*
!include/uapi/linux/netfilter/xt_CONNMARK.h
!include/uapi/linux/netfilter/xt_DSCP.h
!include/uapi/linux/netfilter/xt_MARK.h
!include/uapi/linux/netfilter/xt_RATEEST.h
!include/uapi/linux/netfilter/xt_TCPMSS.h
!include/uapi/linux/netfilter_ipv4/ipt_ECN.h
!include/uapi/linux/netfilter_ipv4/ipt_TTL.h
!include/uapi/linux/netfilter_ipv6/ip6t_HL.h
!net/netfilter/xt_DSCP.c
!net/netfilter/xt_HL.c
!net/netfilter/xt_RATEEST.c
!net/netfilter/xt_TCPMSS.c
!tools/memory-model/litmus-tests/Z6.0+pooncelock+poonceLock+pombonce.litmus
EOF

# Re-checkout with sparse rules
git checkout

# Verify
git status
# Should be clean now
```

---

### Advantages

```
✓ Works on regular macOS filesystem
✓ Quick fix

✗ INCOMPLETE kernel tree
✗ Can't build kernel (missing files)
✗ Can't work on netfilter code
✗ Not suitable for actual development
✗ Only good for READING code
```

---

## Solution 3: Linux VM (FULL DEVELOPMENT)

**Run Linux in a VM, develop there:**

### Option A: UTM (Recommended for Apple Silicon)

```bash
# Install UTM
brew install --cask utm

# Download Ubuntu ARM64 (for M1/M2/M3)
# https://ubuntu.com/download/server/arm

# Or use Fedora ARM
# https://getfedora.org/en/server/download/

# Create VM:
# - 4+ CPU cores
# - 8+ GB RAM
# - 100+ GB disk
# - Shared folder with macOS

# Inside VM:
sudo apt update
sudo apt install -y build-essential git libncurses-dev \
  flex bison libssl-dev libelf-dev

git clone https://github.com/torvalds/linux.git
cd linux

# Full kernel development possible!
make defconfig
make -j$(nproc)
```

---

### Option B: Docker (For Code Browsing)

```bash
# Install Docker Desktop for Mac
brew install --cask docker

# Run Ubuntu container with kernel source
docker run -it --rm \
  -v ~/kernel-dev:/work \
  ubuntu:22.04 bash

# Inside container:
apt update
apt install -y git build-essential

cd /work
git clone https://github.com/torvalds/linux.git

# Work in container, files visible on macOS via mount
```

---

### Option C: Multipass (Ubuntu VMs)

```bash
# Install Multipass
brew install --cask multipass

# Launch Ubuntu VM
multipass launch --name kernel-dev \
  --cpus 4 --mem 8G --disk 100G

# Enter VM
multipass shell kernel-dev

# Inside VM
git clone https://github.com/torvalds/linux.git
cd linux

# Can access from macOS via:
multipass mount ~/macos-share kernel-dev:/shared
```

---

### Advantages

```
✓ Full Linux environment
✓ Actually build and test kernel
✓ Can run KVM code (nested virt)
✓ Native case-sensitive filesystem

✗ Performance overhead (especially on Intel Macs)
✗ Need to run VM
✗ More resource usage
```

---

## Solution 4: Remote Development

**Develop on a remote Linux server:**

```bash
# Use VS Code Remote SSH
# 1. Install VS Code
brew install --cask visual-studio-code

# 2. Install Remote-SSH extension
code --install-extension ms-vscode-remote.remote-ssh

# 3. Connect to Linux server (AWS, DigitalOcean, etc.)
# Use Command Palette: "Remote-SSH: Connect to Host"

# 4. Open kernel folder on remote server
# All development happens remotely
# VS Code UI on macOS, execution on Linux

# Or use plain SSH + vim/emacs:
ssh yourserver
cd ~/linux
vim ...
```

---

### Advantages

```
✓ Real Linux environment
✓ Can compile and test
✓ MacBook is just a terminal
✓ Can use powerful remote hardware

✗ Requires internet connection
✗ Need access to Linux server
✗ Potential latency
```

---

## Solution 5: Browse on GitHub/Bootlin

**For just READING code:**

```
If you only want to read/study the kernel:

1. GitHub web interface:
   https://github.com/torvalds/linux
   
   - Search code
   - Browse files
   - View git history
   - No case-sensitivity issues

2. Bootlin Elixir (BEST for code reading):
   https://elixir.bootlin.com/linux/latest/source
   
   - Cross-referenced kernel source
   - Function definitions/references
   - Includes multiple versions
   - Fast search
   - No local checkout needed

3. LXR (Linux Cross Referencer):
   https://lxr.linux.no/
   
   - Similar to Elixir
   - Cross-referenced
```

---

### Advantages

```
✓ Zero setup
✓ Fast search
✓ Cross-referencing
✓ Multiple versions
✓ No disk space needed

✗ Can't edit/build
✗ Can't use local tools
✗ Need internet
```

---

## My Recommendation

**For your use case (learning KVM from source):**

```
Primary: Case-Sensitive APFS Volume (Solution 1)
─────────────────────────────────────────────────
✓ Best for macOS-native development
✓ Use your familiar tools (VS Code, etc.)
✓ Good enough for code reading/tracing
✓ Can build kernel if needed

Create sparse image:
  hdiutil create -size 50g -type SPARSE \
    -fs "Case-sensitive APFS" \
    -volname "LinuxKernel" ~/LinuxKernel.sparseimage
  
  hdiutil attach ~/LinuxKernel.sparseimage
  cd /Volumes/LinuxKernel
  git clone https://github.com/torvalds/linux.git


Secondary: Linux VM (Solution 3) for actual kernel hacking
───────────────────────────────────────────────────────────
✓ When you need to compile/test
✓ When working on KVM code specifically
✓ Can run nested virtualization

Use UTM (ARM) or VMware Fusion (Intel)


Tertiary: Bootlin Elixir for quick browsing
────────────────────────────────────────────
✓ Fast lookup
✓ Cross-references
✓ No setup

https://elixir.bootlin.com/linux/latest/source
```

---

## Quick Start: Get Going NOW

```bash
# Fastest solution to get you working:

# 1. Create case-sensitive volume (5 minutes)
hdiutil create -size 50g -type SPARSE \
  -fs "Case-sensitive APFS" \
  -volname "LinuxKernel" ~/LinuxKernel.sparseimage

hdiutil attach ~/LinuxKernel.sparseimage

# 2. Clone kernel (15 minutes, it's large!)
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git

# 3. Start exploring!
cd linux
git log arch/x86/kvm/ --oneline | head -20

# You're done! No more case-sensitivity errors!
```

---

## Debugging

**If sparse image won't mount:**

```bash
# Check what's mounted
mount | grep LinuxKernel

# Force unmount if stuck
hdiutil detach /Volumes/LinuxKernel -force

# Remount
hdiutil attach ~/LinuxKernel.sparseimage

# If corrupted, verify/repair
hdiutil verify ~/LinuxKernel.sparseimage
hdiutil resize -size 60g ~/LinuxKernel.sparseimage
```

**Verify case-sensitivity:**

```bash
cd /Volumes/LinuxKernel
touch test TEST
ls -l
# Should see TWO files

# Clean up
rm test TEST
```

---

## Summary

The case-sensitivity issue is a **filesystem limitation**, not a git problem.

**Solutions ranked:**
1. ⭐ **Case-sensitive APFS volume** - Best for macOS users
2. 🖥️ **Linux VM** - Best for serious kernel development
3. 🌐 **Bootlin Elixir** - Best for reading code only
4. ☁️ **Remote Linux server** - Best if you have one
5. 📦 **Docker/Multipass** - Alternative to full VM
6. ⚠️ **Sparse checkout** - Limited, only for browsing

**For learning KVM source code: Use case-sensitive APFS volume!**

You can browse code, use grep/ripgrep, use VS Code, and even build the kernel if needed. It's the sweet spot for your use case.
