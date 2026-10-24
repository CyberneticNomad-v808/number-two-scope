# SpiderFoot OSINT API Keys Reference

> **Source:** `api_key_hunter.ipynb` — ALL_116_SERVICES catalog
> **Generated:** 2026-03-07
> **Account:** `api-manager@blking.net`
> **Temp Email:** `agogfze@mailto.plus` → check at https://tempmail.plus/
> **1Password Vault:** `LOCAL_DEV_VAULT` → Item: `OSINT Free API Keys`

---

## Summary

| Metric | Count |
|--------|-------|
| Total modules requiring API keys | 114 |
| Free tier | 38 |
| Freemium tier | 30 |
| Paid tier | 40 |
| Mixed/N/A | 6 |
| Categories | 11 |

---

## Top 10 Priority Keys (Configure First)

1. **VirusTotal** — Malware detection & file reputation
2. **Shodan** — Internet search & device enumeration
3. **HaveIBeenPwned** — Breach database searches
4. **SecurityTrails** — WHOIS & DNS history
5. **Hunter.io** — Email discovery
6. **Censys** — Internet scanning & certificate data
7. **AlienVault OTX** — Threat intelligence feeds
8. **CertSpotter** — SSL certificate monitoring
9. **Cisco Umbrella** — Malware & phishing detection
10. **IPInfo.io** — IP geolocation & metadata

---

## 1. Security & Threat Intelligence

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 1 | AbuseIPDB | `sfp_abuseipdb` | `api_key` | Free | High | https://www.abuseipdb.com/register |
| 2 | AlienVault OTX | `sfp_alienvault` | `api_key` | Free | High | https://otx.alienvault.com/#signup |
| 3 | GreyNoise | `sfp_greynoise` | `api_key` | Freemium | High | https://www.greynoise.io/viz/signup |
| 4 | GreyNoise Community | `sfp_greynoise_community` | `api_key` | Free | High | https://www.greynoise.io/community |
| 5 | Hybrid Analysis | `sfp_hybrid_analysis` | `api_key` | Free | Medium | https://www.hybrid-analysis.com/signup |
| 6 | Mandiant Threat Intel | `sfp_mandiant_ti` | `api_key` | Paid | Medium | — |
| 7 | Recorded Future | `sfp_recordedfuture` | `api_key` | Paid | High | — |
| 8 | SHODAN | `sfp_shodan` | `api_key` | Paid | High | https://account.shodan.io/register |
| 9 | VirusTotal | `sfp_virustotal` | `api_key` | Freemium | High | https://www.virustotal.com/gui/join-us |
| 10 | Pulsedive | `sfp_pulsedive` | `api_key` | Free | Medium | https://pulsedive.com/register |

### Notes
- **VirusTotal**: Sign in with Google SSO, then navigate to API key page
- **GreyNoise Community**: Free community API key after signup, separate from enterprise
- **Pulsedive**: Email signup, API key in profile
- **SHODAN**: Paid but sometimes offers free academic/developer keys

---

## 2. Search & Discovery

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 11 | BinaryEdge | `sfp_binaryedge` | `binaryedge_api_key` | Freemium | Medium | https://app.binaryedge.io/sign-up |
| 12 | Bing Search | `sfp_bingsearch` | `api_key` | Paid | Medium | — |
| 13 | Bing Shared IPs | `sfp_bingsharedip` | `api_key` | Paid | Low | — |
| 14 | Censys | `sfp_censys` | `censys_api_key_uid`, `censys_api_key_secret` | Freemium | High | https://censys.io/register |
| 15 | Google Search | `sfp_googlesearch` | `api_key` | Paid | High | — |
| 16 | Google Maps | `sfp_googlemaps` | `api_key` | Paid | Low | — |
| 17 | Google Safe Browsing | `sfp_googlesafebrowsing` | `api_key` | Free | Medium | https://console.cloud.google.com/ |
| 18 | Project Discovery | `sfp_projectdiscovery` | `api_key` | Freemium | Medium | https://cloud.projectdiscovery.io/ |
| 19 | ZoomEye | `sfp_zoomeye` | `api_key` | Paid | Medium | https://www.zoomeye.org/register |

