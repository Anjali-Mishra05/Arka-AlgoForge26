"use client";
import { useState, useRef } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { LuSend, LuBrain, LuLightbulb, LuChevronRight, LuFileText } from "react-icons/lu";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import Markdown from "react-markdown";

interface Msg { isUser: boolean; text: string; sources?: string[]; }

const OBJECTION_TEMPLATES = [
  ["💸 Too Expensive", "The prospect says the price is too high. How should I respond?"],
  ["🏢 Using Competitor", "They already use a competitor. What should I say?"],
  ["⏰ Not Right Time", "Now is not a good time, they say. How do I handle this?"],
  ["🤔 Need to Think", "They need to think about it. How do I keep the deal moving?"],
  ["👔 Need Approval", "Needs leadership approval. What are the next steps?"],
  ["📊 No ROI Proof", "They want proof of ROI. How do I respond?"],
  ["🔒 Security Concerns", "They have data security concerns. How should I address them?"],
  ["📅 Bad Timing", "Budget cycle doesn't align. How do I plant seeds for future?"],
];

const PRO_TIPS = [
  "Always acknowledge the objection first",
  'Use "feel, felt, found" framework',
  "Ask discovery questions before pitching",
  "Reference case studies when possible",
  "Mirror the prospect's language",
  "Set a clear next step at every call",
];

