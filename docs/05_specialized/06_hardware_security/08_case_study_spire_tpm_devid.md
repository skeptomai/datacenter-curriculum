---
level: specialized
estimated_time: 50 min
prerequisites:
  - 05_specialized/06_hardware_security/02_key_hierarchy_and_provisioning.md
  - 05_specialized/06_hardware_security/03_sealing_attestation_pcrs.md
  - 05_specialized/06_hardware_security/04_vendor_landscape_dtpm_vs_ftpm.md
next_recommended: []
tags: [tpm, spire, spiffe, devid, credential-activation, case-study, zero-trust]
---

# Case Study: TPM-Backed Node Identity with SPIRE/SPIFFE

## Learning Objectives

After reading this document, you will understand:
- A real, running production pattern that uses TPM credential activation for something
  other than boot-state attestation: proving *device identity*
- How a six-node homelab Kubernetes cluster's mixed TPM vendor hardware (Infineon and
  Nuvoton) shows up as genuine, measurable operational behavior — not just a spec-sheet
  difference
- Why "the server trusts the agent via hardware" and "the agent trusts the server via
  hardware" turned out to be two separate engineering problems, not one
- The honest limits of this design: which parts are hardware-rooted and which still rely
  on policy rather than cryptographic proof

## Prerequisites

Before reading this, you should understand:
- [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md) — EK, AK, credential activation
- [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md) — the quoting pattern this case study deliberately does *not* use
- [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md) — dTPM/fTPM and capability variance

---

## 1. The Cluster

Six commodity mini-PCs running Kubernetes (k3s): three HP Elite Mini 800 G9 units and
three similarly-specced i5 machines. All six carry a genuine TPM 2.0 chip. Querying the
hardware directly (`tpm2_getcap properties-fixed`) across the fleet turned up something
the procurement paperwork didn't mention:

| Node | Manufacturer | Chip | Firmware |
|---|---|---|---|
| Node A | Nuvoton (`0x4E544300`) | NPCT75x | 7.0.2 |
| Node B | Nuvoton (`0x4E544300`) | NPCT75x | 7.0.2 |
| Node C | Nuvoton (`0x4E544300`) | NPCT75x | 7.0.2 |
| Node D | Nuvoton (`0x4E544300`) | NPCT75x | 7.0.2 |
| Node E | Infineon (`0x49465800`) | SLB9672 | 15.0.22 |
| Node F | Infineon (`0x49465800`) | SLB9672 | 15.0.22 |

The exact same HP Elite Mini model shipped with **either** chip depending on production
lot — nobody chose this, it's just what came in the box. This is the "within a single
hardware SKU, the TPM vendor isn't fixed" variance described abstractly in
[TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md), observed directly on real
purchased hardware rather than read off a spec sheet.

Both NPCT75x and SLB9672 are **discrete TPM chips** — separate silicon from the CPU,
communicating over the platform's TPM bus — not firmware TPMs. Section 7 below shows why
confirming this distinction mattered in practice, not just in theory.

---

## 2. The Problem Being Solved: Hardware-Rooted Node Trust

This cluster runs **SPIRE** (the reference implementation of **SPIFFE**, the Secure
Production Identity Framework For Everyone) to issue short-lived cryptographic identities
to workloads, instead of hand-distributing TLS certificates or shared secrets. Before any
of that can happen, though, the SPIRE server has to answer a prior question: **is the
agent asking to join really running on hardware I enrolled, and not on an attacker's
machine impersonating it?** This is **node attestation**, and it's a different problem
from everything covered so far in this section — it isn't about boot state, it's about
device identity.

This cluster's node attestation evolved through two designs:

| | Trust root | What a compromised control plane can do |
|---|---|---|
| **Original design (`k8s_psat`)** | Kubernetes' own TokenReview API validates a projected service account token | A compromised Kubernetes control plane can forge valid tokens — the trust root *is* Kubernetes |
| **Current design (`tpm_devid`)** | The node's physical TPM, via credential activation | Nothing — a compromised control plane cannot forge possession of a physical chip it doesn't hold |

The switch to TPM-based attestation moved the trust root out of software entirely,
exactly the motivation described in
[TPM Fundamentals](01_tpm_fundamentals.md) — except applied here to "which machine is
this" rather than "what did this machine boot."

---

## 3. A New Application of a Familiar Primitive: Credential Activation for Identity, Not Boot State

[Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md) introduced
credential activation (`TPM2_MakeCredential` / `TPM2_ActivateCredential`) as the mechanism
that proves an **Attestation Key** is genuinely co-resident with a real **Endorsement
Key**, so a later PCR quote can be trusted. This cluster reuses the exact same underlying
mechanism for a structurally different purpose.

Instead of an Attestation Key used to sign PCR quotes, each node has a **DevID key** — a
key pair defined by **IEEE 802.1AR** ("Secure Device Identity"), generated inside the
node's TPM by the cluster administrator at enrollment time (not at manufacturing — this
is specific to this cluster's identity scheme), paired with a certificate signed by a
private CA the administrator controls. The DevID key's job is simply "prove which
enrolled node this is," every time the agent attests — there is no PCR quoting involved
at all.

