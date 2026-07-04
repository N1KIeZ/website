(function() {
    'use strict';

    const HWID_KEY = 'license_hwid';
    const LICENSE_KEY = 'license_key';
    const LICENSE_STATUS_KEY = 'license_status';
    const API_BASE = '/api';

    function generateFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('license-fingerprint', 2, 2);
        const canvasFp = canvas.toDataURL();

        const screenInfo = [
            screen.width,
            screen.height,
            screen.colorDepth,
            screen.pixelDepth
        ].join('|');

        const navInfo = [
            navigator.userAgent,
            navigator.language,
            navigator.platform,
            navigator.hardwareConcurrency || 0,
            navigator.deviceMemory || 0
        ].join('|');

        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const plugins = Array.from(navigator.plugins).map(p => p.name).sort().join('|');
        const mimeTypes = Array.from(navigator.mimeTypes).map(m => m.type).sort().join('|');

        const combined = [
            canvasFp,
            screenInfo,
            navInfo,
            tz,
            plugins,
            mimeTypes
        ].join('||');

        let hash = 0;
        for (let i = 0; i < combined.length; i++) {
            const char = combined.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        hash = Math.abs(hash).toString(36);

        const extra = Math.random().toString(36).substring(2, 8);
        return `HWID-${hash}-${extra}`.toUpperCase();
    }

    function getHWID() {
        let hwid = localStorage.getItem(HWID_KEY);
        if (!hwid) {
            hwid = generateFingerprint();
            localStorage.setItem(HWID_KEY, hwid);
        }
        return hwid;
    }

    function resetHWID() {
        localStorage.removeItem(HWID_KEY);
        return getHWID();
    }

    async function validateKey(key) {
        const hwid = getHWID();
        const response = await fetch(`${API_BASE}/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: key.trim().toUpperCase(), hwid })
        });
        const data = await response.json();
        
        if (data.valid) {
            localStorage.setItem(LICENSE_KEY, key.trim().toUpperCase());
            localStorage.setItem(LICENSE_STATUS_KEY, JSON.stringify(data));
            return { valid: true, message: data.message, key: data.key };
        }
        
        localStorage.setItem(LICENSE_STATUS_KEY, JSON.stringify(data));
        return { valid: false, message: data.message };
    }

    function getStoredKey() {
        return localStorage.getItem(LICENSE_KEY);
    }

    function getStoredStatus() {
        try {
            return JSON.parse(localStorage.getItem(LICENSE_STATUS_KEY) || '{}');
        } catch {
            return {};
        }
    }

    function clearLicense() {
        localStorage.removeItem(LICENSE_KEY);
        localStorage.removeItem(LICENSE_STATUS_KEY);
    }

    async function checkLicenseOnLoad() {
        const storedKey = getStoredKey();
        if (!storedKey) return { valid: false, message: 'No license key stored' };
        
        const status = getStoredStatus();
        if (status.valid && status.key) {
            const hwid = getHWID();
            if (status.key.hwid && status.key.hwid !== hwid) {
                clearLicense();
                return { valid: false, message: 'License key locked to different device' };
            }
            return { valid: true, message: 'License valid', key: status.key };
        }
        
        return await validateKey(storedKey);
    }

    async function generateKeys(amount, adminKey) {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminKey}`
            },
            body: JSON.stringify({ amount })
        });
        return await response.json();
    }

    async function getStock(adminKey) {
        const response = await fetch(`${API_BASE}/stock`, {
            headers: { 'Authorization': `Bearer ${adminKey}` }
        });
        return await response.json();
    }

    async function banKey(key, adminKey) {
        const response = await fetch(`${API_BASE}/ban`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminKey}`
            },
            body: JSON.stringify({ key })
        });
        return await response.json();
    }

    async function unbanKey(key, adminKey) {
        const response = await fetch(`${API_BASE}/unban`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminKey}`
            },
            body: JSON.stringify({ key })
        });
        return await response.json();
    }

    async function listKeys(adminKey) {
        const response = await fetch(`${API_BASE}/keys`, {
            headers: { 'Authorization': `Bearer ${adminKey}` }
        });
        return await response.json();
    }

    window.LicenseSystem = {
        getHWID,
        resetHWID,
        validateKey,
        getStoredKey,
        getStoredStatus,
        clearLicense,
        checkLicenseOnLoad,
        generateKeys,
        getStock,
        banKey,
        unbanKey,
        listKeys,
        API_BASE
    };
})();