### Notes
- **Censys**: 50 queries/month free — requires both UID and Secret
- **Google Safe Browsing**: Requires Google Cloud account, enable Safe Browsing API

---

## 3. Blockchain & Cryptocurrency

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 20 | Advanced Blockchain | `sfp_blockchain_analytics` | `blockcypher_api_key`, `etherscan_api_key` | Mixed | Low | — |
| 21 | Arbitrum | `sfp_arbitrum` | `api_key` | Free | Low | — |
| 22 | Bitcoin WhoIsWho | `sfp_bitcoinwhoswho` | `api_key` | Freemium | Low | — |
| 23 | BNB Chain | `sfp_bnb` | `api_key` | Free | Low | — |
| 24 | Ethereum | `sfp_ethereum` | `api_key` | Free | Low | — |
| 25 | Etherscan | `sfp_etherscan` | `api_key` | Free | Medium | https://etherscan.io/register |
| 26 | Tron | `sfp_tron` | `api_key` | Free | Low | — |

### Notes
- **Etherscan**: Email signup, API key in My API-KEYs section
- **Arbitrum/BNB/Tron**: Same pattern as Etherscan — register on their respective block explorers

---

## 4. Email & Identity

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 27 | Dehashed | `sfp_dehashed` | `api_key_username`, `api_key` | Paid | High | — |
| 28 | EmailCrawlr | `sfp_emailcrawlr` | `api_key` | Paid | Medium | — |
| 29 | EmailRep | `sfp_emailrep` | `api_key` | Free | Medium | https://emailrep.io/key |
| 30 | FullContact | `sfp_fullcontact` | `api_key` | Paid | Medium | — |
| 31 | HaveIBeenPwned | `sfp_haveibeenpwned` | `api_key` | Free | High | https://haveibeenpwned.com/API/Key |
| 32 | Hunter.io | `sfp_hunter` | `api_key` | Freemium | High | https://hunter.io/users/sign_up |
| 33 | LeakCheck | `sfp_leakcheck` | `api_key` | Paid | High | — |
| 34 | LeakIX | `sfp_leakix` | `api_key` | Free | Medium | https://leakix.net/ |
| 35 | Snov.io | `sfp_snov` | `api_key_client_id`, `api_key_client_secret` | Freemium | Medium | — |

### Notes
- **EmailRep**: Just enter email, key sent immediately
- **HaveIBeenPwned**: Listed as Free in catalog but actually requires $3.50/month minimum
- **Hunter.io**: Email signup, API key in account settings — 25 searches/month free
- **LeakIX**: Free API key after account creation

---

## 5. Domain & DNS

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 36 | CertSpotter | `sfp_certspotter` | `api_key` | Free | High | https://sslmate.com/certspotter/pricing |
| 37 | CIRCL.LU | `sfp_circllu` | `api_key_login`, `api_key_password` | Free | Medium | — |
| 38 | Cisco Umbrella | `sfp_cisco_umbrella` | `api_key` | Paid | High | — |
| 39 | DNSGrep | `sfp_dnsgrep` | *(CSRF auto-managed)* | Free | Low | — |
| 40 | HostIO | `sfp_hostio` | `api_key` | Freemium | Medium | — |
| 41 | JsonWHOIS.com | `sfp_jsonwhoiscom` | `api_key` | Freemium | Low | — |
| 42 | SecurityTrails | `sfp_securitytrails` | `api_key` | Paid | High | https://securitytrails.com/app/signup |
| 43 | ViewDNS.info | `sfp_viewdns` | `api_key` | Freemium | Medium | https://viewdns.info/api/ |
| 44 | WhoisFreaks | `sfp_whoisfreaks` | `api_key` | Freemium | Medium | — |
| 45 | Whoisology | `sfp_whoisology` | `api_key` | Paid | Medium | — |
| 46 | Whoxy | `sfp_whoxy` | `api_key` | Freemium | Low | — |
| 47 | ZoneFile.io | `sfp_zonefiles` | `api_key` | Paid | Low | — |
| 48 | Zetalytics | `sfp_zetalytics` | `api_key` | Paid | Low | — |

