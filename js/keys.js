var PUBLIC_N = "59596791868544965917715049293139712060670803368525004046780554740535049298561";
var PUBLIC_E = 65537n;

var _CH = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

var DURATION_SECONDS = {
    'L': null,
    'W': 7 * 24 * 60 * 60,
    'M': 30 * 24 * 60 * 60,
};

function b32Decode(str) {
    var bits = "";
    for (var i = 0; i < str.length; i++) {
        var val = _CH.indexOf(str[i]);
        if (val === -1) return null;
        bits += val.toString(2).padStart(5, '0');
    }
    var bytes = [];
    for (var i = 0; i < bits.length; i += 8) {
        if (i + 8 <= bits.length) {
            bytes.push(parseInt(bits.slice(i, i + 8), 2));
        }
    }
    return bytes;
}

function bytesToBigInt(bytes) {
    var hex = [];
    bytes.forEach(function(b) {
        hex.push(b.toString(16).padStart(2, '0'));
    });
    return BigInt("0x" + hex.join(""));
}

function _h(str) {
    var h = 0n;
    for (var i = 0; i < str.length; i++) {
        h = ((h * 31n) + BigInt(str.charCodeAt(i))) & 0xFFFFFFFFFFFFFFFFn;
    }
    return h;
}

function powerMod(base, exp, mod) {
    var res = 1n;
    base = base % mod;
    while (exp > 0n) {
        if (exp % 2n === 1n) res = (res * base) % mod;
        base = (base * base) % mod;
        exp = exp / 2n;
    }
    return res;
}

function isValidKey(key) {
    if (!key) return false;
    var clean = key.trim().toUpperCase().replace(/-/g, '');
    if (clean.length < 15) return false;

    var payload = clean.slice(0, 10);
    var sigStr = clean.slice(10);

    var sigBytes = b32Decode(sigStr);
    if (!sigBytes) return false;

    var sig = bytesToBigInt(sigBytes);
    var n = BigInt(PUBLIC_N);

    var decrypted = powerMod(sig, PUBLIC_E, n);
    var expectedHash = _h(payload);

    return decrypted === expectedHash;
}

function getKeyDuration(key) {
    if (!key) return null;
    var clean = key.trim().toUpperCase().replace(/-/g, '');
    if (clean.length < 10) return null;
    var durationChar = clean.charAt(9);
    return DURATION_SECONDS[durationChar] !== undefined ? DURATION_SECONDS[durationChar] : null;
}

function isKeyExpired(key, createdAt) {
    var duration = getKeyDuration(key);
    if (duration === null) return false;
    var expiresAt = createdAt + duration;
    return Date.now() > expiresAt * 1000;
}
