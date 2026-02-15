---
level: specialized
estimated_time: 60 min
prerequisites:
  - 04_containers/03_orchestration/03_services_networking.md
  - 01_foundations/02_datacenter_topology/01_modern_topology.md
next_recommended:
  - 04_containers/04_networking/02_calico_vs_cilium.md
tags: [cni, networking, kubernetes, plugins, veth, bridge, overlay]
---

# CNI Deep Dive: How Container Networking Really Works

## Learning Objectives

After reading this document, you will understand:
- The CNI specification and plugin interface
- How kubelet invokes CNI plugins
- Network namespace setup and veth pairs
- Bridge and overlay network implementations
- IPAM (IP Address Management) plugins
- CNI plugin chaining and meta-plugins
- Writing a simple CNI plugin

## Prerequisites

Before reading this, you should understand:
- Kubernetes networking basics (Services, pods)
- Linux network namespaces
- Basic datacenter networking concepts

---

## 1. The CNI (Container Network Interface) Specification

### Why CNI (Container Network Interface) Exists

**Problem before CNI**:
```
Each container runtime had its own networking:
- Docker: libnetwork
- rkt: rkt networking
- Mesos: Mesos CNI (different interface)

Kubernetes had to support all of them (complex, fragile)
```

**CNI solution**: Standard interface for container networking.

```
┌─────────────────────────────────────────┐
│ Container Runtime (kubelet)             │
└──────────────┬──────────────────────────┘
               │ Executes CNI plugin
               ↓
┌─────────────────────────────────────────┐
│ CNI Plugin (executable)                 │
│ - Input: JSON config                    │
│ - Output: JSON result                   │
└──────────────┬──────────────────────────┘
               │ Configures
               ↓
┌─────────────────────────────────────────┐
│ Linux Networking (netns, veth, routes)  │
└─────────────────────────────────────────┘
```

### CNI Interface

**CNI plugin is just an executable** that:
1. Reads JSON config from stdin
2. Performs network operations
3. Writes JSON result to stdout

**Four operations** (commands):

```bash
# ADD: Set up networking for container
CNI_COMMAND=ADD /opt/cni/bin/bridge < config.json

# DEL: Tear down networking
CNI_COMMAND=DEL /opt/cni/bin/bridge < config.json

# CHECK: Verify network still configured
CNI_COMMAND=CHECK /opt/cni/bin/bridge < config.json

# VERSION: Report plugin versions
CNI_COMMAND=VERSION /opt/cni/bin/bridge
```

---

## 2. CNI Plugin Invocation

### How kubelet Uses CNI

```
1. kubelet creates pod sandbox (pause container)
2. kubelet creates network namespace for pod
3. kubelet reads CNI config from /etc/cni/net.d/
4. kubelet executes CNI plugin(s)
5. kubelet starts application containers in same netns
```

**Environment variables** (passed to plugin):

```bash
CNI_COMMAND=ADD
CNI_CONTAINERID=abc123def456  # Container ID
CNI_NETNS=/var/run/netns/pod-ns  # Network namespace path
CNI_IFNAME=eth0  # Interface name to create in container
CNI_ARGS=K8S_POD_NAME=mypod;K8S_POD_NAMESPACE=default
CNI_PATH=/opt/cni/bin  # Where to find other plugins
```

**Input JSON** (stdin to plugin):

```json
{
  "cniVersion": "1.0.0",
  "name": "mynet",
  "type": "bridge",  // ← Plugin to execute
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.244.0.0/16",
    "routes": [
      { "dst": "0.0.0.0/0" }
    ]
  }
}
```

**Output JSON** (stdout from plugin):

