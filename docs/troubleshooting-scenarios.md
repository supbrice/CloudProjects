# Troubleshooting scenarios (CPS network)

Five problems I actually worked through on this style of build. Addresses are **sanitized** to match [`vlan-plan.md`](vlan-plan.md). Client-sized site — not a fake 10,000-user campus.

Each scenario: **symptom → checks → root cause → fix → how I proved it**.

---

## 1) DNS  staff browse OK, guest “works” but apps fail oddly

**Symptom**  
Corporate (VLAN 10) resolved internal and internet names. Public (VLAN 20) could open some sites but lookups were slow or hit the corporate resolver by mistake after an SSID/VLAN change.

**Checks**
- From a staff PC: `nslookup cps.internal` and a public name; DNS server should be `10.10.10.1`.
- - From a guest client: DNS should be public resolvers only (`1.1.1.1` / `9.9.9.9`), **not** `10.10.10.1`.
  - - Confirm SSID → VLAN map (CPS-Guest → VLAN 20) on the AP trunk.
   
    - **Root cause**
    - Guest DHCP still handed out the corporate DNS option after the VLAN cutover, so guest traffic depended on a resolver it should never reach (and isolation rules blocked it inconsistently).
   
    - **Fix**
    - Set DHCP option 006 on VLAN 20 to public DNS only; remove corporate DNS from the guest scope. Keep guest client isolation on.
   
    - **Proof**
    - Guest `nslookup` shows `1.1.1.1`/`9.9.9.9`. Guest cannot TCP to `10.10.10.1:53`. Staff DNS unchanged.
   
    - ---
    ## 2) DHCP — new drop on VLAN 10 gets an address that can’t reach the gateway

    **Symptom**
    Printer/PC on a “Corporate” jack got a lease but default gateway ping failed. Same switch, other ports fine.

    **Checks**
    - `ipconfig` / `ip route`: lease range, gateway, DNS.
    - - Switchport mode: should be **access VLAN 10**, not an old trunk or wrong access VLAN.
      - - Compare to plan: corporate scope `10.10.10.50–199`, gateway `10.10.10.1`.
       
        - **Root cause**
        - Port left as access VLAN 20 (or untagged wrong VLAN) after cabling work. Client DHCP’d on the public scope while the user expected corporate.
       
        - **Fix**
        - Set port to Access-Corp (VLAN 10). Bounce the client. Confirm scope options match [`vlan-plan.md`](vlan-plan.md).
       
        - **Proof**
        - Client gets `10.10.10.x`, gateway `10.10.10.1`, DNS `10.10.10.1`. Ping gateway + resolve `cps.internal`.
       
        - ---

        ## 3) VLAN isolation — OT signage can still hit a staff printer

        **Symptom**
        After “segmentation,” a signage player on VLAN 30 could still ARP/TCP toward a corporate printer on VLAN 10.

        **Checks**
        - From OT client: traceroute / TCP to `10.10.10.0/24`.
        - - Gateway firewall: inter-VLAN policy should **deny** OT → Corporate.
          - - Confirm player is really on VLAN 30 (not corporate Wi-Fi with a static IP that looks “OT”).
           
          - **Root cause**
          - Missing or inverted firewall rule on the UniFi gateway (allow-any leftover) between VLAN 30 and VLAN 10.
         
          - **Fix**
          - Default deny inter-VLAN; allow only OT → approved vendor destinations via NAT. Corporate → OT stays deny except jump host on VLAN 99.
         
          - **Proof**
          - OT client fails to `10.10.10.1:53` and to a known printer IP. OT still reaches its vendor HTTPS target. See [`configs/unifi/firewall-and-nat.md`](../configs/unifi/firewall-and-nat.md).
         
          - ---

          ## 4) “VPN / vendor path” — fleet trackers show WAN up, vendor portal down from VLAN 50

          **Symptom**
          Internet from corporate worked. Fleet gateways on VLAN 50 could not reach the vendor-hosted tracking URL. People said “VPN is down”; WAN light was fine.

          **Checks**
          - From VLAN 50 host: DNS to vendor hostname, then HTTPS.
          - - From corporate: same vendor URL (control).
            - - NAT/firewall: does VLAN 50 have specific outbound allow + NAT?
              - - QoS: fleet queue not starved by Protect camera bursts.
               
                - **Root cause**
                - Not a site-to-site VPN failure — **missing outbound allow/NAT for VLAN 50** to the vendor destination (or DNS on VLAN 50 pointed at a resolver OT could not use). WAN up ≠ OT path up.
               
                - **Fix**
                - Add explicit outbound allow for fleet VLAN to vendor endpoints; NAT to WAN; keep deny to corporate/public. Verify DNS on `10.10.50.1`.
               
                - **Proof**
                - Vendor URL loads from VLAN 50 only. Corporate still cannot be reached from fleet. WAN tests from VLAN 10 still pass.
               
                - ---
                ## 5) Layer 2 / UniFi — switch or camera stuck adopting / flapping to an old controller

                **Symptom**
                Device cycled Adopting → Offline → back on an old inform host. New site controller never stayed Connected.

                **Checks**
                - Device shell `info`: inform URL.
                - - VLAN: switches/APs on 99, cameras on 60 with PoE.
                  - - Only **one** controller should adopt.
                   
                    - **Root cause**
                    - Stale inform URL in NVRAM + L2 discovery fighting the new gateway DHCP/inform.
                   
                    - **Fix**
                    - Factory NVRAM reset → correct VLAN/address → single `set-inform` to current controller → adopt once. Full runbook: [`adoption-and-validation.md`](adoption-and-validation.md).
                   
                    - **Proof**
                    - Controller shows Connected; `info` shows only the new inform URL; uplink trunk carries planned VLANs; camera PoE draw matches [`poe-budget.csv`](poe-budget.csv).
                   
                    - ---

                    ## Interview cheat-sheet

                    | Theme | Scenario |
                    | --- | --- |
                    | DNS | #1 |
                    | DHCP | #2 |
                    | VLAN / segmentation | #3 |
                    | VPN / vendor / NAT path | #4 |
                    | L2 adoption / switching | #5 |

                    When talking this through: say what you **measured**, what you **changed**, and what **pass** looked like — not that the site was “enterprise scale.
