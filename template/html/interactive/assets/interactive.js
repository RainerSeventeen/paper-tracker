"use strict";

function initPaperToggle() {
  const cards = document.querySelectorAll(".paper-card");
  cards.forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        return;
      }
      card.classList.toggle("expanded");
    });
  });
}

function initThemeToggle() {
  const themeToggle = document.getElementById("theme-toggle");
  const root = document.body;
  if (!themeToggle || !root) {
    return;
  }

  const savedTheme = localStorage.getItem("paper-tracker-theme") || "light";
  root.classList.remove("theme-light", "theme-dark");
  root.classList.add(`theme-${savedTheme}`);

  themeToggle.addEventListener("click", () => {
    const current = root.classList.contains("theme-dark") ? "dark" : "light";
    const next = current === "dark" ? "light" : "dark";
    root.classList.remove(`theme-${current}`);
    root.classList.add(`theme-${next}`);
    localStorage.setItem("paper-tracker-theme", next);
  });
}

function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) {
    return;
  }

  const sections = document.querySelectorAll(".query-section");
  if (sections.length === 0) {
    return;
  }

  const nav = document.createElement("nav");
  nav.className = "sidebar-nav";

  sections.forEach((section) => {
    const title = section.querySelector("h2");
    if (!title || !section.id) {
      return;
    }
    const link = document.createElement("a");
    link.href = `#${section.id}`;
    link.textContent = title.textContent || section.id;
    link.className = "nav-link";
    nav.appendChild(link);
  });

  sidebar.appendChild(nav);
}

document.addEventListener("DOMContentLoaded", () => {
  initPaperToggle();
  initThemeToggle();
  initSidebar();
});
