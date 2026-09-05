/**
 * StudyBuddy Frontend Client Script
 * Handles UI interactions, theme toggle, mobile drawer, toasts, modal notes, and course filtering.
 */

(() => {
  'use strict';

  // --- Theme Management ---
  function initTheme() {
    const toggleBtn = document.querySelector('[data-theme-toggle]');
    if (!toggleBtn) return;

    function updateToggleIcon(isDark) {
      toggleBtn.setAttribute('aria-pressed', String(isDark));
      toggleBtn.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      toggleBtn.innerHTML = `<i data-lucide="${isDark ? 'sun' : 'moon'}"></i>`;
      if (window.lucide) window.lucide.createIcons();
    }

    const currentTheme = document.documentElement.classList.contains('dark-theme') ? 'dark' : 'light';
    updateToggleIcon(currentTheme === 'dark');

    toggleBtn.addEventListener('click', () => {
      const isDark = document.documentElement.classList.toggle('dark-theme');
      const themeName = isDark ? 'dark' : 'light';
      localStorage.setItem('studybuddy-theme', themeName);
      updateToggleIcon(isDark);
    });
  }

  // --- Mobile Drawer Navigation ---
  function initMobileDrawer() {
    const openBtn = document.querySelector('.mobile-menu-button');
    const drawer = document.querySelector('.mobile-drawer');
    const backdrop = document.querySelector('.mobile-drawer-backdrop');
    const closeBtn = document.querySelector('.mobile-drawer-close');

    if (!openBtn || !drawer || !backdrop) return;

    function openDrawer() {
      drawer.classList.add('is-open');
      backdrop.classList.add('is-open');
      openBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
      drawer.classList.remove('is-open');
      backdrop.classList.remove('is-open');
      openBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    openBtn.addEventListener('click', openDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    backdrop.addEventListener('click', closeDrawer);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawer.classList.contains('is-open')) {
        closeDrawer();
      }
    });

    drawer.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeDrawer);
    });
  }

  // --- Toast & Flash Alert Dismissal ---
  function initAlerts() {
    document.querySelectorAll('.alert').forEach((alert) => {
      const dismissBtn = alert.querySelector('.alert-dismiss');
      if (dismissBtn) {
        dismissBtn.addEventListener('click', () => {
          alert.style.transition = 'opacity 200ms ease, transform 200ms ease';
          alert.style.opacity = '0';
          alert.style.transform = 'translateY(-6px)';
          setTimeout(() => alert.remove(), 220);
        });
      }

      // Optional auto-dismiss after 6 seconds
      setTimeout(() => {
        if (document.body.contains(alert)) {
          alert.style.transition = 'opacity 300ms ease, transform 300ms ease';
          alert.style.opacity = '0';
          alert.style.transform = 'translateY(-6px)';
          setTimeout(() => alert.remove(), 320);
        }
      }, 6000);
    });
  }

  // --- Password Visibility Toggle ---
  function initPasswordToggles() {
    document.querySelectorAll('[data-toggle-password]').forEach((btn) => {
      const inputSelector = btn.getAttribute('data-toggle-password');
      const input = document.querySelector(inputSelector);
      if (!input) return;

      btn.addEventListener('click', () => {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        btn.innerHTML = `<i data-lucide="${isPassword ? 'eye-off' : 'eye'}"></i>`;
        if (window.lucide) window.lucide.createIcons();
      });
    });
  }

  // --- Study Request Custom Note Modal ---
  function initRequestModal() {
    const modal = document.querySelector('#study-request-modal');
    if (!modal) return;

    const backdrop = modal;
    const form = modal.querySelector('form');
    const closeBtns = modal.querySelectorAll('[data-close-modal]');
    const recipientNameSpan = modal.querySelector('#modal-partner-name');
    const messageTextarea = modal.querySelector('#modal-partner-message');

    function openModal(actionUrl, partnerName) {
      if (form) form.action = actionUrl;
      if (recipientNameSpan) recipientNameSpan.textContent = partnerName || 'study partner';
      if (messageTextarea) {
        messageTextarea.value = "Hi! I'd love to connect and study together for our courses.";
      }
      backdrop.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      if (messageTextarea) messageTextarea.focus();
    }

    function closeModal() {
      backdrop.classList.remove('is-open');
      document.body.style.overflow = '';
    }

    document.querySelectorAll('[data-open-request-modal]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const actionUrl = btn.getAttribute('data-action-url');
        const partnerName = btn.getAttribute('data-partner-name');
        openModal(actionUrl, partnerName);
      });
    });

    closeBtns.forEach((btn) => btn.addEventListener('click', closeModal));
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && backdrop.classList.contains('is-open')) {
        closeModal();
      }
    });
  }

  // --- Requests Page Tabs (Received vs Sent) ---
  function initRequestTabs() {
    const tabs = document.querySelectorAll('[data-request-tab]');
    const sections = {
      received: document.querySelector('#section-received-requests'),
      sent: document.querySelector('#section-sent-requests'),
    };

    if (!tabs.length || !sections.received || !sections.sent) return;

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-request-tab');
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');

        if (target === 'received') {
          sections.received.style.display = 'block';
          sections.sent.style.display = 'none';
        } else if (target === 'sent') {
          sections.received.style.display = 'none';
          sections.sent.style.display = 'block';
        } else {
          sections.received.style.display = 'block';
          sections.sent.style.display = 'block';
        }
      });
    });
  }

  // --- Course Card Checkbox Interactivity & Quick Filter ---
  function initCoursePicker() {
    const cards = document.querySelectorAll('.course-checkbox-card');
    cards.forEach((card) => {
      const checkbox = card.querySelector('input[type="checkbox"]');
      if (!checkbox) return;

      if (checkbox.checked) {
        card.classList.add('is-checked');
      }

      card.addEventListener('click', (e) => {
        if (e.target !== checkbox) {
          checkbox.checked = !checkbox.checked;
          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });

      checkbox.addEventListener('change', () => {
        card.classList.toggle('is-checked', checkbox.checked);
      });
    });

    const filterInput = document.querySelector('#course-search-filter');
    if (filterInput) {
      filterInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        cards.forEach((card) => {
          const text = card.textContent.toLowerCase();
          card.style.display = text.includes(query) ? 'flex' : 'none';
        });
      });
    }
  }

  // --- Form Draft Autosave ---
  function initDraftProtection() {
    document.querySelectorAll('form[data-draft-key]').forEach((form) => {
      const key = `studybuddy-draft:${form.dataset.draftKey}`;
      const fields = [...form.querySelectorAll('input, select, textarea')].filter(
        (field) => field.name && field.type !== 'hidden' && field.type !== 'password'
      );
      try {
        const saved = JSON.parse(localStorage.getItem(key) || '{}');
        fields.forEach((field) => {
          if (saved[field.name] !== undefined && !field.value) {
            field.value = saved[field.name];
          }
          field.addEventListener('input', () => {
            const draft = Object.fromEntries(fields.map((item) => [item.name, item.value]));
            localStorage.setItem(key, JSON.stringify(draft));
          });
        });
        form.addEventListener('submit', () => localStorage.removeItem(key));
      } catch (err) {
        console.warn('Draft protection error', err);
      }
    });
  }

  // --- DOM Ready ---
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initMobileDrawer();
    initAlerts();
    initPasswordToggles();
    initRequestModal();
    initRequestTabs();
    initCoursePicker();
    initDraftProtection();

    if (window.lucide) {
      window.lucide.createIcons();
    }
  });
})();
