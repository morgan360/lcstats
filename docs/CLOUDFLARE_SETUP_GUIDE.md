# Cloudflare Setup Guide for NumScoil
## Multi-Domain SSL Setup with Zero Downtime

This guide will help you set up both lcai.ie and numscoil.ie with free SSL certificates using Cloudflare, pointing to your single PythonAnywhere web app.

---

## Prerequisites
- ✅ Access to your domain registrar for lcai.ie
- ✅ Access to your domain registrar for numscoil.ie
- ✅ PythonAnywhere web app running at www.lcai.ie
- ✅ Updated ALLOWED_HOSTS in Django settings

---

## Phase 1: Cloudflare Account Setup (5 minutes)

### Step 1.1: Create Cloudflare Account
1. Go to https://www.cloudflare.com
2. Click **Sign Up** (top right)
3. Enter your email and create a password
4. Verify your email address

### Step 1.2: Add Your First Domain (lcai.ie)
1. After login, click **Add a Site**
2. Enter: `lcai.ie` (without www)
3. Click **Add site**
4. Select **Free Plan** ($0/month)
5. Click **Continue**

### Step 1.3: Review DNS Records
Cloudflare will automatically scan and import your existing DNS records.

**Verify these records exist:**
- `A` or `CNAME` record for `lcai.ie` → (your current IP/hostname)
- `A` or `CNAME` record for `www.lcai.ie` → (your current IP/hostname)

**If missing, add them manually:**
- **Type**: CNAME
- **Name**: `@` (for root domain)
- **Target**: `webapp-51817.eu.pythonanywhere.com`
- **Proxy status**: 🟠 Proxied (orange cloud - click to toggle)

- **Type**: CNAME
- **Name**: `www`
- **Target**: `webapp-51817.eu.pythonanywhere.com`
- **Proxy status**: 🟠 Proxied (orange cloud)

Click **Continue**

---

## Phase 2: Configure SSL/TLS Settings (3 minutes)

### Step 2.1: SSL/TLS Configuration
1. In Cloudflare dashboard, click **SSL/TLS** (left sidebar)
2. Select **Full** mode (NOT Full (strict))
   - This is important! PythonAnywhere has its own SSL
3. Enable **Always Use HTTPS**:
   - Go to **SSL/TLS** → **Edge Certificates**
   - Toggle **Always Use HTTPS** to ON
4. Enable **Automatic HTTPS Rewrites**: Toggle ON

### Step 2.2: Additional Security (Optional but Recommended)
1. Go to **SSL/TLS** → **Edge Certificates**
2. Enable **Minimum TLS Version**: TLS 1.2 or higher
3. Enable **Opportunistic Encryption**: ON

---

## Phase 3: Update Nameservers (The Switch) - lcai.ie

⚠️ **Important**: This is where the switch happens. No downtime, but DNS propagation takes time.

### Step 3.1: Get Cloudflare Nameservers
Cloudflare will show you two nameservers like:
```
ava.ns.cloudflare.com
brad.ns.cloudflare.com
```
**Copy these down** - you'll need them!

### Step 3.2: Update at Your Domain Registrar
1. Log into your domain registrar (where you bought lcai.ie)
2. Find DNS/Nameserver settings
3. **Change nameservers** from current to Cloudflare's nameservers
4. Save changes

**Common Registrars:**
- **Blacknight.com**: Domains → Manage → Nameservers
- **GoDaddy**: Domain Settings → Nameservers → Change
- **Namecheap**: Domain List → Manage → Nameservers → Custom DNS

### Step 3.3: Verify in Cloudflare
1. Return to Cloudflare
2. Click **Done, check nameservers**
3. Cloudflare will start checking (can take up to 24 hours)
4. You'll receive an email when it's active

**During this time:**
- ✅ Your site continues to work normally
- ⏳ Some users gradually start routing through Cloudflare
- ✅ Both paths work (old direct path + new Cloudflare path)

---

## Phase 4: Add Second Domain (numscoil.ie)

### Step 4.1: Add numscoil.ie to Cloudflare
1. In Cloudflare dashboard, click your account name (top left)
2. Click **Add a Site**
3. Enter: `numscoil.ie`
4. Select **Free Plan**
5. Click **Continue**

### Step 4.2: Configure DNS for numscoil.ie
Add these DNS records:

**Root domain:**
- **Type**: CNAME
- **Name**: `@`
- **Target**: `webapp-51817.eu.pythonanywhere.com`
- **Proxy status**: 🟠 Proxied

**WWW subdomain:**
- **Type**: CNAME
- **Name**: `www`
- **Target**: `webapp-51817.eu.pythonanywhere.com`
- **Proxy status**: 🟠 Proxied

Click **Continue**

### Step 4.3: Configure SSL for numscoil.ie
Same as Phase 2:
1. **SSL/TLS** → Select **Full** mode
2. Enable **Always Use HTTPS**
3. Enable **Automatic HTTPS Rewrites**

### Step 4.4: Update Nameservers for numscoil.ie
1. Cloudflare will show you nameservers (same or different from lcai.ie)
2. Log into your numscoil.ie domain registrar
3. Update nameservers to Cloudflare's nameservers
4. Save changes
5. Return to Cloudflare and click **Done, check nameservers**

---

## Phase 5: Update PythonAnywhere Settings

### Step 5.1: Update .env file
1. Go to PythonAnywhere → **Files** tab
2. Navigate to `/home/morganmck/lcstats/.env`
3. Update `ALLOWED_HOSTS` line:
```
ALLOWED_HOSTS=morganmck.pythonanywhere.com,webapp-51817.eu.pythonanywhere.com,www.lcai.ie,lcai.ie,www.numscoil.ie,numscoil.ie
```
4. Save the file

