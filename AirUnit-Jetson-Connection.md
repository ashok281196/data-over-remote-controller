# Bringing Up the SIYI MK15 Ethernet Network on Jetson/Linux

This guide explains how to:
- Identify the MK15 Ethernet interface  
- Assign a static IP  
- Stop NetworkManager from resetting or closing the interface  
- Make the connection persistent  
- Verify stable communication with the MK15 Air Unit

---

## 1. Identify Your Ethernet Interface

Run:

```bash
ip a
```

Find the Ethernet interface connected to the MK15 Air Unit.  
Example:

```
enxc8a3624fb799
```

This is the interface we will configure.

---

## 2. Stop NetworkManager From Managing or Closing the Interface

NetworkManager interferes by:
- Removing the static IP  
- Setting the link down  
- Reinitializing the interface randomly  

To completely stop that:

### 2.1 Mark the interface as unmanaged

```bash
sudo nmcli dev set enxc8a3624fb799 managed no
```

Check the status:

```bash
nmcli dev status
```

Expected line:

```
enxc8a3624fb799  ethernet  unmanaged  --
```

### 2.2 Remove any active NM connection profiles

```bash
sudo nmcli connection delete "$(nmcli -t -f NAME,DEVICE connection show | grep enxc8a3624fb799 | cut -d: -f1)"
```

### 2.3 Tell NetworkManager to permanently ignore this interface

Edit the NM config:

```bash
sudo nano /etc/NetworkManager/NetworkManager.conf
```

Add:

```ini
[keyfile]
unmanaged-devices=interface-name:enxc8a3624fb799
```

Reload NM:

```bash
sudo systemctl restart NetworkManager
```

Now NM will **never** modify or close this interface.

---

## 3. Assign the Static MK15 IP

Flush old settings:

```bash
sudo ip addr flush dev enxc8a3624fb799
```

Assign:

```bash
sudo ip addr add 192.168.144.25/24 dev enxc8a3624fb799
sudo ip link set enxc8a3624fb799 up
```

Verify:

```bash
ip a show enxc8a3624fb799
```

You should see:

```
inet 192.168.144.25/24
```

---

## 4. Test MK15 Air Unit Connectivity

Air Unit default IP: `192.168.144.11`

```bash
ping 192.168.144.11
```

If you get stable replies → network is working correctly.

---

## 5. Make the Static IP Permanent (systemd-networkd)

Optional but recommended.

Create:

```bash
sudo nano /etc/systemd/network/10-mk15.network
```

Paste:

```ini
[Match]
Name=enxc8a3624fb799

[Network]
Address=192.168.144.25/24
DHCP=no
LinkLocalAddressing=no
```

Apply:

```bash
sudo systemctl restart systemd-networkd
```

---

## 6. Summary

- MK15 Ethernet uses static IP **192.168.144.x**  
- NetworkManager must be **disabled** for this interface  
- Static IP is applied using `ip addr add`  
- Ping confirms the Air Unit connection  
- Optional: use systemd-networkd for persistence  

---

## 7. Verification Checklist

- [ ] `nmcli dev status` shows interface as **unmanaged**  
- [ ] `ip a` shows `192.168.144.25/24`  
- [ ] Stable ping to `192.168.144.11`  
- [ ] Interface no longer drops unexpectedly  

---

**End of Guide — MK15 Ethernet Link Stable & Ready for Video Streaming**
