/* ============================================================
   HireAI — Main Application JavaScript
   Full SPA routing, charts, dynamic data, interactions
   ============================================================ */

'use strict';

function escapeHTML(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ── Company Domain Map → Clearbit Logo API ───────────────────
const COMPANY_DOMAINS = {
  // Indian IT Giants
  'tcs': 'tcs.com', 'tata consultancy services': 'tcs.com',
  'infosys': 'infosys.com',
  'wipro': 'wipro.com',
  'hcl': 'hcltech.com', 'hcl technologies': 'hcltech.com',
  'tech mahindra': 'techmahindra.com',
  'mphasis': 'mphasis.com',
  'hexaware': 'hexaware.com',
  'mindtree': 'mindtree.com',
  'ltimindtree': 'ltimindtree.com',
  'persistent systems': 'persistent.com',
  'coforge': 'coforge.com',
  'birlasoft': 'birlasoft.com',
  // Indian Product / Startup
  'flipkart': 'flipkart.com',
  'meesho': 'meesho.com',
  'zomato': 'zomato.com',
  'swiggy': 'swiggy.com',
  'ola': 'olacabs.com',
  'oyo': 'oyorooms.com',
  'razorpay': 'razorpay.com',
  'paytm': 'paytm.com',
  'phonepe': 'phonepe.com',
  'cred': 'cred.club',
  'nykaa': 'nykaa.com',
  'byju\'s': 'byjus.com', 'byjus': 'byjus.com',
  'unacademy': 'unacademy.com',
  'groww': 'groww.in',
  'zerodha': 'zerodha.com',
  'freshworks': 'freshworks.com',
  'zoho': 'zoho.com',
  'postman': 'postman.com',
  'browserstack': 'browserstack.com',
  'naukri.com': 'naukri.com', 'naukri': 'naukri.com',
  'nazara technologies': 'nazaratechnologies.com', 'nazara': 'nazaratechnologies.com',
  // Indian Telecom / Conglomerates
  'jio': 'jio.com', 'reliance jio': 'jio.com',
  'airtel': 'airtel.in',
  'bsnl': 'bsnl.co.in',
  'tata': 'tata.com',
  // Global Companies (India offices)
  'google': 'google.com',
  'microsoft': 'microsoft.com',
  'amazon': 'amazon.com', 'aws': 'aws.amazon.com',
  'meta': 'meta.com', 'facebook': 'meta.com',
  'apple': 'apple.com',
  'ibm': 'ibm.com',
  'oracle': 'oracle.com',
  'sap': 'sap.com', 'sap india': 'sap.com',
  'salesforce': 'salesforce.com', 'salesforce india': 'salesforce.com',
  'adobe': 'adobe.com',
  'accenture': 'accenture.com', 'accenture india': 'accenture.com',
  'deloitte': 'deloitte.com', 'deloitte india': 'deloitte.com',
  'pwc': 'pwc.com',
  'kpmg': 'kpmg.com',
  'ey': 'ey.com', 'ernst & young': 'ey.com',
  'mckinsey': 'mckinsey.com',
  'capgemini': 'capgemini.com',
  'cognizant': 'cognizant.com',
  'dxc': 'dxc.com', 'dxc technology': 'dxc.com',
  'atos': 'atos.net',
  'nvidia': 'nvidia.com',
  'intel': 'intel.com',
  'qualcomm': 'qualcomm.com',
  'samsung': 'samsung.com',
  'bosch': 'bosch.com',
  'siemens': 'siemens.com',
  'jp morgan': 'jpmorgan.com', 'jpmorgan': 'jpmorgan.com',
  'goldman sachs': 'goldmansachs.com',
  'morgan stanley': 'morganstanley.com',
  'deutsche bank': 'db.com',
  'hsbc': 'hsbc.com',
  'barclays': 'barclays.com',
  'linkedin': 'linkedin.com',
  'twitter': 'twitter.com', 'x': 'x.com',
  'uber': 'uber.com',
  'netflix': 'netflix.com',
  'spotify': 'spotify.com',
  'slack': 'slack.com',
  'atlassian': 'atlassian.com',
  'jfrog': 'jfrog.com',
  'gitlab': 'gitlab.com',
  'github': 'github.com',
  // ── Aerospace & Defence ──
  'isro': 'isro.gov.in',
  'hal': 'hal-india.co.in', 'hindustan aeronautics': 'hal-india.co.in',
  'drdo': 'drdo.gov.in',
  'safran': 'safran-group.com', 'safran engineering india': 'safran-group.com',
  'honeywell': 'honeywell.com', 'honeywell india': 'honeywell.com',
  // ── Electric Vehicles & CleanTech ──
  'ola electric': 'olaelectric.com',
  'tata motors': 'tatamotors.com', 'tata motors ev': 'tatamotors.com',
  'revolt motors': 'revoltmotors.in',
  'greaves electric': 'greavescotton.com',
  'renew power': 'renewpower.in',
  'ather energy': 'atherenergy.com',
  // ── Pharma & BioTech ──
  "dr. reddy's": 'drreddys.com', "dr. reddy's laboratories": 'drreddys.com',
  'sun pharma': 'sunpharma.com',
  'cipla': 'cipla.com',
  'medgenome': 'medgenome.com',
  // ── Government Tech ──
  'npci': 'npci.org.in', 'npci (upi)': 'npci.org.in',
  'uidai': 'uidai.gov.in', 'uidai (aadhaar)': 'uidai.gov.in',
  'nic': 'nic.in', 'nic (national informatics centre)': 'nic.in',
  'c-dac': 'cdac.in', 'c-dac india': 'cdac.in',
  // ── Retail & D2C ──
  'reliance retail': 'relianceretail.com',
  'decathlon': 'decathlon.co.in', 'decathlon india': 'decathlon.co.in',
  'mamaearth': 'mamaearth.in',
  'boat': 'boat-lifestyle.com', 'boat lifestyle': 'boat-lifestyle.com',
  // ── HR Tech ──
  'darwinbox': 'darwinbox.com',
  'hackerearth': 'hackerearth.com', 'iimjobs.com / hackerearth': 'hackerearth.com',
  'keka hr': 'keka.com', 'keka': 'keka.com',
  'spotdraft': 'spotdraft.com',
  // ── PropTech ──
  'nobroker': 'nobroker.in',
  '99acres': '99acres.com', '99acres (info edge)': '99acres.com',
  'square yards': 'squareyards.com',
  // ── AgriTech ──
  'dehaat': 'dehaat.com',
  'cropin': 'cropin.com', 'cropin technology': 'cropin.com',
  'agrostar': 'agrostar.in',
  // ── InsurTech ──
  'acko': 'acko.com', 'acko insurance': 'acko.com',
  'digit insurance': 'godigit.com', 'digit': 'godigit.com',
  'turtlemint': 'turtlemint.com',
  // ── Space Tech ──
  'skyroot': 'skyroot.in', 'skyroot aerospace': 'skyroot.in',
  'agnikul': 'agnikul.in', 'agnikul cosmos': 'agnikul.in',
  'pixxel': 'pixxel.space', 'pixxel space': 'pixxel.space',
  // ── Media & Content ──
  'zee5': 'zee5.com',
  'times internet': 'timesinternet.in',
  'dailyhunt': 'dailyhunt.in', 'verse innovation': 'dailyhunt.in',
  'inmobi': 'inmobi.com',
  // ── Supply Chain ──
  'juspay': 'juspay.in',
  'moglix': 'moglix.com',
  'ofbusiness': 'ofbusiness.com',
  // ── Automotive ──
  'mahindra tech': 'mahindra.com', 'mahindra': 'mahindra.com',
  'tata elxsi': 'tataelxsi.com',
  'maruti suzuki': 'marutisuzuki.com', 'maruti suzuki india': 'marutisuzuki.com',
  // ── International ──
  'uber': 'uber.com', 'uber india': 'uber.com',
  'linkedin': 'linkedin.com', 'linkedin india': 'linkedin.com',
  'adobe': 'adobe.com', 'adobe india': 'adobe.com',
  'spotify': 'spotify.com', 'spotify india': 'spotify.com',
  'netflix': 'netflix.com', 'netflix india': 'netflix.com',
  'zendesk': 'zendesk.com', 'zendesk india': 'zendesk.com',
  // ── More ──
  'polygon': 'polygon.technology', 'polygon (matic)': 'polygon.technology',
  'coindcx': 'coindcx.com',
  'dream11': 'dream11.com',
  'games24x7': 'games24x7.com',
  'mpl': 'mpl.live', 'mobile premier league': 'mpl.live',
  'hotstar': 'hotstar.com', 'jiostar': 'jiostar.com',
  'delhivery': 'delhivery.com',
  'bigbasket': 'bigbasket.com',
  'rapido': 'rapido.bike',
  'palo alto networks': 'paloaltonetworks.com',
  'nutanix': 'nutanix.com',
  'walmart': 'walmart.com', 'walmart global tech': 'walmart.com',
  'fractal analytics': 'fractal.ai', 'fractal': 'fractal.ai',
  'amd': 'amd.com', 'amd india': 'amd.com',
  'texas instruments': 'ti.com',
  'crowdstrike': 'crowdstrike.com',
  'tata communications': 'tatacommunications.com',
  'upstox': 'upstox.com',
  'pine labs': 'pinelabs.com',
  'bajaj finserv': 'bajajfinserv.in',
  'policybazaar': 'policybazaar.com',
  'chargebee': 'chargebee.com',
  'hasura': 'hasura.io',
  'druva': 'druva.com',
};

/**
 * Called when a Clearbit logo fails to load — replaces img with letter avatar.
 */
function onLogoError(img, abbr, color, textColor) {
  const div = document.createElement('div');
  div.style.cssText = `width:44px;height:44px;border-radius:8px;background:${color};color:${textColor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;font-family:'Syne',sans-serif;`;
  div.textContent = abbr;
  img.parentNode.replaceChild(div, img);
}

/**
 * Returns HTML for a company logo — real Clearbit img with letter-avatar fallback.
 */
function getCompanyLogoHTML(companyName, color, textColor) {
  color     = color     || '#e0f2fe';
  textColor = textColor || '#0369a1';
  const key  = (companyName || '').toLowerCase().trim();
  const abbr = (companyName || '??').substring(0, 2).toUpperCase();
  const domain = COMPANY_DOMAINS[key]
    || Object.entries(COMPANY_DOMAINS).find(([k]) => key.includes(k))?.[1];

  if (domain) {
    // Use a named global function in onerror — avoids all escaping issues
    const c = encodeURIComponent(color);
    const t = encodeURIComponent(textColor);
    const a = encodeURIComponent(abbr);
    return `<img src="https://logo.clearbit.com/${domain}" alt="${abbr}"
      style="width:44px;height:44px;object-fit:contain;border-radius:6px;display:block;"
      onerror="onLogoError(this,'${abbr}','${color}','${textColor}')">`;
  }
  // No domain found — immediate letter avatar
  return `<div style="width:44px;height:44px;border-radius:8px;background:${color};color:${textColor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;font-family:'Syne',sans-serif;">${abbr}</div>`;
}


// ── Data Store ──────────────────────────────────────────────
const DB = {
  currentUser: null,
  users: [],
  jobs: [],
  candidates: [],
  talentPool: [],
  notifications: [],
  // Settings state
  settings: {
    emailNotif: true,
    smsNotif: false,
    jobAlerts: true,
    profileVisible: true,
    darkMode: false,
  }
};

// ── Universal Jobs Registry (State-safe lookup across all views & caches) ──
const _allKnownJobsMap = new Map();
function registerKnownJob(job) {
  if (!job) return;
  if (job.id !== undefined && job.id !== null) _allKnownJobsMap.set(String(job.id), job);
  if (job.raw_id !== undefined && job.raw_id !== null) _allKnownJobsMap.set(String(job.raw_id), job);
  if (job.source_job_id !== undefined && job.source_job_id !== null) _allKnownJobsMap.set(String(job.source_job_id), job);
}


// ── Router ───────────────────────────────────────────────────
const Router = {
  current: 'landing',
  innerPages: { cand: 'dash', admin: 'dash', 'platform-admin': 'overview' },

  // Pages that should be saved to the URL hash (dashboard & public pages)
  _hashPages: new Set(['cand', 'admin', 'platform-admin', 'landing', 'login', 'register', 'forgot', 'reset', 'verify', 'about', 'blog', 'careers', 'product', 'contact', 'legal']),

  go(page) {
    // Role-based route guard
    if (DB.currentUser) {
      if (page === 'platform-admin' && DB.currentUser.role !== 'admin') {
        Toast.show('Access denied. Platform Admin privileges required.', 'error');
        const fallback = DB.currentUser.role === 'hr' ? 'admin' : 'cand';
        return this.go(fallback);
      }
      if (page === 'admin' && DB.currentUser.role !== 'hr' && DB.currentUser.role !== 'admin') {
        Toast.show('Access denied. HR privileges required.', 'error');
        return this.go('cand');
      }
    } else {
      const publicPages = ['landing', 'login', 'register', 'forgot', 'reset', 'verify', 'about', 'blog', 'careers', 'product', 'contact', 'legal'];
      if (!publicPages.includes(page)) {
        Toast.show('Please log in to continue.', 'warning');
        return this.go('login');
      }
    }

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById('page-' + page);
    if (el) { el.classList.add('active'); window.scrollTo(0,0); }
    this.current = page;
    // Clear login fields when navigating to login page (prevent stale autofill)
    if (page === 'login') {
      const emailEl = document.getElementById('login-email');
      const passEl  = document.getElementById('login-password');
      if (emailEl) emailEl.value = '';
      if (passEl)  passEl.value  = '';
    }
    // Clear register fields when navigating to register page
    if (page === 'register') {
      ['reg-fname','reg-lname','reg-email','reg-pass','reg-cpass'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
    }
    // Save page to URL hash so refresh restores it
    if (this._hashPages.has(page)) {
      history.replaceState(null, '', '#' + page);
    }
  },

  inner(portal, section) {
    // Role-based inner section guards
    if (portal === 'cand' && section === 'pipeline') {
      Toast.show('The AI/ML Pipeline is restricted to Platform Administrators.', 'warning');
      section = 'dash';
    }
    if (portal === 'platform-admin' && (!DB.currentUser || DB.currentUser.role !== 'admin')) {
      Toast.show('Access denied. Platform Admin privileges required.', 'error');
      if (DB.currentUser) {
        this.go(DB.currentUser.role === 'hr' ? 'admin' : 'cand');
      } else {
        this.go('login');
      }
      return;
    }
    if (portal === 'admin' && (!DB.currentUser || (DB.currentUser.role !== 'hr' && DB.currentUser.role !== 'admin'))) {
      Toast.show('Access denied. HR privileges required.', 'error');
      if (DB.currentUser) {
        this.go('cand');
      } else {
        this.go('login');
      }
      return;
    }

    document.querySelectorAll(`[data-portal="${portal}"]`).forEach(s => s.classList.add('hidden'));
    const el = document.getElementById(`${portal}-${section}`);
    if (el) el.classList.remove('hidden');
    this.innerPages[portal] = section;
    // Also update the hash to include the inner section
    history.replaceState(null, '', '#' + portal + '-' + section);
    if (portal === 'cand' && section === 'settings') {
      loadCandidateSettings();
    }
    if (portal === 'cand' && section === 'dash' && typeof renderDashboardTopJobs === 'function') {
      renderDashboardTopJobs();
    }
    if (portal === 'cand' && section === 'jobs' && typeof LiveJobsManager !== 'undefined') {
      LiveJobsManager.init();
      const hasActiveSearch = Boolean(
        LiveJobsManager.state.q ||
        LiveJobsManager.state.location ||
        (LiveJobsManager.state.work_mode && LiveJobsManager.state.work_mode !== 'any') ||
        (LiveJobsManager.state.min_salary && LiveJobsManager.state.min_salary !== '0') ||
        (LiveJobsManager.state.experience && LiveJobsManager.state.experience !== 'any')
      );
      if (hasActiveSearch) {
        LiveJobsManager.fetchJobs();
      } else if (_mlJobsCache && _mlJobsCache.length > 0) {
        DB.jobs = _mlJobsCache;
        UI.renderJobCards('cand-jobs-grid', DB.jobs, true);
        setEl('cand-jobs-count', `${DB.jobs.length} Matching Jobs Found`);
      } else {
        fetchJobsFromServer();
      }
    }
    if (portal === 'cand' && section === 'notif' && typeof CandidateNotifCenter !== 'undefined') {
      CandidateNotifCenter.fetchNotifications();
    }
  }
};

// ── Auth ─────────────────────────────────────────────────────
const Auth = {
  selectedRole: { login: 'candidate', register: 'candidate' },

  login(form) {
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const role     = this.selectedRole.login;

    if (!email || !password) { Toast.show('Please fill in all fields.', 'warning'); return; }
    
    fetch('/api/auth/login', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password, role})
    }).then(r=>r.json()).then(data => {
        if(!data.success) { Toast.show(data.message || 'Invalid credentials.', 'error'); return; }
        const user = data.user;
        user.avatar = user.name.slice(0,2).toUpperCase();
        DB.currentUser = user;
        this.setupPortal(user);
        if (user.role === 'admin') {
            Router.go('platform-admin');
        } else {
            Router.go(user.role === 'hr' ? 'admin' : 'cand');
        }
        Toast.show(`Welcome back, ${user.name.split(' ')[0]}! <i class="fa-solid fa-hand-sparkles" style="color: #34d399; margin-left: 4px;"></i>`, 'success');

        fetchJobsFromServer();
        fetchNotificationsFromServer(user.id);
        if (user.role === 'admin') {
            fetchPlatformAdminAnalytics();
        } else if (user.role === 'hr') {
            fetchCandidatesFromServer();
            fetchAdminStats();
            fetchTalentPool();
        } else {
            fetchCandidateStats(user.id);
            fetchCandidateProfile(user.id);
        }
    }).catch(e => Toast.show('Server error', 'error'));
  },

  register() {
    const fname = document.getElementById('reg-fname').value.trim();
    const lname = document.getElementById('reg-lname').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const pass  = document.getElementById('reg-pass').value;
    const cpass = document.getElementById('reg-cpass').value;
    const role  = this.selectedRole.register;

    if (!fname||!lname||!email||!pass||!cpass) { Toast.show('Please fill in all required fields.','warning'); return; }
    if (pass !== cpass) { Toast.show('Passwords do not match!','error'); return; }
    if (pass.length < 10) { Toast.show('Password must be at least 10 characters.','warning'); return; }

    // Show loading state
    const btn = document.querySelector('#page-register .btn-primary');
    if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...'; }

    fetch('/api/auth/register', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: `${fname} ${lname}`, email, password: pass, role})
    }).then(r=>r.json()).then(data => {
        if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-rocket"></i> Create Account'; }
        if(!data.success) { Toast.show(data.message, 'error'); return; }
        const user = data.user;
        user.avatar = user.name.slice(0,2).toUpperCase();
        DB.currentUser = user;
        this.setupPortal(user);
        if (user.role === 'admin') {
            Router.go('platform-admin');
        } else {
            Router.go(user.role === 'hr' ? 'admin' : 'cand');
        }
        Toast.show(`Account created! Welcome, ${fname}! <i class="fa-solid fa-wand-magic-sparkles"></i>`, 'success');

        fetchJobsFromServer();
        fetchNotificationsFromServer(user.id);
        if (user.role === 'admin') {
            fetchPlatformAdminAnalytics();
        } else if (user.role === 'hr') {
            fetchCandidatesFromServer();
            fetchAdminStats();
            fetchTalentPool();
        } else {
            fetchCandidateStats(user.id);
            fetchCandidateProfile(user.id);
        }
    }).catch(e => {
        if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-rocket"></i> Create Account'; }
        Toast.show('Server error — is the server running?', 'error');
    });
  },

  forgotPwd() {
    const email = document.getElementById('forgot-email').value.trim();
    if (!email) { Toast.show('Please enter your email address.', 'warning'); return; }

    const btn = document.querySelector('#page-forgot .btn-primary');
    const successEl = document.getElementById('forgot-success');
    const errorEl   = document.getElementById('forgot-error');
    const errorMsg  = document.getElementById('forgot-error-msg');

    // Reset state
    successEl.classList.add('hidden');
    errorEl.classList.add('hidden');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...'; }

    fetch('/api/auth/forgot_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    }).then(r => r.json()).then(data => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right:8px;"></i> Send Reset Link'; }
      if (data.success) {
        successEl.classList.remove('hidden');
        Toast.show('Reset link sent to ' + email, 'success');
        document.getElementById('forgot-email').value = '';
      } else {
        if (errorMsg) errorMsg.textContent = data.message || 'Email not found in our system.';
        errorEl.classList.remove('hidden');
        Toast.show(data.message || 'Email not found.', 'error');
      }
    }).catch(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right:8px;"></i> Send Reset Link'; }
      Toast.show('Server error — please try again.', 'error');
    });
  },

  resetPwd() {
    const token = document.getElementById('reset-token').value.trim();
    const pass  = document.getElementById('reset-pass').value;
    const cpass = document.getElementById('reset-cpass').value;
    const errEl = document.getElementById('reset-error');
    const errMsg = document.getElementById('reset-error-msg');
    const succEl = document.getElementById('reset-success');
    const btn = document.getElementById('reset-submit-btn');

    if (errEl) errEl.classList.add('hidden');
    if (succEl) succEl.classList.add('hidden');

    if (!token) { Toast.show('Reset token is required.', 'warning'); return; }
    if (!pass || !cpass) { Toast.show('Please fill in all password fields.', 'warning'); return; }
    if (pass !== cpass) { Toast.show('Passwords do not match!', 'error'); return; }
    if (pass.length < 10) { Toast.show('Password must be at least 10 characters.', 'warning'); return; }

    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...'; }

    fetch('/api/auth/reset_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: pass })
    })
    .then(r => r.json())
    .then(data => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Update Password'; }
      if (data.success) {
        if (succEl) succEl.classList.remove('hidden');
        Toast.show('Password reset successful! 🔒', 'success');
        setTimeout(() => Router.go('login'), 1500);
      } else {
        if (errMsg) errMsg.textContent = data.message || 'Invalid or expired reset token.';
        if (errEl) errEl.classList.remove('hidden');
        Toast.show(data.message || 'Failed to reset password.', 'error');
      }
    })
    .catch(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Update Password'; }
      Toast.show('Server error — please try again.', 'error');
    });
  },

  verifyEmail() {
    const token = document.getElementById('verify-token').value.trim();
    const errEl = document.getElementById('verify-error');
    const errMsg = document.getElementById('verify-error-msg');
    const succEl = document.getElementById('verify-success');
    const btn = document.getElementById('verify-submit-btn');

    if (errEl) errEl.classList.add('hidden');
    if (succEl) succEl.classList.add('hidden');

    if (!token) { Toast.show('Verification token is required.', 'warning'); return; }

    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...'; }

    fetch('/api/auth/verify_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    })
    .then(r => r.json())
    .then(data => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check"></i> Verify Email'; }
      if (data.success) {
        if (succEl) succEl.classList.remove('hidden');
        Toast.show('Email verified successfully! ✓', 'success');
        setTimeout(() => Router.go('login'), 1500);
      } else {
        if (errMsg) errMsg.textContent = data.message || 'Invalid or expired verification token.';
        if (errEl) errEl.classList.remove('hidden');
        Toast.show(data.message || 'Verification failed.', 'error');
      }
    })
    .catch(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check"></i> Verify Email'; }
      Toast.show('Server error — please try again.', 'error');
    });
  },

  resendVerification() {
    const email = document.getElementById('verify-resend-email').value.trim();
    if (!email) { Toast.show('Please enter your registered email.', 'warning'); return; }

    fetch('/api/auth/resend_verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        Toast.show('Verification token generated! Check email.', 'success');
        if (data.dev_verification_token) {
          const tEl = document.getElementById('verify-token');
          if (tEl) tEl.value = data.dev_verification_token;
        }
      } else {
        Toast.show(data.message || 'Failed to resend token.', 'error');
      }
    })
    .catch(() => Toast.show('Server error.', 'error'));
  },

  logout() {
    fetch('/api/auth/logout', { method: 'POST' }).then(() => {
      _mlJobsCache = null;
      _mlJobsCacheKey = '';
      DB.currentUser = null;
      Router.go('landing');
      Toast.show('Logged out successfully! <i class="fa-solid fa-right-from-bracket" style="color: #34d399; margin-left: 4px;"></i>', 'success');
      setTimeout(() => window.location.reload(), 1000);
    });
  },

  setupPortal(user) {
    const avatar = user.avatar || user.name.slice(0,2).toUpperCase();
    const isHR   = user.role === 'hr';

    // --- Sidebar + topbar names/avatars ---
    document.querySelectorAll('.cand-name').forEach(el => el.textContent = user.name);
    document.querySelectorAll('.cand-avatar').forEach(el => el.textContent = avatar);
    document.querySelectorAll('.cand-role').forEach(el => el.textContent = isHR ? 'HR Admin' : 'Candidate');
    document.querySelectorAll('.admin-name').forEach(el => el.textContent = user.name);
    document.querySelectorAll('.admin-avatar').forEach(el => el.textContent = avatar);
    document.querySelectorAll('.pa-admin-name').forEach(el => el.textContent = user.name);
    document.querySelectorAll('.pa-admin-avatar').forEach(el => el.textContent = avatar);

    // --- Populate candidate profile form with REAL user data ---
    const setVal = (id, v) => { const el = document.getElementById(id); if(el) el.value = v || ''; };
    setVal('cand-profile-name',  user.name ? user.name.split(' ')[0] : '');
    setVal('cand-profile-lname', user.name ? (user.name.split(' ')[1] || '') : '');
    setVal('cand-profile-email', user.email || '');
    setVal('cand-profile-phone', user.phone || '');
    setVal('cand-profile-loc', user.location || '');
    setVal('cand-profile-link', user.linkedin || '');
    setVal('cand-profile-git', user.github || '');
    setVal('cand-profile-sum', user.summary || '');
    setVal('cand-profile-edu', user.education || '');

    if (!isHR) {
      loadResumeHistory();
    }

    // --- ML Insights card (real data from DB) ---
    const clusterLabel  = user.cluster_label || 'Unclustered';
    const isOutlier     = user.is_outlier === 1 || user.is_outlier === true;
    const atsScore      = user.ats_score || 0;

    // Cluster label
    const clEl = document.getElementById('profile-cluster-label');
    if (clEl) clEl.textContent = clusterLabel;

    // Cluster badge in header
    const clBadge = document.getElementById('profile-cluster-badge');
    if (clBadge) { clBadge.textContent = clusterLabel; clBadge.style.display = ''; }

    // Outlier status
    const outlierEl   = document.getElementById('profile-outlier-status');
    const outlierIcon = document.getElementById('profile-outlier-icon');
    const outlierBadge = document.getElementById('profile-outlier-badge');
    if (outlierEl) {
      if (isOutlier) {
        outlierEl.textContent = '⚠ Suspicious Flag Active';
        outlierEl.style.color = '#dc2626';
        if (outlierIcon) { outlierIcon.textContent = '⚠️'; outlierIcon.style.background = 'rgba(220,38,38,.12)'; }
        if (outlierBadge) outlierBadge.style.display = '';
      } else {
        outlierEl.textContent = '✓ Normal Profile';
        outlierEl.style.color = '#16a34a';
      }
    }

    // Profile Strength: based on fields filled in
    const filledFields = [user.phone, user.location, user.linkedin, user.github, user.summary, user.education, user.skills].filter(Boolean).length;
    const strengthPct  = Math.round((filledFields / 7) * 100);
    const strengthEl   = document.getElementById('profile-strength-label');
    if (strengthEl) {
      const label = strengthPct >= 80 ? '🟢 Strong' : strengthPct >= 50 ? '🟡 Medium' : '🔴 Needs Work';
      strengthEl.textContent = `${label} (${strengthPct}%)`;
      strengthEl.style.color = strengthPct >= 80 ? '#16a34a' : strengthPct >= 50 ? '#d97706' : '#dc2626';
    }

    setVal('admin-profile-name', user.name || '');
    setVal('admin-profile-email', user.email || '');
    setVal('admin-profile-phone', user.phone || '');
    setVal('admin-profile-loc', user.location || '');

    // --- Candidate welcome banner with real name ---
    const banner = document.getElementById('cand-welcome-name');
    if(banner) banner.textContent = user.name.split(' ')[0];

    // --- New user: show upload CTA, hide stats until resume uploaded ---
    const hasResume = user.ats_score && user.ats_score > 0;
    const newUserBanner = document.getElementById('new-user-banner');
    const resumePrompt  = document.getElementById('resume-upload-prompt');
    if(newUserBanner) newUserBanner.classList.toggle('hidden', hasResume);
    if(resumePrompt)  resumePrompt.classList.toggle('hidden', hasResume);

    // --- Init inner pages based on user role ---
    if (user.role === 'admin') {
      Router.inner('platform-admin', 'overview');
    } else if (user.role === 'hr') {
      Router.inner('admin', 'dash');
    } else {
      Router.inner('cand', 'dash');
    }
  },

  setRole(portal, role, el) {
    this.selectedRole[portal] = role;
    el.closest('.role-picker').querySelectorAll('.role-option').forEach(o => o.classList.remove('active'));
    el.classList.add('active');
    
    if (portal === 'login') {
      const emailInput = document.getElementById('login-email');
      if (emailInput) {
        emailInput.value = role === 'hr' ? 'priya@demo.com' : 'hetsony143@gmail.com';
      }
    }
  },

  checkSession() {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(data => {
        if (data.success && data.user) {
          const user = data.user;
          user.avatar = user.name.slice(0,2).toUpperCase();
          DB.currentUser = user;
          this.setupPortal(user);

          // ── Restore the page from URL hash on refresh ──
          const hash = window.location.hash.replace('#', '');
          const portalPage = user.role === 'admin' ? 'platform-admin' : (user.role === 'hr' ? 'admin' : 'cand');

          if (hash === 'cand-pipeline') {
            // Block candidate-facing pipeline hash and redirect to candidate dashboard
            Router.go('cand');
            Router.inner('cand', 'dash');
          } else if (hash && (hash === portalPage || hash.startsWith(portalPage + '-'))) {
            Router.go(portalPage);
            const prefix = portalPage + '-';
            if (hash.startsWith(prefix)) {
              const section = hash.substring(prefix.length);
              const sectionEl = document.getElementById(`${portalPage}-${section}`);
              if (sectionEl) {
                Router.inner(portalPage, section);
                if (portalPage === 'platform-admin' && section === 'pipeline') {
                  loadMLPipelineStatus();
                }
              }
            }
          } else {
            Router.go(portalPage);
          }

          fetchJobsFromServer();
          fetchNotificationsFromServer(user.id);
          if (user.role === 'admin') {
              fetchPlatformAdminAnalytics();
          } else if (user.role === 'hr') {
              fetchCandidatesFromServer();
              fetchAdminStats();
              fetchTalentPool();
          } else {
              fetchCandidateStats(user.id);
              fetchCandidateProfile(user.id);
              loadResumeHistory();
          }
        } else {
          // Unauthenticated user — navigate to hash page if public, otherwise default to landing page
          const hashWithParams = window.location.hash.replace('#', '');
          const hash = hashWithParams.split('?')[0];
          const queryParams = new URLSearchParams(hashWithParams.includes('?') ? hashWithParams.split('?')[1] : window.location.search);
          const tokenParam = queryParams.get('token');
          const publicPages = ['landing', 'login', 'register', 'forgot', 'reset', 'verify', 'about', 'blog', 'careers', 'product', 'contact', 'legal'];
          if (publicPages.includes(hash)) {
            Router.go(hash);
            if (hash === 'reset' && tokenParam) {
              const rEl = document.getElementById('reset-token');
              if (rEl) rEl.value = tokenParam;
            } else if (hash === 'verify' && tokenParam) {
              const vEl = document.getElementById('verify-token');
              if (vEl) vEl.value = tokenParam;
            }
          } else {
            Router.go('landing');
          }
        }
      })
      .catch(e => {
        console.error('Session check failed', e);
        const hashWithParams = window.location.hash.replace('#', '');
        const hash = hashWithParams.split('?')[0];
        const publicPages = ['landing', 'login', 'register', 'forgot', 'reset', 'verify', 'about', 'blog', 'careers', 'product', 'contact', 'legal'];
        if (publicPages.includes(hash)) {
          Router.go(hash);
        } else {
          Router.go('landing');
        }
      });
  }
};

// Check session on page load
document.addEventListener('DOMContentLoaded', () => {
  Auth.checkSession();
});