```json
{
  "cniVersion": "1.0.0",
  "interfaces": [
    {
      "name": "cni0",
      "mac": "00:11:22:33:44:55"
    },
    {
      "name": "veth12345678",
      "mac": "aa:bb:cc:dd:ee:ff"
    },
    {
      "name": "eth0",
      "mac": "aa:bb:cc:dd:ee:ff",
      "sandbox": "/var/run/netns/pod-ns"
    }
  ],
  "ips": [
    {
      "address": "10.244.0.5/16",
      "gateway": "10.244.0.1",
      "interface": 2  // ← Index into interfaces array (eth0)
    }
  ],
  "routes": [
    {
      "dst": "0.0.0.0/0",
      "gw": "10.244.0.1"
    }
  ],
  "dns": {
    "nameservers": ["10.96.0.10"],
    "search": ["default.svc.cluster.local", "svc.cluster.local"]
  }
}
```

---

## 3. Bridge Plugin Implementation

The **bridge** plugin creates a Linux bridge and connects containers to it.

### Step-by-Step: What the Bridge Plugin Does

**Initial state** (node):
```
Node: eth0 (10.0.0.5)
```

**After plugin execution**:
```
Node networking:
  eth0: 10.0.0.5 (unchanged, node IP)
  cni0: 10.244.0.1/16 (bridge, gateway for pods)

Pod networking:
  Network namespace: /var/run/netns/pod-abc123
    eth0@if5: 10.244.0.5/16
      ↓ veth pair
    veth12345678@if4 (attached to cni0 bridge)
```

### Detailed Bridge Plugin Steps