### Notes
- **CertSpotter**: Free tier available, API key after signup
- **CIRCL.LU**: Requires both login and password credentials
- **DNSGrep**: No key needed — CSRF auto-managed

---

## 6. IP & Geolocation

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 49 | AbstractAPI | `sfp_abstractapi` | `companyenrichment_api_key`, `phonevalidation_api_key`, `ipgeolocation_api_key` | Freemium | Medium | — |
| 50 | CriminalIP | `sfp_criminalip` | `api_key` | Freemium | High | https://www.criminalip.io/ |
| 51 | Fraudguard | `sfp_fraudguard` | `fraudguard_api_key_account`, `fraudguard_api_key_password` | Paid | Medium | — |
| 52 | IPInfo.io | `sfp_ipinfo` | `api_key` | Freemium | High | https://ipinfo.io/signup |
| 53 | IPQualityScore | `sfp_ipqualityscore` | `api_key` | Freemium | Medium | https://www.ipqualityscore.com/create-account |
| 54 | IP Registry | `sfp_ipregistry` | `api_key` | Freemium | Medium | — |
| 55 | IPStack | `sfp_ipstack` | `api_key` | Freemium | Medium | — |
| 56 | ipapi.com | `sfp_ipapicom` | `api_key` | Freemium | Medium | — |
| 57 | iknowwhatyoudownload | `sfp_iknowwhatyoudownload` | `api_key` | Paid | Low | — |
| 58 | Netlas | `sfp_netlas` | `api_key` | Freemium | Medium | — |
| 59 | NetworksDB | `sfp_networksdb` | `api_key` | Paid | Low | — |
| 60 | spur.us | `sfp_spur` | `api_key` | Paid | Low | — |
| 61 | UnwiredLabs | `sfp_unwiredlabs` | `api_key` | Free | Low | — |

### Notes
- **AbstractAPI**: Has 3 separate API keys for different endpoints
- **IPInfo.io**: 50k requests/month free
- **CriminalIP**: Generous free tier after signup

---

## 7. Social Media & Communication

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 62 | Bluesky | `sfp_bluesky` | `access_token` | Free | Low | — |
| 63 | Discord | `sfp_discord` | `bot_token` | Free | Low | — |
| 64 | Instagram | `sfp_instagram` | `access_token` | Paid | Low | — |
| 65 | Mastodon | `sfp_mastodon` | `access_token` | Free | Low | — |
| 66 | Matrix | `sfp_matrix` | `access_token` | Free | Low | — |
| 67 | Mattermost | `sfp_mattermost` | `access_token` | Free | Low | — |
| 68 | Reddit | `sfp_reddit` | `client_secret`, `client_id` | Free | Medium | — |
| 69 | Rocket.Chat | `sfp_rocketchat` | `access_token` | Free | Low | — |
| 70 | Social Links | `sfp_sociallinks` | `api_key` | Paid | Low | — |
| 71 | Social Profiles | `sfp_socialprofiles` | `bing_api_key`, `google_api_key` | Paid | Medium | — |
| 72 | TikTok OSINT | `sfp_tiktok_osint` | `api_key`, `api_secret` | Free | Low | — |
| 73 | WeChat | `sfp_wechat` | `api_key` | Paid | Low | — |
| 74 | WhatsApp | `sfp_whatsapp` | `api_key` | Paid | Low | — |

