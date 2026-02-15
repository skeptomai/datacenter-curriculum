---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 04_containers/05_security/01_image_security.md
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
next_recommended:
  - 04_containers/05_security/03_pod_security.md
tags: [security, runtime, seccomp, apparmor, selinux, capabilities, falco]
---

# Runtime Security: Securing Running Containers

## Learning Objectives

After reading this document, you will understand:
- Linux security modules (seccomp, AppArmor, SELinux (Security-Enhanced Linux))
- Capabilities and privilege escalation prevention
- Runtime security monitoring with Falco
- Container escape techniques and defenses
- Principle of least privilege for containers
- Runtime vs build-time security

## Prerequisites

Before reading this, you should understand:
- Container primitives (namespaces, cgroups)
- Image security basics
- Linux permissions and syscalls

---

## 1. Runtime Security Layers

### Defense in Depth

```
┌──────────────────────────────────────────┐
│ Application Code                         │ ← Your code
├──────────────────────────────────────────┤
│ Container Runtime Security               │
│  - readOnlyRootFilesystem                │
│  - runAsNonRoot                          │
│  - Capabilities dropped                  │
├──────────────────────────────────────────┤
│ Linux Security Modules                   │
│  - seccomp (syscall filtering)           │
│  - AppArmor / SELinux (MAC - Mandatory Access Control) │
├──────────────────────────────────────────┤
│ Kernel Namespaces                        │
│  - PID, NET, MNT, UTS, IPC, USER         │
├──────────────────────────────────────────┤
│ Runtime Monitoring                       │
│  - Falco (anomaly detection)             │
│  - Audit logs                            │
└──────────────────────────────────────────┘
```

**Each layer provides different protection**:
- **seccomp (Secure Computing Mode)**: Blocks dangerous syscalls
- **AppArmor/SELinux**: Restricts file access
- **Capabilities**: Limits privileged operations
- **Namespaces**: Isolation
- **Monitoring**: Detects attacks

---

## 2. seccomp (Secure Computing Mode)

### What is seccomp?

**seccomp** filters system calls (syscalls) a process can make.

```
Container process calls: execve("/bin/sh")
  ↓
Kernel checks seccomp profile
  ↓
If allowed: Execute syscall
If blocked: Return error (EPERM) or kill process
```

**Why it matters**:
```
Linux kernel has 300+ syscalls
  - Most apps use <100 syscalls
  - Remaining 200+ include dangerous ones:
    - ptrace (debugging other processes)
    - reboot (reboot system)
    - mount (mount filesystems)
    - bpf (load eBPF programs)

Block unused syscalls → Reduce attack surface
```

### Docker Default seccomp Profile

**Docker blocks ~50 dangerous syscalls by default**:
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": ["accept", "bind", "connect", ...],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["reboot", "mount", "ptrace", "bpf", ...],
      "action": "SCMP_ACT_ERRNO"
    }
  ]
}
```

**Effect**:
```bash
# In container
reboot
# Error: Operation not permitted

mount /dev/sda1 /mnt
# Error: Operation not permitted
```

### Custom seccomp Profile

**Create profile** (block all except read/write/exit):
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": ["read", "write", "exit", "exit_group"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

**Apply in Kubernetes**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    seccompProfile:
      type: Localhost
      localhostProfile: profiles/restricted.json

  containers:
  - name: app
    image: myapp:1.0
```

**Built-in profiles**:
```yaml
seccompProfile:
  type: RuntimeDefault  # Use container runtime's default
  # Or:
  type: Unconfined      # No seccomp (dangerous!)
```

### Generating seccomp Profiles

**Problem**: How do you know which syscalls your app needs?

**Solution**: Record syscalls during normal operation.

**Using `strace`**:
```bash
# Run app under strace
strace -c -f -S name ./myapp 2>&1 | grep % | awk '{print $NF}' > syscalls.txt

# Generate seccomp profile
cat > seccomp.json <<EOF
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": $(cat syscalls.txt | jq -R . | jq -s .),
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
EOF
```

**Using `oci-seccomp-bpf-hook`**:
```bash
# Run container in "training mode"
docker run --security-opt seccomp=unconfined \
  --annotation io.containers.trace-syscall=of:/tmp/profile.json \
  myapp:1.0

# Generated profile saved to /tmp/profile.json
```

