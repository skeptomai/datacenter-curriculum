---
level: specialized
estimated_time: 50 min
prerequisites:
  - 04_containers/03_orchestration/03_services_networking.md
  - 04_containers/03_orchestration/06_production_patterns.md
next_recommended:
  - 04_containers/05_security/01_image_security.md
tags: [network-policies, security, multi-tenancy, zero-trust, isolation]
---

# Advanced Network Policy Patterns

## Learning Objectives

After reading this document, you will understand:
- Multi-tenancy isolation with NetworkPolicies
- Namespace-based network segmentation
- Egress policies and external access control
- DNS-based policies (Cilium/Calico)
- Policy for system namespaces (kube-system)
- Troubleshooting NetworkPolicy issues
- Performance considerations at scale
- Real-world policy architectures

## Prerequisites

Before reading this, you should understand:
- Basic NetworkPolicy API
- Kubernetes namespaces and labels
- Network fundamentals (CIDR notation, DNS)

---

## 1. Multi-Tenancy Network Isolation

### Complete Namespace Isolation

**Goal**: Teams can't access each other's services.

**Architecture**:
```
cluster:
  ├─ team-a/ (namespace)
  │   ├─ frontend
  │   ├─ backend
  │   └─ database
  │
  ├─ team-b/ (namespace)
  │   ├─ api
  │   └─ cache
  │
  └─ shared/ (namespace)
      └─ monitoring

Isolation requirement:
  team-a pods ✗ team-b pods
  team-b pods ✗ team-a pods
  all teams ✓ shared/monitoring
```

**Default deny all (per namespace)**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Deploy to all namespaces**:
```bash
for ns in team-a team-b; do
  kubectl apply -n $ns -f default-deny-all.yaml
done
```

**Allow within namespace only**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}  # Any pod in same namespace

  egress:
  - to:
    - podSelector: {}  # Any pod in same namespace

  # Also allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

**Allow access to shared services**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-monitoring
  namespace: team-a
