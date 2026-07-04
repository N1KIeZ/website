const captchas = {};

function newCaptcha(which) {
    const a = Math.floor(Math.random() * 8) + 2;
    const b = Math.floor(Math.random() * 8) + 2;
    captchas[which] = a * b;
    document.getElementById('captcha-q-' + which).textContent = 'what is ' + a + ' × ' + b + '?';
    document.getElementById('captcha-a-' + which).value = '';
}

function checkCaptcha(which) {
    const val = document.getElementById('captcha-a-' + which).value.trim();
    return val !== '' && parseInt(val, 10) === captchas[which];
}

newCaptcha('register');
newCaptcha('login');
