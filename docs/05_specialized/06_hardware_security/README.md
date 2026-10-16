# Hardware Security & Trusted Boot

**Hardware roots of trust, from the silicon up through the boot chain (4–5 hours total)**

Seven documents building from "what is a TPM" through to the two complementary
mechanisms — measured boot and Secure Boot — that actually use it in a running
system.

---

## The Learning Sequence

### 1. [TPM Fundamentals](01_tpm_fundamentals.md) 🎯 START HERE
**Time:** 30 minutes

**The Question:** Why does secure key storage need a dedicated chip instead of just better encryption?

**What you'll learn:** What a TPM physically is, and why its command set having no "export the private key" operation is the real source of its guarantees.

---

### 2. [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md)
**Time:** 45 minutes | **Prerequisites:** Document #1

**The Question:** What key does a TPM come with from the factory, and where does an Attestation Key actually come from?

**What you'll learn:** Seeds vs. stored keys, the four hierarchies, the Endorsement Key, and why the Attestation Key is a separate, certified-but-disposable identity — never the EK itself.

---

### 3. [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md)
**Time:** 45 minutes | **Prerequisites:** Document #2

**The Question:** How does a TPM tie a secret's release to a specific boot state, and prove that state to someone else?

**What you'll learn:** PCR extend mechanics, seal/unseal, quoting with the AK, and what else lives in TPM NVRAM.

---

### 4. [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)
**Time:** 40 minutes | **Prerequisites:** Document #1

**The Question:** Is a TPM one-size-fits-all across vendors and models?

**What you'll learn:** Discrete vs. firmware vs. die-integrated TPMs, TPM 1.2 vs. 2.0, and real capability/certification variance even within "TPM 2.0 compliant" hardware.

---

### 5. [TPM in Practice](05_tpm_in_practice.md)
**Time:** 40 minutes | **Prerequisites:** Documents #3, #4

**The Question:** How does all of this show up in things you actually use?

**What you'll learn:** BitLocker/LUKS sealing, TPM-backed SSH keys, a full remote attestation walkthrough, and hands-on `tpm2-tools` commands.

---

### 6. [Measured Boot](06_measured_boot.md)
**Time:** 50 minutes | **Prerequisites:** Document #3

**The Question:** What actually stops someone from feeding the TPM a fake measurement?

**What you'll learn:** The "measure before execute" principle, the CRTM as the one link anchored in hardware instead of software trust, the full SRTM boot chain, and SRTM vs. DRTM.

---

### 7. [Secure Boot](07_secure_boot.md)
**Time:** 40 minutes | **Prerequisites:** Document #6

**The Question:** How is this different from (and complementary to) measured boot?

**What you'll learn:** The UEFI PK/KEK/db/dbx key hierarchy, shim + MOK for Linux, and a concrete rollback-attack example showing why production systems need both mechanisms.

---

## Navigation Tips

- Documents #1–#3 are the conceptual core — read them in order.
- Document #4 (vendor landscape) can be read any time after #1; it doesn't depend on #2/#3.
- Documents #5–#7 apply the concepts to real systems and can be read in any order after #3/#4.

---

**⏱️ Total Time:** ~4.5 hours
**📊 Depth:** 🔬 Specialized throughout
