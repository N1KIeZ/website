// Main Cheat Menu for nikita.gg

document.addEventListener('DOMContentLoaded', () => {
    // Check for valid session
    const authData = sessionStorage.getItem('nikita_auth');
    if (!authData) {
        window.location.href = 'login.html';
        return;
    }

    const auth = JSON.parse(authData);

    // Update UI with user data
    document.getElementById('username').textContent = auth.username || 'User';

    // Mask license key (if available)
    const key = auth.key || '';
    const maskedKey = key.length >= 5 ? key.substring(0, 5) + '-*****' : '*****-*****';
    document.getElementById('licenseKey').textContent = maskedKey;

    // Inject button
    document.getElementById('injectBtn').addEventListener('click', () => {
        const btn = document.getElementById('injectBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Injecting...</span>';

        // Simulate injection
        setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-check"></i><span>Injected!</span>';
            setTimeout(() => {
                btn.innerHTML = '<i class="fas fa-play"></i><span>Inject to FiveM</span>';
                btn.disabled = false;
            }, 2000);
        }, 1500);
    });

    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => {
        sessionStorage.removeItem('nikita_auth');
        window.location.href = 'login.html';
    });
});