---

## 3. AppArmor

**AppArmor** (Application Armor): Mandatory Access Control (MAC) for file access.

### How AppArmor Works

```
Process tries: open("/etc/shadow", O_RDONLY)
  ↓
Kernel checks AppArmor profile
  ↓
Profile says: "/etc/shadow" → DENY for this process
  ↓
Return error: Permission denied
```

**AppArmor profiles** specify:
- Which files can be read
- Which files can be written
- Which files can be executed
- Network access

### Docker Default AppArmor Profile

**Location**: `/etc/apparmor.d/docker-default`

**Example restrictions**:
```
# Deny access to /proc/sys/*
deny /proc/sys/** rwklx,

# Deny mount operations
deny mount,

# Deny access to /sys/kernel/security
deny /sys/kernel/security/** rwklx,

# Allow read to most of /proc
/proc/** r,
```

### Custom AppArmor Profile

**Create profile**:
```bash
cat > /etc/apparmor.d/myapp-profile <<EOF
#include <tunables/global>

profile myapp-profile flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  # Allow network
  network inet tcp,
  network inet udp,

  # Allow reading app files
  /app/** r,

  # Allow writing to /tmp only
  /tmp/** rw,

  # Deny everything else
  /** deny,
}
EOF

# Load profile
sudo apparmor_parser -r /etc/apparmor.d/myapp-profile
```

**Apply in Kubernetes**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apparmor-pod
  annotations:
    container.apparmor.security.beta.kubernetes.io/app: localhost/myapp-profile
spec:
  containers:
  - name: app
    image: myapp:1.0
```

**Test**:
```bash
kubectl exec -it apparmor-pod -- /bin/sh

# Inside container
cat /app/config.txt   # ✓ Allowed
echo "test" > /tmp/f  # ✓ Allowed
cat /etc/shadow       # ✗ Permission denied
```

---

## 4. SELinux

**SELinux** (Security-Enhanced Linux): More powerful than AppArmor, used on RHEL/CentOS.

### SELinux Modes

```
Disabled:  No SELinux enforcement
Permissive: Log violations, don't block
Enforcing: Block violations
```

**Check mode**:
```bash
getenforce
# Output: Enforcing
```

### SELinux Contexts

**Every file/process has a security context**:
```bash
ls -Z /var/lib/
drwxr-xr-x. root root system_u:object_r:var_lib_t:s0 ...
```

**Format**: `user:role:type:level`
- **type**: Most important (e.g., `container_t` for containers)

### Container SELinux Types

**Default context for containers**:
```
Process: container_t
Files: container_file_t
```

**SELinux policy** allows:
- `container_t` can read/write `container_file_t`
- `container_t` CANNOT read/write `admin_home_t` (admin files)

**Apply SELinux label in Kubernetes**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: selinux-pod
spec:
  securityContext:
    seLinuxOptions:
      level: "s0:c123,c456"  # Multi-Category Security (MCS)

  containers:
  - name: app
    image: myapp:1.0
```

**MCS labels** isolate containers from each other:
```
Pod A: s0:c123,c456
Pod B: s0:c789,c012

Pod A cannot access Pod B's files (different MCS labels)
```

---

## 5. Linux Capabilities

**Capabilities** break down root privileges into granular permissions.

### Root Capabilities Problem

**Traditional UNIX**: Either root (all permissions) or non-root (limited).

```
Root user can:
  - Bind to port 80
  - Change file ownership (chown)
  - Load kernel modules
  - Reboot system
  - ... 40+ other dangerous operations
```

**Problem**: Web server needs port 80, but doesn't need kernel module loading!

### Capabilities Solution

**Linux divides root privileges** into ~40 capabilities:

| Capability            | Allows                                    |
|-----------------------|-------------------------------------------|
| CAP_NET_BIND_SERVICE  | Bind to ports < 1024                      |
| CAP_NET_RAW           | Use raw sockets (ping, packet sniffing)   |
| CAP_SYS_ADMIN         | Mount filesystems, many admin operations  |
| CAP_SYS_MODULE        | Load kernel modules                       |
| CAP_SYS_TIME          | Set system clock                          |
| CAP_CHOWN             | Change file ownership                     |
| CAP_DAC_OVERRIDE      | Bypass file permission checks             |
| CAP_KILL              | Send signals to any process               |