// ── Toast ─────────────────────────────────────────────────────
const Toast = {
  _recent: {},
  show(msg, type='info', duration=5000) {
    if (!msg) return;
    const cleanKey = `${type}:${String(msg).replace(/<[^>]+>/g, '').trim()}`;
    const now = Date.now();
    // Deduplicate identical toasts within a 5-second sliding window
    if (this._recent[cleanKey] && (now - this._recent[cleanKey] < 5000)) {
      return;
    }
    this._recent[cleanKey] = now;

    const icons = { success:'fa-check-circle', error:'fa-times-circle', warning:'fa-exclamation-triangle', info:'fa-info-circle' };
    const c = document.getElementById('toast-container');
    if (!c) return;

    // Check if duplicate toast is already active in the DOM
    const isAlreadyInDom = Array.from(c.querySelectorAll('.toast span')).some(s => s.innerHTML === msg);
    if (isAlreadyInDom) return;

    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<i class="fas ${icons[type] || 'fa-info-circle'}"></i><span>${msg}</span><span class="toast-close" onclick="this.parentElement.remove()">✕</span>`;
    c.appendChild(t);
    setTimeout(() => { if (t.parentElement) t.style.animation = 'slideInRight .3s ease reverse'; }, Math.max(100, duration - 400));
    setTimeout(() => { if (t.parentElement) t.remove(); }, duration);
  }
};

// ── Sidebar ───────────────────────────────────────────────────
const Sidebar = {
  open(portal) {
    document.getElementById(`sb-${portal}`).classList.add('open');
    document.getElementById(`mob-overlay-${portal}`).classList.add('show');
  },
  close(portal) {
    document.getElementById(`sb-${portal}`).classList.remove('open');
    document.getElementById(`mob-overlay-${portal}`).classList.remove('show');
  },
  setActive(el) {
    el.closest('.sb-nav').querySelectorAll('.sb-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');
  }
};

// ── Modal ─────────────────────────────────────────────────────
const Modal = {
  open(id) { document.getElementById(id).classList.add('show'); },
  close(id) { document.getElementById(id).classList.remove('show'); },
  closeAll() { document.querySelectorAll('.modal-backdrop.show').forEach(m => m.classList.remove('show')); }
};

// ── Tabs ──────────────────────────────────────────────────────
function switchTab(el, group) {
  document.querySelectorAll(`[data-tabgroup="${group}"]`).forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}

// ── Candidate Status Update ───────────────────────────────────
function updateCandidateStatus(id, status) {
  fetch('/api/admin/update_status', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({app_id: id, status: status})
  }).then(r=>r.json()).then(data => {
      if(data.success) {
          const candidate = DB.candidates.find(c => c.id === parseInt(id));
          if (candidate) {
            candidate.status = status;
            UI.renderCandidatesTable();
            Toast.show(`${candidate.name} status updated to ${status}.`, 'success');
            // Refresh tab counts live
            setEl('tab-count-all',         DB.candidates.length);
            setEl('tab-count-shortlisted', DB.candidates.filter(c=>c.status==='Shortlisted').length);
            setEl('tab-count-reviewing',   DB.candidates.filter(c=>c.status==='Reviewing'||c.status==='Pending').length);
            setEl('tab-count-rejected',    DB.candidates.filter(c=>c.status==='Rejected').length);
          }
      }
  });
}

// ── UI Renderers ──────────────────────────────────────────────
const UI = {
  renderJobCards(containerId, jobs, isCandidateView = true, page = 0) {
    const c = document.getElementById(containerId);
    if (!c) return;

    const PAGE_SIZE = 12;
    const start   = page * PAGE_SIZE;
    const slice   = jobs.slice(start, start + PAGE_SIZE);
    const hasMore = start + PAGE_SIZE < jobs.length;

    if (page === 0) c.innerHTML = '';

    const temp = document.createElement('div');
    temp.innerHTML = slice.map(j => {
      registerKnownJob(j);
      const key    = (j.company || '').toLowerCase().trim();
      const domain = COMPANY_DOMAINS[key]
        || Object.entries(COMPANY_DOMAINS).find(([k]) => key.includes(k))?.[1];
      const abbr   = (j.company || '??').substring(0, 2).toUpperCase();
      const color  = j.color    || '#e0f2fe';
      const tcolor = j.textColor || '#1e40af';
      const extUrl = (j.external_apply_url || j.apply_url || '').trim();
      const isExt = Boolean(j.is_external || j.source === 'adzuna' || extUrl);
      const safeId = String(j.id).replace(/'/g, "\\'");
      const encodedUrl = encodeURIComponent(extUrl);

      // Google Favicon — fast, reliable, no Clearbit delay
      const logoHTML = domain
        ? `<img
            src="https://www.google.com/s2/favicons?domain=${domain}&sz=128"
            loading="eager"
            alt="${abbr}"
            width="40" height="40"
            style="object-fit:contain;border-radius:6px;display:block;"
           >`
        : `<div style="width:44px;height:44px;border-radius:8px;background:${color};color:${tcolor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;font-family:'Syne',sans-serif;">${abbr}</div>`;

      return `
      <div class="job-card ${j.match >= 85 ? 'featured' : ''}">
        <div class="job-card-badge" style="display:flex;gap:6px;align-items:center;">
          ${(j.is_external || j.source === 'adzuna')
            ? '<span class="badge badge-success" style="background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;font-size:11px;font-weight:600;"><i class="fas fa-bolt" style="font-size:10px;margin-right:3px;"></i> Live</span>'
            : '<span class="badge badge-secondary" style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;font-size:11px;font-weight:600;"><i class="fas fa-database" style="font-size:10px;margin-right:3px;"></i> Saved</span>'
          }
          ${j.match >= 85 ? '<span class="badge badge-teal">⭐ Top Match</span>' : ''}
        </div>
        <div class="company-row">
          <div class="company-logo" style="background:#fff;">${logoHTML}</div>
          <div>
            <div class="job-title">${j.title}</div>
            <div class="company-name">${j.company}</div>
          </div>
        </div>
        <div class="job-metas">
          <div class="job-meta"><i class="fas fa-map-marker-alt"></i> ${j.location || 'Remote'}</div>
          <div class="job-meta"><i class="fas fa-clock"></i> ${j.type || 'Full-time'}</div>
          <div class="job-meta"><i class="fas fa-rupee-sign"></i> ${j.salary || 'Competitive'}</div>
          <div class="job-meta"><i class="fas fa-calendar-alt"></i> ${j.posted_date ? new Date(j.posted_date).toLocaleDateString() : 'Recent'}</div>
        </div>
        <div class="job-skills" style="margin-bottom: 8px;">
          <div style="font-size: 11px; color: var(--text-3); margin-bottom: 4px;">Matching Skills:</div>
          ${(j.matching_skills || j.skills).slice(0,5).map(s => `<span class="job-skill-tag" style="background:#dcfce7;color:#166534;border:1px solid #bbf7d0">${s}</span>`).join('')}
        </div>
        <div style="font-size: 12px; color: var(--text-2); margin-bottom: 12px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
          ${j.description || ''}
        </div>
        ${isCandidateView ? `
        <div class="match-row">
          <div class="match-labels"><span>AI Match Score</span><strong>${j.match}%</strong></div>
          <div class="progress"><div class="progress-bar" style="width:${j.match}%;background:linear-gradient(90deg,#00c9a7,#1260cc)"></div></div>
        </div>
        ${isExt ? (
          extUrl ? `
          <button class="btn btn-primary btn-full mt-2 btn-apply-external"
            data-job-id="${escapeHTML(String(safeId))}"
            data-is-external="true"
            data-apply-url="${encodedUrl}"
            data-job-title="${escapeHTML(j.title || '')}"
            data-job-company="${escapeHTML(j.company || '')}"
            data-match-score="${j.match || j.match_score || 0}"
            onclick="applyJob('${escapeHTML(String(safeId))}', true, '${encodedUrl}', this)">
            Apply on External Site <i class="fas fa-external-link-alt" style="font-size:11px;margin-left:6px"></i>
          </button>
          ` : `
          <button class="btn btn-secondary btn-full mt-2" disabled style="opacity:0.6;cursor:not-allowed;">External application link unavailable</button>
          `
        ) : `
        <button class="btn btn-primary btn-full mt-2"
          data-job-id="${escapeHTML(String(safeId))}"
          data-is-external="false"
          onclick="applyJob('${escapeHTML(String(safeId))}', false, '', this)">
          Apply Now
        </button>
        `}
        ` : `
        <div style="display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)">
          <button class="btn btn-navy" style="flex:1;font-size:13px" onclick="viewJobRankings(${j.id})">View Rankings</button>
          <button class="btn btn-outline btn-sm" onclick="editJob(${j.id})"><i class="fas fa-edit"></i></button>
          <button class="btn btn-outline btn-sm" onclick="deleteJob(${j.id})"><i class="fas fa-trash"></i></button>
        </div>
        <div style="margin-top:10px;font-size:12px;color:var(--text-3)"><i class="fas fa-users"></i> ${j.applicants} applicants · <span class="badge ${j.status==='Active'?'badge-success':'badge-warning'}" style="font-size:11px">${j.status}</span></div>
        `}
      </div>
    `}).join('');

    // Move children as direct grid elements (DocumentFragment preserves CSS grid)
    const frag = document.createDocumentFragment();
    while (temp.firstChild) frag.appendChild(temp.firstChild);
    c.appendChild(frag);

    // Load-More button
    const oldBtn = document.getElementById(`${containerId}-load-more`);
    if (oldBtn) oldBtn.remove();
    if (hasMore) {
      const btn = document.createElement('button');
      btn.id = `${containerId}-load-more`;
      btn.className = 'btn btn-outline';
      btn.style.cssText = 'width:100%;margin-top:20px;padding:14px;font-size:14px;';
      btn.innerHTML = `<i class="fas fa-chevron-down"></i> Load More (${jobs.length - start - PAGE_SIZE} remaining)`;
      btn.onclick = () => { btn.remove(); this.renderJobCards(containerId, jobs, isCandidateView, page + 1); };
      c.parentNode.insertBefore(btn, c.nextSibling);
    }
  },


  renderCandidatesTable(filter='All') {
    const tbody = document.getElementById('candidates-tbody');
    if (!tbody) return;
    let data = DB.candidates;
    if (filter === 'Flagged')  data = data.filter(c => c.outlier_flag);
    else if (filter !== 'All') data = data.filter(c => c.status === filter);

    tbody.innerHTML = data.map((c,i) => `
      <tr style="${c.outlier_flag ? 'background:rgba(220,38,38,0.04);border-left:3px solid #dc2626' : ''}">
        <td>${this.rankBadge(i+1)}</td>
        <td>
          <div style="display:flex;align-items:center;gap:10px">
            <div class="avatar avatar-sm" style="background:${this.avatarColor(c.name)};color:#fff">${c.name.slice(0,2).toUpperCase()}</div>
            <div>
              <div class="fw-600">${c.name}</div>
              <div class="text-xs text-muted">${c.email}</div>
              ${c.outlier_flag ? `<span title="${c.outlier_reason}" style="display:inline-flex;align-items:center;gap:3px;margin-top:3px;background:#fee2e2;color:#dc2626;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;border:1px solid #fca5a5">⚠️ SUSPICIOUS</span>` : ''}
              <span style="display:inline-block;margin-top:3px;background:#eff6ff;color:#2563eb;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600">${c.cluster_label}</span>
            </div>
          </div>
        </td>
        <td><span class="text-sm">${c.degree}</span></td>
        <td>${c.job}</td>
        <td>
          <div style="display:flex;gap:4px;flex-wrap:wrap;max-width:220px">
            ${c.skills.slice(0, 4).map(s=>`<span class="badge badge-primary" style="font-size:11px">${s}</span>`).join('')}
            ${c.skills.length > 4 ? `<span class="badge badge-gray" style="font-size:11px">+${c.skills.length - 4} more</span>` : ''}
          </div>
        </td>
        <td><span class="badge ${this.atsBadge(c.ats)}">${c.ats}/100</span></td>
        <td><strong style="color:${c.match>=80?'#16a34a':c.match>=60?'#d97706':'#dc2626'}">${c.match}%</strong></td>
        <td>${this.statusBadge(c.status)}</td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm btn-primary" onclick="viewCandidate(${c.id})">View</button>
            <select class="form-control" style="padding:5px 8px;font-size:12px;height:auto;width:auto" onchange="updateCandidateStatus(${c.id},this.value)">
              <option ${c.status==='Reviewing'?'selected':''}>Reviewing</option>
              <option ${c.status==='Shortlisted'?'selected':''}>Shortlisted</option>
              <option ${c.status==='Pending'?'selected':''}>Pending</option>
              <option ${c.status==='Rejected'?'selected':''}>Rejected</option>
            </select>
          </div>
        </td>
      </tr>
    `).join('') || `<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-3)">No candidates found</td></tr>`;
  },

  renderRankingsTable(jobFilter = 'All', searchQuery = '') {
    const tbody = document.getElementById('rankings-tbody');
    if (!tbody) return;

    // Populate job filter options dynamically if needed
    const jobSelect = document.getElementById('rankings-filter-job');
    if (jobSelect && jobSelect.options.length <= 1 && Array.isArray(DB.jobs) && DB.jobs.length > 0) {
      const distinctJobTitles = Array.from(new Set(DB.jobs.map(j => j.title).filter(Boolean)));
      distinctJobTitles.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        jobSelect.appendChild(opt);
      });
    }

    if (!Array.isArray(DB.candidates) || DB.candidates.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-inbox" style="font-size:24px;margin-bottom:8px;display:block;opacity:0.4"></i>No applicant candidates found</td></tr>`;
      return;
    }

    // Filter by Job role
    let filtered = [...DB.candidates];
    if (jobFilter && jobFilter !== 'All') {
      filtered = filtered.filter(c => (c.job || '').toLowerCase().trim() === jobFilter.toLowerCase().trim());
    }

    // Filter by Search Query
    if (searchQuery && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(c => 
        (c.name || '').toLowerCase().includes(q) || 
        (c.job || '').toLowerCase().includes(q) || 
        (c.email || '').toLowerCase().includes(q)
      );
    }

    // Deduplicate candidate per job application
    const seen = new Set();
    filtered = filtered.filter(c => {
      const key = `${c.user_id || c.id}_${c.job}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Calculate true Composite AI Score (ATS 40% + Skill Match 30% + Cosine Similarity 30%)
    filtered.forEach(c => {
      const ats = Number(c.ats) || 0;
      const match = Number(c.match) || 0;
      const simPercent = typeof c.sim === 'number' ? c.sim * 100 : match;
      c.compositeAIScore = Math.round((ats * 0.4) + (match * 0.3) + (simPercent * 0.3));
    });

    // Sort strictly descending by Composite AI Score
    filtered.sort((a, b) => b.compositeAIScore - a.compositeAIScore);

    const subEl = document.getElementById('admin-rankings-subtitle');
    if (subEl) {
      subEl.textContent = jobFilter === 'All' 
        ? `All Roles (${filtered.length} candidates) · Ranked by AI Composite Score` 
        : `${jobFilter} (${filtered.length} candidates) · Ranked by AI Composite Score`;
    }

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-search" style="font-size:24px;margin-bottom:8px;display:block;opacity:0.4"></i>No candidates match the selected filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map((c, i) => {
      const topBadgeClass = i === 0 ? 'class="top-rank-row"' : '';
      const isShortlisted = c.status === 'Shortlisted';
      const isRejected = c.status === 'Rejected';

      return `
        <tr ${topBadgeClass}>
          <td>${this.rankBadge(i + 1)}</td>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div class="avatar avatar-sm" style="background:${this.avatarColor(c.name)};color:#fff">${(c.name || '??').slice(0, 2).toUpperCase()}</div>
              <div>
                <div class="fw-600" style="cursor:pointer;color:var(--primary)" onclick="viewCandidate(${c.id})">${c.name}</div>
                <div style="font-size:11px;color:var(--text-3)">${c.email || ''}</div>
              </div>
            </div>
          </td>
          <td><span style="font-weight:600;color:var(--text-1)">${c.job}</span></td>
          <td><span class="badge ${this.atsBadge(c.ats)}">${c.ats}/100</span></td>
          <td><strong style="color:${c.match >= 80 ? '#16a34a' : c.match >= 60 ? '#d97706' : '#dc2626'}">${c.match}%</strong></td>
          <td>${c.exp || '0 yrs'}</td>
          <td>
            <div style="display:flex;align-items:center;gap:6px">
              <strong style="font-size:15px;font-family:'Syne',sans-serif;color:${c.compositeAIScore >= 75 ? '#16a34a' : c.compositeAIScore >= 50 ? '#d97706' : '#dc2626'}">${c.compositeAIScore}</strong>
              <div class="progress" style="width:36px;height:5px;background:var(--border)"><div class="progress-bar" style="width:${c.compositeAIScore}%;background:${c.compositeAIScore >= 75 ? '#16a34a' : c.compositeAIScore >= 50 ? '#d97706' : '#dc2626'}"></div></div>
            </div>
          </td>
          <td>${this.statusBadge(c.status)}</td>
          <td>
            <div style="display:flex;gap:6px;align-items:center">
              <button class="btn btn-sm ${isShortlisted ? 'btn-success' : 'btn-outline'}" style="font-size:11px;padding:4px 8px" onclick="updateCandidateStatus(${c.id}, 'Shortlisted');UI.renderRankingsTable(document.getElementById('rankings-filter-job')?.value || 'All')">
                ${isShortlisted ? '<i class="fas fa-check"></i> Shortlisted' : 'Shortlist'}
              </button>
              ${!isRejected ? `
                <button class="btn btn-sm btn-outline-danger" style="font-size:11px;padding:4px 6px" title="Reject candidate" onclick="updateCandidateStatus(${c.id}, 'Rejected');UI.renderRankingsTable(document.getElementById('rankings-filter-job')?.value || 'All')">
                  <i class="fas fa-times"></i>
                </button>
              ` : `
                <span class="badge badge-danger" style="font-size:10px">Rejected</span>
              `}
              <button class="btn btn-sm btn-primary" style="font-size:11px;padding:4px 8px" onclick="viewCandidate(${c.id})">Profile</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  renderNotifications(portal) {
    const c = document.getElementById(`${portal}-notif-list`);
    if (!c) return;
    
    if (!DB.notifications || DB.notifications.length === 0) {
      c.innerHTML = `<div style="padding:40px 20px;text-align:center;color:var(--text-3);font-size:14px;">
        <i class="fas fa-bell-slash" style="font-size:32px;opacity:0.3;margin-bottom:12px;display:block"></i>
        You're all caught up! No notifications yet.
      </div>`;
      return;
    }

    c.innerHTML = DB.notifications.map(n => `
      <div class="notif-item ${n.unread?'unread':''}">
        <div class="notif-icon" style="background:${n.iconBg}"><i class="fas ${n.icon}" style="color:${n.iconColor}"></i></div>
        <div class="notif-body">
          <div class="title">${n.title}</div>
          <div class="msg">${n.msg}</div>
          <div class="time">${n.time}</div>
        </div>
        ${n.unread ? '<div class="unread-dot"></div>' : ''}
      </div>
    `).join('');
  },

  rankBadge(n) {
    if(n===1) return `<div class="rank-num rank-gold">1</div>`;
    if(n===2) return `<div class="rank-num rank-silver">2</div>`;
    if(n===3) return `<div class="rank-num rank-bronze">3</div>`;
    return `<div class="rank-num rank-plain">${n}</div>`;
  },
  atsBadge(score) { return score>=80?'badge-success':score>=60?'badge-warning':'badge-danger'; },
  statusBadge(status) {
    const map = { Shortlisted:'badge-success', Reviewing:'badge-info', Pending:'badge-warning', Rejected:'badge-danger' };
    return `<span class="badge ${map[status]||'badge-gray'}">${status}</span>`;
  },
  avatarColor(name) {
    const colors = ['#1260cc','#7c3aed','#0891b2','#047857','#be185d','#b45309','#dc2626','#065f46'];
    let h = 0; for(let c of name) h = c.charCodeAt(0) + h*31;
    return colors[Math.abs(h) % colors.length];
  }
};

// ── Charts ────────────────────────────────────────────────────
const Charts = {
  instances: {},

  destroy(id) { if(this.instances[id]) { this.instances[id].destroy(); delete this.instances[id]; } },

  create(id, config) {
    this.destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    this.instances[id] = new Chart(ctx, config);
  },

  defaults: {
    plugins: { legend: { labels: { font:{ family:'DM Sans', size:12 }, padding:14 } } },
    scales: {
      y: { grid: { color:'#f0f4f9' }, ticks: { font:{ family:'DM Sans', size:12 } } },
      x: { grid: { display:false },   ticks: { font:{ family:'DM Sans', size:12 } } }
    }
  },

  initCandidateCharts(score) {
    // ATS score donut — real data driven
    const s = score || (DB.currentUser && DB.currentUser.ats_score) || 0;
    this.create('cand-ats-mini', {
      type: 'doughnut',
      data: {
        labels: ['Score', 'Remaining'],
        datasets: [{ data: [s, 100-s], backgroundColor: ['#1260cc','#e6edf7'], borderWidth: 0, cutout:'78%' }]
      },
      options: { responsive:true, plugins:{ legend:{display:false}, tooltip:{enabled:false} } }
    });
    // NOTE: Profile Views timeline chart is now rendered with REAL API data
    // inside fetchCandidateStats() — do NOT add it here to avoid overwriting real data.
  },


  initAdminCharts() {
    // Charts are now fully driven by fetchAdminStats() — no hardcoded data
  },

  initAdminMiniCharts() {
    // Driven by fetchAdminStats() real data
  },

  initAnalyticsCharts(portal) {
    // All analytics charts are driven by fetchAdminStats() / fetchCandidateStats() real data
    // They will be populated when the API response arrives — no hardcoded data
  }
};

// ── Actions ───────────────────────────────────────────────────
function applyJob(id, isExternal = false, directUrl = '', btnElement = null) {
  if (!DB.currentUser) return Toast.show('Please login first', 'warning');

  const btn = btnElement || (typeof event !== 'undefined' && event && event.currentTarget ? event.currentTarget : null);

  // 1. Resolve directUrl from argument or button dataset
  let resolvedDirectUrl = (directUrl || (btn && btn.dataset && btn.dataset.applyUrl) || '').trim();
  if (resolvedDirectUrl) {
    try {
      resolvedDirectUrl = decodeURIComponent(resolvedDirectUrl).trim();
    } catch (e) {
      // already plain text
    }
  }

  // 2. Multi-tiered job resolution
  let job = _allKnownJobsMap.get(String(id));
  if (!job && Array.isArray(_mlJobsCache)) {
    job = _mlJobsCache.find(j => String(j.id) === String(id) || (j.raw_id && String(j.raw_id) === String(id)) || (j.source_job_id && String(j.source_job_id) === String(id)));
  }
  if (!job && typeof LiveJobsManager !== 'undefined' && Array.isArray(LiveJobsManager.lastResults)) {
    job = LiveJobsManager.lastResults.find(j => String(j.id) === String(id) || (j.raw_id && String(j.raw_id) === String(id)) || (j.source_job_id && String(j.source_job_id) === String(id)));
  }
  if (!job && Array.isArray(DB.jobs)) {
    job = DB.jobs.find(j => String(j.id) === String(id) || (j.raw_id && String(j.raw_id) === String(id)) || (j.source_job_id && String(j.source_job_id) === String(id)));
  }

  // 3. Resolve external URL: directUrl takes precedence, then job object
  const extUrl = (resolvedDirectUrl || (job && (job.external_apply_url || job.apply_url)) || '').trim();
  const external = Boolean(isExternal || resolvedDirectUrl || (job && (job.is_external || job.source === 'adzuna')));

  if (external) {
    if (!extUrl) {
      return Toast.show('External application link unavailable.', 'warning');
    }

    // Client-side protocol & scheme validation
    const lowerUrl = extUrl.toLowerCase();
    if (!lowerUrl.startsWith('http://') && !lowerUrl.startsWith('https://')) {
      return Toast.show('Invalid external URL protocol.', 'error');
    }
    if (lowerUrl.includes('javascript:') || lowerUrl.includes('data:') || lowerUrl.includes('file:') || lowerUrl.includes('vbscript:')) {
      return Toast.show('Disallowed URL scheme.', 'error');
    }

    const jobTitle = (job && job.title) || (btn && btn.dataset && btn.dataset.jobTitle) || 'Job';
    const jobCompany = (job && job.company) || (btn && btn.dataset && btn.dataset.jobCompany) || '';
    const matchScore = (job && (job.match || job.match_score)) || (btn && btn.dataset && Number(btn.dataset.matchScore)) || 0;

    fetch('/api/apply', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        job_id: id,
        is_external: true,
        external_apply_url: extUrl,
        apply_url: extUrl,
        title: jobTitle,
        company: jobCompany,
        match_score: matchScore
      })
    })
    .then(r => r.json())
    .then(data => {
      const redirectTarget = data.redirect_url || data.external_apply_url || extUrl;
      if (data.success && redirectTarget) {
        Toast.show(`Redirecting to external application for ${escapeHTML(jobTitle)}... ↗`, 'info');
        const win = window.open(redirectTarget, '_blank', 'noopener,noreferrer');
        if (!win) {
          window.location.href = redirectTarget;
        }
      } else {
        Toast.show(data.message || 'Unable to open external application.', 'warning');
      }
    })
    .catch(err => {
      console.error(err);
      Toast.show('Network error processing external application.', 'error');
    });
    return;
  }

  // Internal application flow
  fetch('/api/apply', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      job_id: id,
      is_external: false,
      match_score: job ? (job.match || job.match_score || 0) : 0
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      Toast.show(`Application submitted for ${escapeHTML(job ? job.title : 'Job')} at ${escapeHTML(job ? job.company : '')}! 🚀`, 'success');
      if (job) job.applicants = (job.applicants || 0) + 1;
    } else {
      Toast.show(data.message || 'Failed to submit application.', 'warning');
    }
  })
  .catch(err => {
    console.error(err);
    Toast.show('Network error submitting application.', 'error');
  });
}

function editJob(id) {
  const job = DB.jobs.find(j => j.id === id);
  if (!job) return;
  document.getElementById('edit-job-title').value    = job.title;
  document.getElementById('edit-job-company').value  = job.company;
  document.getElementById('edit-job-location').value = job.location;
  document.getElementById('edit-job-type').value     = job.type;
  document.getElementById('edit-job-salary').value   = job.salary;
  document.getElementById('edit-job-skills').value   = job.skills.join(', ');
  document.getElementById('edit-job-id').value       = id;
  Modal.open('edit-job-modal');
}

function saveEditJob() {
  const id      = parseInt(document.getElementById('edit-job-id').value);
  const title   = document.getElementById('edit-job-title').value.trim();
  const company = document.getElementById('edit-job-company').value.trim();
  const location= document.getElementById('edit-job-location').value.trim();
  const type    = document.getElementById('edit-job-type').value;
  const salary  = document.getElementById('edit-job-salary').value.trim();
  const skills  = document.getElementById('edit-job-skills').value.trim();
  
  if (!title||!company) { Toast.show('Title and company are required.','warning'); return; }
  
  fetch(`/api/admin/jobs/${id}`, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title, company, location, type, salary, skills, description: ''})
  }).then(r => r.json()).then(data => {
    if (data.success) {
      // Update local store
      const job = DB.jobs.find(j => j.id === id);
      if (job) {
        job.title = title; job.company = company; job.location = location;
        job.type = type; job.salary = salary;
        job.skills = skills.split(',').map(s => s.trim()).filter(Boolean);
      }
      Modal.close('edit-job-modal');
      UI.renderJobCards('admin-jobs-grid', DB.jobs, false);
      Toast.show('Job updated successfully!', 'success');
    } else {
      Toast.show('Failed to update job.', 'error');
    }
  }).catch(() => Toast.show('Server error.', 'error'));
}

function deleteJob(id) {
  if (!confirm('Are you sure you want to delete this job?')) return;
  fetch(`/api/admin/delete_job/${id}`, { method: 'DELETE' }).then(r=>r.json()).then(res => {
    if(res.success) {
      DB.jobs = DB.jobs.filter(j => j.id !== id);
      UI.renderJobCards('admin-jobs-grid', DB.jobs, false);
      Toast.show('Job deleted.', 'info');
    }
  });
}

function postJob() {
  const title    = document.getElementById('new-job-title').value.trim();
  const company  = document.getElementById('new-job-company').value.trim();
  const location = document.getElementById('new-job-location').value.trim();
  const type     = document.getElementById('new-job-type').value;
  const salary   = document.getElementById('new-job-salary').value.trim();
  const skills   = document.getElementById('new-job-skills').value.trim();
  const desc     = document.getElementById('new-job-desc').value.trim();

  if (!title||!company||!location||!salary) { Toast.show('Please fill in all required fields.','warning'); return; }

  fetch('/api/admin/jobs', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({title, company, location, type, salary, skills, description: desc})
  }).then(r=>r.json()).then(data => {
      Modal.close('post-job-modal');
      // Reset form
      ['new-job-title','new-job-company','new-job-location','new-job-salary','new-job-skills','new-job-desc'].forEach(id=>{
        const el = document.getElementById(id); if(el) el.value='';
      });
      Toast.show(`"${title}" posted successfully! <i class="fa-solid fa-wand-magic-sparkles"></i>`, 'success');
      fetchJobsFromServer(); // Refresh live jobs
  });
}

function viewCandidate(id) {
  const c = DB.candidates.find(x => x.id === id);
  if (!c) return;
  
  // Avatar initials
  const avatarEl = document.getElementById('modal-cand-avatar');
  if (avatarEl) {
    avatarEl.textContent = c.name.slice(0,2).toUpperCase();
    avatarEl.style.background = UI.avatarColor(c.name);
  }
  
  document.getElementById('modal-cand-name').textContent    = c.name;
  document.getElementById('modal-cand-email').textContent   = c.email;

  const phoneEl = document.getElementById('modal-cand-phone');
  if (phoneEl) phoneEl.textContent = c.phone || 'Not provided';

  const locEl = document.getElementById('modal-cand-loc');
  if (locEl) locEl.textContent = c.location || 'Not provided';

  const linksEl = document.getElementById('modal-cand-links');
  if (linksEl) {
    const links = [];
    if (c.linkedin) links.push(`<a href="${escapeHTML(c.linkedin)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">LinkedIn</a>`);
    if (c.github) links.push(`<a href="${escapeHTML(c.github)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">GitHub</a>`);
    linksEl.innerHTML = links.length ? links.join(' · ') : 'None';
  }

  document.getElementById('modal-cand-degree').textContent  = c.degree || 'Not detected';
  document.getElementById('modal-cand-job').textContent     = c.job;
  document.getElementById('modal-cand-exp').textContent     = c.exp || 'Not detected';
  document.getElementById('modal-cand-ats').textContent     = c.ats + '/100';
  document.getElementById('modal-cand-match').textContent   = c.match + '%';
  document.getElementById('modal-cand-status').innerHTML    = UI.statusBadge(c.status);
  document.getElementById('modal-cand-skills').innerHTML    = c.skills.length
    ? c.skills.map(s=>`<span class="skill-tag skill-neutral">${escapeHTML(s)}</span>`).join('')
    : '<span class="text-muted text-sm">No skills extracted yet</span>';

  const resNameEl = document.getElementById('modal-cand-resume-name');
  if (resNameEl) resNameEl.textContent = c.resume_name || 'None attached';

  // Wire Download and Preview buttons
  const dlBtn = document.getElementById('modal-btn-download');
  const prevBtn = document.getElementById('modal-btn-preview');
  if (c.resume_id) {
    if (dlBtn) {
      dlBtn.style.display = 'inline-flex';
      dlBtn.href = `/api/resume/download/${c.resume_id}`;
    }
    if (prevBtn) {
      const isPdf = (c.resume_mime === 'application/pdf' || (c.resume_name && c.resume_name.toLowerCase().endsWith('.pdf')));
      if (isPdf) {
        prevBtn.style.display = 'inline-flex';
        prevBtn.href = `/api/resume/download/${c.resume_id}?preview=1`;
      } else {
        prevBtn.style.display = 'none';
      }
    }
  } else {
    if (dlBtn) dlBtn.style.display = 'none';
    if (prevBtn) prevBtn.style.display = 'none';
  }

  // Wire action buttons to real API
  const btnShortlist = document.getElementById('modal-btn-shortlist');
  const btnReject    = document.getElementById('modal-btn-reject');
  if (btnShortlist) {
    btnShortlist.style.display = 'inline-flex';
    btnShortlist.onclick = () => {
      updateCandidateStatus(id, 'Shortlisted');
      document.getElementById('modal-cand-status').innerHTML = UI.statusBadge('Shortlisted');
      Modal.close('view-cand-modal');
    };
  }
  if (btnReject) {
    btnReject.style.display = 'inline-flex';
    btnReject.onclick = () => {
      updateCandidateStatus(id, 'Rejected');
      document.getElementById('modal-cand-status').innerHTML = UI.statusBadge('Rejected');
      Modal.close('view-cand-modal');
    };
  }
  
  Modal.open('view-cand-modal');
}


function viewJobRankings(jobId) {
  const job = DB.jobs.find(j => j.id === jobId);
  Sidebar.setActive(document.querySelector('#sb-admin .sb-item[data-section="rankings"]'));
  Router.inner('admin','rankings');
  UI.renderRankingsTable(jobId);
  if (job) Toast.show(`Showing rankings for: ${job.title}`, 'info');
}

