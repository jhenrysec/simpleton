import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Check, Copy, Download, Lock, Radio } from "lucide-react";
import {
  CHANNELS,
  DEFAULT_CONFIG,
  PRESET_OPEN,
  PRESET_PRIVILEGED,
  linuxAgentCommand,
  needsPythonOnWindows,
  normalizeConfig,
  operatorCommand,
  windowsCommand,
  type BenchConfig,
  type Timing,
} from "@/lib/bench";
import { LabFloor } from "@/components/lab-floor";

export const Route = createFileRoute("/")({ component: Home });

const STORAGE_KEY = "range-bench";

function Home() {
  const [cfg, setCfg] = useState<BenchConfig>(DEFAULT_CONFIG);
  const [preset, setPreset] = useState<"class" | "open">("class");
  const [htmlName, setHtmlName] = useState("");
  const [htmlText, setHtmlText] = useState("");
  const [imageName, setImageName] = useState("");
  const [imageBytes, setImageBytes] = useState<Uint8Array | null>(null);
  const [uploadNote, setUploadNote] = useState("");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as Partial<BenchConfig> & { preset?: "class" | "open" };
      setCfg(normalizeConfig(saved));
      if (saved.preset === "open" || saved.preset === "class") setPreset(saved.preset);
    } catch {
      /* keep defaults */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...cfg, preset }));
  }, [cfg, preset]);

  const channel = CHANNELS.find((item) => item.id === cfg.channel) ?? CHANNELS[0];
  const tokenShort = cfg.token.trim().length > 0 && cfg.token.trim().length < 8;

  function patch(partial: Partial<BenchConfig>) {
    setCfg((current) => ({ ...current, ...partial }));
  }

  function applyPreset(next: "class" | "open") {
    setPreset(next);
    patch(next === "class" ? PRESET_PRIVILEGED : PRESET_OPEN);
  }

  function newToken() {
    const alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    const bytes = new Uint8Array(24);
    crypto.getRandomValues(bytes);
    patch({ token: Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join("") });
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 sm:py-10">
      <header className="flex flex-col gap-6 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="font-mono text-xs tracking-widest text-primary uppercase">Isolated lab only</p>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Range Bench</h1>
          <p className="max-w-2xl text-base leading-relaxed text-muted">
            One operator on the attacker VM, one agent on each student guest. Six readable
            callback channels, the same live shell, and a deface that also locks the page.
          </p>
        </div>
        <a
          href="/range-lab.zip"
          download
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-fg"
        >
          <Download className="size-4" aria-hidden="true" />
          Download kit
        </a>
      </header>

      <section className="grid gap-4 lg:grid-cols-5">
        <div className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-4 lg:col-span-2 sm:p-5">
          <h2 className="text-lg font-semibold">Lab settings</h2>
          <Field label="Attacker address" value={cfg.attacker} onChange={(attacker) => patch({ attacker })} />
          <div className="flex flex-col gap-2">
            <div className="flex items-end justify-between gap-3">
              <label className="text-sm text-muted" htmlFor="token">
                Lab token
              </label>
              <button type="button" className="min-h-11 px-2 text-sm text-primary" onClick={newToken}>
                Generate
              </button>
            </div>
            <input
              id="token"
              value={cfg.token}
              autoComplete="off"
              spellCheck={false}
              suppressHydrationWarning
              placeholder="at least 8 characters"
              onChange={(event) => patch({ token: event.target.value })}
              className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
            />
            {tokenShort ? (
              <p className="text-sm text-primary">Token must be at least 8 characters or the agent will refuse it.</p>
            ) : null}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Linux agent id" value={cfg.linuxId} onChange={(linuxId) => patch({ linuxId })} />
            <Field label="Windows agent id" value={cfg.windowsId} onChange={(windowsId) => patch({ windowsId })} />
          </div>
          <label className="flex flex-col gap-2 text-sm text-muted">
            Timing
            <select
              value={cfg.timing}
              onChange={(event) => patch({ timing: event.target.value as Timing })}
              className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 text-fg"
            >
              <option value="continuous">Continuous — stays up for the class</option>
              <option value="off">Off — no beacon until you turn it back on</option>
            </select>
            <p className="text-sm leading-relaxed text-muted">
              Continuous is the attacker for the whole exercise. TCP, WebSocket, and MQTT stay connected, so there is no poll clock. HTTP, DNS, and ICMP have to ask, about once a second, or a command cannot land. Off stops that beacon. Those three look again in about half an hour, which is how <span className="font-mono text-fg">profile continuous</span> gets through without a login.
            </p>
          </label>
          <div className="flex flex-col gap-2">
            <span className="text-sm text-muted">Ports</span>
            <div className="grid grid-cols-2 gap-2">
              <PresetButton active={preset === "class"} onClick={() => applyPreset("class")} label="Class ports" detail="443, 80, 53" />
              <PresetButton active={preset === "open"} onClick={() => applyPreset("open")} label="No sudo bind" detail="8443, 8088, 5353" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <PortField label="TCP" value={cfg.tcp} onChange={(tcp) => patch({ tcp })} />
            <PortField label="HTTP" value={cfg.http} onChange={(http) => patch({ http })} />
            <PortField label="DNS" value={cfg.dns} onChange={(dns) => patch({ dns })} />
            <PortField label="MQTT" value={cfg.mqtt} onChange={(mqtt) => patch({ mqtt })} />
            <PortField label="WebSocket" value={cfg.ws} onChange={(ws) => patch({ ws })} />
            <Field label="DNS zone" value={cfg.zone} onChange={(zone) => patch({ zone })} />
          </div>
          <Field
            label="Web root override"
            value={cfg.webroot}
            placeholder="blank = autodetect per guest"
            onChange={(webroot) => patch({ webroot })}
          />
        </div>

        <div className="flex flex-col gap-4 lg:col-span-3">
          <CommandCard title="Attacker" hint="Ubuntu operator. sudo is required for ports under 1024 and for ICMP." command={operatorCommand(cfg, { page: htmlName ? `deface/${htmlName}` : undefined, image: imageName ? `deface/${imageName}` : undefined })} />
          <CommandCard title="Linux guest" hint="Debian 9 or 12. sudo so the immutable flag can be set. Python 3.5 or newer, no packages." command={linuxAgentCommand(cfg)} />
          <CommandCard
            title="Windows 10 guest"
            hint={
              needsPythonOnWindows(cfg.channel)
                ? "PowerShell only speaks TCP, HTTP, and WebSocket. This channel needs range.py and Python on the guest."
                : "Stock PowerShell 5.1. Elevate the prompt if you want the ACL lock. The switch is -Timing, not -Profile."
            }
            command={windowsCommand(cfg)}
          />
        </div>
      </section>

      <LabFloor cfg={cfg} onChange={patch} htmlName={htmlName} htmlText={htmlText} imageName={imageName} imageBytes={imageBytes} />

      <section className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <Radio className="size-5 text-primary" aria-hidden="true" />
          <h2 className="text-lg font-semibold">Channel the class will see</h2>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {CHANNELS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => patch({ channel: item.id })}
              className={
                "min-h-11 rounded-xl border px-3 py-3 text-left text-sm font-medium " +
                (cfg.channel === item.id
                  ? "border-primary bg-surface text-primary"
                  : "border-border bg-surface text-fg")
              }
              aria-pressed={cfg.channel === item.id}
            >
              {item.label}
            </button>
          ))}
        </div>
        <article className="rounded-xl border border-border bg-surface p-4 sm:p-5">
          <h3 className="text-base font-semibold">{channel.label}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">{channel.tell}</p>
          <p className="mt-4 font-mono text-xs tracking-wide text-muted uppercase">Wireshark</p>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-sm text-fg">{channel.filter}</pre>
          <p className="mt-4 font-mono text-xs tracking-wide text-muted uppercase">Shape, not a capture</p>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-sm text-fg">{channel.shape}</pre>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:p-5">
          <div className="flex items-center gap-2">
            <Lock className="size-5 text-primary" aria-hidden="true" />
            <h2 className="text-lg font-semibold">Deface and lock</h2>
          </div>
          <p className="text-sm leading-relaxed text-muted">
            After <span className="font-mono text-fg">sessions</span> shows the guest, select it and run the play.
            The page heading becomes whatever your file says, or Defaced if you did not upload one. Linux then sets the immutable attribute. Windows sets read-only and a
            write deny. Say the brief out loud. Do not paste the fix into the guest.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm text-muted">
              index.html
              <input
                type="file"
                accept=".html,text/html"
                className="min-h-11 text-sm text-fg file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:text-fg"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  if (file.size > 200000) {
                    setUploadNote("That page is over 200KB. Trim it.");
                    return;
                  }
                  file.text().then((text) => {
                    const name = file.name.replace(/[^A-Za-z0-9._-]/g, "") || "index.html";
                    setHtmlName(name);
                    setHtmlText(text);
                    setUploadNote("");
                  });
                }}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted">
              Image next to the page
              <input
                type="file"
                accept="image/*"
                className="min-h-11 text-sm text-fg file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:text-fg"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  if (file.size > 350000) {
                    setUploadNote("That image is over 350KB. Use WebSocket, TCP, or MQTT, and keep it smaller.");
                    return;
                  }
                  file.arrayBuffer().then((buffer) => {
                    const name = file.name.replace(/[^A-Za-z0-9._-]/g, "") || "banner.png";
                    setImageName(name);
                    setImageBytes(new Uint8Array(buffer));
                    setUploadNote("Put the image in the same folder as index.html. Reference it with a relative src. DNS will carry it, slowly.");
                  });
                }}
              />
            </label>
          </div>
          {htmlName || imageName ? (
            <p className="text-sm text-muted">
              Unzip the path files so <span className="font-mono text-fg">deface/</span> sits next to range.py.
              {htmlName ? ` Page: ${htmlName}.` : ""}
              {imageName ? ` Image: ${imageName}.` : ""}
            </p>
          ) : null}
          {uploadNote ? <p className="text-sm text-primary">{uploadNote}</p> : null}
          <CommandCard title="What you say" hint="Safe to project." command="A site you control has changed. Capture the traffic, find the callback, and put the page back. If the editor will not save, that problem is on the host." />
          <CommandCard title="What you type" hint="One agent selected. If that guest is off, profile continuous first. HTTP, DNS, and ICMP hear that on the next quiet check." command={"use " + (cfg.linuxId || "web01") + "\nplay deface"} />
        </article>
        <article className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:p-5">
          <h2 className="text-lg font-semibold">What “done” looks like for them</h2>
          <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed text-muted">
            <li>The page and its mtime changed, and it was not an SSH session.</li>
            <li>The callback is one of the six patterns, with the command in hex or base64 inside a field that is the wrong size.</li>
            <li>The file itself is locked. Removing the callback process does not unlock it.</li>
            <li>The agent is still running, named range.py or range-agent.ps1. Stopping it is a separate step from restoring the page.</li>
          </ol>
          <details className="rounded-lg border border-border bg-surface-2 p-3">
            <summary className="min-h-11 cursor-pointer text-sm font-medium text-fg">Instructor key — remediation</summary>
            <div className="mt-3 flex flex-col gap-3 text-sm leading-relaxed text-muted">
              <p>
                Linux: <span className="font-mono text-fg">lsattr index.html</span> shows <span className="font-mono text-fg">i</span>.{" "}
                <span className="font-mono text-fg">chattr -i index.html</span>, then restore from their own copy or rewrite the page.
                If you kept a backup it is in the agent user’s <span className="font-mono text-fg">~/.range-lab/index.html.orig</span> (root: <span className="font-mono text-fg">/root/.range-lab</span>).
              </p>
              <p>
                Windows: <span className="font-mono text-fg">attrib</span> shows R, <span className="font-mono text-fg">icacls</span> shows a deny for Everyone (S-1-1-0).{" "}
                <span className="font-mono text-fg">attrib -R</span>, then <span className="font-mono text-fg">icacls index.html /remove:d *S-1-1-0</span>.
                Backup, if you kept one: <span className="font-mono text-fg">C:\ProgramData\RangeLab\index.html.orig</span>.
              </p>
              <p>
                <span className="font-mono text-fg">play undo</span> does both steps for you when the room is stuck.{" "}
                <span className="font-mono text-fg">play deface nobackup</span> leaves no side copy.{" "}
                <span className="font-mono text-fg">IMMUTABLE=failed</span> means that guest is not ext4 or the agent is not root — the page still changes, the lock does not.
              </p>
            </div>
          </details>
        </article>
      </section>

      <footer className="border-t border-border pt-4 text-sm leading-relaxed text-muted">
        Run <span className="font-mono text-fg">python3 range.py selftest</span> on the attacker before class.
        Pass means TCP, HTTP, DNS, MQTT, and WebSocket round-tripped a real deface and restore on loopback.
        ICMP needs a raw socket, so it only comes up under sudo on Linux. Nothing here listens outside the VM network you point it at.
      </footer>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const id = label.replace(/\s+/g, "-").toLowerCase();
  return (
    <label className="flex flex-col gap-2 text-sm text-muted" htmlFor={id}>
      {label}
      <input
        id={id}
        value={value}
        placeholder={placeholder}
        spellCheck={false}
        suppressHydrationWarning
        onChange={(event) => onChange(event.target.value)}
        className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
      />
    </label>
  );
}

function PortField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="flex flex-col gap-2 text-sm text-muted">
      {label}
      <input
        inputMode="numeric"
        value={String(value)}
        suppressHydrationWarning
        onChange={(event) => {
          const next = Number(event.target.value.replace(/[^0-9]/g, ""));
          if (Number.isFinite(next)) onChange(Math.min(next, 65535));
        }}
        className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 font-mono text-sm text-fg"
      />
    </label>
  );
}

function PresetButton({
  active,
  onClick,
  label,
  detail,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  detail: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "min-h-11 rounded-lg border px-3 py-2 text-left " +
        (active ? "border-primary text-primary" : "border-border text-fg")
      }
      aria-pressed={active}
    >
      <span className="block text-sm font-medium">{label}</span>
      <span className="block font-mono text-xs text-muted">{detail}</span>
    </button>
  );
}

function CommandCard({ title, hint, command }: { title: string; hint: string; command: string }) {
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
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 font-mono text-sm leading-relaxed text-fg">
        {command}
      </pre>
    </section>
  );
}
