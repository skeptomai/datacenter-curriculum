---
level: specialized
estimated_time: 90 min
prerequisites:
  - 05_specialized/03_serverless/02_firecracker_deep_dive.md
  - 02_intermediate/03_complete_virtualization/01_evolution_complete.md
next_recommended:
  - 05_specialized/04_cpu_memory/01_tlb_ept_explained.md
tags: [virtualization, firecracker, virtio, block, network, vsock]
---

# The Three virtio Devices in Firecracker

## Why Only 3 Devices?

**Serverless workloads need:**
- Network connectivity (HTTP requests/responses)
- Disk storage (code, dependencies, scratch space)
- Host communication (metrics, logs, control)

**That's it.**

No need for:
- ✗ Graphics (VGA) - headless workloads
- ✗ Audio - no multimedia
- ✗ USB - no peripherals
- ✗ PS/2 keyboard/mouse - no user interaction
- ✗ Serial/parallel ports - not needed
- ✗ Floppy/CD-ROM - legacy

---

## Part 1: virtio-net (Network Device)

### What It Does

Provides network connectivity to the guest VM.

```
Guest Application
    ↓ TCP/IP Stack
virtio-net Driver (Guest Kernel)
    ↓ virtqueue (shared memory)
Firecracker virtio-net Backend
    ↓ TAP device
Host Network Stack
    ↓
Physical NIC
```

---

### The virtio-net virtqueue Architecture

**Two queues (TX and RX):**

```
┌──────────────────────────────────────────────────┐
│             Guest Memory                         │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  TX Queue (Transmit - Guest → Host)        │ │
│  │                                            │ │
│  │  Descriptor Table:                         │ │
│  │  [0]: addr=0x10000, len=1514, flags=0     │ │
│  │  [1]: addr=0x11000, len=1514, flags=0     │ │
│  │  [2]: addr=0x12000, len=1514, flags=0     │ │
│  │  ...                                       │ │
│  │                                            │ │
│  │  Available Ring (Guest writes):            │ │
│  │  idx=3, [0,1,2]                            │ │
│  │                                            │ │
│  │  Used Ring (Host writes):                  │ │
│  │  idx=2, [(0,1514),(1,1514)]               │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  RX Queue (Receive - Host → Guest)         │ │
│  │                                            │ │
│  │  Descriptor Table:                         │ │
│  │  [0]: addr=0x20000, len=2048, flags=WRITE │ │
│  │  [1]: addr=0x22000, len=2048, flags=WRITE │ │
│  │  [2]: addr=0x24000, len=2048, flags=WRITE │ │
│  │  ...                                       │ │
│  │                                            │ │
│  │  Available Ring (Guest writes - buffers): │ │
│  │  idx=10, [0,1,2,3,4,5,6,7,8,9]            │ │
│  │                                            │ │
│  │  Used Ring (Host writes - packets recvd): │ │
│  │  idx=5, [(0,1500),(1,800),(2,1200),...]   │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

### virtio-net Packet Transmission (TX)

**Step-by-step packet send:**

```
Step 1: Application sends data
────────────────────────────────
Application:
  write(sock_fd, data, 1500);

TCP/IP Stack (Guest Kernel):
  - Build TCP segment
  - Build IP packet
  - Calculate checksums
  - Determine output interface: eth0 (virtio-net)
  - Pass to virtio-net driver

Step 2: virtio-net driver queues packet
────────────────────────────────────────
virtio-net driver (Guest):
  1. Allocate descriptor: desc_idx = 5
  
  2. Fill descriptor:
     desc[5].addr = virt_to_phys(skb->data)  // Guest physical address
     desc[5].len = 1500
     desc[5].flags = 0  // Read-only (guest → host)
     desc[5].next = -1  // No chaining
  
  3. Add to available ring:
     avail_ring.ring[avail_ring.idx % QUEUE_SIZE] = 5
     avail_ring.idx++
  
  4. Memory barrier (ensure writes visible):
     wmb()
  
  5. Kick backend (notify Firecracker):
     // Option A: I/O port write (causes VM exit)
     outw(VIRTIO_PCI_QUEUE_NOTIFY, queue_id);
     
     // Option B: MMIO write (modern, causes VM exit)
     writel(queue_id, notify_addr);

Step 3: VM Exit to Firecracker
───────────────────────────────
Guest writes to notification register
  ↓
