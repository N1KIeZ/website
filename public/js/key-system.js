/**
 * key-system.js — Unified Key System API for nikita.gg
 * Used by both the main site and admin dashboard.
 * Connects to the FastAPI backend.
 */
(function () {
    'use strict';

    var API_BASE = '/api';

    // ── Generic API helpers ──────────────────────────────
    function apiGet(path, token) {
        var headers = {};
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return fetch(API_BASE + path, { headers: headers })
            .then(function (r) {
                if (!r.ok) throw new Error('Request failed: ' + r.status);
                return r.json();
            });
    }

    function apiPost(path, body, token) {
        var headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return fetch(API_BASE + path, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(body)
        }).then(function (r) {
            if (!r.ok) return r.json().then(function (e) { throw new Error(e.detail || 'Request failed'); });
            return r.json();
        });
    }

    // ── Public API ───────────────────────────────────────
    var KeySystem = {
        // Validate a license key (with optional HWID)
        validateKey: function (key, hwid) {
            return apiPost('/validate', { key: key, hwid: hwid || null });
        },

        // Check if a key has a valid cryptographic signature (client-side)
        isValidKey: function (key) {
            if (!key) return false;
            var clean = key.trim().toUpperCase().replace(/-/g, '');
            if (clean.length < 15) return false;
            var payload = clean.slice(0, 10);
            var sigStr = clean.slice(10);
            var sigBytes = b32Decode(sigStr);
            if (!sigBytes) return false;
            var sig = bytesToBigInt(sigBytes);
            var n = BigInt("59596791868544965917715049293139712060670803368525004046780554740535049298561");
            var decrypted = powerMod(sig, 65537n, n);
            var expectedHash = _h(payload);
            return decrypted === expectedHash;
        },

        // Generate keys (admin only)
        generateKeys: function (amount, adminKey) {
            return apiPost('/generate', { amount: amount }, adminKey);
        },

        // Get stock counts (admin only)
        getStock: function (adminKey) {
            return apiGet('/stock', adminKey);
        },

        // List all keys (admin only)
        listKeys: function (adminKey) {
            return apiGet('/keys', adminKey);
        },

        // Ban a key (admin only)
        banKey: function (key, adminKey) {
            return apiPost('/ban', { key: key }, adminKey);
        },

        // Unban a key (admin only)
        unbanKey: function (key, adminKey) {
            return apiPost('/unban', { key: key }, adminKey);
        },

        // Register a new user
        register: function (username, password, key) {
            return apiPost('/register', { username: username, password: password, key: key });
        },

        // Login
        login: function (username, password) {
            return apiPost('/login', { username: username, password: password });
        },

        // Get current session
        getSession: function (token) {
            return apiGet('/session', token);
        },

        // Health check
        health: function () {
            return apiGet('/health');
        },

        API_BASE: API_BASE
    };

    // ── Client-side RSA helpers (mirrors keygen.py) ──────
    var _CH = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

    function b32Decode(str) {
        var bits = "";
        for (var i = 0; i < str.length; i++) {
            var val = _CH.indexOf(str[i]);
            if (val === -1) return null;
            bits += val.toString(2).padStart(5, '0');
        }
        var bytes = [];
        for (var i = 0; i < bits.length; i += 8) {
            if (i + 8 <= bits.length) bytes.push(parseInt(bits.slice(i, i + 8), 2));
        }
        return bytes;
    }

    function bytesToBigInt(bytes) {
        var hex = [];
        bytes.forEach(function (b) { hex.push(b.toString(16).padStart(2, '0')); });
        return BigInt("0x" + hex.join(""));
    }

    function _h(s) {
        var h = 0n;
        for (var i = 0; i < s.length; i++) h = ((h * 31n) + BigInt(s.charCodeAt(i))) & 0xFFFFFFFFFFFFFFFFn;
        return h;
    }

    function powerMod(base, exp, mod) {
        var r = 1n; base = base % mod;
        while (exp > 0n) { if (exp % 2n === 1n) r = (r * base) % mod; base = (base * base) % mod; exp = exp / 2n; }
        return r;
    }

    // ── Expose globally ──────────────────────────────────
    window.KeySystem = KeySystem;
    window.isValidKey = KeySystem.isValidKey;
})();