function exportCSV() {
  const headers = ['Rank','Name','Email','Degree','Job','ATS','Match','Experience','Status'];
  const rows = DB.candidates.sort((a,b)=>b.ats-a.ats).map((c,i)=>[i+1,c.name,c.email,c.degree,c.job,c.ats+'%',c.match+'%',c.exp,c.status]);
  const csv = [headers,...rows].map(r=>r.join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download='candidates.csv'; a.click();
  URL.revokeObjectURL(url);
  Toast.show('CSV exported successfully!','success');
}

function searchCandidates(val) {
  const q = val.toLowerCase();
  const filtered = DB.candidates.filter(c => c.name.toLowerCase().includes(q) || c.job.toLowerCase().includes(q) || c.email.toLowerCase().includes(q));
  const tbody = document.getElementById('candidates-tbody');
  if (!tbody) return;
  if (!q) { UI.renderCandidatesTable(); return; }
  // Temporarily swap
  const saved = DB.candidates;
  const bak = DB.candidates;
  DB.candidates = filtered;
  UI.renderCandidatesTable();
  DB.candidates = bak;
}

function filterJobs(portal) {
  if (portal === 'cand') {
    if (typeof LiveJobsManager !== 'undefined') LiveJobsManager.fetchJobs();
    return;
  }
  const loc  = document.getElementById(`${portal}-filter-loc`).value;
  const type = document.getElementById(`${portal}-filter-type`).value;
  let jobs = [...DB.jobs];
  if (loc && loc !== 'All') jobs = jobs.filter(j => j.location.includes(loc) || (loc==='Remote'&&j.type==='Contract'));
  if (type && type !== 'All') jobs = jobs.filter(j => j.type === type);
  UI.renderJobCards('admin-jobs-grid', jobs, false);
}

function resetFilters(portal) {
  if (portal === 'cand') {
    if (typeof LiveJobsManager !== 'undefined') LiveJobsManager.resetAll();
    return;
  }
  document.getElementById(`${portal}-filter-loc`).value  = 'All';
  document.getElementById(`${portal}-filter-type`).value = 'All';
  UI.renderJobCards('admin-jobs-grid', DB.jobs, false);
}

// ── Highlight Search Term ──────────────────────────────────────
function highlightText(text, query) {
  if (!text) return '';
  const escaped = escapeHTML(text);
  if (!query || typeof query !== 'string' || !query.trim()) return escaped;
  const terms = query.trim().split(/\s+/).filter(t => t.length > 1);
  if (terms.length === 0) return escaped;
  const pattern = new RegExp(`(${terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return escaped.replace(pattern, '<mark style="background:#fef08a;color:#713f12;padding:0 2px;border-radius:2px;">$1</mark>');
}

// ── Live Jobs Manager (Reactive State & Search Engine) ───────────
const LiveJobsManager = {
  state: {
    q: '',
    location: '',
    work_mode: 'any',
    min_salary: '0',
    experience: 'any',
    sort: 'relevance',
    page: 1,
    per_page: 10
  },
  abortController: null,
  debounceTimer: null,
  totalResults: 0,
  totalPages: 1,
  hasInitialized: false,

  init() {
    this.restoreFromUrl();
    this.syncInputsToState();
    this.hasInitialized = true;
  },

  restoreFromUrl() {
    try {
      const hash = window.location.hash || '';
      const qIndex = hash.indexOf('?');
      if (qIndex !== -1) {
        const params = new URLSearchParams(hash.substring(qIndex + 1));
        if (params.has('q')) this.state.q = params.get('q');
        if (params.has('location')) this.state.location = params.get('location');
        if (params.has('work_mode')) this.state.work_mode = params.get('work_mode');
        if (params.has('min_salary')) this.state.min_salary = params.get('min_salary');
        if (params.has('experience')) this.state.experience = params.get('experience');
        if (params.has('sort')) this.state.sort = params.get('sort');
        if (params.has('page')) this.state.page = parseInt(params.get('page'), 10) || 1;
      }
    } catch (e) {
      console.warn("Error restoring search state from URL:", e);
    }
  },

  syncUrl() {
    try {
      const params = new URLSearchParams();
      if (this.state.q) params.set('q', this.state.q);
      if (this.state.location) params.set('location', this.state.location);
      if (this.state.work_mode && this.state.work_mode !== 'any') params.set('work_mode', this.state.work_mode);
      if (this.state.min_salary && this.state.min_salary !== '0') params.set('min_salary', this.state.min_salary);
      if (this.state.experience && this.state.experience !== 'any') params.set('experience', this.state.experience);
      if (this.state.sort && this.state.sort !== 'relevance') params.set('sort', this.state.sort);
      if (this.state.page > 1) params.set('page', String(this.state.page));

      const baseHash = '#cand-jobs';
      const queryString = params.toString();
      const newHash = queryString ? `${baseHash}?${queryString}` : baseHash;
      history.replaceState(null, '', newHash);
    } catch (e) {
      console.warn("Error updating URL query params:", e);
    }
  },

  syncInputsToState() {
    const kwInput = document.getElementById('live-search-keyword');
    if (kwInput) kwInput.value = this.state.q || '';

    const topInput = document.getElementById('topbar-search-cand');
    if (topInput) topInput.value = this.state.q || '';

    const locInput = document.getElementById('live-search-location');
    if (locInput) locInput.value = this.state.location || '';

    const remoteSel = document.getElementById('live-filter-remote');
    if (remoteSel) remoteSel.value = this.state.work_mode || 'any';

    const salSel = document.getElementById('live-filter-salary');
    if (salSel) salSel.value = this.state.min_salary || '0';

    const expSel = document.getElementById('live-filter-exp');
    if (expSel) expSel.value = this.state.experience || 'any';

    const sortSel = document.getElementById('live-filter-sort');
    if (sortSel) sortSel.value = this.state.sort || 'relevance';

    this.renderActiveChips();
  },

  renderActiveChips() {
    const container = document.getElementById('live-filter-chips');
    if (!container) return;

    const chips = [];
    if (this.state.q) {
      chips.push({ key: 'q', label: `Keyword: "${this.state.q}"` });
    }
    if (this.state.location) {
      chips.push({ key: 'location', label: `Location: "${this.state.location}"` });
    }
    if (this.state.work_mode && this.state.work_mode !== 'any') {
      const modeLabels = { remote: 'Remote Only', onsite: 'On-site', hybrid: 'Hybrid' };
      chips.push({ key: 'work_mode', label: modeLabels[this.state.work_mode] || this.state.work_mode });
    }
    if (this.state.min_salary && this.state.min_salary !== '0') {
      const salVal = parseInt(this.state.min_salary, 10);
      chips.push({ key: 'min_salary', label: `Salary: ₹${salVal/100000}L+` });
    }
    if (this.state.experience && this.state.experience !== 'any') {
      const expLabels = { '0-1': 'Fresher / 0-1 yr', '1-3': '1-3 yrs', '3-5': '3-5 yrs', '5-8': '5-8 yrs', '8+': '8+ yrs' };
      chips.push({ key: 'experience', label: `Exp: ${expLabels[this.state.experience] || this.state.experience}` });
    }

    if (chips.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = chips.map(c => `
      <span class="badge" style="background:var(--primary-light, #e0f2fe);color:var(--primary, #0369a1);border:1px solid rgba(3,105,161,0.25);font-size:12px;padding:4px 10px;border-radius:20px;display:inline-flex;align-items:center;gap:6px;font-weight:600;">
        ${escapeHTML(c.label)}
        <i class="fas fa-times" style="cursor:pointer;opacity:0.75;" onclick="removeLiveFilterChip('${c.key}')" title="Remove filter"></i>
      </span>
    `).join('') + `
      <span style="font-size:12px;color:var(--text-3);cursor:pointer;text-decoration:underline;margin-left:4px;" onclick="resetLiveFilters()">Clear all</span>
    `;
  },

  removeChip(key) {
    if (key === 'q') this.state.q = '';
    else if (key === 'location') this.state.location = '';
    else if (key === 'work_mode') this.state.work_mode = 'any';
    else if (key === 'min_salary') this.state.min_salary = '0';
    else if (key === 'experience') this.state.experience = 'any';
    
    this.state.page = 1;
    this.syncInputsToState();
    this.fetchJobs();
  },

  handleInput(field, val, debounce = true) {
    this.state[field] = val;
    this.state.page = 1;
    if (field === 'q') {
      const topInput = document.getElementById('topbar-search-cand');
      if (topInput && topInput.value !== val) topInput.value = val;
      const kwInput = document.getElementById('live-search-keyword');
      if (kwInput && kwInput.value !== val) kwInput.value = val;
    }
    this.renderActiveChips();

    if (debounce) {
      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.fetchJobs();
      }, 400);
    } else {
      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.fetchJobs();
    }
  },

  handleDropdown(field, val) {
    this.state[field] = val;
    this.state.page = 1;
    this.renderActiveChips();
    this.fetchJobs();
  },

  resetAll() {
    this.state = {
      q: '',
      location: '',
      work_mode: 'any',
      min_salary: '0',
      experience: 'any',
      sort: 'relevance',
      page: 1,
      per_page: 10
    };
    this.syncInputsToState();
    this.fetchJobs();
  },

  changePage(delta) {
    const newPage = this.state.page + delta;
    if (newPage >= 1 && newPage <= this.totalPages) {
      this.state.page = newPage;
      this.fetchJobs();
      const el = document.getElementById('cand-jobs');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  setLoading(isLoading) {
    const skeleton = document.getElementById('live-jobs-skeleton');
    const grid = document.getElementById('cand-jobs-grid');
    const empty = document.getElementById('live-jobs-empty');
    const error = document.getElementById('live-jobs-error');
    const searchBtn = document.getElementById('btn-live-search');

    if (isLoading) {
      if (skeleton) skeleton.classList.remove('hidden');
      if (grid) grid.style.display = 'none';
      if (empty) empty.classList.add('hidden');
      if (error) error.classList.add('hidden');
      if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
      }
    } else {
      if (skeleton) skeleton.classList.add('hidden');
      if (grid) grid.style.display = 'flex';
      if (searchBtn) {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search"></i> Search';
      }
    }
  },

  fetchJobs() {
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    this.syncUrl();
    this.setLoading(true);

    const params = new URLSearchParams();
    if (this.state.q) params.set('q', this.state.q);
    if (this.state.location) params.set('location', this.state.location);
    if (this.state.work_mode && this.state.work_mode !== 'any') params.set('work_mode', this.state.work_mode);
    if (this.state.min_salary && this.state.min_salary !== '0') params.set('min_salary', this.state.min_salary);
    if (this.state.experience && this.state.experience !== 'any') params.set('experience', this.state.experience);
    if (this.state.sort) params.set('sort', this.state.sort);
    params.set('page', String(this.state.page || 1));
    params.set('per_page', String(this.state.per_page || 10));

    fetch(`/api/jobs/search?${params.toString()}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: this.abortController.signal
    })
    .then(r => {
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}`);
      }
      return r.json();
    })
    .then(data => {
      this.setLoading(false);
      if (!data.success) {
        this.showError(data.message || 'Failed to search jobs');
        return;
      }
      this.renderResults(data);
    })
    .catch(err => {
      if (err.name === 'AbortError') return;
      this.setLoading(false);
      this.showError('Unable to connect to search service. Please retry.');
    });
  },

  showError(msg) {
    const errorEl = document.getElementById('live-jobs-error');
    const msgEl = document.getElementById('live-jobs-error-msg');
    const grid = document.getElementById('cand-jobs-grid');
    const empty = document.getElementById('live-jobs-empty');
    const pagination = document.getElementById('live-jobs-pagination');

    if (grid) grid.style.display = 'none';
    if (empty) empty.classList.add('hidden');
    if (pagination) pagination.style.display = 'none';
    if (msgEl) msgEl.textContent = msg;
    if (errorEl) errorEl.classList.remove('hidden');
  },

  renderResults(data) {
    const grid = document.getElementById('cand-jobs-grid');
    const empty = document.getElementById('live-jobs-empty');
    const meta = document.getElementById('live-jobs-meta');
    const warnBanner = document.getElementById('live-jobs-warning-banner');
    const pagination = document.getElementById('live-jobs-pagination');
    const pageInfo = document.getElementById('live-jobs-page-info');
    const btnPrev = document.getElementById('btn-page-prev');
    const btnNext = document.getElementById('btn-page-next');

    this.totalResults = data.total || 0;
    this.totalPages = data.total_pages || 1;

    // Warnings
    if (warnBanner) {
      if (data.warnings && data.warnings.length > 0) {
        warnBanner.innerHTML = `<i class="fas fa-info-circle"></i> <span>${data.warnings.map(w => escapeHTML(w)).join(' · ')}</span>`;
        warnBanner.classList.remove('hidden');
      } else {
        warnBanner.classList.add('hidden');
      }
    }

    // Meta count
    if (meta) {
      meta.textContent = `${this.totalResults} jobs found`;
    }

    // Empty state
    if (!data.jobs || data.jobs.length === 0) {
      if (grid) grid.style.display = 'none';
      if (empty) empty.classList.remove('hidden');
      if (pagination) pagination.style.display = 'none';
      return;
    }

    if (empty) empty.classList.add('hidden');
    if (grid) grid.style.display = 'flex';

    // Save search results reference and register in global known jobs map
    this.lastResults = data.jobs || [];
    this.lastResults.forEach(j => {
      if (typeof registerKnownJob === 'function') registerKnownJob(j);
    });

    // Update DB.jobs for top recommendations & applyJob compatibility
    DB.jobs = data.jobs.map(j => {
      const extUrl = (j.external_apply_url || j.apply_url || '').trim();
      const isExternal = Boolean(j.is_external || j.source === 'adzuna' || extUrl);
      const mapped = {
        ...j,
        match: j.match_score,
        external_apply_url: extUrl || null,
        apply_url: extUrl,
        is_external: isExternal
      };
      if (typeof registerKnownJob === 'function') registerKnownJob(mapped);
      return mapped;
    });

    // Render cards
    grid.innerHTML = data.jobs.map((j, i) => {
      const key = (j.company || '').toLowerCase().trim();
      const domain = COMPANY_DOMAINS[key]
        || Object.entries(COMPANY_DOMAINS).find(([k]) => key.includes(k))?.[1];
      const abbr = (j.company || '??').substring(0, 2).toUpperCase();
      const color = JOB_COLORS[i % JOB_COLORS.length].color;
      const tcolor = JOB_COLORS[i % JOB_COLORS.length].textColor;
      const extUrl = (j.external_apply_url || j.apply_url || '').trim();
      const isExt = Boolean(j.is_external || j.source === 'adzuna' || (extUrl && !extUrl.startsWith('/')));
      const safeId = String(j.id).replace(/'/g, "\\'");
      const encodedUrl = encodeURIComponent(extUrl);

      const highlightedTitle = highlightText(j.title, this.state.q);
      const highlightedCompany = highlightText(j.company, this.state.q);

      const logoHTML = domain
        ? `<img src="https://www.google.com/s2/favicons?domain=${domain}&sz=128"
               loading="lazy" alt="${abbr}" width="40" height="40"
               style="object-fit:contain;border-radius:8px;padding:3px;background:#fff;border:1px solid rgba(0,0,0,0.08);display:block;"
               onerror="this.onerror=null;this.parentElement.innerHTML='<div style=\\\'width:40px;height:40px;border-radius:8px;background:${color};color:${tcolor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;font-family:Syne,sans-serif;\\\'>${abbr}</div>';">`
        : `<div style="width:40px;height:40px;border-radius:8px;background:${color};color:${tcolor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;font-family:'Syne',sans-serif;">${abbr}</div>`;

      const workModeBadge = j.work_mode === 'remote'
        ? '<span class="badge badge-teal" style="font-size:11px"><i class="fas fa-laptop-house"></i> Remote</span>'
        : (j.work_mode === 'hybrid'
          ? '<span class="badge badge-info" style="font-size:11px"><i class="fas fa-building-user"></i> Hybrid</span>'
          : '<span class="badge badge-gray" style="font-size:11px"><i class="fas fa-building"></i> On-site</span>');

      const expDisplay = j.experience_min !== null
        ? `${j.experience_min}${j.experience_max ? '-' + j.experience_max : '+'} yrs exp`
        : 'Exp not specified';

      return `
        <div class="job-card ${j.match_score >= 85 ? 'featured' : ''}" style="transition:box-shadow 0.2s ease, transform 0.2s ease;">
          <div class="job-card-badge" style="display:flex;gap:6px;align-items:center;">
            ${(j.source === 'adzuna' || isExt)
              ? '<span class="badge badge-success" style="background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;font-size:11px;font-weight:600;"><i class="fas fa-bolt" style="font-size:10px;margin-right:3px;"></i> Live</span>'
              : '<span class="badge badge-secondary" style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;font-size:11px;font-weight:600;"><i class="fas fa-database" style="font-size:10px;margin-right:3px;"></i> Saved</span>'
            }
            ${j.match_score >= 85 ? '<span class="badge badge-teal"><i class="fas fa-star" style="font-size:10px"></i> Top Match</span>' : ''}
          </div>
          <div class="company-row">
            <div class="company-logo" style="background:#fff;">${logoHTML}</div>
            <div style="flex:1;min-width:0;">
              <div class="job-title" style="font-size:17px;font-weight:700;color:var(--text);">${highlightedTitle}</div>
              <div class="company-name" style="font-size:13px;color:var(--text-2);margin-top:2px;">${highlightedCompany} · <span style="text-transform:capitalize;font-size:11.5px;color:var(--text-3);">${j.source === 'adzuna' ? 'Live External' : 'TalentSync Partner'}</span></div>
            </div>
          </div>
          <div class="job-metas" style="margin:10px 0;">
            <div class="job-meta"><i class="fas fa-map-marker-alt" style="color:var(--primary)"></i> ${escapeHTML(j.location || 'India')}</div>
            <div class="job-meta">${workModeBadge}</div>
            <div class="job-meta" style="color:#059669;font-weight:600;"><i class="fas fa-rupee-sign"></i> ${escapeHTML(j.salary_display)}</div>
            <div class="job-meta"><i class="fas fa-user-graduate"></i> ${escapeHTML(expDisplay)}</div>
            <div class="job-meta"><i class="fas fa-clock"></i> ${j.posted_at ? new Date(j.posted_at).toLocaleDateString() : 'Recent'}</div>
          </div>
          ${j.matched_skills && j.matched_skills.length > 0 ? `
          <div class="job-skills" style="margin-bottom:8px;">
            <div style="font-size:11px;color:var(--text-3);margin-bottom:4px;">Matched Skills:</div>
            ${j.matched_skills.slice(0, 6).map(s => `<span class="job-skill-tag" style="background:#dcfce7;color:#166534;border:1px solid #bbf7d0">${escapeHTML(s)}</span>`).join('')}
          </div>
          ` : (j.skills && j.skills.length > 0 ? `
          <div class="job-skills" style="margin-bottom:8px;">
            <div style="font-size:11px;color:var(--text-3);margin-bottom:4px;">Required Skills:</div>
            ${j.skills.slice(0, 6).map(s => `<span class="job-skill-tag">${escapeHTML(s)}</span>`).join('')}
          </div>
          ` : '')}
          <div style="font-size:12.5px;color:var(--text-2);margin-bottom:12px;line-height:1.45;">
            ${escapeHTML(j.description_snippet)}
          </div>
          <div class="match-row" style="margin-top:auto;padding-top:10px;border-top:1px solid var(--border);">
            <div class="match-labels">
              <span style="font-size:12px;color:var(--text-2)">AI Match Score</span>
              <strong style="color:var(--primary);font-size:14px">${j.match_score}%</strong>
            </div>
            <div class="progress" style="height:6px;border-radius:99px;background:rgba(0,0,0,0.06);overflow:hidden;">
              <div class="progress-bar" style="width:${Math.max(5, j.match_score)}%;height:100%;border-radius:99px;background:linear-gradient(90deg,#00c9a7,#1260cc);transition:width 0.4s ease;"></div>
            </div>
          </div>
          ${isExt ? (
            extUrl ? `
              <button class="btn btn-primary btn-full mt-2" 
                      data-job-id="${escapeHTML(String(j.id))}"
                      data-is-external="true"
                      data-apply-url="${encodedUrl}"
                      data-job-title="${escapeHTML(j.title || '')}"
                      data-job-company="${escapeHTML(j.company || '')}"
                      data-match-score="${j.match_score || 0}"
                      onclick="applyJob('${escapeHTML(String(safeId))}', true, '${encodedUrl}', this)" 
                      style="border-radius:8px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;">
                Apply on External Site <i class="fas fa-external-link-alt" style="font-size:11px;"></i>
              </button>
            ` : `
              <button class="btn btn-secondary btn-full mt-2" disabled style="border-radius:8px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;opacity:0.6;cursor:not-allowed;">
                External application link unavailable
              </button>
            `
          ) : `
            <button class="btn btn-primary btn-full mt-2" 
                    data-job-id="${escapeHTML(String(j.id))}"
                    data-is-external="false"
                    onclick="applyJob('${escapeHTML(String(safeId))}', false, '', this)" 
                    style="border-radius:8px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;">
              Apply Now
            </button>
          `}
        </div>
      `;
    }).join('');

    // Pagination display
    if (pagination && pageInfo) {
      if (this.totalPages > 1) {
        pagination.style.display = 'flex';
        pageInfo.textContent = `Page ${this.state.page} of ${this.totalPages}`;
        if (btnPrev) btnPrev.disabled = this.state.page <= 1;
        if (btnNext) btnNext.disabled = this.state.page >= this.totalPages;
      } else {
        pagination.style.display = 'none';
      }
    }
  }
};

// UI Action Triggers wired to index.html controls
function handleMainSearchInput(val) {
  LiveJobsManager.handleInput('q', val, true);
}

function handleLocationInput(val) {
  LiveJobsManager.handleInput('location', val, true);
}

function triggerSearch() {
  LiveJobsManager.handleInput('q', LiveJobsManager.state.q, false);
}

function handleDropdownFilterChange(field, val) {
  LiveJobsManager.handleDropdown(field, val);
}

function resetLiveFilters() {
  LiveJobsManager.resetAll();
}

function removeLiveFilterChip(key) {
  LiveJobsManager.removeChip(key);
}

function changeLiveJobsPage(delta) {
  LiveJobsManager.changePage(delta);
}

function handleHeaderSearchInput(val) {
  LiveJobsManager.state.q = val;
  const kwInput = document.getElementById('live-search-keyword');
  if (kwInput) kwInput.value = val;
  if (Router.current === 'cand' && Router.innerPages['cand'] === 'jobs') {
    LiveJobsManager.handleInput('q', val, true);
  }
}

function handleHeaderSearchEnter(val) {
  LiveJobsManager.state.q = val;
  const kwInput = document.getElementById('live-search-keyword');
  if (kwInput) kwInput.value = val;
  
  if (Router.current !== 'cand' || Router.innerPages['cand'] !== 'jobs') {
    Router.go('cand');
    Router.inner('cand', 'jobs');
    const jobsTab = document.querySelector('#sb-cand [data-section=jobs]');
    if (jobsTab) Sidebar.setActive(jobsTab);
  }
  LiveJobsManager.handleInput('q', val, false);
}

function saveProfile(portal) {
  if (!DB.currentUser) return;
  
  let name;
  if (portal === 'cand') {
    const fname = (document.getElementById('cand-profile-name')?.value || '').trim();
    const lname = (document.getElementById('cand-profile-lname')?.value || '').trim();
    name = lname ? `${fname} ${lname}` : fname;
  } else {
    name = (document.getElementById('admin-profile-name')?.value || '').trim();
  }
  
  const data = {
    name,
    email:     (document.getElementById(`${portal}-profile-email`)?.value || '').trim(),
    phone:     (document.getElementById(`${portal}-profile-phone`)?.value || '').trim(),
    location:  (document.getElementById(`${portal}-profile-loc`)?.value || '').trim(),
    linkedin:  (document.getElementById(`${portal}-profile-link`)?.value || '').trim(),
    github:    (document.getElementById(`${portal}-profile-git`)?.value || '').trim(),
    summary:   (document.getElementById(`${portal}-profile-sum`)?.value || '').trim(),
    education: (document.getElementById(`${portal}-profile-edu`)?.value || '').trim()
  };
  
  if (!data.name) { Toast.show('Name cannot be empty.','warning'); return; }
  
  fetch(`/api/users/${DB.currentUser.id}/profile`, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }).then(r=>r.json()).then(res => {
    if(res.success) {
      // Update local store and all UI elements
      Object.assign(DB.currentUser, data);
      DB.currentUser.avatar = data.name.slice(0,2).toUpperCase();
      Auth.setupPortal(DB.currentUser);
      // Also update analysis/profile display
      setEl('profile-name', data.name);
      setEl('profile-email', data.email);
      setEl('profile-phone', data.phone);
      setEl('profile-location', data.location);
      setEl('profile-linkedin', data.linkedin);
      setEl('profile-github', data.github);
      setEl('profile-summary', data.summary);
      setEl('profile-education', data.education);
      Toast.show('Profile saved successfully! ✓','success');
    } else { Toast.show('Failed to save profile.','error'); }
  }).catch(() => Toast.show('Server error.','error'));
}


function changePwd(portal) {
  const cur  = document.getElementById(`${portal}-cur-pwd`).value;
  const nw   = document.getElementById(`${portal}-new-pwd`).value;
  const conf = document.getElementById(`${portal}-conf-pwd`).value;
  if (!cur||!nw||!conf) { Toast.show('Please fill in all password fields.','warning'); return; }
  if (nw !== conf) { Toast.show('New passwords do not match!','error'); return; }
  if (nw.length < 10) { Toast.show('Password must be at least 10 characters.','warning'); return; }
  
  fetch('/api/auth/change_password', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ current_password: cur, new_password: nw })
  }).then(r => r.json()).then(data => {
    if (data.success) {
      Toast.show('Password changed successfully! 🔒', 'success');
      ['cur-pwd','new-pwd','conf-pwd'].forEach(s => { const el=document.getElementById(`${portal}-${s}`); if(el) el.value=''; });
    } else {
      Toast.show(data.message || 'Failed to change password.', 'error');
    }
  }).catch(() => Toast.show('Server error.', 'error'));
}

function saveSettings() {
  const settings = {
    newAlerts: document.getElementById('set-new-alerts')?.checked,
    emailShortlist: document.getElementById('set-email-shortlist')?.checked,
    weeklyReport: document.getElementById('set-weekly-report')?.checked,
    autoRank: document.getElementById('set-auto-rank')?.checked,
    strictAts: document.getElementById('set-strict-ats')?.checked,
    softSkills: document.getElementById('set-soft-skills')?.checked,
    tfa: document.getElementById('set-2fa')?.checked,
    darkMode: document.getElementById('set-dark-mode')?.checked
  };
  localStorage.setItem('hireai_settings', JSON.stringify(settings));
  Toast.show('Settings saved to device.', 'success');
}

function saveCandidateSettings(silent = false) {
  const settings = {
    email: document.getElementById('cand-set-email')?.checked ?? true,
    sms: document.getElementById('cand-set-sms')?.checked ?? false,
    jobAlerts: document.getElementById('cand-set-job-alerts')?.checked ?? true,
    appStatus: document.getElementById('cand-set-app-status')?.checked ?? true,
    digest: document.getElementById('cand-set-digest')?.checked ?? true,
    profileVis: document.getElementById('cand-set-profile-vis')?.checked ?? true,
    anonScreening: document.getElementById('cand-set-anon-screening')?.checked ?? false,
    recruiterMsg: document.getElementById('cand-set-recruiter-msg')?.checked ?? true,
    activeStatus: document.getElementById('cand-set-active-status')?.checked ?? true,
    tfa: document.getElementById('cand-set-2fa')?.checked ?? false,
    darkMode: document.getElementById('cand-set-dark-mode')?.checked ?? false,
    compactCards: document.getElementById('cand-set-compact-cards')?.checked ?? false,
    highContrast: document.getElementById('cand-set-high-contrast')?.checked ?? false,
    lang: document.getElementById('cand-set-lang')?.value || 'en',
    dateFmt: document.getElementById('cand-set-date-fmt')?.value || 'DD/MM/YYYY',
    currency: document.getElementById('cand-set-currency')?.value || 'INR',
    timezone: document.getElementById('cand-set-timezone')?.value || 'Asia/Kolkata'
  };
  localStorage.setItem('talentsync_cand_settings', JSON.stringify(settings));
  if (!silent) {
    Toast.show('Candidate settings saved successfully! ✓', 'success');
  }
}

function switchSettingTab(tab, el) {
  document.querySelectorAll('#admin-settings .settings-nav-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.set-tab-pane').forEach(p => p.classList.add('hidden'));
  const target = document.getElementById('set-tab-' + tab);
  if (target) target.classList.remove('hidden');
}

function switchCandSettingTab(tab, el) {
  document.querySelectorAll('#cand-settings .settings-nav-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('#cand-settings .cand-set-tab-pane').forEach(p => p.classList.add('hidden'));
  const target = document.getElementById('cand-set-tab-' + tab);
  if (target) target.classList.remove('hidden');
}

function exportCandidateProfileData() {
  const profileData = {
    user: DB.currentUser || { name: 'Candidate User', email: 'candidate@talentsync.ai' },
    profile: DB.currentProfile || {},
    appliedJobs: DB.applications || [],
    settings: JSON.parse(localStorage.getItem('talentsync_cand_settings') || '{}'),
    exportTimestamp: new Date().toISOString()
  };
  const blob = new Blob([JSON.stringify(profileData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `talentsync_candidate_profile_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  Toast.show('Candidate profile data exported successfully! 📁', 'success');
}

function toggleDarkMode(isDark) {
  if (isDark) {
    document.body.classList.add('dark-mode');
  } else {
    document.body.classList.remove('dark-mode');
  }
  const elAdmin = document.getElementById('set-dark-mode');
  if (elAdmin) elAdmin.checked = isDark;
  const elCand = document.getElementById('cand-set-dark-mode');
  if (elCand) elCand.checked = isDark;

  saveSettings();
  saveCandidateSettings(true);
}

function loadCandidateSettings() {
  const saved = localStorage.getItem('talentsync_cand_settings');
  if (saved) {
    try {
      const s = JSON.parse(saved);
      if (s.email !== undefined) { const el = document.getElementById('cand-set-email'); if(el) el.checked = s.email; }
      if (s.sms !== undefined) { const el = document.getElementById('cand-set-sms'); if(el) el.checked = s.sms; }
      if (s.jobAlerts !== undefined) { const el = document.getElementById('cand-set-job-alerts'); if(el) el.checked = s.jobAlerts; }
      if (s.appStatus !== undefined) { const el = document.getElementById('cand-set-app-status'); if(el) el.checked = s.appStatus; }
      if (s.digest !== undefined) { const el = document.getElementById('cand-set-digest'); if(el) el.checked = s.digest; }
      if (s.profileVis !== undefined) { const el = document.getElementById('cand-set-profile-vis'); if(el) el.checked = s.profileVis; }
      if (s.anonScreening !== undefined) { const el = document.getElementById('cand-set-anon-screening'); if(el) el.checked = s.anonScreening; }
      if (s.recruiterMsg !== undefined) { const el = document.getElementById('cand-set-recruiter-msg'); if(el) el.checked = s.recruiterMsg; }
      if (s.activeStatus !== undefined) { const el = document.getElementById('cand-set-active-status'); if(el) el.checked = s.activeStatus; }
      if (s.tfa !== undefined) { const el = document.getElementById('cand-set-2fa'); if(el) el.checked = s.tfa; }
      if (s.darkMode !== undefined) {
        const el = document.getElementById('cand-set-dark-mode');
        if(el) el.checked = s.darkMode;
        if(s.darkMode) document.body.classList.add('dark-mode');
      }
      if (s.compactCards !== undefined) { const el = document.getElementById('cand-set-compact-cards'); if(el) el.checked = s.compactCards; }
      if (s.highContrast !== undefined) { const el = document.getElementById('cand-set-high-contrast'); if(el) el.checked = s.highContrast; }
      if (s.lang) { const el = document.getElementById('cand-set-lang'); if(el) el.value = s.lang; }
      if (s.dateFmt) { const el = document.getElementById('cand-set-date-fmt'); if(el) el.value = s.dateFmt; }
      if (s.currency) { const el = document.getElementById('cand-set-currency'); if(el) el.value = s.currency; }
      if (s.timezone) { const el = document.getElementById('cand-set-timezone'); if(el) el.value = s.timezone; }
    } catch(e){}
  }
}

function loadSettings() {
  const saved = localStorage.getItem('hireai_settings');
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      if (parsed.newAlerts !== undefined) { const el = document.getElementById('set-new-alerts'); if(el) el.checked = parsed.newAlerts; }
      if (parsed.emailShortlist !== undefined) { const el = document.getElementById('set-email-shortlist'); if(el) el.checked = parsed.emailShortlist; }
      if (parsed.weeklyReport !== undefined) { const el = document.getElementById('set-weekly-report'); if(el) el.checked = parsed.weeklyReport; }
      if (parsed.autoRank !== undefined) { const el = document.getElementById('set-auto-rank'); if(el) el.checked = parsed.autoRank; }
      if (parsed.strictAts !== undefined) { const el = document.getElementById('set-strict-ats'); if(el) el.checked = parsed.strictAts; }
      if (parsed.softSkills !== undefined) { const el = document.getElementById('set-soft-skills'); if(el) el.checked = parsed.softSkills; }
      if (parsed.tfa !== undefined) { const el = document.getElementById('set-2fa'); if(el) el.checked = parsed.tfa; }
      if (parsed.darkMode !== undefined) { 
        const el = document.getElementById('set-dark-mode'); 
        if(el) el.checked = parsed.darkMode; 
        if(parsed.darkMode) document.body.classList.add('dark-mode'); 
      }
    } catch(e){}
  }
  loadCandidateSettings();
}
// Load on startup
document.addEventListener('DOMContentLoaded', loadSettings);

function markAllRead(portal) {
  if (!DB.currentUser) return;
  fetch(`/api/notifications/${DB.currentUser.id}/read`, { method: 'POST' })
  .then(r=>r.json()).then(res => {
    if(res.success) {
      DB.notifications.forEach(n => n.unread = false);
      UI.renderNotifications(portal); // will fetch fresh list
      updateSidebarBadges();
      Toast.show('All notifications marked as read.','info');
    }
  });
}

function viewMatchedJobs() {
  Router.inner('cand','jobs');
  Sidebar.setActive(document.querySelector('#sb-cand [data-section=jobs]'));
  
  // Real logic: The ML API already returns the Top 10 matched jobs. Show them all.
  const matchedJobs = DB.jobs;
  UI.renderJobCards('cand-jobs-grid', matchedJobs, true);
  
  Toast.show(`Showing top ${matchedJobs.length} AI-matched jobs for your profile!`, 'info');
}

function triggerReupload() {
  Router.inner('cand','upload');
  Sidebar.setActive(document.querySelector('#sb-cand [data-section=upload]'));
  // Trigger file selection natively after a short delay
  setTimeout(() => {
    document.getElementById('resume-file-input').click();
  }, 50);
}

