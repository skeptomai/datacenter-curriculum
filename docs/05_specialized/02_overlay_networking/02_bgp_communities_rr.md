---
level: specialized
estimated_time: 45 min
prerequisites:
  - 05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md
next_recommended:
  - 05_specialized/02_overlay_networking/03_rr_session_cardinality.md
tags: [networking, bgp, route-reflectors, communities, scaling]
---

# BGP Communities vs Route Reflectors - Clarifying Different Solutions

## What BGP Communities Actually Solve

### BGP Communities Are Tags, Not Topology Solutions

**BGP Communities** are 32-bit values attached to routes as metadata. They solve the problem of **route policy and traffic engineering**, NOT the iBGP full-mesh scaling problem.

#### Community Structure

```
Standard Community: 32 bits
  ┌─────────────────┬─────────────────┐
  │   AS Number     │   Local Value   │
  │    (16 bits)    │    (16 bits)    │
  └─────────────────┴─────────────────┘
  
Example: 65000:100
  AS: 65000
  Local Value: 100
  
Meaning is operator-defined, e.g.:
  65000:100 = "Routes from customers"
  65000:200 = "Routes from peers"
  65000:300 = "Routes from upstreams"
```

#### Well-Known Communities

```
NO_EXPORT (0xFFFFFF01)
  - Don't advertise to eBGP peers
  - Keep within AS

NO_ADVERTISE (0xFFFFFF02)
  - Don't advertise to ANY peer
  - Local router only

NO_EXPORT_SUBCONFED (0xFFFFFF03)
  - Don't advertise outside confederation

LOCAL_PREF:xxx
  - Used for traffic engineering
```

### What Communities Are Used For

#### 1. Route Filtering

```
Provider network:
  - Customer A routes tagged with 65000:100
  - Customer B routes tagged with 65000:101
  - Internal routes tagged with 65000:200

Policy at edge router:
  "Don't advertise customer routes to other customers"
  
  if community == 65000:100 or 65000:101:
      don't advertise to customers
```

#### 2. Traffic Engineering

```
Customer wants to control inbound traffic:

Customer advertises route with community tags:
  203.0.113.0/24 community 65000:120  → "Use primary link"
  203.0.113.0/24 community 65000:110  → "Use backup link"

Provider action based on community:
  65000:120 → Set LOCAL_PREF = 200 (prefer this)
  65000:110 → Set LOCAL_PREF = 100 (use as backup)
  
Result: Traffic enters via primary link
```

#### 3. Blackhole/Rate-Limit Routing

```
DDoS attack on 203.0.113.50:

Customer advertises:
  203.0.113.50/32 community 65000:666  ← Blackhole community

Provider sees 65000:666:
  Route to null0 (drop traffic)
  Protects rest of network

Common provider communities:
  3356:666 (Level3 blackhole)
  174:666 (Cogent blackhole)
```

#### 4. Prepending Control

```
Customer wants to make path less attractive:

Customer tags route: 65000:prepend-3times

Provider sees community:
  Add own AS to AS_PATH 3 times
  AS_PATH becomes: [65000, 65000, 65000, 200, 100]
  
Longer AS_PATH → Less preferred by remote networks
```

### Communities Do NOT Solve Scaling

**Key Point:** Communities don't reduce the number of BGP sessions needed. They're just metadata on routes.

```
Without Communities:
  Node A ←→ Node B ←→ Node C ←→ Node D
  (Full mesh: 6 sessions for 4 nodes)

With Communities:
  Node A ←→ Node B ←→ Node C ←→ Node D
  (Still full mesh: 6 sessions for 4 nodes)
  
Routes just have tags attached, but topology unchanged!
```

---

## What You Might Be Thinking Of: BGP Confederations

I suspect you might be thinking of **BGP Confederations**, which DO solve the same problem as Route Reflectors (the iBGP full-mesh scaling issue).

### BGP Confederations - Alternative to Route Reflectors

#### The Concept