CPU detects: MMIO write to virtio notify region
  ↓
VM Exit (reason: MMIO)
  ↓
KVM kernel: Save guest state, return to user space
  ↓
Firecracker: ioctl(KVM_RUN) returns
  ↓
Firecracker: Check exit reason
  exit_reason = KVM_EXIT_MMIO
  mmio_addr = virtio_net.notify_addr
  
Step 4: Firecracker processes TX queue
───────────────────────────────────────
Firecracker virtio-net backend:
  
  1. Read available ring:
     last_avail_idx = self.last_avail_idx;
     avail_idx = read_u16(&avail_ring.idx);
     
     while last_avail_idx != avail_idx {
       desc_idx = avail_ring.ring[last_avail_idx % QUEUE_SIZE];
       last_avail_idx++;
       
       // Process this descriptor
       process_tx_descriptor(desc_idx);
     }
  
  2. Read descriptor chain:
     desc = &descriptor_table[desc_idx];
     guest_addr = desc.addr;  // Guest physical address
     len = desc.len;          // 1500 bytes
  
  3. Map guest memory:
     // Firecracker has guest memory mapped
     host_addr = guest_mem_base + guest_addr;
     packet_data = *(u8*)host_addr;
  
  4. Copy packet to host buffer:
     memcpy(host_buffer, packet_data, len);
  
  5. Write to TAP device:
     write(tap_fd, host_buffer, len);
     // Packet goes to host network stack
  
  6. Mark descriptor as used:
     used_ring.ring[used_ring.idx % QUEUE_SIZE] = {
       id: desc_idx,
       len: len
     };
     used_ring.idx++;
  
  7. Inject interrupt (if guest wants one):
     if (!guest_disabled_interrupts) {
       ioctl(irqfd, KVM_IRQFD_ASSIGN, &irq_config);
     }

Step 5: Guest processes TX completion
──────────────────────────────────────
Guest receives interrupt:
  virtio_net_tx_interrupt_handler()
  
  1. Read used ring:
     last_used_idx = self.last_used_idx;
     used_idx = read_u16(&used_ring.idx);
     
     while last_used_idx != used_idx {
       used_elem = used_ring.ring[last_used_idx % QUEUE_SIZE];
       desc_idx = used_elem.id;
       
       // Free the transmitted packet
       free_skb(desc_idx);
       
       last_used_idx++;
     }
  
  2. If TX queue was full, wake up blocked senders
```

---

### virtio-net Packet Reception (RX)

**Guest pre-allocates receive buffers:**

```
Step 1: Guest provides empty RX buffers
───────────────────────────────────────
virtio-net driver initialization (Guest):
  
  for (i = 0; i < RX_QUEUE_SIZE; i++) {
    // Allocate 2KB buffer for incoming packet
    skb = alloc_skb(2048);
    
    // Fill descriptor
    desc[i].addr = virt_to_phys(skb->data);
    desc[i].len = 2048;
    desc[i].flags = VIRTQ_DESC_F_WRITE;  // Host can write here
    
    // Add to available ring
    avail_ring.ring[avail_ring.idx % QUEUE_SIZE] = i;
    avail_ring.idx++;
  }
  
  // Notify backend: "RX buffers ready"
  writel(RX_QUEUE_ID, notify_addr);

Step 2: Packet arrives at host
───────────────────────────────
Physical NIC → Host network stack → TAP device → read() returns packet

Firecracker event loop:
  poll([tap_fd, vcpu_fd, ...])
  // tap_fd becomes readable

Step 3: Firecracker fills RX buffer
────────────────────────────────────
Firecracker virtio-net RX handler:
  
  1. Read packet from TAP:
     len = read(tap_fd, packet_buffer, 2048);
     // len = 1500 (typical Ethernet frame)
  
  2. Get available RX buffer from guest:
     if avail_ring.idx == last_used_idx {
       // No RX buffers available!
       // Drop packet or queue for later
       return;
     }
     
     desc_idx = avail_ring.ring[last_used_idx % QUEUE_SIZE];
     last_used_idx++;
  
  3. Get descriptor:
     desc = descriptor_table[desc_idx];
     guest_addr = desc.addr;
     max_len = desc.len;  // 2048
     
     if (len > max_len) {
       // Packet too large, drop
       return;
     }
  
  4. Copy packet to guest memory:
     host_addr = guest_mem_base + guest_addr;
     memcpy(host_addr, packet_buffer, len);
  
  5. Mark buffer as used:
     used_ring.ring[used_ring.idx % QUEUE_SIZE] = {
       id: desc_idx,
       len: len  // Actual packet length
     };
     used_ring.idx++;
  
  6. Inject interrupt:
     ioctl(irqfd, KVM_IRQFD_ASSIGN, &irq_config);