spec:
  podSelector: {}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: shared
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
```

**Result**:
```
team-a/frontend → team-a/backend ✓
team-a/frontend → team-b/api ✗ (different namespace)
team-a/frontend → shared/prometheus ✓ (explicitly allowed)
```

---

## 2. Egress Policies

### Problem: Unrestricted Outbound Access

**Without egress policies**:
```
Any pod can connect to:
  - Internet (curl https://evil.com)
  - Cloud metadata API (curl http://169.254.169.254)
  - Internal infrastructure (curl http://jenkins.corp.internal)

Security risk: Compromised pod can exfiltrate data
```

### Default Deny Egress

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress: []  # No egress allowed
```

**Effect**: Pods can't connect to anything (not even DNS!).

### Allow DNS Only

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Allow Specific External IPs

**Use case**: Backend needs to call external API at specific IP.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53

  # Allow specific external API
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24  # External API IP range
    ports:
    - protocol: TCP
      port: 443
```

**Limitation**: Requires knowing external service IPs (hard for cloud services with dynamic IPs).

### Block Cloud Metadata API

**Problem**: Cloud metadata APIs expose sensitive info.

```
AWS: http://169.254.169.254/latest/meta-data/iam/security-credentials/
GCP: http://metadata.google.internal/computeMetadata/v1/
Azure: http://169.254.169.254/metadata/instance?api-version=2021-02-01
```

**Solution**: Block 169.254.0.0/16 (link-local).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-metadata-api
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 169.254.0.0/16  # Block link-local (metadata API)
        - 10.0.0.0/8      # Block private ranges (optional)
        - 172.16.0.0/12
        - 192.168.0.0/16
```

**Important**: This blocks legitimate link-local uses (e.g., IPv6 link-local). Test carefully.

---

## 3. DNS-Based Policies (Cilium)

### Problem with IP-Based Policies

```
Allow access to api.github.com (52.203.211.10)

Problem:
  - GitHub IPs change frequently
  - Multiple IPs per domain
  - Hard to maintain

Better: Allow by DNS name
```

### Cilium DNS-Aware Policy

**Requires**: Cilium CNI (not available in standard NetworkPolicy API).

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-github-api
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  - toEndpoints:
    - matchLabels:
        "k8s:io.kubernetes.pod.namespace": kube-system
        "k8s:k8s-app": kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"  # Allow all DNS queries

  - toFQDNs:
    - matchName: "api.github.com"  # Allow by DNS name
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**How it works**:
```
1. Pod queries DNS for api.github.com
2. Cilium DNS proxy intercepts query
3. Cilium learns: api.github.com → 52.203.211.10, 52.203.211.11
4. Cilium creates temporary eBPF map entries:
   52.203.211.10:443 → ALLOW
   52.203.211.11:443 → ALLOW
5. Entries expire after TTL (DNS record lifetime)
6. Pod connects to 52.203.211.10:443 → ✓ Allowed
```

**Wildcard patterns**:
```yaml
toFQDNs:
- matchPattern: "*.amazonaws.com"  # Allow all AWS services
- matchPattern: "*.github.com"     # Allow all GitHub
```

**Regex patterns** (advanced):
```yaml
toFQDNs:
- matchName: "api.github.com"
  matchPattern: "api-.*\\.github\\.com"  # Regex
```

### Calico DNS Policy

**Calico** supports DNS policies via `NetworkSet`.

```yaml
apiVersion: crd.projectcalico.org/v1
kind: NetworkSet
metadata:
  name: github-api
  namespace: production
spec:
  allowedEgressDomains:
  - "*.github.com"
```

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-github
spec:
  selector: app == "backend"
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      domains:
      - "*.github.com"
```

---

## 4. System Namespace Policies

### kube-system Access Control

**Problem**: kube-system is critical (DNS, metrics-server, etc.).

**Default**: All pods can access kube-system services.
```
Any pod → kube-dns:53 ✓ (needed)
Any pod → kube-apiserver:443 ✓ (usually not needed!)
```

**Secure approach**: Only allow necessary access.

**Allow DNS from all namespaces**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: kube-system
spec:
  podSelector:
    matchLabels:
      k8s-app: kube-dns
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector: {}  # All namespaces
    ports:
    - protocol: UDP
      port: 53
```

**Restrict API server access**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apiserver-ingress
  namespace: kube-system
spec:
  podSelector:
    matchLabels:
      component: kube-apiserver
  policyTypes:
  - Ingress
  ingress:
  # Allow from control plane
  - from:
    - podSelector:
        matchLabels:
          tier: control-plane

  # Allow from specific namespaces
  - from:
    - namespaceSelector:
        matchLabels:
          allow-apiserver-access: "true"
```

**Label trusted namespaces**:
```bash
kubectl label namespace platform allow-apiserver-access=true
kubectl label namespace monitoring allow-apiserver-access=true
```

**Result**:
```
platform/operator → kube-apiserver ✓
production/backend → kube-apiserver ✗
```

---

## 5. Layer 7 Policies (HTTP/gRPC)

### Cilium L7 NetworkPolicy

**Standard NetworkPolicy**: L3/L4 only (IP, port, protocol).

**Cilium**: L7-aware (HTTP methods, paths, headers).

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/.*"  # Regex
        - method: "POST"
          path: "/api/submit"
```

**Effect**:
```
frontend → GET /api/users → ✓ Allowed
frontend → GET /api/data → ✓ Allowed (matches /api/.*)
frontend → POST /api/submit → ✓ Allowed
frontend → POST /api/delete → ✗ Denied (no POST to /api/.* except /api/submit)
frontend → DELETE /api/users → ✗ Denied (only GET/POST allowed)
```

**gRPC policy**:
```yaml
rules:
  kafka:
  - role: "produce"
    topic: "orders"

  # Or gRPC
  grpc:
  - method: "orderservice.OrderService/GetOrder"
  - method: "orderservice.OrderService/CreateOrder"
```

**Performance cost**: L7 parsing in eBPF (still fast, ~10µs per request).

---

## 6. Real-World Policy Architecture

### Three-Tier Application

```
┌──────────────────────────────────────────────┐
│ Ingress (external traffic)                   │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Frontend Tier (namespace: frontend)          │
│   Policy: Allow from Ingress only           │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Backend Tier (namespace: backend)            │
│   Policy: Allow from Frontend only          │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Database Tier (namespace: database)          │
│   Policy: Allow from Backend only           │
└──────────────────────────────────────────────┘
```

**Frontend policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow from ingress controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080

  egress:
  # Allow to backend
  - to:
    - namespaceSelector:
        matchLabels:
          name: backend
    ports:
    - protocol: TCP
      port: 8080

  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

**Backend policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow from frontend only
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080

  egress:
  # Allow to database
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432

  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53

  # Allow external API (example)
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
```

**Database policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: database
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  # Allow from backend only
  - from:
    - namespaceSelector:
        matchLabels:
          name: backend
    ports:
    - protocol: TCP
      port: 5432

  # No egress rules (database doesn't initiate connections)
```

---

## 7. Troubleshooting NetworkPolicies

### Common Issues

**1. Pod has no network connectivity**

**Symptoms**:
```bash
kubectl exec -it mypod -- curl http://backend:8080
# Hangs or connection refused
```

**Debug steps**:
```bash
# 1. Check if NetworkPolicies exist
kubectl get networkpolicy -n production

# 2. Describe policies
kubectl describe networkpolicy default-deny-all -n production

# 3. Check pod labels
kubectl get pod mypod -n production --show-labels

# 4. Check if CNI supports NetworkPolicy
# (Flannel does NOT, Calico/Cilium do)

# 5. Test without policies (delete temporarily)
kubectl delete networkpolicy --all -n production
kubectl exec -it mypod -- curl http://backend:8080  # Works now?
```

**Common mistakes**:
```yaml
# ✗ WRONG: Typo in namespace selector
ingress:
- from:
  - namespaceSelector:
      matchLabels:
        name: fronted  # Typo! Should be "frontend"

# ✓ CORRECT:
ingress:
- from:
  - namespaceSelector:
      matchLabels:
        name: frontend
```

**2. DNS doesn't work**

**Symptom**:
```bash
kubectl exec -it mypod -- nslookup backend
# Timeout or no response
```

**Cause**: Egress policy blocks DNS.

**Fix**: Always allow DNS.
```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: kube-system
  ports:
  - protocol: UDP
    port: 53
```

**3. Policy not taking effect**

**Symptom**: Created NetworkPolicy, but traffic still allowed/denied incorrectly.

**Debug**:
```bash
# Check CNI plugin logs
kubectl logs -n kube-system -l k8s-app=calico-node

# Cilium: Check policy enforcement
cilium endpoint list
cilium policy get <endpoint-id>

# Calico: Check iptables rules
iptables-save | grep cali
```

**Important**: NetworkPolicy changes can take 10-30 seconds to propagate.

### Testing NetworkPolicies

**Use netshoot for debugging**:
```bash
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash

# Inside container
curl http://backend:8080  # Test HTTP
nc -zv backend 8080       # Test TCP
nslookup backend          # Test DNS
```

**Automated testing** (bash script):
```bash
#!/bin/bash
# test-network-policy.sh

NS="production"
POD="test-pod"

# Deploy test pod
kubectl run $POD -n $NS --image=busybox --rm -it --restart=Never -- sh -c "
  # Test 1: DNS should work
  nslookup backend && echo 'DNS: PASS' || echo 'DNS: FAIL'

  # Test 2: Backend should be reachable
  nc -zv backend 8080 && echo 'Backend: PASS' || echo 'Backend: FAIL'

  # Test 3: External should be blocked
  nc -zv google.com 443 && echo 'External: FAIL (should be blocked)' || echo 'External: PASS'
"
```

---

## 8. Performance Considerations

### Policy Scale Limits

**iptables-based (Calico default)**:
```
~1000 pods per node with complex policies
  → iptables rules grow linearly
  → Rule evaluation is O(N)

At scale (>5000 pods):
  → iptables rule reload takes 30+ seconds
  → Network latency spikes during policy updates
```

**eBPF-based (Cilium)**:
```
10,000+ pods per node
  → eBPF map lookups are O(1)
  → Policy updates take <1 second

Better for large clusters (>100 nodes)
```

### Policy Optimization Tips

**1. Use broader selectors (fewer policies)**:
```yaml
# ✗ BAD: One policy per pod
- podSelector:
    matchLabels:
      app: backend
      version: v1
      team: platform

# ✓ GOOD: One policy per tier
- podSelector:
    matchLabels:
      tier: backend
```

**2. Combine ingress and egress in one policy**:
```yaml
# ✓ GOOD: Single policy
spec:
  policyTypes:
  - Ingress
  - Egress
  ingress: [...]
  egress: [...]

# ✗ BAD: Separate policies (more rules)
# policy-ingress.yaml + policy-egress.yaml
```

**3. Use namespace selectors over pod selectors**:
```yaml
# ✓ GOOD: Matches entire namespace (one rule)
from:
- namespaceSelector:
    matchLabels:
      name: frontend

# ✗ BAD: Matches pods individually (N rules for N pods)
from:
- podSelector:
    matchLabels:
      app: frontend
```

---

## Quick Reference

### Common Policy Patterns

**Default deny all (template)**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Allow same namespace**:
```yaml
ingress:
- from:
  - podSelector: {}
egress:
- to:
  - podSelector: {}
```

**Allow DNS (always needed with egress policies)**:
```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: kube-system
  ports:
  - protocol: UDP
    port: 53
```

**Block cloud metadata API**:
```yaml
egress:
- to:
  - ipBlock:
      cidr: 0.0.0.0/0
      except:
      - 169.254.0.0/16
```

### Troubleshooting Commands

```bash
# List all policies
kubectl get networkpolicy --all-namespaces

# Describe policy
kubectl describe networkpolicy <name> -n <namespace>

# Check pod labels
kubectl get pods --show-labels -n <namespace>

# Test connectivity (netshoot)
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash

# Cilium: Check endpoint policies
cilium endpoint list
cilium policy get <endpoint-id>

# Calico: View generated iptables rules
iptables-save | grep cali
```

### Policy Validation

```bash
# Dry-run policy creation
kubectl apply -f policy.yaml --dry-run=server

# Validate with kubectl
kubectl describe networkpolicy <name>

# Automated testing
kubectl run test --rm -it --image=busybox -- nc -zv <target> <port>
```

---

## Summary

**Multi-tenancy**: Namespace-based isolation with default deny + explicit allow.

**Egress control**:
- Default deny egress prevents data exfiltration
- Always allow DNS (UDP 53 to kube-system)
- Block cloud metadata API (169.254.0.0/16)

**DNS-based policies** (Cilium/Calico):
- Allow by domain name (not IP)
- Handles dynamic IPs automatically
- Use wildcards for cloud services

**System namespace policies**:
- Protect kube-system (allow DNS to all, restrict API server)
- Use namespace labels for access control

**Layer 7 policies** (Cilium only):
- HTTP method/path filtering
- gRPC method filtering
- Kafka topic ACLs

**Troubleshooting**:
- Check policy exists and matches pod labels
- Always allow DNS in egress policies
- Test with netshoot or busybox pods
- Policy changes take 10-30 seconds

**Performance**:
- eBPF (Cilium) scales better than iptables (Calico) for >1000 pods
- Use broad selectors (namespace-level, not pod-level)
- Combine ingress + egress in one policy

**Next**: We've completed networking. Now we'll shift to **container security**, starting with **image security** and supply chain concerns.

---

## Related Documents

- **Previous**: `04_networking/04_service_mesh.md` - Service mesh patterns
- **Next**: `05_security/01_image_security.md` - Container image security
- **Foundation**: `03_orchestration/03_services_networking.md` - NetworkPolicy basics
- **Related**: `03_orchestration/06_production_patterns.md` - Zero-trust networking
