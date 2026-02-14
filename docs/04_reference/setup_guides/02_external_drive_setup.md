---
level: reference
estimated_time: 20 min
prerequisites: []
next_recommended:
  - 04_reference/learning_resources/01_learning_kvm_guide.md
tags: [setup, macos, kernel-development, storage, howto]
---

# Linux Kernel on External Drive (macOS)

## Option 1: Format Entire External Drive (SIMPLEST)

**If you can dedicate the whole external drive to kernel work:**

```bash
# 1. Find your external drive
diskutil list

# Look for your external drive, something like:
# /dev/disk2 (external, physical):
#    #:                       TYPE NAME                    SIZE
#    0:      GUID_partition_scheme                        *1.0 TB
#    1:                        EFI EFI                     209.7 MB
#    2:                 Apple_APFS Container disk3         999.9 GB

# Note the disk identifier: disk2 (or whatever yours is)


# 2. Erase and format as case-sensitive APFS
# WARNING: This ERASES everything on the drive!
diskutil eraseDisk APFS LinuxKernel disk2

# Where:
#   APFS = filesystem type (case-sensitive by default when erasing)
#   LinuxKernel = volume name
#   disk2 = your external drive (CHANGE THIS!)


# 3. Wait for format to complete (~30 seconds)


# 4. Clone kernel
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git

# Done! Drive will auto-mount when plugged in
```

---

## Option 2: Add Case-Sensitive Volume (Keep Existing Data)

**If your external drive has data you want to keep:**

```bash
# 1. Find your external drive's APFS container
diskutil list

# Example output:
# /dev/disk2 (external, physical):
#    0: GUID_partition_scheme               *1.0 TB     disk2
#    1: EFI EFI                              209.7 MB   disk2s1
#    2: Apple_APFS Container disk3           999.9 GB   disk2s2

# Note the Container disk: disk3


# 2. Add a case-sensitive volume to the container
diskutil apfs addVolume disk3 "Case-sensitive APFS" LinuxKernel

# Where:
#   disk3 = the container disk (from step 1)
#   "Case-sensitive APFS" = filesystem type
#   LinuxKernel = volume name


# 3. Clone kernel
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git

# Done! Both volumes (old + new) exist on same drive
```

---

## Option 3: Partition External Drive

**If you want to split the drive between case-sensitive and regular:**

```bash
# 1. Find your drive
diskutil list

# Your external drive: disk2


# 2. Partition the drive
# Example: 500GB case-sensitive + 500GB regular (on 1TB drive)
diskutil partitionDisk disk2 2 GPT \
  "Case-sensitive APFS" LinuxKernel 500GB \
  APFS Data 0

# Where:
#   disk2 = your drive
#   2 = number of partitions
#   GPT = partition scheme
#   First partition: Case-sensitive APFS, named LinuxKernel, 500GB
#   Second partition: Regular APFS, named Data, rest of space (0 = remaining)


# 3. Verify
diskutil list disk2

# Should see:
#   disk2s1: LinuxKernel (Case-sensitive)
#   disk2s2: Data (Regular APFS)


# 4. Clone kernel
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git
```

---

## Key Differences from Internal Drive

### Advantages ✓

```
✓ Can format entire drive as case-sensitive
✓ No sparse image needed
✓ Better performance (no image overhead)
✓ Portable (unplug and use on another Mac)
✓ Easy to wipe and start over
✓ Auto-mounts when plugged in
✓ Simpler setup
```

### Considerations

```
⚠ Must remember to plug in drive
⚠ USB/Thunderbolt speed vs internal SSD
⚠ Can't work if drive not connected
⚠ Physical device can fail/disconnect
```

---

## Quick Decision Guide

### Scenario 1: Dedicated External SSD for Kernel Work
```bash
# Fastest setup - just erase and format
diskutil list                    # Find disk number
diskutil eraseDisk APFS LinuxKernel disk2
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git
```

### Scenario 2: External Drive with Other Files
```bash
# Add volume to existing container
diskutil list                    # Find container number (disk3)
diskutil apfs addVolume disk3 "Case-sensitive APFS" LinuxKernel
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git
```

### Scenario 3: Share Drive with Other Uses
```bash
# Partition: half kernel, half data
diskutil partitionDisk disk2 2 GPT \
  "Case-sensitive APFS" LinuxKernel 250GB \
  APFS Data 0
cd /Volumes/LinuxKernel
git clone https://github.com/torvalds/linux.git
```

---

## Verification Steps

```bash
# 1. Verify case-sensitivity
cd /Volumes/LinuxKernel
touch test.txt TEST.txt
ls -l
# Should show TWO files!
rm test.txt TEST.txt

# 2. Verify it's your external drive
diskutil info /Volumes/LinuxKernel | grep "Device Node"
# Should show disk2 or disk3 (not disk1 which is internal)

# 3. Test git works
cd /Volumes/LinuxKernel/linux
git status
# Should be clean, no warnings!
```

