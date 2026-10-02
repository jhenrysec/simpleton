import { useState } from "react";
import { Check, Copy, Download } from "lucide-react";
import {
  fanoutCommand,
  keysCommand,
  plantCommand,
  watchCommand,
  hostsDocument,
  openTunnelCommand,
  pingCommand,
  reachOcelotCommand,
  copyKitCommand,
  sshConfig,
  tradecraftScript,
  zipStore,
  type BenchConfig,
  type LabHost,
} from "@/lib/bench";

function CopyBlock({ title, hint, command }: { title: string; hint: string; command: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-muted">{hint}</p>
        </div>
        <button
          type="button"
          onClick={copy}
          className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-border px-3 text-sm text-fg"
        >
          {copied ? <Check className="size-4 text-primary" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 font-mono text-sm leading-relaxed text-fg">{command}</pre>
    </section>
  );
}

export function LabFloor({
  cfg,
  onChange,
  htmlName,
  htmlText,
  imageName,
  imageBytes,
}: {
  cfg: BenchConfig;
  onChange: (partial: Partial<BenchConfig>) => void;
  htmlName: string;
  htmlText: string;
  imageName: string;
  imageBytes: Uint8Array | null;
}) {
  const nginx = cfg.hosts.find((host) => host.id === "web-nginx");
  const dupes = new Set<string>();
  const seen = new Set<string>();
  cfg.hosts.forEach((host) => {
    const key = host.address.trim();
    if (!key) return;
    if (seen.has(key)) dupes.add(key);
    seen.add(key);
  });

  function patchHost(id: string, partial: Partial<LabHost>) {
    onChange({
      hosts: cfg.hosts.map((host) => (host.id === id ? { ...host, ...partial } : host)),
    });
  }

  async function downloadPath() {
    const encoder = new TextEncoder();
    const files: { name: string; data: Uint8Array }[] = [
      { name: "range-hosts.json", data: encoder.encode(JSON.stringify(hostsDocument(cfg), null, 2) + "\n") },
      { name: "range-ssh.conf", data: encoder.encode(sshConfig(cfg)) },
    ];
    if (htmlText && htmlName) {
      files.push({ name: `deface/${htmlName}`, data: encoder.encode(htmlText) });
    }
    if (imageBytes && imageName) {
      files.push({ name: `deface/${imageName}`, data: new Uint8Array(imageBytes) });
    }
    const blob = zipStore(files);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "range-path.zip";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Path into the lab</h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">
            The laptop only reaches ocelot, through one jump. Ocelot is Kali and has no internet. Hosts cannot see the laptop. They call ocelot’s public address, which changes. From ocelot the path is the WAN router, then the hosts. Run the operator, plant, and watch on ocelot.
          </p>
        </div>
        <button
          type="button"
          onClick={downloadPath}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-border px-4 text-sm font-semibold text-fg"
        >
          <Download className="size-4" aria-hidden="true" />
          Download path files
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Mini label="Jump user" value={cfg.jump1User} onChange={(jump1User) => onChange({ jump1User })} />
        <Mini label="Jump host" value={cfg.jump1Host} onChange={(jump1Host) => onChange({ jump1Host })} />
        <Mini label="Ocelot user" value={cfg.jump2User} onChange={(jump2User) => onChange({ jump2User })} />
        <Mini label="Ocelot management address" value={cfg.jump2Host} onChange={(jump2Host) => onChange({ jump2Host })} />
        <Mini label="WAN user" value={cfg.wanUser} onChange={(wanUser) => onChange({ wanUser })} />
      </div>
      <p className="text-sm leading-relaxed text-muted">
        This is not a SOCKS proxy. The laptop command only opens a shell on ocelot. The path files are for ocelot: it talks to the WAN router directly, and that router is the jump to every host. The socket on ocelot stays up until you close it.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <CopyBlock title="Reach ocelot" hint="Run on the laptop. One jump, then the ocelot account. This management address is not the address hosts call." command={reachOcelotCommand(cfg)} />
        <CopyBlock title="Copy the kit onto ocelot" hint="Run on the laptop, in the folder that contains range.py and the two path files. Ocelot cannot download them. Kali already has Python." command={copyKitCommand(cfg)} />
        <CopyBlock title="Open the master" hint="Run on ocelot, inside range-lab. Type the WAN password once. There is no jump in this file." command={openTunnelCommand()} />
        <CopyBlock title="Install your key" hint="Run on ocelot. Copies ocelot’s public key to the WAN router, both LAN routers, and every host. Each one asks once." command={keysCommand()} />
        <CopyBlock title="ICMP" hint="Runs ping on the WAN router, which can actually reach the lab. A laptop ping still will not cross the jump." command={pingCommand(nginx?.address || "172.24.10.180")} />
        <CopyBlock title="One command, every host" hint="Routers included. The WAN hop is the path, not a target." command={fanoutCommand()} />
      </div>
      <CopyBlock
        title="Plant the agents"
        hint="Run this on ocelot, in range-lab, after the operator is already up. It logs in to the WAN router and both LAN routers as atropia_admin, and to each host as the user in the roster. Then it installs ocelot’s key, copies range.py or range-agent.ps1, and starts the agent. The id is the last octet, so 172.24.10.180 is use 180. Agents call the public address, not the management address. Routers get the key only."
        command={plantCommand(cfg)}
      />
      <CopyBlock
        title="Watch the class"
        hint="Opens an SSH socket to every focused host and both LAN routers, then keeps them. Every few seconds it prints who is logged in and the last lines of the student history. Same output is marked unchanged. Ctrl-C stops the printing. The sockets stay. Agents are separate: sessions in the operator only lists hosts where a callback is running."
        command={watchCommand(cfg.student)}
      />

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Roster</h2>
        {dupes.size > 0 ? (
          <p className="text-sm text-primary">Two rows share {Array.from(dupes).join(", ")}. Watch uses the first. Fanout still opens both until you change one.</p>
        ) : null}
        <div className="flex flex-col gap-3">
          {cfg.hosts.map((host) => (
            <div key={host.id} className="grid gap-2 rounded-xl border border-border bg-surface p-3 sm:grid-cols-6 sm:items-end">
              <Mini id={`${host.id}-name`} label="Name" value={host.name} onChange={(name) => patchHost(host.id, { name })} />
              <Mini id={`${host.id}-os`} label="OS" value={host.os} onChange={(os) => patchHost(host.id, { os })} />
              <Mini id={`${host.id}-address`} label="Address" value={host.address} onChange={(address) => patchHost(host.id, { address })} />
              <label className="flex flex-col gap-2 text-sm text-muted">
                Port
                <input
                  inputMode="numeric"
                  value={String(host.port)}
                  onChange={(event) => {
                    const next = Number(event.target.value.replace(/[^0-9]/g, ""));
                    if (Number.isFinite(next)) patchHost(host.id, { port: Math.min(next, 65535) });
                  }}
                  className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
                />
              </label>
              <Mini id={`${host.id}-ssh`} label="SSH user" value={host.sshUser} onChange={(sshUser) => patchHost(host.id, { sshUser })} />
              <label className="flex min-h-11 items-center gap-2 text-sm text-fg">
                <input
                  type="checkbox"
                  checked={host.focus}
                  onChange={(event) => patchHost(host.id, { focus: event.target.checked })}
                  className="size-4"
                />
                Fanout
              </label>
              {host.note ? <p className="text-sm text-muted sm:col-span-6">{host.note}</p> : null}
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">On the host, after the agent is up</h2>
        <p className="max-w-3xl text-sm leading-relaxed text-muted">
          These run through the callback, as root on Linux. The student stays <span className="font-mono text-fg">{cfg.student || "defender"}</span>. You move to a service account once they find the first one. The Linux account password is printed on your console and is not inside the tasking. The shadow file gets the hash. Windows <span className="font-mono text-fg">net user</span> cannot take a hash, so that password does travel in the clear. Prefer the Linux account when the class is decoding live.
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Mini label="Student" value={cfg.student} onChange={(student) => onChange({ student })} />
          <Mini label="Service account" value={cfg.actor} onChange={(actor) => onChange({ actor })} />
          <label className="flex flex-col gap-2 text-sm text-muted">
            Login shell
            <select
              value={cfg.shell}
              onChange={(event) => onChange({ shell: event.target.value as BenchConfig["shell"] })}
              className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 text-fg"
            >
              <option value="vi">vi</option>
              <option value="python">python</option>
              <option value="perl">perl</option>
            </select>
          </label>
          <Mini label="wall -n" value={cfg.wall} onChange={(wall) => onChange({ wall })} />
        </div>
        <CopyBlock
          title="What you type"
          hint="One agent selected. history shows what they are hunting. shell is usermod -s. cloak copies bash over false and nologin. veil wraps ps, ss, netstat, w, and who. htop, top, and last stay unwrapped. stamp is touch -r against /bin/ls. boot logs the student off. play logs zeroes auth, syslog, nginx, wtmp, and the journal, and leaves bash history. tty is a real terminal, so nano works there. Ctrl-] leaves it. get and put move one file if you would rather edit it on this machine."
          command={tradecraftScript(cfg)}
        />
      </div>
    </section>
  );
}

function Mini({
  label,
  value,
  onChange,
  id,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  id?: string;
}) {
  const fieldId = id || label.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return (
    <label className="flex flex-col gap-2 text-sm text-muted" htmlFor={fieldId}>
      {label}
      <input
        id={fieldId}
        value={value}
        spellCheck={false}
        suppressHydrationWarning
        onChange={(event) => onChange(event.target.value)}
        className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
      />
    </label>
  );
}
