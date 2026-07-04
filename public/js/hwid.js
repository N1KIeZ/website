(function () {
    'use strict';

    const STORAGE_KEY = 'license_hwid';

    function generateFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.textAlign = 'left';
            ctx.fillText('license-hwid-' + Math.random(), 2, 2);
            const canvasFp = canvas.toDataURL();

            const screenInfo = [
                screen.width,
                screen.height,
                screen.colorDepth,
                screen.pixelDepth,
                screen.availWidth,
                screen.availHeight,
            ].join('|');

            const navInfo = [
                navigator.userAgent,
                navigator.language,
                navigator.platform,
                navigator.hardwareConcurrency || 0,
                navigator.deviceMemory || 0,
            ].join('|');

            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const plugins = Array.from(navigator.plugins || [])
                .map(function (p) { return p.name; })
                .sort()
                .join('|');

            const combined = [
                canvasFp,
                screenInfo,
                navInfo,
                tz,
                plugins,
            ].join('||');

            let hash = 0;
            for (let i = 0; i < combined.length; i++) {
                const ch = combined.charCodeAt(i);
                hash = ((hash << 5) - hash) + ch;
                hash = hash & hash;
            }
            hash = Math.abs(hash).toString(36);

            const extra = Math.random().toString(36).substring(2, 8);
            return ('HWID-' + hash + '-' + extra).toUpperCase();
        } catch (e) {
            return 'HWID-FALLBACK-' + Math.random().toString(36).substring(2, 10).toUpperCase();
        }
    }

    function getHWID() {
        let hwid = localStorage.getItem(STORAGE_KEY);
        if (!hwid || hwid.length < 10) {
            hwid = generateFingerprint();
            localStorage.setItem(STORAGE_KEY, hwid);
        }
        return hwid;
    }

    function resetHWID() {
        localStorage.removeItem(STORAGE_KEY);
        return getHWID();
    }

    window.HWID = {
        get: getHWID,
        reset: resetHWID,
        generate: generateFingerprint,
    };
})();
