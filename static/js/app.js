/**
 * Gentle Reminders — Shared UI Utilities
 * 暗色模式切换 · 涟漪反馈 · 移动菜单 · 图表主题刷新
 */
(function () {
    'use strict';

    /* ========== 暗色/浅色模式切换 ========== */
    const THEME_KEY = 'gr-theme';
    const DARK = 'dark';
    const LIGHT = 'light';

    function getStoredTheme() {
        try { return localStorage.getItem(THEME_KEY) || LIGHT; } catch (e) { return LIGHT; }
    }
    function setStoredTheme(t) {
        try { localStorage.setItem(THEME_KEY, t); } catch (e) { /* noop */ }
    }
    function applyTheme(theme) {
        if (theme === DARK) {
            document.documentElement.setAttribute('data-theme', DARK);
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }
    function toggleTheme() {
        const current = document.documentElement.hasAttribute('data-theme') ? DARK : LIGHT;
        const next = current === DARK ? LIGHT : DARK;
        applyTheme(next);
        setStoredTheme(next);
        updateThemeToggleIcon(next);
        if (window.__onThemeChange) window.__onThemeChange(next);
    }
    function updateThemeToggleIcon(theme) {
        var btns = document.querySelectorAll('.theme-toggle');
        btns.forEach(function (btn) {
            btn.textContent = theme === DARK ? '\u2600' : '\u263D';  /* ☀ / ☽ */
            btn.title = theme === DARK ? '切换浅色模式' : '切换暗色模式';
        });
    }

    // Initialize theme on load
    var saved = getStoredTheme();
    applyTheme(saved);
    document.addEventListener('DOMContentLoaded', function () {
        updateThemeToggleIcon(saved);
    });

    // Expose
    window.GR = window.GR || {};
    window.GR.toggleTheme = toggleTheme;
    window.GR.getTheme = function () {
        return document.documentElement.hasAttribute('data-theme') ? DARK : LIGHT;
    };
    window.GR.onThemeChange = function (fn) {
        window.__onThemeChange = fn;
    };

    /* ========== 按钮涟漪效果 ========== */
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.btn, .ripple');
        if (!btn || btn.disabled) return;

        var ripple = document.createElement('span');
        ripple.className = 'ripple-effect';
        var rect = btn.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
        btn.appendChild(ripple);
        ripple.addEventListener('animationend', function () { ripple.remove(); });
    });

    /* ========== 移动端汉堡菜单 ========== */
    document.addEventListener('DOMContentLoaded', function () {
        var navLinks = document.querySelector('.nav-links');
        if (!navLinks) return;

        // Create mobile menu button if it doesn't exist
        var existingBtn = document.querySelector('.mobile-menu-btn');
        if (!existingBtn) {
            var menuBtn = document.createElement('button');
            menuBtn.className = 'mobile-menu-btn';
            menuBtn.innerHTML = '\u2630'; /* ☰ */
            menuBtn.title = '菜单';
            menuBtn.addEventListener('click', function () {
                navLinks.classList.toggle('open');
                menuBtn.innerHTML = navLinks.classList.contains('open') ? '\u2715' : '\u2630';
            });
            var navbar = document.querySelector('.navbar');
            if (navbar) {
                navbar.insertBefore(menuBtn, navLinks);
            }
        }
    });

    /* ========== ECharts 暗色模式适配 ========== */
    window.GR.getChartTheme = function () {
        var isDark = document.documentElement.hasAttribute('data-theme');
        return {
            textStyle: { color: isDark ? '#A0A8B8' : '#6B7280' },
            axisLine: { lineStyle: { color: isDark ? '#3A3F4A' : '#E5E7EB' } },
            splitLine: { lineStyle: { color: isDark ? '#2D323A' : '#F0F2F5' } },
            backgroundColor: 'transparent'
        };
    };

    /* ========== Smooth number counter animation ========== */
    window.GR.animateNumber = function (el, target, duration) {
        duration = duration || 800;
        var start = 0;
        var startTime = null;
        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3); /* ease-out */
            el.textContent = Math.round(eased * target);
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    };

    window.GR.logout = function (target) {
        target = target || '/logout';
        if (confirm('确定要退出登录吗？')) window.location.href = target;
    };

    /* ========== Shared constants ========== */

    window.GR.EMO_COLORS = {
        '开心': '#4ECDC4', '放松': '#8FD4BE', '平静': '#7EB8DA',
        '低落': '#E07B7B', '焦虑': '#F0A050', '疲惫': '#9B8EC4'
    };

    window.GR.EMO_EMOJIS = {
        '开心': '😊', '放松': '😎', '平静': '😌', '低落': '😢', '焦虑': '😰', '疲惫': '😴'
    };

    window.GR.TREE_EMOJIS = ['🌱', '🌿', '🪴', '🌿', '🪴', '🌳', '🌳', '🌲', '🌲', '🌲'];

    window.GR.getTreeEmoji = function (level) {
        return level <= 10 ? window.GR.TREE_EMOJIS[Math.max(0, level - 1)] : '🌲';
    };

    /* ========== Toast 通知 ========== */
    var _toastTimer = null;
    var _toastEl = null;
    window.GR.toast = function (message, type) {
        type = type || 'info';
        var el = document.getElementById('gr-toast');
        if (!el) {
            el = document.createElement('div');
            el.id = 'gr-toast';
            el.className = 'toast-container';
            document.body.appendChild(el);
        }
        var toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.textContent = message;
        el.appendChild(toast);
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 3200);
    };

    /* ========== 登录/注册等全局函数 ========== */
})();