**1. Create bridge (if doesn't exist)**:
```bash
ip link add cni0 type bridge
ip link set cni0 up
ip addr add 10.244.0.1/16 dev cni0
```

**2. Create veth pair**:
```bash
# Generate random name for host-side interface
VETH_NAME=veth$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 8)

# Create veth pair (both ends initially in host namespace)
# This creates TWO interfaces: ${VETH_NAME} and eth0, connected like a cable
ip link add ${VETH_NAME} type veth peer name eth0
```

**What is a veth pair?**
A **virtual ethernet pair** acts like a virtual cable with two ends:
- Both ends are kernel network devices (not userspace)
- Packets sent to one end immediately appear at the other end
- Used to connect different network namespaces

**veth vs TAP/TUN** (used for VMs):
- TAP/TUN: kernel ↔ userspace process (file descriptor)
- veth: kernel ↔ kernel (different namespaces)
- VMs use TAP (QEMU reads packets from file descriptor)
- Containers use veth (kernel-to-kernel, no userspace overhead)

**3. Move one end into container netns**:
```bash
# Move the eth0 end into the container's network namespace
# The ${VETH_NAME} end stays in the host's network namespace
ip link set eth0 netns ${CNI_NETNS}
```

**Critical point**: After this step:
- `eth0` is **inside the container** (container namespace)
- `${VETH_NAME}` is **on the host** (root namespace)
- They're still connected like a cable through the namespace boundary

**4. Configure container-side interface**:
```bash
# Inside network namespace
ip netns exec ${CNI_NETNS} ip link set eth0 up
ip netns exec ${CNI_NETNS} ip addr add 10.244.0.5/16 dev eth0
ip netns exec ${CNI_NETNS} ip route add default via 10.244.0.1
```

**5. Attach host-side veth to bridge**:
```bash
ip link set ${VETH_NAME} master cni0
ip link set ${VETH_NAME} up
```

**6. Enable IP masquerading** (if ipMasq: true):
```bash
iptables -t nat -A POSTROUTING \
  -s 10.244.0.0/16 \
  -j MASQUERADE
```

**Result** (namespace boundary clearly shown):
```
┌─────────────────────────────────────────────────┐
│ Pod Network Namespace (isolated)                │
│                                                  │
│   lo: 127.0.0.1                                 │
│   eth0: 10.244.0.5/16                          │
│      ↑                                          │
└──────┼──────────────────────────────────────────┘
       │ veth pair (crosses namespace boundary)
       │
┌──────┼──────────────────────────────────────────┐
│ Host Network Namespace (root namespace)         │
│      ↓                                          │
│   veth12345678 ──┐                             │
│   vethabcdefgh ──┼─→ cni0 bridge: 10.244.0.1   │
│   veth98765432 ──┘      ↕                       │
│                      eth0: 10.0.0.5 (node IP)   │
└─────────────────────────────────────────────────┘
```

**Key insight**: The veth pair is the **only** connection between the isolated container namespace and the host. The container cannot see the host's eth0 or other interfaces - it only sees its own eth0 (which is really one end of the veth pair).

### Traffic Flow

**Pod → Internet**:
```
1. Pod sends packet: src=10.244.0.5, dst=8.8.8.8
2. Routing: default via 10.244.0.1 (cni0)
3. Packet leaves eth0, enters veth pair
4. Packet arrives at cni0 bridge
5. Bridge forwards to node's routing stack
6. iptables MASQUERADE: src=10.244.0.5 → src=10.0.0.5 (node IP)
7. Packet leaves node via eth0: src=10.0.0.5, dst=8.8.8.8
8. Return traffic: dst=10.0.0.5
9. iptables reverse NAT: dst=10.0.0.5 → dst=10.244.0.5
10. Routing: 10.244.0.5 via cni0
11. Bridge forwards to veth12345678
12. Packet enters pod netns via eth0
```

**Pod-to-pod (same node)**:
```
Pod A (10.244.0.5) → Pod B (10.244.0.6)

1. Pod A sends packet: src=10.244.0.5, dst=10.244.0.6
2. Pod A routing: 10.244.0.6 via 10.244.0.1 (cni0)
3. Packet arrives at cni0 bridge
4. Bridge learns Pod B is on veth98765432
5. Bridge forwards packet directly to veth98765432
6. Packet enters Pod B netns

No iptables, no NAT (same L2 domain)
```

---

## 4. IPAM (IP Address Management)

**Problem**: Who assigns IP addresses to pods?

**Solution**: IPAM (IP Address Management) plugins (invoked by main plugin).

### host-local IPAM

**Most common IPAM plugin** (local state on each node).

**Configuration**:
```json
{
  "type": "host-local",
  "subnet": "10.244.0.0/16",
  "rangeStart": "10.244.0.10",
  "rangeEnd": "10.244.0.250",
  "gateway": "10.244.0.1",
  "routes": [
    { "dst": "0.0.0.0/0" }
  ]
}
```

**State storage** (per-node):
```
/var/lib/cni/networks/mynet/
├── 10.244.0.5  (contains container ID)
├── 10.244.0.6
├── 10.244.0.7
└── last_reserved_ip.0  (last IP allocated)
```

**ADD operation**:
```
1. Read last_reserved_ip
2. Increment to next IP
3. Check if in range (10.244.0.10 - 10.244.0.250)
4. Check if already allocated (file exists)
5. Create file: echo ${CONTAINERID} > 10.244.0.5
6. Return IP to main plugin
```

**DEL operation**:
```
1. Find IP file containing this container ID
2. Delete file
3. IP is free for reuse
```

**Limitations**:
- No cluster-wide coordination (each node has separate pool)
- IP reuse can happen if file deleted manually
- Requires subnet per node (e.g., node1: 10.244.0.0/24, node2: 10.244.1.0/24)

### DHCP IPAM

**Alternative**: Run DHCP server, pods get IPs via DHCP.

```json
{
  "type": "dhcp"
}
```

**How it works**:
```
1. CNI DHCP plugin starts daemon on node
2. When pod created, daemon sends DHCP request in pod netns
3. DHCP server responds with IP
4. Plugin configures interface
5. Daemon renews lease periodically
```

**Use case**: Integration with existing DHCP infrastructure.

---

## 5. Overlay Networking (VXLAN Example)

**Problem**: Pods on different nodes need to communicate, but nodes are on different subnets.

**Solution**: Encapsulate pod traffic in VXLAN tunnel.

### VXLAN CNI Plugin

**Configuration**:
```json
{
  "name": "mynet",
  "type": "vxlan",
  "vni": 4096,  // VNI is VXLAN Network Identifier
  "port": 4789,
  "ipam": {
    "type": "host-local",
    "subnet": "10.244.0.0/16"
  }
}
```

**What the plugin creates**:

```
Node 1 (10.0.0.5):
  vtep0: VXLAN device
    VNI: 4096
    Local IP: 10.0.0.5
    Port: 4789

Pod on Node 1: 10.244.0.5
```

**Forwarding table** (learned or configured):
```
FDB (Forwarding Database):
  10.244.1.0/24 → vtep0 → remote 10.0.0.6 (Node 2)
  10.244.2.0/24 → vtep0 → remote 10.0.0.7 (Node 3)
```

**Packet flow** (Pod on Node 1 → Pod on Node 2):

```
Inner packet:
  src: 10.244.0.5 (Pod on Node 1)
  dst: 10.244.1.10 (Pod on Node 2)

1. Pod sends packet
2. Routing: 10.244.1.0/24 via vtep0
3. VXLAN encapsulation:
   Outer packet:
     src: 10.0.0.5 (Node 1 IP)
     dst: 10.0.0.6 (Node 2 IP)
     UDP port: 4789
     VXLAN header: VNI 4096
     Inner packet: [unchanged]

4. Packet sent over node network
5. Node 2 receives on UDP 4789
6. VXLAN decapsulation
7. Inner packet forwarded to pod: 10.244.1.10
```

**Connection to earlier concepts**:
Recall from `02_intermediate/01_advanced_networking/02_overlay_mechanics.md`:
- VXLAN adds 50-byte overhead
- Uses UDP port 4789
- VNI (24-bit) allows 16M isolated networks

---

## 6. Plugin Chaining and Meta-Plugins

### Plugin Chaining

**Use case**: Combine multiple plugins (e.g., bridge + firewall + bandwidth).

**Configuration** (/etc/cni/net.d/10-mynet.conflist):
```json
{
  "cniVersion": "1.0.0",
  "name": "mynet",
  "plugins": [
    {
      "type": "bridge",
      "bridge": "cni0",
      "ipam": {
        "type": "host-local",
        "subnet": "10.244.0.0/16"
      }
    },
    {
      "type": "firewall",
      "backend": "iptables"
    },
    {
      "type": "bandwidth",
      "ingressRate": 1000000,  // 1 Mbps
      "egressRate": 1000000
    },
    {
      "type": "portmap",
      "capabilities": {"portMappings": true}
    }
  ]
}
```

**Execution flow**:
```
kubelet executes plugins in order:
  1. bridge: Creates veth, assigns IP
  2. firewall: Adds iptables rules
  3. bandwidth: Configures TC (traffic control) qdisc
  4. portmap: Sets up port forwarding (like docker -p)

Each plugin receives previous plugin's result as input
```

**Result chaining**:
```json
// After bridge plugin
{
  "ips": [{"address": "10.244.0.5/16"}]
}

// Passed to firewall plugin (may add/modify)
// Passed to bandwidth plugin (may add/modify)
// Final result returned to kubelet
```

### Meta-Plugins

**Meta-plugins** don't configure networking directly; they modify or coordinate other plugins.

**1. Multus** (multiple network interfaces):
```
Problem: Pod needs multiple network interfaces (management + data plane)

Multus solution:
  - Delegates to multiple CNI plugins
  - Creates eth0 (default network) + net1, net2 (additional)
```

**Configuration**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multipod
  annotations:
    k8s.v8s.io/networks: sriov-net1,sriov-net2
spec:
  containers:
  - name: app
    image: myapp:1.0
```

**Result**:
```
Pod namespace:
  eth0: 10.244.0.5 (default CNI)
  net1: 192.168.1.10 (SR-IOV network)
  net2: 192.168.2.10 (SR-IOV network)
```

**2. Bandwidth** (traffic shaping):
```json
{
  "type": "bandwidth",
  "ingressRate": 10000000,  // 10 Mbps
  "ingressBurst": 2000000,  // 2 MB
  "egressRate": 10000000,
  "egressBurst": 2000000
}
```

Uses Linux **tc (traffic control)** to enforce limits.

---

## 7. Writing a Simple CNI Plugin

### Minimal CNI Plugin (bash example)

```bash
#!/bin/bash
# simple-cni.sh

set -e

# Read config from stdin
config=$(cat)

# Extract fields
CONTAINER_ID=${CNI_CONTAINERID}
NETNS=${CNI_NETNS}
IFNAME=${CNI_IFNAME}

case ${CNI_COMMAND} in
  ADD)
    # 1. Create veth pair
    HOST_IFNAME=veth${CONTAINER_ID:0:8}
    ip link add ${HOST_IFNAME} type veth peer name ${IFNAME}

    # 2. Move container end into netns
    ip link set ${IFNAME} netns ${NETNS}

    # 3. Configure container interface
    ip netns exec ${NETNS} ip link set ${IFNAME} up
    ip netns exec ${NETNS} ip addr add 10.244.0.5/24 dev ${IFNAME}
    ip netns exec ${NETNS} ip route add default via 10.244.0.1

    # 4. Configure host interface
    ip link set ${HOST_IFNAME} up

    # 5. Return result
    cat <<EOF
{
  "cniVersion": "1.0.0",
  "interfaces": [
    {"name": "${IFNAME}", "sandbox": "${NETNS}"}
  ],
  "ips": [
    {
      "address": "10.244.0.5/24",
      "gateway": "10.244.0.1",
      "interface": 0
    }
  ]
}
EOF
    ;;

  DEL)
    # Clean up (delete veth pair)
    # Note: Deleting netns automatically deletes veth pair
    exit 0
    ;;

  VERSION)
    cat <<EOF
{
  "cniVersion": "1.0.0",
  "supportedVersions": ["0.4.0", "1.0.0"]
}
EOF
    ;;
