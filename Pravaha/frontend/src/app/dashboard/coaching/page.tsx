"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import {
  LuBrain,
  LuTrendingUp,
  LuListChecks,
  LuUsers,
  LuRefreshCw,
  LuThumbsUp,
  LuThumbsDown,
  LuCheckCircle,
  LuPlus,
  LuTrash2,
  LuZap,
} from "react-icons/lu";

// ── Types ────────────────────────────────────────────────────────────────────

interface CoachingStats {
  total_tips: number;
  tips_by_type: Record<string, number>;
  unique_calls_coached: number;
  avg_tips_per_call: number;
  feedback_count: number;
  helpful_count: number;
  adoption_rate: number;
  top_objections: { subtype: string; count: number }[];
  period_days: number;
}

interface CoachingTip {
  tip_id: string;
  call_id: string;
  type: string;
  subtype?: string;
  detected?: string;
  suggested_response?: string;
  urgency?: string;
  utterance?: string;
  timestamp: string;
  feedback?: string | null;
}

interface LeaderboardEntry {
  rep_id: string;
  total_tips: number;
  helpful: number;
  calls_coached: number;
  adoption_rate: number;
}

interface PlaybookEntry {
  entry_id: string;
  category: string;
  trigger_phrase: string;
  label: string;
  suggested_response: string;
  urgency: string;
  priority: number;
  enabled: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const URGENCY_COLORS: Record<string, string> = {
  high: "#EF4444",
  medium: "#F59E0B",
  low: "#22C55E",
};

const TYPE_COLORS: Record<string, string> = {
  objection: "#EF4444",
  signal: "#22C55E",
  question: "#6366F1",
  opportunity: "#F59E0B",
};

function UrgencyBadge({ urgency }: { urgency?: string }) {
  const color = URGENCY_COLORS[urgency ?? ""] ?? "#9CA3AF";
  return (
    <span style={{ padding: "3px 10px", backgroundColor: color + "20", border: `2px solid ${color}`, borderRadius: "12px", fontSize: "0.65rem", fontWeight: 800, color, textTransform: "uppercase", letterSpacing: "0.1em" }}>
      {urgency ?? "—"}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const color = TYPE_COLORS[type] ?? "#9CA3AF";
  return (
    <span style={{ padding: "3px 10px", backgroundColor: color + "20", border: `2px solid ${color}`, borderRadius: "12px", fontSize: "0.65rem", fontWeight: 800, color, textTransform: "uppercase", letterSpacing: "0.1em" }}>
      {type}
    </span>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, color, icon: Icon }: { label: string; value: string | number; color: string; icon: React.ElementType }) {
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "20px", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
      <div>
        <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "8px" }}>{label}</div>
        <div style={{ fontSize: "2rem", fontWeight: 800, color: "#1A1A1A", lineHeight: 1 }}>{value}</div>
      </div>
      <div style={{ width: "44px", height: "44px", backgroundColor: color, border: "2px solid #1A1A1A", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "2px 2px 0px rgba(26,26,26,0.2)", flexShrink: 0 }}>
        <Icon size={22} color="#FFFFFF" />
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CoachingPage() {
  const [stats, setStats] = useState<CoachingStats | null>(null);
  const [history, setHistory] = useState<CoachingTip[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [playbook, setPlaybook] = useState<PlaybookEntry[]>([]);
  const [tab, setTab] = useState<"overview" | "history" | "leaderboard" | "playbook">("overview");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Playbook form state
  const [pbCategory, setPbCategory] = useState("objection");
  const [pbTrigger, setPbTrigger] = useState("");
  const [pbLabel, setPbLabel] = useState("");
  const [pbResponse, setPbResponse] = useState("");
  const [pbUrgency, setPbUrgency] = useState("medium");
  const [pbSaving, setPbSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [statsRes, historyRes, lbRes, pbRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/admin/coaching/stats`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/coaching/history?limit=30`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/coaching/leaderboard`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/coaching/playbook`, { headers: getAuthHeaders() }),
      ]);
      setStats(statsRes.data);
      setHistory(historyRes.data);
      setLeaderboard(lbRes.data);
      setPlaybook(pbRes.data);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        setLoadError("Not authenticated. Please sign in as admin to view coaching data.");
      } else {
        setLoadError("Failed to load coaching data. Check that the backend is running.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const submitFeedback = async (tipId: string, feedback: string) => {
    try {
      await axios.post(`${API_BASE_URL}/admin/coaching/tip/${tipId}/feedback`, { feedback }, { headers: getAuthHeaders() });
      setHistory((prev) => prev.map((t) => t.tip_id === tipId ? { ...t, feedback } : t));
      toast.success("Feedback saved");
    } catch {
      toast.error("Failed to save feedback");
    }
  };

  const savePlaybookEntry = async () => {
    if (!pbTrigger.trim() || !pbLabel.trim() || !pbResponse.trim()) {
      toast.error("Fill in all fields");
      return;
    }
    setPbSaving(true);
    try {
      await axios.post(`${API_BASE_URL}/admin/coaching/playbook`, {
        category: pbCategory,
        trigger_phrase: pbTrigger,
        label: pbLabel,
        suggested_response: pbResponse,
        urgency: pbUrgency,
      }, { headers: getAuthHeaders() });
      toast.success("Playbook entry saved");
      setPbTrigger(""); setPbLabel(""); setPbResponse("");
      void load();
    } catch {
      toast.error("Failed to save entry");
    } finally {
      setPbSaving(false);
    }
  };

  const deletePlaybookEntry = async (entryId: string) => {
    try {
      await axios.delete(`${API_BASE_URL}/admin/coaching/playbook/${entryId}`, { headers: getAuthHeaders() });
      setPlaybook((prev) => prev.filter((e) => e.entry_id !== entryId));
      toast.success("Entry deleted");
    } catch {
      toast.error("Failed to delete entry");
    }
  };

  const TABS = [
    { id: "overview", label: "Overview", icon: LuBrain },
    { id: "history", label: "Tip History", icon: LuListChecks },
    { id: "leaderboard", label: "Leaderboard", icon: LuUsers },
    { id: "playbook", label: "Playbook", icon: LuZap },
  ] as const;

  return (
    <main className="mx-auto flex min-h-full w-full max-w-6xl flex-col gap-6 px-4 py-6 text-slate-950">
      {/* Header */}
      <section className="rounded-[28px] border-2 border-black bg-[linear-gradient(135deg,#EEF2FF_0%,#F5F3FF_100%)] p-6 shadow-[10px_10px_0_#000]">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.25em] text-indigo-700 mb-2">AI Sales Coach</p>
            <h1 className="text-4xl font-black leading-tight">Coaching Dashboard</h1>
            <p className="text-sm font-medium text-slate-600 mt-1">Real-time tips, audit history, rep performance, and playbook management.</p>
          </div>
          <button
            onClick={load}
            className="flex items-center gap-2 rounded-2xl border-2 border-black bg-white px-4 py-2 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-0.5 hover:translate-y-0.5"
          >
            <LuRefreshCw size={14} /> Refresh
          </button>
        </div>
      </section>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              padding: "10px 18px",
              border: "2px solid #1A1A1A",
              borderRadius: "12px",
              fontWeight: 800,
              fontSize: "0.85rem",
              cursor: "pointer",
              backgroundColor: tab === id ? "#6366F1" : "#FFFFFF",
              color: tab === id ? "#FFFFFF" : "#1A1A1A",
              boxShadow: tab === id ? "3px 3px 0px #1A1A1A" : "2px 2px 0px #1A1A1A",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-sm font-black uppercase tracking-widest text-slate-400">Loading coaching data...</div>
        </div>
      )}

      {!loading && loadError && (
        <div className="rounded-2xl border-2 border-red-400 bg-red-50 p-6 shadow-[4px_4px_0_#EF4444]">
          <p className="text-sm font-black text-red-600">{loadError}</p>
          <p className="mt-2 text-xs text-red-500 font-medium">
            Sign in at <a href="/sign-in" className="underline font-black">/sign-in</a> with admin credentials, then return here.
          </p>
        </div>
      )}

      {!loading && !loadError && (
        <>
          {/* ── Overview Tab ── */}
          {tab === "overview" && !stats && (
            <div className="rounded-2xl border-2 border-dashed border-slate-300 bg-white p-10 text-center">
              <p className="text-sm font-black text-slate-400 uppercase tracking-widest">No coaching data yet</p>
              <p className="text-xs text-slate-400 mt-2 font-medium">Coaching tips appear here after your first AI-assisted call.</p>
            </div>
          )}
          {tab === "overview" && stats && (
            <div className="grid gap-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Total Tips" value={stats.total_tips} color="#6366F1" icon={LuBrain} />
                <StatCard label="Calls Coached" value={stats.unique_calls_coached} color="#FF6B9D" icon={LuZap} />
                <StatCard label="Adoption Rate" value={`${stats.adoption_rate}%`} color="#22C55E" icon={LuTrendingUp} />
                <StatCard label="Avg Tips / Call" value={stats.avg_tips_per_call} color="#F59E0B" icon={LuListChecks} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Tips by type */}
                <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
                  <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Tips by Type</p>
                  <div className="space-y-3">
                    {Object.entries(stats.tips_by_type).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between">
                        <TypeBadge type={type} />
                        <span className="text-lg font-black">{count}</span>
                      </div>
                    ))}
                    {Object.keys(stats.tips_by_type).length === 0 && (
                      <p className="text-sm text-slate-400 font-medium">No tips recorded yet.</p>
                    )}
                  </div>
                </div>

                {/* Top objections */}
                <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
                  <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Top Objections (Last {stats.period_days}d)</p>
                  <div className="space-y-3">
                    {stats.top_objections.map((o) => (
                      <div key={o.subtype} className="flex items-center justify-between rounded-xl border-2 border-black bg-[#FFF7ED] px-3 py-2 shadow-[2px_2px_0_#000]">
                        <span className="text-sm font-black">{o.subtype || "unknown"}</span>
                        <span className="text-sm font-black text-orange-600">{o.count}×</span>
                      </div>
                    ))}
                    {stats.top_objections.length === 0 && (
                      <p className="text-sm text-slate-400 font-medium">No objections detected yet.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── History Tab ── */}
          {tab === "history" && (
            <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Recent Coaching Tips</p>
              <div className="space-y-3">
                {history.map((tip) => (
                  <div key={tip.tip_id} className="rounded-2xl border-2 border-black bg-[#FAFAF5] p-4 shadow-[3px_3px_0_#000]">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <TypeBadge type={tip.type} />
                        <UrgencyBadge urgency={tip.urgency} />
                      </div>
                      <span className="text-xs text-slate-400 font-medium">{new Date(tip.timestamp).toLocaleString()}</span>
                    </div>
                    {tip.utterance && (
                      <p className="text-xs font-medium text-slate-500 mb-2 italic">&quot;{tip.utterance}&quot;</p>
                    )}
                    {tip.suggested_response && (
                      <p className="text-sm font-medium text-slate-800">{tip.suggested_response}</p>
                    )}
                    <div className="mt-3 flex items-center gap-2">
                      {tip.feedback ? (
                        <span className="text-xs font-black uppercase tracking-[0.15em] text-slate-400">Feedback: {tip.feedback}</span>
                      ) : (
                        <>
                          <button onClick={() => submitFeedback(tip.tip_id, "helpful")} className="flex items-center gap-1 rounded-xl border-2 border-black bg-emerald-100 px-3 py-1 text-xs font-black shadow-[2px_2px_0_#000] hover:translate-x-0.5 hover:translate-y-0.5 transition-transform">
                            <LuThumbsUp size={12} /> Helpful
                          </button>
                          <button onClick={() => submitFeedback(tip.tip_id, "used")} className="flex items-center gap-1 rounded-xl border-2 border-black bg-indigo-100 px-3 py-1 text-xs font-black shadow-[2px_2px_0_#000] hover:translate-x-0.5 hover:translate-y-0.5 transition-transform">
                            <LuCheckCircle size={12} /> Used It
                          </button>
                          <button onClick={() => submitFeedback(tip.tip_id, "not_relevant")} className="flex items-center gap-1 rounded-xl border-2 border-black bg-red-100 px-3 py-1 text-xs font-black shadow-[2px_2px_0_#000] hover:translate-x-0.5 hover:translate-y-0.5 transition-transform">
                            <LuThumbsDown size={12} /> Not Relevant
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
                {history.length === 0 && (
                  <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-6 text-center text-sm font-medium text-slate-400">
                    No coaching tips recorded yet. Tips appear here after live calls.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Leaderboard Tab ── */}
          {tab === "leaderboard" && (
            <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Rep Coaching Performance</p>
              {leaderboard.length > 0 ? (
                <div className="overflow-x-auto">
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #F0F0E8", backgroundColor: "#FAFAF5" }}>
                        {["Rep", "Tips Received", "Helpful", "Calls Coached", "Adoption %"].map((h) => (
                          <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: "0.65rem", fontWeight: 800, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.1em" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((entry, i) => (
                        <tr key={entry.rep_id} style={{ borderBottom: "1px solid #F0F0E8", backgroundColor: i === 0 ? "#FFFBEB" : "transparent" }}>
                          <td style={{ padding: "14px 16px", fontWeight: 700, fontSize: "0.9rem" }}>{entry.rep_id || "Unknown"}</td>
                          <td style={{ padding: "14px 16px", fontWeight: 600 }}>{entry.total_tips}</td>
                          <td style={{ padding: "14px 16px", fontWeight: 700, color: "#22C55E" }}>{entry.helpful}</td>
                          <td style={{ padding: "14px 16px", fontWeight: 600 }}>{entry.calls_coached}</td>
                          <td style={{ padding: "14px 16px", fontWeight: 800, color: entry.adoption_rate >= 50 ? "#22C55E" : "#F59E0B" }}>{Math.round(entry.adoption_rate)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-6 text-center text-sm font-medium text-slate-400">
                  No rep data yet. Leaderboard populates after tips receive feedback.
                </div>
              )}
            </div>
          )}

          {/* ── Playbook Tab ── */}
          {tab === "playbook" && (
            <div className="grid gap-6">
              {/* Add entry form */}
              <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
                <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Add Playbook Entry</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-black uppercase tracking-[0.15em] mb-1">Category</label>
                    <select value={pbCategory} onChange={(e) => setPbCategory(e.target.value)} className="w-full rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000] focus:outline-none">
                      <option value="objection">Objection</option>
                      <option value="signal">Signal</option>
                      <option value="question">Question</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-black uppercase tracking-[0.15em] mb-1">Urgency</label>
                    <select value={pbUrgency} onChange={(e) => setPbUrgency(e.target.value)} className="w-full rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000] focus:outline-none">
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-black uppercase tracking-[0.15em] mb-1">Trigger Phrase</label>
                    <input value={pbTrigger} onChange={(e) => setPbTrigger(e.target.value)} placeholder="e.g. too expensive" className="w-full rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000] focus:outline-none" />
                  </div>
                  <div>
                    <label className="block text-xs font-black uppercase tracking-[0.15em] mb-1">Label</label>
                    <input value={pbLabel} onChange={(e) => setPbLabel(e.target.value)} placeholder="e.g. Price Objection" className="w-full rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000] focus:outline-none" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-xs font-black uppercase tracking-[0.15em] mb-1">Suggested Response</label>
                    <textarea value={pbResponse} onChange={(e) => setPbResponse(e.target.value)} rows={3} placeholder="What the rep should say..." className="w-full rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000] focus:outline-none resize-none" />
                  </div>
                </div>
                <button onClick={savePlaybookEntry} disabled={pbSaving} className="mt-4 flex items-center gap-2 rounded-2xl border-2 border-black bg-lime-300 px-5 py-2 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-0.5 hover:translate-y-0.5 disabled:opacity-60">
                  <LuPlus size={14} /> {pbSaving ? "Saving..." : "Add Entry"}
                </button>
              </div>

              {/* Existing entries */}
              <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px" }}>
                <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-4">Playbook Entries ({playbook.length})</p>
                <div className="space-y-3">
                  {playbook.map((entry) => (
                    <div key={entry.entry_id} className="rounded-2xl border-2 border-black bg-[#FAFAF5] p-4 shadow-[3px_3px_0_#000]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <TypeBadge type={entry.category} />
                            <UrgencyBadge urgency={entry.urgency} />
                            <span className="text-xs font-black text-slate-500">&quot;{entry.trigger_phrase}&quot;</span>
                          </div>
                          <p className="text-sm font-black text-slate-900">{entry.label}</p>
                          <p className="text-sm font-medium text-slate-600 mt-1">{entry.suggested_response}</p>
                        </div>
                        <button onClick={() => deletePlaybookEntry(entry.entry_id)} className="flex-shrink-0 rounded-xl border-2 border-black bg-red-100 p-2 shadow-[2px_2px_0_#000] hover:translate-x-0.5 hover:translate-y-0.5 transition-transform">
                          <LuTrash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {playbook.length === 0 && (
                    <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-6 text-center text-sm font-medium text-slate-400">
                      No playbook entries yet. Add your first coaching rule above.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