Instead of one large AS with full-mesh iBGP, split into multiple **sub-ASes** that use eBGP between them:

```
Original AS 65000 with 1000 routers:
  ┌─────────────────────────────────────────┐
  │         AS 65000                        │
  │                                         │
  │  R1 ←→ R2 ←→ R3 ←→ ... ←→ R1000        │
  │  (499,500 iBGP sessions needed!)       │
  └─────────────────────────────────────────┘

With Confederations:
  ┌──────────────────────────────────────────────────────┐
  │    Confederation AS 65000 (visible externally)       │
  │                                                      │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐     │
  │  │ Sub-AS   │←eBGP│ Sub-AS   │←eBGP│ Sub-AS   │     │
  │  │ 65001    │    │ 65002    │    │ 65003    │     │
  │  │          │    │          │    │          │     │
  │  │ R1 ←→ R2 │    │ R3 ←→ R4 │    │ R5 ←→ R6 │     │
  │  │   iBGP   │    │   iBGP   │    │   iBGP   │     │
  │  └──────────┘    └──────────┘    └──────────┘     │
  └──────────────────────────────────────────────────────┘
```

#### How Confederations Work

**Configuration Example:**

```
AS 65000 divided into 3 sub-ASes: 65001, 65002, 65003

Router in Sub-AS 65001:
  router bgp 65001
    bgp confederation identifier 65000
    bgp confederation peers 65002 65003
    
  neighbor 10.0.1.2 remote-as 65001  ← iBGP within sub-AS
  neighbor 10.0.2.1 remote-as 65002  ← confederation eBGP
  neighbor 10.0.3.1 remote-as 65003  ← confederation eBGP
```

**Key Properties:**

1. **External View:** Outside world sees only AS 65000
2. **Internal View:** Subdivided into smaller iBGP domains
3. **eBGP Between Sub-ASes:** Use eBGP rules (easier than iBGP)
4. **No Full Mesh:** Only full mesh within each sub-AS

#### AS_PATH Handling

```
Route advertised within confederation:

Internal AS_PATH: [65001, 65002, 65003]
  (Confederation path - not visible externally)

External AS_PATH: [65000]
  (Confederation identifier - what peers see)

Example:
  Router in AS 65001 advertises 10.1.1.0/24
  Passes through AS 65002, AS 65003
  
  Internal view: AS_PATH = (65001, 65002, 65003) 10.1.1.0/24
  External view: AS_PATH = (65000) 10.1.1.0/24
  
  External peers see single AS!
```

#### Loop Prevention

```
Uses AS_PATH for loop prevention (like eBGP):

Router in AS 65001 receives route with AS_PATH containing 65001
  → Reject (loop detected)
  
Simpler than route reflector's Cluster ID mechanism!
```

### Confederations vs Route Reflectors

```
┌────────────────────────┬──────────────────┬──────────────────┐
│ Aspect                 │ Confederations   │ Route Reflectors │
├────────────────────────┼──────────────────┼──────────────────┤
│ Complexity             │ Higher           │ Lower            │
│ Configuration          │ More complex     │ Simpler          │
│ Session Type           │ eBGP (between    │ iBGP             │
│                        │ sub-ASes)        │                  │
│ Loop Prevention        │ AS_PATH          │ Cluster ID,      │
│                        │                  │ Originator ID    │
│ Path Selection         │ More predictable │ Can be complex   │
│ Hierarchical Design    │ Natural          │ Requires care    │
│ Deployment Ease        │ Harder (change   │ Easier (add RR   │
│                        │ all routers)     │ nodes)           │
│ Industry Preference    │ Less common      │ More common      │
│ Kubernetes Use         │ Rare             │ Standard (Calico)│
└────────────────────────┴──────────────────┴──────────────────┘
```

#### Scaling Comparison

**1000 nodes, 10 sub-ASes of 100 nodes each:**

