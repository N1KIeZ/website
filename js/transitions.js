function enterDashboard(username) {
    document.getElementById('dash-user').textContent = username;
    setCurrentUser(username);

    var loader = document.getElementById('loader');
    var fill = document.getElementById('loader-fill');
    var status = document.getElementById('loader-status');

    fill.style.width = '0%';
    status.textContent = 'authenticating...';
    loader.classList.add('on');
    requestAnimationFrame(function() { loader.classList.add('shown'); });

    var steps = [
        [300,  '30%', 'authenticating...'],
        [900,  '65%', 'loading dashboard...'],
        [1500, '100%', '<span class="ok">access granted</span>']
    ];
    steps.forEach(function(s) {
        setTimeout(function() {
            fill.style.width = s[1];
            status.innerHTML = s[2];
        }, s[0]);
    });

    setTimeout(function() {
        show('dashboard');
        document.getElementById('main-nav').style.display = 'none';
        updateNavUnderline();
        var dash = document.getElementById('view-dashboard');
        dash.classList.remove('enter');
        void dash.offsetWidth;
        dash.classList.add('enter');
        loader.classList.remove('shown');
        setTimeout(function() { loader.classList.remove('on'); }, 400);
        startBanPolling();
    }, 2100);
}

function logout() {
    var loader = document.getElementById('loader');
    var fill = document.getElementById('loader-fill');
    var status = document.getElementById('loader-status');

    if (banCheckInterval) clearInterval(banCheckInterval);

    var dash = document.getElementById('view-dashboard');
    dash.classList.remove('enter');
    dash.classList.add('leave');

    fill.style.width = '0%';
    status.textContent = 'signing out...';
    loader.classList.add('on');
    requestAnimationFrame(function() { loader.classList.add('shown'); });

    var steps = [
        [250,  '45%', 'signing out...'],
        [800,  '100%', 'ending session...'],
        [1300, '100%', '<span class="ok">session closed</span>']
    ];
    steps.forEach(function(s) {
        setTimeout(function() {
            fill.style.width = s[1];
            status.innerHTML = s[2];
        }, s[0]);
    });

    setTimeout(function() {
        clearCurrentUser();
        document.getElementById('form-login').reset();
        document.getElementById('form-register').reset();
        newCaptcha('register');
        newCaptcha('login');
        dash.classList.remove('leave');
        document.getElementById('main-nav').style.display = '';
        show('home');
        var logo = document.querySelector('#view-home .logo');
        logo.classList.remove('enter');
        void logo.offsetWidth;
        logo.classList.add('enter');
        loader.classList.remove('shown');
        setTimeout(function() { loader.classList.remove('on'); }, 400);
    }, 1900);
}

function banLogout() {
    var loader = document.getElementById('loader');
    var fill = document.getElementById('loader-fill');
    var status = document.getElementById('loader-status');

    if (banCheckInterval) clearInterval(banCheckInterval);

    fill.style.width = '0%';
    status.textContent = 'terminating session...';
    loader.classList.add('on');
    requestAnimationFrame(function() { loader.classList.add('shown'); });

    var steps = [
        [300,  '50%', 'revoking access...'],
        [800,  '100%', '<span style="color:#ff4d6a">access denied</span>'],
        [1400, '100%', 'session terminated']
    ];
    steps.forEach(function(s) {
        setTimeout(function() {
            fill.style.width = s[1];
            status.innerHTML = s[2];
        }, s[0]);
    });

    setTimeout(function() {
        clearCurrentUser();
        document.getElementById('form-login').reset();
        document.getElementById('form-register').reset();
        newCaptcha('register');
        newCaptcha('login');
        document.getElementById('main-nav').style.display = '';
        show('home');
        var logo = document.querySelector('#view-home .logo');
        logo.classList.remove('enter');
        void logo.offsetWidth;
        logo.classList.add('enter');
        loader.classList.remove('shown');
        setTimeout(function() { loader.classList.remove('on'); }, 400);
    }, 2000);
}