---

## Unmount/Eject

```bash
# Safely eject when done
diskutil eject /Volumes/LinuxKernel

# Or use Finder:
# Right-click drive → Eject
```

---

## Auto-Mount Settings

**External drives auto-mount by default on macOS, but if you want to ensure it:**

```bash
# Check mount status
diskutil info /Volumes/LinuxKernel

# If it doesn't auto-mount, you can manually mount:
diskutil mount LinuxKernel

# Or mount by device:
diskutil mount disk2s1
```

---

## Performance Tips

### Use SSD External Drive
```
✓ NVMe Thunderbolt 3/4 enclosure (fastest)
  Example: Samsung X5, OWC Envoy Pro
  Speed: ~2800 MB/s

✓ USB-C SSD (good)
  Example: Samsung T7, SanDisk Extreme Pro
  Speed: ~1000 MB/s

✗ USB 3.0 HDD (slow)
  Speed: ~150 MB/s
  Too slow for kernel work
```

### Optimize for Git
```bash
# In your kernel repo
cd /Volumes/LinuxKernel/linux

# Enable filesystem cache
git config core.preloadindex true
git config core.fscache true

# Use faster hash
git config feature.manyFiles true
```

---

## Troubleshooting

### Drive Not Showing Up

```bash
# List all disks
diskutil list

# Mount manually
diskutil mount disk2s1

# Or by name
diskutil mount LinuxKernel
```

### "Resource Busy" Error

```bash
# Something is using the drive
lsof | grep /Volumes/LinuxKernel

# Force unmount
sudo diskutil unmount force /Volumes/LinuxKernel

# Then remount
diskutil mount LinuxKernel
```

### Wrong Filesystem Type

```bash
# Check what you actually created
diskutil info /Volumes/LinuxKernel | grep "File System Personality"

# Should say: "Case-sensitive APFS"
# If it says "APFS" (without case-sensitive), you need to reformat
```

### Slow Performance

```bash
# Check connection type
system_profiler SPUSBDataType | grep -A 10 "LinuxKernel"
# Or for Thunderbolt:
system_profiler SPThunderboltDataType

# Ensure USB 3.0+ or Thunderbolt, not USB 2.0
```

---

## Complete Example Session

```bash
# Plug in external SSD
# (macOS automatically detects)

# Find it
diskutil list
# Output shows: /dev/disk2 (external)

# Format it (WARNING: ERASES DRIVE!)
diskutil eraseDisk APFS LinuxKernel disk2
# Takes ~30 seconds

# Verify case-sensitivity
cd /Volumes/LinuxKernel
touch test TEST
ls -l
# Shows: TEST  test (two files!)
rm test TEST

# Clone kernel
git clone https://github.com/torvalds/linux.git
# Takes ~10-15 minutes

# Start working!
cd linux
code .
# or
vim arch/x86/kvm/vmx/vmx.c

# When done for the day:
# Eject in Finder or:
diskutil eject /Volumes/LinuxKernel

# Next time: just plug in drive
# Auto-mounts to /Volumes/LinuxKernel
```

---

## Comparison: External vs Internal Sparse Image

```
┌─────────────────────┬──────────────────┬────────────────┐
│ Feature             │ External Drive   │ Sparse Image   │
├─────────────────────┼──────────────────┼────────────────┤
│ Setup complexity    │ Very easy        │ Easy           │
│ Performance         │ SSD: Excellent   │ Very good      │
│                     │ HDD: Poor        │                │
│ Portability         │ Excellent        │ File-based     │
│ Auto-mount          │ Yes              │ Manual/script  │
│ Format entire drive │ Yes              │ N/A            │
│ Keep other data     │ Add volume       │ Always         │
│ Disk space          │ Fixed            │ Grows as needed│
│ Can work offline    │ No (need drive)  │ Yes            │
│ Use on other Mac    │ Plug and play    │ Copy file      │
└─────────────────────┴──────────────────┴────────────────┘
```

---

## My Recommendation for External Drive

```bash
# If drive is dedicated to kernel work:
# ═══════════════════════════════════════
diskutil eraseDisk APFS LinuxKernel disk2

# Simplest, fastest, no complexity


# If drive has other files you need:
# ═══════════════════════════════════
diskutil apfs addVolume disk3 "Case-sensitive APFS" LinuxKernel

# Keeps existing data, adds kernel volume


# If using USB HDD (slow):
# ════════════════════════
# Consider internal sparse image instead
# Better performance than slow USB drive
```

**Bottom line: External SSD is actually BETTER than sparse image if you have one! Simpler setup, no mounting hassle, portable, and excellent performance with Thunderbolt/USB-C SSD.**