function resumeUpload(e) {
  const files = e.target.files;
  if (!files.length) return;
  const file = files[0];
  const allowed = ['application/pdf','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  if (!allowed.includes(file.type)) { Toast.show('Only PDF, DOC, DOCX files allowed.','error'); return; }
  if (file.size > 5*1024*1024) { Toast.show('File must be under 5MB.','error'); return; }

  const isWord = file.name.toLowerCase().endsWith('.docx') || file.name.toLowerCase().endsWith('.doc');
  const iconClass = isWord ? 'fas fa-file-word' : 'fas fa-file-pdf';
  const iconColor = isWord ? '#2563eb' : '#dc2626'; // blue for Word, red for PDF
  const iconBg = isWord ? '#dbeafe' : '#fee2e2';

  const list = document.getElementById('upload-list');
  const item = document.createElement('div');
  item.className = 'upload-item';
  item.innerHTML = `
    <div class="upload-item-icon" style="background:${iconBg}"><i class="${iconClass}" style="color:${iconColor}"></i></div>
    <div class="upload-item-body">
      <div class="upload-item-name">${file.name}</div>
      <div class="upload-item-meta">${(file.size/1024).toFixed(0)} KB · Uploading...</div>
      <div class="progress"><div class="progress-bar" id="up-prog" style="width:0%;background:#1260cc"></div></div>
    </div>
    <span class="badge badge-info">Uploading...</span>
  `;
  list.prepend(item);

  const formData = new FormData();
  formData.append('resume', file);
  if (DB.currentUser) formData.append('user_id', DB.currentUser.id);
  
  const bar = item.querySelector('#up-prog');
  const badge = item.querySelector('.badge');
  
  bar.style.width = '40%';
  Toast.show(`Uploading "${file.name}" to AI server...`,'info');

  fetch('/api/upload_resume', {
      method: 'POST',
      body: formData
  })
  .then(res => res.json())
  .then(data => {
      if (!data || !data.success) {
          const errMsg = (data && (data.message || data.error)) || 'Failed to parse resume.';
          bar.style.width = '100%';
          bar.style.background = '#dc2626';
          badge.className = 'badge badge-danger';
          badge.innerHTML = '<i class="fas fa-times"></i> Error';
          Toast.show(errMsg, 'error');
          return;
      }
      bar.style.width = '100%';
      bar.style.background='#16a34a';
      badge.className='badge badge-success';
      badge.innerHTML='<i class="fas fa-check"></i> Analyzed';
      const atsScore = (data.data && data.data.ats_score !== undefined) ? data.data.ats_score : 0;
      Toast.show(`Resume parsed! ATS Score: ${atsScore}/100 <i class="fa-solid fa-wand-magic-sparkles"></i>`, 'success');
      
      // Update current user's data in memory so the ML pipeline works everywhere
      if(DB.currentUser && data.data) {
          DB.currentUser.ats_score = atsScore;
          DB.currentUser.skills = (data.data.skills || []).join(',');
          fetchCandidateStats(DB.currentUser.id);
      }

      // Render Resume Intelligence immediately
      if (data.data && data.data.intel) {
          renderResumeIntelligence(data.data.intel, {
              original_name: file.name,
              ats_score: atsScore,
              id: data.resume_id
          });
      }

      // Reload resume history from server to update list with download/preview buttons
      loadResumeHistory();

      // Force-refresh ML job matches (invalidates cache since skills changed)
      _mlJobsCache = null;
      _mlJobsCacheKey = '';
      fetchJobsFromServer(true);
  })
  .catch(err => {
      bar.style.width = '100%';
      bar.style.background = '#dc2626';
      badge.className='badge badge-danger'; badge.innerHTML='<i class="fas fa-times"></i> Error';
      Toast.show('Error connecting to AI Server. Is it running?', 'error');
  });
}

function fetchJobs(skills) {
  fetch('/api/match_jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skills: skills })
  })
  .then(res => res.json())
  .then(data => {
      if(data.success && data.jobs.length > 0) {
          Toast.show(`AI found ${data.jobs.length} highly matched jobs!`, 'info');
          // Map backend jobs to frontend UI schema
          const mappedJobs = data.jobs.map(j => ({
              id: j.id,
              title: j.title,
              company: j.company,
              location: j.location || 'Remote/Office',
              type: j.contract_time || j.type || 'Full-time',
              salary: (j.salary_min && j.salary_max) ? `₹${j.salary_min} - ₹${j.salary_max}` : (j.salary || 'To be discussed'),
              skills: Array.isArray(j.skills) ? j.skills : (typeof j.skills === 'string' ? j.skills.split(',').map(s=>s.trim()) : skills.slice(0, 3)),
              matching_skills: j.matching_skills || [],
              applicants: 0,
              status: j.status || 'Active',
              match: typeof j.match_percentage === 'number' ? j.match_percentage : 50,
              apply_url: j.apply_url || '',
              is_external: Boolean(j.source === 'adzuna' && j.apply_url),
              color: '#eff6ff', textColor: '#1e40af',
              logo: (j.company || '??').substring(0, 2).toUpperCase()
          }));
          DB.jobs = mappedJobs;
          UI.renderJobCards('cand-jobs-grid', mappedJobs, true);
          if (typeof renderDashboardTopJobs === 'function') {
            renderDashboardTopJobs();
          }
      }
  })
  .catch(err => console.error(err));
}

function handleDrop(e, zone) {
  e.preventDefault();
  zone.classList.remove('dragover');
  const files = e.dataTransfer.files;
  if (files.length) {
    const fakeInput = { target: { files } };
    resumeUpload(fakeInput);
  }
}

// Topbar search
function topbarSearch(val, portal) {
  if (!val.trim()) return;
  if (portal === 'admin') searchCandidates(val);
  Toast.show(`Searching for "${val}"...`,'info');
}

// ── AI Rankings Filter & Export Handlers ────────────────────────
function filterRankingsByJob(jobTitle) {
  const q = document.getElementById('rankings-search')?.value || '';
  UI.renderRankingsTable(jobTitle, q);
}

function filterRankingsSearch(q) {
  const jobTitle = document.getElementById('rankings-filter-job')?.value || 'All';
  UI.renderRankingsTable(jobTitle, q);
}

function exportRankingsCSV() {
  const jobTitle = document.getElementById('rankings-filter-job')?.value || 'All';
  let list = [...(DB.candidates || [])];
  if (jobTitle !== 'All') {
    list = list.filter(c => (c.job || '').toLowerCase().trim() === jobTitle.toLowerCase().trim());
  }

  // Deduplicate
  const seen = new Set();
  list = list.filter(c => {
    const key = `${c.user_id || c.id}_${c.job}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  list.forEach(c => {
    const ats = Number(c.ats) || 0;
    const match = Number(c.match) || 0;
    const simPercent = typeof c.sim === 'number' ? c.sim * 100 : match;
    c.compositeAIScore = Math.round((ats * 0.4) + (match * 0.3) + (simPercent * 0.3));
  });

  list.sort((a, b) => b.compositeAIScore - a.compositeAIScore);

  let csv = 'Rank,Candidate Name,Email,Job Applied,ATS Score,Skill Match,Experience,AI Composite Score,Status\n';
  list.forEach((c, idx) => {
    const clean = (val) => {
      let s = String(val || '').replace(/"/g, '""');
      if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
      return `"${s}"`;
    };
    csv += `${idx + 1},${clean(c.name)},${clean(c.email)},${clean(c.job)},${c.ats},${c.match}%,${clean(c.exp)},${c.compositeAIScore},${clean(c.status)}\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `talentsync_ai_rankings_${jobTitle.replace(/\s+/g,'_').toLowerCase()}_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  Toast.show('AI Candidate Rankings exported to CSV! 📊', 'success');
}

// ── API Fetchers (World-Class Live Data) ────────────────────────────────
const JOB_COLORS = [
  {color:'#eff6ff',textColor:'#1e40af'},{color:'#f0fdf4',textColor:'#166534'},
  {color:'#fff7ed',textColor:'#9a3412'},{color:'#fdf2f8',textColor:'#86198f'},
  {color:'#f5f3ff',textColor:'#6d28d9'},{color:'#fff1f2',textColor:'#9f1239'},
  {color:'#ecfdf5',textColor:'#065f46'},{color:'#fffbeb',textColor:'#92400e'},
];

// ── ML Job Cache (avoids re-running expensive ML pipeline) ───
let _mlJobsCache = null;
let _mlJobsCacheKey = '';
let _isFetchingJobs = false;
let _fetchJobsPromise = null;

function fetchJobsFromServer(forceMLRefresh = false) {
  // 0. ANONYMOUS GUEST: Never call protected endpoints from landing/public view
  if (!DB.currentUser) {
    return Promise.resolve();
  }

  // 1. HR PORTAL: Fetch all jobs for the Admin view
  if (DB.currentUser.role === 'hr') {
    return fetch('/api/admin/jobs')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (!Array.isArray(data)) {
          console.warn("Expected array from /api/admin/jobs, got:", data);
          return;
        }
        const adminJobs = data.map((j, i) => {
          const jobSkills = j.skills ? (typeof j.skills === 'string' ? j.skills.split(',').map(s=>s.trim()) : j.skills) : [];
          return {
            id: j.id, title: j.title, company: j.company, location: j.location,
            type: j.type || 'Full-time', salary: j.salary,
            skills: jobSkills, description: j.description, status: j.status || 'Active',
            applicants: 0, match: 50,
            ...JOB_COLORS[i % JOB_COLORS.length],
            logo: (j.company||'??').substring(0,2).toUpperCase()
          };
        });
        DB.jobs = adminJobs;
        UI.renderJobCards('admin-jobs-grid', adminJobs, false);
        updateSidebarBadges();
      })
      .catch(err => {
        console.error("Error fetching admin jobs:", err);
      });
  }

  // 2. CANDIDATE PORTAL: Uses /api/match_jobs (never calls /api/admin/jobs)
  const userSkills = DB.currentUser.skills
    ? DB.currentUser.skills.split(',').map(s => s.trim()).filter(Boolean)
    : [];
  const userKey = (DB.currentUser && (DB.currentUser.id || DB.currentUser.email)) || 'anon';
  const skillsHash = userSkills.slice().map(s => s.toLowerCase().trim()).sort().join(',');
  const candExp = (DB.currentUser && DB.currentUser.experience || '').trim().toLowerCase();
  const candLoc = (DB.currentUser && DB.currentUser.location || '').trim().toLowerCase();
  const cacheKey = `${userKey}|${skillsHash}|${candExp}|${candLoc}`;

  // Use cached ML results unless explicitly forced or skills changed
  if (!forceMLRefresh && _mlJobsCache && _mlJobsCacheKey === cacheKey) {
    DB.jobs = _mlJobsCache;
    UI.renderJobCards('cand-jobs-grid', DB.jobs, true);
    setEl('cand-jobs-count', `${DB.jobs.length} Matching Jobs Found`);
    setEl('cand-stat-matches', DB.jobs.length);
    setEl('cand-analytics-matches', DB.jobs.length);
    updateSidebarBadges();
    if (typeof renderDashboardTopJobs === 'function') {
      renderDashboardTopJobs();
    }
    return Promise.resolve(DB.jobs);
  }

  // Single shared in-flight request — prevent duplicate concurrent calls & toasts
  if (_fetchJobsPromise && !forceMLRefresh) {
    return _fetchJobsPromise;
  }

  _isFetchingJobs = true;
  _fetchJobsPromise = fetch('/api/match_jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      skills: userSkills,
      experience: DB.currentUser.experience || '',
      location: DB.currentUser.location || ''
    })
  })
  .then(r => {
    if (!r.ok) {
      if (r.status === 401) {
        console.warn("Unauthenticated or expired session while fetching jobs (HTTP 401).");
        return null;
      }
      if (r.status === 403) {
        console.warn("Access forbidden for job matching (HTTP 403).");
        return null;
      }
      if (r.status === 429) {
        Toast.show("Rate limit exceeded. Please wait a moment.", "warning");
        return null;
      }
      if (r.status >= 500) {
        Toast.show("Server error loading jobs. Please retry.", "error");
        return null;
      }
      return null;
    }
    return r.json();
  })
  .then(data => {
    if (!data) return; // Handled non-200 HTTP status gracefully

    // 5. TRANSPARENCY: Display personalization summary under header
    const transEl = document.getElementById('cand-jobs-personalization-info');
    if (transEl) {
      if (data.personalization_summary) {
        transEl.textContent = data.personalization_summary;
        transEl.style.display = 'block';
      } else {
        transEl.style.display = 'none';
      }
    }

    // 3. NEW CANDIDATE / NO RESUME: Render friendly prompt instead of generic Developer matches
    if (data.needs_resume) {
      DB.jobs = [];
      _mlJobsCache = [];
      _mlJobsCacheKey = cacheKey;

      const grid = document.getElementById('cand-jobs-grid');
      if (grid) {
        let emptyHtml = `
          <div class="card" style="padding:40px 24px;text-align:center;background:var(--surface);border:1px dashed var(--primary);border-radius:14px;margin-bottom:20px;">
            <div style="width:52px;height:52px;border-radius:50%;background:rgba(37,99,235,0.1);display:inline-flex;align-items:center;justify-content:center;color:var(--primary);font-size:22px;margin-bottom:14px;">
              <i class="fas fa-file-upload"></i>
            </div>
            <div style="font-size:18px;font-weight:700;color:var(--text-1);margin-bottom:6px;">Upload your resume to get personalized job matches</div>
            <div style="font-size:13px;color:var(--text-3);max-width:460px;margin:0 auto 18px auto;line-height:1.5;">
              We haven't parsed your skills yet. Upload your resume so our AI can match you with the best live opportunities tailored to your career.
            </div>
            <button class="btn btn-primary" onclick="Router.inner('cand','upload')">
              <i class="fas fa-upload"></i> Upload Resume
            </button>
          </div>
        `;

        if (Array.isArray(data.popular_jobs) && data.popular_jobs.length > 0) {
          emptyHtml += `
            <div style="margin-top:16px;margin-bottom:12px;">
              <div style="font-size:14px;font-weight:700;color:var(--text-2);display:flex;align-items:center;gap:8px;">
                <i class="fas fa-fire" style="color:#f59e0b;"></i> Popular Openings <span class="badge badge-secondary" style="font-size:10px;font-weight:500;">Generic</span>
              </div>
            </div>
            <div id="cand-popular-jobs-subgrid" style="display:flex;flex-direction:column;gap:16px;"></div>
          `;
          grid.innerHTML = emptyHtml;
          const popMapped = data.popular_jobs.map((j, i) => ({
            id: j.id, title: j.title, company: j.company, location: j.location || 'Remote/Office',
            type: j.type || 'Full-time', salary: j.salary || 'Competitive',
            skills: typeof j.skills === 'string' ? j.skills.split(',').map(s=>s.trim()) : (j.skills || []),
            description: j.description || '', status: j.status || 'Active',
            match: 0, applicants: 0, ...JOB_COLORS[i % JOB_COLORS.length],
            logo: (j.company||'??').substring(0,2).toUpperCase()
          }));
          UI.renderJobCards('cand-popular-jobs-subgrid', popMapped, true);
        } else {
          grid.innerHTML = emptyHtml;
        }
      }

      setEl('cand-jobs-count', '0 Matching Jobs (Upload resume for live matches)');
      setEl('cand-stat-matches', 0);
      setEl('cand-analytics-matches', 0);
      updateSidebarBadges();
      if (typeof renderDashboardTopJobs === 'function') {
        renderDashboardTopJobs();
      }
      return DB.jobs;
    }

    if (!data.success || !Array.isArray(data.jobs)) {
      console.warn("Invalid jobs response shape from /api/match_jobs:", data);
      DB.jobs = [];
      UI.renderJobCards('cand-jobs-grid', [], true);
      setEl('cand-jobs-count', '0 Matching Jobs Found');
      setEl('cand-stat-matches', 0);
      setEl('cand-analytics-matches', 0);
      updateSidebarBadges();
      if (typeof renderDashboardTopJobs === 'function') {
        renderDashboardTopJobs();
      }
      return;
    }

    const sourceStatus = data.source_status || {};
    if (data.source === 'adzuna') {
      // Live jobs retrieved successfully
      const header = document.getElementById('cand-jobs-count');
      if (header) {
        header.innerHTML = `${data.jobs.length} Live Matches Found`;
      }
    } else if (sourceStatus.adzuna === 'failed') {
      // Only show warning toast if Adzuna truly failed, and at most ONCE per browser session
      const sessionKey = 'talentsync_adzuna_fallback_toast_shown';
      if (!sessionStorage.getItem(sessionKey)) {
        sessionStorage.setItem(sessionKey, '1');
        let msg = "Live jobs temporarily unavailable — showing saved jobs.";
        if (sourceStatus.reason === 'rate_limit') {
          msg = "Live job network busy — showing saved jobs.";
        } else if (sourceStatus.reason === 'auth' || sourceStatus.reason === 'config') {
          msg = "Live job network offline — showing saved jobs.";
        }
        Toast.show(msg, 'warning', 5000);
      }
      const header = document.getElementById('cand-jobs-count');
      if (header) {
        header.innerHTML = `${data.jobs.length} Saved Jobs <button onclick="fetchJobsFromServer(true)" class="btn btn-sm btn-outline" style="margin-left:10px"><i class="fas fa-sync"></i> Retry Live Jobs</button>`;
      }
    } else {
      // Local jobs shown because specific search query returned 0 results
      const header = document.getElementById('cand-jobs-count');
      if (header) {
        header.innerHTML = `${data.jobs.length} Matching Jobs`;
      }
    }

    DB.jobs = data.jobs.map((j, i) => ({
      id: j.id,
      title: j.title,
      company: j.company,
      location: j.location || 'Remote/Office',
      work_mode: j.work_mode || 'onsite',
      experience_hint: j.experience_hint || '',
      type: j.contract_time || j.type || 'Full-time',
      salary: j.salary_display || ((j.salary_min && j.salary_max) ? `₹${j.salary_min} - ₹${j.salary_max}` : j.salary || 'To be discussed'),
      salary_min: j.salary_min || 0,
      salary_max: j.salary_max || 0,
      salary_display: j.salary_display || '',
      skills: j.skills ? (typeof j.skills === 'string' ? j.skills.split(',').map(s=>s.trim()) : j.skills) : [],
      matching_skills: j.matching_skills || [],
      description: j.description || '',
      status: j.status || 'Active',
      applicants: 0,
      match: typeof j.match_percentage === 'number' ? j.match_percentage : (typeof j.match_score === 'number' ? j.match_score : 50),
      external_apply_url: (j.external_apply_url || j.apply_url || '').trim() || null,
      apply_url: (j.external_apply_url || j.apply_url || '').trim(),
      source: j.source || (data.source === 'adzuna' ? 'adzuna' : 'internal'),
      is_external: Boolean(j.is_external || j.source === 'adzuna' || j.external_apply_url || j.apply_url),
      source_job_id: j.source_job_id || j.raw_id || j.id,
      ...JOB_COLORS[i % JOB_COLORS.length],
      logo: (j.company||'??').substring(0,2).toUpperCase()
    }));

    DB.jobs.forEach(job => registerKnownJob(job));
    DB.jobs.sort((a, b) => b.match - a.match);
    _mlJobsCache = DB.jobs;
    _mlJobsCacheKey = cacheKey;
    UI.renderJobCards('cand-jobs-grid', DB.jobs, true);
    
    // Update candidate dashboard counters from the same response
    setEl('cand-stat-matches', DB.jobs.length);
    setEl('cand-analytics-matches', DB.jobs.length);
    updateSidebarBadges();

    if (typeof renderDashboardTopJobs === 'function') {
      renderDashboardTopJobs();
    }
    return DB.jobs;
  })
  .catch(err => {
    console.error("Error fetching ML job matches:", err);
    const errStr = String(err).toLowerCase();
    if (errStr.includes("failed to fetch") || errStr.includes("networkerror") || errStr.includes("typeerror")) {
      Toast.show("Network failure connecting to backend.", "error");
    }
  })
  .finally(() => {
    _isFetchingJobs = false;
    _fetchJobsPromise = null;
  });

  return _fetchJobsPromise;
}

function fetchCandidatesFromServer() {
  if (!DB.currentUser || DB.currentUser.role !== 'hr') {
    return;
  }
  fetch('/api/admin/candidates')
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(data => {
      if (!Array.isArray(data)) return;
      DB.candidates = data.map(c => ({
      id: c.app_id,
      user_id: c.user_id,
      name: c.name,
      email: c.email,
      phone: c.phone || 'Not provided',
      location: c.location || 'Not provided',
      linkedin: c.linkedin || '',
      github: c.github || '',
      degree: c.degree || 'Not detected',
      job: c.job,
      ats: c.ats_score || 0,
      match: c.match_score || 0,
      exp: c.exp || 'Not detected',
      exp_years: c.exp_years,
      sim: (c.match_score||0)/100,
      status: c.status,
      resume_id: c.resume_id || null,
      resume_name: c.resume_name || '',
      resume_mime: c.resume_mime || '',
      outlier_flag:   c.outlier_flag   || false,
      outlier_reason: c.outlier_reason || '',
      cluster_label:  c.cluster_label  || 'Unclustered',
      skills: c.skills ? c.skills.split(',').map(s=>s.trim()).filter(Boolean) : []
    }));
    UI.renderCandidatesTable();
    UI.renderRankingsTable();

    // ── Update HR filter tab counts with real numbers ──
    const all         = DB.candidates.length;
    const shortlisted = DB.candidates.filter(c => c.status === 'Shortlisted').length;
    const reviewing   = DB.candidates.filter(c => c.status === 'Reviewing').length;
    const pending     = DB.candidates.filter(c => c.status === 'Pending').length;
    const rejected    = DB.candidates.filter(c => c.status === 'Rejected').length;
    setEl('tab-count-all',         all);
    setEl('tab-count-shortlisted', shortlisted);
    setEl('tab-count-reviewing',   reviewing + pending);   // Reviewing + Pending combined
    setEl('tab-count-rejected',    rejected);
    const outlierCount = DB.candidates.filter(c => c.outlier_flag).length;
    setEl('tab-count-outliers', outlierCount);
    // Render cluster view if it exists in DOM
    renderClusterView();

    updateSidebarBadges();
    
    // Populate recent applications on HR Dashboard (top 5 by ID desc as proxy for recent)
    const recentTbody = document.getElementById('admin-dash-recent-tbody');
    if (recentTbody && DB.candidates) {
      const recentCands = [...DB.candidates].sort((a,b) => b.id - a.id).slice(0, 5);
      recentTbody.innerHTML = recentCands.map(c => `
        <tr>
          <td><div class="fw-600">${c.name}</div><div class="text-xs text-muted">${c.email}</div></td>
          <td>${c.job}</td>
          <td><span class="badge ${c.ats >= 80 ? 'badge-success' : (c.ats >= 50 ? 'badge-warning' : 'badge-danger')}">${c.ats}</span></td>
          <td>${UI.statusBadge(c.status)}</td>
          <td><button class="btn btn-sm btn-primary" onclick="viewCandidate(${c.id})">View</button></td>
        </tr>
      `).join('');
    }
  });
}

// ═══════════════════════════════════════════════════════════
// CANDIDATE NOTIFICATION CENTER (Enterprise Grade)
// ═══════════════════════════════════════════════════════════

function formatRelativeTime(dateStr) {
  if (!dateStr) return '';
  const cleanStr = String(dateStr).replace(/-/g, '/');
  const date = new Date(cleanStr);
  if (isNaN(date.getTime())) return dateStr;
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);
  if (diffSec < 60) return 'Just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function navigateToNotifAction(targetHash, notifId) {
  if (notifId && typeof CandidateNotifCenter !== 'undefined') {
    CandidateNotifCenter.markRead(notifId, null, false);
  }
  const cleanTarget = String(targetHash || '').replace('#', '').trim();
  if (cleanTarget === 'cand-applications' || cleanTarget === 'applications') {
    Router.inner('cand', 'applications');
    Sidebar.setActive(document.querySelector('#sb-cand [data-section=applications]'));
  } else if (cleanTarget === 'cand-jobs' || cleanTarget === 'jobs') {
    Router.inner('cand', 'jobs');
    Sidebar.setActive(document.querySelector('#sb-cand [data-section=jobs]'));
  } else if (cleanTarget === 'cand-ats' || cleanTarget === 'ats') {
    Router.inner('cand', 'ats');
    Sidebar.setActive(document.querySelector('#sb-cand [data-section=ats]'));
  } else if (cleanTarget === 'cand-profile' || cleanTarget === 'profile') {
    Router.inner('cand', 'profile');
    Sidebar.setActive(document.querySelector('#sb-cand [data-section=profile]'));
  } else if (cleanTarget) {
    Router.go(cleanTarget);
  }
}

const CandidateNotifCenter = {
  state: {
    category: 'all',
    search: '',
    notifications: [],
    unreadCount: 0,
    total: 0,
    loading: false
  },

  searchDebounceTimer: null,

  fetchNotifications(category, search) {
    if (category !== undefined) this.state.category = category;
    if (search !== undefined) this.state.search = search;

    const catParam = encodeURIComponent(this.state.category || 'all');
    const searchParam = encodeURIComponent(this.state.search || '');
    this.state.loading = true;

    const container = document.getElementById('cand-notif-list');
    if (container && this.state.notifications.length === 0) {
      container.innerHTML = `
        <div style="padding:44px 20px;text-align:center;color:var(--text-3);font-size:13px;">
          <i class="fas fa-circle-notch fa-spin" style="font-size:22px;color:var(--primary);margin-bottom:10px;display:block"></i>
          Loading notifications...
        </div>`;
    }

    fetch(`/api/notifications?category=${catParam}&search=${searchParam}`)
      .then(r => {
        if (r.status === 401) throw new Error('Unauthenticated');
        return r.json();
      })
      .then(res => {
        this.state.loading = false;
        if (!res || !res.success) return;

        this.state.notifications = res.notifications || [];
        this.state.unreadCount = res.unread_count || 0;
        this.state.total = res.total || 0;

        // Keep DB.notifications in sync
        DB.notifications = this.state.notifications.map(n => ({
          id: n.id,
          title: n.title,
          msg: n.message,
          time: n.created_at,
          unread: n.is_read === 0
        }));

        this.render();
        updateSidebarBadges();
      })
      .catch(err => {
        this.state.loading = false;
        console.error('Error fetching candidate notifications:', err);
      });
  },

  render() {
    const listEl = document.getElementById('cand-notif-list');
    if (!listEl) return;

    // Update unread count badge in header
    const unreadBadge = document.getElementById('cand-notif-unread-badge');
    if (unreadBadge) {
      unreadBadge.textContent = `${this.state.unreadCount} Unread`;
      unreadBadge.className = `badge ${this.state.unreadCount > 0 ? 'badge-primary' : 'badge-gray'}`;
    }

    const notifs = this.state.notifications;

    if (!notifs || notifs.length === 0) {
      listEl.innerHTML = this.renderEmptyState();
      return;
    }

    listEl.innerHTML = notifs.map(n => this.renderCard(n)).join('');
  },

  renderEmptyState() {
    const cat = this.state.category;
    let title = "You're all caught up!";
    let desc = "There are no notifications to show right now.";
    let icon = "fa-bell-slash";

    if (cat === 'unread') {
      title = "No unread notifications";
      desc = "You've read all your notifications.";
      icon = "fa-check-circle";
    } else if (cat === 'application') {
      title = "No application updates yet";
      desc = "We'll notify you whenever your application status changes.";
      icon = "fa-paper-plane";
    } else if (cat === 'match') {
      title = "No new job matches";
      desc = "Keep your resume updated to receive tailored job recommendations.";
      icon = "fa-briefcase";
    } else if (cat === 'view') {
      title = "No profile views yet";
      desc = "Recruiter profile views will appear here.";
      icon = "fa-eye";
    } else if (cat === 'system') {
      title = "No system alerts";
      desc = "Security, upload, and system events will appear here.";
      icon = "fa-shield-alt";
    }

    return `
      <div style="padding:44px 20px;text-align:center;color:var(--text-3);">
        <div style="width:52px;height:52px;border-radius:50%;background:var(--bg-2);display:inline-flex;align-items:center;justify-content:center;margin-bottom:12px;">
          <i class="fas ${icon}" style="font-size:22px;opacity:0.5;color:var(--primary);"></i>
        </div>
        <div style="font-size:15px;font-weight:700;color:var(--text-1);margin-bottom:5px;">${title}</div>
        <p style="max-width:360px;margin:0 auto 16px auto;font-size:13px;line-height:1.5;">${desc}</p>
        <div style="display:inline-flex;gap:10px;flex-wrap:wrap;justify-content:center;">
          <button class="btn btn-sm btn-primary" onclick="Router.inner('cand','jobs');Sidebar.setActive(document.querySelector('#sb-cand [data-section=jobs]'))"><i class="fas fa-briefcase"></i> Explore Live Jobs</button>
          <button class="btn btn-sm btn-outline" onclick="Router.inner('cand','ats');Sidebar.setActive(document.querySelector('#sb-cand [data-section=ats]'))"><i class="fas fa-trophy"></i> Improve ATS Score</button>
        </div>
      </div>`;
  },

  renderCard(n) {
    const isUnread = (n.is_read === 0 || n.is_read === false || n.unread === true);
    const typeMeta = this.getTypeMeta(n.type, n.title);
    const timeFormatted = formatRelativeTime(n.created_at);
    const actionBtnHtml = this.renderActionBtn(n);

    return `
      <div class="notif-item ${isUnread ? 'unread' : ''}" id="notif-card-${n.id}">
        <div class="notif-icon-wrap" style="background:${typeMeta.bg};color:${typeMeta.color}">
          <i class="fas ${typeMeta.icon}"></i>
        </div>

        <div class="notif-content">
          <div class="notif-top">
            <span class="notif-type-badge" style="background:${typeMeta.badgeBg};color:${typeMeta.badgeColor}">
              ${typeMeta.label}
            </span>
            <div style="display:flex;align-items:center;gap:8px;">
              ${isUnread ? '<span class="unread-pill" title="Unread"></span>' : ''}
              <span class="notif-item-time"><i class="far fa-clock"></i> ${timeFormatted}</span>
            </div>
          </div>

          <div class="notif-item-title">
            ${escapeHTML(n.title)}
          </div>
          
          <div class="notif-item-msg">
            ${escapeHTML(n.message)}
          </div>

          <div class="notif-footer">
            <div class="notif-actions-group">
              ${actionBtnHtml}
            </div>

            <div style="display:inline-flex;align-items:center;gap:6px;">
              ${isUnread ? `
                <button class="notif-icon-btn" title="Mark notification as read" onclick="CandidateNotifCenter.markRead(${n.id}, event)">
                  <i class="fas fa-check"></i>
                </button>` : ''}
              <button class="notif-icon-btn delete-btn" title="Delete notification" onclick="CandidateNotifCenter.delete(${n.id}, event)">
                <i class="fas fa-trash-alt"></i>
              </button>
            </div>
          </div>
        </div>
      </div>`;
  },

  getTypeMeta(type, title) {
    const t = String(type || '').toLowerCase();
    const ttl = String(title || '').toLowerCase();

    if (t === 'application' || ttl.includes('application') || ttl.includes('shortlist') || ttl.includes('interview')) {
      return {
        label: 'Application',
        icon: 'fa-paper-plane',
        bg: '#eff6ff',
        color: '#1d4ed8',
        badgeBg: 'rgba(29,78,216,0.1)',
        badgeColor: '#1d4ed8'
      };
    }
    if (t === 'match' || ttl.includes('match') || ttl.includes('job') || ttl.includes('recommend')) {
      return {
        label: 'Job Match',
        icon: 'fa-briefcase',
        bg: '#f0fdf4',
        color: '#15803d',
        badgeBg: 'rgba(21,128,61,0.1)',
        badgeColor: '#15803d'
      };
    }
    if (t === 'view' || t === 'profile_view' || ttl.includes('view') || ttl.includes('recruiter')) {
      return {
        label: 'Profile View',
        icon: 'fa-eye',
        bg: '#fdf4ff',
        color: '#7e22ce',
        badgeBg: 'rgba(126,34,206,0.1)',
        badgeColor: '#7e22ce'
      };
    }
    if (t === 'security' || ttl.includes('password') || ttl.includes('login') || ttl.includes('security')) {
      return {
        label: 'Security',
        icon: 'fa-shield-alt',
        bg: '#fff1f2',
        color: '#be123c',
        badgeBg: 'rgba(190,18,60,0.1)',
        badgeColor: '#be123c'
      };
    }
    return {
      label: 'System',
      icon: 'fa-bell',
      bg: '#f8fafc',
      color: '#475569',
      badgeBg: 'rgba(71,85,105,0.1)',
      badgeColor: '#475569'
    };
  },

  renderActionBtn(n) {
    const actType = n.action_type || '';
    const actTarget = n.action_target || '';
    const t = String(n.type || '').toLowerCase();
    const ttl = String(n.title || '').toLowerCase();

    if (actType === 'view_application' || t === 'application' || ttl.includes('application')) {
      return `<button class="notif-action-btn btn-outline" onclick="navigateToNotifAction('${actTarget || '#cand-applications'}', ${n.id})"><i class="fas fa-external-link-alt"></i> Track Application</button>`;
    }
    if (actType === 'view_jobs' || t === 'match' || ttl.includes('job') || ttl.includes('match')) {
      return `<button class="notif-action-btn btn-outline" onclick="navigateToNotifAction('${actTarget || '#cand-jobs'}', ${n.id})"><i class="fas fa-search"></i> View Matching Jobs</button>`;
    }
    if (actType === 'view_ats' || ttl.includes('resume') || ttl.includes('ats')) {
      return `<button class="notif-action-btn btn-outline" onclick="navigateToNotifAction('${actTarget || '#cand-ats'}', ${n.id})"><i class="fas fa-chart-line"></i> View ATS Breakdown</button>`;
    }
    if (actType === 'view_profile' || t === 'view' || ttl.includes('profile')) {
      return `<button class="notif-action-btn btn-outline" onclick="navigateToNotifAction('${actTarget || '#cand-profile'}', ${n.id})"><i class="fas fa-user-edit"></i> Enhance Profile</button>`;
    }
    return '';
  },

  filter(category, btnEl) {
    this.state.category = category;
    if (btnEl) {
      document.querySelectorAll('#cand-notif-tabs .notif-tab').forEach(t => t.classList.remove('active'));
      btnEl.classList.add('active');
    }
    this.fetchNotifications(category, this.state.search);
  },

  search(val) {
    clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => {
      this.state.search = val.trim();
      this.fetchNotifications(this.state.category, this.state.search);
    }, 250);
  },

  markRead(notifId, event, showToast = true) {
    if (event) event.stopPropagation();

    fetch(`/api/notifications/${notifId}/read`, { method: 'POST' })
      .then(r => r.json())
      .then(res => {
        if (!res || !res.success) return;

        const item = this.state.notifications.find(x => x.id === notifId);
        if (item) item.is_read = 1;

        this.state.unreadCount = res.unread_count !== undefined ? res.unread_count : Math.max(0, this.state.unreadCount - 1);
        this.render();
        updateSidebarBadges();

        if (showToast) Toast.show('Notification marked as read.', 'info');
      })
      .catch(err => console.error('Error marking notification read:', err));
  },

  delete(notifId, event) {
    if (event) event.stopPropagation();

    fetch(`/api/notifications/${notifId}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(res => {
        if (!res || !res.success) {
          Toast.show(res.message || 'Could not delete notification.', 'error');
          return;
        }

        this.state.notifications = this.state.notifications.filter(x => x.id !== notifId);
        this.state.unreadCount = res.unread_count !== undefined ? res.unread_count : this.state.unreadCount;
        this.render();
        updateSidebarBadges();

        Toast.show('Notification deleted.', 'info');
      })
      .catch(err => console.error('Error deleting notification:', err));
  },

  markAllRead() {
    fetch('/api/notifications/read-all', { method: 'POST' })
      .then(r => r.json())
      .then(res => {
        if (!res || !res.success) return;

        this.state.notifications.forEach(n => n.is_read = 1);
        this.state.unreadCount = 0;
        this.render();
        updateSidebarBadges();

        Toast.show('All notifications marked as read.', 'success');
      })
      .catch(err => console.error('Error marking all read:', err));
  },

  clearRead() {
    fetch('/api/notifications/clear', { method: 'DELETE' })
      .then(r => r.json())
      .then(res => {
        if (!res || !res.success) return;

        // Keep unread (is_read === 0) only
        this.state.notifications = this.state.notifications.filter(n => n.is_read === 0);
        this.render();
        updateSidebarBadges();

        Toast.show(`Cleared ${res.deleted_count || 0} read notifications.`, 'info');
      })
      .catch(err => console.error('Error clearing read notifications:', err));
  }
};

// Global Bridge Helpers for UI Template
function filterNotifications(cat, el) { CandidateNotifCenter.filter(cat, el); }
function handleNotificationSearch(val) { CandidateNotifCenter.search(val); }
function markAllNotificationsRead() { CandidateNotifCenter.markAllRead(); }
function clearReadNotifications() { CandidateNotifCenter.clearRead(); }
function markNotificationRead(id, ev) { CandidateNotifCenter.markRead(id, ev); }
function deleteNotification(id, ev) { CandidateNotifCenter.delete(id, ev); }

// Global fetch helper
function fetchNotificationsFromServer(userId) {
  if (typeof CandidateNotifCenter !== 'undefined') {
    CandidateNotifCenter.fetchNotifications();
  }
}

// Pull ALL live stats and update admin dashboard numbers
function fetchAdminStats() {
  fetch('/api/admin/stats').then(r=>r.json()).then(d=>{
    // Stat cards (dashboard KPIs)
    setEl('stat-total-applicants', d.total_applicants);
    setEl('stat-resumes-analyzed', d.resumes_analyzed);
    setEl('stat-shortlisted',      d.shortlisted);
    setEl('stat-active-jobs',      d.active_jobs);
    setEl('stat-avg-ats',          d.avg_ats_score);
    setEl('stat-reviewing',        d.reviewing);
    // NOTE: tab counts (All/Shortlisted/Reviewing/Rejected) are set by
    // fetchCandidatesFromServer() which uses the real joined candidate list.

    // Charts with real data
    const skillLabels = d.top_skills.map(x=>x.skill);
    const skillCounts = d.top_skills.map(x=>x.count);

    Charts.create('admin-skills-donut', {
      type:'doughnut',
      data:{ labels: skillLabels,
        datasets:[{ data: skillCounts,
          backgroundColor:['#1260cc','#00c9a7','#16a34a','#d97706','#7c3aed','#94a3b8','#e11d48','#0891b2'],
          borderWidth:3, borderColor:'#fff' }] },
      options:{ responsive:true, plugins:{ legend:{ position:'bottom', labels:{ font:{family:'DM Sans',size:12}, padding:10 }}}, cutout:'60%' }
    });

    Charts.create('admin-app-trend', {
      type:'bar',
      data:{ labels:['Shortlisted','Reviewing','Pending','Rejected'],
        datasets:[{ label:'Candidates', data:[d.shortlisted,d.reviewing,d.pending,d.rejected],
          backgroundColor:['#16a34a','#1260cc','#d97706','#dc2626'], borderRadius:6 }] },
      options:{ responsive:true, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} }}
    });

    // Analytics charts
    const roleLabels = d.apps_by_role.map(x=>x.role);
    const roleCounts = d.apps_by_role.map(x=>x.count);
    Charts.create('admin-role-pie', {
      type:'pie',
      data:{ labels:roleLabels,
        datasets:[{ data:roleCounts, backgroundColor:['#1260cc','#00c9a7','#16a34a','#d97706','#7c3aed','#94a3b8'], borderWidth:3, borderColor:'#fff' }] },
      options:{ responsive:true, plugins:{ legend:{ position:'bottom', labels:{ font:{family:'DM Sans',size:12}, padding:10 }}}}
    });
    Charts.create('admin-skills-bar', {
      type:'bar',
      data:{ labels:skillLabels,
        datasets:[{ label:'Candidates with skill', data:skillCounts, backgroundColor:'#1260cc', borderRadius:6 }] },
      options:{ indexAxis:'y', responsive:true, plugins:{legend:{display:false}}, scales:{ x:{beginAtZero:true,grid:{color:'#f0f4f9'}}, y:{grid:{display:false}} }}
    });
    Charts.create('admin-status-funnel', {
      type:'doughnut',
      data:{ labels:['Shortlisted','Reviewing','Pending','Rejected'],
        datasets:[{ data:[d.shortlisted,d.reviewing,d.pending,d.rejected],
          backgroundColor:['#16a34a','#1260cc','#d97706','#dc2626'], borderWidth:3, borderColor:'#fff' }] },
      options:{ responsive:true, plugins:{ legend:{ position:'bottom', labels:{ font:{family:'DM Sans',size:12}, padding:10 }}}, cutout:'65%' }
    });
    Charts.create('admin-ats-dist', {
      type:'bar',
      data:{
        labels:['0–20','21–40','41–60','61–70','71–80','81–90','91–100'],
        datasets:[{
          label:'Candidates',
          data:d.ats_distribution,
          backgroundColor:['#fee2e2','#fecaca','#fed7aa','#fef08a','#bbf7d0','#6ee7b7','#00c9a7'],
          borderRadius:6
        }]
      },
      options:{ responsive:true, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} } }
    });
    Charts.create('admin-app-time', {
      type:'line',
      data:{
        labels:d.app_time.labels,
        datasets:[{
          label:'Total Applications',
          data:d.app_time.total,
          borderColor:'#1260cc', backgroundColor:'rgba(18,96,204,.1)',
          tension:.4, fill:true, pointBackgroundColor:'#1260cc'
        },{
          label:'Shortlisted',
          data:d.app_time.shortlisted,
          borderColor:'#00c9a7', backgroundColor:'rgba(0,201,167,.08)',
          tension:.4, fill:true, pointBackgroundColor:'#00c9a7'
        }]
      },
      options:{ responsive:true, plugins:{ legend:{ position:'top', labels:{ font:{family:'DM Sans',size:12}, padding:14 } } }, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} } }
    });
    Charts.create('admin-hires', {
      type:'line',
      data:{
        labels: d.app_time.labels,
        datasets:[{
          label:'Shortlisted',
          data: d.app_time.shortlisted,
          borderColor:'#16a34a', backgroundColor:'rgba(22,163,74,.1)',
          tension:.4, fill:true, pointBackgroundColor:'#16a34a'
        }]
      },
      options:{ responsive:true, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} } }
    });

    // ── Analytics page stat cards (dynamic) ──
    // Avg ATS
    const avgAtsEl = document.querySelector('#admin-analytics .stat-value');
    if (avgAtsEl) avgAtsEl.textContent = d.avg_ats_score;
    
    // Bind all analytics stats by ID
    setEl('stat-analytics-avg-ats',        d.avg_ats_score || 0);
    setEl('stat-analytics-time-shortlist', d.time_to_shortlist || '2.4h');
    setEl('stat-analytics-top-skill',      d.top_skill_demanded || (d.top_skills && d.top_skills[0]?.skill) || 'Python');
    setEl('stat-analytics-accept-rate',    (d.acceptance_rate !== undefined ? d.acceptance_rate : 0) + '%');
    setEl('stat-analytics-active-jobs',    d.active_jobs || 0);
    
    // Job postings header: "X active positions"
    const jobsHeader = document.getElementById('admin-jobs-header-count');
    if (jobsHeader) jobsHeader.textContent = `${d.active_jobs} active positions · ${d.reviewing} reviewing`;
    
    updateSidebarBadges();
  });
}