```
Per node (once, at enrollment, from an out-of-band admin host — never over the
cluster network):
  1. Generate a new key pair inside this node's TPM (the DevID key)
  2. Build a certificate signing request, signed by the TPM internally
  3. Sign that CSR with the cluster's private DevID CA (kept entirely off the
     cluster — not in Git, not in Kubernetes)
  4. Install the signed certificate + TPM key blobs on the node
```

**Attestation, every time the agent starts, is a two-part proof:**

```
Agent                                    SPIRE Server
─────                                    ────────────
1. Load DevID key into this node's TPM
2. Sign a server-issued nonce with
   the DevID private key
                                     →    3. Verify DevID cert chains to the
                                            cluster's DevID CA
                                          4. Verify DevID cert's EK chains to a
                                            genuine manufacturer CA
                                            (Nuvoton / Infineon)
                                          5. MakeCredential: encrypt a random
                                            secret to this node's EK public key
                                     ←    6. Send the encrypted blob
7. ActivateCredential(EK, DevID key,
   blob) — TPM decrypts ONLY if:
     a) this TPM holds the matching
        EK private key, AND
     b) the DevID key is loaded in
        THIS SAME TPM right now
8. Return the decrypted secret
                                     →    9. Secret matches → both proofs held
                                            simultaneously → issue Node identity
```

**Why this is stronger than checking the DevID signature alone:** signature verification
alone (step 1–4) only proves *somebody* holds the DevID private key — it doesn't prove
*where*. An attacker who somehow copied the DevID key blob off the disk still couldn't
pass step 7, because a TPM-bound key blob can only be loaded and used inside the specific
physical chip that created it (the same `fixedTPM` property from
[TPM Fundamentals](01_tpm_fundamentals.md)). Credential activation forces the DevID key
and the EK to both be live, loaded, and usable in the *same* chip, at the *same* moment —
which is the one thing a stolen file can never reproduce.

**The key insight for this document:** measured boot (covered earlier in this section)
answers "what software booted on this machine." This mechanism answers an entirely
orthogonal question: "is this the same physical, enrolled machine" — regardless of what
it's currently running. A cluster could use both simultaneously (verify the hardware
*and* verify the boot state) and gain two independent, complementary guarantees. This
cluster currently implements only the hardware-identity half.

---

## 4. Trust Has to Be Engineered in Both Directions

The design above makes the **server's trust in the agent** hardware-rooted. It does
**not** automatically make the **agent's trust in the server** hardware-rooted — that
turned out to be a separate problem the team had to solve deliberately, and it's worth
walking through because the gap is easy to miss.

**The circularity:** before an agent can even attempt attestation, it needs to trust the
server's TLS certificate, which means it needs the server's CA bundle. SPIRE's
out-of-the-box options for delivering that bundle (a Kubernetes ConfigMap, a pre-placed
file, a fetched URL) all reduce to: "the agent trusts whatever Kubernetes — or whoever
controls the delivery channel — handed it." A rogue actor who could substitute that
bundle would be indistinguishable to the agent from the real server; the agent has no
independent way to check.

**The fix applied here:** a *second*, entirely separate TPM key — a bundle-signing key,
living only on the SPIRE server's own node, never reused for anything else — signs the
trust bundle. Every agent node is given that key's **public** half out-of-band, through
the exact same direct-provisioning channel used to install each node's DevID material,
before SPIRE ever starts. An init container on every agent verifies the server's signed
bundle against that public key before the SPIRE agent is even allowed to launch.

```
Resulting posture:

  Direction                  | Trust root
  ----------------------------|---------------------------------------
  Server trusts agent         | Agent's TPM (credential activation)
  Agent trusts server         | Server's TPM (signature over the bundle)
  Both public keys delivered  | An out-of-band channel Kubernetes cannot
  to every node               | influence — not a Secret, not a ConfigMap
```

**Why a separate key, not the DevID key reused:** this mirrors the same reasoning from
[Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md) for not reusing
the Endorsement Key as the Attestation Key — a key used for one specific, narrow purpose
is easier to reason about and audit than one key quietly pressed into service for
several unrelated jobs.

**What this design is honest about not covering:** the out-of-band provisioning channel
itself — a human with direct administrative access to each physical machine — is still
the ultimate root of trust for the *whole* scheme. TPM hardware proves "this is the same
chip we enrolled"; it cannot prove the enrollment itself was done correctly or by the
right person. Every hardware-rooted trust chain has to start somewhere outside hardware,
and naming that starting point explicitly — rather than letting "it's all hardware
secured" become an unexamined assumption — is itself a useful habit this case study
models.

---

## 5. Vendor Variance Shows Up as a Real Bug, Not a Spec-Sheet Footnote

[TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md) claimed that capability and
performance vary even within compliant TPM 2.0 hardware. Here is exactly how that played
out operationally on this cluster.

**Symptom:** five of the six nodes attested to SPIRE in 11–34 seconds after a restart.
One Infineon-chip node consistently took **~76 seconds** — still within the configured
liveness-probe window, but a glaring outlier.

