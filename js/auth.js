var bannedKeys = [];
var CURRENT_USER = null;
var banCheckInterval = null;
var BANS_API = '/.netlify/functions/bans';

function fetchBannedKeys() {
    return fetch(BANS_API + '?t=' + Date.now())
        .then(function(r) {
            if (!r.ok) throw new Error('fetch failed');
            return r.json();
        })
        .then(function(data) {
            var list = data.banned || [];
            bannedKeys = list.map(function(k) {
                return k.trim().toUpperCase().replace(/-/g, '');
            });
            return bannedKeys;
        })
        .catch(function() {
            bannedKeys = [];
            return bannedKeys;
        });
}

function isKeyBanned(key) {
    var nk = key.trim().toUpperCase().replace(/-/g, '');
    return bannedKeys.indexOf(nk) !== -1;
}

function getAccounts() {
    try { return JSON.parse(localStorage.getItem('ng_accounts') || '{}'); }
    catch (e) { return {}; }
}

function saveAccount(username, email, password, key) {
    var accounts = getAccounts();
    accounts[username.toLowerCase()] = { username: username, email: email, password: password, key: key, joined: Date.now() };
    localStorage.setItem('ng_accounts', JSON.stringify(accounts));
}

function findAccount(username, password) {
    var accounts = getAccounts();
    var entry = accounts[username.toLowerCase()];
    if (entry && entry.password === password) return entry;
    return null;
}

function setCurrentUser(username) {
    CURRENT_USER = username;
    localStorage.setItem('ng_session', username);
}

function clearCurrentUser() {
    CURRENT_USER = null;
    localStorage.removeItem('ng_session');
}

function showBanScreen(key) {
    var display = key.substring(0, 7) + '-****-****-****';
    document.getElementById('ban-key-display').textContent = display;
    document.getElementById('ban-title').textContent = 'access revoked';
    document.getElementById('ban-subtitle').textContent = 'your license has been terminated';
    document.getElementById('main-nav').style.display = 'none';
    show('banned');
}

function showExpiredScreen(key) {
    var display = key.substring(0, 7) + '-****-****-****';
    document.getElementById('ban-key-display').textContent = display;
    document.getElementById('ban-title').textContent = 'key expired';
    document.getElementById('ban-subtitle').textContent = 'your license key has expired. contact support to renew.';
    document.getElementById('main-nav').style.display = 'none';
    show('banned');
}

function doRegister(e) {
    e.preventDefault();
    var err = document.getElementById('err-register');
    var user = document.getElementById('reg-user').value.trim();
    var email = document.getElementById('reg-email').value.trim();
    var pass = document.getElementById('reg-pass').value;
    var key = document.getElementById('reg-key').value.trim();

    err.textContent = '';

    if (!user || !email || !pass || !key) {
        err.textContent = 'please fill in all fields';
        return false;
    }
    if (!isValidKey(key)) {
        err.textContent = 'invalid license key';
        return false;
    }
    if (!checkCaptcha('register')) {
        err.textContent = 'incorrect captcha answer';
        newCaptcha('register');
        return false;
    }

    fetchBannedKeys().then(function() {
        if (isKeyBanned(key)) {
            showBanScreen(key);
            return;
        }
        var accounts = getAccounts();
        if (accounts[user.toLowerCase()]) {
            err.textContent = 'username already taken';
            return;
        }
        saveAccount(user, email, pass, key);
        setCurrentUser(user);
        enterDashboard(user);
    });

    return false;
}

function doLogin(e) {
    e.preventDefault();
    var err = document.getElementById('err-login');
    var user = document.getElementById('log-user').value.trim();
    var pass = document.getElementById('log-pass').value;

    err.textContent = '';

    if (!user || !pass) {
        err.textContent = 'please fill in all fields';
        return false;
    }
    if (!checkCaptcha('login')) {
        err.textContent = 'incorrect captcha answer';
        newCaptcha('login');
        return false;
    }

    fetchBannedKeys().then(function() {
        var account = findAccount(user, pass);
        if (!account) {
            err.textContent = 'invalid username or password';
            newCaptcha('login');
            return;
        }
        if (account.key && isKeyBanned(account.key)) {
            showBanScreen(account.key);
            return;
        }
        if (account.key && isKeyExpired(account.key, account.joined / 1000)) {
            showExpiredScreen(account.key);
            return;
        }
        setCurrentUser(user);
        enterDashboard(account.username);
    });

    return false;
}