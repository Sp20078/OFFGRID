# ⚡ OFFGRID

### Communication doesn't stop when the Internet does.

<p align="center">
  <b>🚫 No Internet</b> &nbsp; • &nbsp;
  <b>🚫 No Cellular Network</b> &nbsp; • &nbsp;
  <b>✅ Still Connected</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge">
  <img src="https://img.shields.io/badge/Network-P2P%20Mesh-blue?style=for-the-badge">
  <img src="https://img.shields.io/badge/Communication-Offline-orange?style=for-the-badge">
  <img src="https://img.shields.io/badge/Files-Chunked%20Transfer-purple?style=for-the-badge">
  <img src="https://img.shields.io/badge/Tests-25%20Passing-brightgreen?style=for-the-badge">
</p>

---

## 🌐 The Problem

What happens when the Internet disappears?

A disaster strikes.

Cell towers go down.

Wi-Fi infrastructure fails.

Power becomes unreliable.

Suddenly, billions of connected devices become **isolated islands**.

Traditional communication systems depend heavily on centralized infrastructure.

**OFFGRID takes a different approach.**

---

# 🛰️ The OFFGRID Idea

OFFGRID turns nearby devices into a **self-organizing communication network**.

Instead of:

```text
        INTERNET
           │
           ▼
        SERVER
        /     \
       A       B

OFFGRID works like:

       📱 A
        │
        ▼
       📱 B
        │
        ▼
       📱 C
        │
        ▼
       📱 D
        │
        ▼
       📱 E

If A cannot directly reach E...

B, C and D become the network.

No central server.

No Internet.

Just devices helping devices.

🔥 What Makes OFFGRID Different?

OFFGRID isn't simply a chat application.

It is a resilient communication layer designed for environments where conventional connectivity cannot be trusted.

Core capabilities
Feature	Description
🕸️ P2P Mesh	Devices communicate through neighboring nodes
📨 Store & Forward	Messages wait until the destination becomes reachable
🔁 ACK & Retry	Failed deliveries can be retried
🛡️ Duplicate Detection	Prevents the same message from being processed repeatedly
⏳ TTL	Messages automatically expire after exceeding their lifetime
📦 Chunked Files	Large files are split into transferable chunks
🧩 File Reassembly	Chunks are reconstructed at the destination
📡 Route Discovery	Network layer determines viable paths
💓 Node Heartbeats	Detects unavailable devices
🚨 Failure Recovery	Network can adapt when nodes disappear
🧠 How It Works

Imagine five devices:

A ─── B ─── C ─── D ─── E

A wants to send:

"We need medical supplies."

But A cannot directly reach E.

Instead:

A
│
│ Message
▼
B
│
│ Forward
▼
C
│
│ Forward
▼
D
│
│ Forward
▼
E

Every device can potentially become a relay.

Now imagine C suddenly disappears:

A ─── B ─── ❌ C

             D ─── E

The network can attempt to find another available path.

The goal:

Connectivity should survive individual failures.

📦 Store-and-Forward

What if the destination is completely unavailable?

OFFGRID doesn't simply throw the message away.

        SEND
          │
          ▼
    Destination?
       /      \
     YES       NO
      │         │
      ▼         ▼
  DELIVER     STORE
                │
                ▼
          Wait for node
                │
                ▼
          Retry delivery

When the destination returns:

📨 Stored Message
       │
       ▼
 Destination Online
       │
       ▼
     DELIVERED ✅

This makes OFFGRID suitable for intermittent connectivity.

🔁 Reliable Message Delivery

Every message has its own identity.

Message
├── message_id
├── source
├── destination
├── payload
├── timestamp
├── TTL
├── sequence
└── status

Message lifecycle:

        ┌──────────┐
        │ PENDING  │
        └────┬─────┘
             │
             ▼
       ┌───────────┐
       │ FORWARDED │
       └─────┬─────┘
             │
             ▼
       ┌───────────┐
       │ DELIVERED │
       └───────────┘

             OR

       ┌──────────┐
       │ EXPIRED  │
       └──────────┘
🛡️ Duplicate Protection

Mesh networks can cause messages to travel through multiple paths.

Without protection:

A ── B ── D
 \       /
  C ────

The same message may arrive multiple times.

OFFGRID tracks message IDs:

Message ID: 8f31...

First arrival
      ↓
   ACCEPTED ✅

Second arrival
      ↓
   DUPLICATE 🛑

Third arrival
      ↓
   DUPLICATE 🛑

This prevents unnecessary processing and forwarding.

⏳ TTL — Preventing Zombie Messages

Every message has a Time-To-Live.

Example:

TTL = 5

After forwarding:

5 → 4 → 3 → 2 → 1 → 0

At:

TTL = 0

The message becomes:

EXPIRED ⛔

This prevents messages from circulating indefinitely.

📁 Large File Transfer

OFFGRID doesn't stop at text.

Large files are split into chunks.

📄 emergency_map.pdf

        ↓

┌──────────┐
│ Chunk 0  │
├──────────┤
│ Chunk 1  │
├──────────┤
│ Chunk 2  │
├──────────┤
│ Chunk 3  │
└──────────┘
        ↓
   NETWORK
        ↓
┌──────────┐
│ Chunk 0  │
│ Chunk 1  │
│ Chunk 2  │
│ Chunk 3  │
└──────────┘
        ↓
   REASSEMBLE
        ↓
📄 emergency_map.pdf

If chunks arrive in a different order:

3 → 1 → 0 → 2

OFFGRID can still reconstruct:

0 → 1 → 2 → 3
🧩 Architecture
                    ┌──────────────────────┐
                    │      OFFGRID UI      │
                    │   Dashboard / Demo   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     API / EVENTS     │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌─────────────────────────────────┐
              │       MESSAGING ENGINE          │
              │                                 │
              │  Message Manager                │
              │  Store & Forward                │
              │  ACK / Retry                    │
              │  Duplicate Detection            │
              │  TTL Management                 │
              └───────────────┬─────────────────┘
                              │
                              ▼
              ┌─────────────────────────────────┐
              │        NETWORK CORE             │
              │                                 │
              │  Discovery                      │
              │  Routing                        │
              │  Heartbeats                     │
              │  Failure Detection              │
              └───────────────┬─────────────────┘
                              │
                              ▼
                ┌──────────────────────────┐
                │     P2P DEVICE MESH      │
                │                          │
                │ 📱 ── 📱 ── 💻 ── 📱 ── 📱 │
                └──────────────────────────┘
🏗️ Project Structure
OFFGRID/
│
├── backend/
│   ├── messaging/
│   │   ├── message.py
│   │   ├── duplicate.py
│   │   ├── store.py
│   │   ├── queue.py
│   │   ├── delivery.py
│   │   ├── file_transfer.py
│   │   ├── file_manager.py
│   │   │
│   │   ├── test_message.py
│   │   ├── test_duplicate.py
│   │   ├── test_store.py
│   │   ├── test_store_forward.py
│   │   ├── test_ack_retry.py
│   │   ├── test_file_transfer.py
│   │   └── test_file_manager.py
│   │
│   └── ...
│
├── store_forward_demo.py
│
├── README.md
│
└── requirements.txt
🧪 Tested & Verified

OFFGRID currently includes automated tests covering:

Message Creation              ✅
Message Serialization         ✅
Message Status                ✅
Duplicate Detection           ✅
Message Storage               ✅
Store & Forward               ✅
ACK Handling                  ✅
Retry Mechanism               ✅
TTL Expiration                ✅
File Chunking                 ✅
File Reassembly               ✅
File Transfer Integration     ✅
Current test status
25 TESTS
   │
   ├── 25 PASSED ✅
   │
   └── 0 FAILED
🚨 Designed For

OFFGRID is designed around situations where normal communication infrastructure becomes unreliable.

🌪️ Natural Disasters

Earthquakes, floods, cyclones and hurricanes can destroy communication infrastructure.

OFFGRID allows nearby devices to continue communicating.

🔥 Emergency Response

First responders can exchange information across a local device network.

Responder A
     ↓
Relay Node
     ↓
Relay Node
     ↓
Command Node
🏕️ Remote Areas

Places without reliable cellular or Internet connectivity can still exchange information through nearby nodes.

🏟️ Infrastructure Failure

Large-scale outages shouldn't automatically mean communication failure.

⚔️ Traditional Communication vs OFFGRID
	Traditional	OFFGRID
Internet required	Often	❌
Cellular tower required	Often	❌
Central server	Usually	❌
Peer-to-peer	Limited	✅
Store & forward	Limited	✅
Multi-hop communication	Limited	✅
Duplicate protection	Depends	✅
TTL management	Depends	✅
Chunked file transfer	Depends	✅
Network failure resilience	Limited	🚀
🎯 The Big Vision

OFFGRID aims to transform ordinary devices into infrastructure.

Today:

📱 = Consumer Device

Tomorrow:

📱 = Communication Node
📱 = Relay
📱 = Router
📱 = Emergency Infrastructure

Imagine a city where thousands of devices can automatically form a communication fabric when conventional infrastructure goes down.

No single device needs to control the network.

No single failure needs to destroy it.

🧠 Design Philosophy

OFFGRID follows three principles:

1. No Single Point of Failure
        ❌ CENTRAL SERVER
              ↓
       ┌──────┴──────┐
       │             │
      FAIL          FAIL

Instead:

📱 ── 📱 ── 📱
│  ╲  │  ╱  │
📱 ── 📱 ── 📱
│  ╱     ╲  │
📱 ── 📱 ── 📱

The network is distributed.

2. Assume Connectivity Will Fail

Instead of assuming:

"The network is always available."

OFFGRID assumes:

"The network will eventually fail."

Therefore:

Messages can wait.
Messages can retry.
Routes can change.
Nodes can disappear.
Files can arrive in pieces.
3. Make Failure Normal

A failed node isn't necessarily a disaster.

It's a network event.

NODE ONLINE
     ↓
     ❤️
     ↓
NODE OFFLINE
     ↓
ROUTE FAILURE
     ↓
FIND ALTERNATIVE
     ↓
CONTINUE 🚀
🧑‍💻 Team

Built as a collaborative project with separate engineering modules.

┌───────────────────────────────────────────┐
│                 OFFGRID                   │
├───────────────────────────────────────────┤
│                                           │
│  👤 Person 1 - Shaswath                   │
│  Network Core                             │
│  Routing • Discovery • Heartbeats         │
│                                           │
│  👤 Person 2 - Praneeth                   │
│  Dashboard                                │
│  Visualization • Monitoring • UI          │
│                                           │
│  👤 Person 3 - Saiyam                     │
│  Messaging Engine                         │
│  Store/Forward • ACK • Retry • Files

    👤 Person 4 - Adarsh
    Research and pitching
    
    👤 Person 5 - Kamal
    Research and presentation  │
│                                           │
└───────────────────────────────────────────┘