esac
```

**Install and test**:
```bash
# Install plugin
sudo cp simple-cni.sh /opt/cni/bin/simple-cni
sudo chmod +x /opt/cni/bin/simple-cni

# Create config
cat > /etc/cni/net.d/10-simple.conf <<EOF
{
  "cniVersion": "1.0.0",
  "name": "simple",
  "type": "simple-cni"
}
EOF

# Test (create netns first)
sudo ip netns add testns

# Invoke plugin
sudo CNI_COMMAND=ADD \
  CNI_CONTAINERID=test123 \
  CNI_NETNS=/var/run/netns/testns \
  CNI_IFNAME=eth0 \
  CNI_PATH=/opt/cni/bin \
  /opt/cni/bin/simple-cni < /etc/cni/net.d/10-simple.conf

# Verify
sudo ip netns exec testns ip addr show eth0
```

---

## 8. CNI vs Other Networking Models

### CNI vs CNM (libnetwork)

**CNM** (Docker's Container Network Model):
```
Concepts:
  - Sandbox: Network namespace
  - Endpoint: Network interface
  - Network: Isolated network

API: Programming library (not executable plugins)
```

**CNI**:
```
Concepts:
  - Network namespace
  - Interface in namespace

API: Executable plugins (JSON in/out)
```

**Why Kubernetes chose CNI**:
- Simpler interface (exec vs library)
- Language-agnostic (any language, just exec)
- Community-driven (CNCF)

---

## 9. Debugging CNI

### Common Issues

**1. Pod stuck in ContainerCreating**:
```bash
kubectl describe pod mypod
# Events:
#   Failed to create pod sandbox: error adding network: ...

