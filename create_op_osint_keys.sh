#!/usr/bin/env bash
# =============================================================================
# Create/Recreate 1Password item "OSINT Free API Keys" in LOCAL_DEV_VAULT
#
# Source: api_key_hunter.ipynb → ALL_116_SERVICES catalog
# Filter: Free + Freemium tiers only (no Paid, no N/A)
#
# SAFE MIGRATION: If item already exists, backs up all populated values,
# deletes the old item, creates new one with clean labels, then restores
# any non-placeholder values automatically.
#
# Usage:
#   chmod +x create_op_osint_keys.sh && ./create_op_osint_keys.sh
#
# Prerequisites:
#   - op CLI v2.x installed
#   - 1Password desktop app with CLI integration enabled
#   - LOCAL_DEV_VAULT must exist
# =============================================================================

set -euo pipefail

VAULT="LOCAL_DEV_VAULT"
ITEM_TITLE="OSINT Free API Keys"
PH="REPLACE_WITH_API_KEY"
BACKUP_FILE="/tmp/osint_keys_backup_$(date +%Y%m%dT%H%M%S).json"

# Maps old field labels (with ::) to new clean labels
# Format: "old_label_substring|new_clean_label"
declare -A LABEL_MAP=(
  # The old labels contain ":: sfp_module :: config_key" but the part
  # before :: is "service_name ". We match on the new clean label since
  # that's what we key the restore on. The backup JSON gives us field
  # values keyed by their old label — we extract values by section+position.
)

echo "============================================="
echo " 1Password OSINT API Keys Manager"
echo " Vault: ${VAULT}"
echo " Item:  ${ITEM_TITLE}"
echo "============================================="
echo ""

# Sign in (will prompt biometric/password ONCE)
eval "$(op signin)" || { echo "ERROR: op signin failed"; exit 1; }
echo "[+] Authenticated successfully."
echo ""

# ---------------------------------------------------------------------------
# Phase 1: Check for existing item and back up populated values
# ---------------------------------------------------------------------------
EXISTING_VALUES=""
ITEM_EXISTS=false