```
Confederations:
  - Within each sub-AS: 100 nodes × 99 peers = 9,900 sessions per sub-AS
  - Total within sub-ASes: 10 × 4,950 sessions = 49,500
  - Between sub-ASes: Full mesh of 10 = 45 sessions
  - Total: 49,545 sessions
  
Route Reflectors (2 per cluster):
  - 1000 nodes × 2 RRs = 2,000 client sessions
  - RR-to-RR: 1 session
  - Total: 2,001 sessions

Route Reflectors win massively for scaling!
```

#### When to Use Confederations

**Use Confederations when:**
- You have clear organizational boundaries
  - Example: Different data centers, each with own team
- You want predictable path selection
- You're already using eBGP and comfortable with it
- You need administrative boundaries within AS

**Example: Multi-datacenter company**
```
Company AS 65000:
  - DC1: Sub-AS 65001 (Network team A)
  - DC2: Sub-AS 65002 (Network team B)
  - DC3: Sub-AS 65003 (Network team C)

Each DC team manages their sub-AS independently
Use confederation eBGP between DCs
External peers see only AS 65000
```

**Use Route Reflectors when:**
- Single administrative domain
- Simpler deployment needed
- Kubernetes/cloud environment
- Want easy scaling without restructuring
- Industry standard approach preferred

---

## How Communities and Route Reflectors Work Together

While they solve different problems, they're often used together:

### Example: Route Reflector with Traffic Engineering

```
Kubernetes cluster with Calico:

Setup:
  - Route Reflectors: RR1, RR2
  - Nodes: N1, N2, ... N1000
  - Each node peers with both RRs

Use Communities for Policy:

Node N1 advertises routes with communities:
  10.244.1.0/24 community 64512:100  ← "High priority traffic"
  10.244.2.0/24 community 64512:200  ← "Best effort traffic"

Route Reflectors see communities and apply policy:
  Community 64512:100 → Set LOCAL_PREF = 200
  Community 64512:200 → Set LOCAL_PREF = 100

Result:
  - RRs reflect routes to all nodes (solving scaling)
  - Nodes prefer high-priority routes (via community tags)
  - Best of both worlds!
```

### Example: Multi-tenant with Security Policies

```
Multi-tenant Kubernetes:

Tenant isolation using communities:
  Tenant A pods: Routes tagged 64512:1000
  Tenant B pods: Routes tagged 64512:2000
  Shared services: Routes tagged 64512:9999

Route Reflector policy:
  if route has community 64512:1000:
      only advertise to nodes with tenant-a label
  if route has community 64512:2000:
      only advertise to nodes with tenant-b label
  if route has community 64512:9999:
      advertise to all nodes

Network isolation without separate clusters!
```

---

## Large Communities (RFC 8092)

### The Problem with Standard Communities

Standard communities are 32 bits (AS:Value), limiting flexibility:

```
AS 65000 wants to encode:
  - Customer ID (16 bits) - up to 65,535 customers
  - Service Type (16 bits)
  - QoS Level (8 bits)
  - Geographic Region (8 bits)

Can't fit in 32 bits!
```

### Large Communities Solution

```
Large Community: 96 bits (12 bytes)
  ┌─────────────┬─────────────┬─────────────┐
  │ Global Admin│ Local Data 1│ Local Data 2│
  │  (32 bits)  │  (32 bits)  │  (32 bits)  │
  └─────────────┴─────────────┴─────────────┘

Example: 65000:100:200
  Global: 65000 (AS number or private identifier)
  LD1: 100 (customer ID)
  LD2: 200 (service type)

More Examples:
  65000:1234:5 = Customer 1234, Gold service
  65000:1234:1 = Customer 1234, Bronze service
  65000:5678:10 = Customer 5678, Geographic region 10
```

### Large Communities in Practice

