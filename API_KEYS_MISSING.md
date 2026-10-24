# SpiderFoot — API Keys Still Needed

Generated 2026-08-28 by cross-checking every `module:field` in `SpiderFoot.cfg`
whose name contains `key`, `token`, or `secret` against which ones actually
hold a value. Service names, tiers, and signup URLs are pulled from
`OSINT_API_KEYS_REFERENCE.md`, which already documents 114 modules.

## Cross-check against the 1Password DEV_VAULT export

The vault item `number-two-scope-api-keys` holds the working set of OSINT
keys for this environment. Every value in it that maps to a SpiderFoot
module is already live in `SpiderFoot.cfg` (the 21 keys in
`.env.spiderfoot.live_keys.env`), except for three entries that needed a
closer look against the actual module code, not just the config file:

| OP entry | Value | Status |
|---|---|---|
| `urlscan` | `019c63bd-7cb8-7719-a9d1-c3ee209d0a26` | `sfp_urlscan.py` is installed, but it has **no `api_key` config option** — only `verify=1`. It only does unauthenticated lookups as written. This key can't be wired in without patching the module to add an authenticated request path. |
| `solscan` | (JWT token) | No `sfp_solscan.py` module exists anywhere in the 278 installed modules. Not usable by this SpiderFoot install as-is — would need a new module written first. |
| `botswot` | `2L1N06hGvotswFr` | Identical value to `botscout`, which is already configured. No `sfp_botswot` module exists — this is a duplicate/typo entry in 1Password, not a distinct key. |

The `io` field in that same item (`0x1234567890abcdef...`) is a sequential
placeholder-looking hex string, not tied to any labeled service — not
treated as a real key here.

**21 modules are already configured** (see `.env.spiderfoot.live_keys.env`).
**87 modules below have no key set.** Signup URLs marked "—" mean the
reference doc didn't have one on file; a best-guess URL is given where the
service is unambiguous, otherwise it's left blank.

Excluded from this list: `sfp_tool_*` remote SSH key fields (server access,
not an API signup), `sfp_dideo:keywords`, `sfp__stor_elasticsearch:api_key`
(internal storage, not a third-party service).

## Fix first (incomplete pair)

| Service | Module | Missing field | Signup |
|---|---|---|---|
| Censys | `sfp_censys` | `censys_api_key_uid` | https://censys.io/register — you already have the secret half; just need the UID from the same account |

## 1. Security & Threat Intelligence

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| Mandiant Threat Intel | `sfp_mandiant_ti` | `api_key` | Paid | No public self-serve signup — enterprise sales only |
| Recorded Future | `sfp_recordedfuture` | `api_key` | Paid | No public self-serve signup — enterprise sales only |

## 2. Search & Discovery

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| BinaryEdge | `sfp_binaryedge` | `binaryedge_api_key` | Freemium | https://app.binaryedge.io/sign-up |
| Bing Search | `sfp_bingsearch` | `api_key` | Paid | https://portal.azure.com/ (Azure "Bing Search" resource) |
| Bing Shared IPs | `sfp_bingsharedip` | `api_key` | Paid | Same Bing/Azure key as above |
| Google Search | `sfp_googlesearch` | `api_key` | Paid | https://developers.google.com/custom-search/v1/overview |
| Google Maps | `sfp_googlemaps` | `api_key` | Paid | https://console.cloud.google.com/google/maps-apis |
| Google Safe Browsing | `sfp_googlesafebrowsing` | `api_key` | Free | https://console.cloud.google.com/ (enable Safe Browsing API) |
| ZoomEye | `sfp_zoomeye` | `api_key` | Paid | https://www.zoomeye.org/register |

## 3. Blockchain & Cryptocurrency

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| BlockCypher | `sfp_blockchain_analytics` | `blockcypher_api_key` | Mixed | https://accounts.blockcypher.com/tokens |
| Blockchair | `sfp_blockchain_analytics` | `blockchair_api_key` | Mixed | https://blockchair.com/api |
| Bitcoin WhoIsWho | `sfp_bitcoinwhoswho` | `api_key` | Freemium | https://www.bitcoinwhoswho.com/ |
| Tron | `sfp_tron` | `api_key` | Free | https://tronscan.org/#/tools/api — same-pattern signup as Etherscan |

*(`sfp_blockchain_analytics:etherscan_api_key` is a duplicate slot for the key you already have — copy the Etherscan value in.)*

