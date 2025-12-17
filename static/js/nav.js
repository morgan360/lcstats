// Navbar and Dropdown Menu Functionality

document.addEventListener('DOMContentLoaded', function() {
  const hamburger = document.getElementById('hamburger');
  const navMenu = document.getElementById('navMenu');
  const navOverlay = document.getElementById('navOverlay');
  const menuIcon = document.getElementById('menuIcon');
  const closeIcon = document.getElementById('closeIcon');
  const mobileDropdownToggles = document.querySelectorAll('.mobile-dropdown-toggle');
  const desktopDropdownToggles = document.querySelectorAll('.desktop-dropdown-toggle');
  const desktopDropdowns = document.querySelectorAll('.desktop-dropdown');

  function openMenu() {
    navMenu.classList.remove('-translate-x-full');
    navOverlay.classList.remove('hidden');
    menuIcon.classList.add('hidden');
    closeIcon.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  function closeMenu() {
    navMenu.classList.add('-translate-x-full');
    navOverlay.classList.add('hidden');
    menuIcon.classList.remove('hidden');
    closeIcon.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    document.querySelectorAll('.mobile-dropdown').forEach(menu => {
      menu.classList.add('hidden');
    });
  }

  function toggleMenu() {
    if (navMenu.classList.contains('-translate-x-full')) {
      openMenu();
    } else {
      closeMenu();
    }
  }

  function closeDesktopDropdowns() {
    desktopDropdowns.forEach(menu => {
      menu.classList.add('opacity-0', 'invisible', 'translate-y-1', 'pointer-events-none');
      menu.classList.remove('opacity-100', 'visible', 'translate-y-0', 'pointer-events-auto');
    });
  }

  function toggleDesktopDropdown(button) {
    const menu = button.nextElementSibling;
    if (!menu || !menu.classList.contains('desktop-dropdown')) return;
    const isOpen = !menu.classList.contains('opacity-0');
    closeDesktopDropdowns();
    if (!isOpen) {
      menu.classList.remove('opacity-0', 'invisible', 'translate-y-1', 'pointer-events-none');
      menu.classList.add('opacity-100', 'visible', 'translate-y-0', 'pointer-events-auto');
    }
  }

  hamburger.addEventListener('click', toggleMenu);
  navOverlay.addEventListener('click', closeMenu);

  mobileDropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', function(e) {
      e.preventDefault();
      const menu = this.nextElementSibling;
      if (menu) {
        menu.classList.toggle('hidden');
      }
    });
  });

  desktopDropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', function(e) {
      if (window.innerWidth >= 1024) {
        e.preventDefault();
        toggleDesktopDropdown(this);
      }
    });
  });

  document.addEventListener('click', function(e) {
    if (window.innerWidth < 1024) return;
    const isInside = e.target.closest('.desktop-dropdown') || e.target.closest('.desktop-dropdown-toggle');
    if (!isInside) {
      closeDesktopDropdowns();
    }
  });

  document.querySelectorAll('.nav-link:not(.dropdown-toggle), .dropdown-item').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeMenu();
      closeDesktopDropdowns();
    }
  });

  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      if (window.innerWidth >= 1024) {
        closeMenu();
        closeDesktopDropdowns();
      }
    }, 200);
  });
});