Step 4: Guest processes received packet
────────────────────────────────────────
Guest receives RX interrupt:
  virtio_net_rx_interrupt_handler()
  
  1. Read used ring:
     while last_seen_used != used_ring.idx {
       used_elem = used_ring.ring[last_seen_used % QUEUE_SIZE];
       desc_idx = used_elem.id;
       packet_len = used_elem.len;
       
       // Get the skb we allocated earlier
       skb = get_skb_for_desc(desc_idx);
       skb->len = packet_len;
       
       // Pass to network stack
       netif_receive_skb(skb);
       
       last_seen_used++;
     }
  
  2. Replenish RX buffers:
     // Allocate new skbs and add to available ring
     for (i = 0; i < processed_count; i++) {
       new_skb = alloc_skb(2048);
       add_to_avail_ring(new_skb);
     }
```

---

### virtio-net Header

**Each packet has a virtio-net header:**

```c
struct virtio_net_hdr {
    u8  flags;          // Flags (checksum offload, etc.)
    u8  gso_type;       // GSO type
    u16 hdr_len;        // Header length
    u16 gso_size;       // GSO segment size
    u16 csum_start;     // Checksum start offset
    u16 csum_offset;    // Checksum offset
    u16 num_buffers;    // Number of buffers (for mergeable RX)
};

Packet in memory:
┌────────────────────┬───────────────────────────────┐
│ virtio_net_hdr     │  Ethernet Frame               │
│ (12 bytes)         │  (14 + IP + TCP + data)       │
└────────────────────┴───────────────────────────────┘
```

**Offload features:**

```
VIRTIO_NET_F_CSUM (bit 0):
  Guest doesn't calculate checksums
  Host/hardware does it
  Saves CPU cycles

VIRTIO_NET_F_GUEST_CSUM (bit 1):
  Host doesn't calculate checksums
  Guest does it on receive
  
VIRTIO_NET_F_GSO (bit 6):
  Guest can send large packets (>MTU)
  Host segments them (GSO = Generic Segmentation Offload)
  Reduces overhead for large transfers
```

---

## Part 2: virtio-blk (Block Device)

### What It Does

Provides block storage (disk) to the guest VM.

```
Guest Application
    ↓ Filesystem (ext4, xfs, etc.)
Block Layer (Guest Kernel)
    ↓
virtio-blk Driver
    ↓ virtqueue (shared memory)
Firecracker virtio-blk Backend
    ↓ pread/pwrite
Backing File (on host filesystem)
```

---

### virtio-blk Request Structure

```c
struct virtio_blk_req {
    u32 type;        // VIRTIO_BLK_T_IN (read) or VIRTIO_BLK_T_OUT (write)
    u32 reserved;
    u64 sector;      // Starting sector (512-byte units)
};

struct virtio_blk_resp {
    u8 status;       // VIRTIO_BLK_S_OK, VIRTIO_BLK_S_IOERR, etc.
};

Request layout in virtqueue:
┌──────────────────┐  Descriptor 0 (read-only by host)
│ virtio_blk_req   │  Contains: type, sector
│ type=OUT         │
│ sector=2048      │
└──────────────────┘
         ↓
┌──────────────────┐  Descriptor 1 (read-only by host for write, write-only for read)
│ Data Buffer      │  Contains: actual data
│ (4096 bytes)     │  For WRITE: data to write
└──────────────────┘  For READ: buffer for result
         ↓
┌──────────────────┐  Descriptor 2 (write-only by host)
│ virtio_blk_resp  │  Contains: status
│ status=OK        │
└──────────────────┘
```

---

### virtio-blk Read Request Flow

```
Step 1: Guest issues read
─────────────────────────
Guest filesystem:
  bio = bio_alloc();
  bio->bi_sector = 2048;     // Read from sector 2048
  bio->bi_size = 4096;       // 4KB
  submit_bio(READ, bio);

