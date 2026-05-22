#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT Ultimate v3.0 - Tüm internet OSINT kaynaklarını kullanan araç
Flask tabanlı - hiçbir versiyon sorunu çıkarmaz!
"""

import os
import sys
import re
import json
import socket
import ssl
import hashlib
import urllib.parse
import time
import threading
import subprocess
import html
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote

# =========================================================================
# OTO-KURULUM MEKANİZMASI 
# =========================================================================
def check_and_install_requirements():
    requirements = {
        "flask": "flask",
        "requests": "requests",
        "dns": "dnspython",
        "whois": "python-whois",
        "bs4": "beautifulsoup4",
        "phonenumbers": "phonenumbers",
        "pycountry": "pycountry"
    }
    
    for module_name, pip_name in requirements.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"[*] Eksik kütüphane kuruluyor: {pip_name}...")
            os.system(f"{sys.executable} -m pip install {pip_name} -q")

check_and_install_requirements()

# Kütüphaneler garantilendiğine göre import edebiliriz
from flask import Flask, request, render_template_string, jsonify
import requests
import dns.resolver
import dns.reversename
import whois
from bs4 import BeautifulSoup

app = Flask(__name__)

# =========================================================================
# API Anahtarları
# =========================================================================
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
})

def safe_get(url, timeout=15, **kwargs):
    try: 
        return session.get(url, timeout=timeout, **kwargs)
    except: 
        return None

# =========================================================================
# HTML ŞABLON (CSS + JS dahil, tek sayfa)
# =========================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕵️ OSINT Ultimate Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0e17; color: #e0e0e0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { text-align: center; padding: 30px 0; border-bottom: 1px solid #1a2a4a; margin-bottom: 30px; }
        header h1 { font-size: 2.5em; background: linear-gradient(135deg, #00d4aa, #0088ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        header p { color: #8899aa; margin-top: 10px; font-size: 1.1em; }
        .warning-banner { background: #1a0a0a; border: 1px solid #ff4444; border-radius: 8px; padding: 12px 20px; margin-bottom: 25px; color: #ff6666; text-align: center; font-weight: bold; }
        .tab-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 25px; }
        .tab-btn { padding: 12px 24px; background: #151d2e; border: 1px solid #1a2a4a; border-radius: 8px; color: #8899aa; cursor: pointer; font-size: 15px; transition: all 0.3s; }
        .tab-btn:hover { background: #1a2a4a; color: #fff; }
        .tab-btn.active { background: #00d4aa; color: #000; border-color: #00d4aa; font-weight: bold; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .card { background: #111927; border: 1px solid #1a2a4a; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
        .card h3 { color: #00d4aa; margin-bottom: 15px; font-size: 1.3em; }
        .input-group { display: flex; gap: 12px; margin-bottom: 15px; flex-wrap: wrap; }
        .input-group input { flex: 1; min-width: 250px; padding: 14px 18px; background: #0d1525; border: 1px solid #1a2a4a; border-radius: 8px; color: #fff; font-size: 15px; }
        .input-group input:focus { outline: none; border-color: #00d4aa; }
        .btn { padding: 14px 32px; background: #00d4aa; border: none; border-radius: 8px; color: #000; font-weight: bold; font-size: 15px; cursor: pointer; transition: all 0.3s; }
        .btn:hover { background: #00ffc0; transform: translateY(-2px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .output-box { background: #0a0e17; border: 1px solid #1a2a4a; border-radius: 8px; padding: 20px; min-height: 200px; max-height: 500px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; color: #c0c0c0; margin-top: 15px; }
        .output-box .success { color: #00ff88; }
        .output-box .error { color: #ff4444; }
        .output-box .warning { color: #ffaa00; }
        .output-box .info { color: #44aaff; }
        .output-box .header { color: #ff44ff; font-weight: bold; }
        .spinner { display: none; text-align: center; padding: 20px; }
        .spinner.active { display: block; }
        .spinner::after { content: ''; display: inline-block; width: 40px; height: 40px; border: 4px solid #1a2a4a; border-top-color: #00d4aa; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .api-status { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; margin-bottom: 20px; }
        .api-item { background: #0d1525; border: 1px solid #1a2a4a; border-radius: 6px; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; }
        .api-item .status { font-size: 1.2em; }
        .api-item .status.ok { color: #00ff88; }
        .api-item .status.no { color: #ff4444; }
        footer { text-align: center; padding: 30px 0; color: #445566; border-top: 1px solid #1a2a4a; margin-top: 40px; }
        @media (max-width: 768px) {
            .tab-btn { flex: 1; text-align: center; padding: 10px 16px; font-size: 13px; }
            .input-group { flex-direction: column; }
            .input-group input { min-width: 100%; }
            .btn { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🕵️ OSINT ULTIMATE TOOL</h1>
            <p>İnternetteki tüm açık kaynak istihbarat kaynaklarını kullanan kapsamlı araç</p>
        </header>
        
        <div class="warning-banner">⚠️ YALNIZCA YETKİLİ GÜVENLİK TESTLERİ İÇİN KULLANIN</div>
        
        <div class="api-status">
            <div class="api-item"><span>Shodan</span><span class="status {{ 'ok' if shodan_ok else 'no' }}">{{ '✅' if shodan_ok else '❌' }}</span></div>
            <div class="api-item"><span>HIBP (Breach)</span><span class="status {{ 'ok' if hibp_ok else 'no' }}">{{ '✅' if hibp_ok else '❌' }}</span></div>
            <div class="api-item"><span>GitHub</span><span class="status {{ 'ok' if github_ok else 'no' }}">{{ '✅' if github_ok else '❌' }}</span></div>
            <div class="api-item"><span>AbuseIPDB</span><span class="status {{ 'ok' if abuse_ok else 'no' }}">{{ '✅' if abuse_ok else '❌' }}</span></div>
            <div class="api-item"><span>WHOIS</span><span class="status ok">✅</span></div>
            <div class="api-item"><span>DNS</span><span class="status ok">✅</span></div>
        </div>
        
        <div class="tab-container">
            <button class="tab-btn active" onclick="switchTab('email')">📧 Email</button>
            <button class="tab-btn" onclick="switchTab('domain')">🌐 Domain</button>
            <button class="tab-btn" onclick="switchTab('ip')">🌍 IP</button>
            <button class="tab-btn" onclick="switchTab('username')">👤 Username</button>
            <button class="tab-btn" onclick="switchTab('phone')">📱 Telefon</button>
            <button class="tab-btn" onclick="switchTab('dork')">🔎 Google Dork</button>
        </div>
        
        <div id="tab-email" class="tab-content active">
            <div class="card">
                <h3>📧 Email OSINT</h3>
                <div class="input-group">
                    <input type="text" id="email-input" placeholder="ornek@email.com">
                    <button class="btn" onclick="runOSINT('email')">🔍 Tara</button>
                </div>
                <div class="spinner" id="spinner-email"></div>
                <div class="output-box" id="output-email">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <div id="tab-domain" class="tab-content">
            <div class="card">
                <h3>🌐 Domain OSINT</h3>
                <div class="input-group">
                    <input type="text" id="domain-input" placeholder="ornek.com">
                    <button class="btn" onclick="runOSINT('domain')">🔍 Tara</button>
                </div>
                <div class="spinner" id="spinner-domain"></div>
                <div class="output-box" id="output-domain">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <div id="tab-ip" class="tab-content">
            <div class="card">
                <h3>🌍 IP OSINT</h3>
                <div class="input-group">
                    <input type="text" id="ip-input" placeholder="8.8.8.8">
                    <button class="btn" onclick="runOSINT('ip')">🔍 Tara</button>
                </div>
                <div class="spinner" id="spinner-ip"></div>
                <div class="output-box" id="output-ip">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <div id="tab-username" class="tab-content">
            <div class="card">
                <h3>👤 Username OSINT</h3>
                <div class="input-group">
                    <input type="text" id="username-input" placeholder="kullaniciadi">
                    <button class="btn" onclick="runOSINT('username')">🔍 Tara</button>
                </div>
                <div class="spinner" id="spinner-username"></div>
                <div class="output-box" id="output-username">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <div id="tab-phone" class="tab-content">
            <div class="card">
                <h3>📱 Telefon OSINT</h3>
                <div class="input-group">
                    <input type="text" id="phone-input" placeholder="+905551234567">
                    <button class="btn" onclick="runOSINT('phone')">🔍 Tara</button>
                </div>
                <div class="spinner" id="spinner-phone"></div>
                <div class="output-box" id="output-phone">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <div id="tab-dork" class="tab-content">
            <div class="card">
                <h3>🔎 Google Dork</h3>
                <div class="input-group">
                    <input type="text" id="dork-input" placeholder='site:ornek.com filetype:pdf "gizli"'>
                    <button class="btn" onclick="runOSINT('dork')">🔍 Ara</button>
                </div>
                <div class="spinner" id="spinner-dork"></div>
                <div class="output-box" id="output-dork">Sonuçlar burada görünecek...</div>
            </div>
        </div>
        
        <footer>OSINT Ultimate Tool v3.0 - Flask ile çalışır, hiçbir versiyon sorunu çıkarmaz 🚀<br>API anahtarlarını .env dosyasına ekleyin</footer>
    </div>
    
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tab).classList.add('active');
            document.querySelector(`.tab-btn[onclick="switchTab('${tab}')"]`).classList.add('active');
        }
        
        function runOSINT(module) {
            const input = document.getElementById(module + '-input');
            const output = document.getElementById('output-' + module);
            const spinner = document.getElementById('spinner-' + module);
            const value = input.value.trim();
            
            if (!value) { output.innerHTML = '<span class="error">❌ Lütfen bir değer girin!</span>'; return; }
            
            spinner.classList.add('active');
            output.innerHTML = '<span class="info">⏳ Taranıyor...</span>';
            
            fetch('/api/' + module, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: value})
            })
            .then(r => r.json())
            .then(data => {
                output.innerHTML = data.result;
                spinner.classList.remove('active');
            })
            .catch(err => {
                output.innerHTML = '<span class="error">❌ Hata: ' + err + '</span>';
                spinner.classList.remove('active');
            });
        }
        
        document.querySelectorAll('input').forEach(inp => {
            inp.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const parent = this.closest('.tab-content');
                    if (parent) {
                        const id = parent.id.replace('tab-', '');
                        runOSINT(id);
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

# =========================================================================
# OSINT FONKSİYONLARI
# =========================================================================

def email_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "📧 EMAIL OSINT: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    valid = bool(re.match(pattern, value))
    lines.append(f"\n[+] Format: {'✅ Geçerli' if valid else '❌ Geçersiz'}")
    
    if valid:
        domain = value.split("@")[1]
        lines.append(f"    Domain: {html.escape(domain)}")
        
        try:
            mx = dns.resolver.resolve(domain, "MX", lifetime=5)
            lines.append(f"    MX Kayıtları:")
            for m in mx:
                lines.append(f"      • {html.escape(str(m.exchange).rstrip('.'))}")
        except: 
            pass
        
        if HIBP_API_KEY:
            try:
                h = {"hibp-api-key": HIBP_API_KEY, "user-agent": "osint-ultimate"}
                r = session.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(value)}", headers=h, timeout=15)
                if r.status_code == 200:
                    breaches = r.json()
                    lines.append(f"\n[+] 🔴 DATA BREACH ({len(breaches)} adet):")
                    for b in breaches[:10]:
                        lines.append(f"      • {html.escape(b.get('Name','?'))} ({html.escape(b.get('BreachDate','?'))})")
                    if len(breaches) > 10:
                        lines.append(f"      ... +{len(breaches)-10} daha")
                else:
                    lines.append(f"\n[+] ✅ Breach bulunamadı")
            except Exception as e:
                lines.append(f"\n[!] HIBP hatası: {html.escape(str(e))}")
        
        h_md5 = hashlib.md5(value.lower().encode()).hexdigest()
        r = safe_get(f"https://www.gravatar.com/avatar/{h_md5}?d=404")
        if r and r.status_code == 200:
            lines.append(f"\n[+] Gravatar: https://www.gravatar.com/avatar/{h_md5}")
        
        if GITHUB_TOKEN:
            try:
                r = session.get(f"https://api.github.com/search/users?q={quote(value)}+in%3Aemail",
                                headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
                if r.status_code == 200:
                    users = r.json().get("items", [])
                    if users:
                        lines.append(f"\n[+] GitHub Bağlantıları:")
                        for u in users[:5]:
                            lines.append(f"      • {html.escape(u['login'])} -> {html.escape(u['html_url'])}")
            except: 
                pass
    
    return "<br>".join(lines)

def domain_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "🌐 DOMAIN OSINT: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    try:
        w = whois.whois(value)
        lines.append(f"\n[+] WHOIS:")
        for k in ["registrar","creation_date","expiration_date","name_servers","organization","country","emails"]:
            v = w.get(k)
            if v:
                if isinstance(v, list): v = ", ".join(str(x) for x in v[:3])
                lines.append(f"    {k.replace('_',' ').title()}: {html.escape(str(v))}")
    except Exception as e:
        lines.append(f"\n[!] WHOIS hatası: {html.escape(str(e))}")
    
    lines.append(f"\n[+] DNS Kayıtları:")
    for rtype in ["A","AAAA","MX","NS","TXT","SOA","CNAME"]:
        try:
            answers = dns.resolver.resolve(value, rtype, lifetime=5)
            for a in answers:
                txt = str(a)
                if rtype in ("MX","SRV") and hasattr(a, "exchange"):
                    txt = str(a.exchange).rstrip(".")
                lines.append(f"    {rtype}: {html.escape(txt)}")
        except: 
            pass
    
    try:
        r = safe_get(f"https://crt.sh/?q=%25.{value}&output=json", timeout=15)
        if r and r.status_code == 200:
            subs = set()
            for entry in r.json()[:80]:
                for s in entry.get("name_value","").split("\n"):
                    s = s.strip().lower()
                    if s.endswith(f".{value}") and s != f"*.{value}":
                        subs.add(s)
            if subs:
                lines.append(f"\n[+] Subdomain ({len(subs)}):")
                for s in sorted(subs)[:20]:
                    lines.append(f"    • {html.escape(s)}")
    except: 
        pass
    
    return "<br>".join(lines)

def ip_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "🌍 IP OSINT: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    try:
        r = safe_get(f"http://ip-api.com/json/{value}")
        if r and r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                lines.append(f"\n[+] Konum Bilgileri:")
                for k in ["country","regionName","city","isp","org","as","lat","lon","timezone"]:
                    if d.get(k): 
                        lines.append(f"    {k.replace('regionName','Region').title()}: {html.escape(str(d[k]))}")
    except: 
        pass
    
    try:
        rev = str(dns.reversename.from_address(value))
        answers = dns.resolver.resolve(rev, "PTR", lifetime=5)
        lines.append(f"\n[+] Reverse DNS: {html.escape(', '.join(str(a) for a in answers))}")
    except: 
        pass

    # Shodan API Sorgusu (Eklenen Kısım)
    if SHODAN_API_KEY:
        try:
            r = session.get(f"https://api.shodan.io/shodan/host/{value}?key={SHODAN_API_KEY}", timeout=10)
            if r.status_code == 200:
                sd = r.json()
                lines.append(f"\n[+] Shodan İstihbaratı:")
                if sd.get("os"): lines.append(f"    İşletim Sistemi: {html.escape(str(sd['os']))}")
                if sd.get("ports"): lines.append(f"    Algılanan Portlar: {', '.join(str(p) for p in sd['ports'])}")
                if sd.get("vulns"): lines.append(f"    Zafiyetler (CVE): {html.escape(', '.join(sd['vulns'][:10]))}")
        except Exception as e:
            lines.append(f"\n[!] Shodan sorgu hatası: {html.escape(str(e))}")
    
    lines.append(f"\n[+] Aktif Port Taraması:")
    ports = [21,22,23,25,53,80,81,110,111,135,139,143,443,445,993,995,
             1433,1521,2049,3306,3389,5432,5900,5985,5986,6379,8080,8443,9000,9090,27017]
    open_ports = []
    
    def check(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            res = s.connect_ex((value, p))
            s.close()
            return p if res == 0 else None
        except: 
            return None
            
    with ThreadPoolExecutor(max_workers=50) as ex:
        for f in as_completed({ex.submit(check, p): p for p in ports}):
            res = f.result()
            if res: 
                open_ports.append(res)
                
    if open_ports:
        lines.append(f"    Açık: {', '.join(str(p) for p in sorted(open_ports))}")
    else:
        lines.append("    Hiçbir yaygın port açık tespit edilmedi.")
    
    if ABUSEIPDB_API_KEY:
        try:
            r = session.get(f"https://api.abuseipdb.com/api/v2/check?ipAddress={value}",
                            headers={"Key": ABUSEIPDB_API_KEY, "Accept": "application/json"}, timeout=10)
            if r.status_code == 200:
                d = r.json().get("data", {})
                score = d.get("abuseConfidenceScore", 0)
                lines.append(f"\n[+] AbuseIPDB Raporu: Skor={score}% {'🔴' if score>50 else '✅'} Toplam Rapor={d.get('totalReports',0)}")
        except: 
            pass
    
    return "<br>".join(lines)

def username_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "👤 USERNAME OSINT: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    platforms = [
        ("GitHub", f"https://github.com/{value}"),
        ("Twitter/X", f"https://twitter.com/{value}"),
        ("Instagram", f"https://www.instagram.com/{value}/"),
        ("Reddit", f"https://www.reddit.com/user/{value}"),
        ("Medium", f"https://medium.com/@{value}"),
        ("Dev.to", f"https://dev.to/{value}"),
        ("Keybase", f"https://keybase.io/{value}"),
        ("Telegram", f"https://t.me/{value}"),
        ("Twitch", f"https://www.twitch.tv/{value}"),
        ("TikTok", f"https://www.tiktok.com/@{value}"),
        ("YouTube", f"https://www.youtube.com/@{value}"),
        ("LinkedIn", f"https://www.linkedin.com/in/{value}/"),
        ("Steam", f"https://steamcommunity.com/id/{value}"),
        ("Spotify", f"https://open.spotify.com/user/{value}"),
        ("Patreon", f"https://www.patreon.com/{value}"),
        ("HackerOne", f"https://hackerone.com/{value}"),
        ("Bugcrowd", f"https://bugcrowd.com/{value}"),
        ("TryHackMe", f"https://tryhackme.com/p/{value}"),
    ]
    
    lines.append(f"\n[+] Platform Taraması ({len(platforms)} site):")
    found = False
    for name, url in platforms:
        try:
            r = safe_get(url, timeout=5)
            if r and r.status_code == 200:
                lines.append(f"    ✅ {name}: {html.escape(url)}")
                found = True
                time.sleep(0.1)
        except: 
            pass
    
    if not found:
        lines.append("    ❌ Hiçbir platformda halka açık profil bulunamadı.")
    
    return "<br>".join(lines)

def phone_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "📱 TELEFON OSINT: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    try:
        import phonenumbers
        from phonenumbers import carrier, geocoder, timezone as pn_tz
        
        num = phonenumbers.parse(value, None)
        lines.append(f"\n[+] Numaralandırma Bilgileri:")
        lines.append(f"    Ülke Kodu: +{num.country_code}")
        lines.append(f"    Ulusal Format: {html.escape(phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL))}")
        lines.append(f"    Uluslararası Format: {html.escape(phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL))}")
        lines.append(f"    Geçerlilik Durumu: {'✅ Geçerli' if phonenumbers.is_valid_number(num) else '❌ Geçersiz'}")
        
        region = phonenumbers.region_code_for_number(num)
        if region:
            try:
                import pycountry
                c = pycountry.countries.get(alpha_2=region)
                lines.append(f"    Ülke: {html.escape(c.name if c else region)}")
            except: 
                lines.append(f"    Ülke: {html.escape(region)}")
        
        tz = pn_tz.time_zones_for_number(num)
        if tz: 
            lines.append(f"    Zaman Dilimi: {html.escape(', '.join(tz))}")
        
        op = carrier.name_for_number(num, "en")
        if op: 
            lines.append(f"    Operatör (Kayıtlı): {html.escape(op)}")
        
        loc = geocoder.description_for_number(num, "en")
        if loc: 
            lines.append(f"    Konum/Bölge: {html.escape(loc)}")
            
    except ImportError:
        lines.append("\n⚠️ Sistemde 'phonenumbers' veya 'pycountry' modülü eksik.")
    except Exception as e:
        lines.append(f"\n❌ Çözümleme Hatası: {html.escape(str(e))}")
    
    return "<br>".join(lines)

def dork_osint(value):
    clean_val = html.escape(value)
    lines = ["═══════════════════════════════════════════════════",
             "🔎 GOOGLE DORK SORGUSU: " + clean_val,
             "═══════════════════════════════════════════════════"]
    
    try:
        url = f"https://www.google.com/search?q={quote(value)}&num=10"
        r = safe_get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        if r and r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            results = soup.select("div.g")
            if results:
                lines.append(f"\n[+] Bulunan Sonuçlar ({len(results)}):")
                for i, res in enumerate(results[:10], 1):
                    h3 = res.select_one("h3")
                    a = res.select_one("a")
                    if h3 and a:
                        link = a.get("href","")
                        if link.startswith("/url?q="):
                            parsed_url = urllib.parse.urlparse(link)
                            qs = urllib.parse.parse_qs(parsed_url.query)
                            link = qs.get("q", [link])[0]
                            
                        lines.append(f"\n  {i}. {html.escape(h3.get_text(strip=True))}")
                        lines.append(f"     {html.escape(link[:200])}")
            else:
                lines.append("\n  Arama sonucu dönmedi (Google bot korumasına veya Captcha'ya takılmış olabilir)")
        else:
            lines.append("\n  Google arama motoruna erişim sağlanamadı (HTTP Engellemesi)")
    except Exception as e:
        lines.append(f"\n  Arama hatası: {html.escape(str(e))}")
    
    return "<br>".join(lines)

# =========================================================================
# FLASK ROUTES
# =========================================================================

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE,
        shodan_ok=bool(SHODAN_API_KEY),
        hibp_ok=bool(HIBP_API_KEY),
        github_ok=bool(GITHUB_TOKEN),
        abuse_ok=bool(ABUSEIPDB_API_KEY)
    )

@app.route("/api/<module>", methods=["POST"])
def api(module):
    data = request.get_json() or {}
    value = data.get("value", "").strip()
    
    if not value:
        return jsonify({"result": '<span class="error">❌ Giriş değeri boş bırakılamaz!</span>'})
    
    try:
        if module == "email": result = email_osint(value)
        elif module == "domain": result = domain_osint(value)
        elif module == "ip": result = ip_osint(value)
        elif module == "username": result = username_osint(value)
        elif module == "phone": result = phone_osint(value)
        elif module == "dork": result = dork_osint(value)
        else: result = '<span class="error">❌ Geçersiz veya bilinmeyen modül çağrısı!</span>'
    except Exception as e:
        result = f'<span class="error">❌ Kritik Sunucu Hatası: {html.escape(str(e))}</span>'
    
    return jsonify({"result": result})

# =========
# ================================================================
# ANA ÇALIŞTIRMA
# =========================================================================

if __name__ == "__main__":
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""# OSINT Ultimate API Anahtarları
SHODAN_API_KEY=
GITHUB_TOKEN=
HIBP_API_KEY=
ABUSEIPDB_API_KEY=
""")
    
    print("""
╔═══════════════════════════════════════════════════╗
║     🕵️  OSINT ULTIMATE TOOL v3.0                  ║
║     Tüm internet OSINT kaynaklarını kullanır      ║
║     Yalnızca yetkili testler için!                ║
╚═══════════════════════════════════════════════════╝
    """)
    
    print(f"[+] Web arayüzü başlatıldı: http://127.0.0.1:5000")
    print("[+] Kapatmak için terminalde Ctrl+C tuşlarına basın.\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)