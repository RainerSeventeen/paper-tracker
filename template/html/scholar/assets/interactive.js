"use strict";

const THEME_STORAGE_KEY = "paper-tracker-theme";

function listPaperDetails() {
  return Array.from(document.querySelectorAll("[data-paper-details]"));
}

function setAllDetails(expanded) {
  listPaperDetails().forEach((detail) => {
    detail.open = expanded;
  });
}

function initDetailControls() {
  const expandButton = document.getElementById("expand-all");
  const collapseButton = document.getElementById("collapse-all");

  if (expandButton) {
    expandButton.addEventListener("click", () => setAllDetails(true));
  }
  if (collapseButton) {
    collapseButton.addEventListener("click", () => setAllDetails(false));
  }
}

function applyTheme(root, toggleButton, theme) {
  const safeTheme = theme === "dark" ? "dark" : "light";
  root.classList.remove("theme-light", "theme-dark");
  root.classList.add(`theme-${safeTheme}`);
  if (toggleButton) {
    toggleButton.textContent = safeTheme === "dark" ? "切换浅色模式" : "切换暗色模式";
  }
}

function initThemeToggle() {
  const root = document.body;
  const toggleButton = document.getElementById("theme-toggle");
  if (!root) {
    return;
  }

  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) || "light";
  applyTheme(root, toggleButton, savedTheme);

  if (!toggleButton) {
    return;
  }

  toggleButton.addEventListener("click", () => {
    const isDark = root.classList.contains("theme-dark");
    const nextTheme = isDark ? "light" : "dark";
    applyTheme(root, toggleButton, nextTheme);
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  });
}

function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) {
    return [];
  }

  const sections = Array.from(document.querySelectorAll(".query-section"));
  if (sections.length === 0) {
    return [];
  }

  const nav = document.createElement("nav");
  nav.className = "sidebar-nav";

  const links = sections
    .map((section) => {
      const titleElement = section.querySelector(".query-header h2");
      if (!titleElement || !section.id) {
        return null;
      }

      const title = section.dataset.queryLabel || titleElement.textContent || section.id;
      const count = section.dataset.paperCount || "0";

      const link = document.createElement("a");
      link.href = `#${section.id}`;
      link.className = "nav-link";

      const titleNode = document.createElement("span");
      titleNode.className = "nav-link-title";
      titleNode.textContent = title;
      link.appendChild(titleNode);

      const metaNode = document.createElement("span");
      metaNode.className = "nav-link-meta";
      metaNode.textContent = `${count} 篇`;
      link.appendChild(metaNode);

      nav.appendChild(link);
      return { section, link };
    })
    .filter(Boolean);

  sidebar.appendChild(nav);
  return links;
}

function initActiveSectionHighlight(navItems) {
  if (!navItems.length) {
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const matched = navItems.find((item) => item.section === entry.target);
        if (!matched) {
          return;
        }

        if (entry.isIntersecting) {
          navItems.forEach((item) => item.link.classList.remove("is-active"));
          matched.link.classList.add("is-active");
        }
      });
    },
    {
      rootMargin: "-30% 0px -55% 0px",
      threshold: 0.1,
    },
  );

  navItems.forEach((item) => observer.observe(item.section));
}

function initPrintModeBehavior() {
  window.addEventListener("beforeprint", () => setAllDetails(true));
}

document.addEventListener("DOMContentLoaded", () => {
  initDetailControls();
  initThemeToggle();
  const navItems = initSidebar();
  initActiveSectionHighlight(navItems);
  initPrintModeBehavior();
});
