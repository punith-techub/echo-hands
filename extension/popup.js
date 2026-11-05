/**
 * Echo-Hands // Extension Popup Controller
 * Manages Python AI Backend URL and live connection status.
 */

document.addEventListener("DOMContentLoaded", () => {
  const backendInput = document.getElementById("eh-backend-input");
  const backendSaveBtn = document.getElementById("eh-backend-save-btn");
  const backendStatusTxt = document.getElementById("eh-backend-status-txt");
  const statusBadge = document.querySelector(".status-badge");

  const DEFAULT_BACKEND = "https://python-crouch-bucked.ngrok-free.dev";

  function resolveValidUrl(url) {
    if (!url || typeof url !== "string") return DEFAULT_BACKEND;
    const clean = url.trim().replace(/\/+$/, "");
    // Auto-migrate away from expired/rate-limited tunnels
    if (clean.includes("dark-dogs-flash") || clean.includes("loca.lt") || clean.length < 8) {
      return DEFAULT_BACKEND;
    }
    return clean;
  }

  // Load saved backend URL with auto-migration
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["backend_url"], (res) => {
      const savedUrl = resolveValidUrl(res ? res.backend_url : null);
      if (backendInput) backendInput.value = savedUrl;
      testConnection(savedUrl);
    });
  } else {
    const raw = localStorage.getItem("echohands_backend_url");
    const savedUrl = resolveValidUrl(raw);
    if (backendInput) backendInput.value = savedUrl;
    testConnection(savedUrl);
  }

  // Save backend URL
  if (backendSaveBtn && backendInput) {
    backendSaveBtn.addEventListener("click", () => {
      let rawUrl = backendInput.value.trim().replace(/\/+$/, "");
      if (!rawUrl) rawUrl = DEFAULT_BACKEND;
      backendInput.value = rawUrl;

      // Save to chrome.storage.local
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ backend_url: rawUrl }, () => {
          console.log("[Echo-Hands Popup] Saved backend URL:", rawUrl);
        });
      }

      // Save to localStorage
      try {
        localStorage.setItem("echohands_backend_url", rawUrl);
      } catch (e) {}

      // Notify active tabs about new backend URL
      if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
        chrome.tabs.query({}, (tabs) => {
          if (tabs && tabs.length > 0) {
            tabs.forEach((tab) => {
              if (tab.id) {
                chrome.tabs.sendMessage(tab.id, { type: "UPDATE_BACKEND_URL", url: rawUrl }).catch(() => {});
              }
            });
          }
        });
      }

      // Visual button feedback
      backendSaveBtn.textContent = "Saved ✓";
      backendSaveBtn.style.background = "#00ffcc";
      if (backendStatusTxt) {
        backendStatusTxt.textContent = "Testing connection to " + rawUrl + "...";
        backendStatusTxt.style.color = "#00e6b4";
      }

      testConnection(rawUrl);

      setTimeout(() => {
        if (backendSaveBtn) {
          backendSaveBtn.textContent = "Save";
          backendSaveBtn.style.background = "#00e6b4";
        }
      }, 1800);
    });
  }

  // Test live backend connection
  async function testConnection(url) {
    if (!url) return;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);

      const res = await fetch(`${url}/api/health`, {
        headers: { 
          "Bypass-Tunnel-Reminder": "true",
          "ngrok-skip-browser-warning": "69420"
        },
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (backendStatusTxt) {
          backendStatusTxt.textContent = "✓ Connected to Python AI Brain!";
          backendStatusTxt.style.color = "#00e6b4";
        }
        if (statusBadge) {
          statusBadge.textContent = "✓ AI Backend Online";
          statusBadge.style.color = "#00e6b4";
          statusBadge.style.borderColor = "rgba(0, 230, 180, 0.5)";
        }
      } else {
        if (backendStatusTxt) {
          if (res.status === 502) {
            backendStatusTxt.textContent = "⚠️ HTTP 502: Tunnel is up, but Python server on port 8000 was offline.";
          } else {
            backendStatusTxt.textContent = "⚠️ Server responded with HTTP " + res.status;
          }
          backendStatusTxt.style.color = "#f59e0b";
        }
      }
    } catch (e) {
      if (backendStatusTxt) {
        backendStatusTxt.textContent = "⚠️ Cannot reach server. Is Python running?";
        backendStatusTxt.style.color = "#ef4444";
      }
    }
  }
});