**Docker default capabilities** (container gets these):
```
CAP_CHOWN
CAP_DAC_OVERRIDE
CAP_FOWNER
CAP_FSETID
CAP_KILL
CAP_NET_BIND_SERVICE
CAP_NET_RAW
CAP_SETGID
CAP_SETUID
CAP_SYS_CHROOT
... (~14 total)
```

### Dropping Capabilities

**Best practice**: Drop all, add only what's needed.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      capabilities:
        drop:
        - ALL  # Drop all capabilities
        add:
        - NET_BIND_SERVICE  # Add only what's needed (port 80)
```

**Effect**:
```bash
# In container
ping google.com
# Error: Operation not permitted (CAP_NET_RAW dropped)

chown nobody /app/file
# Error: Operation not permitted (CAP_CHOWN dropped)
```

### Privileged Containers (Dangerous!)

```yaml
# ✗ NEVER DO THIS:
securityContext:
  privileged: true
  # Gives ALL capabilities + access to host devices
```

**Privileged container** can:
- Access host devices (`/dev/*`)
- Load kernel modules
- Access host network stack
- Easily escape to host

**Only use for**: Infrastructure pods (CNI, CSI drivers, monitoring agents).

---

## 6. Runtime Security Monitoring

### Falco: Runtime Threat Detection

**Falco** (CNCF project): Detects anomalous behavior at runtime.

**How it works**:
```
1. Falco runs as DaemonSet (one pod per node)
2. Monitors syscalls via eBPF or kernel module
3. Matches syscalls against rules
4. Alerts on suspicious activity
```

**Example rule**: Detect shell spawned in container.
```yaml
- rule: Terminal shell in container
  desc: Detect shell execution in container
  condition: >
    spawned_process and
    container and
    proc.name in (bash, sh, zsh)
  output: >
    Shell spawned in container (user=%user.name container=%container.name
    shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: WARNING
```

**Alerts**:
```
Attacker runs: kubectl exec -it mypod -- /bin/bash

Falco detects:
  Priority: WARNING
  Rule: Terminal shell in container
  Output: Shell spawned in container (user=root container=mypod
          shell=bash parent=containerd-shim cmdline=bash)

Alert sent to: Slack, PagerDuty, Webhook, etc.
```

**More rules**:
```yaml
# Detect sensitive file reads
- rule: Read sensitive file untrusted
  desc: Attempt to read /etc/shadow
  condition: >
    open_read and
    container and
    fd.name=/etc/shadow
  output: Sensitive file read (%user.name %fd.name %container.name)
  priority: CRITICAL

# Detect privilege escalation
- rule: Privilege escalation
  desc: Container process gained root
  condition: >
    spawned_process and
    container and
    proc.euid=0 and
    proc.ruid!=0
  priority: CRITICAL

# Detect unexpected network connections
- rule: Outbound connection to suspicious IP
  desc: Connection to known malicious IP
  condition: >
    outbound and
    container and
    fd.sip in (suspicious_ips)
  priority: HIGH
```

**Install Falco** (Helm):
```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco \
  --set driver.kind=ebpf \
  --set falco.grpc.enabled=true \
  --set falcosidekick.enabled=true
```

**View alerts**:
```bash
kubectl logs -n falco -l app.kubernetes.io/name=falco

# Or forward to Slack/PagerDuty via Falcosidekick
```

---

## 7. Container Escape Prevention

### Common Escape Techniques

**1. Privileged container escape**:
```bash
# In privileged container
mkdir /host
mount /dev/sda1 /host
chroot /host

# Now have root access to host!
```

**Defense**: Never use `privileged: true` except for infrastructure.

**2. Docker socket mount escape**:
```yaml
# ✗ DANGEROUS:
volumeMounts:
- name: docker-sock
  mountPath: /var/run/docker.sock

volumes:
- name: docker-sock
  hostPath:
    path: /var/run/docker.sock
```

**Attack**:
```bash
# In container with Docker socket access
docker run -v /:/host -it alpine chroot /host

# Escaped to host!
```

**Defense**: Never mount Docker socket into untrusted containers.

**3. Kernel exploit**:
```
Container exploits kernel vulnerability
  → Kernel runs with full privileges
  → Container can escape via kernel
```

**Defense**:
- Keep kernel updated
- Use secure container runtimes (Kata, gVisor) for untrusted workloads

**4. CAP_SYS_ADMIN escape**:
```yaml
# CAP_SYS_ADMIN is very powerful
capabilities:
  add:
  - SYS_ADMIN  # Dangerous!
```

**Attack**: CAP_SYS_ADMIN allows many operations that can lead to escape.

**Defense**: Never grant CAP_SYS_ADMIN. Use more specific capabilities.

---

## 8. Principle of Least Privilege

### Secure Container Specification

**Template for secure pods**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true  # Prevent running as root
    runAsUser: 1000     # Specific non-root UID
    fsGroup: 2000       # File ownership group
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true  # Immutable filesystem
      capabilities:
        drop:
        - ALL  # Drop all capabilities

    # App needs /tmp for temp files
    volumeMounts:
    - name: tmp
      mountPath: /tmp

  volumes:
  - name: tmp
    emptyDir: {}
```

**What this prevents**:
```
✓ Container runs as non-root (runAsNonRoot: true)
✓ Can't escalate to root (allowPrivilegeEscalation: false)
✓ Can't modify filesystem (readOnlyRootFilesystem: true)
✓ Syscalls filtered (seccompProfile: RuntimeDefault)
✓ No capabilities (drop: ALL)
```

### Auditing Existing Workloads

**Find insecure pods**:
```bash
# Pods running as root
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.securityContext.runAsNonRoot != true) | .metadata.name'

# Pods with privileged containers
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].securityContext.privileged == true) | .metadata.name'

# Pods without readOnlyRootFilesystem
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].securityContext.readOnlyRootFilesystem != true) | .metadata.name'
```

---

## Quick Reference

### Security Context Best Practices

```yaml
# Pod-level
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
  seccompProfile:
    type: RuntimeDefault

# Container-level
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

### seccomp Profiles

```yaml
# Use runtime default
seccompProfile:
  type: RuntimeDefault

# Use custom profile
seccompProfile:
  type: Localhost
  localhostProfile: profiles/custom.json

# No seccomp (dangerous!)
seccompProfile:
  type: Unconfined
```

### AppArmor/SELinux

```yaml
# AppArmor (annotation)
metadata:
  annotations:
    container.apparmor.security.beta.kubernetes.io/app: localhost/myprofile

# SELinux (spec)
securityContext:
  seLinuxOptions:
    level: "s0:c123,c456"
```

### Common Commands

```bash
# Check AppArmor profiles
sudo aa-status

# Check seccomp support
grep -i seccomp /boot/config-$(uname -r)

# Check SELinux mode
getenforce

# View container capabilities
docker inspect <container> | jq '.[].HostConfig.CapDrop'

# Falco logs
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

---

## Summary

**Runtime security** protects containers while they're running:
- **seccomp**: Filters syscalls (block dangerous operations)
- **AppArmor/SELinux**: Mandatory access control (restrict file access)
- **Capabilities**: Granular privileges (drop ALL, add only needed)
- **Falco**: Runtime monitoring (detect anomalies)

**Best practices**:
- runAsNonRoot (never run as root)
- readOnlyRootFilesystem (immutable containers)
- Drop all capabilities (add only needed)
- RuntimeDefault seccomp (or custom profile)
- Never use privileged: true
- Monitor with Falco

**Container escape prevention**:
- Don't mount Docker socket
- Don't use CAP_SYS_ADMIN
- Don't run privileged containers
- Use Kata/gVisor for untrusted workloads

**Next**: We've covered image and runtime security. Now we'll explore **Pod Security Standards** and RBAC.

---

## Related Documents

- **Previous**: `05_security/01_image_security.md` - Image security
- **Next**: `05_security/03_pod_security.md` - Pod Security Standards
- **Foundation**: `01_fundamentals/01_cgroups_namespaces.md` - Container primitives
- **Related**: `03_orchestration/06_production_patterns.md` - Security hardening