virtio-blk driver:
  1. Allocate 3 descriptors (for request header, data, status)
     
  2. Fill request header:
     req = kmalloc(sizeof(virtio_blk_req));
     req->type = VIRTIO_BLK_T_IN;  // Read
     req->sector = 2048;
     
     desc[0].addr = virt_to_phys(req);
     desc[0].len = sizeof(virtio_blk_req);
     desc[0].flags = 0;  // Read-only
     desc[0].next = 1;   // Chain to next descriptor
  
  3. Fill data buffer:
     data = bio_data(bio);  // 4KB buffer
     
     desc[1].addr = virt_to_phys(data);
     desc[1].len = 4096;
     desc[1].flags = VIRTQ_DESC_F_WRITE;  // Host writes here
     desc[1].next = 2;
  
  4. Fill status byte:
     status = kmalloc(1);
     
     desc[2].addr = virt_to_phys(status);
     desc[2].len = 1;
     desc[2].flags = VIRTQ_DESC_F_WRITE;  // Host writes status
     desc[2].next = -1;  // End of chain
  
  5. Add to available ring:
     avail_ring.ring[avail_ring.idx % QUEUE_SIZE] = 0;  // First desc
     avail_ring.idx++;
  
  6. Notify backend:
     writel(0, notify_addr);  // Causes VM exit

Step 2: Firecracker processes read
───────────────────────────────────
Firecracker virtio-blk backend:
  
  1. VM exit received, check available ring
     desc_idx = avail_ring.ring[last_avail_idx % QUEUE_SIZE];
  
  2. Walk descriptor chain:
     // Descriptor 0: Request header
     req_desc = &desc_table[desc_idx];
     req = (virtio_blk_req*)(guest_mem + req_desc.addr);
     
     type = req->type;      // VIRTIO_BLK_T_IN (read)
     sector = req->sector;  // 2048
     
     // Descriptor 1: Data buffer
     data_desc = &desc_table[req_desc.next];
     data_addr = guest_mem + data_desc.addr;
     data_len = data_desc.len;  // 4096
     
     // Descriptor 2: Status
     status_desc = &desc_table[data_desc.next];
     status_addr = guest_mem + status_desc.addr;
  
  3. Read from backing file:
     offset = sector * 512;  // 2048 * 512 = 1,048,576
     
     ret = pread(backing_file_fd, temp_buffer, data_len, offset);
     
     if (ret != data_len) {
       // I/O error
       *(u8*)status_addr = VIRTIO_BLK_S_IOERR;
     } else {
       // Success: copy to guest memory
       memcpy(data_addr, temp_buffer, data_len);
       *(u8*)status_addr = VIRTIO_BLK_S_OK;
     }
  
  4. Mark request complete:
     used_ring.ring[used_ring.idx % QUEUE_SIZE] = {
       id: desc_idx,
       len: sizeof(virtio_blk_req) + data_len + 1
     };
     used_ring.idx++;
  
  5. Inject interrupt:
     ioctl(irqfd, KVM_IRQFD_ASSIGN);

Step 3: Guest processes completion
───────────────────────────────────
virtio_blk interrupt handler:
  
  1. Read used ring:
     used_elem = used_ring.ring[last_used_idx % QUEUE_SIZE];
     desc_idx = used_elem.id;
  
  2. Check status:
     status = *(u8*)(desc[2].addr);
     if (status == VIRTIO_BLK_S_OK) {
       bio->bi_status = BLK_STS_OK;
       // Data is now in buffer, pass to filesystem
     } else {
       bio->bi_status = BLK_STS_IOERR;
     }
  
  3. Complete I/O:
     bio_endio(bio);  // Wake up waiting process
  
  4. Free descriptors:
     free_desc(desc_idx);
```

---

### virtio-blk Write Request Flow

```
Write is similar but data flows guest → host:

1. Guest fills:
   desc[0]: Request (type=OUT, sector=X)
   desc[1]: Data to write (flags=0, read-only by host)
   desc[2]: Status (flags=WRITE, host writes result)

2. Firecracker:
   - Read request header
   - Read data from guest memory
   - pwrite() to backing file
   - Set status byte
   - Complete request

3. Guest:
   - Check status
   - Mark write complete
   - Filesystem continues
```

---

### virtio-blk Features

```
VIRTIO_BLK_F_SIZE_MAX (bit 1):
  Maximum size of any single segment
  Firecracker typically: 128KB

VIRTIO_BLK_F_SEG_MAX (bit 2):
  Maximum number of segments per request
  Allows scatter-gather I/O