### Notes
- **Discord**: Create a bot application at https://discord.com/developers/applications
- **Reddit**: Create an app at https://www.reddit.com/prefs/apps — requires both client_id and client_secret
- **Bluesky/Mastodon/Matrix**: Use personal access tokens from respective platforms

---

## 8. Business Intelligence

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 75 | BuiltWith | `sfp_builtwith` | `api_key` | Paid | Medium | — |
| 76 | c99 | `sfp_c99` | `api_key` | Paid | Low | — |
| 77 | Deepinfo | `sfp_deepinfo` | `api_key` | Paid | Low | — |
| 78 | Focsec | `sfp_focsec` | `api_key` | Paid | Low | — |
| 79 | Fofa | `sfp_fofa` | `api_key` | Freemium | Medium | — |
| 80 | FullHunt | `sfp_fullhunt` | `api_key` | Paid | Medium | https://fullhunt.io/ |
| 81 | Leak-Lookup (Citadel) | `sfp_citadel` | `api_key` | Paid | High | — |
| 82 | Luminar | `sfp_luminar` | `api_key` | Paid | Low | — |
| 83 | NameAPI | `sfp_nameapi` | `api_key` | Paid | Low | — |
| 84 | numverify | `sfp_numverify` | `api_key` | Freemium | Low | — |
| 85 | NeutrinoAPI | `sfp_neutrinoapi` | `api_key` | Freemium | Low | — |
| 86 | OpenCorporates | `sfp_opencorporates` | `api_key` | Freemium | Low | — |
| 87 | Onyphe | `sfp_onyphe` | `api_key` | Freemium | Medium | https://www.onyphe.io/ |
| 88 | RocketReach | `sfp_rocketreach` | `api_key` | Paid | Medium | — |
| 89 | Seon | `sfp_seon` | `api_key` | Paid | Low | — |
| 90 | StackOverflow | `sfp_stackoverflow` | `api_key` | Free | Low | — |
| 91 | WhatCMS | `sfp_whatcms` | `api_key` | Freemium | Low | — |

---

## 9. Malware & Security Analysis

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 92 | Grayhat Warfare | `sfp_grayhatwarfare` | `api_key` | Paid | Low | — |
| 93 | Koodous | `sfp_koodous` | `api_key` | Free | Low | — |
| 94 | MalwarePatrol | `sfp_malwarepatrol` | `api_key` | Freemium | Low | — |
| 95 | MetaDefender | `sfp_metadefender` | `api_key` | Freemium | Low | — |
| 96 | Project Honey Pot | `sfp_honeypot` | `api_key` | Free | Low | — |

---

## 10. Communication & Specialized

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 97 | Twilio | `sfp_twilio` | `api_key_account_sid`, `api_key_auth_token` | Paid | Low | — |
| 98 | TextMagic | `sfp_textmagic` | `api_key_username`, `api_key` | Paid | Low | — |
| 99 | Onion.link | `sfp_onioncity` | `api_key` | Paid | Low | — |
| 100 | WiGLE | `sfp_wigle` | `api_key_encoded` | Free | Low | — |
| 101 | API Key Leak Detector | `sfp_apileak` | `github_token` | Free | Low | — |
| 102 | AI Summary | `sfp_ai_summary` | `api_key` | Paid | Low | — |
| 103 | BotScout | `sfp_botscout` | `api_key` | Free | Low | — |
| 104 | F-Secure Riddler.io | `sfp_fsecure_riddler` | `password` | Paid | Low | — |
| 105 | IntelligenceX | `sfp_intelx` | `api_key` | Paid | High | https://intelx.io/signup |
| 106 | PasteBin | `sfp_pastebin` | `api_key` | Freemium | Medium | https://pastebin.com/doc_scraping_api |
| 107 | XForce Exchange | `sfp_xforce` | `xforce_api_key`, `xforce_api_key_password` | Paid | Medium | — |

---

## 11. Tools (External Binaries)

