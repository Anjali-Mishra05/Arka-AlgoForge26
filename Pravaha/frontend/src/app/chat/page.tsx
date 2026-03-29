"use client";

import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import Markdown from "react-markdown";
import toast from "react-hot-toast";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { FaVolumeHigh, FaVolumeOff } from "react-icons/fa6";
import {
  LuArrowRight,
  LuBarChart4,
  LuBrain,
  LuChevronRight,
  LuLightbulb,
  LuMic,
  LuSend,
  LuSparkles,
  LuUsers,
  LuZap,
} from "react-icons/lu";

import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import NextBestActionPanel from "@/components/intelligence/next-best-action";

type Role = "user" | "team" | "admin";

type ChatMessage = {
  isUser: boolean;
  text: string;
};

type AdminSnapshot = {
  totalInteractions: number;
  activeLeads: number;
  totalViews: number;
  staleDeals: number;
  topQuestions: string[];
};

const ROLE_CONFIG: Record<
  Role,
  { label: string; placeholder: string; color: string; badgeColor: string; icon: React.ReactNode }
> = {
  user: {
    label: "Product Assistant",
    placeholder: "Ask me anything about Pravaha.",
    color: "#2563EB",
    badgeColor: "#DBEAFE",
    icon: <LuBrain size={14} />,
  },
  team: {
    label: "Sales Coach",
    placeholder: "Describe the objection you are facing.",
    color: "#16A34A",
    badgeColor: "#DCFCE7",
    icon: <LuUsers size={14} />,
  },
  admin: {
    label: "Sales Intelligence",
    placeholder: "Ask about deal health, team performance, or risk.",
    color: "#A855F7",
    badgeColor: "#F3E8FF",
    icon: <LuBarChart4 size={14} />,
  },
};

const OBJECTION_TEMPLATES: [string, string][] = [
  ["Too expensive", "The prospect says the price is too high. How should I respond?"],
  ["Using competitor", "The prospect says they already use a competitor. What should I say?"],
  ["Not right now", "The prospect says now is not a good time. How do I handle this?"],
  ["Need to think", "The prospect says they need to think about it. How do I keep momentum?"],
  ["Need approval", "The prospect needs approval from leadership. What are the next steps?"],
  ["No ROI proof", "The prospect wants proof of ROI before committing. How do I respond?"],
];

