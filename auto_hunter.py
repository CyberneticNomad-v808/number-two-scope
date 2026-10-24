#!/usr/bin/env python3
"""
Automated API Key Hunter with Notifications
Uses api-manager@blking.net for SSO and email verification
"""

import os
import sys
import subprocess
from live_api_hunter import APIKeyDatabase, SERVICES

# Bell/beep sound
def notify(message):
    """Play system bell and print BIG notification"""
    # Clear screen for visibility
    print("\n" * 3)
    print("\033[91m" + "█" * 60 + "\033[0m")  # Red bar
    print("\033[91m█" + " " * 58 + "█\033[0m")
    print(f"\033[91m█  🔔 🔔 🔔  ATTENTION NEEDED  🔔 🔔 🔔{' ' * 16}█\033[0m")
    print("\033[91m█" + " " * 58 + "█\033[0m")
    print(f"\033[93m█  {message:<56}█\033[0m")
    print("\033[91m█" + " " * 58 + "█\033[0m")
    print("\033[91m" + "█" * 60 + "\033[0m")
    print("\n")
    # System bell (multiple times)
    for _ in range(5):
        sys.stdout.write('\a')
        sys.stdout.flush()
    # Try audio notification
    try:
        subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/bell.oga'], 
                      capture_output=True, timeout=1)
    except:
        pass

# Priority services that work well with Google SSO
GOOGLE_SSO_SERVICES = [
    {
        "name": "VirusTotal",
        "url": "https://www.virustotal.com/gui/my-apikey",
        "login_url": "https://www.virustotal.com/gui/sso/google",
        "notes": "Sign in with Google SSO, then navigate to API key page"
    },
    {
        "name": "GitHub",
        "url": "https://github.com/settings/tokens",
        "notes": "Can use Google SSO if linked, create personal access token"
    }
]

# Services with simple email signup
EMAIL_SIGNUP_SERVICES = [
    {
        "name": "IPInfo.io",
        "url": "https://ipinfo.io/signup",
        "notes": "Simple email signup, API key displayed after verification"
    },
    {
        "name": "Hunter.io",
        "url": "https://hunter.io/users/sign_up",
        "notes": "Email signup, API key in account settings"
    },
    {
        "name": "Etherscan",
        "url": "https://etherscan.io/register",
        "notes": "Email signup, API key in My API-KEYs section"
    },
    {
        "name": "EmailRep",
        "url": "https://emailrep.io/key",
        "notes": "Just enter email, key sent immediately"
    },
    {
        "name": "GreyNoise Community",
        "url": "https://www.greynoise.io/viz/account/api-key",
        "notes": "Free community API key after signup"
    },
    {
        "name": "Pulsedive",
        "url": "https://pulsedive.com/register",
        "notes": "Email signup, API key in profile"
    },
    {
        "name": "CertSpotter",
        "url": "https://sslmate.com/certspotter/pricing",
        "notes": "Free tier available, API key after signup"
    },
    {
        "name": "LeakIX",
        "url": "https://leakix.net/",
        "notes": "Free API key after account creation"
    }
]

def print_instructions():
    """Print detailed instructions for manual signup"""
    print("\n" + "="*60)
    print("🎯 AUTOMATED API KEY HUNTER")
    print("="*60)
    
    print("\n📧 Using Account: api-manager@blking.net")
    print("   This account can:")
    print("   - Sign in with Google SSO to many services")
    print("   - Receive verification emails")
    
    print("\n🔥 STRATEGY:")
    print("\n1. Google SSO Services (EASIEST):")
    for svc in GOOGLE_SSO_SERVICES:
        print(f"   ✓ {svc['name']}: {svc['url']}")
        print(f"     → {svc['notes']}")
    
    print("\n2. Email Signup Services (USE api-manager@blking.net):")
    for svc in EMAIL_SIGNUP_SERVICES:
        print(f"   ✓ {svc['name']}: {svc['url']}")
        print(f"     → {svc['notes']}")
    
    print("\n🔔 The script will:")
    print("   - Open each service in the browser")
    print("   - BEEP when manual action needed")
    print("   - Wait for you to complete signup/login")
    print("   - Extract and save the API key")
    
    print("\n💡 WORKFLOW:")
    print("   1. Browser opens to signup page")
    print("   2. 🔔 BEEP - Complete signup manually")
    print("   3. Get API key from their dashboard")
    print("   4. Script auto-saves it to database")
    print("   5. Repeat for next service")
    
    print("\n" + "="*60)

def manual_workflow():
    """Guide user through manual API key collection"""
    db = APIKeyDatabase()
    
    print_instructions()
    
    notify("Ready to start! Press Enter to begin...")
    input()
    
    print("\n🚀 Starting with Google SSO services...")
    
    for svc in GOOGLE_SSO_SERVICES:
        print(f"\n{'='*60}")
        print(f"📍 Service: {svc['name']}")
        print(f"🔗 URL: {svc['url']}")
        print(f"📝 Notes: {svc['notes']}")
        print(f"{'='*60}")
        
        notify(f"Opening {svc['name']} - Complete signup and get API key!")
        
        # Open browser (MCP Playwright will handle this)
        print(f"\n✓ Opening {svc['url']} in browser...")
        print("  1. Sign in with Google using api-manager@blking.net")
        print("  2. Navigate to API key section")
        print("  3. Copy the API key")
        print("  4. Come back here and paste it\n")
        
        # Wait for user to get the key
        api_key = input(f"Enter API key for {svc['name']} (or 'skip'): ").strip()
        
        if api_key and api_key.lower() != 'skip':
            db.save_api_key(svc['name'], api_key)
            print(f"✅ Saved API key for {svc['name']}")
        else:
            print(f"⏭️  Skipped {svc['name']}")
    
    print("\n\n🚀 Now moving to email signup services...")
    
    for svc in EMAIL_SIGNUP_SERVICES:
        print(f"\n{'='*60}")
        print(f"📍 Service: {svc['name']}")
        print(f"🔗 URL: {svc['url']}")
        print(f"📝 Notes: {svc['notes']}")
        print(f"{'='*60}")
        
        notify(f"Opening {svc['name']} - Use api-manager@blking.net!")
        
        print(f"\n✓ Opening {svc['url']} in browser...")
        print("  1. Sign up with email: api-manager@blking.net")
        print("  2. Check Gmail for verification email if needed")
        print("  3. Get API key from dashboard/profile")
        print("  4. Come back here and paste it\n")
        
        api_key = input(f"Enter API key for {svc['name']} (or 'skip'): ").strip()
        
        if api_key and api_key.lower() != 'skip':
            db.save_api_key(svc['name'], api_key)
            print(f"✅ Saved API key for {svc['name']}")
        else:
            print(f"⏭️  Skipped {svc['name']}")
    
    print("\n\n" + "="*60)
    print("🎉 COLLECTION SESSION COMPLETE!")
    print("="*60)
    db.status_report()
    
    print("\n💾 To export all keys:")
    print("   python3 live_api_hunter.py --export")

if __name__ == "__main__":
    try:
        manual_workflow()
    except KeyboardInterrupt:
        print("\n\n⏸️  Paused. Run again to continue from where you left off.")
        db = APIKeyDatabase()
        db.status_report()
