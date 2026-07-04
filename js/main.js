document.body.classList.add('loaded');

fetchBannedKeys().then(function() {
    var session = localStorage.getItem('ng_session');
    if (session) {
        var accounts = getAccounts();
        var acc = accounts[session.toLowerCase()];
        if (acc) {
            if (acc.key && isKeyBanned(acc.key)) {
                clearCurrentUser();
                return;
            }
            if (acc.key && isKeyExpired(acc.key, acc.joined / 1000)) {
                clearCurrentUser();
                return;
            }
            setCurrentUser(session);
            show('dashboard');
            document.getElementById('dash-user').textContent = session;
            document.getElementById('main-nav').style.display = 'none';
            startBanPolling();
            return;
        }
        clearCurrentUser();
    }
});

function startBanPolling() {
    if (banCheckInterval) clearInterval(banCheckInterval);
    banCheckInterval = setInterval(function() {
        if (!CURRENT_USER) return;
        fetchBannedKeys().then(function() {
            var accounts = getAccounts();
            var acc = accounts[CURRENT_USER.toLowerCase()];
            if (acc && acc.key && isKeyBanned(acc.key)) {
                clearInterval(banCheckInterval);
                showBanScreen(acc.key);
                return;
            }
            if (acc && acc.key && isKeyExpired(acc.key, acc.joined / 1000)) {
                clearInterval(banCheckInterval);
                showExpiredScreen(acc.key);
                return;
            }
        });
    }, 15000);
}