// ── Top Job Recommendations (Candidate Dashboard) ─────────────────
function renderDashboardTopJobs() {
  const tbody = document.getElementById('cand-dash-jobs-tbody');
  if (!tbody) return;

  const hasSkills = DB.currentUser && DB.currentUser.skills && DB.currentUser.skills.trim() !== '';

  if (!DB.jobs || DB.jobs.length === 0) {
    if (!hasSkills && DB.currentUser && DB.currentUser.role === 'candidate') {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center;padding:36px 16px;">
            <div style="display:inline-flex;flex-direction:column;align-items:center;gap:10px;color:var(--text-3);font-size:13px;">
              <i class="fas fa-file-upload" style="font-size:26px;color:var(--primary);opacity:0.85;"></i>
              <span style="font-weight:700;font-size:15px;color:var(--text-1);">Upload your resume to get personalized job matches</span>
              <span style="max-width:400px;line-height:1.4;">Add your resume so our AI can extract your skills and recommend tailored opportunities.</span>
              <button class="btn btn-sm btn-primary mt-2" onclick="Router.inner('cand','upload')"><i class="fas fa-upload"></i> Upload Resume</button>
            </div>
          </td>
        </tr>`;
      return;
    }

    if (DB.currentUser && DB.currentUser.role === 'candidate' && !_isFetchingJobs) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center;padding:36px 16px;">
            <div style="display:inline-flex;flex-direction:column;align-items:center;gap:10px;color:var(--text-3);font-size:13px;">
              <i class="fas fa-circle-notch fa-spin" style="font-size:24px;color:var(--primary);"></i>
              <span style="font-weight:500;">Finding top matching jobs for your profile...</span>
            </div>
          </td>
        </tr>`;
      fetchJobsFromServer();
      return;
    }
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:36px 16px;">
          <div style="display:inline-flex;flex-direction:column;align-items:center;gap:8px;color:var(--text-3);font-size:13px;">
            <i class="fas fa-briefcase" style="font-size:24px;opacity:0.4;"></i>
            <span style="font-weight:500;">No recommendations yet. Upload your resume or update your skills to see top matches.</span>
            <button class="btn btn-sm btn-outline mt-2" onclick="Router.inner('cand','upload')"><i class="fas fa-upload"></i> Upload Resume</button>
          </div>
        </td>
      </tr>`;
    return;
  }

  const topJobs = [...DB.jobs].sort((a, b) => (b.match || 0) - (a.match || 0)).slice(0, 5);
  tbody.innerHTML = topJobs.map(j => {
    registerKnownJob(j);
    const key = (j.company || '').toLowerCase().trim();
    const domain = COMPANY_DOMAINS[key] || Object.entries(COMPANY_DOMAINS).find(([k]) => key.includes(k))?.[1];
    const abbr = (j.company || '??').substring(0, 2).toUpperCase();
    const color = j.color || '#e0f2fe';
    const tcolor = j.textColor || '#1e40af';
    const extUrl = (j.external_apply_url || j.apply_url || '').trim();
    const isExt = Boolean(j.is_external || j.source === 'adzuna' || extUrl);
    const safeId = String(j.id).replace(/'/g, "\\'");
    const encodedUrl = encodeURIComponent(extUrl);
    const matchScore = typeof j.match === 'number' ? j.match : 50;

    let badgeClass = 'badge-success';
    let matchGradient = 'linear-gradient(90deg, #10b981, #059669)';
    if (matchScore < 60) {
      badgeClass = 'badge-warning';
      matchGradient = 'linear-gradient(90deg, #f59e0b, #d97706)';
    } else if (matchScore < 80) {
      badgeClass = 'badge-info';
      matchGradient = 'linear-gradient(90deg, #0ea5e9, #2563eb)';
    }

    const jobType = j.type || 'Full-time';
    const typeClass = jobType.toLowerCase().includes('contract') ? 'badge-teal' : (jobType.toLowerCase().includes('part') ? 'badge-info' : 'badge-violet');

    const logoHTML = domain
      ? `<img src="https://www.google.com/s2/favicons?domain=${domain}&sz=128"
              alt="${abbr}"
              loading="lazy"
              style="width:38px;height:38px;object-fit:contain;border-radius:8px;padding:3px;background:#fff;border:1px solid rgba(0,0,0,0.08);box-shadow:0 1px 3px rgba(0,0,0,0.05);flex-shrink:0;"
              onerror="this.onerror=null;this.parentElement.innerHTML='<div style=\\\'width:38px;height:38px;border-radius:8px;background:${color};color:${tcolor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;font-family:Syne,sans-serif;flex-shrink:0;box-shadow:0 1px 3px rgba(0,0,0,0.05);\\\'>${abbr}</div>';">`
      : `<div style="width:38px;height:38px;border-radius:8px;background:${color};color:${tcolor};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;font-family:\'Syne\',sans-serif;flex-shrink:0;box-shadow:0 1px 3px rgba(0,0,0,0.05);">${abbr}</div>`;

    return `
      <tr style="transition:background 0.15s ease;">
        <td style="padding:14px 16px;">
          <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:38px;height:38px;flex-shrink:0;display:flex;align-items:center;justify-content:center;">${logoHTML}</div>
            <div style="min-width:0;">
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <span style="font-weight:700;font-size:14px;color:var(--text);letter-spacing:-0.01em;">${escapeHTML(j.title)}</span>
                ${(j.is_external || j.source === 'adzuna')
                  ? '<span class="badge badge-success" style="background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px;"><i class="fas fa-bolt" style="font-size:8px;margin-right:2px;"></i>Live</span>'
                  : '<span class="badge badge-secondary" style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px;"><i class="fas fa-database" style="font-size:8px;margin-right:2px;"></i>Saved</span>'
                }
                ${matchScore >= 85 ? '<span class="badge badge-teal" style="font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px;"><i class="fas fa-star" style="font-size:8px;margin-right:2px;"></i>Top Match</span>' : ''}
              </div>
              <div style="display:flex;align-items:center;gap:12px;margin-top:3px;font-size:11.5px;color:var(--text-3);flex-wrap:wrap;">
                <span style="display:inline-flex;align-items:center;gap:4px;"><i class="fas fa-map-marker-alt" style="font-size:10px;color:var(--primary);opacity:0.8;"></i> ${escapeHTML(j.location || 'Remote')}</span>
                <span style="display:inline-flex;align-items:center;gap:3px;font-weight:600;color:#059669;"><i class="fas fa-rupee-sign" style="font-size:10px;"></i> ${escapeHTML(j.salary || 'Competitive')}</span>
              </div>
            </div>
          </div>
        </td>
        <td style="padding:14px 16px;white-space:nowrap;">
          <div style="font-weight:600;font-size:13.5px;color:var(--text);">${escapeHTML(j.company || 'Company')}</div>
          <div style="font-size:11px;color:var(--text-3);margin-top:2px;">${j.posted_date ? new Date(j.posted_date).toLocaleDateString(undefined, {month:'short', day:'numeric'}) : 'Recently posted'}</div>
        </td>
        <td style="padding:14px 16px;">
          <div style="min-width:110px;max-width:140px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
              <span class="badge ${badgeClass}" style="font-weight:700;font-size:11px;padding:2px 7px;border-radius:5px;">${matchScore}%</span>
              <span style="font-size:10.5px;color:var(--text-3);font-weight:500;">Match</span>
            </div>
            <div style="height:5px;width:100%;background:rgba(148,163,184,0.2);border-radius:99px;overflow:hidden;">
              <div style="height:100%;width:${Math.min(100, Math.max(8, matchScore))}%;background:${matchGradient};border-radius:99px;transition:width 0.5s ease;"></div>
            </div>
          </div>
        </td>
        <td style="padding:14px 16px;white-space:nowrap;">
          <span class="badge ${typeClass}" style="display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:4px 9px;border-radius:6px;">
            <i class="fas fa-briefcase" style="font-size:9px;opacity:0.8;"></i> ${escapeHTML(jobType)}
          </span>
        </td>
        <td style="padding:14px 16px;text-align:right;white-space:nowrap;">
          <button class="btn btn-sm btn-primary btn-apply-external"
            data-job-id="${escapeHTML(String(safeId))}"
            data-is-external="${isExt}"
            data-apply-url="${encodedUrl}"
            data-job-title="${escapeHTML(j.title || '')}"
            data-job-company="${escapeHTML(j.company || '')}"
            data-match-score="${matchScore}"
            onclick="applyJob('${escapeHTML(String(safeId))}', ${isExt}, '${encodedUrl}', this)"
            style="display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;padding:6px 14px;border-radius:7px;box-shadow:0 2px 6px rgba(18,96,204,0.22);transition:all 0.15s ease;">
            Apply ${isExt ? '<i class="fas fa-external-link-alt" style="font-size:10px;opacity:0.85;"></i>' : ''}
          </button>
        </td>
      </tr>
    `;
  }).join('');
}


// Pull live candidate stats for the logged-in user
function fetchCandidateStats(userId) {
  fetch(`/api/candidate/stats/${userId}`).then(r=>r.json()).then(d=>{
    const hasResume = Boolean(d.has_resume);
    const score = hasResume ? (d.ats_score || 0) : 0;
    const skillsCount = hasResume ? (d.skills_count || (d.skills ? d.skills.length : 0)) : 0;
    
    // Stat cards
    setEl('cand-stat-ats',          score > 0 ? score : '--');
    setEl('cand-stat-skills',       skillsCount);
    // Real ML matched jobs count — only populated when candidate has uploaded resume with skills
    const realMatchedCount = hasResume ? ((_mlJobsCache && _mlJobsCache.length > 0) ? _mlJobsCache.length : (d.job_matches || 0)) : 0;
    setEl('cand-stat-matches',      realMatchedCount);
    setEl('cand-stat-apps',         d.applications || 0);
    setEl('cand-analytics-stat-ats', score > 0 ? score : '--');
    // ATS display in welcome banner + mini donut + dashboard ATS
    setEl('cand-ats-display', score > 0 ? score : '--');
    setEl('ats-score-big-num', score > 0 ? score : '--');
    setEl('cand-ats-mini-num', score > 0 ? score : '--');
    const svg = document.querySelector('.score-svg');
    if(svg) svg.setAttribute('data-score', score);

    // Profile Views — real from DB (0 means no HR has viewed your profile yet)
    const realViews = d.profile_views !== undefined ? d.profile_views : 0;
    const realWeekly = d.profile_views_weekly !== undefined ? d.profile_views_weekly : 0;
    setEl('cand-stat-views', realViews);
    setEl('cand-stat-views-weekly', realWeekly > 0 ? `+${realWeekly} this week` : 'No views yet');
    setEl('cand-analytics-views', realViews);
    setEl('cand-analytics-views-weekly', realWeekly > 0 ? `+${realWeekly}` : '0');
    setEl('cand-analytics-apps', d.applications || 0);
    setEl('cand-analytics-matches', realMatchedCount);

    // Matched keywords
    const atsMatchedContainer = document.getElementById('ats-matched-keywords');
    if (atsMatchedContainer) {
      if (hasResume && d.skills && d.skills.length > 0) {
        atsMatchedContainer.innerHTML = d.skills.map(s => `<span class="skill-tag skill-match">${s} ✓</span>`).join('');
      } else {
        atsMatchedContainer.innerHTML = '<p class="text-muted text-sm" style="color:var(--text-3);padding:6px 0;">No resume uploaded yet. Upload your resume to extract skills.</p>';
      }
    }
    
    // Missing keywords
    const missingContainer = document.getElementById('cand-missing-keywords');
    const missingCount = document.getElementById('cand-missing-count');
    if (missingContainer) {
      if (hasResume && d.missing_skills && d.missing_skills.length > 0) {
        missingContainer.innerHTML = d.missing_skills.map(s => `<span class="skill-tag skill-missing">${s} ✗</span>`).join('');
        if (missingCount) missingCount.textContent = `${d.missing_skills.length} Missing`;
      } else {
        missingContainer.innerHTML = '<p class="text-muted text-sm" style="color:var(--text-3);padding:6px 0;">Upload your resume to see missing keyword recommendations.</p>';
        if (missingCount) missingCount.textContent = '0 Missing';
      }
    }

    // Top Jobs in Dashboard
    renderDashboardTopJobs();

    // ATS mini-donut
    Charts.create('cand-ats-mini', {
      type:'doughnut',
      data:{ labels:['Score','Remaining'],
        datasets:[{ data:[score, 100-score], backgroundColor:['#1260cc','#e6edf7'], borderWidth:0, cutout:'78%' }] },
      options:{ responsive:true, plugins:{ legend:{display:false}, tooltip:{enabled:false} }}
    });
    // Dynamic Weekly Profile Views & Activity Timeline
    const timelineCanvas = document.getElementById('cand-timeline');
    if (timelineCanvas) {
      const dayLabels = (d.day_labels && d.day_labels.length === 7) ? d.day_labels : ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'];
      const dailyViews = (d.views_daily && d.views_daily.length === 7) ? d.views_daily : [0, 0, 0, 0, 0, 0, 0];
      const dailyApps  = (d.apps_daily && d.apps_daily.length === 7) ? d.apps_daily : [0, 0, 0, 0, 0, 0, 0];

      Charts.create('cand-timeline', {
        type: 'line',
        data: {
          labels: dayLabels,
          datasets: [
            {
              label: 'Profile Views',
              data: dailyViews,
              borderColor: '#1260cc',
              backgroundColor: 'rgba(18,96,204,.12)',
              borderWidth: 2.5,
              fill: true,
              tension: 0.35,
              pointBackgroundColor: '#1260cc',
              pointRadius: 4,
              pointHoverRadius: 6
            },
            {
              label: 'Applications Submitted',
              data: dailyApps,
              borderColor: '#00c9a7',
              backgroundColor: 'rgba(0,201,167,.08)',
              borderWidth: 2,
              borderDash: [5, 5],
              fill: false,
              tension: 0.35,
              pointBackgroundColor: '#00c9a7',
              pointRadius: 3,
              pointHoverRadius: 5
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              position: 'top',
              labels: { font: { family: 'DM Sans', size: 12 }, padding: 12, usePointStyle: true }
            },
            tooltip: {
              mode: 'index',
              intersect: false
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0, stepSize: 1, font: { size: 11 } },
              grid: { color: '#f0f4f9' }
            },
            x: {
              grid: { display: false },
              ticks: { font: { size: 12 } }
            }
          }
        }
      });
    }

    // Dynamic Candidate Charts
    if (d.market_trends) {
      const mt = d.market_trends;
      Charts.create('cand-ats-dist', {
        type:'bar',
        data:{
          labels:['0–20','21–40','41–60','61–70','71–80','81–90','91–100'],
          datasets:[{
            label:'Candidates',
            data:mt.ats_distribution,
            backgroundColor:['#fee2e2','#fecaca','#fed7aa','#fef08a','#bbf7d0','#6ee7b7','#00c9a7'],
            borderRadius:6
          }]
        },
        options:{ responsive:true, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} } }
      });

      Charts.create('cand-app-time', {
        type:'line',
        data:{
          labels:mt.app_time.labels,
          datasets:[{
            label:'Total Applications',
            data:mt.app_time.total,
            borderColor:'#1260cc', backgroundColor:'rgba(18,96,204,.1)',
            tension:.4, fill:true, pointBackgroundColor:'#1260cc'
          },{
            label:'Shortlisted',
            data:mt.app_time.shortlisted,
            borderColor:'#00c9a7', backgroundColor:'rgba(0,201,167,.08)',
            tension:.4, fill:true, pointBackgroundColor:'#00c9a7'
          }]
        },
        options:{ responsive:true, plugins:{ legend:{ position:'top', labels:{ font:{family:'DM Sans',size:12}, padding:14 } } }, scales:{ y:{beginAtZero:true,grid:{color:'#f0f4f9'}}, x:{grid:{display:false}} } }
      });

      const cSkillLabels = mt.top_skills.map(x=>x.skill);
      const cSkillCounts = mt.top_skills.map(x=>x.count);
      Charts.create('cand-skills-bar', {
        type:'bar',
        data:{
          labels:cSkillLabels,
          datasets:[{
            label:'Candidates with skill',
            data:cSkillCounts,
            backgroundColor:'#1260cc',
            borderRadius:6
          }]
        },
        options:{ indexAxis:'y', responsive:true, plugins:{legend:{display:false}}, scales:{ x:{beginAtZero:true,grid:{color:'#f0f4f9'}}, y:{grid:{display:false}} } }
      });
    }

    if (d.radar) {
      Charts.create('skills-radar', {
        type: 'radar',
        data: {
          labels: d.radar.labels,
          datasets: [{
            label:'Your Level',
            data: d.radar.levels,
            backgroundColor:'rgba(18,96,204,.15)',
            borderColor:'#1260cc', borderWidth:2,
            pointBackgroundColor:'#1260cc'
          },{
            label:'Required',
            data: d.radar.required,
            backgroundColor:'rgba(0,201,167,.12)',
            borderColor:'#00c9a7', borderWidth:2,
            pointBackgroundColor:'#00c9a7'
          }]
        },
        options: { responsive:true, plugins:{ legend:{ position:'bottom', labels:{ font:{family:'DM Sans',size:12}, padding:14 } } }, scales:{ r:{ grid:{color:'#e6edf7'}, ticks:{font:{size:11},stepSize:20}, suggestedMin:0, suggestedMax:100 } } }
      });
    }

      // Candidate analytics: role distribution from market_trends
      if (d.market_trends && d.market_trends.top_skills) {
        const roleLabels = d.market_trends.top_skills.slice(0,6).map(x => x.skill);
        const roleCounts = d.market_trends.top_skills.slice(0,6).map(x => x.count);
        Charts.create('cand-role-pie', {
          type:'pie',
          data:{ labels:roleLabels,
            datasets:[{ data:roleCounts, backgroundColor:['#1260cc','#00c9a7','#16a34a','#d97706','#7c3aed','#94a3b8'], borderWidth:3, borderColor:'#fff' }] },
          options:{ responsive:true, plugins:{ legend:{ position:'bottom', labels:{ font:{family:'DM Sans',size:12}, padding:10 }}}}
        });
      }

    // ── Render skill gaps (real proficiency bars) ──
    renderSkillGaps(d.skills || [], d.missing_skills || [], d.skill_demand_pct || {});

    
    // ── Render ATS page hero dynamically ──
    renderATSPage(score, d.skills || [], d.missing_skills || [], d.skills_count || 0);
    
    // ── Profile hero badge (ATS score) ──
    const profileAtsBadge = document.getElementById('profile-ats-badge');
    if (profileAtsBadge) profileAtsBadge.textContent = `ATS Score: ${score}/100`;
    
    // ── Profile Views This Week chart — REAL data from API ──
    const dayNames   = d.day_names   || ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const viewsDaily = d.views_daily || [0,0,0,0,0,0,0];
    const appsDaily  = d.apps_daily  || [0,0,0,0,0,0,0];

    Charts.create('cand-timeline', {
      type: 'line',
      data: {
        labels: dayNames,
        datasets: [
          {
            label: 'Profile Views',
            data: viewsDaily,
            borderColor: '#1260cc',
            backgroundColor: 'rgba(18,96,204,.12)',
            tension: .4, fill: true, pointBackgroundColor: '#1260cc',
            pointRadius: 4
          },
          {
            label: 'Applications Sent',
            data: appsDaily,
            borderColor: '#00c9a7',
            backgroundColor: 'rgba(0,201,167,.08)',
            tension: .4, fill: true, pointBackgroundColor: '#00c9a7',
            pointRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'top', labels: { font: { family: 'DM Sans', size: 12 }, padding: 14 } },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          y: { beginAtZero: true, precision: 0, grid: { color: '#f0f4f9' }, ticks: { stepSize: 1 } },
          x: { grid: { display: false } }
        }
      }
    });

    // Also update the ATS mini-donut (already done above but keep in sync)
    Charts.initCandidateCharts(score);

    updateSidebarBadges();

  });
}

// ── Render dynamic skill gap progress bars ──────────────────
function renderSkillGaps(skills, missingSkills, demandPct) {
  const container = document.getElementById('cand-skill-gaps');
  if (!container) return;

  // Combine candidate's own skills + missing skills (top 5 total)
  const allSkills = [...skills.slice(0, 3), ...missingSkills.slice(0, 2)];
  if (!allSkills.length) {
    container.innerHTML = '<p class="text-muted text-sm">Upload resume to see skill gaps.</p>';
    return;
  }

  container.innerHTML = allSkills.map(skill => {
    const isMissing  = missingSkills.includes(skill);
    // Real % = market demand from DB (how many candidates on platform have this skill)
    const realPct    = demandPct[skill] || demandPct[skill.toLowerCase()] || 0;
    const displayPct = isMissing ? 0 : (realPct > 0 ? realPct : 5);
    const color      = isMissing ? '#dc2626' : (displayPct >= 60 ? '#16a34a' : '#d97706');
    const label      = isMissing
      ? '<span style="font-size:10px;color:#dc2626;font-weight:600">⚠ Missing from your resume</span>'
      : `<span style="font-size:10px;color:#64748b">${displayPct}% market demand</span>`;

    return `
      <div style="margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:13px;margin-bottom:4px">
          <div>
            <span style="font-weight:600">${skill}</span>
            <br>${label}
          </div>
          <span style="font-weight:700;color:${color};font-size:14px">${isMissing ? '0%' : displayPct + '%'}</span>
        </div>
        <div class="progress">
          <div class="progress-bar" style="width:${isMissing ? 2 : displayPct}%;background:${color};transition:width .8s ease"></div>
        </div>
      </div>`;
  }).join('');
}


// ── Render ATS page hero + breakdown bars dynamically ───────
function renderATSPage(score, skills, missingSkills, skillCount) {
  // Hero band text
  const atsHeading = document.getElementById('ats-hero-heading');
  const atsSubtext = document.getElementById('ats-hero-subtext');
  const atsBadgeMatched = document.getElementById('ats-badge-matched');
  const atsBadgeMissing = document.getElementById('ats-badge-missing');
  
  if (atsHeading) {
    const grade = score >= 80 ? 'Excellent' : score >= 65 ? 'Good' : score >= 50 ? 'Fair' : 'Needs Work';
    const emoji = score >= 80 ? '<i class="fa-solid fa-trophy"></i>' : score >= 65 ? '<i class="fa-solid fa-wand-magic-sparkles"></i>' : score >= 50 ? '<i class="fa-solid fa-thumbs-up"></i>' : '<i class="fa-solid fa-dumbbell"></i>';
    atsHeading.innerHTML = `${grade} ATS Score <span style="margin-left: 8px;">${emoji}</span>`;
  }
  if (atsSubtext) {
    atsSubtext.textContent = score >= 65
      ? `Your resume performs well. ${missingSkills.length > 0 ? 'Add ' + missingSkills.slice(0,2).join(', ') + ' to push above 90.' : 'Keep it up!'}`
      : `Add these skills to improve: ${missingSkills.slice(0,3).join(', ')}`;
  }
  if (atsBadgeMatched) atsBadgeMatched.textContent = `${skillCount} Keywords Matched`;
  if (atsBadgeMissing) atsBadgeMissing.textContent = `${missingSkills.length} Keywords Missing`;
  
  // SVG ring
  const svg = document.querySelector('.score-svg');
  if (svg) svg.setAttribute('data-score', score);
  setEl('ats-score-big-num', score);
  setTimeout(() => animateATSRings(), 200);
  
  // Breakdown progress bars (computed from ATS score)
  const bars = [
    { id:'ats-bar-keyword',    label:'Keyword Match',          pct: Math.min(100, Math.round(score * 1.05)) },
    { id:'ats-bar-skills',     label:'Skills Alignment',       pct: Math.min(100, Math.round(score * 0.97)) },
    { id:'ats-bar-experience', label:'Experience Match',       pct: Math.min(100, Math.round(score * 0.82)) },
    { id:'ats-bar-education',  label:'Education Fit',          pct: Math.min(100, Math.round(score * 1.1)) },
    { id:'ats-bar-format',     label:'Format & Readability',   pct: Math.min(100, Math.round(score * 0.78)) },
    { id:'ats-bar-contact',    label:'Contact Completeness',   pct: Math.min(100, score > 0 ? 85 : 0) }
  ];
  bars.forEach(b => {
    const el = document.getElementById(b.id);
    if (!el) return;
    const color = b.pct >= 80 ? 'linear-gradient(90deg,#16a34a,#4ade80)' : b.pct >= 60 ? 'linear-gradient(90deg,#d97706,#fbbf24)' : 'linear-gradient(90deg,#dc2626,#f87171)';
    const txtColor = b.pct >= 80 ? '#16a34a' : b.pct >= 60 ? '#d97706' : '#dc2626';
    el.innerHTML = `
      <div style="font-size:13px;font-weight:600;margin-bottom:10px;display:flex;justify-content:space-between">
        <span>${b.label}</span><span style="color:${txtColor};font-weight:700">${b.pct}%</span>
      </div>
      <div class="progress progress-lg"><div class="progress-bar" style="width:${b.pct}%;background:${color}"></div></div>`;
  });
}

// ── Render upload history from real database state (GAP-03, GAP-04) ────
function loadResumeHistory() {
  const list = document.getElementById('upload-list');
  if (!list) return;
  list.innerHTML = '<p class="text-muted text-sm" style="padding:16px"><i class="fas fa-spinner fa-spin"></i> Loading resumes...</p>';

  fetch('/api/resume/my_resumes')
    .then(r => r.json())
    .then(data => {
      if (!data || !data.success || !data.resumes || data.resumes.length === 0) {
        list.innerHTML = '<p class="text-muted text-sm" style="padding:16px">No resume uploaded yet.</p>';
        return;
      }

      list.innerHTML = data.resumes.map(r => {
        const isPdf = (r.mime_type === 'application/pdf' || (r.original_name && r.original_name.toLowerCase().endsWith('.pdf')));
        const iconClass = isPdf ? 'fa-file-pdf' : 'fa-file-word';
        const iconColor = isPdf ? '#dc2626' : '#2563eb';
        const iconBg = isPdf ? '#fee2e2' : '#dbeafe';
        const dateStr = r.uploaded_at ? new Date(r.uploaded_at).toLocaleDateString() : 'Recent';
        const score = r.ats_score !== undefined ? r.ats_score : 0;

        return `
          <div class="upload-item" style="margin-bottom:12px;display:flex;align-items:center;gap:14px;padding:12px 16px;background:var(--bg);border-radius:10px;border:1px solid var(--border)">
            <div class="upload-item-icon" style="background:${iconBg};width:42px;height:42px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0"><i class="fas ${iconClass}" style="color:${iconColor};font-size:20px"></i></div>
            <div class="upload-item-body" style="flex:1;min-width:0">
              <div class="upload-item-name" style="font-weight:600;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHTML(r.original_name)}</div>
              <div class="upload-item-meta" style="font-size:12px;color:var(--text-3)">Uploaded ${dateStr} · ATS Score: <strong>${score}/100</strong></div>
            </div>
            <span class="badge badge-success" style="flex-shrink:0"><i class="fas fa-check"></i> ${escapeHTML(r.status || 'Analyzed')}</span>
            <div style="display:flex;gap:6px;flex-shrink:0">
              ${isPdf ? `<a href="/api/resume/download/${r.id}?preview=1" target="_blank" class="btn btn-sm btn-outline" title="Preview in Browser"><i class="fas fa-eye"></i> Preview</a>` : ''}
              <a href="/api/resume/download/${r.id}" class="btn btn-sm btn-navy" title="Download File"><i class="fas fa-download"></i> Download</a>
              <button class="btn btn-sm btn-primary" onclick="Router.inner('cand','ats');Sidebar.setActive(document.querySelector('#sb-cand [data-section=ats]'))">ATS</button>
              <button class="btn btn-sm btn-danger" onclick="deleteResume(${r.id})" title="Delete Resume" style="background:#ef4444;color:#fff;border:none"><i class="fas fa-trash"></i> Delete</button>
            </div>
          </div>
        `;
      }).join('');

      // Also hydrate Resume Intelligence view from latest uploaded resume (GAP-01)
      const latest = data.resumes[0];
      if (latest && latest.structured_json) {
        try {
          const intel = typeof latest.structured_json === 'string' ? JSON.parse(latest.structured_json) : latest.structured_json;
          renderResumeIntelligence(intel, latest);
        } catch(e) {
          console.error("Failed to parse structured_json:", e);
        }
      }
    })
    .catch(err => {
      list.innerHTML = '<p class="text-danger text-sm" style="padding:16px">Failed to load resume history.</p>';
    });
}

function deleteResume(resumeId) {
  if (!confirm('Are you sure you want to delete this resume? This action cannot be undone.')) {
    return;
  }
  fetch(`/api/resume/${resumeId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(r => r.json())
    .then(data => {
      if (data && data.success) {
        Toast.show(data.message || 'Resume deleted successfully. 🗑️', 'success');
        loadResumeHistory();
        if (typeof fetchDashboardStats === 'function') fetchDashboardStats();
      } else {
        Toast.show((data && data.message) || 'Failed to delete resume.', 'danger');
      }
    })
    .catch(err => {
      console.error('Failed to delete resume:', err);
      Toast.show('Network error while deleting resume.', 'danger');
    });
}
window.deleteResume = deleteResume;

function renderUploadHistory(user) {
  loadResumeHistory();
}

// ── Render Full Canonical Resume Intelligence (GAP-01) ──────
function renderResumeIntelligence(intel, resumeMeta = {}) {
  if (!intel) return;

  // 1. Candidate Personal & Contact Information
  const cand = intel.candidate || {};
  const contact = intel.contact || {};
  const sections = intel.sections || {};

  const nameEl = document.getElementById('profile-name');
  if (nameEl) nameEl.textContent = cand.name || (DB.currentUser ? DB.currentUser.name : 'Not detected');

  const emailEl = document.getElementById('profile-email');
  if (emailEl) emailEl.textContent = contact.email || (DB.currentUser ? DB.currentUser.email : 'Not detected');

  const phoneEl = document.getElementById('profile-phone');
  if (phoneEl) phoneEl.textContent = contact.phone || (DB.currentUser && DB.currentUser.phone ? DB.currentUser.phone : 'Not detected');

  const locEl = document.getElementById('profile-location');
  if (locEl) {
    const locParts = [contact.city, contact.country].filter(Boolean);
    locEl.textContent = locParts.length ? locParts.join(', ') : (DB.currentUser && DB.currentUser.location ? DB.currentUser.location : 'Not detected');
  }

  const sumEl = document.getElementById('profile-summary');
  if (sumEl) sumEl.textContent = (sections.summary && sections.summary.trim()) || (DB.currentUser && DB.currentUser.summary ? DB.currentUser.summary : 'Not detected');

  const eduSummaryEl = document.getElementById('profile-education');
  if (eduSummaryEl) {
    let eduText = 'Not detected';
    if (intel.education && intel.education.length > 0) {
      const e = intel.education[0];
      eduText = `${e.degree || ''} · ${e.institution || ''}`.replace(/^[\s·]+|[\s·]+$/g, '') || 'Not detected';
    } else if (sections.education && sections.education.trim()) {
      eduText = sections.education.trim().slice(0, 100);
    }
    eduSummaryEl.textContent = eduText;
  }

  const linkEl = document.getElementById('profile-linkedin');
  if (linkEl) {
    const lurl = contact.linkedin || (DB.currentUser ? DB.currentUser.linkedin : '');
    if (lurl) {
      linkEl.innerHTML = `<a href="${escapeHTML(lurl)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">${escapeHTML(lurl)}</a>`;
    } else {
      linkEl.textContent = 'Not detected';
    }
  }

  const gitEl = document.getElementById('profile-github');
  if (gitEl) {
    const gurl = contact.github || (DB.currentUser ? DB.currentUser.github : '');
    if (gurl) {
      gitEl.innerHTML = `<a href="${escapeHTML(gurl)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">${escapeHTML(gurl)}</a>`;
    } else {
      gitEl.textContent = 'Not detected';
    }
  }

  // 2. Technical Skills Cloud
  const skillsCloud = document.getElementById('profile-skills-tech');
  if (skillsCloud) {
    const rawSkills = intel.skills || (DB.currentUser && DB.currentUser.skills ? DB.currentUser.skills.split(',') : []);
    const skillList = rawSkills.map(s => (typeof s === 'object' && s !== null) ? (s.canonical || s.name || s.raw || '') : String(s)).filter(Boolean);
    if (skillList.length) {
      skillsCloud.innerHTML = skillList.map(s => `<span class="skill-tag skill-matched">${escapeHTML(s)}</span>`).join('');
    } else {
      skillsCloud.innerHTML = '<span class="text-muted text-sm">No skills detected</span>';
    }
  }

  // 3. Work Experience Timeline
  const expList = document.getElementById('profile-experience-list');
  const expBadge = document.getElementById('profile-exp-badge');
  const expEntries = Array.isArray(intel.experience) ? intel.experience : [];
  const totalYears = intel.total_experience_years !== undefined ? intel.total_experience_years : (expEntries.length ? expEntries.length : 0);

  if (expBadge) {
    expBadge.textContent = totalYears > 0 ? `${totalYears} Years` : (expEntries.length ? `${expEntries.length} Roles` : '0 Years');
  }

  if (expList) {
    if (expEntries.length > 0) {
      expList.innerHTML = expEntries.map(e => `
        <div style="padding:14px;background:var(--bg);border-radius:10px;margin-bottom:12px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
            <div>
              <div style="font-weight:700;font-size:15px;color:var(--text-1)">${escapeHTML(e.job_title || e.title || 'Role')}</div>
              <div style="font-size:13px;color:var(--primary);font-weight:600">${escapeHTML(e.company || 'Company')}</div>
            </div>
            <div style="text-align:right">
              <span class="badge badge-gray" style="font-size:11px">${escapeHTML(e.duration_str || e.dates || e.duration || 'Duration not specified')}</span>
            </div>
          </div>
          ${e.description ? `<p style="margin-top:8px;font-size:13px;color:var(--text-2);line-height:1.5">${escapeHTML(e.description)}</p>` : ''}
        </div>
      `).join('');
    } else {
      expList.innerHTML = '<p class="text-muted text-sm" style="padding:8px">No work experience detected in resume.</p>';
    }
  }

  // 4. Education Credentials
  const eduList = document.getElementById('profile-education-list');
  const eduEntries = Array.isArray(intel.education) ? intel.education : [];
  if (eduList) {
    if (eduEntries.length > 0) {
      eduList.innerHTML = eduEntries.map(e => `
        <div style="padding:14px;background:var(--bg);border-radius:10px;margin-bottom:12px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
            <div>
              <div style="font-weight:700;font-size:15px;color:var(--text-1)">${escapeHTML(e.degree || 'Degree / Credential')}</div>
              <div style="font-size:13px;color:var(--teal-d);font-weight:600">${escapeHTML(e.institution || e.university || e.school || 'Institution')}</div>
            </div>
            <div style="text-align:right">
              ${e.year || e.graduation_year ? `<span class="badge badge-gray" style="font-size:11px">${escapeHTML(String(e.year || e.graduation_year))}</span>` : ''}
              ${e.gpa || e.cgpa ? `<span class="badge badge-success" style="font-size:11px;margin-left:4px">GPA: ${escapeHTML(String(e.gpa || e.cgpa))}</span>` : ''}
            </div>
          </div>
        </div>
      `).join('');
    } else {
      eduList.innerHTML = '<p class="text-muted text-sm" style="padding:8px">No formal education records detected in resume.</p>';
    }
  }

  // 5. Resume Quality Breakdown
  const qBreakdown = document.getElementById('profile-quality-breakdown');
  const qBadge = document.getElementById('profile-quality-score');
  const quality = intel.quality || {};
  const qScore = quality.quality_score !== undefined ? quality.quality_score : (resumeMeta.ats_score || 0);

  if (qBadge) {
    qBadge.textContent = `Quality Score: ${qScore}/100`;
  }

  if (qBreakdown) {
    const coverage = quality.section_coverage || {};
    const readability = quality.readability || {};
    const contactComp = quality.contact_completeness || {};
    const lengthInfo = quality.resume_length || {};
    const missingSec = quality.missing_sections || [];

    qBreakdown.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:16px">
        <div style="padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase">Section Coverage</div>
          <div style="font-size:18px;font-weight:800;color:var(--primary);margin-top:4px">${coverage.present || 0} / ${coverage.expected || 8} Sections</div>
          <div style="font-size:11px;color:var(--text-2);margin-top:2px">${Math.round(coverage.percentage || 0)}% completed</div>
        </div>
        <div style="padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase">Contact Completeness</div>
          <div style="font-size:18px;font-weight:800;color:#10b981;margin-top:4px">${contactComp.score || 0} / 100</div>
          <div style="font-size:11px;color:var(--text-2);margin-top:2px">${(contactComp.missing_fields || []).length === 0 ? 'All contact fields present' : 'Missing: ' + (contactComp.missing_fields || []).join(', ')}</div>
        </div>
        <div style="padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase">Readability</div>
          <div style="font-size:18px;font-weight:800;color:#8b5cf6;margin-top:4px">${readability.score || 0} / 100</div>
          <div style="font-size:11px;color:var(--text-2);margin-top:2px">Avg ${Math.round(readability.average_sentence_words || 0)} words/sentence</div>
        </div>
        <div style="padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase">Word Count</div>
          <div style="font-size:18px;font-weight:800;color:#f59e0b;margin-top:4px">${lengthInfo.word_count || 0} Words</div>
          <div style="font-size:11px;color:var(--text-2);margin-top:2px">Status: ${escapeHTML(lengthInfo.length_status || 'normal')}</div>
        </div>
      </div>
      ${missingSec.length ? `
        <div style="padding:12px 16px;background:rgba(220,38,38,0.05);border-left:3px solid #dc2626;border-radius:6px;">
          <strong style="color:#dc2626;font-size:12px;">Suggested Improvements:</strong>
          <span style="font-size:12px;color:var(--text-2);margin-left:6px;">Consider adding sections for: <em>${escapeHTML(missingSec.join(', '))}</em> to improve recruiter visibility.</span>
        </div>
      ` : ''}
    `;
  }
}



// ── ML Pipeline Status ──────────────────────────────────
function loadMLPipelineStatus() {
  if (DB.currentUser && DB.currentUser.role !== 'admin') {
    console.warn('Unauthorized access to ML Pipeline status');
    return;
  }
  const btn = document.getElementById('pipeline-refresh-btn');
  if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...'; }

  fetch('/api/ml/status')
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(data => {
      // Pipeline Status
      const isReady = data.status === 'ready';
      setEl('ml-pipeline-status', isReady ? '● Online' : '○ Not Trained');
      const statusEl = document.getElementById('ml-pipeline-status');
      if(statusEl) statusEl.style.color = isReady ? '#16a34a' : '#dc2626';
      setEl('ml-pipeline-status-sub', isReady ? 'All models loaded & operational' : 'Run training to activate');

      // TF-IDF Model
      const tfidf = data.models?.tfidf_recommender || {};
      setEl('ml-vocab-size', tfidf.vocab_size ? tfidf.vocab_size.toLocaleString() : '--');
      setEl('ml-tfidf-vocab', tfidf.vocab_size ? `${tfidf.vocab_size.toLocaleString()} terms` : '--');
      setEl('ml-corpus-size', tfidf.corpus_size || '--');
      setEl('ml-corpus-detail', `${tfidf.corpus_size || '800'} documents trained on`);
      setEl('ml-tfidf-corpus', `${tfidf.corpus_size || '--'} docs (resumes + job descriptions)`);

      const tfidfBadge = document.getElementById('ml-tfidf-badge');
      if(tfidfBadge) {
        tfidfBadge.className = tfidf.trained ? 'badge badge-success' : 'badge badge-danger';
        tfidfBadge.textContent = tfidf.trained ? '✓ Trained' : '✗ Not Trained';
      }

      // Hit rates
      const hr = tfidf.hit_rate || {};
      setEl('ml-tfidf-hit1', hr.hit_rate_top1 != null ? `${(hr.hit_rate_top1 * 100).toFixed(0)}%` : '--');
      setEl('ml-tfidf-hit3', hr.hit_rate_top3 != null ? `${(hr.hit_rate_top3 * 100).toFixed(0)}%` : '--');
      setEl('ml-tfidf-hit5', hr.hit_rate_top5 != null ? `${(hr.hit_rate_top5 * 100).toFixed(0)}%` : '--');
      setEl('ml-hit-rate', hr.hit_rate_top5 != null ? `${(hr.hit_rate_top5 * 100).toFixed(0)}%` : '--');

      // spaCy NER Model
      const ner = data.models?.spacy_ner || {};
      const nerBadge = document.getElementById('ml-ner-badge');
      if(nerBadge) {
        nerBadge.className = ner.trained ? 'badge badge-success' : 'badge badge-danger';
        nerBadge.textContent = ner.trained ? '✓ Trained' : '✗ Not Trained';
      }
      setEl('ml-ner-f1', ner.best_f1 != null ? `${(ner.best_f1 * 100).toFixed(1)}%` : '--');
      setEl('ml-ner-epochs', ner.epochs || '--');
      setEl('ml-ner-method', data.extraction_method || 'spaCy NER + Regex');
      setEl('ml-extraction-method', data.extraction_method || 'spaCy NER + Regex');

      // Dataset info
      const ds = data.dataset || {};
      setEl('ml-dataset-resumes', ds.num_resumes || '600');
      setEl('ml-dataset-jobs', ds.num_jobs || '200');
      setEl('ml-dataset-ner', ds.num_ner_samples || '~4,800');

      // Live jobs count from DB
      fetch('/api/admin/jobs').then(r=>r.json()).then(jobs => {
        setEl('ml-live-jobs', (jobs && jobs.length) || '--');
      }).catch(() => {});

      if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Status'; }
    })
    .catch(err => {
      console.error('ML Pipeline status error:', err);
      setEl('ml-pipeline-status', '● Error');
      if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Status'; }
    });
}


function fetchCandidateProfile(userId) {
  fetch(`/api/users/${userId}/profile`).then(r=>r.json()).then(d=>{
    setEl('profile-name', d.name || '-');
    setEl('profile-email', d.email || '-');
    setEl('profile-phone', d.phone || '-');
    setEl('profile-linkedin', d.linkedin || '-');
    setEl('profile-github', d.github || '-');
    setEl('profile-education', d.education || '-');
    setEl('profile-summary', d.summary || '-');
    setEl('profile-location', d.location || '-');

    const skillsTech = document.getElementById('profile-skills-tech');
    if (skillsTech && d.skills) {
      const skillsArray = d.skills.split(',').filter(s => s.trim() !== '');
      skillsTech.innerHTML = skillsArray.map(s => `<span class="skill-tag skill-neutral">${s.trim()}</span>`).join('');
    }
  });
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if(el) el.textContent = val;
}

function updateSidebarBadges() {
  const cNotifs = DB.notifications ? DB.notifications.filter(n=>n.unread).length : 0;
  const upd = (id, count) => {
    const el = document.getElementById(id);
    if(el) {
      el.textContent = count;
      el.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  };

  // HR Admin Badges
  upd('badge-admin-candidates', DB.candidates ? DB.candidates.length : 0);
  upd('badge-admin-jobs', DB.jobs ? DB.jobs.length : 0);
  upd('badge-admin-notifs', cNotifs);

  // Candidate Badges
  const score = DB.currentUser ? (DB.currentUser.ats_score || 0) : 0;
  upd('badge-cand-upload', score > 0 ? 0 : 1);
  const totalJobs = DB.jobs ? DB.jobs.length : 0;
  upd('badge-cand-jobs', totalJobs);
  upd('badge-cand-notifs', cNotifs);

  // Buttons Logic
  const btnJobs = document.getElementById('ats-btn-jobs');
  if(btnJobs) { btnJobs.innerHTML = `<i class="fas fa-briefcase"></i> View Job Matches (${totalJobs})`; }
  
  const notifDots = document.querySelectorAll('.notif-dot');
  notifDots.forEach(dot => { dot.style.display = cNotifs > 0 ? 'block' : 'none'; });
}

// ── DOMContentLoaded ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Router.go('landing');
  if (DB.currentUser) {
    fetchJobsFromServer();
    if (DB.currentUser.role === 'hr') {
      fetchCandidatesFromServer();
      fetchAdminStats();
    }
  }
  UI.renderNotifications('cand');
  UI.renderNotifications('admin');
  // Fetch and display real landing stats
  fetch('/api/auth/landing_stats').then(r => r.json()).then(d => {
    const rEl = document.getElementById('hero-stat-resumes');
    const jEl = document.getElementById('hero-stat-jobs');
    if (rEl) rEl.textContent = d.resumes_analyzed > 0 ? d.resumes_analyzed + '+' : '12+';
    if (jEl) jEl.textContent = d.jobs_matched > 0 ? d.jobs_matched + '+' : '10+';
  }).catch(() => {});
  
  // Lightweight auto-refresh every 2 min (only stats, NOT the heavy ML pipeline)
  setInterval(() => {
    if (document.hidden) return;  // Don't poll when tab is in background
    if (DB.currentUser?.role === 'hr') {
      fetchAdminStats();
      fetchCandidatesFromServer();
    }
  }, 120000);

  // Bind settings toggles
  ['email','sms','jobs','profile'].forEach(key => {
    const el = document.getElementById(`toggle-${key}`);
    if (el) el.checked = DB.settings[key === 'email' ? 'emailNotif' : key === 'sms' ? 'smsNotif' : key === 'jobs' ? 'jobAlerts' : 'profileVisible'];
  });

  // ATS score SVG animations
  animateATSRings();

  // Close modal on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) m.classList.remove('show'); });
  });

  // Candidate tab filter
  document.querySelectorAll('[data-tabgroup="cand-filter"]').forEach(btn => {
    btn.addEventListener('click', function() {
      switchTab(this, 'cand-filter');
      const filter = this.dataset.filter || 'All';
      UI.renderCandidatesTable(filter);
    });
  });
});

// ── Mobile Landing Menu ──────────────────────────────────────
function toggleMobileMenu() {
  const menu = document.getElementById('land-mobile-menu');
  if (!menu) return;
  menu.classList.toggle('open');
  document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
}

function closeMobileMenuAndScroll(sectionId) {
  toggleMobileMenu();
  setTimeout(() => {
    const el = document.getElementById(sectionId);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, 200);
}

function animateATSRings() {
  // Animate all SVG score rings
  document.querySelectorAll('.animated-ring').forEach(ring => {
    const score = parseInt(ring.dataset.score || 78);
    const r = 54;
    const circum = 2 * Math.PI * r;
    const fill = ring.querySelector('.ring-fill');
    if (fill) {
      fill.style.strokeDasharray = circum;
      fill.style.strokeDashoffset = circum;
      setTimeout(() => {
        fill.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)';
        fill.style.strokeDashoffset = circum * (1 - score/100);
      }, 300);
    }
  });
}

// Global expose for inline handlers
window.Router    = Router;
window.Auth      = Auth;
window.Toast     = Toast;
window.Modal     = Modal;
window.Sidebar   = Sidebar;
window.UI        = UI;
window.Charts    = Charts;
window.switchTab = switchTab;
window.applyJob  = applyJob;
window.editJob   = editJob;
window.saveEditJob = saveEditJob;
window.deleteJob = deleteJob;
window.postJob   = postJob;
window.viewCandidate = viewCandidate;
window.viewJobRankings = viewJobRankings;
window.exportCSV = exportCSV;
window.searchCandidates = searchCandidates;
window.filterJobs = filterJobs;
window.resetFilters = resetFilters;
window.saveProfile = saveProfile;
window.changePwd = changePwd;
window.saveSettings = saveSettings;
window.markAllRead = markAllRead;
window.resumeUpload = resumeUpload;
window.handleDrop = handleDrop;
window.topbarSearch = topbarSearch;
window.updateCandidateStatus = updateCandidateStatus;
window.animateATSRings = animateATSRings;
window.fetchJobsFromServer = fetchJobsFromServer;
window.fetchCandidatesFromServer = fetchCandidatesFromServer;
window.fetchAdminStats = fetchAdminStats;
window.fetchNotificationsFromServer = fetchNotificationsFromServer;
window.fetchCandidateStats = fetchCandidateStats;
window.setEl = setEl;
window.switchSettingTab = switchSettingTab;
window.switchCandSettingTab = switchCandSettingTab;
window.saveCandidateSettings = saveCandidateSettings;
window.loadCandidateSettings = loadCandidateSettings;
window.exportCandidateProfileData = exportCandidateProfileData;
window.toggleDarkMode = toggleDarkMode;
window.toggleMobileMenu = toggleMobileMenu;
window.closeMobileMenuAndScroll = closeMobileMenuAndScroll;
window.viewMatchedJobs = viewMatchedJobs;
window.triggerReupload = triggerReupload;
window.fetchJobs = fetchJobs;
window.renderDashboardTopJobs = renderDashboardTopJobs;
window.LiveJobsManager = LiveJobsManager;
window.handleMainSearchInput = handleMainSearchInput;
window.handleLocationInput = handleLocationInput;
window.triggerSearch = triggerSearch;
window.handleDropdownFilterChange = handleDropdownFilterChange;
window.resetLiveFilters = resetLiveFilters;
window.removeLiveFilterChip = removeLiveFilterChip;
window.changeLiveJobsPage = changeLiveJobsPage;
window.handleHeaderSearchInput = handleHeaderSearchInput;
window.handleHeaderSearchEnter = handleHeaderSearchEnter;
window.highlightText = highlightText;

// ── Cluster View Renderer ─────────────────────────────────────────────────
function renderClusterView() {
  const container = document.getElementById('cluster-view-container');
  if (!container || !DB.candidates) return;

  // Group candidates by cluster label
  const groups = {};
  DB.candidates.forEach(c => {
    const label = c.cluster_label || 'Unclustered';
    if (!groups[label]) groups[label] = [];
    groups[label].push(c);
  });

  // Sort each group by ATS score desc
  Object.values(groups).forEach(g => g.sort((a, b) => b.ats - a.ats));

  const clusterColors = {
    'Python / Data Science':  '#2563eb',
    'Frontend / UI Developer':'#7c3aed',
    'DevOps / Cloud Engineer':'#059669',
    'Java / Backend Developer':'#b45309',
    'Database / Data Engineer':'#0891b2',
    'Mobile Developer':        '#db2777',
    'General / Mixed Skills':  '#6b7280',
    'Unclustered':             '#9ca3af'
  };

  container.innerHTML = Object.entries(groups).map(([label, members]) => {
    const cleanLabel = label.replace(/[\u{1F000}-\u{1FFFF}]/gu, '').trim();
    const color = Object.entries(clusterColors).find(([k]) => cleanLabel.includes(k.split('/')[0].trim()))?.[1] || '#6b7280';
    const flagged = members.filter(c => c.outlier_flag).length;

    return `
      <div class="card" style="margin-bottom:18px;border-left:4px solid ${color}">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
          <div style="display:flex;align-items:center;gap:10px">
            <div style="width:10px;height:10px;border-radius:50%;background:${color}"></div>
            <span style="font-weight:700;font-size:15px">${label}</span>
            <span style="background:#f1f5f9;color:#64748b;font-size:12px;padding:2px 10px;border-radius:12px">${members.length} candidates</span>
            ${flagged > 0 ? `<span style="background:#fee2e2;color:#dc2626;font-size:11px;padding:2px 8px;border-radius:12px;font-weight:600">\u26a0\ufe0f ${flagged} flagged</span>` : ''}
          </div>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:10px">
          ${members.map(c => `
            <div style="display:flex;align-items:center;gap:8px;background:${c.outlier_flag?'#fff5f5':'var(--bg-2)'};border:1px solid ${c.outlier_flag?'#fca5a5':'var(--border)'};border-radius:8px;padding:8px 12px;min-width:200px;flex:1">
              <div class="avatar avatar-sm" style="background:${UI.avatarColor(c.name)};color:#fff;flex-shrink:0">${c.name.slice(0,2).toUpperCase()}</div>
              <div style="min-width:0">
                <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${c.name}</div>
                <div style="font-size:11px;color:var(--text-3)">${c.job}</div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
                  <span class="badge ${UI.atsBadge(c.ats)}" style="font-size:10px">${c.ats}/100</span>
                  ${c.outlier_flag ? '<span style="font-size:10px;color:#dc2626;font-weight:700">\u26a0\ufe0f</span>' : ''}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>`;
  }).join('') || '<div style="text-align:center;padding:40px;color:var(--text-3)">No candidates to cluster yet.</div>';
}
window.renderClusterView = renderClusterView;

// ── Global Talent Pool Management (GAP-10) ───────────────────
let _talentPoolTimer = null;
function onTalentPoolSearch(val) {
  clearTimeout(_talentPoolTimer);
  _talentPoolTimer = setTimeout(() => {
    fetchTalentPool(val);
  }, 300);
}

function fetchTalentPool(query = '') {
  const tbody = document.getElementById('talentpool-tbody');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:36px;color:var(--text-3)"><i class="fas fa-spinner fa-spin fa-2x" style="margin-bottom:10px;display:block"></i>Loading talent pool...</td></tr>';
  }

  const url = query ? `/api/admin/talent_pool?q=${encodeURIComponent(query)}` : '/api/admin/talent_pool';
  fetch(url)
    .then(r => r.json())
    .then(data => {
      if (!data || !data.success) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:36px;color:var(--danger)"><i class="fas fa-exclamation-triangle fa-2x" style="margin-bottom:10px;display:block"></i>Unable to load talent pool.</td></tr>';
        return;
      }
      DB.talentPool = data.candidates || [];
      const totalCount = data.total !== undefined ? data.total : DB.talentPool.length;

      const countEl = document.getElementById('talentpool-total-count');
      if (countEl) countEl.textContent = totalCount;
      const badgeEl = document.getElementById('badge-admin-talentpool');
      if (badgeEl) {
        badgeEl.textContent = totalCount;
        badgeEl.style.display = totalCount > 0 ? 'inline-block' : 'none';
      }

      renderTalentPoolTable();
    })
    .catch(err => {
      console.error("Failed to load talent pool:", err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:36px;color:var(--danger)"><i class="fas fa-exclamation-triangle fa-2x" style="margin-bottom:10px;display:block"></i>Network failure connecting to talent pool.</td></tr>';
    });
}

function renderTalentPoolTable() {
  const tbody = document.getElementById('talentpool-tbody');
  if (!tbody) return;

  if (!DB.talentPool || DB.talentPool.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:36px;color:var(--text-3)"><i class="fas fa-users-slash fa-2x" style="margin-bottom:10px;display:block"></i>No candidates found in Talent Pool.</td></tr>';
    return;
  }

  tbody.innerHTML = DB.talentPool.map(c => {
    const avatar = (c.name || '??').slice(0, 2).toUpperCase();
    const bg = UI.avatarColor(c.name || '');
    const skillsList = Array.isArray(c.skills) ? c.skills : [];
    const skillsHtml = skillsList.length
      ? skillsList.slice(0, 4).map(s => `<span class="skill-tag skill-neutral" style="font-size:11px;padding:2px 8px">${escapeHTML(s)}</span>`).join('') + (skillsList.length > 4 ? ` <span style="font-size:11px;color:var(--text-3)">+${skillsList.length - 4}</span>` : '')
      : '<span class="text-muted text-sm">No skills</span>';

    const atsScore = c.ats_score || 0;
    const atsClass = atsScore >= 75 ? 'badge-success' : (atsScore >= 50 ? 'badge-warning' : 'badge-gray');
    const appsCount = c.application_count || 0;
    const appsBadge = appsCount > 0
      ? `<span class="badge badge-primary" style="font-size:11px">${appsCount} applied</span>`
      : `<span class="badge badge-gray" style="font-size:11px">0 applied</span>`;

    const resumeHtml = c.resume_id
      ? `<div style="display:flex;gap:4px">
          ${(c.resume_mime === 'application/pdf' || (c.resume_name && c.resume_name.endsWith('.pdf')))
            ? `<a href="/api/resume/download/${c.resume_id}?preview=1" target="_blank" class="btn btn-xs btn-outline" title="Preview Resume"><i class="fas fa-eye"></i></a>`
            : ''}
          <a href="/api/resume/download/${c.resume_id}" class="btn btn-xs btn-navy" title="Download Resume"><i class="fas fa-download"></i></a>
        </div>`
      : '<span class="badge badge-gray" style="font-size:11px">No resume</span>';

    return `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:10px">
            <div class="avatar avatar-sm" style="background:${bg};color:#fff;flex-shrink:0">${escapeHTML(avatar)}</div>
            <div>
              <div style="font-weight:600;font-size:13px;color:var(--text-1)">${escapeHTML(c.name)}</div>
              <div style="font-size:11px;color:var(--text-3)">${escapeHTML(c.email)}</div>
            </div>
          </div>
        </td>
        <td style="font-size:13px;color:var(--text-2)">${escapeHTML(c.degree || 'Not detected')}</td>
        <td style="font-size:13px"><span class="badge badge-gray">${escapeHTML(c.exp || '0 yrs')}</span></td>
        <td><div class="skills-cloud" style="margin:0">${skillsHtml}</div></td>
        <td><span class="badge ${atsClass}">${atsScore}/100</span></td>
        <td>${resumeHtml}</td>
        <td>${appsBadge}</td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="viewTalentCandidate(${c.candidate_id})">
            <i class="fas fa-user"></i> View Profile
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function viewTalentCandidate(candidateId) {
  const c = (DB.talentPool || []).find(x => x.candidate_id === candidateId);
  if (!c) return;

  const avatarEl = document.getElementById('modal-cand-avatar');
  if (avatarEl) {
    avatarEl.textContent = (c.name || '??').slice(0, 2).toUpperCase();
    avatarEl.style.background = UI.avatarColor(c.name || '');
  }

  document.getElementById('modal-cand-name').textContent    = c.name || '';
  document.getElementById('modal-cand-email').textContent   = c.email || '';

  const phoneEl = document.getElementById('modal-cand-phone');
  if (phoneEl) phoneEl.textContent = c.phone || 'Not provided';

  const locEl = document.getElementById('modal-cand-loc');
  if (locEl) locEl.textContent = c.location || 'Not provided';

  const linksEl = document.getElementById('modal-cand-links');
  if (linksEl) {
    const links = [];
    if (c.linkedin) links.push(`<a href="${escapeHTML(c.linkedin)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">LinkedIn</a>`);
    if (c.github) links.push(`<a href="${escapeHTML(c.github)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">GitHub</a>`);
    linksEl.innerHTML = links.length ? links.join(' · ') : 'None';
  }

  document.getElementById('modal-cand-degree').textContent  = c.degree || 'Not detected';
  document.getElementById('modal-cand-job').textContent     = `Talent Pool (${c.application_count || 0} active applications)`;
  document.getElementById('modal-cand-exp').textContent     = c.exp || 'Not detected';
  document.getElementById('modal-cand-ats').textContent     = (c.ats_score || 0) + '/100';
  document.getElementById('modal-cand-match').textContent   = 'N/A';
  document.getElementById('modal-cand-status').innerHTML    = '<span class="badge badge-teal">Talent Pool</span>';

  const skillsList = Array.isArray(c.skills) ? c.skills : [];
  document.getElementById('modal-cand-skills').innerHTML    = skillsList.length
    ? skillsList.map(s => `<span class="skill-tag skill-neutral">${escapeHTML(s)}</span>`).join('')
    : '<span class="text-muted text-sm">No skills extracted yet</span>';

  const resNameEl = document.getElementById('modal-cand-resume-name');
  if (resNameEl) resNameEl.textContent = c.resume_name || 'None attached';

  // Wire Download and Preview buttons
  const dlBtn = document.getElementById('modal-btn-download');
  const prevBtn = document.getElementById('modal-btn-preview');
  if (c.resume_id) {
    if (dlBtn) {
      dlBtn.style.display = 'inline-flex';
      dlBtn.href = `/api/resume/download/${c.resume_id}`;
    }
    if (prevBtn) {
      const isPdf = (c.resume_mime === 'application/pdf' || (c.resume_name && c.resume_name.toLowerCase().endsWith('.pdf')));
      if (isPdf) {
        prevBtn.style.display = 'inline-flex';
        prevBtn.href = `/api/resume/download/${c.resume_id}?preview=1`;
      } else {
        prevBtn.style.display = 'none';
      }
    }
  } else {
    if (dlBtn) dlBtn.style.display = 'none';
    if (prevBtn) prevBtn.style.display = 'none';
  }

  // Hide application shortlist/reject buttons for talent pool view (no active application to shortlist/reject)
  const btnShortlist = document.getElementById('modal-btn-shortlist');
  const btnReject    = document.getElementById('modal-btn-reject');
  if (btnShortlist) btnShortlist.style.display = 'none';
  if (btnReject)    btnReject.style.display = 'none';

  Modal.open('view-cand-modal');
}

function exportTalentPoolCSV() {
  const searchInput = document.getElementById('talentpool-search-input');
  const q = searchInput ? searchInput.value.trim() : '';
  const url = q ? `/api/admin/talent_pool/export?q=${encodeURIComponent(q)}` : '/api/admin/talent_pool/export';

  Toast.show('Generating Talent Pool CSV export...', 'info');
  fetch(url)
    .then(res => {
      if (!res.ok) {
        if (res.status === 401) {
          Toast.show('Please log in to export.', 'danger');
        } else if (res.status === 403) {
          Toast.show('Unauthorized: Only HR and Admin can export talent pool.', 'danger');
        } else {
          Toast.show('Failed to export talent pool.', 'danger');
        }
        throw new Error('Export failed with status ' + res.status);
      }
      return res.blob();
    })
    .then(blob => {
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const today = new Date().toISOString().slice(0, 10);
      a.download = `TalentSync_Talent_Pool_${today}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      Toast.show('Talent Pool exported to CSV! 📥', 'success');
    })
    .catch(err => {
      console.error('CSV export error:', err);
    });
}

window.fetchTalentPool       = fetchTalentPool;
window.renderTalentPoolTable = renderTalentPoolTable;
window.viewTalentCandidate   = viewTalentCandidate;
window.onTalentPoolSearch    = onTalentPoolSearch;
window.exportTalentPoolCSV   = exportTalentPoolCSV;


// ============================================================
// PLATFORM ADMIN PORTAL
// Centralized Administrative Control Layer (6 Core Sections)
// ============================================================

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = (val !== null && val !== undefined) ? String(val) : '--';
}

const PlatformAdminState = {
  // Section 2: Users
  usersPage: 1,
  usersTotalPages: 1,
  selectedUser: null,
  // Section 3: Jobs & Applications
  jobsPage: 1,
  jobsTotalPages: 1,
  selectedJob: null,
  appsPage: 1,
  appsTotalPages: 1,
  selectedApp: null,
  // Section 4: Resumes
  resumesPage: 1,
  resumesTotalPages: 1,
  selectedResume: null,
  // Section 5: Security & Audit
  loginsPage: 1,
  loginsTotalPages: 1,
  auditPage: 1,
  auditTotalPages: 1,
  // Cache
  analyticsCache: null
};

// ── Sub-Tab Switchers ────────────────────────────────────────

function switchPaJobsAppsTab(tab) {
  const btnJobs = document.getElementById('pa-tab-btn-jobs');
  const btnApps = document.getElementById('pa-tab-btn-apps');
  const contentJobs = document.getElementById('pa-content-jobs');
  const contentApps = document.getElementById('pa-content-applications');
  if (tab === 'jobs') {
    if (btnJobs) btnJobs.classList.add('active');
    if (btnApps) btnApps.classList.remove('active');
    if (contentJobs) contentJobs.classList.remove('hidden');
    if (contentApps) contentApps.classList.add('hidden');
    fetchPlatformAdminJobs(PlatformAdminState.jobsPage || 1);
  } else {
    if (btnJobs) btnJobs.classList.remove('active');
    if (btnApps) btnApps.classList.add('active');
    if (contentJobs) contentJobs.classList.add('hidden');
    if (contentApps) contentApps.classList.remove('hidden');
    fetchPlatformAdminApplications(PlatformAdminState.appsPage || 1);
  }
}

function switchPaSecAuditTab(tab) {
  const btnSec = document.getElementById('pa-tab-btn-security');
  const btnAudit = document.getElementById('pa-tab-btn-audit');
  const contentSec = document.getElementById('pa-content-security');
  const contentAudit = document.getElementById('pa-content-audit');
  if (tab === 'security') {
    if (btnSec) btnSec.classList.add('active');
    if (btnAudit) btnAudit.classList.remove('active');
    if (contentSec) contentSec.classList.remove('hidden');
    if (contentAudit) contentAudit.classList.add('hidden');
    fetchPlatformAdminSecurity();
  } else {
    if (btnSec) btnSec.classList.remove('active');
    if (btnAudit) btnAudit.classList.add('active');
    if (contentSec) contentSec.classList.add('hidden');
    if (contentAudit) contentAudit.classList.remove('hidden');
    fetchPlatformAdminAudit(PlatformAdminState.auditPage || 1);
  }
}

function switchPaSystemTab(tab) {
  const btnHealth = document.getElementById('pa-tab-btn-health');
  const btnInteg = document.getElementById('pa-tab-btn-integrations');
  const contentHealth = document.getElementById('pa-content-system-health');
  const contentInteg = document.getElementById('pa-content-system-integrations');
  if (tab === 'health') {
    if (btnHealth) btnHealth.classList.add('active');
    if (btnInteg) btnInteg.classList.remove('active');
    if (contentHealth) contentHealth.classList.remove('hidden');
    if (contentInteg) contentInteg.classList.add('hidden');
    fetchPlatformAdminSystemHealth();
  } else {
    if (btnHealth) btnHealth.classList.remove('active');
    if (btnInteg) btnInteg.classList.add('active');
    if (contentHealth) contentHealth.classList.add('hidden');
    if (contentInteg) contentInteg.classList.remove('hidden');
    fetchPlatformAdminIntegrations();
  }
}

// ═══════════════════════════════════════════════════════════
// SECTION 1: DASHBOARD
// ═══════════════════════════════════════════════════════════

function fetchPlatformAdminAnalytics() {
  fetch('/api/platform-admin/analytics')
    .then(r => {
      if (r.status === 401 || r.status === 403) {
        Toast.show('Administrative access denied.', 'error');
        throw new Error('Unauthorized');
      }
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) return;
      const data = res.data;
      PlatformAdminState.analyticsCache = data;

      // 1. Dynamic KPIs
      setEl('pa-stat-total-users', data.users.total);
      setEl('pa-stat-roles-sub', `Candidates: ${data.users.by_role.candidate || 0} | HR: ${data.users.by_role.hr || 0} | Admins: ${data.users.by_role.admin || 0}`);

      setEl('pa-stat-active-users', data.users.active);
      setEl('pa-stat-users-sub', `Active: ${data.users.active} | Inactive: ${data.users.inactive}`);

      setEl('pa-stat-total-jobs', data.jobs.total);
      setEl('pa-stat-jobs-sub', `Active: ${data.jobs.active} | Closed: ${data.jobs.closed}`);

      setEl('pa-stat-total-apps', data.applications.total);
      setEl('pa-stat-apps-sub', `Reviewing: ${data.applications.reviewing} | Shortlisted: ${data.applications.shortlisted}`);

      if (data.resumes) {
        setEl('pa-stat-total-resumes', data.resumes.total);
        setEl('pa-stat-resumes-sub', `Processed: ${data.resumes.processed} | Pending: ${data.resumes.pending} | Failed: ${data.resumes.failed}`);
      }

      setEl('pa-stat-avg-ats', `${data.ats.average}/100`);
      setEl('pa-stat-ats-sub', `Scored Candidates: ${data.ats.total_candidates_scored}`);

      // 2. Render Charts
      // Users by Role
      Charts.create('pa-role-chart', {
        type: 'doughnut',
        data: {
          labels: ['Candidate', 'HR / Recruiter', 'Platform Admin'],
          datasets: [{
            data: [
              data.users.by_role.candidate || 0,
              data.users.by_role.hr || 0,
              data.users.by_role.admin || 0
            ],
            backgroundColor: ['#2563eb', '#10b981', '#6366f1'],
            borderWidth: 3,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { font: { family: 'DM Sans', size: 12 }, padding: 12 } }
          },
          cutout: '62%'
        }
      });

      // Recruitment Funnel
      Charts.create('pa-funnel-chart', {
        type: 'bar',
        data: {
          labels: ['Pending', 'Reviewing', 'Shortlisted', 'Rejected'],
          datasets: [{
            label: 'Applications',
            data: [
              data.applications.pending || 0,
              data.applications.reviewing || 0,
              data.applications.shortlisted || 0,
              data.applications.rejected || 0
            ],
            backgroundColor: ['#f59e0b', '#2563eb', '#10b981', '#ef4444'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: '#f0f4f9' }, ticks: { stepSize: 1 } },
            x: { grid: { display: false } }
          }
        }
      });

      // Jobs by Status
      Charts.create('pa-jobs-chart', {
        type: 'doughnut',
        data: {
          labels: ['Active', 'Closed', 'Draft'],
          datasets: [{
            data: [
              data.jobs.active || 0,
              data.jobs.closed || 0,
              data.jobs.draft || 0
            ],
            backgroundColor: ['#10b981', '#64748b', '#f59e0b'],
            borderWidth: 3,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { font: { family: 'DM Sans', size: 12 }, padding: 12 } }
          },
          cutout: '62%'
        }
      });

      // ATS Distribution
      const dist = data.ats.distribution || {};
      Charts.create('pa-ats-chart', {
        type: 'bar',
        data: {
          labels: ['0–20', '21–40', '41–60', '61–70', '71–80', '81–90', '91–100'],
          datasets: [{
            label: 'Candidates',
            data: [
              dist['0-20'] || 0,
              dist['21-40'] || 0,
              dist['41-60'] || 0,
              dist['61-70'] || 0,
              dist['71-80'] || 0,
              dist['81-90'] || 0,
              dist['91-100'] || 0
            ],
            backgroundColor: ['#fee2e2', '#fecaca', '#fed7aa', '#fef08a', '#bbf7d0', '#6ee7b7', '#00c9a7'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: '#f0f4f9' }, ticks: { stepSize: 1 } },
            x: { grid: { display: false } }
          }
        }
      });

      // 3. Load Recent System Activity
      fetchPlatformAdminRecentActivity();

      // 4. Quick probe for Health Summary Banner
      fetch('/api/platform-admin/system/health')
        .then(r => r.json())
        .then(hRes => {
          if (!hRes || !hRes.success) return;
          const h = hRes.data;
          const badge = document.getElementById('pa-dash-health-badge');
          const desc = document.getElementById('pa-dash-health-desc');
          const banner = document.getElementById('pa-dash-health-banner');
          if (badge) {
            badge.className = `badge ${h.overall === 'Healthy' ? 'badge-success' : (h.overall === 'Degraded' ? 'badge-warning' : 'badge-danger')}`;
            badge.textContent = h.overall.toUpperCase();
          }
          if (desc) {
            desc.textContent = h.overall === 'Healthy'
              ? 'All 8 core platform subsystems (Database, Storage, Auth, Parsers, ATS, Matcher) are functioning normally.'
              : `System operational state: ${h.overall}. Check Diagnostics for details.`;
          }
          if (banner) {
            banner.style.borderLeftColor = h.overall === 'Healthy' ? '#10b981' : (h.overall === 'Degraded' ? '#f59e0b' : '#ef4444');
          }
        })
        .catch(() => {});
    })
    .catch(err => {
      console.error('Error fetching Platform Admin analytics:', err);
    });
}

