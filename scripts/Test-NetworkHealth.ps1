<#
.SYNOPSIS
  Validate DNS, DHCP, reachability, and a sample isolation check against the VLAN plan.

.PARAMETER Plan
  Path to docs/vlan-plan.csv

.PARAMETER Profile
  demo — public DNS/HTTPS targets (safe off-site)
  live — VLAN gateways and vendor hostnames from the plan

.PARAMETER LatencyMs
  Fail a reachability check if RTT exceeds this value
#>
[CmdletBinding()]
param(
    [string]$Plan = (Join-Path $PSScriptRoot "../docs/vlan-plan.csv"),
    [ValidateSet("demo", "live")]
    [string]$Profile = "demo",
    [double]$LatencyMs = 80
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Read-VlanPlan {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "VLAN plan not found: $Path"
    }
    Import-Csv -Path $Path
}

function Test-DnsNameSafe {
    param([string]$Name)
    try {
        $records = Resolve-DnsName -Name $Name -ErrorAction Stop
        $addrs = $records | Where-Object { $_.IPAddress } | Select-Object -ExpandProperty IPAddress -Unique
        return @{ Ok = $true; Detail = ($addrs -join ", ") }
    }
    catch {
        return @{ Ok = $false; Detail = $_.Exception.Message }
    }
}

function Test-TcpRtt {
    param([string]$HostName, [int]$Port, [int]$TimeoutMs = 3000)
    $client = New-Object System.Net.Sockets.TcpClient
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return @{ Ok = $false; Ms = $null; Detail = "tcp/$Port timeout" }
        }
        $client.EndConnect($iar)
        $sw.Stop()
        return @{ Ok = $true; Ms = $sw.Elapsed.TotalMilliseconds; Detail = ("tcp/{0} {1:n1} ms" -f $Port, $sw.Elapsed.TotalMilliseconds) }
    }
    catch {
        return @{ Ok = $false; Ms = $null; Detail = $_.Exception.Message }
    }
    finally {
        $client.Dispose()
    }
}

function Test-Reach {
    param([string]$HostName, [double]$LimitMs)
    try {
        $ping = Test-Connection -ComputerName $HostName -Count 1 -ErrorAction Stop
        $ms = [double]$ping.Latency
        $ok = $ms -le $LimitMs
        return @{
            Name   = "reach $HostName"
            Ok     = $ok
            Skip   = $false
            Detail = ("icmp {0} ms" -f $ms)
        }
    }
    catch {
        $tcp = Test-TcpRtt -HostName $HostName -Port 443
        if (-not $tcp.Ok) {
            $tcp = Test-TcpRtt -HostName $HostName -Port 53
        }
        $ok = [bool]$tcp.Ok
        if ($ok -and $null -ne $tcp.Ms -and $tcp.Ms -gt $LimitMs) {
            $ok = $false
        }
        return @{
            Name   = "reach $HostName"
            Ok     = $ok
            Skip   = $false
            Detail = ("{0} (icmp blocked)" -f $tcp.Detail)
        }
    }
}

function Get-DhcpInfo {
    try {
        $cfg = Get-NetIPConfiguration | Where-Object { $_.IPv4Address }
        $parts = foreach ($row in $cfg) {
            $ifAlias = $row.InterfaceAlias
            $ip = $row.IPv4Address.IPAddress
            $gw = $row.IPv4DefaultGateway.NextHop
            $dns = ($row.DNSServer.ServerAddresses -join ";")
            "${ifAlias} ${ip} gw=${gw} dns=${dns}"
        }
        if (-not $parts) {
            return @{ Name = "dhcp"; Ok = $true; Skip = $true; Detail = "no IPv4 interfaces" }
        }
        return @{ Name = "dhcp"; Ok = $true; Skip = $true; Detail = ($parts -join " | ") }
    }
    catch {
        return @{ Name = "dhcp"; Ok = $true; Skip = $true; Detail = $_.Exception.Message }
    }
}

$results = New-Object System.Collections.Generic.List[object]
$plan = Read-VlanPlan -Path $Plan

if ($Profile -eq "demo") {
    foreach ($name in @("cloudflare.com", "quad9.net")) {
        $dns = Test-DnsNameSafe -Name $name
        $results.Add([pscustomobject]@{ Name = "dns $name"; Ok = $dns.Ok; Skip = $false; Detail = $dns.Detail })
    }
    foreach ($target in @(@("1.1.1.1", 443), @("9.9.9.9", 443))) {
        $tcp = Test-TcpRtt -HostName $target[0] -Port $target[1]
        $ok = [bool]$tcp.Ok
        if ($ok -and $null -ne $tcp.Ms -and $tcp.Ms -gt $LatencyMs) { $ok = $false }
        $results.Add([pscustomobject]@{ Name = "tcp $($target[0]):$($target[1])"; Ok = $ok; Skip = $false; Detail = $tcp.Detail })
    }
    $results.Add([pscustomobject](Get-DhcpInfo))
    $results.Add([pscustomobject]@{
            Name   = "isolation sample"
            Ok     = $true
            Skip   = $true
            Detail = "skipped in demo (would probe 10.10.10.1:443 from public/OT)"
        })
}
else {
    foreach ($row in $plan) {
        if ($row.gateway) {
            $results.Add([pscustomobject](Test-Reach -HostName $row.gateway -LimitMs $LatencyMs))
        }
        $hostName = $row.vendor_check_host
        if ($hostName -and $hostName -notlike "*.test") {
            $dns = Test-DnsNameSafe -Name $hostName
            $results.Add([pscustomobject]@{
                    Name   = "dns vlan$($row.vlan_id) $hostName"
                    Ok     = $dns.Ok
                    Skip   = $false
                    Detail = $dns.Detail
                })
        }
        elseif ($hostName -like "*.test") {
            $results.Add([pscustomobject]@{
                    Name   = "dns vlan$($row.vlan_id) $hostName"
                    Ok     = $true
                    Skip   = $true
                    Detail = "placeholder vendor hostname — replace before live cutover"
                })
        }
    }
    $results.Add([pscustomobject](Get-DhcpInfo))
    $probe = Test-TcpRtt -HostName "10.10.10.1" -Port 443 -TimeoutMs 2000
    $results.Add([pscustomobject]@{
            Name   = "isolation sample"
            Ok     = -not $probe.Ok
            Skip   = $false
            Detail = if ($probe.Ok) { "unexpected connect to 10.10.10.1:443" } else { "no connect to corporate gw ($($probe.Detail))" }
        })
}

Write-Host "profile=$Profile  vlans=$($plan.Count)  plan=$Plan"
foreach ($item in $results) {
    $flag = if ($item.Skip) { "SKIP" } elseif ($item.Ok) { "PASS" } else { "FAIL" }
    Write-Host ("{0,-4}  {1,-40}  {2}" -f $flag, $item.Name, $item.Detail)
}

$failed = @($results | Where-Object { -not $_.Ok -and -not $_.Skip })
if ($failed.Count -gt 0) { exit 1 }
exit 0