## 4. Email & Identity

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| Dehashed | `sfp_dehashed` | `api_key`, `api_key_username` | Paid | https://dehashed.com/register |
| EmailCrawlr | `sfp_emailcrawlr` | `api_key` | Paid | https://emailcrawlr.com/ |
| EmailRep | `sfp_emailrep` | `api_key` | Free | https://emailrep.io/key |
| FullContact | `sfp_fullcontact` | `api_key` | Paid | https://platform.fullcontact.com/ |
| HaveIBeenPwned | `sfp_haveibeenpwned` | `api_key` | Free* | https://haveibeenpwned.com/API/Key (*actually ~$3.50/mo minimum) |
| LeakCheck | `sfp_leakcheck` | `api_key` | Paid | https://leakcheck.io/ |
| Snov.io | `sfp_snov` | `api_key_client_id`, `api_key_client_secret` | Freemium | https://app.snov.io/ (API key under Settings) |

## 5. Domain & DNS

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| CertSpotter | `sfp_certspotter` | `api_key` | Free | https://sslmate.com/certspotter/pricing |
| CIRCL.LU | `sfp_circllu` | `api_key_login`, `api_key_password` | Free | https://www.circl.lu/services/passive-dns/ — requires a manually-approved account request |
| Cisco Umbrella | `sfp_cisco_umbrella` | `api_key` | Paid | https://umbrella.cisco.com/ — enterprise account required |
| HostIO | `sfp_hostio` | `api_key` | Freemium | https://host.io/ |
| JsonWHOIS.com | `sfp_jsonwhoiscom` | `api_key` | Freemium | https://jsonwhois.com/ |
| WhoisFreaks | `sfp_whoisfreaks` | `api_key` | Freemium | https://whoisfreaks.com/ |
| Whoisology | `sfp_whoisology` | `api_key` | Paid | https://whoisology.com/ |
| Whoxy | `sfp_whoxy` | `api_key` | Freemium | https://www.whoxy.com/ |
| ZoneFiles.io | `sfp_zonefiles` | `api_key` | Paid | https://zonefiles.io/ |
| Zetalytics | `sfp_zetalytics` | `api_key` | Paid | https://zetalytics.com/ |

## 6. IP & Geolocation

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| AbstractAPI | `sfp_abstractapi` | `companyenrichment_api_key`, `ipgeolocation_api_key`, `phonevalidation_api_key` | Freemium | https://www.abstractapi.com/ — 3 separate keys, one per endpoint |
| CriminalIP | `sfp_criminalip` | `api_key` | Freemium | https://www.criminalip.io/ |
| Fraudguard | `sfp_fraudguard` | `fraudguard_api_key_account`, `fraudguard_api_key_password` | Paid | https://fraudguard.io/ |
| IPQualityScore | `sfp_ipqualityscore` | `api_key` | Freemium | https://www.ipqualityscore.com/create-account |
| IP Registry | `sfp_ipregistry` | `api_key` | Freemium | https://ipregistry.co/ |
| IPStack | `sfp_ipstack` | `api_key` | Freemium | https://ipstack.com/ |
| ipapi.com | `sfp_ipapicom` | `api_key` | Freemium | https://ipapi.com/ |
| iknowwhatyoudownload | — | — | — | *already configured, see live_keys.env* |
| Netlas | `sfp_netlas` | `api_key` | Freemium | https://app.netlas.io/ |
| NetworksDB | `sfp_networksdb` | `api_key` | Paid | https://networksdb.io/ |
| spur.us | `sfp_spur` | `api_key` | Paid | https://spur.us/ |
| UnwiredLabs | `sfp_unwiredlabs` | `api_key` | Free | https://unwiredlabs.com/ |

## 7. Social Media & Communication

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| Bluesky | `sfp_bluesky` | `access_token` | Free | https://bsky.app/settings/app-passwords |
| Discord | `sfp_discord` | `bot_token` | Free | https://discord.com/developers/applications — create a bot app |
| Instagram | `sfp_instagram` | `access_token` | Paid | https://developers.facebook.com/ (Meta Graph API) |
| Mastodon | `sfp_mastodon` | `access_token` | Free | Your Mastodon instance → Preferences → Development |
| Matrix | `sfp_matrix` | `access_token` | Free | Generated from your Matrix client (e.g. Element → Settings → Help & About) |
| Mattermost | `sfp_mattermost` | `access_token` | Free | Your Mattermost instance → Account Settings → Security → Personal Access Tokens |
| Reddit | `sfp_reddit` | `client_secret` (client_id already labeled in cfg, also empty) | Free | https://www.reddit.com/prefs/apps |
| Rocket.Chat | `sfp_rocketchat` | `access_token` | Free | Your Rocket.Chat instance → Profile → Personal Access Tokens |
| Social Links | `sfp_sociallinks` | `api_key` | Paid | https://sociallinks.io/ — enterprise sales |
| Social Profiles | `sfp_socialprofiles` | `bing_api_key`, `google_api_key` | Paid | Same Bing/Google Search keys as section 2 |
| TikTok OSINT | `sfp_tiktok_osint` | `api_key`, `api_secret` | Free | https://developers.tiktok.com/ |
| WeChat | `sfp_wechat` | `api_key` | Paid | https://open.weixin.qq.com/ |
| WhatsApp | `sfp_whatsapp` | `api_key` | Paid | https://developers.facebook.com/docs/whatsapp |

