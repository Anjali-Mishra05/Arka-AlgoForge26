"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import DOMPurify from "dompurify";
import { useParams } from "next/navigation";
import toast from "react-hot-toast";
import { LuEye, LuMessageSquare, LuSend, LuShield, LuSparkles, LuX } from "react-icons/lu";
import PravahaLogo from "@/components/PravahaLogo";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

type ProposalPayload = {
  html_content?: string;
  created_at?: string;
  proposal_id?: string;
  title?: string;
  brand?: {
    company_name?: string;
    company_description?: string;
    website?: string;
    watermark_text?: string;
  };
};

const sanitizeHtml = (html: string) => DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });

const leadKey = (proposalId: string) => `proposal-lead:${proposalId}`;
const sessionKey = (proposalId: string) => `proposal-session:${proposalId}`;
const messagesKey = (proposalId: string, sessionId: string) => `proposal-messages:${proposalId}:${sessionId}`;

const readMessages = (proposalId: string, sessionId: string): ChatMessage[] => {
  try {
    const stored = localStorage.getItem(messagesKey(proposalId, sessionId));
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (message): message is ChatMessage =>
        (message?.role === "user" || message?.role === "assistant") && typeof message?.text === "string"
    );
  } catch {
    localStorage.removeItem(messagesKey(proposalId, sessionId));
    return [];
  }
};

const writeMessages = (proposalId: string, sessionId: string, nextMessages: ChatMessage[]) => {
  localStorage.setItem(messagesKey(proposalId, sessionId), JSON.stringify(nextMessages));
};

