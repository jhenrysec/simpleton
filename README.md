# Range Bench

Instructor console and portable callback kit for an isolated defensive-operations lab. One operator on the attacker, one agent on each guest, six readable channels, and a class that runs for days. The virtual machines are wiped and rebuilt between classes. Nothing in the lab expires on a clock.

**Isolated lab only.** Install agents only on virtual machines you administer. Do not hand the plays, the remediation, or this repository to the class. Project only the sentence in the deface step. This repository is private on purpose.

## What is in here

| Path | What it is |
|---|---|
| `src/` | Range Bench. The page that builds the attacker command, the guest commands, the roster, the SSH path, and the plays. |
| `kit/range.py` | Operator and Linux agent. Python 3.5 or newer. No packages. |
| `kit/range-agent.ps1` | Windows 10 agent for stock PowerShell 5.1. TCP, HTTP, and WebSocket only. |
| `kit/range.json.example` | Optional. Same settings as the form, passed with `--config`. |
| `kit/README.md` | Operator manual: console, deface, plays, terminal, files, logs, and the SSH path. |
| `public/range-lab.zip` | The kit the **Download kit** button serves. |

Range Bench remembers the last form in the browser. Ports, the token, and addresses live in those commands, not in the scripts. A later class keeps the same files.

## Start here

Two pieces. **Range Bench** is the page on your laptop. It does not connect to the lab. It fills in the commands. **The kit** is the `kit` folder. That is what you copy onto the attacker and the guests. **Download kit** on the page is only a zip of that same folder. If you cloned this repository, you already have it.

### Open Range Bench

On your laptop, in the folder that contains `package.json`. That is the clone itself, not `kit`. The page needs Node.js 22. `node -v` has to print `v22`. Anything older fails immediately with `Unexpected token {` in `scripts/with-app-env.mjs`. Ubuntu’s `nodejs` package is that older Node. Do not install it.

If `node -v` is not v22, put Node 22 in your home directory. This does not replace the system Node.

```bash
curl -fsSL -o /tmp/node22.tar.xz https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.xz
mkdir -p "$HOME/.local/node22"
tar -xJf /tmp/node22.tar.xz -C "$HOME/.local/node22" --strip-components=1
export PATH="$HOME/.local/node22/bin:$PATH"
node -v
```

Add that `export` line to `~/.bashrc` if you want the new Node in later terminals. On an arm64 machine, use `node-v22.23.3-linux-arm64.tar.xz` instead. Guests do not need Node 22. Only the laptop running this page does.

```bash
npm install
npm run dev
```

Node 22. Open `http://localhost:8080`. Leave that terminal running. The page needs no account. Lab settings stay in this browser.

Set the attacker address to the address the guests use to reach the attacker, generate a token, and leave timing on **Continuous**. Then copy the three commands. If you change the token, the channel, the timing, or a port after copying, copy again.

### On the attacker

Copy `kit` onto the Ubuntu attacker. The folder name does not matter.

```bash
cd kit
python3 range.py selftest
```

`PASS tcp,http,dns,mqtt,ws` means the check worked. **The command then exits.** It does not start the operator. ICMP is skipped unless that shell can open a raw socket. Do not start class if the line is not `PASS`.

The operator is a second command. Leave it in the foreground. It does not return to a prompt. That window is the console. Replace the token, and replace `10.0.0.10` with the attacker address.

```bash
sudo python3 range.py operator --token 'lab-token-change-me' --bind 0.0.0.0 \
  --tcp-port 443 --http-port 80 --dns-port 53 --mqtt-port 1883 --ws-port 8070 --zone lab
```

`sessions` stays empty until a guest calls in. Copy `range.py` to each Linux guest and `range-agent.ps1` to Windows, and start one agent per machine with its own id. The commands on the page are the ones to paste. Operator detail is in [kit/README.md](kit/README.md).

## Order of the class

1. Open Range Bench from the repository root, or skip it and use the commands below.
2. Copy `kit` to the attacker. Self-test. Start the operator and leave it open. Start one agent per guest.
3. Open the SSH master. Install your key. It asks once per hop.
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
| deb-22 | Debian 12 | `172.24.22.19` | `22` |

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

`python3 range.py selftest` only checks this machine, then exits. The operator command in [Start here](#start-here) is what stays running.

The bench builds three commands: the attacker, the Linux guest, and Windows. Change `--id` so every VM is unique. `sessions` lists agents that have called in. A TCP, WebSocket, or MQTT session stays listed for as long as the socket is up. It does not age out.

Operator detail, including `tty`, `get` / `put`, `play logs`, and the host plays, is in [kit/README.md](kit/README.md).

## Path

The bench writes `range-ssh.conf` and `range-hosts.json`. Put them next to `range.py`.

```bash
ssh -F range-ssh.conf lab-wan
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
