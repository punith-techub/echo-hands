/**
 * ECHOHANDS Extension Popup Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  const meetingBadge = document.getElementById("meeting-badge");
  const roleSigner = document.getElementById("role-signer");
  const roleSpeaker = document.getElementById("role-speaker");
  const langSelect = document.getElementById("lang-select");
  const autoVoiceToggle = document.getElementById("auto-voice-toggle");
  const avatarToggle = document.getElementById("avatar-toggle");
  const btnToggleHUD = document.getElementById("btn-toggle-hud");
  const btnOpenSimulator = document.getElementById("btn-open-simulator");

  // Load saved state
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["role", "language", "autoVoice", "avatarVisible"], (res) => {
      if (res.role === "speaker") {
        roleSpeaker.classList.add("active");
        roleSigner.classList.remove("active");
      } else {
        roleSigner.classList.add("active");
        roleSpeaker.classList.remove("active");
      }

      if (res.language) langSelect.value = res.language;
      if (res.autoVoice !== undefined) autoVoiceToggle.checked = res.autoVoice;
      if (res.avatarVisible !== undefined) avatarToggle.checked = res.avatarVisible;
    });
  }

  // Check active meeting status
  if (chrome.runtime && chrome.runtime.sendMessage) {
    chrome.runtime.sendMessage({ type: "GET_ACTIVE_MEETING_STATUS" }, (res) => {
      if (res && res.isMeeting) {
        meetingBadge.textContent = "MEETING ACTIVE";
        meetingBadge.classList.remove("inactive");
      } else {
        meetingBadge.textContent = "STANDBY";
        meetingBadge.classList.add("inactive");
      }
    });
  }

  // Role selections
  roleSigner.addEventListener("click", () => {
    roleSigner.classList.add("active");
    roleSpeaker.classList.remove("active");
    saveConfig({ role: "signer" });
  });

  roleSpeaker.addEventListener("click", () => {
    roleSpeaker.classList.add("active");
    roleSigner.classList.remove("active");
    saveConfig({ role: "speaker" });
  });

  langSelect.addEventListener("change", () => {
    saveConfig({ language: langSelect.value });
  });

  autoVoiceToggle.addEventListener("change", () => {
    saveConfig({ autoVoice: autoVoiceToggle.checked });
  });

  avatarToggle.addEventListener("change", () => {
    saveConfig({ avatarVisible: avatarToggle.checked });
  });

  // Toggle HUD on active tab
  btnToggleHUD.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "TRIGGER_HUD_TOGGLE" });
    window.close();
  });

  // Open Simulator
  btnOpenSimulator.addEventListener("click", () => {
    const simUrl = chrome.runtime.getURL ? chrome.runtime.getURL("simulator.html") : "http://localhost:8000/simulator";
    // Check if we are hosted locally or on Vercel
    chrome.tabs.create({ url: "http://localhost:8000/simulator" });
  });

  function saveConfig(obj) {
    if (chrome.storage && chrome.storage.local) {
      chrome.storage.local.set(obj);
    }
  }
});