## 8. Business Intelligence

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| BuiltWith | `sfp_builtwith` | `api_key` | Paid | https://builtwith.com/api |
| c99 | `sfp_c99` | `api_key` | Paid | https://api.c99.nl/ |
| Deepinfo | `sfp_deepinfo` | `api_key` | Paid | https://api.deepinfo.com/ |
| Focsec | `sfp_focsec` | `api_key` | Paid | https://focsec.com/ |
| Fofa | `sfp_fofa` | `api_key` | Freemium | https://fofa.info/ |
| Leak-Lookup (Citadel) | `sfp_citadel` | `api_key` | Paid | https://leak-lookup.com/ |
| Luminar | `sfp_luminar` | `api_key` | Paid | No public self-serve signup — Cognyte enterprise product |
| NameAPI | `sfp_nameapi` | `api_key` | Paid | https://www.nameapi.org/ |
| numverify | `sfp_numverify` | `api_key` | Freemium | https://numverify.com/ |
| NeutrinoAPI | `sfp_neutrinoapi` | `api_key` | Freemium | https://www.neutrinoapi.com/ |
| OpenCorporates | `sfp_opencorporates` | `api_key` | Freemium | https://opencorporates.com/api_accounts/new |
| Onyphe | `sfp_onyphe` | `api_key` | Freemium | https://www.onyphe.io/ |
| RocketReach | `sfp_rocketreach` | `api_key` | Paid | https://rocketreach.co/api |
| Seon | `sfp_seon` | `api_key` | Paid | https://seon.io/ |
| StackOverflow | `sfp_stackoverflow` | `api_key` | Free | https://stackapps.com/apps/oauth/register |
| WhatCMS | `sfp_whatcms` | `api_key` | Freemium | https://whatcms.org/API |

## 9. Malware & Security Analysis

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| Grayhat Warfare | `sfp_grayhatwarfare` | `api_key` | Paid | https://buckets.grayhatwarfare.com/ |
| Koodous | `sfp_koodous` | `api_key` | Free | https://koodous.com/ |
| MalwarePatrol | `sfp_malwarepatrol` | `api_key` | Freemium | https://www.malwarepatrol.net/ |
| MetaDefender | `sfp_metadefender` | `api_key` | Freemium | https://metadefender.opswat.com/ |
| Project Honey Pot | `sfp_honeypot` | `api_key` | Free | https://www.projecthoneypot.org/ |

## 10. Communication & Specialized

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| Twilio | `sfp_twilio` | `api_key_account_sid`, `api_key_auth_token` | Paid | https://www.twilio.com/try-twilio |
| TextMagic | `sfp_textmagic` | `api_key`, `api_key_username` | Paid | https://www.textmagic.com/ |
| Onion.link | `sfp_onioncity` | `api_key` | Paid | No current public signup found — service appears dormant |
| WiGLE | `sfp_wigle` | `api_key_encoded` | Free | https://wigle.net/ |
| API Key Leak Detector | `sfp_apileak` | `github_token` | Free | https://github.com/settings/tokens (personal access token) |
| AI Summary | `sfp_ai_summary` | `api_key` | Paid | Depends on which LLM backend this module is pointed at (e.g. OpenAI) — check module docs for the expected provider |
| IntelligenceX | `sfp_intelx` | `api_key` | Paid | https://intelx.io/signup |
| PasteBin | `sfp_pastebin` | `api_key` | Freemium | https://pastebin.com/doc_scraping_api |
| XForce Exchange | `sfp_xforce` | `xforce_api_key`, `xforce_api_key_password` | Paid | https://exchange.xforce.ibmcloud.com/ |

## 11. Tools (external binaries)

| Service | Module | Field(s) | Tier | Signup |
|---|---|---|---|---|
| PhoneInfoga | `sfp_tool_phoneinfoga` | `api_key` | Free | Uses numverify under the hood — see numverify above |
| Wappalyzer | `sfp_tool_wappalyzer` | `wappalyzer_api_key` | Paid | https://www.wappalyzer.com/api/ |

---

## Suggested next targets

Cross-referencing the reference doc's "Top 10 Priority" list against what's
already configured, these are the highest-value gaps:

1. **Censys UID** — you're one field away from a working key (see top of this file)
2. **HaveIBeenPwned** — breach data, no equivalent already configured
3. **CertSpotter** — free tier, high priority per the reference doc, currently empty
4. **IntelligenceX** — high priority, currently empty
5. **BinaryEdge** — freemium, high priority, currently empty
