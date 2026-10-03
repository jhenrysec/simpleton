import pkg from "/workspace/node_modules/playwright-core/index.js";
const { chromium } = pkg;
import fs from "fs";

const chrome = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome";
const outDir = "/workspace/docs/usage-images";
fs.mkdirSync(outDir, { recursive: true });

function esc(text) {
  return text.replace(/&/g, "&").replace(/</g, "<");
}

function terminal(title, lines) {
  const body = lines
    .map((line) => {
      if (line.startsWith("range")) {
        const cut = line.indexOf("> ");
        const prompt = esc(line.slice(0, cut + 1));
        const rest = esc(line.slice(cut + 2));
        return `<div><span class="pr">${prompt}</span> ${rest}</div>`;
      }
      if (line.startsWith("$ ")) return `<div><span class="pr">$</span> ${esc(line.slice(2))}</div>`;
      return `<div class="out">${esc(line) || "&nbsp;"}</div>`;
    })
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;background:#111318;color:#f4f7fb;font:14px/1.4 ui-monospace,Consolas,monospace}
    .bar{height:28px;background:#1c212b;display:flex;align-items:center;padding:0 12px;color:#9aa3b2;font:12px system-ui,sans-serif}
    .dot{width:8px;height:8px;border-radius:50%;background:#3a4250;display:inline-block;margin-right:5px}
    pre{margin:0;padding:12px 14px 14px}
    .pr{color:#7dcea0}
    .out{color:#c5ced8}
  </style></head><body><div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>${title}</div><pre>${body}</pre></body></html>`;
}

const shots = {
  "start-range": ["ocelot", ["$ range", "Opening the path to the WAN router. Type that password.", "Installing keys and starting an agent on each host. The id is the last octet.", "starting 5 agent(s). The id is the last octet of the address.", "Starting the operator. This window is now the range console.", "range>"]],
  "start-skip": ["ocelot", ["$ range plant --skip 172.24.18.82", "Extra plant arguments: --skip 172.24.18.82", "skipping 172.24.18.82", "starting 4 agent(s). The id is the last octet of the address."]],
  "start-watch": ["ocelot", ["$ range watch", "180  abdullayev  pts/0  10.50.11.4", "44   student      tty1   local"]],
  "start-selftest": ["ocelot", ["$ python3 range.py selftest", "PASS tcp,http,dns,mqtt,ws"]],
  sessions: ["range", ["range> sessions", "id          channel  state  profile    os       user     age", "180         ws       up     continuous linux    abdullay 4s", "44          mqtt     up     continuous linux    student  9s"]],
  ports: ["range", ["range> ports", "tcp 443", "http 80", "dns 53", "mqtt 1883", "ws 8070", "icmp echo (raw)", "dns zone lab"]],
  use: ["range", ["range> use 180", "using 180", "range 180> hostname", "web-nginx", "[rc=0]"]],
  back: ["range", ["range 180> back", "range>"]],
  profile: ["range", ["range 180> profile off", "180 profile off queued", "range 180> profile continuous", "180 profile continuous queued"]],
  broadcast: ["range", ["range> broadcast hostname", "---- 180 ----", "web-nginx", "[rc=0]", "---- 44 ----", "deb9-44", "[rc=0]"]],
  raw: ["range", ["range 180> id", "uid=0(root) gid=0(root) groups=0(root)", "[rc=0]"]],
  shell: ["range", ["range 180> shell", "line shell on 180. Each line is one command. cd sticks. nano needs tty. exit returns.", "180$ pwd", "/root", "180$ exit", "range 180>"]],
  tty: ["range", ["range 180> tty", "remote terminal. Type .quit and press Enter to leave.", "root@web-nginx:~# nano /var/www/html/index.html", "root@web-nginx:~# .quit", "range 180>"]],
  get: ["range", ["range 180> get /tmp/range-test", "got 3 bytes -> range-test"]],
  put: ["range", ["range 180> put range-test /tmp/range-test-back", "WROTE=/tmp/range-test-back BYTES=3"]],
  look: ["range", ["range 180> play look", "WEBROOT=/var/www/html", "MODE=644 OWNER=root GROUP=root MTIME=...", "---- head ----", "<!DOCTYPE html>", "DONE", "[rc=0]"]],
  snapshot: ["range", ["range 180> play snapshot", "SAVED=/var/lib/.hold/site/index.html", "DONE", "[rc=0]"]],
  deface: ["range", ["range 180> play deface", "WEBROOT=/var/www/html", "IMAGE=/var/www/html/3ntity-logo.png", "DONE", "[rc=0]"]],
  undo: ["range", ["range 180> play undo", "RESTORED=/var/www/html/index.html", "DONE", "[rc=0]"]],
  revert: ["range", ["range 180> play revert", "REVERTED=/var/www/html/index.html", "DONE", "[rc=0]"]],
  history: ["range", ["range 180> play history", "LOOKING_FOR=root", "DONE", "[rc=0]"]],
  "history-clear": ["range", ["range 180> play history backup clear", "ABSENT=/var/backups/.bash_history", "CLEARED=/root/.bash_history", "DONE", "[rc=0]"]],
  wall: ["range", ["range 180> play wall The page changed. The process list is the wrong tool.", "WALL=nobanner", "DONE", "[rc=0]"]],
  stamp: ["range", ["range 180> play stamp", "STAMPED=/usr/bin/ps", "DONE", "[rc=0]"]],
  account: ["range", ["range 180> play account backup", "login for backup is local only (not in the tasking): (printed here)", "EXISTS=backup", "GROUP=sudo", "SHADOW=hash", "DONE", "[rc=0]"]],
  cloak: ["range", ["range 180> play cloak", "BACKUP=/var/lib/.hold/bin/false.orig", "CLOAKED=/usr/bin/false", "CLOAKED=/usr/sbin/nologin", "DONE", "[rc=0]"]],
  uncloak: ["range", ["range 180> play uncloak", "RESTORED=/usr/bin/false", "RESTORED=/usr/sbin/nologin", "DONE", "[rc=0]"]],
  veil: ["range", ["range 180> play veil abdullayev.coshgun", "COPIED=/usr/bin/ps", "VEILED=/usr/bin/ps", "VEILED=/usr/bin/netstat", "DONE", "[rc=0]"]],
  unveil: ["range", ["range 180> play unveil", "RESTORED=/usr/bin/ps", "RESTORED=/bin/netstat", "DONE", "[rc=0]"]],
  "play-shell": ["range", ["range 180> play shell backup bash", "BEFORE=backup:x:34:34:backup:/var/backups:/usr/sbin/nologin", "AFTER=backup:x:34:34:backup:/var/backups:/bin/bash", "SHELL=/bin/bash", "DONE", "[rc=0]"]],
  persist: ["range", ["range 180> play persist", "PERSIST=systemd", "UNIT=/etc/systemd/system/mailq-local.service", "DONE", "[rc=0]"]],
  unpersist: ["range", ["range 180> play unpersist", "UNPERSIST=done", "DONE", "[rc=0]"]],
  boot: ["range", ["range 180> play boot abdullayev.coshgun", "DONE", "[rc=0]"]],
  logs: ["range", ["range 180> play logs", "DONE", "[rc=0]"]],
  "logs-all": ["range", ["range 180> play logs all", "CLEARED=/root/.bash_history", "DONE", "[rc=0]"]],
  exit: ["range", ["range 180> exit"]],
};

const browser = await chromium.launch({
  executablePath: chrome,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 880, height: 160 } });
for (const [name, [title, lines]] of Object.entries(shots)) {
  await page.setContent(terminal(title, lines));
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: 880, height: h });
  await page.screenshot({ path: `${outDir}/${name}.png` });
}
await browser.close();
console.log("shots", Object.keys(shots).length);
