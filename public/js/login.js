// Modern Login UI for nikita.gg
// Connects to the key system backend

const API_BASE = 'https://website-0bcg.onrender.com';

// Show loader animation
function showLoader() {
    const loader = document.getElementById('loader');
    const loaderBar = document.getElementById('loaderBar');
    const loaderStatus = document.getElementById('loaderStatus');

    loader.classList.add('on');
    setTimeout(() => loader.classList.add('shown'), 10);

    // Animate progress bar
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
        }
        loaderBar.style.width = progress + '%';
    }, 100);

    return { loader, loaderBar, loaderStatus, interval };
}

// Hide loader
function hideLoader(loader, interval) {
    clearInterval(interval);
    loader.classList.remove('shown');
    setTimeout(() => loader.classList.remove('on'), 400);
}

// Login with username and password
async function loginUser(username, password) {
    try {
        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: username, password: password })
        });

        const data = await response.json();

        if (data.success) {
            sessionStorage.setItem('nikita_auth', JSON.stringify({
                username: data.user.username,
                token: data.token,
                email: data.user.email || '',
                subscription_expiry: data.user.subscription_expiry || '',
                created_at: data.user.created_at || '',
                valid: true,
                timestamp: Date.now()
            }));
            return { success: true, message: 'Login successful!' };
        } else {
            return { success: false, message: data.message || 'Invalid username or password' };
        }
    } catch (error) {
        return { success: false, message: 'Connection failed - server unreachable' };
    }
}

// Handle login form submission
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const errorMessage = document.getElementById('errorMessage');
    const continueBtn = document.getElementById('continueBtn');
    const togglePassword = document.getElementById('togglePassword');

    // Password visibility toggle
    togglePassword.addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
        togglePassword.className = type === 'password' ? 'fas fa-eye toggle-password' : 'fas fa-eye-slash toggle-password';
    });

    // Form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        // Basic validation - both fields are required
        if (!username || !password) {
            errorMessage.textContent = 'Please enter both username and password';
            return;
        }

        // Show loading state
        continueBtn.disabled = true;
        continueBtn.classList.add('loading');
        continueBtn.querySelector('span').textContent = 'Logging in...';

        // Show loader animation
        const { loader, loaderBar, loaderStatus, interval } = showLoader();
        loaderStatus.textContent = 'Authenticating...';

        // Login with username and password
        const result = await loginUser(username, password);

        if (result.success) {
            loaderStatus.textContent = 'Success! Loading cheat...';
            loaderBar.style.background = 'linear-gradient(90deg, #00ff88, #00d46a)';

            setTimeout(() => {
                hideLoader(loader, interval);
                // Redirect to main cheat menu
                window.location.href = 'main.html';
            }, 800);
        } else {
            hideLoader(loader, interval);
            errorMessage.textContent = result.message;
            continueBtn.disabled = false;
            continueBtn.classList.remove('loading');
            continueBtn.querySelector('span').textContent = 'Continue';
        }
    });

    // Forgot password link
    document.querySelector('.forgot-password').addEventListener('click', (e) => {
        e.preventDefault();
        errorMessage.textContent = 'Contact support on Discord for key recovery';
    });
});

// Auto-format key input with dashes
function formatKeyInput(input) {
    input.addEventListener('input', (e) => {
        let value = e.target.value.replace(/-/g, '').replace(/\s/g, '').toUpperCase();
        let formatted = '';
        for (let i = 0; i < value.length; i += 5) {
            if (i > 0) formatted += '-';
            formatted += value.substring(i, i + 5);
        }
        e.target.value = formatted;
    });
}