### Step 5.2: Reload Web App
1. Go to **Web** tab
2. Click green **Reload www.lcai.ie** button

### Step 5.3: Disable Force HTTPS (Optional)
Since Cloudflare handles HTTPS now:
1. In **Web** tab, scroll to **Security** section
2. Set **Force HTTPS**: Disabled (optional - Cloudflare handles this)

---

## Phase 6: Verification & Testing (After DNS Propagation)

### Step 6.1: Check DNS Propagation
Use https://dnschecker.org to check if your domains are propagating:
- Enter `lcai.ie` - should show Cloudflare nameservers
- Enter `numscoil.ie` - should show Cloudflare nameservers

⏱️ **Typical times:**
- Starts working: 15 minutes - 2 hours
- Fully propagated: 24-48 hours

### Step 6.2: Test All Domain Variants
Once propagated, test all URLs:
- ✅ https://lcai.ie
- ✅ https://www.lcai.ie
- ✅ https://numscoil.ie
- ✅ https://www.numscoil.ie
- ✅ http://lcai.ie (should redirect to https)
- ✅ http://numscoil.ie (should redirect to https)

### Step 6.3: Check SSL Certificates
1. Visit each URL
2. Click the padlock icon in browser
3. Verify certificate is issued by Cloudflare
4. Should show "Connection is secure"

---

## Phase 7: Additional Cloudflare Optimizations (Optional)

### Performance Improvements
1. **Speed** → **Optimization**
   - Enable **Auto Minify**: HTML, CSS, JS
   - Enable **Brotli** compression
   - Enable **Rocket Loader** (test first - may break some sites)

2. **Caching**
   - Go to **Caching** → **Configuration**
   - Set **Browser Cache TTL**: 4 hours
   - Create **Page Rules** for static files:
     - URL pattern: `*.lcai.ie/static/*`
     - Setting: Cache Level = Cache Everything

### Security Improvements
1. **Security** → **Settings**
   - Set **Security Level**: Medium
   - Enable **Browser Integrity Check**: ON
   - Enable **Challenge Passage**: 30 minutes

2. **Firewall Rules** (optional)
   - Block countries/IPs if needed
   - Rate limiting rules

---

## Troubleshooting

### Issue: Site shows "Too many redirects"
**Solution**:
- Go to Cloudflare → **SSL/TLS**
- Change from "Flexible" to **"Full"**

### Issue: Site not loading at all
**Solution**:
- Check DNS records in Cloudflare are correct
- Verify proxy status (🟠 orange cloud) is enabled
- Wait for DNS propagation (up to 48 hours)

### Issue: Some pages work, others don't
**Solution**:
- Check **ALLOWED_HOSTS** in Django includes all domain variants
- Reload PythonAnywhere web app

### Issue: SSL certificate warning
**Solution**:
- Wait for DNS to fully propagate
- Ensure SSL/TLS mode is set to "Full" in Cloudflare
- Try clearing browser cache

### Issue: Old domain works, new domain doesn't
**Solution**:
- Check nameservers are updated for the new domain
- Verify DNS records exist in Cloudflare for new domain
- Wait for DNS propagation

---

## Final Checklist

### Before Starting:
- [ ] Cloudflare account created
- [ ] Have access to both domain registrars
- [ ] Have PythonAnywhere login ready
- [ ] Noted current DNS settings (backup)

### During Setup:
- [ ] lcai.ie added to Cloudflare
- [ ] DNS records verified for lcai.ie
- [ ] SSL set to "Full" mode for lcai.ie
- [ ] Nameservers updated for lcai.ie
- [ ] numscoil.ie added to Cloudflare
- [ ] DNS records verified for numscoil.ie
- [ ] SSL set to "Full" mode for numscoil.ie
- [ ] Nameservers updated for numscoil.ie
- [ ] ALLOWED_HOSTS updated in .env
- [ ] PythonAnywhere web app reloaded

### After DNS Propagation:
- [ ] Both domains load with HTTPS
- [ ] WWW and non-WWW variants work
- [ ] HTTP redirects to HTTPS
- [ ] Green padlock shows in browser
- [ ] All pages/features working correctly
- [ ] Mobile site works
- [ ] Images/static files loading

---

## Support Resources

- **Cloudflare Help**: https://support.cloudflare.com
- **DNS Checker**: https://dnschecker.org
- **SSL Checker**: https://www.ssllabs.com/ssltest/
- **PythonAnywhere Help**: https://help.pythonanywhere.com

---

## Rollback Plan (If Something Goes Wrong)

If you need to revert:

1. **At domain registrar**: Change nameservers back to original
2. **Wait for DNS to propagate** (24-48 hours)
3. **Site returns to original state**

**Note**: Keep your original nameserver information before starting!

---

## Expected Timeline

| Phase | Duration | Your Site Status |
|-------|----------|------------------|
| Cloudflare setup | 10 minutes | ✅ Online, unchanged |
| Nameserver update | 2 minutes | ✅ Online, unchanged |
| DNS propagation | 2-48 hours | ✅ Online, gradual transition |
| Full activation | 48 hours max | ✅ Online, both domains working |

**Total downtime: 0 seconds** ⚡

---

## Questions?

If anything is unclear during setup, stop and document the issue. The beauty of this approach is there's no rush - your site stays online throughout!

Good luck! 🚀
