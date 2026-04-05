const API_BASE = '/api';

function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function clearToken() {
    localStorage.removeItem('token');
}

async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const resp = await fetch(API_BASE + url, { ...options, headers });
    if (resp.status === 401) {
        clearToken();
        showAuthView();
        throw new Error('Unauthorized');
    }
    return resp;
}

function showAuthView() {
    document.getElementById('auth-view').style.display = 'flex';
    document.getElementById('dashboard-view').style.display = 'none';
}

function showDashboard() {
    document.getElementById('auth-view').style.display = 'none';
    document.getElementById('dashboard-view').style.display = 'block';
    loadDashboard();
}

let isLoginMode = true;

document.getElementById('toggle-auth').addEventListener('click', (e) => {
    e.preventDefault();
    isLoginMode = !isLoginMode;
    document.getElementById('auth-btn-text').textContent = isLoginMode ? 'Sign in' : 'Create account';
    document.getElementById('auth-title').textContent = isLoginMode ? 'Welcome back' : 'Get started';
    document.getElementById('auth-subtitle').textContent = isLoginMode
        ? 'Sign in to your account to continue'
        : 'Create an account to start your journey';
    document.getElementById('toggle-label').textContent = isLoginMode
        ? "Don't have an account?"
        : "Already have an account?";
    document.getElementById('toggle-auth').textContent = isLoginMode ? 'Create one' : 'Sign in';
    document.getElementById('auth-error').textContent = '';
});

document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    const errorEl = document.getElementById('auth-error');
    errorEl.textContent = '';

    const endpoint = isLoginMode ? '/auth/login' : '/auth/register';

    try {
        const resp = await fetch(API_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();
        if (!resp.ok) {
            errorEl.textContent = data.error || 'Something went wrong';
            return;
        }
        setToken(data.token);
        showDashboard();
    } catch (err) {
        errorEl.textContent = 'Network error. Please try again.';
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    clearToken();
    showAuthView();
});

// Password visibility toggle
document.getElementById('password-toggle').addEventListener('click', () => {
    const pw = document.getElementById('auth-password');
    pw.type = pw.type === 'password' ? 'text' : 'password';
});

// Auto-login moved to app.js (must run after loadDashboard is defined)