**Root cause, traced with kernel-level syscall tracing on the TPM device file:** the
SPIRE node-attestor plugin calls `TPM2_CreatePrimary` **three separate times** per
attestation attempt (once each to load the DevID key, create a working key, and load
it). On the slow node, **each** `TPM2_CreatePrimary` call blocked for **~24 seconds**
inside the kernel — genuinely waiting on the chip, not a software timeout or retry. That
single command generates a fresh 2048-bit RSA key entirely on-chip, and this particular
silicon took 24 seconds to do it. A second node with the identical chip model and
firmware version took only ~10 seconds per call — same part number, real-world
performance variance between individual units or production batches.

```
3 calls × 24s  =  ~72s of the observed ~76s delay — confirmed exactly by trace data,
not estimated.
```

**The fix:** since all three `CreatePrimary` calls used identical parameters, they were
provably generating the *same* deterministic key three times over (recall from
[Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md): TPM 2.0 primary
keys are deterministic — same hierarchy, same template, same key, every time). A patch
to reuse one key across all three steps cut attestation time from ~76s to ~28s on the
affected node — one slow 24-second operation instead of three.

**Why this belongs in this document:** the slowness wasn't a software bug pretending to
be a hardware limitation — it was genuinely the chip's own on-die RSA key-generation
circuitry taking that long, confirmed by watching the actual blocking syscall. This is
the sharpest possible illustration of
[TPM Fundamentals](01_tpm_fundamentals.md)'s claim that a TPM is dedicated silicon with
real physical performance characteristics, not a software abstraction layer — those
characteristics can and do vary enough, between individual chips of the identical model
and firmware revision, to be the dominant factor in a real production timing bug.

---

## 6. Endorsement Key Certificates Don't Last Forever — Now What?

Pulling the manufacturer-issued EK certificates from all six chips turned up expiry dates
ranging from 2037 to 2043, split by vendor and even by production batch of the identical
chip model. [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md)
described the EK certificate as the factory-issued proof that an EK belongs to genuine
hardware — but that certificate is a normal X.509 cert, and normal X.509 certs expire.

**What does *not* happen at expiry:** the TPM chip keeps working exactly as before. The
EK key pair itself has no expiry — only the manufacturer's signed vouching document does.

**What actually changes:** the cryptographic chain "I trust this node because its EK
cert chains to [Manufacturer]'s CA" goes stale. The practical fallback, standard across
real deployments and not specific to this cluster, is **EK public-key fingerprinting**:
record each node's EK public key once, during enrollment, and afterward trust "this is
the same hardware that presented this specific public key" rather than "the manufacturer
currently vouches for this." You lose the manufacturer-provenance guarantee but keep the
cryptographic identity guarantee — the same public key can never belong to two different
physical chips. A pragmatic cluster operator can enroll fingerprints alongside
cert-chain validation well before expiry, turning a future scramble into a quiet config
change.

---

## Quick Reference

| Concept from earlier documents | How it shows up in this case study |
|---|---|
| EK (factory-provisioned identity) | Used only during the credential activation challenge, never for day-to-day signing |
| Credential activation | Proves the DevID key and EK are co-resident — same primitive as AK certification, applied to device identity instead of PCR quoting |
| `fixedTPM` non-exportability | What makes a stolen DevID key blob useless without the physical chip |
| Vendor/model variance | A real ~24s-per-call RSA keygen difference between two units of the identical chip model, confirmed by syscall tracing |
| "Trust has a root somewhere" | The out-of-band provisioning channel — a human with physical/administrative access — is the explicit, named root of this entire scheme |

---

## What You've Learned

✅ A real cluster's TPM hardware inventory varies by vendor even within one purchased SKU, exactly as [Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md) predicted
✅ Credential activation is a general primitive — this case study applies it to device identity, not boot-state quoting, and the distinction matters
✅ Hardware-rooted trust in one direction (server↔agent) does not automatically cover the other direction — both halves had to be engineered, with separate keys
✅ A measured ~24-second-per-call hardware latency difference between two units of the identical TPM chip model caused a real, debugged production timing issue
✅ Every hardware-rooted trust chain still has a named, non-hardware starting point — here, the out-of-band enrollment process itself

---

## Hands-On Resources

- **[SPIFFE / SPIRE project](https://spiffe.io/)** — the open-source implementation this case study is built on
- **[IEEE 802.1AR Secure Device Identity](https://1.ieee802.org/security/802-1ar/)** — the DevID standard
- **[go-tpm-tools](https://github.com/google/go-tpm-tools)** — the library underlying SPIRE's `tpm_devid` node attestor
- **[spiffe/spire-server-attestor-tpm](https://github.com/spiffe/spire-server-attestor-tpm)** — the project behind the server-side TPM bundle-signing pattern described in Section 4

---

## Next Steps

**Related topics:**
→ [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md)
→ [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)
→ [Measured Boot](06_measured_boot.md) — the complementary guarantee this cluster does not yet combine with node identity