const ADMIN_QUERIES: string[] = [
  "Summarize the current pipeline health",
  "What are the most common objections from recent calls?",
  "Which deals are at risk this month?",
  "What is the team conversion rate trend?",
  "Recommend top actions for this week",
];

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [role, setRole] = useState<Role>("user");
  const [showPanel, setShowPanel] = useState(false);
  const [adminSnapshot, setAdminSnapshot] = useState<AdminSnapshot | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    let active = true;

    const loadProfile = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/me`, { headers: getAuthHeaders() });
        const nextRole = (response.data?.role || "user") as Role;
        if (!active) return;

        setRole(nextRole);
        setShowPanel(nextRole !== "user");

        if (nextRole === "admin") {
          const analyticsResponse = await axios.get(`${API_BASE_URL}/admin/analytics`, {
            headers: getAuthHeaders(),
          });

          if (!active) return;

          const analytics = analyticsResponse.data || {};
          const details = Array.isArray(analytics.analytics?.details) ? analytics.analytics.details : [];
          const findCount = (title: string) =>
            Number(details.find((item: { title?: string; count?: number }) => item.title === title)?.count || 0);

          setAdminSnapshot({
            totalInteractions: findCount("Total Interactions"),
            activeLeads: findCount("Active Leads"),
            totalViews: Number(analytics.analytics?.details?.find((item: { title?: string }) => item.title === "Proposal Views")?.count || 0),
            staleDeals: Number(analytics.dealStatus?.stale || 0),
            topQuestions: Array.isArray(analytics.topQueries)
              ? analytics.topQueries
                  .map((entry: { query?: string }) => entry.query || "")
                  .filter(Boolean)
                  .slice(0, 4)
              : [],
          });
        } else {
          setAdminSnapshot(null);
        }
      } catch (error: any) {
        if (error?.response?.status === 401) {
          toast.error("Session expired. Sign in again.");
          router.push("/sign-in");
          return;
        }
        toast.error("Unable to load chat session.");
      } finally {
        if (active) {
          setProfileLoading(false);
        }
      }
    };

    void loadProfile();

    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const config = ROLE_CONFIG[role] || ROLE_CONFIG.user;

  const speak = (text: string) => {
    try {
      const synth = window.speechSynthesis;
      synth.cancel();
      setTimeout(() => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.onerror = (event) => {
          if (event.error !== "interrupted") console.error("Speech error:", event.error);
        };
        synth.speak(utterance);
      }, 100);
    } catch {
      // Ignore speech failures.
    }
  };

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) {
      toast.error("Message cannot be empty");
      return;
    }

    // Cancel any playing audio when sending new message
    window.speechSynthesis.cancel();

    setMessages((current) => [...current, { isUser: true, text: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/chat/response?query=${encodeURIComponent(trimmed)}`,
        {},
        { headers: getAuthHeaders() }
      );
      const reply = response.data.response || response.data;
      setMessages((current) => [...current, { isUser: false, text: reply }]);
      if (ttsEnabled) {
        speak(reply);
      }
    } catch (error: any) {
      setMessages((current) => current.slice(0, -1));
      if (error?.response?.status === 401) {
        toast.error("Session expired. Sign in again.");
        router.push("/sign-in");
      } else {
        toast.error("Failed to get response. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const bookDemo = () => {
    window.location.href = "mailto:sales@pravaha.ai?subject=Book%20a%20demo";
  };

  const insertTemplate = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  if (profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#FAFAF5] px-4 text-slate-950">
        <div className="rounded-[28px] border-2 border-black bg-white px-6 py-5 shadow-[8px_8px_0_#000]">
          <div className="text-sm font-black uppercase tracking-[0.3em] text-slate-500">Loading chat session</div>
          <div className="mt-2 text-lg font-black">Resolving your role and context...</div>
        </div>
      </div>
    );
  }



  return (
    <div className="flex min-h-screen flex-col bg-[linear-gradient(#E5E5DD_1px,transparent_1px),linear-gradient(90deg,#E5E5DD_1px,transparent_1px)] bg-[size:24px_24px] bg-[#FAFAF5] text-slate-950">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-black bg-white px-4 py-3 shadow-[0_4px_0_#000] md:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-black md:text-2xl">AI Chat</h1>
          <span
            className="inline-flex items-center gap-2 rounded-full border-2 border-black px-3 py-1 text-xs font-black uppercase tracking-[0.2em]"
            style={{ backgroundColor: config.badgeColor, color: config.color }}
          >
            {config.icon}
            {config.label}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {(role === "team" || role === "admin") && (
            <button
              type="button"
              onClick={() => setShowPanel((current) => !current)}
              className="rounded-2xl border-2 border-black px-3 py-2 text-xs font-black shadow-[3px_3px_0_#000]"
              style={{ backgroundColor: showPanel ? config.color : "#FFFDF7", color: showPanel ? "#fff" : config.color }}
            >
              {showPanel ? "Hide panel" : "Show panel"}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setTtsEnabled((current) => {
                const newState = !current;
                if (!newState) {
                  window.speechSynthesis.cancel();
                }
                return newState;
              });
            }}
            className="flex items-center justify-center rounded-2xl border-2 border-black bg-white px-3 py-2 shadow-[3px_3px_0_#000]"
            aria-label="Toggle text to speech"
          >
            {ttsEnabled ? <FaVolumeHigh size={16} /> : <FaVolumeOff size={16} />}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
            {messages.length === 0 && (
              <section className="mx-auto flex max-w-3xl flex-col items-center gap-4 rounded-[28px] border-2 border-black bg-white px-6 py-10 text-center shadow-[8px_8px_0_#000]">
                <div className="flex h-16 w-16 items-center justify-center rounded-[18px] border-2 border-black bg-[#2563EB] shadow-[4px_4px_0_#000]">
                  {role === "admin" ? <LuBarChart4 size={30} color="white" /> : role === "team" ? <LuUsers size={30} color="white" /> : <LuBrain size={30} color="white" />}
                </div>
                <div>
                  <div className="text-2xl font-black md:text-3xl">Pravaha AI</div>
                  <div className="mt-2 max-w-2xl text-sm font-medium text-slate-600">{config.placeholder}</div>
                </div>

                {role === "user" && (
                  <div className="flex flex-wrap justify-center gap-3">
                    <button
                      type="button"
                      onClick={bookDemo}
                      className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-[#DCFCE7] px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                    >
                      <LuMic size={16} />
                      Book a demo
                    </button>
                    <button
                      type="button"
                      onClick={() => router.push("/pricing")}
                      className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-white px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                    >
                      <LuArrowRight size={16} />
                      View pricing
                    </button>
                  </div>
                )}
              </section>
            )}

            <div className="mx-auto flex max-w-4xl flex-col gap-4">
              {messages.map((message, index) => (
                <div
                  key={`msg-${index}`}
                  style={{ display: "flex", flexDirection: "column", alignItems: message.isUser ? "flex-end" : "flex-start", maxWidth: "80%", alignSelf: message.isUser ? "flex-end" : "flex-start" }}
                >
                  <div
                    style={message.isUser ? {
                      backgroundColor: config.color,
                      color: "#FFFFFF",
                      border: "2px solid #1A1A1A",
                      borderRadius: "14px 14px 4px 14px",
                      boxShadow: "3px 3px 0px #1A1A1A",
                      padding: "10px 16px",
                      fontSize: "0.9rem",
                      lineHeight: "1.5",
                    } : {
                      backgroundColor: "#FFFFFF",
                      color: "#1A1A1A",
                      border: "2px solid #1A1A1A",
                      borderRadius: "14px 14px 14px 4px",
                      boxShadow: "3px 3px 0px #1A1A1A",
                      padding: "10px 16px",
                      fontSize: "0.9rem",
                      lineHeight: "1.5",
                    }}
                  >
                    {message.isUser ? message.text : <Markdown>{message.text}</Markdown>}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex max-w-[75%] items-center gap-2 rounded-[22px] border-2 border-black bg-white px-4 py-3 shadow-[4px_4px_0_#000]">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-700" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-700 [animation-delay:120ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-700 [animation-delay:240ms]" />
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t-2 border-black bg-white px-4 py-4 shadow-[0_-4px_0_#000] md:px-6">
            <div className="mx-auto flex max-w-4xl gap-3">
              <input
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void sendMessage(input);
                  }
                }}
                placeholder={config.placeholder}
                className="min-w-0 flex-1 rounded-2xl border-2 border-black bg-[#FAFAF5] px-4 py-3 text-sm font-medium outline-none shadow-[3px_3px_0_#000] placeholder:text-slate-500 focus:border-black"
              />
              <button
                type="button"
                onClick={() => void sendMessage(input)}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-2xl border-2 border-black px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000] disabled:cursor-not-allowed disabled:opacity-60"
                style={{ backgroundColor: loading ? "#9CA3AF" : config.color, color: "#fff" }}
              >
                <LuSend size={16} />
                Send
              </button>
            </div>
            <div className="mx-auto mt-2 max-w-4xl text-center text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Press Enter to send. Shift+Enter for a new line.
            </div>
          </div>
        </main>

        <AnimatePresence>
          {showPanel && (role === "team" || role === "admin") && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-y-0 right-0 z-40 w-[min(88vw,320px)] border-l-2 border-black bg-white shadow-[-4px_0_0_#000] md:relative md:inset-auto md:z-auto md:block"
            >
              <div className="h-full overflow-y-auto p-4">
                {role === "team" && (
                  <section className="space-y-4">
                    <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#DCFCE7] px-3 py-1 text-xs font-black uppercase tracking-[0.2em]">
                      <LuLightbulb size={14} />
                      Coaching tips
                    </div>
                    <div className="rounded-[22px] border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                      <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Document aware</div>
                      <p className="mt-2 text-sm font-medium text-slate-700">
                        These prompts use the current proposal and uploaded docs as context, so the responses stay specific to the deal.
                      </p>
                    </div>
                    <div className="space-y-2">
                      {OBJECTION_TEMPLATES.map(([label, prompt]) => (
                        <button
                          key={label}
                          type="button"
                          onClick={() => insertTemplate(prompt)}
                          className="flex w-full items-center justify-between rounded-2xl border-2 border-black bg-white px-3 py-3 text-left text-sm font-black shadow-[3px_3px_0_#000]"
                        >
                          <span>{label}</span>
                          <LuChevronRight size={14} />
                        </button>
                      ))}
                    </div>
                    <NextBestActionPanel scope="chat" />
                  </section>
                )}

                {role === "admin" && (
                  <section className="space-y-4">
                    <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#F3E8FF] px-3 py-1 text-xs font-black uppercase tracking-[0.2em]">
                      <LuZap size={14} />
                      Quick insights
                    </div>

                    {adminSnapshot ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-[20px] border-2 border-black bg-[#FFF7ED] p-3 shadow-[3px_3px_0_#000]">
                          <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Interactions</div>
                          <div className="mt-1 text-xl font-black">{adminSnapshot.totalInteractions}</div>
                        </div>
                        <div className="rounded-[20px] border-2 border-black bg-[#DCFCE7] p-3 shadow-[3px_3px_0_#000]">
                          <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Active leads</div>
                          <div className="mt-1 text-xl font-black">{adminSnapshot.activeLeads}</div>
                        </div>
                        <div className="rounded-[20px] border-2 border-black bg-[#DBEAFE] p-3 shadow-[3px_3px_0_#000]">
                          <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Views</div>
                          <div className="mt-1 text-xl font-black">{adminSnapshot.totalViews}</div>
                        </div>
                        <div className="rounded-[20px] border-2 border-black bg-[#FEE2E2] p-3 shadow-[3px_3px_0_#000]">
                          <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Stale deals</div>
                          <div className="mt-1 text-xl font-black">{adminSnapshot.staleDeals}</div>
                        </div>
                      </div>
                    ) : null}

                    <div className="space-y-2">
                      {ADMIN_QUERIES.map((query) => (
                        <button
                          key={query}
                          type="button"
                          onClick={() => void sendMessage(query)}
                          className="flex w-full items-center justify-between rounded-2xl border-2 border-black bg-[#FFFDF7] px-3 py-3 text-left text-sm font-black shadow-[3px_3px_0_#000]"
                        >
                          <span>{query}</span>
                          <LuChevronRight size={14} />
                        </button>
                      ))}
                    </div>

                    <NextBestActionPanel scope="admin" />

                    <div className="rounded-[22px] border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                      <div className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-[0.2em] text-slate-500">
                        <LuSparkles size={14} />
                        Top buyer questions
                      </div>
                      <div className="mt-3 space-y-2">
                        {adminSnapshot?.topQuestions?.length ? (
                          adminSnapshot.topQuestions.map((question) => (
                            <div key={question} className="rounded-2xl border-2 border-black bg-white px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000]">
                              {question}
                            </div>
                          ))
                        ) : (
                          <div className="rounded-2xl border-2 border-dashed border-black bg-white px-3 py-2 text-sm font-medium text-slate-500">
                            No question summary available yet.
                          </div>
                        )}
                      </div>
                    </div>
                  </section>
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default ChatPage; 