function getAuditSeverity(action, sourceTable) {
  const act = String(action || '').toLowerCase();
  const src = String(sourceTable || '').toLowerCase();

  // CRITICAL severity (Red)
  if (act.includes('delete') || act.includes('role') || act.includes('escalat') ||
      act.includes('deactivat') || act.includes('lockout') || act.includes('destroy') ||
      act.includes('drop') || act.includes('purge') || act.includes('revoke')) {
    return '<span class="badge badge-danger" style="font-size:11px;font-weight:700">CRITICAL</span>';
  }

  // WARNING severity (Amber / Orange)
  if (act.includes('fail') || act.includes('warn') || act.includes('outlier') ||
      act.includes('flag') || act.includes('degrad') || act.includes('attempt') ||
      act.includes('denied') || act.includes('unauthorized') || act.includes('reset')) {
    return '<span class="badge badge-warning" style="font-size:11px;font-weight:700">WARNING</span>';
  }

  // INFO severity (Teal)
  return '<span class="badge badge-teal" style="font-size:11px;font-weight:700">INFO</span>';
}

function fetchPlatformAdminRecentActivity() {
  const tbody = document.getElementById('pa-dash-activity-tbody');
  fetch('/api/platform-admin/audit?limit=6')
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success || !tbody) return;
      const events = res.data.events || [];
      if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-3)">No system events recorded yet.</td></tr>';
        return;
      }
      tbody.innerHTML = events.map(e => {
        let detailsFormatted = '';
        if (typeof e.details === 'object' && e.details !== null) {
          detailsFormatted = Object.entries(e.details).map(([k, v]) => `<strong>${escapeHTML(k)}:</strong> ${escapeHTML(String(v))}`).join(' · ');
        } else {
          detailsFormatted = escapeHTML(String(e.details || ''));
        }
        const severityBadge = getAuditSeverity(e.action, e.source_table);
        return `
          <tr>
            <td style="color:var(--text-3);font-size:12px;font-family:monospace">#${e.id}</td>
            <td>${severityBadge}</td>
            <td><span class="badge badge-primary" style="font-size:11px">${escapeHTML(e.source_table)}</span></td>
            <td style="font-size:12px;color:var(--text-3)">${e.timestamp ? new Date(e.timestamp).toLocaleString() : 'N/A'}</td>
            <td style="font-weight:600;font-size:13px">${escapeHTML(e.actor || 'System')}</td>
            <td><span class="badge badge-gray" style="font-size:11px">${escapeHTML(e.action)}</span></td>
            <td style="font-size:12px;color:var(--text-2);max-width:320px">${detailsFormatted || '<span class="text-muted">None</span>'}</td>
          </tr>
        `;
      }).join('');
    })
    .catch(() => {
      if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--danger)">Error loading activity feed.</td></tr>';
    });
}