# Check CNI logs
journalctl -u kubelet | grep CNI

# Check CNI config
ls -l /etc/cni/net.d/
cat /etc/cni/net.d/10-mynet.conf

# Verify plugins exist
ls -l /opt/cni/bin/
```

**2. Pod has no network connectivity**:
```bash
# Check pod network namespace
kubectl exec -it mypod -- ip addr
kubectl exec -it mypod -- ip route

# Check routing on node
ip route | grep 10.244.0.0

# Check bridge (if using bridge plugin)
ip link show cni0
bridge fdb show | grep <pod-mac>

# Check iptables rules
iptables -t nat -L POSTROUTING -v
```

**3. CNI plugin errors**:
```bash
# Run plugin manually to see errors
sudo CNI_COMMAND=ADD \
  CNI_CONTAINERID=test \
  CNI_NETNS=/var/run/netns/test \
  CNI_IFNAME=eth0 \
  CNI_PATH=/opt/cni/bin \
  /opt/cni/bin/bridge < /etc/cni/net.d/10-bridge.conf
```

### CNI Plugin Logs

**Most plugins log to**:
```
/var/log/pods/
/var/log/containers/
journalctl -u kubelet
```

**Enable CNI debugging**:
```json
{
  "name": "mynet",
  "type": "bridge",
  "cniVersion": "1.0.0",
  "logLevel": "debug",
  "logFile": "/var/log/cni.log"
}
```

---

## Quick Reference

### CNI Interface

```bash
# Environment variables
CNI_COMMAND=ADD|DEL|CHECK|VERSION
CNI_CONTAINERID=<container-id>
CNI_NETNS=<network-namespace-path>
CNI_IFNAME=<interface-name>
CNI_PATH=<plugin-search-path>