function SalesTeamChatbot() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((p) => [...p, { isUser: true, text: trimmed }]);
    setInput("");
    setLoading(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/chat/coach?query=${encodeURIComponent(trimmed)}`,
        {},
        { headers: getAuthHeaders(), withCredentials: true }
      );
      const reply = response.data.response || response.data;
      const sources: string[] = response.data.sources || [];
      setMessages((p) => [...p, { isUser: false, text: reply, sources }]);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 401 || status === 403) {
        toast.error("Not signed in — please log in at /sign-in first");
      } else if (!err?.response) {
        toast.error("Network error — is the backend running on port 8000?");
      } else if (detail) {
        toast.error(`Coach error: ${detail}`);
      } else {
        toast.error("Failed to get coach response");
      }
      setMessages((p) => p.slice(0, -1));
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  };

  return (
    <div style={{ display: "flex", height: "calc(100vh - 72px)", backgroundColor: "#FAFAF5", backgroundImage: "linear-gradient(#E5E5DD 1px, transparent 1px), linear-gradient(90deg, #E5E5DD 1px, transparent 1px)", backgroundSize: "24px 24px", overflow: "hidden" }}>

      {/* Left sidebar */}
      <div style={{ width: "260px", minWidth: "260px", borderRight: "2px solid #1A1A1A", backgroundColor: "#FFFFFF", display: "flex", flexDirection: "column", overflowY: "auto" }}>
        <div style={{ padding: "20px 16px", borderBottom: "2px solid #1A1A1A" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <div style={{ width: "32px", height: "32px", backgroundColor: "#22C55E", border: "2px solid #1A1A1A", borderRadius: "10px", boxShadow: "3px 3px 0px #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <LuBrain size={16} color="white" />
            </div>
            <span style={{ fontWeight: 800, fontSize: "1rem", color: "#1A1A1A" }}>Sales Coach</span>
          </div>
          <p style={{ fontSize: "0.72rem", color: "#6B7280", fontWeight: 500 }}>AI-powered objection handling</p>
        </div>

        <div style={{ padding: "16px" }}>
          <div style={{ fontWeight: 800, fontSize: "0.75rem", color: "#22C55E", letterSpacing: "0.08em", marginBottom: "10px", display: "flex", alignItems: "center", gap: "5px" }}>
            <LuLightbulb size={12} /> OBJECTION TEMPLATES
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {OBJECTION_TEMPLATES.map(([label, prompt]) => (
              <button
                key={label}
                onClick={() => setInput(prompt)}
                style={{ textAlign: "left", padding: "9px 12px", backgroundColor: "#F0FFF4", border: "2px solid #1A1A1A", borderRadius: "10px", boxShadow: "3px 3px 0px #1A1A1A", fontSize: "0.78rem", fontWeight: 600, color: "#1A1A1A", cursor: "pointer", transition: "all 0.1s", display: "flex", alignItems: "center", gap: "6px" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = "translate(2px,2px)"; (e.currentTarget as HTMLElement).style.boxShadow = "1px 1px 0px #1A1A1A"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = "translate(0,0)"; (e.currentTarget as HTMLElement).style.boxShadow = "3px 3px 0px #1A1A1A"; }}
              >
                <LuChevronRight size={12} style={{ color: "#22C55E", flexShrink: 0 }} /> {label}
              </button>
            ))}
          </div>

          <div style={{ fontWeight: 800, fontSize: "0.75rem", color: "#22C55E", letterSpacing: "0.08em", marginTop: "20px", marginBottom: "10px" }}>📌 PRO TIPS</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {PRO_TIPS.map((tip) => (
              <div key={tip} style={{ fontSize: "0.75rem", color: "#374151", padding: "8px 10px", backgroundColor: "#FAFAF5", border: "1.5px solid #E5E5DD", borderRadius: "8px", display: "flex", alignItems: "flex-start", gap: "6px" }}>
                <span style={{ color: "#22C55E", flexShrink: 0 }}>✓</span> {tip}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: "2px solid #1A1A1A", backgroundColor: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
          <h1 style={{ fontWeight: 800, fontSize: "1.25rem", color: "#1A1A1A", margin: 0 }}>Sales Coaching Chat</h1>
          <span style={{ padding: "3px 10px", backgroundColor: "#F0FFF4", border: "2px solid #1A1A1A", borderRadius: "9999px", fontSize: "0.65rem", fontWeight: 800, color: "#22C55E" }}>TEAM</span>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
          {messages.length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: "12px", opacity: 0.55 }}>
              <div style={{ width: "56px", height: "56px", backgroundColor: "#22C55E", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <LuBrain size={28} color="white" />
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 800, fontSize: "1.1rem", color: "#1A1A1A" }}>Sales Coach Ready</div>
                <div style={{ fontSize: "0.82rem", color: "#6B7280", marginTop: "4px" }}>Ask about any sales objection or use the templates on the left</div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              style={{ display: "flex", alignItems: "flex-start", gap: "10px", flexDirection: msg.isUser ? "row-reverse" : "row" }}
            >
              <div style={{ width: "32px", height: "32px", backgroundColor: msg.isUser ? "#6366F1" : "#22C55E", border: "2px solid #1A1A1A", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "2px 2px 0px #1A1A1A" }}>
                {msg.isUser ? "U" : <LuBrain size={14} color="white" />}
              </div>
              <div style={{ maxWidth: "70%" }}>
                <div style={msg.isUser ? {
                  backgroundColor: "#6366F1", color: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "14px 14px 4px 14px", boxShadow: "3px 3px 0px #1A1A1A", padding: "10px 14px", fontSize: "0.875rem",
                } : {
                  backgroundColor: "#FFFFFF", color: "#1A1A1A", border: "2px solid #1A1A1A", borderRadius: "14px 14px 14px 4px", boxShadow: "3px 3px 0px #1A1A1A", padding: "10px 14px", fontSize: "0.875rem",
                }}>
                  {msg.isUser ? msg.text : <Markdown>{String(msg.text)}</Markdown>}
                </div>
                {!msg.isUser && msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ fontSize: "0.68rem", fontWeight: 800, color: "#6366F1", letterSpacing: "0.06em", display: "flex", alignItems: "center", gap: "4px" }}>
                      <LuFileText size={11} /> RELEVANT DOCS
                    </div>
                    {msg.sources.map((src, j) => (
                      <div key={j} style={{ padding: "8px 10px", backgroundColor: "#EEF2FF", border: "1.5px solid #C7D2FE", borderRadius: "8px", fontSize: "0.75rem", color: "#374151", lineHeight: 1.4 }}>
                        {src.length > 200 ? src.slice(0, 200) + "..." : src}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
              <div style={{ width: "32px", height: "32px", backgroundColor: "#22C55E", border: "2px solid #1A1A1A", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "2px 2px 0px #1A1A1A" }}>
                <LuBrain size={14} color="white" />
              </div>
              <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "14px 14px 14px 4px", boxShadow: "3px 3px 0px #1A1A1A", padding: "12px 16px" }}>
                <div style={{ display: "flex", gap: "5px" }}>
                  {[0, 1, 2].map((i) => (
                    <div key={i} style={{ width: "7px", height: "7px", backgroundColor: "#22C55E", borderRadius: "50%", animation: `bounce 1s ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: "14px 20px", borderTop: "2px solid #1A1A1A", backgroundColor: "#FFFFFF", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: "10px", maxWidth: "800px", margin: "0 auto" }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder="Describe the situation or objection you're facing…"
              style={{ flex: 1, padding: "11px 16px", backgroundColor: "#FAFAF5", border: "2px solid #1A1A1A", borderRadius: "10px", fontSize: "0.875rem", color: "#1A1A1A", outline: "none" }}
              onFocus={(e) => { e.target.style.borderColor = "#22C55E"; e.target.style.boxShadow = "4px 4px 0px #22C55E"; }}
              onBlur={(e) => { e.target.style.borderColor = "#1A1A1A"; e.target.style.boxShadow = "none"; }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={loading}
              style={{ padding: "11px 18px", backgroundColor: loading ? "#9CA3AF" : "#22C55E", color: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "10px", cursor: loading ? "not-allowed" : "pointer", boxShadow: loading ? "none" : "4px 4px 0px #1A1A1A", fontWeight: 700, display: "flex", alignItems: "center", gap: "6px", transition: "all 0.1s" }}
              onMouseEnter={(e) => { if (!loading) { (e.currentTarget as HTMLElement).style.transform = "translate(2px,2px)"; (e.currentTarget as HTMLElement).style.boxShadow = "2px 2px 0px #1A1A1A"; } }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = "translate(0,0)"; (e.currentTarget as HTMLElement).style.boxShadow = loading ? "none" : "4px 4px 0px #1A1A1A"; }}
            >
              <LuSend size={15} /> Send
            </button>
          </div>
        </div>
      </div>

      <style>{`@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-5px)} }`}</style>
    </div>
  );
}

export default SalesTeamChatbot;
