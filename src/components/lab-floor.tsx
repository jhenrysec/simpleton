import { useState } from "react";
import { Check, Copy } from "lucide-react";
import {
  tradecraftScript,
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
}: {
  cfg: BenchConfig;
  onChange: (partial: Partial<BenchConfig>) => void;
}) {
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

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">Path into the lab</h2>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">
          Ocelot talks to the WAN router, and that router is the hop to every host. The kit download includes this roster. You do not copy a second file.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Mini label="WAN user" value={cfg.wanUser} onChange={(wanUser) => onChange({ wanUser })} />
      </div>

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
