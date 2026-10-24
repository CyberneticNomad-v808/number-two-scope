#!/usr/bin/env python3
"""
Live API Key Hunter - Uses Playwright MCP for real-time automation
Credentials: 
- Username: spiderfoot_hunter
- Password: SpiderFoot2024!Secure
- Temp Email: agogfze@mailto.plus (check at https://tempmail.plus/)
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

# Services with their signup URLs (High Priority Free/Freemium first)
SERVICES = {
    # Security & Threat Intelligence - FREE
    "AlienVault OTX": {
        "url": "https://otx.alienvault.com/#signup",
        "tier": "Free",
        "priority": "High",
        "status": "in_progress",
        "notes": "Form filled, needs CAPTCHA solve, then check email agogfze@mailto.plus for verification"
    },
    "AbuseIPDB": {
        "url": "https://www.abuseipdb.com/register",
        "tier": "Free",
        "priority": "High"
    },
    "GreyNoise Community": {
        "url": "https://www.greynoise.io/community",
        "tier": "Free",
        "priority": "High"
    },
    "Hybrid Analysis": {
        "url": "https://www.hybrid-analysis.com/signup",
        "tier": "Free",
        "priority": "Medium"
    },
    "Pulsedive": {
        "url": "https://pulsedive.com/register",
        "tier": "Free",
        "priority": "Medium"
    },
    
    # Search & Discovery - FREE
    "Google Safe Browsing": {
        "url": "https://console.cloud.google.com/",
        "tier": "Free",
        "priority": "Medium",
        "notes": "Requires Google account, enable Safe Browsing API"
    },
    
    # Email & Identity - FREE
    "EmailRep": {
        "url": "https://emailrep.io/key",
        "tier": "Free",
        "priority": "Medium"
    },
    "HaveIBeenPwned": {
        "url": "https://haveibeenpwned.com/API/Key",
        "tier": "Free",
        "priority": "High",
        "notes": "Requires verification, $3.50/month minimum"
    },
    "LeakIX": {
        "url": "https://leakix.net/",
        "tier": "Free",
        "priority": "Medium"
    },
    
    # Domain & DNS - FREE
    "CertSpotter": {
        "url": "https://sslmate.com/certspotter/pricing",
        "tier": "Free",
        "priority": "High"
    },
    
    # IP & Geolocation - FREEMIUM
    "IPInfo.io": {
        "url": "https://ipinfo.io/signup",
        "tier": "Freemium",
        "priority": "High",
        "notes": "50k requests/month free"
    },
    "CriminalIP": {
        "url": "https://www.criminalip.io/",
        "tier": "Freemium",
        "priority": "High"
    },
    
    # Blockchain - FREE
    "Etherscan": {
        "url": "https://etherscan.io/register",
        "tier": "Free",
        "priority": "Medium"
    },
    
    # Search Engines - FREEMIUM
    "Censys": {
        "url": "https://censys.io/register",
        "tier": "Freemium",
        "priority": "High",
        "notes": "50 queries/month free"
    },
    "Project Discovery": {
        "url": "https://cloud.projectdiscovery.io/",
        "tier": "Freemium",
        "priority": "Medium"
    },
    "Hunter.io": {
        "url": "https://hunter.io/users/sign_up",
        "tier": "Freemium",
        "priority": "High"
    },
    
    # Threat Intelligence - FREEMIUM/PAID
    "VirusTotal": {
        "url": "https://www.virustotal.com/gui/join-us",
        "tier": "Freemium",
        "priority": "High"
    },
    "GreyNoise": {
        "url": "https://www.greynoise.io/viz/signup",
        "tier": "Freemium",
        "priority": "High"
    },
    "BinaryEdge": {
        "url": "https://app.binaryedge.io/sign-up",
        "tier": "Freemium",
        "priority": "Medium"
    },
}


class APIKeyDatabase:
    """Simple database for tracking API keys"""
    
    def __init__(self, db_path="api_keys_progress.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS api_keys
                     (service TEXT PRIMARY KEY,
                      url TEXT,
                      tier TEXT,
                      priority TEXT,
                      api_key TEXT,
                      status TEXT,
                      notes TEXT,
                      created_at TIMESTAMP,
                      updated_at TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS credentials
                     (id INTEGER PRIMARY KEY,
                      service TEXT,
                      username TEXT,
                      email TEXT,
                      password TEXT,
                      temp_email TEXT,
                      created_at TIMESTAMP)''')
        conn.commit()
        conn.close()
    
    def save_service(self, service: str, data: Dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO api_keys 
                     (service, url, tier, priority, api_key, status, notes, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (service, data.get('url'), data.get('tier'), data.get('priority'),
                   data.get('api_key'), data.get('status', 'pending'), 
                   data.get('notes', ''), datetime.now()))
        conn.commit()
        conn.close()
    
    def save_api_key(self, service: str, api_key: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''UPDATE api_keys SET api_key=?, status='completed', updated_at=?
                     WHERE service=?''', (api_key, datetime.now(), service))
        conn.commit()
        conn.close()
        print(f"✅ Saved API key for {service}")
    
    def save_credentials(self, service: str, username: str, email: str, password: str, temp_email: str = None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO credentials 
                     (service, username, email, password, temp_email, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (service, username, email, password, temp_email, datetime.now()))
        conn.commit()
        conn.close()
    
    def get_all_keys(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT service, api_key, status FROM api_keys WHERE api_key IS NOT NULL')
        results = c.fetchall()
        conn.close()
        return results
    
    def export_env(self):
        """Export as .env format"""
        keys = self.get_all_keys()
        lines = []
        for service, api_key, status in keys:
            env_name = service.upper().replace(' ', '_').replace('.', '_')
            lines.append(f"{env_name}_API_KEY={api_key}")
        return "\n".join(lines)
    
    def status_report(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM api_keys')
        total = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM api_keys WHERE status="completed"')
        completed = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM api_keys WHERE status="in_progress"')
        in_progress = c.fetchone()[0]
        conn.close()
        
        print("\n" + "="*60)
        print("📊 API KEY ACQUISITION STATUS")
        print("="*60)
        print(f"Total Services: {total}")
        print(f"✅ Completed: {completed}")
        print(f"🔄 In Progress: {in_progress}")
        print(f"⏳ Pending: {total - completed - in_progress}")
        print("="*60)


def init_database():
    """Initialize database with all services"""
    db = APIKeyDatabase()
    for service, data in SERVICES.items():
        db.save_service(service, data)
    print(f"✅ Initialized database with {len(SERVICES)} services")
    return db


def generate_next_steps():
    """Generate actionable next steps"""
    print("\n" + "="*60)
    print("🎯 NEXT STEPS TO GET API KEYS")
    print("="*60)
    print("\n1. AlienVault OTX (IN PROGRESS):")
    print("   - Browser is at signup page with form filled")
    print("   - Solve the CAPTCHA manually")
    print("   - Click 'sign up' button")
    print("   - Check email at: https://tempmail.plus/")
    print("   - Email: agogfze@mailto.plus")
    print("   - Click verification link in email")
    print("   - Login and go to: https://otx.alienvault.com/api")
    print("   - Copy your API key")
    
    print("\n2. Continue with other High Priority FREE services:")
    for service, data in SERVICES.items():
        if data.get('tier') == 'Free' and data.get('priority') == 'High' and service != 'AlienVault OTX':
            print(f"   - {service}: {data['url']}")
    
    print("\n3. Use same credentials for consistency:")
    print("   Username: spiderfoot_hunter")
    print("   Password: SpiderFoot2024!Secure")
    print("   Get new temp emails from: https://tempmail.plus/")
    
    print("\n4. Store each API key using:")
    print("   python3 live_api_hunter.py --save-key 'ServiceName' 'API_KEY_HERE'")
    
    print("\n5. Export all keys when done:")
    print("   python3 live_api_hunter.py --export")
    print("="*60)


def save_key_manual(service: str, api_key: str):
    """Manually save an API key"""
    db = APIKeyDatabase()
    db.save_api_key(service, api_key)
    print(f"\n✅ API key saved for {service}")
    print("\nRun --status to see progress")


def main():
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--init":
            db = init_database()
            db.status_report()
            generate_next_steps()
        
        elif sys.argv[1] == "--status":
            db = APIKeyDatabase()
            db.status_report()
        
        elif sys.argv[1] == "--export":
            db = APIKeyDatabase()
            print("\n📋 API Keys (.env format):\n")
            print(db.export_env())
        
        elif sys.argv[1] == "--save-key" and len(sys.argv) == 4:
            service = sys.argv[2]
            api_key = sys.argv[3]
            save_key_manual(service, api_key)
        
        elif sys.argv[1] == "--next":
            generate_next_steps()
        
        else:
            print("Usage:")
            print("  --init          Initialize database with all services")
            print("  --status        Show current progress")
            print("  --export        Export all acquired keys")
            print("  --save-key 'Service' 'API_KEY'  Manually save an API key")
            print("  --next          Show next steps")
    
    else:
        print("🔥 Live API Key Hunter")
        print("\nInitializing...")
        db = init_database()
        db.save_credentials("AlienVault OTX", "spiderfoot_hunter", "agogfze@mailto.plus", 
                           "SpiderFoot2024!Secure", "agogfze@mailto.plus")
        db.status_report()
        generate_next_steps()


if __name__ == "__main__":
    main()
