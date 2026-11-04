/**
 * ECHOHANDS Manifest V3 Background Service Worker
 * Manages tab tracking, video meeting detection, and cross-context message routing.
 */

const MEETING_PATTERNS = [
  "meet.google.com",
  "zoom.us",
  "teams.microsoft.com",
  "teams.live.com",
  "meet.jit.si",
  "simulator",
  "meeting"
];

chrome.runtime.onInstalled.addListener((details) => {
  console.log("[ECHOHANDS] Extension installed successfully. Reason:", details.reason);
  chrome.storage.local.set({
    role: "signer", // 'signer' (deaf/mute) or 'speaker' (hearing)
    language: "en-IN", // 'en-IN' or 'hi-IN'
    autoVoice: true,
    avatarVisible: true,
    hudPosition: { x: 30, y: 30 },
    peerRoomId: "meeting_default"
  });
});

// Update badge when a video call tab is focused or updated
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (tab.url) {
    const isMeeting = MEETING_PATTERNS.some(p => tab.url.includes(p));
    if (isMeeting) {
      chrome.action.setBadgeText({ tabId, text: "LIVE" });
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#00e6b4" });
    } else {
      chrome.action.setBadgeText({ tabId, text: "" });
    }
  }
});

// Relay messages between popup and active tabs
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "GET_ACTIVE_MEETING_STATUS") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0 && tabs[0].url) {
        const isMeeting = MEETING_PATTERNS.some(p => tabs[0].url.includes(p));
        sendResponse({ isMeeting, url: tabs[0].url });
      } else {
        sendResponse({ isMeeting: false, url: "" });
      }
    });
    return true; // async
  }

  if (request.type === "TRIGGER_HUD_TOGGLE") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "TOGGLE_HUD" });
      }
    });
    sendResponse({ status: "dispatched" });
    return true;
  }
});