VIRTIO_BLK_F_RO (bit 5):
  Device is read-only
  For immutable images (e.g., Lambda layers)

VIRTIO_BLK_F_FLUSH (bit 9):
  Support flush/sync operations
  Ensure data is on disk

VIRTIO_BLK_F_DISCARD (bit 13):
  Support discard/trim (SSD optimization)
```

---

## Part 3: virtio-vsock (Host-Guest Communication)

### What It Does

Provides a socket-like interface for communication between guest and host.

**Use cases in Firecracker:**
- Logging (guest → host)
- Metrics (guest → host)
- Configuration (host → guest)
- Control commands
- Avoid network for internal communication

---

### vsock vs Network

```
Using virtio-net for host-guest communication:
  Guest → TCP/IP stack → virtio-net → TAP → Host network stack → App
  
  Problems:
  - Full TCP/IP overhead
  - Uses IP addresses/ports
  - Firewall rules needed
  - More complex

Using virtio-vsock:
  Guest → vsock API → virtqueue → Firecracker → App
  
  Benefits:
  - Simpler (no TCP/IP)
  - Direct guest-host channel
  - More efficient
  - Purpose-built for host-guest
```

---

### vsock Addressing

**Instead of IP:port, uses CID:port:**

```
CID (Context ID):
  - VMADDR_CID_ANY = 0xFFFFFFFF (any)
  - VMADDR_CID_HYPERVISOR = 0 (reserved)
  - VMADDR_CID_RESERVED = 1 (reserved)
  - VMADDR_CID_HOST = 2 (the host)
  - VM CIDs: 3+ (each VM gets unique CID)

Port: 32-bit port number (like TCP)

Example:
  Guest CID: 42
  Host CID: 2
  
  Guest connects to: (CID=2, Port=1234)
  Host connects to: (CID=42, Port=5678)
```

---

### vsock Socket API (Guest)

```c
// Guest application
#include <linux/vm_sockets.h>

// Create vsock socket
int sock = socket(AF_VSOCK, SOCK_STREAM, 0);

// Connect to host on port 1234
struct sockaddr_vm addr = {
    .svm_family = AF_VSOCK,
    .svm_cid = VMADDR_CID_HOST,  // 2
    .svm_port = 1234
};
connect(sock, (struct sockaddr*)&addr, sizeof(addr));

// Send data
write(sock, "Hello host!", 11);

// Receive data
read(sock, buffer, 1024);

close(sock);
```

---

### vsock Socket API (Host)

```c
// Firecracker or host application
#include <linux/vm_sockets.h>

// Create vsock socket
int sock = socket(AF_VSOCK, SOCK_STREAM, 0);

// Listen on port 1234 for any VM
struct sockaddr_vm addr = {
    .svm_family = AF_VSOCK,
    .svm_cid = VMADDR_CID_ANY,  // Accept from any VM
    .svm_port = 1234
};
bind(sock, (struct sockaddr*)&addr, sizeof(addr));
listen(sock, 5);

// Accept connection
struct sockaddr_vm guest_addr;
int client = accept(sock, (struct sockaddr*)&guest_addr, &len);

printf("Connection from VM CID %u\n", guest_addr.svm_cid);

// Read/write like normal socket
read(client, buffer, 1024);
write(client, "Hello VM!", 9);

close(client);
```

---

### virtio-vsock Packet Structure

```c
struct virtio_vsock_hdr {
    u64 src_cid;      // Source CID
    u64 dst_cid;      // Destination CID
    u32 src_port;     // Source port
    u32 dst_port;     // Destination port
    u32 len;          // Payload length
    u16 type;         // STREAM or DGRAM
    u16 op;           // Operation (see below)
    u32 flags;        // Flags
    u32 buf_alloc;    // Buffer space available at receiver
    u32 fwd_cnt;      // Bytes forwarded to application
};

Operations (op field):
  VIRTIO_VSOCK_OP_INVALID = 0
  VIRTIO_VSOCK_OP_REQUEST = 1    // Connection request (SYN)
  VIRTIO_VSOCK_OP_RESPONSE = 2   // Connection accepted (SYN-ACK)
  VIRTIO_VSOCK_OP_RST = 3        // Reset connection
  VIRTIO_VSOCK_OP_SHUTDOWN = 4   // Graceful shutdown
  VIRTIO_VSOCK_OP_RW = 5         // Data packet
  VIRTIO_VSOCK_OP_CREDIT_UPDATE = 6  // Flow control update
  VIRTIO_VSOCK_OP_CREDIT_REQUEST = 7 // Request flow control info

