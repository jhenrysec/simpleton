# Range Bench

Instructor console and portable callback kit for an isolated defensive-operations lab. One operator on the attacker, one agent on each guest, six readable channels, and a class that runs for days. The virtual machines are wiped and rebuilt between classes. Nothing in the lab expires on a clock.

**Isolated lab only.** Install agents only on virtual machines you administer. Do not hand the plays, the remediation, or this repository to the class. Project only the sentence in the deface step. This repository is private on purpose.

## What is in here

| Path | What it is |
|---|---|
| `src/` | Range Bench, the page that builds the kit. |
| `kit/` | The operator, the agents, and `setup`. Python 3.5 or newer. No packages. |
| `scripts/install.sh` | Installs Node.js v22.23.3 if needed, then installs the page. |

The **Download kit** button builds the zip in the browser from `kit/` and the form. There is no separate zip to keep in the repository.

## Install the page

On the laptop. This does not connect to the lab. Guests and ocelot do not need Node.

```bash
git clone https://github.com/jhenrysec/charm-prism-glade-bolt.git
cd charm-prism-glade-bolt
sh scripts/install.sh
```

`scripts/install.sh` checks Node. If it is missing, or older than 22, the script downloads Node.js v22.23.3 into `~/.local/node22` and adds it to `~/.bashrc` and `~/.profile`. It does not use `apt` and it does not replace a system Node. It then runs `npm install` and starts the page.

Leave that window open. Open `http://localhost:8080`. The page needs no account.

The same steps, with screenshots, are in [docs/Range-Bench-Install-Guide.pdf](docs/Range-Bench-Install-Guide.pdf).

Set the attacker address to the address the guests use, generate a token, and leave timing on **Continuous**. Upload `index.html` and the image if you are using them. **Download kit**.

## Install the kit on ocelot

Copy `range-lab.zip` to ocelot. Extract it in your home directory and run setup once. Do not use sudo.

```bash
unzip range-lab.zip -d ~
cd ~/range-lab
sh setup
```

Open a new terminal and type `range`. That opens the WAN path, copies the agent to every host, and leaves you at the console.

Before class, on ocelot:

```bash
cd ~/range-lab
python3 range.py selftest
```

`PASS tcp,http,dns,mqtt,ws` means the check worked. The command then exits. It does not start the operator. Do not start class if the line is not `PASS`.

Operator commands, plays, and the terminal are in [kit/README.md](kit/README.md). Every command, with the syntax and a screenshot, is in [docs/Range-Usage-Guide.pdf](docs/Range-Usage-Guide.pdf).

## Order of the class

1. Clone the repository and run `sh scripts/install.sh`. That installs Node if needed and starts the page.
2. Download the kit, copy it to ocelot, and run `sh setup`. Type `range`.
3. Open the SSH master when `range` asks. It installs the key and starts one agent per host.
4. Watch from a second terminal. Work one agent at a time in the first.
5. Deface when you mean to. Say the brief. Do not paste the fix.

## Roster

Focus stays off on the WAN router. It stays on for everyone fanout and watch should touch. Router SSH is `20222`. Hosts are port `22`. The WAN router’s last two octets change. Its port does not.

| Name | Role | Address | Port |
|---|---|---|---|
| wan | VYOS, path only | `10.50.160.129` | `20222` |
| lan | VYOS | `172.24.18.1` | `20222` |
| lan2 | VYOS | `172.24.2.4` | `20222` |
| win-82 | Windows 10 | `172.24.18.82` | `22` |
| deb-68 | Debian 12 | `172.24.18.68` | `22` |
| deb-150 | Debian 12 | `172.24.10.150` | `22` |
| web-nginx | Debian 12, NGINX | `172.24.10.180` | `22` |
| deb9-44 | Debian 9 | `172.24.19.44` | `22` |
| deb-22 | Debian 12 | `172.24.19.19` | `22` |

Debian 9 is `172.24.19.44`. It is not a second copy of `172.24.10.150`. If a saved bench still shows the old duplicate, reload the page. The saved row is rewritten.

Students should treat `10.50.0.0/24` as the public side. There is no internet. The SSH path is `cvte@10.50.11.232`, then `cvte@172.24.24.101`, then `atropia_admin` on the WAN router.

## Channels

Frames are signed, not encrypted. After a short decode, Wireshark can read them. A student who decodes a frame can see that a tag is present. They do not see the token.