# Input: JSON config (stdin)
# Output: JSON result (stdout)
```

### Common CNI Plugins

| Plugin      | Type    | Purpose                              |
|-------------|---------|--------------------------------------|
| bridge      | Main    | Linux bridge networking              |
| vlan        | Main    | VLAN tagging                         |
| ipvlan      | Main    | ipvlan networking                    |
| macvlan     | Main    | macvlan networking                   |
| host-local  | IPAM    | Local IP address management          |
| dhcp        | IPAM    | DHCP-based IP management             |
| bandwidth   | Meta    | Traffic shaping (tc qdisc)           |
| portmap     | Meta    | Port forwarding (like docker -p)     |
| firewall    | Meta    | iptables rules                       |
| tuning      | Meta    | Interface tuning (MTU, etc.)         |

### Debugging Commands

```bash
# View CNI config
ls -l /etc/cni/net.d/

# View installed plugins
ls -l /opt/cni/bin/

# Check kubelet CNI usage
journalctl -u kubelet | grep CNI

# Run plugin manually (for debugging)
sudo CNI_COMMAND=ADD ... /opt/cni/bin/<plugin> < config.json

# Check network namespaces
ip netns list

# Check veth pairs
ip link | grep veth
```

---

## Summary

**CNI specification** defines a simple interface:
- Executable plugins (not libraries)
- JSON config input, JSON result output
- Four operations: ADD, DEL, CHECK, VERSION

**kubelet invocation**:
- Creates network namespace for pod
- Executes CNI plugin(s) with environment variables
- Configures container to use resulting network

**Bridge plugin** (common implementation):
- Creates Linux bridge (cni0)
- Creates veth pair per pod
- Connects pods to bridge
- Enables IP masquerading for external traffic

**IPAM plugins**:
- Assign IP addresses to pods
- host-local: Local state, subnet per node
- DHCP: External DHCP server

**Overlay networking** (VXLAN):
- Encapsulates pod traffic in UDP packets
- Enables pod communication across subnets
- Adds overhead (50 bytes per packet)

**Plugin chaining**:
- Combine multiple plugins (network + firewall + bandwidth)
- Each plugin receives previous result

**Meta-plugins**:
- Multus: Multiple network interfaces
- Bandwidth: Traffic shaping
- Portmap: Port forwarding

**Next**: Now that you understand CNI internals, we'll compare two major implementations: **Calico vs Cilium**.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[CNI Plugins Repository](https://github.com/containernetworking/plugins)** - Reference implementations of bridge, host-device, and other core CNI plugins
- **[Writing a CNI Plugin](https://www.cni.dev/docs/spec/)** - Official CNI specification and plugin development guide
- **[CNI Plugin Tutorial](https://karampok.me/posts/writing-a-cni-plugin/)** - Step-by-step guide to creating a custom CNI plugin

---

## Related Documents

- **Previous**: `03_orchestration/03_services_networking.md` - CNI overview
- **Next**: `04_networking/02_calico_vs_cilium.md` - CNI plugin comparison
- **Foundation**: `01_fundamentals/01_cgroups_namespaces.md` - Network namespaces
- **Related**: `02_intermediate/01_advanced_networking/02_overlay_mechanics.md` - VXLAN details
