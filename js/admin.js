(function() {
    'use strict';

    const ADMIN_KEY_KEY = 'admin_api_key';
    const DEFAULT_ADMIN_KEY = 'ADMIN-KEY-CHANGE-ME';

    let currentAdminKey = localStorage.getItem(ADMIN_KEY_KEY) || DEFAULT_ADMIN_KEY;
    let keysData = [];
    let selectedKeys = new Set();

    function setAdminKey(key) {
        currentAdminKey = key;
        localStorage.setItem(ADMIN_KEY_KEY, key);
    }

    function getAdminKey() {
        return currentAdminKey;
    }

    function showAdminAuth() {
        document.getElementById('admin-auth').style.display = 'block';
        document.getElementById('admin-dashboard').style.display = 'none';
    }

    function showAdminDashboard() {
        document.getElementById('admin-auth').style.display = 'none';
        document.getElementById('admin-dashboard').style.display = 'block';
        loadDashboardData();
    }

    async function verifyAdminKey() {
        try {
            const response = await fetch('/api/stock', {
                headers: { 'Authorization': `Bearer ${currentAdminKey}` }
            });
            if (response.ok) {
                showAdminDashboard();
                return true;
            }
        } catch (e) {}
        showAdminAuth();
        return false;
    }

    function renderKeys(keys) {
        const tbody = document.getElementById('keys-tbody');
        tbody.innerHTML = '';
        keysData = keys;

        keys.forEach((key, index) => {
            const tr = document.createElement('tr');
            tr.dataset.key = key.key;
            
            let statusClass = '';
            let statusText = key.status;
            if (key.status === 'available') { statusClass = 'status-available'; statusText = 'Available'; }
            else if (key.status === 'used') { statusClass = 'status-used'; statusText = 'Activated'; }
            else if (key.status === 'banned') { statusClass = 'status-banned'; statusText = 'Banned'; }

            const hwid = key.hwid ? `<span class="hwid">${key.hwid.substring(0, 12)}...</span>` : '-';
            const activated = key.activated_at ? new Date(key.activated_at).toLocaleDateString() : '-';

            tr.innerHTML = `
                <td><input type="checkbox" class="key-checkbox" value="${key.key}"></td>
                <td class="key-cell">${key.key}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${hwid}</td>
                <td>${activated}</td>
                <td>${key.created ? new Date(key.created).toLocaleDateString() : '-'}</td>
                <td>
                    <button class="btn-icon btn-ban" data-key="${key.key}" ${key.status === 'banned' ? 'disabled' : ''}>Ban</button>
                    <button class="btn-icon btn-unban" data-key="${key.key}" ${key.status !== 'banned' ? 'disabled' : ''}>Unban</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        attachKeyActions();
        updateSelectionUI();
    }

    function attachKeyActions() {
        document.querySelectorAll('.key-checkbox').forEach(cb => {
            cb.addEventListener('change', () => {
                const key = cb.value;
                if (cb.checked) selectedKeys.add(key);
                else selectedKeys.delete(key);
                updateSelectionUI();
            });
        });

        document.querySelectorAll('.btn-ban').forEach(btn => {
            btn.addEventListener('click', async () => {
                const key = btn.dataset.key;
                await banKey(key);
            });
        });

        document.querySelectorAll('.btn-unban').forEach(btn => {
            btn.addEventListener('click', async () => {
                const key = btn.dataset.key;
                await unbanKey(key);
            });
        });
    }

    function updateSelectionUI() {
        const count = selectedKeys.size;
        document.getElementById('selection-count').textContent = `${count} selected`;
        document.getElementById('btn-ban-selected').disabled = count === 0;
        document.getElementById('btn-unban-selected').disabled = count === 0;
        document.getElementById('btn-copy-selected').disabled = count === 0;
    }

    async function loadDashboardData() {
        try {
            document.getElementById('loading-indicator').style.display = 'block';
            
            const [stockRes, keysRes] = await Promise.all([
                fetch('/api/stock', { headers: { 'Authorization': `Bearer ${currentAdminKey}` } }),
                fetch('/api/keys', { headers: { 'Authorization': `Bearer ${currentAdminKey}` } })
            ]);

            const stock = await stockRes.json();
            const keysResult = await keysRes.json();

            document.getElementById('stat-available').textContent = stock.available;
            document.getElementById('stat-used').textContent = stock.used;
            document.getElementById('stat-banned').textContent = stock.banned;

            renderKeys(keysResult.keys);
        } catch (e) {
            console.error('Failed to load dashboard:', e);
            showToast('Failed to load dashboard data', 'error');
        } finally {
            document.getElementById('loading-indicator').style.display = 'none';
        }
    }

    async function generateKeys() {
        const amount = parseInt(document.getElementById('gen-amount').value) || 1;
        if (amount < 1 || amount > 1000) {
            showToast('Amount must be between 1 and 1000', 'error');
            return;
        }

        try {
            const keys = await LicenseSystem.generateKeys(amount, currentAdminKey);
            showToast(`Generated ${keys.length} key(s)`, 'success');
            document.getElementById('gen-amount').value = 1;
            loadDashboardData();
        } catch (e) {
            showToast('Failed to generate keys', 'error');
        }
    }

    async function banKey(key) {
        try {
            const result = await LicenseSystem.banKey(key, currentAdminKey);
            if (result.success) {
                showToast('Key banned', 'success');
                loadDashboardData();
            } else {
                showToast(result.message || 'Failed to ban key', 'error');
            }
        } catch (e) {
            showToast('Failed to ban key', 'error');
        }
    }

    async function unbanKey(key) {
        try {
            const result = await LicenseSystem.unbanKey(key, currentAdminKey);
            if (result.success) {
                showToast('Key unbanned', 'success');
                loadDashboardData();
            } else {
                showToast(result.message || 'Failed to unban key', 'error');
            }
        } catch (e) {
            showToast('Failed to unban key', 'error');
        }
    }

    async function banSelected() {
        const keys = Array.from(selectedKeys);
        for (const key of keys) {
            await LicenseSystem.banKey(key, currentAdminKey);
        }
        showToast(`Banned ${keys.length} key(s)`, 'success');
        selectedKeys.clear();
        loadDashboardData();
    }

    async function unbanSelected() {
        const keys = Array.from(selectedKeys);
        for (const key of keys) {
            await LicenseSystem.unbanKey(key, currentAdminKey);
        }
        showToast(`Unbanned ${keys.length} key(s)`, 'success');
        selectedKeys.clear();
        loadDashboardData();
    }

    function copySelected() {
        const keys = Array.from(selectedKeys);
        if (keys.length === 0) return;
        navigator.clipboard.writeText(keys.join('\n'));
        showToast(`Copied ${keys.length} key(s) to clipboard`, 'success');
    }

    function selectAll() {
        const checkboxes = document.querySelectorAll('.key-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = true;
            selectedKeys.add(cb.value);
        });
        updateSelectionUI();
    }

    function deselectAll() {
        const checkboxes = document.querySelectorAll('.key-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
        selectedKeys.clear();
        updateSelectionUI();
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function exportKeys() {
        if (keysData.length === 0) {
            showToast('No keys to export', 'error');
            return;
        }
        const csv = ['Key,Status,HWID,Activated,Created'];
        keysData.forEach(k => {
            csv.push(`"${k.key}","${k.status}","${k.hwid || ''}","${k.activated_at || ''}","${k.created || ''}"`);
        });
        const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `keys-export-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Keys exported to CSV', 'success');
    }

    document.addEventListener('DOMContentLoaded', () => {
        const adminKeyInput = document.getElementById('admin-key-input');
        if (adminKeyInput) {
            adminKeyInput.value = currentAdminKey;
        }

        const authForm = document.getElementById('admin-auth-form');
        if (authForm) {
            authForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const key = document.getElementById('admin-key-input').value.trim();
                if (key) {
                    setAdminKey(key);
                    verifyAdminKey();
                }
            });
        }

        const genBtn = document.getElementById('btn-generate');
        if (genBtn) genBtn.addEventListener('click', generateKeys);

        const banSelBtn = document.getElementById('btn-ban-selected');
        if (banSelBtn) banSelBtn.addEventListener('click', banSelected);

        const unbanSelBtn = document.getElementById('btn-unban-selected');
        if (unbanSelBtn) unbanSelBtn.addEventListener('click', unbanSelected);

        const copySelBtn = document.getElementById('btn-copy-selected');
        if (copySelBtn) copySelBtn.addEventListener('click', copySelected);

        const selectAllBtn = document.getElementById('btn-select-all');
        if (selectAllBtn) selectAllBtn.addEventListener('click', selectAll);

        const deselectAllBtn = document.getElementById('btn-deselect-all');
        if (deselectAllBtn) deselectAllBtn.addEventListener('click', deselectAll);

        const exportBtn = document.getElementById('btn-export');
        if (exportBtn) exportBtn.addEventListener('click', exportKeys);

        const logoutBtn = document.getElementById('btn-admin-logout');
        if (logoutBtn) logoutBtn.addEventListener('click', () => {
            localStorage.removeItem(ADMIN_KEY_KEY);
            currentAdminKey = DEFAULT_ADMIN_KEY;
            showAdminAuth();
        });

        verifyAdminKey();
    });

    window.AdminDashboard = {
        setAdminKey,
        getAdminKey,
        verifyAdminKey,
        loadDashboardData,
        showAdminAuth,
        showAdminDashboard
    };
})();