export default function ProposalPage() {
  const params = useParams<{ id: string }>();
  const proposalId = Array.isArray(params?.id) ? params.id[0] : params?.id || "";
  const [html, setHtml] = useState("");
  const [title, setTitle] = useState("Interactive proposal");
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [brand, setBrand] = useState<ProposalPayload["brand"]>({
    company_name: "Pravaha",
    watermark_text: "Pravaha",
  });
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [leadModalOpen, setLeadModalOpen] = useState(false);
  const [buyerName, setBuyerName] = useState("");
  const [buyerEmail, setBuyerEmail] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const setLocalTranscript = useCallback(
    (activeSessionId: string, nextMessages: ChatMessage[]) => {
      setMessages(nextMessages);
      if (proposalId && activeSessionId) {
        writeMessages(proposalId, activeSessionId, nextMessages);
      }
    },
    [proposalId]
  );

  const loadProposal = useCallback(async () => {
    if (!proposalId) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/proposal/${proposalId}`);
      const payload: ProposalPayload = typeof response.data === "string" ? { html_content: response.data } : response.data;
      setHtml(sanitizeHtml(payload.html_content || ""));
      setTitle(payload.title || "Interactive proposal");
      setCreatedAt(payload.created_at || null);
      setBrand(payload.brand || { company_name: "Pravaha", watermark_text: "Pravaha" });
    } catch {
      toast.error("Proposal could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [proposalId]);

  const recordView = useCallback(
    async (viewerSession: string) => {
      if (!proposalId) return;
      try {
        await axios.post(`${API_BASE_URL}/proposal/${proposalId}/view`, {
          viewer_session: viewerSession,
          referrer: document.referrer || null,
        });
      } catch {
        // Views are best-effort for the demo.
      }
    },
    [proposalId]
  );

  useEffect(() => {
    if (!proposalId) {
      setLoading(false);
      return;
    }

    const savedLead = localStorage.getItem(leadKey(proposalId));
    const savedSession = localStorage.getItem(sessionKey(proposalId));
    const activeSession = savedSession || crypto.randomUUID();

    if (!savedSession) {
      localStorage.setItem(sessionKey(proposalId), activeSession);
    }

    setSessionId(activeSession);
    setMessages(readMessages(proposalId, activeSession));

    if (savedLead) {
      try {
        const parsed = JSON.parse(savedLead);
        setBuyerName(parsed.name || "");
        setBuyerEmail(parsed.email || "");
      } catch {
        localStorage.removeItem(leadKey(proposalId));
        setLeadModalOpen(true);
      }
    } else {
      setLeadModalOpen(true);
    }

    void loadProposal();
    void recordView(activeSession);
  }, [loadProposal, proposalId, recordView]);

  // ─── Section Dwell Tracking ──────────────────────────────────────────
  useEffect(() => {
    if (loading || !html || !proposalId || !sessionId) return;

    const container = contentRef.current;
    if (!container) return;

    // Discover sections from h2/h3 headings inside the rendered proposal HTML
    const headings = container.querySelectorAll("h2, h3");
    if (headings.length === 0) {
      // No headings → track the whole page as one section
      headings.length === 0; // no-op; we'll track "full-page" below
    }

    const slugify = (text: string) =>
      text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "untitled";

    // Map each heading to a section ID
    const sectionIds: string[] = [];
    const elements: Element[] = [];

    if (headings.length === 0) {
      // Treat the entire container as one section
      sectionIds.push("full-page");
      elements.push(container);
    } else {
      headings.forEach((el) => {
        const id = el.id || slugify(el.textContent || "");
        sectionIds.push(id);
        elements.push(el);
      });
    }

    // Track which sections are currently visible
    const visibleSections = new Set<string>();
    // Accumulate seconds per section since last beacon
    const dwellAccum: Record<string, number> = {};
    let pageTotalAccum = 0;
    sectionIds.forEach((id) => (dwellAccum[id] = 0));

    // IntersectionObserver watches headings within the scrollable container
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const idx = elements.indexOf(entry.target);
          if (idx === -1) return;
          const sId = sectionIds[idx];
          if (entry.isIntersecting) {
            visibleSections.add(sId);
          } else {
            visibleSections.delete(sId);
          }
        });
      },
      { root: container, threshold: 0 }
    );

    elements.forEach((el) => observer.observe(el));

    // Every second, increment visible sections
    const tickInterval = setInterval(() => {
      if (document.hidden) return; // don't count if tab is backgrounded
      pageTotalAccum += 1;
      visibleSections.forEach((sId) => {
        dwellAccum[sId] = (dwellAccum[sId] || 0) + 1;
      });
    }, 1000);

    // Beacon sender: every 30s, send accumulated data
    const sendBeacon = () => {
      const hasData = pageTotalAccum > 0 || Object.values(dwellAccum).some((v) => v > 0);
      if (!hasData) return;

      const payload = JSON.stringify({
        viewer_session: sessionId,
        sections: { ...dwellAccum },
        page_total_seconds: pageTotalAccum,
      });

      // Reset accumulators BEFORE sending (so we don't lose data if send is slow)
      sectionIds.forEach((id) => (dwellAccum[id] = 0));
      pageTotalAccum = 0;

      // Use sendBeacon for reliability (fires even on page close)
      const blob = new Blob([payload], { type: "application/json" });
      const sent = navigator.sendBeacon?.(`${API_BASE_URL}/proposal/${proposalId}/section_dwell`, blob);
      if (!sent) {
        // Fallback to fetch fire-and-forget
        fetch(`${API_BASE_URL}/proposal/${proposalId}/section_dwell`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: true,
        }).catch(() => {});
      }
    };

    const beaconInterval = setInterval(sendBeacon, 30000);

    // Final beacon on page unload
    const handleUnload = () => sendBeacon();
    window.addEventListener("beforeunload", handleUnload);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") sendBeacon();
    });

    return () => {
      observer.disconnect();
      clearInterval(tickInterval);
      clearInterval(beaconInterval);
      window.removeEventListener("beforeunload", handleUnload);
      sendBeacon(); // flush remaining data on cleanup
    };
  }, [loading, html, proposalId, sessionId]);

  const saveLead = () => {
    const trimmedName = buyerName.trim();
    const trimmedEmail = buyerEmail.trim();
    if (!trimmedName || !trimmedEmail) {
      toast.error("Name and email are required.");
      return;
    }

    localStorage.setItem(leadKey(proposalId), JSON.stringify({ name: trimmedName, email: trimmedEmail }));
    setBuyerName(trimmedName);
    setBuyerEmail(trimmedEmail);
    setLeadModalOpen(false);
    setChatOpen(true);
    toast.success("Lead captured.");
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) {
      toast.error("Type a question first.");
      return;
    }
    if (!buyerName || !buyerEmail) {
      setLeadModalOpen(true);
      return;
    }

    const activeSession = sessionId || crypto.randomUUID();
    if (!sessionId) {
      localStorage.setItem(sessionKey(proposalId), activeSession);
      setSessionId(activeSession);
    }

    const previousMessages = messages;
    const optimisticMessages: ChatMessage[] = [...previousMessages, { role: "user", text: trimmed }];
    setLocalTranscript(activeSession, optimisticMessages);
    setInput("");
    setSending(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/proposal/${proposalId}/chat`, {
        buyer_name: buyerName,
        buyer_email: buyerEmail,
        message: trimmed,
        session_id: activeSession,
      });

      const confirmedSession = response.data?.session_id || activeSession;
      if (confirmedSession !== activeSession) {
        localStorage.setItem(sessionKey(proposalId), confirmedSession);
        setSessionId(confirmedSession);
      }

      const finalMessages = [
        ...optimisticMessages,
        { role: "assistant" as const, text: response.data?.response || "No response returned." },
      ];
      setLocalTranscript(confirmedSession, finalMessages);
    } catch {
      toast.error("Buyer chat failed.");
      setLocalTranscript(activeSession, previousMessages);
    } finally {
      setSending(false);
    }
  };

  const toggleChat = () => {
    if (!buyerName || !buyerEmail) {
      setLeadModalOpen(true);
      return;
    }
    setChatOpen((open) => !open);
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#fff6c7,_#fafafa_38%,_#e8f3ff_100%)] text-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6">
        <header className="relative overflow-hidden rounded-3xl border-2 border-black bg-white p-5 shadow-[10px_10px_0px_#000]">
          <div className="absolute -right-6 top-4 rotate-6 rounded-full border-2 border-black bg-amber-300 px-4 py-2 text-[11px] font-black uppercase tracking-[0.3em] text-slate-950">
            Pravaha
          </div>
          <div className="absolute bottom-3 right-6 text-5xl font-black uppercase tracking-[0.35em] text-slate-100 md:text-7xl">
            {brand?.watermark_text || "Pravaha"}
          </div>
          <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <PravahaLogo size="sm" className="mb-4" />
              <p className="text-xs font-black uppercase tracking-[0.35em] text-slate-500">Buyer Proposal Room</p>
              <h1 className="mt-2 max-w-4xl text-3xl font-black md:text-5xl">{title}</h1>
              <p className="mt-2 max-w-3xl text-sm font-medium text-slate-600">
                Public proposal access, browser-local buyer chat history, and view tracking stay attached to this shared deal room.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs font-black">
                <span className="rounded-full border-2 border-black bg-white px-3 py-2">{brand?.company_name || "Pravaha"}</span>
                {brand?.website ? (
                  <a
                    href={brand.website}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full border-2 border-black bg-white px-3 py-2 underline"
                  >
                    {brand.website}
                  </a>
                ) : null}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-black">
              <span className="rounded-full border-2 border-black bg-emerald-200 px-3 py-2">Views tracked</span>
              <span className="rounded-full border-2 border-black bg-cyan-200 px-3 py-2">Buyer chat active</span>
              <span className="rounded-full border-2 border-black bg-amber-200 px-3 py-2">Pravaha branded</span>
            </div>
          </div>
        </header>

        <main className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
          <section className="relative overflow-hidden rounded-3xl border-2 border-black bg-white p-4 shadow-[10px_10px_0px_#000] md:p-6">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-12 bg-[linear-gradient(90deg,_#fde68a,_#bfdbfe,_#bbf7d0)] opacity-80" />
            {loading ? (
              <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-8 text-sm font-medium text-slate-500">
                Loading proposal...
              </div>
            ) : (
              <div className="relative overflow-hidden rounded-2xl border-2 border-black">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black bg-slate-950 px-4 py-3 text-xs font-black uppercase tracking-[0.25em] text-white">
                  <span>{title}</span>
                  <span>{createdAt ? new Date(createdAt).toLocaleString() : proposalId}</span>
                </div>
                <div ref={contentRef} className="relative max-h-[calc(100vh-240px)] overflow-auto bg-white p-4 prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: html }} />
              </div>
            )}
          </section>

          <aside className="space-y-4">
            <div className="rounded-3xl border-2 border-black bg-white p-5 shadow-[10px_10px_0px_#000]">
              <p className="text-xs font-black uppercase tracking-[0.35em] text-slate-500">Lead Capture</p>
              <h2 className="mt-2 text-2xl font-black">Buyer profile</h2>
              <div className="mt-4 space-y-3 text-sm font-medium text-slate-700">
                <div className="rounded-2xl border-2 border-black bg-slate-50 p-4">
                  <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-500">Name</div>
                  <div className="mt-1 font-black">{buyerName || "Not captured"}</div>
                </div>
                <div className="rounded-2xl border-2 border-black bg-slate-50 p-4">
                  <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-500">Email</div>
              <div className="mt-1 font-black">{buyerEmail || "Not captured"}</div>
                </div>
                <div className="rounded-2xl border-2 border-black bg-amber-100 p-4">
                  <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-500">Transcript</div>
                  <div className="mt-1 text-sm font-black text-slate-950">
                    {messages.length ? `${messages.length} messages restored for this browser session` : "No local transcript yet"}
                  </div>
                </div>
                {brand?.company_description ? (
                  <div className="rounded-2xl border-2 border-black bg-cyan-100 p-4">
                    <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-500">Shared by</div>
                    <div className="mt-1 text-sm font-medium text-slate-800">{brand.company_description}</div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="relative overflow-hidden rounded-3xl border-2 border-black bg-white p-5 shadow-[10px_10px_0px_#000]">
              <div className="absolute -right-4 top-4 rotate-12 rounded-full border-2 border-black bg-cyan-200 px-3 py-1 text-[10px] font-black uppercase tracking-[0.3em]">
                Shared
              </div>
              <div className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.25em] text-slate-500">
                <LuShield size={14} />
                Pravaha safeguards
              </div>
              <ul className="mt-4 space-y-3 text-sm font-medium text-slate-700">
                <li className="flex items-start gap-2"><LuSparkles size={16} className="mt-0.5 shrink-0" /> Proposal HTML is sanitized before rendering.</li>
                <li className="flex items-start gap-2"><LuEye size={16} className="mt-0.5 shrink-0" /> Views are recorded with session-aware metadata.</li>
                <li className="flex items-start gap-2"><LuMessageSquare size={16} className="mt-0.5 shrink-0" /> Buyer identity and the local transcript are restored only on this browser session.</li>
              </ul>
            </div>
          </aside>
        </main>
      </div>

      <button
        onClick={toggleChat}
        className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full border-2 border-black bg-black px-4 py-3 text-sm font-black text-white shadow-[8px_8px_0px_#000]"
      >
        <LuMessageSquare size={16} />
        {chatOpen ? "Close chat" : "Ask about this proposal"}
      </button>

      {chatOpen && (
        <div className="fixed bottom-20 right-5 z-40 w-[min(92vw,380px)] rounded-3xl border-2 border-black bg-white shadow-[10px_10px_0px_#000]">
          <div className="flex items-center justify-between border-b-2 border-black bg-amber-200 px-4 py-3">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.3em] text-slate-600">Buyer Chat</div>
              <div className="text-sm font-black text-slate-950">Ask Pravaha about this proposal</div>
            </div>
            <button onClick={() => setChatOpen(false)} className="rounded-full border-2 border-black bg-white p-2">
              <LuX size={14} />
            </button>
          </div>
          <div className="max-h-[320px] space-y-3 overflow-auto p-4">
            {messages.length ? (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`max-w-[90%] rounded-2xl border-2 border-black px-3 py-2 text-sm font-medium shadow-[4px_4px_0px_#000] ${
                    message.role === "user" ? "ml-auto bg-cyan-200" : "bg-emerald-200"
                  }`}
                >
                  {message.text}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-4 text-sm font-medium text-slate-500">
                Start with pricing, timeline, implementation, or integration questions.
              </div>
            )}
          </div>
          <div className="border-t-2 border-black p-4">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about the proposal..."
              className="min-h-24 w-full rounded-2xl border-2 border-black bg-slate-50 p-3 text-sm font-medium outline-none"
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500">
                Session {sessionId ? "ready" : "pending"}
              </span>
              <button
                onClick={sendMessage}
                disabled={sending}
                className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-black px-4 py-2 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <LuSend size={14} />
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {leadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-md rounded-3xl border-2 border-black bg-white p-6 shadow-[10px_10px_0px_#000]">
            <p className="text-xs font-black uppercase tracking-[0.35em] text-slate-500">Lead capture</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Unlock the buyer chat</h2>
            <p className="mt-2 text-sm font-medium text-slate-600">
              Save a name and email so the shared proposal room can restore your local transcript on this browser.
            </p>
            <div className="mt-5 space-y-3">
              <input
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                placeholder="Buyer name"
                className="w-full rounded-2xl border-2 border-black bg-slate-50 px-4 py-3 text-sm font-medium outline-none"
              />
              <input
                value={buyerEmail}
                onChange={(e) => setBuyerEmail(e.target.value)}
                placeholder="Buyer email"
                type="email"
                className="w-full rounded-2xl border-2 border-black bg-slate-50 px-4 py-3 text-sm font-medium outline-none"
              />
            </div>
            <div className="mt-5 flex items-center justify-between gap-3">
              <button onClick={() => setLeadModalOpen(false)} className="rounded-2xl border-2 border-black bg-slate-100 px-4 py-2 text-sm font-black">
                Maybe later
              </button>
              <button onClick={saveLead} className="rounded-2xl border-2 border-black bg-amber-300 px-4 py-2 text-sm font-black">
                Start reading
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