// ═══════════════════════════════════════════════════════════
// SECTION 2: USERS
// ═══════════════════════════════════════════════════════════

function fetchPlatformAdminUsers(page = 1) {
  PlatformAdminState.usersPage = page;
  const searchInput = document.getElementById('pa-user-search');
  const roleSelect   = document.getElementById('pa-user-role-filter');
  const statusSelect = document.getElementById('pa-user-status-filter');
  const verifSelect  = document.getElementById('pa-user-verification-filter');

  const q = searchInput ? searchInput.value.trim() : '';
  const role = roleSelect ? roleSelect.value : '';
  const status = statusSelect ? statusSelect.value : '';
  const verification = verifSelect ? verifSelect.value : '';

  const tbody = document.getElementById('pa-users-table-body');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:28px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading platform users...</td></tr>';
  }

  const params = new URLSearchParams({ page: page, limit: 10 });
  if (q) params.set('search', q);
  if (role) params.set('role', role);
  if (status) params.set('status', status);
  if (verification) params.set('verification', verification);

  fetch(`/api/platform-admin/users?${params.toString()}`)
    .then(r => {
      if (r.status === 401 || r.status === 403) throw new Error('Unauthorized');
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--danger)">${res ? res.message : 'Failed to load users'}</td></tr>`;
        return;
      }

      const users = res.data.users || [];
      const pagination = res.data.pagination;
      PlatformAdminState.usersTotalPages = pagination.pages || 1;

      setEl('pa-users-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Total Users)`);
      const prevBtn = document.getElementById('pa-users-prev-btn');
      const nextBtn = document.getElementById('pa-users-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (users.length === 0) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-user-slash" style="font-size:24px;margin-bottom:8px;display:block"></i>No users found matching current filters.</td></tr>';
        return;
      }

      if (tbody) {
        tbody.innerHTML = users.map(u => {
          const avatar = (u.name || '??').slice(0, 2).toUpperCase();
          const bg = UI.avatarColor(u.name || '');
          const roleBadgeColor = u.role === 'admin' ? 'badge-primary' : (u.role === 'hr' ? 'badge-success' : 'badge-info');
          const verifBadge = u.is_verified
            ? '<span class="badge badge-success" style="font-size:11px"><i class="fas fa-check-circle"></i> Verified</span>'
            : '<span class="badge badge-gray" style="font-size:11px"><i class="fas fa-clock"></i> Unverified</span>';
          const statusBadge = u.is_active
            ? '<span class="badge badge-success" style="font-size:11px"><i class="fas fa-check"></i> Active</span>'
            : '<span class="badge badge-danger" style="font-size:11px"><i class="fas fa-ban"></i> Inactive</span>';
          const createdDate = u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A';
          const lastLoginText = u.last_login ? new Date(u.last_login).toLocaleString() : '<span style="color:var(--text-3)">Never</span>';
          const isCurrentUser = DB.currentUser && DB.currentUser.id === u.id;

          return `
            <tr>
              <td style="font-weight:600;color:var(--text-3);font-size:12px">#${u.id}</td>
              <td>
                <div style="display:flex;align-items:center;gap:10px">
                  <div class="avatar avatar-sm" style="background:${bg};color:#fff;flex-shrink:0">${escapeHTML(avatar)}</div>
                  <div>
                    <div style="font-weight:700;font-size:13px;color:var(--text)">${escapeHTML(u.name)} ${isCurrentUser ? '<span class="badge badge-gray" style="font-size:10px;padding:2px 6px">You</span>' : ''}</div>
                    <div style="font-size:11px;color:var(--text-3)">${escapeHTML(u.email)}</div>
                  </div>
                </div>
              </td>
              <td><span class="badge ${roleBadgeColor}" style="text-transform:capitalize;font-size:11px">${escapeHTML(u.role)}</span></td>
              <td>${verifBadge}</td>
              <td>${statusBadge}</td>
              <td><span class="badge ${UI.atsBadge(u.ats_score || 0)}" style="font-size:11px">${u.ats_score || 0}/100</span></td>
              <td style="font-size:12px;color:var(--text-2)">${escapeHTML(u.location || 'Not set')}</td>
              <td style="font-size:12px;color:var(--text-3)">${createdDate}</td>
              <td style="font-size:12px">${lastLoginText}</td>
              <td style="text-align:right">
                <button class="btn btn-sm btn-outline" onclick="openPlatformUserModal(${u.id})">
                  <i class="fas fa-user-cog"></i> Manage
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching platform users:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--danger)">Error loading platform users.</td></tr>';
    });
}

function changePlatformUsersPage(delta) {
  const targetPage = PlatformAdminState.usersPage + delta;
  if (targetPage >= 1 && targetPage <= PlatformAdminState.usersTotalPages) {
    fetchPlatformAdminUsers(targetPage);
  }
}

function openPlatformUserModal(userId) {
  fetch(`/api/platform-admin/users/${userId}`)
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) {
        Toast.show(res ? res.message : 'Failed to retrieve user details', 'error');
        return;
      }

      const u = res.data.user;
      PlatformAdminState.selectedUser = u;

      setEl('pa-modal-name', u.name);
      setEl('pa-modal-email', u.email);
      setEl('pa-modal-id', `#${u.id}`);
      setEl('pa-modal-location', u.location || 'Not provided');
      setEl('pa-modal-phone', u.phone || 'Not provided');
      setEl('pa-modal-education', u.education || 'Not provided');
      setEl('pa-modal-ats', `${u.ats_score || 0} / 100`);
      setEl('pa-modal-created', u.created_at ? new Date(u.created_at).toLocaleString() : 'N/A');
      setEl('pa-modal-last-login', u.last_login ? new Date(u.last_login).toLocaleString() : 'Never logged in');
      setEl('pa-modal-stats', `${u.application_count || 0} job applications · ${u.resume_count || 0} uploaded resumes`);

      const avatarEl = document.getElementById('pa-modal-avatar');
      if (avatarEl) {
        avatarEl.textContent = (u.name || '??').slice(0, 2).toUpperCase();
        avatarEl.style.background = UI.avatarColor(u.name || '');
      }

      const linksEl = document.getElementById('pa-modal-links');
      if (linksEl) {
        const links = [];
        if (u.linkedin) links.push(`<a href="${escapeHTML(u.linkedin)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">LinkedIn</a>`);
        if (u.github) links.push(`<a href="${escapeHTML(u.github)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:underline;">GitHub</a>`);
        linksEl.innerHTML = links.length ? links.join(' · ') : 'None provided';
      }

      const roleBadge = document.getElementById('pa-modal-role-badge');
      if (roleBadge) {
        roleBadge.className = `badge ${u.role === 'admin' ? 'badge-primary' : (u.role === 'hr' ? 'badge-success' : 'badge-info')}`;
        roleBadge.textContent = u.role.toUpperCase();
      }

      const statusBadge = document.getElementById('pa-modal-status-badge');
      if (statusBadge) {
        statusBadge.className = `badge ${u.is_active ? 'badge-success' : 'badge-danger'}`;
        statusBadge.textContent = u.is_active ? 'ACTIVE' : 'INACTIVE';
      }

      const skillsEl = document.getElementById('pa-modal-skills');
      if (skillsEl) {
        const skillsList = Array.isArray(u.skills) ? u.skills : [];
        skillsEl.innerHTML = skillsList.length
          ? skillsList.map(s => `<span class="skill-tag skill-neutral" style="font-size:12px;padding:3px 10px">${escapeHTML(s)}</span>`).join('')
          : '<span class="text-muted text-sm">No skills extracted yet</span>';
      }

      // Recent Activity
      const actEl = document.getElementById('pa-modal-user-activity');
      if (actEl) {
        const act = u.recent_activity || {};
        const apps = act.applications || [];
        const logins = act.logins || [];
        if (!apps.length && !logins.length) {
          actEl.innerHTML = '<span class="text-muted">No recent activity recorded for this user.</span>';
        } else {
          let html = '';
          if (apps.length) {
            html += '<div style="font-weight:700;margin-bottom:4px;color:var(--text)">Recent Applications:</div><ul style="padding-left:18px;margin-bottom:8px">';
            apps.forEach(a => {
              html += `<li>Applied to <strong>${escapeHTML(a.job_title || 'Job #' + a.job_id)}</strong> at ${escapeHTML(a.company || 'TalentSync')} — <span class="badge badge-gray" style="font-size:10px">${escapeHTML(a.status || 'Pending')}</span> <span style="color:var(--text-3);font-size:11px">(${a.applied_at ? new Date(a.applied_at).toLocaleDateString() : ''})</span></li>`;
            });
            html += '</ul>';
          }
          if (logins.length) {
            html += '<div style="font-weight:700;margin-bottom:4px;color:var(--text)">Recent Login Attempts:</div><ul style="padding-left:18px;margin:0">';
            logins.forEach(l => {
              html += `<li>IP: <code>${escapeHTML(l.ip_address || 'N/A')}</code> — <span class="badge ${l.success ? 'badge-success' : 'badge-danger'}" style="font-size:10px">${l.success ? 'Success' : 'Failed'}</span> <span style="color:var(--text-3);font-size:11px">(${l.timestamp ? new Date(l.timestamp).toLocaleString() : ''})</span></li>`;
            });
            html += '</ul>';
          }
          actEl.innerHTML = html;
        }
      }

      const roleSelect = document.getElementById('pa-modal-role-select');
      if (roleSelect) roleSelect.value = u.role;

      const toggleBtn = document.getElementById('pa-modal-btn-toggle-status');
      if (toggleBtn) {
        if (u.is_active) {
          toggleBtn.className = 'btn btn-sm btn-danger';
          toggleBtn.innerHTML = '<i class="fas fa-user-slash"></i> Deactivate Account';
        } else {
          toggleBtn.className = 'btn btn-sm btn-success';
          toggleBtn.innerHTML = '<i class="fas fa-user-check"></i> Activate Account';
        }
      }

      Modal.open('pa-user-modal');
    })
    .catch(err => {
      console.error('Error loading user detail:', err);
      Toast.show('Network error retrieving user details.', 'error');
    });
}

function submitPlatformUserRoleChange() {
  const u = PlatformAdminState.selectedUser;
  if (!u) return;

  const roleSelect = document.getElementById('pa-modal-role-select');
  if (!roleSelect) return;
  const newRole = roleSelect.value;

  if (newRole === u.role) {
    Toast.show('Selected role is identical to current role.', 'info');
    return;
  }

  const btn = document.getElementById('pa-modal-btn-role');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...'; }

  fetch(`/api/platform-admin/users/${u.id}/role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role: newRole })
  })
    .then(r => r.json().then(data => ({ status: r.status, body: data })))
    .then(({ status, body }) => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Update Role'; }
      if (body.success) {
        Toast.show(body.message || 'User role successfully updated.', 'success');
        u.role = newRole;
        const roleBadge = document.getElementById('pa-modal-role-badge');
        if (roleBadge) {
          roleBadge.className = `badge ${newRole === 'admin' ? 'badge-primary' : (newRole === 'hr' ? 'badge-success' : 'badge-info')}`;
          roleBadge.textContent = newRole.toUpperCase();
        }
        fetchPlatformAdminUsers(PlatformAdminState.usersPage);
      } else {
        Toast.show(body.message || 'Failed to update user role.', 'error');
      }
    })
    .catch(err => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Update Role'; }
      console.error('Role change error:', err);
      Toast.show('Network error while updating role.', 'error');
    });
}

function togglePlatformUserStatus() {
  const u = PlatformAdminState.selectedUser;
  if (!u) return;

  const endpoint = u.is_active ? `/api/platform-admin/users/${u.id}/deactivate` : `/api/platform-admin/users/${u.id}/activate`;
  const toggleBtn = document.getElementById('pa-modal-btn-toggle-status');
  if (toggleBtn) { toggleBtn.disabled = true; toggleBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...'; }

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(r => r.json().then(data => ({ status: r.status, body: data })))
    .then(({ status, body }) => {
      if (toggleBtn) toggleBtn.disabled = false;
      if (body.success) {
        u.is_active = !u.is_active;
        Toast.show(body.message || 'User account status updated.', 'success');
        const statusBadge = document.getElementById('pa-modal-status-badge');
        if (statusBadge) {
          statusBadge.className = `badge ${u.is_active ? 'badge-success' : 'badge-danger'}`;
          statusBadge.textContent = u.is_active ? 'ACTIVE' : 'INACTIVE';
        }
        if (toggleBtn) {
          toggleBtn.className = u.is_active ? 'btn btn-sm btn-danger' : 'btn btn-sm btn-success';
          toggleBtn.innerHTML = u.is_active
            ? '<i class="fas fa-user-slash"></i> Deactivate Account'
            : '<i class="fas fa-user-check"></i> Activate Account';
        }
        fetchPlatformAdminUsers(PlatformAdminState.usersPage);
      } else {
        Toast.show(body.message || 'Operation failed.', 'error');
        if (toggleBtn) {
          toggleBtn.innerHTML = u.is_active
            ? '<i class="fas fa-user-slash"></i> Deactivate Account'
            : '<i class="fas fa-user-check"></i> Activate Account';
        }
      }
    })
    .catch(err => {
      if (toggleBtn) {
        toggleBtn.disabled = false;
        toggleBtn.innerHTML = u.is_active
          ? '<i class="fas fa-user-slash"></i> Deactivate Account'
          : '<i class="fas fa-user-check"></i> Activate Account';
      }
      console.error('Status toggle error:', err);
      Toast.show('Network error while toggling status.', 'error');
    });
}

// ═══════════════════════════════════════════════════════════
// SECTION 3: JOBS & APPLICATIONS
// ═══════════════════════════════════════════════════════════

function fetchPlatformAdminJobs(page = 1) {
  PlatformAdminState.jobsPage = page;
  const searchInput = document.getElementById('pa-jobs-search');
  const statusSelect = document.getElementById('pa-jobs-status-filter');
  const q = searchInput ? searchInput.value.trim() : '';
  const status = statusSelect ? statusSelect.value : '';

  const tbody = document.getElementById('pa-jobs-table-body');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:28px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading internal jobs...</td></tr>';
  }

  const params = new URLSearchParams({ page: page, limit: 10 });
  if (q) params.set('search', q);
  if (status) params.set('status', status);

  fetch(`/api/platform-admin/jobs?${params.toString()}`)
    .then(r => {
      if (r.status === 401 || r.status === 403) throw new Error('Unauthorized');
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--danger)">${res ? res.message : 'Failed to load jobs'}</td></tr>`;
        return;
      }
      const jobs = res.data.jobs || [];
      const pagination = res.data.pagination;
      PlatformAdminState.jobsTotalPages = pagination.pages || 1;

      setEl('pa-jobs-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Internal Jobs)`);
      const prevBtn = document.getElementById('pa-jobs-prev-btn');
      const nextBtn = document.getElementById('pa-jobs-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (jobs.length === 0) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-briefcase" style="font-size:24px;margin-bottom:8px;display:block"></i>No internal jobs found matching query.</td></tr>';
        return;
      }

      if (tbody) {
        tbody.innerHTML = jobs.map(j => {
          const statusBadge = j.status === 'Active'
            ? '<span class="badge badge-success" style="font-size:11px">Active</span>'
            : (j.status === 'Closed' ? '<span class="badge badge-gray" style="font-size:11px">Closed</span>' : '<span class="badge badge-warning" style="font-size:11px">Draft</span>');
          const createdDate = j.created_at ? new Date(j.created_at).toLocaleDateString() : 'N/A';

          return `
            <tr>
              <td style="font-weight:600;color:var(--text-3);font-size:12px">#${j.id}</td>
              <td style="font-weight:700;font-size:13px;color:var(--text)">${escapeHTML(j.title)}</td>
              <td style="font-size:13px">${escapeHTML(j.company)}</td>
              <td style="font-size:12px;color:var(--text-2)">${escapeHTML(j.location || 'Remote')}</td>
              <td style="font-size:12px">${escapeHTML(j.type || 'Full-time')}</td>
              <td>${statusBadge}</td>
              <td><span class="badge badge-primary" style="font-size:11px">${j.application_count || 0} Applicants</span></td>
              <td style="font-size:12px;color:var(--text-3)">${createdDate}</td>
              <td style="text-align:right">
                <button class="btn btn-sm btn-outline" onclick="openPlatformJobModal(${j.id})">
                  <i class="fas fa-eye"></i> Details
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching internal jobs:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--danger)">Error loading internal jobs.</td></tr>';
    });
}

function changePlatformJobsPage(delta) {
  const target = PlatformAdminState.jobsPage + delta;
  if (target >= 1 && target <= PlatformAdminState.jobsTotalPages) {
    fetchPlatformAdminJobs(target);
  }
}

function openPlatformJobModal(jobId) {
  fetch(`/api/platform-admin/jobs/${jobId}`)
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) {
        Toast.show(res ? res.message : 'Failed to retrieve job details', 'error');
        return;
      }
      const j = res.data.job;
      PlatformAdminState.selectedJob = j;

      setEl('pa-modal-job-id', `#${j.id}`);
      setEl('pa-modal-job-title', j.title);
      setEl('pa-modal-job-company', j.company);
      setEl('pa-modal-job-location', j.location || 'Remote');
      setEl('pa-modal-job-type', j.type || 'Full-time');
      setEl('pa-modal-job-salary', j.salary || 'Competitive');
      setEl('pa-modal-job-status', j.status || 'Active');
      setEl('pa-modal-job-created', j.created_at ? new Date(j.created_at).toLocaleString() : 'N/A');

      const skillsEl = document.getElementById('pa-modal-job-skills');
      if (skillsEl) {
        const skills = Array.isArray(j.skills) ? j.skills : [];
        skillsEl.innerHTML = skills.length
          ? skills.map(s => `<span class="skill-tag skill-neutral" style="font-size:12px;padding:3px 10px">${escapeHTML(s)}</span>`).join('')
          : '<span class="text-muted text-sm">No specific skills listed</span>';
      }

      setEl('pa-modal-job-desc', j.description || 'No job description provided.');
      setEl('pa-modal-job-app-count', (j.applicants || []).length);

      const appTbody = document.getElementById('pa-modal-job-applicants-tbody');
      if (appTbody) {
        const applicants = j.applicants || [];
        appTbody.innerHTML = applicants.length
          ? applicants.map(a => `
              <tr>
                <td style="font-weight:600;font-size:12px">${escapeHTML(a.name)} <span style="font-size:11px;color:var(--text-3)">(${escapeHTML(a.email)})</span></td>
                <td><span class="badge ${UI.atsBadge(a.match_score || 0)}" style="font-size:11px">${a.match_score || 0}%</span></td>
                <td><span class="badge badge-gray" style="font-size:11px">${escapeHTML(a.status || 'Pending')}</span></td>
                <td style="font-size:11px;color:var(--text-3)">${a.applied_at ? new Date(a.applied_at).toLocaleDateString() : 'N/A'}</td>
              </tr>
            `).join('')
          : '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-3)">No candidates have applied to this job yet.</td></tr>';
      }

      Modal.open('pa-job-modal');
    })
    .catch(err => {
      console.error('Error opening job modal:', err);
      Toast.show('Network error opening job modal.', 'error');
    });
}

function fetchPlatformAdminApplications(page = 1) {
  PlatformAdminState.appsPage = page;
  const searchInput = document.getElementById('pa-apps-search');
  const statusSelect = document.getElementById('pa-apps-status-filter');
  const q = searchInput ? searchInput.value.trim() : '';
  const status = statusSelect ? statusSelect.value : '';

  const tbody = document.getElementById('pa-apps-table-body');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:28px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading platform applications...</td></tr>';
  }

  const params = new URLSearchParams({ page: page, limit: 10 });
  if (q) params.set('search', q);
  if (status) params.set('status', status);

  fetch(`/api/platform-admin/applications?${params.toString()}`)
    .then(r => {
      if (r.status === 401 || r.status === 403) throw new Error('Unauthorized');
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger)">${res ? res.message : 'Failed to load applications'}</td></tr>`;
        return;
      }

      const apps = res.data.applications || [];
      const pagination = res.data.pagination;
      PlatformAdminState.appsTotalPages = pagination.pages || 1;

      setEl('pa-apps-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Total Applications)`);
      const prevBtn = document.getElementById('pa-apps-prev-btn');
      const nextBtn = document.getElementById('pa-apps-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (apps.length === 0) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-file-contract" style="font-size:24px;margin-bottom:8px;display:block"></i>No applications match your filter.</td></tr>';
        return;
      }

      if (tbody) {
        tbody.innerHTML = apps.map(a => {
          const statusBadges = {
            Reviewing: 'badge-primary',
            Shortlisted: 'badge-success',
            Pending: 'badge-warning',
            Rejected: 'badge-danger'
          };
          const badgeClass = statusBadges[a.status] || 'badge-gray';
          const appliedDate = a.applied_at ? new Date(a.applied_at).toLocaleDateString() : 'N/A';

          return `
            <tr>
              <td style="font-weight:600;color:var(--text-3);font-size:12px">#${a.id}</td>
              <td>
                <div style="font-weight:700;font-size:13px;color:var(--text)">${escapeHTML(a.candidate_name)}</div>
                <div style="font-size:11px;color:var(--text-3)">${escapeHTML(a.candidate_email)}</div>
              </td>
              <td style="font-weight:600;font-size:13px">${escapeHTML(a.job_title)}</td>
              <td style="font-size:12px;color:var(--text-2)">${escapeHTML(a.company)}</td>
              <td><span class="badge ${UI.atsBadge(a.match_score || 0)}" style="font-size:11px">${a.match_score || 0}%</span></td>
              <td><span class="badge ${badgeClass}" style="font-size:11px">${escapeHTML(a.status)}</span></td>
              <td style="font-size:12px;color:var(--text-3)">${appliedDate}</td>
              <td style="text-align:right">
                <button class="btn btn-sm btn-outline" onclick="openPlatformAppModal(${a.id})">
                  <i class="fas fa-eye"></i> Details
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching applications:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger)">Error loading applications.</td></tr>';
    });
}

function changePlatformAppsPage(delta) {
  const target = PlatformAdminState.appsPage + delta;
  if (target >= 1 && target <= PlatformAdminState.appsTotalPages) {
    fetchPlatformAdminApplications(target);
  }
}

function openPlatformAppModal(appId) {
  fetch(`/api/platform-admin/applications/${appId}`)
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) {
        Toast.show(res ? res.message : 'Failed to retrieve application details', 'error');
        return;
      }
      const a = res.data.application;
      PlatformAdminState.selectedApp = a;

      setEl('pa-modal-app-id', `#${a.id}`);
      setEl('pa-modal-app-candidate', a.candidate_name);
      setEl('pa-modal-app-email', a.candidate_email);
      setEl('pa-modal-app-cand-ats', `${a.candidate_ats || 0}/100`);
      setEl('pa-modal-app-job', a.job_title);
      setEl('pa-modal-app-company', a.company);
      setEl('pa-modal-app-match', `${a.match_score || 0}%`);
      setEl('pa-modal-app-status', a.status);
      setEl('pa-modal-app-applied', a.applied_at ? new Date(a.applied_at).toLocaleString() : 'N/A');

      const histEl = document.getElementById('pa-modal-app-history');
      if (histEl) {
        const hist = a.status_history || [];
        if (!hist.length) {
          histEl.innerHTML = '<span class="text-muted">Initial submission state preserved. No subsequent recruiter transitions logged.</span>';
        } else {
          histEl.innerHTML = `<ul style="padding-left:18px;margin:0">` + hist.map(h => `
            <li>Changed to <strong>${escapeHTML(h.to_status)}</strong> by ${escapeHTML(h.changed_by || 'Recruiter')} <span style="color:var(--text-3);font-size:11px">(${h.timestamp ? new Date(h.timestamp).toLocaleString() : ''})</span></li>
          `).join('') + `</ul>`;
        }
      }

      Modal.open('pa-app-modal');
    })
    .catch(err => {
      console.error('Error opening application modal:', err);
      Toast.show('Network error opening application modal.', 'error');
    });
}

// ═══════════════════════════════════════════════════════════
// SECTION 4: RESUMES
// ═══════════════════════════════════════════════════════════

function fetchPlatformAdminResumes(page = 1) {
  PlatformAdminState.resumesPage = page;
  const searchInput = document.getElementById('pa-resumes-search');
  const statusSelect = document.getElementById('pa-resumes-status-filter');
  const q = searchInput ? searchInput.value.trim() : '';
  const status = statusSelect ? statusSelect.value : '';

  const tbody = document.getElementById('pa-resumes-table-body');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:28px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading resume inventory...</td></tr>';
  }

  const params = new URLSearchParams({ page: page, limit: 10 });
  if (q) params.set('search', q);
  if (status) params.set('status', status);

  fetch(`/api/platform-admin/resumes?${params.toString()}`)
    .then(r => {
      if (r.status === 401 || r.status === 403) throw new Error('Unauthorized');
      return r.json();
    })
    .then(res => {
      if (!res || !res.success) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger)">${res ? res.message : 'Failed to load resumes'}</td></tr>`;
        return;
      }

      const summary = res.data.summary || {};
      setEl('pa-resumes-total', summary.total);
      setEl('pa-resumes-processed', summary.processed);
      setEl('pa-resumes-pending', summary.pending);
      setEl('pa-resumes-failed', summary.failed);

      const resumes = res.data.resumes || [];
      const pagination = res.data.pagination;
      PlatformAdminState.resumesTotalPages = pagination.pages || 1;

      setEl('pa-resumes-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Resume Records)`);
      const prevBtn = document.getElementById('pa-resumes-prev-btn');
      const nextBtn = document.getElementById('pa-resumes-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (resumes.length === 0) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-3)"><i class="fas fa-file-invoice" style="font-size:24px;margin-bottom:8px;display:block"></i>No resumes match the filter.</td></tr>';
        return;
      }

      if (tbody) {
        tbody.innerHTML = resumes.map(r => {
          const statusBadge = r.status === 'processed'
            ? '<span class="badge badge-success" style="font-size:11px">Processed</span>'
            : (r.status === 'failed' ? '<span class="badge badge-danger" style="font-size:11px">Failed</span>' : '<span class="badge badge-warning" style="font-size:11px">Pending</span>');
          const fileBadge = r.file_exists
            ? '<span class="badge badge-success" style="font-size:11px"><i class="fas fa-hdd"></i> On Disk</span>'
            : '<span class="badge badge-danger" style="font-size:11px"><i class="fas fa-times"></i> Missing</span>';
          const uploadDate = r.uploaded_at ? new Date(r.uploaded_at).toLocaleDateString() : 'N/A';

          return `
            <tr>
              <td style="font-weight:600;color:var(--text-3);font-size:12px">#${r.id}</td>
              <td>
                <div style="font-weight:700;font-size:13px;color:var(--text)">${escapeHTML(r.candidate_name)}</div>
                <div style="font-size:11px;color:var(--text-3)">${escapeHTML(r.candidate_email)}</div>
              </td>
              <td style="font-size:12px;font-family:monospace;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHTML(r.original_filename || r.filename)}">
                ${escapeHTML(r.original_filename || r.filename)}
              </td>
              <td style="font-size:12px;color:var(--text-3)">${uploadDate}</td>
              <td>${statusBadge}</td>
              <td><span class="badge ${UI.atsBadge(r.ats_score || 0)}" style="font-size:11px">${r.ats_score || 0}/100</span></td>
              <td>${fileBadge}</td>
              <td style="text-align:right">
                <div style="display:inline-flex;gap:6px">
                  <button class="btn btn-sm btn-outline" onclick="openPlatformResumeModal(${r.id})" title="Inspect Metadata">
                    <i class="fas fa-eye"></i>
                  </button>
                  <button class="btn btn-sm btn-outline" onclick="downloadPlatformResume(${r.id})" ${r.file_exists ? '' : 'disabled'} title="Download">
                    <i class="fas fa-download"></i>
                  </button>
                  <button class="btn btn-sm btn-outline text-danger" onclick="deletePlatformResume(${r.id}, '${escapeHTML(r.original_filename || r.filename)}')" title="Compliance Deletion">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching resume inventory:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger)">Error loading resume inventory.</td></tr>';
    });
}

function changePlatformResumesPage(delta) {
  const target = PlatformAdminState.resumesPage + delta;
  if (target >= 1 && target <= PlatformAdminState.resumesTotalPages) {
    fetchPlatformAdminResumes(target);
  }
}

function openPlatformResumeModal(resumeId) {
  fetch(`/api/platform-admin/resumes/${resumeId}`)
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) {
        Toast.show(res ? res.message : 'Failed to retrieve resume details', 'error');
        return;
      }
      const r = res.data.resume;
      PlatformAdminState.selectedResume = r;

      setEl('pa-modal-resume-id', `#${r.id}`);
      setEl('pa-modal-resume-candidate', `${r.candidate_name} (${r.candidate_email})`);
      setEl('pa-modal-resume-filename', r.original_filename || r.filename);
      setEl('pa-modal-resume-size', r.file_size ? `${(r.file_size / 1024).toFixed(1)} KB` : 'Unknown');
      setEl('pa-modal-resume-ats', `${r.ats_score || 0}/100`);
      setEl('pa-modal-resume-status', r.status || 'processed');
      setEl('pa-modal-resume-file-status', r.file_exists ? 'Verified on Physical Storage' : 'File missing from storage disk');
      setEl('pa-modal-resume-uploaded', r.uploaded_at ? new Date(r.uploaded_at).toLocaleString() : 'N/A');

      const skillsEl = document.getElementById('pa-modal-resume-skills');
      if (skillsEl) {
        const skills = Array.isArray(r.skills) ? r.skills : [];
        skillsEl.innerHTML = skills.length
          ? skills.map(s => `<span class="skill-tag skill-neutral" style="font-size:12px;padding:3px 10px">${escapeHTML(s)}</span>`).join('')
          : '<span class="text-muted text-sm">No skills extracted</span>';
      }

      setEl('pa-modal-resume-preview', r.parsed_text_preview || 'No textual content extracted from this resume.');

      const dlBtn = document.getElementById('pa-modal-resume-download-btn');
      if (dlBtn) {
        dlBtn.onclick = () => downloadPlatformResume(r.id);
        dlBtn.disabled = !r.file_exists;
      }

      Modal.open('pa-resume-modal');
    })
    .catch(err => {
      console.error('Error opening resume modal:', err);
      Toast.show('Network error opening resume modal.', 'error');
    });
}

function downloadPlatformResume(resumeId) {
  window.open(`/api/resumes/${resumeId}`, '_blank');
}

function deletePlatformResume(resumeId, filename) {
  if (!confirm(`Are you sure you want to permanently delete resume #${resumeId} (${filename})?\n\nThis compliance operation will safely remove the physical file from disk, delete database records, update candidate ATS scores, and write to the audit trail.`)) return;

  fetch(`/api/resumes/${resumeId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(r => r.json().then(data => ({ status: r.status, body: data })))
    .then(({ status, body }) => {
      if (body.success) {
        Toast.show(body.message || 'Resume deleted successfully.', 'success');
        fetchPlatformAdminResumes(PlatformAdminState.resumesPage || 1);
        fetchPlatformAdminAnalytics();
      } else {
        Toast.show(body.message || 'Failed to delete resume.', 'error');
      }
    })
    .catch(err => {
      console.error('Resume deletion error:', err);
      Toast.show('Network error during resume deletion.', 'error');
    });
}

// ═══════════════════════════════════════════════════════════
// SECTION 5: SECURITY & AUDIT
// ═══════════════════════════════════════════════════════════

function fetchPlatformAdminSecurity() {
  fetchPlatformAdminLoginAttempts(1);
  fetchPlatformAdminOutliers();
}

function fetchPlatformAdminLoginAttempts(page = 1) {
  PlatformAdminState.loginsPage = page;
  const statusSelect = document.getElementById('pa-logins-status-filter');
  const searchInput  = document.getElementById('pa-logins-search');

  const status = statusSelect ? statusSelect.value : '';
  const q = searchInput ? searchInput.value.trim() : '';

  const params = new URLSearchParams({ page: page, limit: 10 });
  if (status) params.set('status', status);
  if (q) params.set('search', q);

  const tbody = document.getElementById('pa-logins-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading records...</td></tr>';

  fetch(`/api/platform-admin/security/login-attempts?${params.toString()}`)
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) return;
      const data = res.data;

      // Summary KPIs
      setEl('pa-sec-total', data.summary.total_attempts);
      setEl('pa-sec-success', data.summary.successful_attempts);
      setEl('pa-sec-failed', data.summary.failed_attempts);
      setEl('pa-sec-success-rate', `${data.summary.success_rate_pct}% Success Rate`);

      // Top Failed IPs
      const ipsTbody = document.getElementById('pa-top-failed-ips-tbody');
      if (ipsTbody) {
        const ips = data.top_failed_ips || [];
        ipsTbody.innerHTML = ips.length
          ? ips.map(x => `<tr><td style="font-family:monospace;font-size:12px">${escapeHTML(x.ip_address)}</td><td style="text-align:right"><span class="badge badge-danger">${x.failure_count}</span></td></tr>`).join('')
          : '<tr><td colspan="2" style="text-align:center;padding:20px;color:var(--text-3)">No failed attempts recorded.</td></tr>';
      }

      // Top Targeted Accounts
      const accTbody = document.getElementById('pa-top-targeted-tbody');
      if (accTbody) {
        const accs = data.top_targeted_accounts || [];
        accTbody.innerHTML = accs.length
          ? accs.map(x => `<tr><td style="font-size:12px">${escapeHTML(x.email)}</td><td style="text-align:right"><span class="badge badge-warning">${x.failure_count}</span></td></tr>`).join('')
          : '<tr><td colspan="2" style="text-align:center;padding:20px;color:var(--text-3)">No targeted accounts.</td></tr>';
      }

      // Recent attempts table
      const attempts = data.attempts || [];
      const pagination = data.pagination;
      PlatformAdminState.loginsTotalPages = pagination.pages || 1;

      setEl('pa-logins-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Records)`);
      const prevBtn = document.getElementById('pa-logins-prev-btn');
      const nextBtn = document.getElementById('pa-logins-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (tbody) {
        tbody.innerHTML = attempts.length
          ? attempts.map(a => `
              <tr>
                <td style="color:var(--text-3);font-size:12px">#${a.id}</td>
                <td style="font-weight:600;font-size:13px">${escapeHTML(a.email)}</td>
                <td style="font-family:monospace;font-size:12px;color:var(--text-2)">${escapeHTML(a.ip_address || 'N/A')}</td>
                <td>
                  <span class="badge ${a.success ? 'badge-success' : 'badge-danger'}" style="font-size:11px">
                    <i class="fas ${a.success ? 'fa-check-circle' : 'fa-times-circle'}"></i> ${a.success ? 'Success' : 'Failed'}
                  </span>
                </td>
                <td style="font-size:12px;color:var(--text-3)">${a.timestamp ? new Date(a.timestamp).toLocaleString() : 'N/A'}</td>
              </tr>
            `).join('')
          : '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-3)">No login records found.</td></tr>';
      }
    })
    .catch(err => {
      console.error('Error fetching login attempts:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--danger)">Error loading login attempts.</td></tr>';
    });
}

function changePlatformLoginsPage(delta) {
  const target = PlatformAdminState.loginsPage + delta;
  if (target >= 1 && target <= PlatformAdminState.loginsTotalPages) {
    fetchPlatformAdminLoginAttempts(target);
  }
}

function fetchPlatformAdminOutliers() {
  const tbody = document.getElementById('pa-outliers-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading outliers...</td></tr>';

  fetch('/api/platform-admin/security/outliers')
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) return;
      const outliers = res.data.outliers || [];
      setEl('pa-sec-outliers', res.data.total_outliers);

      if (tbody) {
        tbody.innerHTML = outliers.length
          ? outliers.map(o => {
              const avatar = (o.name || '??').slice(0, 2).toUpperCase();
              const bg = UI.avatarColor(o.name || '');
              return `
                <tr>
                  <td>
                    <div style="display:flex;align-items:center;gap:10px">
                      <div class="avatar avatar-sm" style="background:${bg};color:#fff;flex-shrink:0">${escapeHTML(avatar)}</div>
                      <div>
                        <div style="font-weight:700;font-size:13px">${escapeHTML(o.name)}</div>
                        <div style="font-size:11px;color:var(--text-3)">${escapeHTML(o.email)}</div>
                      </div>
                    </div>
                  </td>
                  <td><span class="badge badge-info" style="text-transform:capitalize;font-size:11px">${escapeHTML(o.role)}</span></td>
                  <td><span class="badge ${UI.atsBadge(o.ats_score || 0)}" style="font-size:11px">${o.ats_score || 0}/100</span></td>
                  <td><span class="badge badge-gray" style="font-size:11px">${escapeHTML(o.cluster_label || 'Unclustered')}</span></td>
                  <td>
                    <span style="color:#ea580c;font-size:12px;font-weight:600">
                      <i class="fas fa-exclamation-circle" style="margin-right:4px"></i> ${escapeHTML(o.outlier_reason || 'Statistical anomaly detected')}
                    </span>
                  </td>
                  <td style="text-align:right">
                    <button class="btn btn-sm btn-outline" onclick="openPlatformUserModal(${o.id})">
                      <i class="fas fa-user-shield"></i> Review
                    </button>
                  </td>
                </tr>
              `;
            }).join('')
          : '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-3)"><i class="fas fa-check-circle" style="color:#16a34a;margin-right:6px"></i>No suspicious outlier candidates flagged at this time.</td></tr>';
      }
    })
    .catch(err => {
      console.error('Error fetching outliers:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--danger)">Error loading outliers.</td></tr>';
    });
}

function fetchPlatformAdminAudit(page = 1) {
  PlatformAdminState.auditPage = page;
  const sourceSelect = document.getElementById('pa-audit-source-filter');
  const searchInput  = document.getElementById('pa-audit-search');

  const source = sourceSelect ? sourceSelect.value : 'all';
  const q = searchInput ? searchInput.value.trim() : '';

  const params = new URLSearchParams({ page: page, limit: 15 });
  if (source && source !== 'all') params.set('source', source);
  if (q) params.set('search', q);

  const tbody = document.getElementById('pa-audit-tbody');
  const emptyState = document.getElementById('pa-audit-empty-state');
  if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Loading audit events...</td></tr>';
  if (emptyState) emptyState.style.display = 'none';

  fetch(`/api/platform-admin/audit?${params.toString()}`)
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--danger)">Failed to load audit records.</td></tr>';
        return;
      }

      const events = res.data.events || [];
      const pagination = res.data.pagination;
      PlatformAdminState.auditTotalPages = pagination.pages || 1;

      setEl('pa-audit-page-info', `Showing Page ${pagination.page} of ${pagination.pages} (${pagination.total} Total Events)`);
      const prevBtn = document.getElementById('pa-audit-prev-btn');
      const nextBtn = document.getElementById('pa-audit-next-btn');
      if (prevBtn) prevBtn.disabled = pagination.page <= 1;
      if (nextBtn) nextBtn.disabled = pagination.page >= pagination.pages;

      if (events.length === 0) {
        if (tbody) tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
      }

      if (emptyState) emptyState.style.display = 'none';
      if (tbody) {
        tbody.innerHTML = events.map(e => {
          const tableBadges = {
            application_status: 'badge-primary',
            recommendation_history: 'badge-teal',
            search_history: 'badge-warning'
          };
          const badgeClass = tableBadges[e.source_table] || 'badge-gray';
          let detailsFormatted = '';
          if (typeof e.details === 'object' && e.details !== null) {
            detailsFormatted = Object.entries(e.details).map(([k, v]) => `<strong>${escapeHTML(k)}:</strong> ${escapeHTML(String(v))}`).join(' · ');
          } else {
            detailsFormatted = escapeHTML(String(e.details || ''));
          }

          const severityBadge = getAuditSeverity(e.action, e.source_table);

          return `
            <tr>
              <td style="color:var(--text-3);font-size:12px;font-family:monospace">#${e.id}</td>
              <td>${severityBadge}</td>
              <td><span class="badge ${badgeClass}" style="font-size:11px">${escapeHTML(e.source_table)}</span></td>
              <td style="font-size:12px;color:var(--text-3)">${e.timestamp ? new Date(e.timestamp).toLocaleString() : 'N/A'}</td>
              <td style="font-weight:600;font-size:13px">${escapeHTML(e.actor || 'System')}</td>
              <td><span class="badge badge-gray" style="font-size:11px">${escapeHTML(e.action)}</span></td>
              <td style="font-size:12px;color:var(--text-2);max-width:320px">${detailsFormatted || '<span class="text-muted">None</span>'}</td>
            </tr>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching audit logs:', err);
      if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--danger)">Error loading audit records.</td></tr>';
    });
}

function changePlatformAuditPage(delta) {
  const target = PlatformAdminState.auditPage + delta;
  if (target >= 1 && target <= PlatformAdminState.auditTotalPages) {
    fetchPlatformAdminAudit(target);
  }
}

// ═══════════════════════════════════════════════════════════
// SECTION 6: SYSTEM & AUTO REFRESH
// ═══════════════════════════════════════════════════════════

let _paAutoRefreshTimer = null;

function togglePlatformAdminAutoRefresh(enabled) {
  if (_paAutoRefreshTimer) {
    clearInterval(_paAutoRefreshTimer);
    _paAutoRefreshTimer = null;
  }

  const indicator = document.getElementById('pa-system-live-indicator');
  if (enabled) {
    if (indicator) {
      indicator.innerHTML = '<span style="color:#10b981">● Auto-refresh: <strong>ON (30s)</strong></span>';
    }
    _paAutoRefreshTimer = setInterval(() => {
      const isPlatformAdmin = Router.currentPage === 'platform-admin';
      if (!isPlatformAdmin) return;

      const activeSub = Router.innerPages['platform-admin'];
      if (activeSub === 'overview') {
        fetchPlatformAdminAnalytics();
        fetchPlatformAdminRecentActivity();
      } else if (activeSub === 'system') {
        fetchPlatformAdminSystemHealth();
        fetchPlatformAdminIntegrations();
      } else if (activeSub === 'security-audit') {
        fetchPlatformAdminSecurity();
      } else if (activeSub === 'pipeline') {
        loadMLPipelineStatus();
      }
    }, 30000);
    showToast('Platform diagnostic auto-refresh enabled (30s interval).', 'success');
  } else {
    if (indicator) {
      indicator.innerHTML = '<span style="color:var(--text-3)">○ Auto-refresh: <strong>OFF</strong></span>';
    }
    showToast('Platform diagnostic auto-refresh paused.', 'info');
  }
}

function fetchPlatformAdminSystemHealth() {
  const grid = document.getElementById('pa-system-health-grid');
  if (grid) grid.innerHTML = '<div class="stat-card" style="grid-column:1/-1;text-align:center;padding:32px"><i class="fas fa-spinner fa-spin" style="font-size:20px;margin-bottom:8px"></i><br>Probing system components...</div>';

  fetch('/api/platform-admin/system/health')
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success) {
        if (grid) grid.innerHTML = '<div class="stat-card" style="grid-column:1/-1;color:var(--danger)">Failed to run system diagnostics.</div>';
        return;
      }
      const data = res.data;
      const overall = data.overall || 'Healthy';

      const overallBadge = document.getElementById('pa-health-overall-badge');
      if (overallBadge) {
        overallBadge.className = `badge ${overall === 'Healthy' ? 'badge-success' : (overall === 'Degraded' ? 'badge-warning' : 'badge-danger')}`;
        overallBadge.textContent = overall.toUpperCase();
      }
      setEl('pa-health-last-checked', new Date(data.timestamp).toLocaleTimeString());
      setEl('pa-health-overall-summary', `Probing 8 core platform subsystems. Overall status is currently ${overall}.`);

      const serviceIcons = {
        database: 'fa-database',
        file_storage: 'fa-hdd',
        authentication: 'fa-shield-alt',
        resume_parser: 'fa-file-pdf',
        ats_engine: 'fa-tachometer-alt',
        job_matcher: 'fa-brain',
        adzuna: 'fa-globe',
        email: 'fa-envelope'
      };

      const statusMap = {
        'Healthy': { badge: 'badge-success', iconColor: '#10b981', border: '#10b981' },
        'Degraded': { badge: 'badge-warning', iconColor: '#f59e0b', border: '#f59e0b' },
        'Unavailable': { badge: 'badge-danger', iconColor: '#ef4444', border: '#ef4444' },
        'Not Configured': { badge: 'badge-gray', iconColor: '#64748b', border: '#cbd5e1' }
      };

      if (grid && data.services) {
        grid.innerHTML = Object.entries(data.services).map(([key, s]) => {
          const cfg = statusMap[s.status] || statusMap['Healthy'];
          const icon = serviceIcons[key] || 'fa-server';
          const latencyText = s.latency_ms !== undefined && s.latency_ms !== null ? `${s.latency_ms} ms` : 'N/A';

          return `
            <div class="stat-card" style="border-top:3px solid ${cfg.border};padding:18px">
              <div class="stat-top" style="margin-bottom:10px">
                <div style="font-weight:700;font-size:14px;color:var(--text)">${escapeHTML(s.name)}</div>
                <div class="stat-icon" style="background:#f8fafc"><i class="fas ${icon}" style="color:${cfg.iconColor}"></i></div>
              </div>
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                <span class="badge ${cfg.badge}" style="font-size:11px;font-weight:700">${escapeHTML(s.status)}</span>
                <span style="font-size:11px;color:var(--text-3);font-family:monospace">Latency: ${latencyText}</span>
              </div>
              <div style="font-size:12px;color:var(--text-2);line-height:1.4">${escapeHTML(s.details)}</div>
            </div>
          `;
        }).join('');
      }
    })
    .catch(err => {
      console.error('Error fetching system health:', err);
      if (grid) grid.innerHTML = '<div class="stat-card" style="grid-column:1/-1;color:var(--danger)">Network error checking health.</div>';
    });
}

function fetchPlatformAdminIntegrations() {
  const grid = document.getElementById('pa-system-integrations-grid');
  if (grid) grid.innerHTML = '<div class="card" style="grid-column:1/-1;padding:32px;text-align:center;color:var(--text-3)"><i class="fas fa-spinner fa-spin"></i> Checking configured integrations...</div>';

  fetch('/api/platform-admin/system/integrations')
    .then(r => r.json())
    .then(res => {
      if (!res || !res.success || !grid) return;
      const list = res.data.integrations || [];
      grid.innerHTML = list.map(item => {
        const isHealthy = item.status === 'Healthy';
        const isNotConfig = item.status === 'Not Configured';
        const badgeClass = isHealthy ? 'badge-success' : (isNotConfig ? 'badge-gray' : 'badge-warning');

        return `
          <div class="card" style="padding:20px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
              <div style="font-weight:800;font-size:15px;color:var(--text)">
                <i class="fas fa-plug" style="color:#2563eb;margin-right:8px"></i> ${escapeHTML(item.name)}
              </div>
              <span class="badge ${badgeClass}" style="font-size:11px">${escapeHTML(item.status)}</span>
            </div>
            <table class="table" style="font-size:12px;margin-bottom:12px">
              <tr><td style="color:var(--text-3);width:130px">Configuration</td><td><strong>${item.configured ? 'Configured' : 'Missing'}</strong></td></tr>
              ${item.masked_app_id ? `<tr><td style="color:var(--text-3)">App ID</td><td><code>${escapeHTML(item.masked_app_id)}</code></td></tr>` : ''}
              ${item.endpoint ? `<tr><td style="color:var(--text-3)">Endpoint</td><td><code>${escapeHTML(item.endpoint)}</code></td></tr>` : ''}
              ${item.sender ? `<tr><td style="color:var(--text-3)">Sender</td><td><code>${escapeHTML(item.sender)}</code></td></tr>` : ''}
              ${item.smtp_host ? `<tr><td style="color:var(--text-3)">Host:Port</td><td><code>${escapeHTML(item.smtp_host)}:${escapeHTML(String(item.smtp_port))}</code></td></tr>` : ''}
              ${item.tesseract_installed !== undefined ? `<tr><td style="color:var(--text-3)">Tesseract Binary</td><td>${item.tesseract_installed ? '<span class="badge badge-success">Installed</span>' : '<span class="badge badge-gray">Not Found</span>'}</td></tr>` : ''}
              <tr><td style="color:var(--text-3)">Last Result</td><td>${escapeHTML(item.last_status || 'Idle')}</td></tr>
            </table>
            <div style="font-size:11px;color:var(--text-3);border-top:1px solid var(--border);padding-top:8px">${escapeHTML(item.notes || '')}</div>
          </div>
        `;
      }).join('');
    })
    .catch(err => {
      console.error('Error fetching integrations:', err);
      if (grid) grid.innerHTML = '<div class="card" style="grid-column:1/-1;color:var(--danger)">Error loading integrations.</div>';
    });
}

// ═══════════════════════════════════════════════════════════
// SECTION 7: AI/ML PIPELINE CONTROLS
// ═══════════════════════════════════════════════════════════

function flushMLCache() {
  if (!confirm('Are you sure you want to flush in-memory ML model caches and recommendation vectors?')) {
    return;
  }
  const btn = document.getElementById('pipeline-flush-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Flushing...'; }

  fetch('/api/ml/cache/flush', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(r => r.json())
    .then(res => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-broom"></i> Flush Cache'; }
      if (res && res.success) {
        showToast(res.message || 'ML cache successfully flushed.', 'success');
        loadMLPipelineStatus();
      } else {
        showToast((res && res.message) || 'Failed to flush ML cache.', 'error');
      }
    })
    .catch(err => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-broom"></i> Flush Cache'; }
      showToast('Network error while flushing ML cache.', 'error');
    });
}

function triggerMLTraining() {
  if (!confirm('Start backend ML pipeline retraining on full corpus? This runs asynchronously on the server.')) {
    return;
  }
  const btn = document.getElementById('pipeline-retrain-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Retraining...'; }

  fetch('/api/ml/train', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skip_ner: false })
  })
    .then(r => r.json())
    .then(res => {
      showToast(res.message || 'Model training task started.', 'info');
      // Poll progress every 3 seconds until completed
      const pollTimer = setInterval(() => {
        fetch('/api/ml/status')
          .then(r => r.json())
          .then(data => {
            if (!data.training_running) {
              clearInterval(pollTimer);
              if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-cogs"></i> Retrain Model'; }
              if (data.last_training && data.last_training.success) {
                showToast(`Training complete in ${data.last_training.elapsed_s}s!`, 'success');
              } else if (data.last_training && data.last_training.error) {
                showToast(`Training failed: ${data.last_training.error}`, 'error');
              }
              loadMLPipelineStatus();
            }
          })
          .catch(() => {
            clearInterval(pollTimer);
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-cogs"></i> Retrain Model'; }
          });
      }, 3000);
    })
    .catch(err => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-cogs"></i> Retrain Model'; }
      showToast('Failed to trigger ML training.', 'error');
    });
}

// ═══════════════════════════════════════════════════════════
// GLOBAL EXPORTS
// ═══════════════════════════════════════════════════════════
window.PlatformAdminState            = PlatformAdminState;
window.getAuditSeverity              = getAuditSeverity;
window.switchPaJobsAppsTab           = switchPaJobsAppsTab;
window.switchPaSecAuditTab           = switchPaSecAuditTab;
window.switchPaSystemTab             = switchPaSystemTab;

// Section 1
window.fetchPlatformAdminAnalytics   = fetchPlatformAdminAnalytics;
window.fetchPlatformAdminRecentActivity = fetchPlatformAdminRecentActivity;

// Section 2
window.fetchPlatformAdminUsers       = fetchPlatformAdminUsers;
window.changePlatformUsersPage       = changePlatformUsersPage;
window.openPlatformUserModal         = openPlatformUserModal;
window.submitPlatformUserRoleChange  = submitPlatformUserRoleChange;
window.togglePlatformUserStatus      = togglePlatformUserStatus;

// Section 3
window.fetchPlatformAdminJobs        = fetchPlatformAdminJobs;
window.changePlatformJobsPage        = changePlatformJobsPage;
window.openPlatformJobModal          = openPlatformJobModal;
window.fetchPlatformAdminApplications = fetchPlatformAdminApplications;
window.changePlatformAppsPage        = changePlatformAppsPage;
window.openPlatformAppModal          = openPlatformAppModal;

// Section 4
window.fetchPlatformAdminResumes     = fetchPlatformAdminResumes;
window.changePlatformResumesPage     = changePlatformResumesPage;
window.openPlatformResumeModal       = openPlatformResumeModal;
window.downloadPlatformResume        = downloadPlatformResume;
window.deletePlatformResume          = deletePlatformResume;

// Section 5
window.fetchPlatformAdminSecurity    = fetchPlatformAdminSecurity;
window.fetchPlatformAdminLoginAttempts = fetchPlatformAdminLoginAttempts;
window.changePlatformLoginsPage      = changePlatformLoginsPage;
window.fetchPlatformAdminOutliers     = fetchPlatformAdminOutliers;
window.fetchPlatformAdminAudit       = fetchPlatformAdminAudit;
window.changePlatformAuditPage       = changePlatformAuditPage;

// Section 6 & 7
window.togglePlatformAdminAutoRefresh = togglePlatformAdminAutoRefresh;
window.fetchPlatformAdminSystemHealth = fetchPlatformAdminSystemHealth;
window.fetchPlatformAdminIntegrations = fetchPlatformAdminIntegrations;
window.flushMLCache                  = flushMLCache;
window.triggerMLTraining             = triggerMLTraining;
window.loadMLPipelineStatus          = loadMLPipelineStatus;

// Candidate Notification Center
window.CandidateNotifCenter          = CandidateNotifCenter;
window.filterNotifications           = filterNotifications;
window.handleNotificationSearch      = handleNotificationSearch;
window.markAllNotificationsRead      = markAllNotificationsRead;
window.clearReadNotifications        = clearReadNotifications;
window.markNotificationRead          = markNotificationRead;
window.deleteNotification            = deleteNotification;
window.navigateToNotifAction         = navigateToNotifAction;