if op item get "${ITEM_TITLE}" --vault "${VAULT}" --format json > "${BACKUP_FILE}" 2>/dev/null; then
  ITEM_EXISTS=true
  echo "[+] Existing item found — backing up to ${BACKUP_FILE}"

  # Extract all fields that have values != REPLACE_WITH_API_KEY and aren't empty
  EXISTING_VALUES=$(python3 -c "
import json, sys

with open('${BACKUP_FILE}') as f:
    data = json.load(f)

populated = {}
for field in data.get('fields', []):
    val = field.get('value', '')
    label = field.get('label', '')
    section = (field.get('section') or {}).get('label', '')
    if val and val != '${PH}' and section and label:
        # Extract clean label: strip everything after ' :: ' if present
        clean = label.split(' :: ')[0].strip() if ' :: ' in label else label.strip()
        # Remove section prefix dot notation if present (e.g., 'Security.' prefix already stripped by 1Password)
        key = f'{section}/{clean}'
        populated[key] = val
        print(f'  Found populated key: {section}/{clean}', file=sys.stderr)

# Output as JSON for later restore
json.dump(populated, sys.stdout)
" 2>&1)

  # Separate stderr (log lines) from stdout (JSON)
  RESTORE_JSON=$(python3 -c "
import json, sys

with open('${BACKUP_FILE}') as f:
    data = json.load(f)

populated = {}
for field in data.get('fields', []):
    val = field.get('value', '')
    label = field.get('label', '')
    section = (field.get('section') or {}).get('label', '')
    if val and val != '${PH}' and section and label:
        clean = label.split(' :: ')[0].strip() if ' :: ' in label else label.strip()
        key = f'{section}/{clean}'
        populated[key] = val

json.dump(populated, sys.stdout)
")

  POPULATED_COUNT=$(echo "${RESTORE_JSON}" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
  echo "[+] Found ${POPULATED_COUNT} populated key(s) to preserve"
  echo ""

  # Delete old item
  echo "[!] Deleting old item (backup saved at ${BACKUP_FILE})..."
  op item delete "${ITEM_TITLE}" --vault "${VAULT}"
  echo "[+] Old item deleted."
  echo ""
else
  echo "[*] No existing item found — creating fresh."
  rm -f "${BACKUP_FILE}"
  echo ""
fi

# ---------------------------------------------------------------------------
# Phase 2: Create new item with clean field labels
# ---------------------------------------------------------------------------
echo "[+] Creating item with clean field labels (op:// compatible)..."
echo ""

op item create \
  --category password \
  --title "${ITEM_TITLE}" \
  --vault "${VAULT}" \
  --tags "osint,spiderfoot,api-keys,free-tier,freemium" \
  \
  'notesPlain=SpiderFoot Free/Freemium API Keys. Cross-reference env.spiderfoot.apikeys for SF module mapping. Run seed-api-keys.sh to deploy into SpiderFoot DB.' \
  \
  'Security.abuseipdb[password]='"${PH}" \
  'Security.alienvault_otx[password]='"${PH}" \
  'Security.greynoise[password]='"${PH}" \
  'Security.greynoise_community[password]='"${PH}" \
  'Security.hybrid_analysis[password]='"${PH}" \
  'Security.virustotal[password]='"${PH}" \
  'Security.pulsedive[password]='"${PH}" \
  \
  'Search.binaryedge[password]='"${PH}" \
  'Search.censys_uid[password]='"${PH}" \
  'Search.censys_secret[password]='"${PH}" \
  'Search.google_safebrowsing[password]='"${PH}" \
  'Search.projectdiscovery[password]='"${PH}" \
  \
  'Blockchain.arbitrum[password]='"${PH}" \
  'Blockchain.bitcoinwhoswho[password]='"${PH}" \
  'Blockchain.bnb_chain[password]='"${PH}" \
  'Blockchain.ethereum[password]='"${PH}" \
  'Blockchain.etherscan[password]='"${PH}" \
  'Blockchain.tron[password]='"${PH}" \
  \
  'Email.emailrep[password]='"${PH}" \
  'Email.haveibeenpwned[password]='"${PH}" \
  'Email.hunter[password]='"${PH}" \
  'Email.leakix[password]='"${PH}" \
  'Email.snov_client_id[password]='"${PH}" \
  'Email.snov_client_secret[password]='"${PH}" \
  \
  'Domain.certspotter[password]='"${PH}" \
  'Domain.circl_lu_login[password]='"${PH}" \
  'Domain.circl_lu_password[password]='"${PH}" \
  'Domain.hostio[password]='"${PH}" \
  'Domain.jsonwhoiscom[password]='"${PH}" \
  'Domain.viewdns[password]='"${PH}" \
  'Domain.whoisfreaks[password]='"${PH}" \
  'Domain.whoxy[password]='"${PH}" \
  \
  'IP.abstractapi_company[password]='"${PH}" \
  'IP.abstractapi_phone[password]='"${PH}" \
  'IP.abstractapi_geo[password]='"${PH}" \
  'IP.criminalip[password]='"${PH}" \
  'IP.ipinfo[password]='"${PH}" \
  'IP.ipqualityscore[password]='"${PH}" \
  'IP.ipregistry[password]='"${PH}" \
  'IP.ipstack[password]='"${PH}" \
  'IP.ipapicom[password]='"${PH}" \
  'IP.netlas[password]='"${PH}" \
  'IP.unwiredlabs[password]='"${PH}" \
  \
  'Social.bluesky[password]='"${PH}" \
  'Social.discord[password]='"${PH}" \
  'Social.mastodon[password]='"${PH}" \
  'Social.matrix[password]='"${PH}" \
  'Social.mattermost[password]='"${PH}" \
  'Social.reddit_client_id[password]='"${PH}" \
  'Social.reddit_client_secret[password]='"${PH}" \
  'Social.rocketchat[password]='"${PH}" \
  'Social.tiktok_api_key[password]='"${PH}" \
  'Social.tiktok_api_secret[password]='"${PH}" \
  \
  'Business.fofa[password]='"${PH}" \
  'Business.numverify[password]='"${PH}" \
  'Business.neutrinoapi[password]='"${PH}" \
  'Business.opencorporates[password]='"${PH}" \
  'Business.onyphe[password]='"${PH}" \
  'Business.stackoverflow[password]='"${PH}" \
  'Business.whatcms[password]='"${PH}" \
  \
  'Malware.koodous[password]='"${PH}" \
  'Malware.malwarepatrol[password]='"${PH}" \
  'Malware.metadefender[password]='"${PH}" \
  'Malware.honeypot[password]='"${PH}" \
  \
  'Comms.wigle[password]='"${PH}" \
  'Comms.apileak_github[password]='"${PH}" \
  'Comms.botscout[password]='"${PH}" \
  'Comms.pastebin[password]='"${PH}" \
  'Comms.phoneinfoga[password]='"${PH}" \
  \
  --format json > /dev/null

echo "[+] New item created with clean labels."
echo ""

# ---------------------------------------------------------------------------
# Phase 3: Restore populated values from backup
# ---------------------------------------------------------------------------
if [ "${ITEM_EXISTS}" = true ] && [ "${POPULATED_COUNT:-0}" -gt "0" ]; then
  echo "[+] Restoring ${POPULATED_COUNT} populated key(s) from backup..."
  echo ""

  # Generate op item edit commands from the backup JSON
  python3 -c "
import json, sys, subprocess

restore = json.loads('''${RESTORE_JSON}''')

restored = 0
failed = 0
for key, val in restore.items():
    section, field = key.split('/', 1)
    # op item edit uses: 'Section.field[password]=value'
    field_spec = f'{section}.{field}[password]={val}'
    try:
        subprocess.run(
            ['op', 'item', 'edit', '${ITEM_TITLE}',
             '--vault', '${VAULT}',
             field_spec],
            check=True, capture_output=True, text=True,
        )
        print(f'  [+] Restored: {section}/{field}')
        restored += 1
    except subprocess.CalledProcessError as e:
        print(f'  [!] FAILED: {section}/{field} — {e.stderr.strip()}')
        failed += 1

print()
print(f'Restore complete: {restored} restored, {failed} failed')
"

  echo ""
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================="
echo "[+] SUCCESS: '${ITEM_TITLE}' ready in '${VAULT}'"
echo "============================================="
echo ""
echo "Total fields: 68 (across 9 sections)"
echo ""
echo "  Security        :  7  (AbuseIPDB, AlienVault, GreyNoise x2, Hybrid Analysis, VT, Pulsedive)"
echo "  Search          :  5  (BinaryEdge, Censys uid+secret, Google SafeBrowsing, ProjectDiscovery)"
echo "  Blockchain      :  6  (Arbitrum, BitcoinWhosWho, BNB, Ethereum, Etherscan, Tron)"
echo "  Email           :  6  (EmailRep, HIBP, Hunter, LeakIX, Snov id+secret)"
echo "  Domain          :  8  (CertSpotter, CIRCL login+pw, HostIO, JsonWhois, ViewDNS, WhoisFreaks, Whoxy)"
echo "  IP              : 11  (AbstractAPI x3, CriminalIP, IPInfo, IPQS, IPRegistry, IPStack, ipapi, Netlas, Unwired)"
echo "  Social          : 10  (Bluesky, Discord, Mastodon, Matrix, Mattermost, Reddit x2, RocketChat, TikTok x2)"
echo "  Business        :  7  (Fofa, Numverify, NeutrinoAPI, OpenCorp, Onyphe, StackOverflow, WhatCMS)"
echo "  Malware         :  4  (Koodous, MalwarePatrol, MetaDefender, HoneyPot)"
echo "  Comms           :  5  (WiGLE, APILeak/GitHub, BotScout, PasteBin, PhoneInfoga)"
echo ""
if [ "${ITEM_EXISTS}" = true ]; then
  echo "  Backup saved:  ${BACKUP_FILE}"
fi
echo ""
echo "Next steps:"
echo "  1. Populate keys: Open 1Password → ${VAULT} → '${ITEM_TITLE}'"
echo "  2. Replace any remaining REPLACE_WITH_API_KEY values"
echo "  3. Deploy to SpiderFoot DB: ./seed-api-keys.sh"
echo ""