| Channel | Wireshark | Where the tasking sits | Windows |
|---|---|---|---|
| TCP | `tcp.port == 443 && !tls` | One base64 line each way. Port 443 with no Client Hello. | PowerShell |
| HTTP | `http.request.uri contains "/debian/dists" or "/ocsp/"` | A long hex MD5Sum, or an OCSP Nonce that grew. | PowerShell |
| DNS | `dns.qry.name contains ".lab" && dns.qry.type == 16` | TXT or query labels, hex, aimed at the attacker. Not the lab resolver. | Python |
| MQTT | `mqtt` | Topics `lab/<id>/in` and `out`. Payload is base64. | Python |
| WebSocket | `websocket` | Upgrade to `/notifications`, then text frames. | PowerShell |
| ICMP | `icmp && data.len > 32` | Echo data is base64. Linux only. Ordinary pings to the attacker stop while the operator has ICMP open. | Not available |

Class ports are `443`, `80`, and `53`. The operator needs root for those. The no-sudo preset is `8443`, `8088`, and `5353`. MQTT stays `1883`. WebSocket stays `8070`.

## Timing

This is a multi-day exercise, not a one-minute demo.

- **Continuous.** The attacker stays up for the class. TCP, WebSocket, and MQTT stay connected, so there is no poll clock. HTTP, DNS, and ICMP ask about once a second, or a command cannot land.
- **Off.** The beacon stops. HTTP, DNS, and ICMP look again in about half an hour, which is how `profile continuous` gets through without a login. TCP, WebSocket, and MQTT stay connected and just go quiet.

`live` is accepted and means continuous. `hunt` is the old 20–45 second jitter. Do not use it for this class. On the guest command, continuous is `--profile continuous` on Linux and `-Timing continuous` on Windows, because `$PROFILE` is reserved.

## Prove the kit

`python3 range.py selftest` only checks this machine, then exits. `range` is what stays running.

The bench builds three commands: the attacker, the Linux guest, and Windows. Change `--id` so every VM is unique. `sessions` lists agents that have called in. A TCP, WebSocket, or MQTT session stays listed for as long as the socket is up. It does not age out.

Operator detail, including `tty`, `get` / `put`, `play logs`, and the host plays, is in [kit/README.md](kit/README.md).

## Path

The bench writes `range-ssh.conf` and `range-hosts.json`. Put them next to `range.py`.

```bash
ssh -fN -o ServerAliveInterval=5 -o ServerAliveCountMax=9999 -F range-ssh.conf lab-wan
python3 range.py keys --hosts range-hosts.json --ssh-config range-ssh.conf
```

Open the master once. Install the key once. Later commands reuse the socket and do not ask for a password. `ControlPersist` is `yes`. Missed keepalives do not drop it. The socket stays until you close it or the class is rebuilt.

`keys` uses the public key already on that account, or creates `~/.ssh/range_lab` if there is none. It copies the key to both jumps, the WAN router, both LAN routers, and every host. The same address is only done once. A rebuilt VM needs it once more. The first hop still needs a password the first time, because nothing is trusted yet.

Watch is not the callback list. `sessions` only lists hosts where an agent is running. Watch is how you see the students move, including on a router that has no agent:

```bash
python3 range.py watch --hosts range-hosts.json --ssh-config range-ssh.conf --student defender
```

ICMP from a laptop will not cross the jump. The ping card runs `ping` on the WAN router. Fanout runs one command on every focused host, including the LAN routers. The WAN hop is the path, not a target.

## Requirements

- Ubuntu attacker the guests can reach. Python 3.5 or newer. No pip packages.
- Debian 12, Debian 9 at `172.24.19.44`, Windows 10, and the VYOS routers in the roster.
- Windows can stay on stock PowerShell 5.1 for TCP, HTTP, and WebSocket. DNS and MQTT on Windows need `range.py`. ICMP cannot run on Windows.
- The Linux file lock needs root on the agent. ICMP needs root on the operator.

## What the class should not see

The instructor key in the bench stays collapsed so it is not on screen while you project the brief. Empty logs are a signal: the file is still there and has nothing in it. Bash history is left unless you run `play logs all`. Do not paste the undo steps into a guest the class is working on.

Say this, and nothing else, when the page changes:

> A site you control has changed. Capture the traffic, find the callback, and put the page back. If the editor will not save, that problem is on the host.
