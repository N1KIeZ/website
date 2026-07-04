(function () {
    'use strict';

    var API_BASE = '/api';
    // Change API_BASE if your backend is on a different domain:
    // API_BASE = 'https://your-app.onrender.com/api';

    async function api(path, options) {
        var opts = options || {};
        var headers = { 'Content-Type': 'application/json' };
        if (opts.headers) {
            for (var k in opts.headers) {
                if (opts.headers.hasOwnProperty(k)) headers[k] = opts.headers[k];
            }
        }
        opts.headers = headers;
        var res = await fetch(API_BASE + path, opts);
        var data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Request failed');
        }
        return data;
    }

    async function validateKey(key, hwid) {
        return api('/validate', {
            method: 'POST',
            body: JSON.stringify({ key: key.trim().toUpperCase(), hwid: hwid || null }),
        });
    }

    async function checkKey(key) {
        return api('/check', {
            method: 'POST',
            body: JSON.stringify({ key: key.trim().toUpperCase() }),
        });
    }

    async function generateKeys(amount, adminKey) {
        return api('/generate', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminKey },
            body: JSON.stringify({ amount: amount }),
        });
    }

    async function getStock(adminKey) {
        return api('/stock', {
            headers: { 'Authorization': 'Bearer ' + adminKey },
        });
    }

    async function listKeys(adminKey) {
        return api('/keys', {
            headers: { 'Authorization': 'Bearer ' + adminKey },
        });
    }

    async function banKey(key, adminKey) {
        return api('/ban', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminKey },
            body: JSON.stringify({ key: key.trim().toUpperCase() }),
        });
    }

    async function unbanKey(key, adminKey) {
        return api('/unban', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminKey },
            body: JSON.stringify({ key: key.trim().toUpperCase() }),
        });
    }

    async function health() {
        return api('/health');
    }

    window.KeySystem = {
        validateKey: validateKey,
        checkKey: checkKey,
        generateKeys: generateKeys,
        getStock: getStock,
        listKeys: listKeys,
        banKey: banKey,
        unbanKey: unbanKey,
        health: health,
        API_BASE: API_BASE,
    };
})();
