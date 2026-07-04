function updateNavUnderline() {
    var bar = document.getElementById('nav-underline');
    var active = document.querySelector('#main-nav a.active');
    if (active) {
        bar.style.left = active.offsetLeft + 'px';
        bar.style.width = active.offsetWidth + 'px';
        bar.style.opacity = '1';
    } else {
        bar.style.opacity = '0';
    }
}
window.addEventListener('resize', updateNavUnderline);

function show(name) {
    document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('visible'); });
    document.getElementById('view-' + name).classList.add('visible');
    if (name !== 'banned') {
        document.querySelectorAll('#main-nav a').forEach(function(a) {
            a.classList.toggle('active', a.dataset.nav === name);
        });
    }
    updateNavUnderline();
    window.scrollTo(0, 0);
}

function showAuth(tab) {
    show('auth');
    document.getElementById('tab-register').classList.toggle('active', tab === 'register');
    document.getElementById('tab-login').classList.toggle('active', tab === 'login');
    document.getElementById('form-register').style.display = tab === 'register' ? '' : 'none';
    document.getElementById('form-login').style.display = tab === 'login' ? '' : 'none';
    document.querySelectorAll('#main-nav a').forEach(function(a) {
        a.classList.toggle('active', a.dataset.nav === tab);
    });
    updateNavUnderline();
    document.getElementById('err-register').textContent = '';
    document.getElementById('err-login').textContent = '';
}