Packet in memory:
┌──────────────────────┬─────────────────────┐
│ virtio_vsock_hdr     │  Payload            │
│ (44 bytes)           │  (variable length)  │
└──────────────────────┴─────────────────────┘
```

---

### vsock Connection Establishment

```
Guest initiates connection to host:

1. Guest: VIRTIO_VSOCK_OP_REQUEST
   ┌────────────────────────────────────┐
   │ src_cid: 42                        │
   │ dst_cid: 2 (host)                  │
   │ src_port: 54321 (ephemeral)        │
   │ dst_port: 1234                     │
   │ op: REQUEST                        │
   │ buf_alloc: 32768 (32KB buffer)     │
   └────────────────────────────────────┘
   
   → Add to TX virtqueue
   → Notify backend
   → VM exit to Firecracker

2. Firecracker processes REQUEST:
   - Check if anyone listening on port 1234
   - If yes: Create connection state
   - Send RESPONSE packet to RX queue
   - Inject interrupt

3. Host → Guest: VIRTIO_VSOCK_OP_RESPONSE
   ┌────────────────────────────────────┐
   │ src_cid: 2 (host)                  │
   │ dst_cid: 42                        │
   │ src_port: 1234                     │
   │ dst_port: 54321                    │
   │ op: RESPONSE                       │
   │ buf_alloc: 65536 (64KB buffer)     │
   └────────────────────────────────────┘
   
   → Guest receives interrupt
   → Connection established

4. Connection is now open, data can flow:
   - Guest can send: VIRTIO_VSOCK_OP_RW packets
   - Host can send: VIRTIO_VSOCK_OP_RW packets
```

---

### vsock Data Transfer with Flow Control

**Key feature:** Credit-based flow control (prevents buffer overflow)

```
Initial state:
  Guest buffer: 32KB free
  Host buffer: 64KB free

Guest sends data:
───────────────────
1. Guest wants to send 10KB:
   - Check host's advertised buffer: 64KB
   - 10KB < 64KB, OK to send
   
2. Guest sends RW packet:
   ┌──────────────────────────────────┐
   │ op: RW                           │
   │ len: 10240 (10KB)                │
   │ buf_alloc: 32768 (my RX buffer)  │
   │ fwd_cnt: 0 (nothing consumed yet)│
   │ [10KB payload]                   │
   └──────────────────────────────────┘

3. Host receives:
   - Copy 10KB to application socket buffer
   - Update state: 64KB - 10KB = 54KB free
   - Application reads data: fwd_cnt += bytes_read

4. Host sends credit update:
   ┌──────────────────────────────────┐
   │ op: CREDIT_UPDATE                │
   │ buf_alloc: 64000 (after app read)│
   │ fwd_cnt: 10240 (10KB consumed)   │
   └──────────────────────────────────┘
   
5. Guest updates view of host buffer:
   - Can send more data now

If buffer full:
──────────────
Guest wants to send 100KB but host only has 5KB buffer:
  - Guest must wait
  - Can request credit: VIRTIO_VSOCK_OP_CREDIT_REQUEST
  - Host responds with current buffer state
  - Guest waits until enough space available
```

---

### vsock in Firecracker - Real Usage

**Example: Sending logs from Lambda function to CloudWatch**

```
Lambda function (Guest):
  int log_fd = socket(AF_VSOCK, SOCK_STREAM, 0);
  struct sockaddr_vm addr = {
    .svm_cid = VMADDR_CID_HOST,
    .svm_port = 8000  // Firecracker log port
  };
  connect(log_fd, &addr, sizeof(addr));
  
  write(log_fd, log_message, len);

Firecracker (Host):
  - Accepts connection on vsock port 8000
  - Receives log messages
  - Forwards to CloudWatch Logs agent
  - No network overhead!
  
  Benefits:
  - Faster than HTTP over network
  - Lower latency
  - No IP address management
  - Isolated from network
