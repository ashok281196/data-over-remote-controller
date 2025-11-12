# Using Jetson with SIYI MK15 for Ethernet Video Streaming

**Purpose:**  
Connect an NVIDIA Jetson board to a **SIYI MK15 Air Unit** via Ethernet, stream camera output (CSI or USB) as **RTSP**, and display it live on the **MK15 Ground Controller** (FPV app or QGroundControl).

---

## 1. Overview
The SIYI MK15 supports external IP cameras over Ethernet.  
By wiring Jetson’s Ethernet port to the MK15 Air Unit’s *Video* port and hosting an RTSP stream, the MK15 controller can view Jetson’s camera feed in real-time.

---

## 2. Hardware Requirements

- ✅ **SIYI MK15 Air Unit** (with original “Video” cable)  
- ✅ **NVIDIA Jetson Nano / Xavier / Orin**  
- ✅ **RJ45 Ethernet plug or breakout board**  
- ✅ **Multimeter** (for pin continuity)  
- ✅ **Cat-5e/Cat-6 shielded cable** (recommended)

---

## 3. MK15 Air Unit Video Port Pinout

| Pin | Signal | Description |
|:--:|:--|:--|
| 1 | D2 | Reserved / unused |
| 2 | RX- | Ethernet receive (−) |
| 3 | RX+ | Ethernet receive (+) |
| 4 | TX+ | Ethernet transmit (+) |
| 5 | TX- | Ethernet transmit (−) |
| 6 | GND | Ground |
| 7 | 12 V | **Power output (⚠️ Do NOT connect to Jetson)** |
| 8 | GND | Ground |

> Only use pins **2–5** for data and **6/8** for optional grounding.

---

## 4. RJ45 Ethernet Mapping (T568B Standard)

| RJ45 Pin | Signal | Color (Typical) |
|:--:|:--|:--|
| 1 | TX+ | Orange/White |
| 2 | TX- | Orange |
| 3 | RX+ | Green/White |
| 6 | RX- | Green |

---

## 5. Wiring Table

| MK15 Pin | RJ45 Pin | Function |
|:--:|:--:|:--|
| 2 (RX-) | 6 | RX− |
| 3 (RX+) | 3 | RX+ |
| 4 (TX+) | 1 | TX+ |
| 5 (TX-) | 2 | TX− |
| 6 or 8 (GND) | RJ45 shield | Ground (optional) |

Use **straight-through wiring** (not crossover).  
⚠️ **Do NOT connect pin 7 (12 V)** to anything on Jetson.

---

## 6. Cable Assembly Steps

1. Identify wire colors on the MK15 “Video” cable using a multimeter.  
2. Crimp the other end to an RJ45 plug using the mapping above.  
3. Ensure the 12 V line is isolated.  
4. Optionally tie GND (pin 6 / 8) to RJ45 shield for stability.

---

## 7. Network Configuration

### MK15 Default IP Scheme

| Device | IP Address |
|:--|:--|
| Air Unit | `192.168.144.11` |
| Ground Unit | `192.168.144.12` |
| Android Controller | `192.168.144.20` |

### Set Static IP on Jetson

```bash
sudo ip addr add 192.168.144.25/24 dev eth0
sudo ip link set eth0 up
ping 192.168.144.11
```

If ping responds, the Ethernet link is working.

---

## 8. Setting up the RTSP Stream

### Install GStreamer

```bash
sudo apt update
sudo apt install gstreamer1.0-tools   gstreamer1.0-plugins-good gstreamer1.0-plugins-bad   gstreamer1.0-plugins-ugly gstreamer1.0-nvvideo4linux2   gstreamer1.0-rtsp
```

### Start RTSP Server (Jetson CSI Camera)

```bash
test-launch '( nvarguscamerasrc ! video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1 ! nvv4l2h264enc insert-sps-pps=true iframeinterval=30 bitrate=4000000 ! h264parse config-interval=1 ! rtph264pay name=pay0 pt=96 )'
```

This exposes:  
👉 `rtsp://192.168.144.25:8554/test`

---

## 9. Viewing the Stream on MK15 Controller

### **SIYI FPV App**
1. Open **Settings → Camera IP / RTSP URL**  
2. Enter `rtsp://192.168.144.25:8554/test`  
3. Tap **Connect** → Live video appears

### **QGroundControl**
1. Go to **Application Settings → Video**  
2. Set *Video Source* → **RTSP**  
3. Paste the same RTSP URL

---

## 10. Verification Checklist

- ✅ Ethernet LEDs lit on Jetson  
- ✅ `ping 192.168.144.11` works  
- ✅ RTSP server reachable  
- ✅ Video visible in FPV or QGC  

---

## 11. Troubleshooting

| Problem | Cause | Fix |
|:--|:--|:--|
| No link light | Incorrect pin wiring | Recheck pins 2–5 only |
| No ping | Wrong IP range | Use 192.168.144.x/24 |
| No video | Wrong codec | Use **H.264** only |
| Laggy stream | Missing keyframes | Add `insert-sps-pps=true iframeinterval=30` |
| Dropped frames | Bitrate too high | Lower to 3–4 Mbps |

---

## 12. Safety Notes

- ⚠️ **Do NOT connect 12 V pin 7** to Jetson.  
- Always use shielded cable near RF modules.  
- Common-ground only if needed to eliminate noise.

---

## 13. Summary

After setup:
- Jetson acts as an **IP camera node** for the MK15.
- Stream any CSI or USB camera feed wirelessly.
- Compatible with **GStreamer**, **FFmpeg**, and **MediaMTX**.

---

**Author:** General Autonomy Robotics Team  
**Revision:** v1.0 — Jetson ↔ MK15 Ethernet RTSP Integration  
**Date:** November 2025
