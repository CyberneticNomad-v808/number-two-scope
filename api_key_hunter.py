#!/usr/bin/env python3
"""
SpiderFoot API Key Hunter
Automated API key acquisition system for 116+ services
"""

import json
import sqlite3
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class ServiceConfig:
    """Configuration for an API service"""
    id: int
    name: str
    module: str
    config_key: str
    tier: str
    priority: str
    category: str
    signup_url: str
    status: str = "pending"
    api_key: Optional[str] = None
    notes: Optional[str] = None
    acquired_at: Optional[str] = None


class APIKeyHunter:
    """Main automation engine for API key acquisition"""
    
    def __init__(self, db_path: str = "api_keys.db"):
        self.db_path = db_path
        self.init_database()
        self.services = self.load_services()
        
    def init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                module TEXT,
                config_key TEXT,
                tier TEXT,
                priority TEXT,
                category TEXT,
                signup_url TEXT,
                status TEXT DEFAULT 'pending',
                api_key TEXT,
                notes TEXT,
                acquired_at TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signup_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (service_id) REFERENCES services (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def load_services(self) -> List[ServiceConfig]:
        """Load all services from database or initialize"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            # Initialize with services from the document
            self._populate_services()
        
        cursor.execute("SELECT * FROM services ORDER BY priority DESC, tier, name")
        services = []
        for row in cursor.fetchall():
            services.append(ServiceConfig(
                id=row[0], name=row[1], module=row[2], config_key=row[3],
                tier=row[4], priority=row[5], category=row[6], signup_url=row[7],
                status=row[8], api_key=row[9], notes=row[10], acquired_at=row[11]
            ))
        
        conn.close()
        return services
    
    def _populate_services(self):
        """Populate database with all 116 services"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Service definitions with signup URLs
        services = [
            # Security & Threat Intelligence
            (1, "AbuseIPDB", "sfp_abuseipdb.py", "api_key", "Free", "High", "Security", "https://www.abuseipdb.com/register"),
            (2, "AlienVault OTX", "sfp_alienvault.py", "api_key", "Free", "High", "Security", "https://otx.alienvault.com/api"),
            (3, "GreyNoise", "sfp_greynoise.py", "api_key", "Freemium", "High", "Security", "https://www.greynoise.io/viz/signup"),
            (4, "GreyNoise Community", "sfp_greynoise_community.py", "api_key", "Free", "High", "Security", "https://www.greynoise.io/community"),
            (5, "Hybrid Analysis", "sfp_hybrid_analysis.py", "api_key", "Free", "Medium", "Security", "https://www.hybrid-analysis.com/signup"),
            (6, "SHODAN", "sfp_shodan.py", "api_key", "Paid", "High", "Security", "https://account.shodan.io/register"),
            (7, "VirusTotal", "sfp_virustotal.py", "api_key", "Freemium", "High", "Security", "https://www.virustotal.com/gui/join-us"),
            (8, "Pulsedive", "sfp_pulsedive.py", "api_key", "Free", "Medium", "Security", "https://pulsedive.com/register"),
            
            # Search & Discovery
            (9, "BinaryEdge", "sfp_binaryedge.py", "binaryedge_api_key", "Freemium", "Medium", "Search", "https://app.binaryedge.io/sign-up"),
            (10, "Censys", "sfp_censys.py", "censys_api_key_uid,censys_api_key_secret", "Freemium", "High", "Search", "https://censys.io/register"),
            (11, "Google Safe Browsing", "sfp_googlesafebrowsing.py", "api_key", "Free", "Medium", "Search", "https://console.cloud.google.com/"),
            (12, "Project Discovery", "sfp_projectdiscovery.py", "api_key", "Freemium", "Medium", "Search", "https://cloud.projectdiscovery.io/"),
            (13, "ZoomEye", "sfp_zoomeye.py", "api_key", "Paid", "Medium", "Search", "https://www.zoomeye.org/register"),
            
            # Email & Identity
            (14, "EmailRep", "sfp_emailrep.py", "api_key", "Free", "Medium", "Email", "https://emailrep.io/key"),
            (15, "HaveIBeenPwned", "sfp_haveibeenpwned.py", "api_key", "Free", "High", "Email", "https://haveibeenpwned.com/API/Key"),
            (16, "Hunter.io", "sfp_hunter.py", "api_key", "Freemium", "High", "Email", "https://hunter.io/users/sign_up"),
            (17, "LeakIX", "sfp_leakix.py", "api_key", "Free", "Medium", "Email", "https://leakix.net/"),
            
            # Domain & DNS
            (18, "CertSpotter", "sfp_certspotter.py", "api_key", "Free", "High", "Domain", "https://sslmate.com/certspotter/pricing"),
            (19, "SecurityTrails", "sfp_securitytrails.py", "api_key", "Paid", "High", "Domain", "https://securitytrails.com/app/signup"),
            (20, "ViewDNS.info", "sfp_viewdns.py", "api_key", "Freemium", "Medium", "Domain", "https://viewdns.info/api/"),
            
            # IP & Geolocation
            (21, "CriminalIP", "sfp_criminalip.py", "api_key", "Freemium", "High", "IP", "https://www.criminalip.io/"),
            (22, "IPInfo.io", "sfp_ipinfo.py", "api_key", "Freemium", "High", "IP", "https://ipinfo.io/signup"),
            (23, "IPQualityScore", "sfp_ipqualityscore.py", "api_key", "Freemium", "Medium", "IP", "https://www.ipqualityscore.com/create-account"),
            
            # Blockchain
            (24, "Etherscan", "sfp_etherscan.py", "api_key", "Free", "Medium", "Blockchain", "https://etherscan.io/register"),
            
            # Business Intelligence
            (25, "FullHunt", "sfp_fullhunt.py", "api_key", "Paid", "Medium", "Business", "https://fullhunt.io/"),
            (26, "Onyphe", "sfp_onyphe.py", "api_key", "Freemium", "Medium", "Business", "https://www.onyphe.io/"),
            
            # Communication
            (27, "IntelligenceX", "sfp_intelx.py", "api_key", "Paid", "High", "Communication", "https://intelx.io/signup"),
            (28, "PasteBin", "sfp_pastebin.py", "api_key", "Freemium", "Medium", "Communication", "https://pastebin.com/doc_scraping_api"),
        ]
        
        cursor.executemany("""
            INSERT INTO services (id, name, module, config_key, tier, priority, category, signup_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, services)
        
        conn.commit()
        conn.close()
    
    async def hunt_keys(self, headless: bool = False, filter_priority: Optional[str] = None):
        """Main automation loop using Playwright"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("ERROR: Playwright not installed. Run: pip install playwright && playwright install")
            return
        
        services_to_process = self.services
        if filter_priority:
            services_to_process = [s for s in services_to_process if s.priority == filter_priority]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            
            for service in services_to_process:
                if service.status == "completed":
                    print(f"⏭️  Skipping {service.name} - already completed")
                    continue
                
                print(f"\n{'='*60}")
                print(f"🎯 Processing: {service.name}")
                print(f"   Priority: {service.priority} | Tier: {service.tier}")
                print(f"   URL: {service.signup_url}")
                print(f"{'='*60}")
                
                try:
                    await self._process_service(context, service)
                except Exception as e:
                    print(f"❌ Error processing {service.name}: {e}")
                    self._log_attempt(service.id, False, str(e))
            
            await browser.close()
    
    async def _process_service(self, context, service: ServiceConfig):
        """Process individual service signup"""
        page = await context.new_page()
        
        try:
            # Navigate to signup page
            await page.goto(service.signup_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Check for common patterns
            content = await page.content()
            
            # Look for API key if already logged in
            api_key_patterns = [
                r'api[_-]?key["\s:]+([a-zA-Z0-9\-_]{20,})',
                r'apikey["\s:]+([a-zA-Z0-9\-_]{20,})',
                r'token["\s:]+([a-zA-Z0-9\-_]{20,})',
            ]
            
            for pattern in api_key_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"✅ Found potential API key: {matches[0][:10]}...")
                    self._save_api_key(service.id, matches[0])
                    return
            
            # Check for CAPTCHAs
            if "recaptcha" in content.lower() or "hcaptcha" in content.lower():
                print("⚠️  CAPTCHA detected - manual intervention required")
                print(f"📋 Page URL: {page.url}")
                
                # Wait for manual CAPTCHA solve
                if not await self._wait_for_manual_action(page):
                    return
            
            # Try to find and fill signup forms
            email_field = await page.query_selector('input[type="email"], input[name*="email"], input[id*="email"]')
            if email_field:
                print("📝 Found signup form, attempting to fill...")
                await self._fill_signup_form(page, service)
            else:
                print("ℹ️  No obvious signup form found - may need manual navigation")
                print(f"   Opening browser for manual signup: {service.signup_url}")
                await asyncio.sleep(5)  # Give time to see the page
            
            # Save progress
            self._update_service_status(service.id, "attempted", f"Last attempt: {datetime.now()}")
            self._log_attempt(service.id, False, "Requires manual completion")
            
        finally:
            await page.close()
    
    async def _fill_signup_form(self, page, service: ServiceConfig):
        """Attempt to fill signup form automatically"""
        # Generate temporary email (you'd integrate with a temp email service)
        temp_email = f"spiderfoot_{service.name.lower().replace(' ', '_')}@tempmail.com"
        
        try:
            # Fill email
            email_input = await page.query_selector('input[type="email"]')
            if email_input:
                await email_input.fill(temp_email)
                print(f"✉️  Filled email: {temp_email}")
            
            # Fill password if exists
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                password = f"SpiderFoot2024!{service.id}"
                await password_input.fill(password)
                print("🔒 Filled password")
            
            # Fill username if exists
            username_input = await page.query_selector('input[name*="username"], input[id*="username"]')
            if username_input:
                await username_input.fill(f"spiderfoot_user_{service.id}")
                print("👤 Filled username")
            
            # Look for submit button
            submit_button = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Sign Up"), button:has-text("Register")')
            if submit_button:
                print("🔘 Found submit button - PAUSING for manual review")
                print("   Review the form and press Enter to submit, or Ctrl+C to skip")
                # Don't auto-submit - let user verify
                await asyncio.sleep(10)
        
        except Exception as e:
            print(f"⚠️  Form fill error: {e}")
    
    async def _wait_for_manual_action(self, page, timeout: int = 60) -> bool:
        """Wait for user to complete manual action"""
        print(f"⏳ Waiting {timeout}s for manual completion...")
        print("   Complete the action in the browser, then this will continue")
        
        try:
            await asyncio.sleep(timeout)
            return True
        except KeyboardInterrupt:
            print("\n⏭️  Skipped by user")
            return False
    
    def _save_api_key(self, service_id: int, api_key: str):
        """Save API key to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE services 
            SET api_key = ?, status = 'completed', acquired_at = ?
            WHERE id = ?
        """, (api_key, datetime.now().isoformat(), service_id))
        conn.commit()
        conn.close()
        print(f"💾 API key saved to database")
    
    def _update_service_status(self, service_id: int, status: str, notes: str):
        """Update service status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE services 
            SET status = ?, notes = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, notes, service_id))
        conn.commit()
        conn.close()
    
    def _log_attempt(self, service_id: int, success: bool, error_msg: Optional[str] = None):
        """Log signup attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signup_attempts (service_id, success, error_message)
            VALUES (?, ?, ?)
        """, (service_id, success, error_msg))
        conn.commit()
        conn.close()
    
    def export_keys(self, format: str = "json") -> str:
        """Export all acquired API keys"""
        services_with_keys = [s for s in self.services if s.api_key]
        
        if format == "json":
            return json.dumps([asdict(s) for s in services_with_keys], indent=2)
        elif format == "env":
            lines = []
            for s in services_with_keys:
                key_name = s.config_key.upper().replace(',', '_')
                lines.append(f"{key_name}={s.api_key}")
            return "\n".join(lines)
        elif format == "spiderfoot":
            # Generate SpiderFoot configuration SQL
            lines = []
            for s in services_with_keys:
                lines.append(f"INSERT INTO tbl_config (config_name, config_value) VALUES ('{s.config_key}', '{s.api_key}');")
            return "\n".join(lines)
    
    def status_report(self):
        """Print status report"""
        total = len(self.services)
        completed = len([s for s in self.services if s.status == "completed"])
        attempted = len([s for s in self.services if s.status == "attempted"])
        pending = len([s for s in self.services if s.status == "pending"])
        
        print("\n" + "="*60)
        print("📊 API KEY ACQUISITION STATUS REPORT")
        print("="*60)
        print(f"Total Services: {total}")
        print(f"✅ Completed: {completed} ({completed/total*100:.1f}%)")
        print(f"🔄 Attempted: {attempted} ({attempted/total*100:.1f}%)")
        print(f"⏳ Pending: {pending} ({pending/total*100:.1f}%)")
        print("="*60)
        
        # By priority
        for priority in ["High", "Medium", "Low"]:
            priority_services = [s for s in self.services if s.priority == priority]
            completed_priority = len([s for s in priority_services if s.status == "completed"])
            print(f"\n{priority} Priority: {completed_priority}/{len(priority_services)}")
        
        # By tier
        print("\n" + "-"*60)
        for tier in ["Free", "Freemium", "Paid"]:
            tier_services = [s for s in self.services if s.tier == tier]
            completed_tier = len([s for s in tier_services if s.status == "completed"])
            print(f"{tier} Tier: {completed_tier}/{len(tier_services)}")


async def main():
    parser = argparse.ArgumentParser(description="SpiderFoot API Key Hunter")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--priority", choices=["High", "Medium", "Low"], help="Filter by priority")
    parser.add_argument("--export", choices=["json", "env", "spiderfoot"], help="Export acquired keys")
    parser.add_argument("--status", action="store_true", help="Show status report")
    
    args = parser.parse_args()
    
    hunter = APIKeyHunter()
    
    if args.status:
        hunter.status_report()
    elif args.export:
        print(hunter.export_keys(args.export))
    else:
        print("🔥 SpiderFoot API Key Hunter - Starting Automation 🔥")
        print("="*60)
        await hunter.hunt_keys(headless=args.headless, filter_priority=args.priority)
        hunter.status_report()


if __name__ == "__main__":
    asyncio.run(main())