```

---

## Comparison: The Three Devices

```
┌───────────────┬──────────────┬──────────────┬──────────────┐
│ Aspect        │ virtio-net   │ virtio-blk   │ virtio-vsock │
├───────────────┼──────────────┼──────────────┼──────────────┤
│ Purpose       │ Network I/O  │ Disk I/O     │ Host-guest   │
│               │              │              │ communication│
│               │              │              │              │
│ Queues        │ 2 (TX, RX)   │ 1 (requests) │ 3 (TX, RX,   │
│               │              │              │  event)      │
│               │              │              │              │
│ Typical       │ 1500 bytes   │ 4KB-128KB    │ Variable     │
│ Transfer Size │ (MTU)        │ (filesystem  │              │
│               │              │  blocks)     │              │
│               │              │              │              │
│ Latency       │ ~100 μs      │ ~200 μs      │ ~50 μs       │
│               │              │ (file I/O)   │              │
│               │              │              │              │
│ Throughput    │ 9+ Gbps      │ 2-3 GB/s     │ 5+ Gbps      │
│               │              │              │              │
│ Backend       │ TAP device   │ File         │ Unix socket  │
│               │              │ (pread/      │ or direct    │
│               │              │  pwrite)     │              │
│               │              │              │              │
│ Use Case      │ External     │ Persistent   │ Logs,        │
│               │ network      │ storage      │ metrics,     │
│               │              │              │ control      │
└───────────────┴──────────────┴──────────────┴──────────────┘
```

---

## Why These 3 Are Sufficient

**Lambda/Fargate workload needs:**

```
✓ Network (virtio-net):
  - Receive HTTP requests
  - Make API calls
  - Download dependencies
  - Send responses

✓ Storage (virtio-blk):
  - Store function code
  - Store /tmp scratch space
  - Store dependencies (node_modules, etc.)

✓ Communication (virtio-vsock):
  - Send logs to CloudWatch
  - Send metrics
  - Receive control commands
  - No need for network overhead

That's literally everything needed for serverless!
```

**What's NOT needed:**

```
✗ Graphics (VGA): No display
✗ Audio: No multimedia
✗ USB: No peripherals
✗ Serial ports: No console (use vsock instead)
✗ PS/2: No keyboard/mouse
✗ Multiple network cards: One is enough
✗ CD-ROM/floppy: Legacy
✗ PCI passthrough: Don't need bare-metal devices
```

---

## Performance Comparison

```
Benchmark: 1000 operations

virtio-net (packet send):
  QEMU emulated e1000: 100 ops/ms (much slower)
  Firecracker virtio-net: 10,000 ops/ms
  
virtio-blk (4KB read):
  QEMU emulated IDE: 5,000 ops/ms
  Firecracker virtio-blk: 20,000 ops/ms
  
virtio-vsock (message send):
  TCP over virtio-net: 8,000 ops/ms
  Firecracker virtio-vsock: 15,000 ops/ms

Why faster than QEMU?
  - Less code (simpler, less overhead)
  - Rust (zero-cost abstractions, safety)
  - Purpose-built (no extra features)
  - Optimized for serverless workloads
```

---

## Summary

**The three devices work together:**

```
┌────────────────────────────────────┐
│         Guest VM                   │
│                                    │
│  Application code                  │
│       ↓         ↓         ↓        │
│  Network    Filesystem   Logs      │
│       ↓         ↓         ↓        │
│  virtio-net virtio-blk virtio-vsock│
└───────┬─────────┬─────────┬────────┘
        │         │         │
    virtqueues (shared memory)
        │         │         │
┌───────▼─────────▼─────────▼────────┐
│      Firecracker (Rust)            │
│                                    │
│  virtio-net → TAP → Network        │
│  virtio-blk → pread/pwrite → File  │
│  virtio-vsock → socket → Host app  │
└────────────────────────────────────┘
```

**Key insights:**

1. **All use virtqueues** - Same shared memory ring mechanism
2. **All minimize VM exits** - Batching and interrupts
3. **All are simple** - Only features needed for serverless
4. **Together: Complete VM** - Network + storage + communication = everything needed

This is why Firecracker can boot in <125ms and use only 5MB RAM - it's JUST these three devices, nothing more.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for virtio and Firecracker's device implementation:**

- **[Virtio Specification (OASIS)](https://docs.oasis-open.org/virtio/virtio/v1.1/virtio-v1.1.html)** - Official virtio specification defining the standard
- **[Firecracker virtio Device Implementations](https://github.com/firecracker-microvm/firecracker/tree/main/src/devices/src/virtio)** - Source code for Firecracker's virtio-net, virtio-block, and virtio-vsock