| # | Service | Module | Config Key(s) | Tier | Priority | Signup URL |
|---|---------|--------|---------------|------|----------|------------|
| 108 | Tool - Nmap | `sfp_tool_nmap` | `remote_password` | N/A | Medium | — |
| 109 | Tool - Nuclei | `sfp_tool_nuclei` | `remote_password` | N/A | Medium | — |
| 110 | Tool - Gobuster | `sfp_tool_gobuster` | `remote_password` | N/A | Low | — |
| 111 | Tool - PhoneInfoga | `sfp_tool_phoneinfoga` | `api_key`, `remote_password` | Free | Low | — |
| 112 | Tool - Wappalyzer | `sfp_tool_wappalyzer` | `wappalyzer_api_key` | Paid | Low | — |

---

## 12. Storage (Internal)

| # | Service | Module | Config Key(s) | Tier | Priority |
|---|---------|--------|---------------|------|----------|
| 113 | Database Storage | `sfp__stor_db` | `postgresql_password` | N/A | N/A |
| 114 | ElasticSearch Storage | `sfp__stor_elasticsearch` | `api_key`, `password` | N/A | N/A |

---

## SpiderFoot Config Key Mapping

Quick-reference for the `module:config_key` format used in SpiderFoot's database:

```
sfp_abuseipdb:api_key
sfp_alienvault:api_key
sfp_binaryedge:binaryedge_api_key
sfp_censys:censys_api_key_uid
sfp_censys:censys_api_key_secret
sfp_certspotter:api_key
sfp_criminalip:api_key
sfp_emailrep:api_key
sfp_etherscan:api_key
sfp_fullhunt:api_key
sfp_googlesafebrowsing:api_key
sfp_greynoise:api_key
sfp_greynoise_community:api_key
sfp_haveibeenpwned:api_key
sfp_hunter:api_key
sfp_hybrid_analysis:api_key
sfp_intelx:api_key
sfp_ipinfo:api_key
sfp_ipqualityscore:api_key
sfp_leakix:api_key
sfp_onyphe:api_key
sfp_pastebin:api_key
sfp_pulsedive:api_key
sfp_securitytrails:api_key
sfp_shodan:api_key
sfp_viewdns:api_key
sfp_virustotal:api_key
```

---

## Configuration Methods

### Method 1: Web UI (Recommended)
1. Navigate to `Settings` → `Module Settings`
2. Find the module and enter the API key
3. Save — keys are encrypted automatically

### Method 2: Environment Variables
```bash
export VIRUSTOTAL_API_KEY="your_key_here"
export SHODAN_API_KEY="your_key_here"
export HUNTER_API_KEY="your_key_here"
```

### Method 3: .env File
```bash
VIRUSTOTAL_API_KEY=your_virustotal_key
SHODAN_API_KEY=your_shodan_key
CENSYS_API_KEY_UID=your_censys_uid
CENSYS_API_KEY_SECRET=your_censys_secret
HUNTER_API_KEY=your_hunter_key
```

### Method 4: 1Password CLI
```bash
# Read a key
op item get "OSINT Free API Keys" --vault LOCAL_DEV_VAULT --fields "Security.abuseipdb :: sfp_abuseipdb :: api_key"

# Update a key
op item edit "OSINT Free API Keys" --vault LOCAL_DEV_VAULT \
  'Security.abuseipdb :: sfp_abuseipdb :: api_key[password]=YOUR_ACTUAL_KEY'
```

---

## Security Best Practices

- Keys stored in SpiderFoot DB are Fernet-encrypted (`enc:` prefix)
- Use env vars in production — keys never touch disk
- Use unique keys per environment (dev/staging/prod)
- Many free tiers have daily/monthly rate limits — monitor usage
- Rotate keys periodically

## Verification Checklist

Before running full scans:
- [ ] API key correctly formatted
- [ ] Key still active (not revoked)
- [ ] Rate limits suitable for use case
- [ ] Test endpoint returns valid response
- [ ] Key has required permissions/scopes