```
Cloud provider example:

Customer 12345 wants to control routing:
  - Prefer region us-west
  - Use tier-1 transit
  - Enable DDoS protection

Customer advertises route with large communities:
  203.0.113.0/24 large-community 65000:12345:1  ← Customer ID:Region West
  203.0.113.0/24 large-community 65000:100:1    ← Tier 1 transit
  203.0.113.0/24 large-community 65000:999:1    ← DDoS protection on

Provider applies policies based on large communities
Much more expressive than 32-bit communities!
```

---

## Summary Table

```
┌──────────────────────┬───────────────────────────────────────┬──────────────────────┐
│ BGP Feature          │ Problem Solved                        │ Use Case             │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ Communities          │ Route policy & traffic engineering    │ Tag routes for       │
│ (Standard/Large)     │                                       │ filtering, QoS,      │
│                      │                                       │ traffic control      │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ Route Reflectors     │ iBGP full-mesh scaling                │ Scale to 1000s of    │
│                      │                                       │ nodes without full   │
│                      │                                       │ mesh                 │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ Confederations       │ iBGP full-mesh scaling (alternative)  │ Multi-admin domain,  │
│                      │                                       │ clear org boundaries │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ AS_PATH Prepending   │ Make paths less attractive            │ Traffic engineering  │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ LOCAL_PREF           │ Control outbound traffic preference   │ Local routing policy │
├──────────────────────┼───────────────────────────────────────┼──────────────────────┤
│ MED (Multi-Exit      │ Influence inbound traffic from peers  │ Multi-homed networks │
│ Discriminator)       │                                       │                      │
└──────────────────────┴───────────────────────────────────────┴──────────────────────┘
```

---

## Real-World Example: ISP Using All Three

```
Large ISP AS 65000:
  - 5000 routers globally
  - Multiple data centers
  - Thousands of customers

Solution Stack:

1. BGP Confederations for administrative boundaries:
   - North America: Sub-AS 65001
   - Europe: Sub-AS 65002
   - Asia: Sub-AS 65003
   - Each region: 200-500 routers

2. Route Reflectors within each sub-AS:
   - NA: 2 route reflectors for 500 routers
   - EU: 2 route reflectors for 400 routers
   - Asia: 2 route reflectors for 300 routers

3. Communities for customer policy:
   - 65000:100:X = Customer X, bronze tier
   - 65000:200:X = Customer X, silver tier
   - 65000:300:X = Customer X, gold tier
   
   Policies based on tier:
     Bronze: Standard routing, rate-limited DDoS protection
     Silver: Priority routing, enhanced DDoS protection
     Gold: Optimized routing, full DDoS protection

Result:
  - Scales to thousands of routers
  - Clear administrative boundaries
  - Flexible customer policies
  - Manageable complexity
```

---

## Key Takeaway

**Communities = Route metadata/tags for policy**
  → Doesn't reduce BGP sessions
  → Adds intelligence to routing decisions

**Route Reflectors = Topology optimization**
  → Reduces BGP sessions from O(N²) to O(N)
  → Solves scaling problem

**Confederations = Alternative topology optimization**
  → Also reduces sessions but with different tradeoffs
  → Less common than route reflectors in modern networks

They solve **different problems** and are often used **together** for powerful, scalable routing!

---

## Hands-On Resources

> Want more? This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all networking and storage topics, see:
> **→ [Complete Networking & Storage Learning Resources](../../02_intermediate/00_NETWORKING_RESOURCES.md)**

**BGP Route Reflectors:**
- [BGP Route Reflector Tutorial](https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/217992-understand-bgp-route-reflector.html) - Cisco comprehensive guide
- [Route Reflector Design and Best Practices](https://www.juniper.net/documentation/us/en/software/junos/bgp/topics/topic-map/route-reflection.html) - Juniper design guide

**BGP Configuration Guides:**
- [Cisco BGP Configuration Guide](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_bgp/configuration/xe-16/irg-xe-16-book.html) - Comprehensive Cisco BGP reference
- [Juniper BGP User Guide](https://www.juniper.net/documentation/us/en/software/junos/bgp/index.html) - Juniper BGP documentation and examples
