/**
 * ECHOHANDS 5.0 // Real-Time Peer-to-Peer Meeting Synchronization
 * Enables zero-latency data channels between meeting participants using
 * BroadcastChannel (for instant multi-tab/simulator testing) and WebRTC / WebSocket signaling.
 */

class PeerSyncManager {
  constructor(roomId = "echohands_default_room") {
    this.roomId = roomId;
    this.channel = null;
    this.socket = null;
    this.onPeerSignReceived = null;
    this.onPeerVoiceReceived = null;
    this.initBroadcastChannel();
  }

  initBroadcastChannel() {
    try {
      this.channel = new BroadcastChannel(`echohands_sync_${this.roomId}`);
      this.channel.onmessage = (event) => {
        this.handleIncomingMessage(event.data);
      };
      console.log(`[ECHOHANDS PeerSync] Broadcast channel active on: ${this.roomId}`);
    } catch (e) {
      console.warn("[ECHOHANDS PeerSync] BroadcastChannel not supported in this context:", e);
    }
  }

  setRoomId(newRoomId) {
    if (this.roomId === newRoomId) return;
    this.roomId = newRoomId;
    if (this.channel) {
      this.channel.close();
    }
    this.initBroadcastChannel();
  }

  // Send ISL Sign detected by Deaf/Mute user
  broadcastSign(signData) {
    const payload = {
      type: "PEER_SIGN_EVENT",
      senderRole: "signer",
      timestamp: Date.now(),
      data: signData // { tokens, english_sentence, hindi_sentence }
    };
    this.send(payload);
  }

  // Send Spoken voice transcribed from Hearing user
  broadcastVoice(voiceData) {
    const payload = {
      type: "PEER_VOICE_EVENT",
      senderRole: "speaker",
      timestamp: Date.now(),
      data: voiceData // { text, isl_tokens, language }
    };
    this.send(payload);
  }

  send(payload) {
    if (this.channel) {
      this.channel.postMessage(payload);
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  handleIncomingMessage(msg) {
    if (!msg || !msg.type) return;

    if (msg.type === "PEER_SIGN_EVENT" && this.onPeerSignReceived) {
      this.onPeerSignReceived(msg.data);
    }

    if (msg.type === "PEER_VOICE_EVENT" && this.onPeerVoiceReceived) {
      this.onPeerVoiceReceived(msg.data);
    }
  }
}

// Attach to window
window.PeerSyncManager = PeerSyncManager;
