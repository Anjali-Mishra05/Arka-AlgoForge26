"use client";
import Visitor from "@/components/analytics/visitor";
import Analytics from "@/components/analytics/analytics";
import CompletedGoals from "@/components/analytics/completed-goals";
import AveragePositions from "@/components/analytics/average-positions";
import CompletedRates from "@/components/analytics/completed-rates";
import SessionBrowser from "@/components/analytics/session-browser";
import SalesCountry from "@/components/analytics/sales-country";
import RecentLeads from "@/components/analytics/recent-leads";
import ToDoList from "@/components/analytics/to-do-list";
import ProposalEngagement from "@/components/analytics/proposal-engagement";
import NextBestActionPanel from "@/components/intelligence/next-best-action";
import DailyBriefPanel from "@/components/intelligence/daily-brief";
import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import { LuFileText, LuZap, LuRefreshCw, LuTrendingUp, LuTarget, LuUsers } from "react-icons/lu";

const KPICard = ({
  label,
  value,
  color,
  icon: Icon,
  trend,
}: {
  label: string;
  value: string | number;
  color: string;
  icon: React.ElementType;
  trend?: string;
}) => (
  <div
    style={{
      backgroundColor: "#FFFFFF",
      border: "2px solid #1A1A1A",
      borderRadius: "16px",
      boxShadow: "4px 4px 0px #1A1A1A",
      padding: "24px",
      position: "relative",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: "-8px",
        right: "-8px",
        width: "80px",
        height: "80px",
        backgroundColor: color,
        opacity: 0.08,
        borderRadius: "50%",
      }}
    />
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", position: "relative", zIndex: 1 }}>
      <div>
        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
          {label}
        </div>
        <div style={{ fontSize: "2.5rem", fontWeight: 800, color: "#1A1A1A", lineHeight: 1, marginBottom: "8px" }}>{value}</div>
        {trend ? (
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: trend.startsWith("+") ? "#22C55E" : "#EF4444", display: "flex", alignItems: "center", gap: "4px" }}>
            <LuTrendingUp size={12} /> {trend}
          </div>
        ) : null}
      </div>
      <div style={{ width: "48px", height: "48px", backgroundColor: color, border: "2px solid #1A1A1A", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "2px 2px 0px rgba(26, 26, 26, 0.2)" }}>
        <Icon size={24} color="#FFFFFF" />
      </div>
    </div>
  </div>
);

const SectionHeader = ({ title, subtitle }: { title: string; subtitle?: string }) => (
  <div style={{ marginBottom: "20px" }}>
    <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "#1A1A1A", margin: 0, lineHeight: 1.2 }}>{title}</h2>
    {subtitle && <p style={{ color: "#9CA3AF", fontSize: "0.875rem", marginTop: "4px", margin: 0 }}>{subtitle}</p>}
  </div>
);

const Page = () => {
  const [analytics, setAnalytics] = useState<any>(undefined);
  const [callInsights, setCallInsights] = useState<any>(undefined);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/analytics`, { headers: getAuthHeaders() });
      setAnalytics(response.data);
      toast.success("Analytics loaded");
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Cannot fetch analytics data");
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  const loadCallInsights = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/call_insights`, {
        headers: getAuthHeaders(),
        params: { limit: 10 },
      });
      setCallInsights(response.data);
    } catch {
      setCallInsights(undefined);
    }
  }, []);

  useEffect(() => {
    void loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    void loadCallInsights();
  }, [loadCallInsights]);

  const generateProposal = () => {
    toast.promise(axios.get(`${API_BASE_URL}/admin/generate_proposal`, { headers: getAuthHeaders() }), {
      loading: "Generating proposal with AI... this may take a moment.",
      success: "Proposal generated successfully!",
      error: "Failed to generate proposal. Please try again.",
    });
  };

  const activeLeadCount =
    analytics?.analytics?.details?.find((detail: { title?: string; count?: number }) => detail.title === "Active Leads")
      ?.count ?? 0;
  const highRiskCalls = Number(callInsights?.risk_breakdown?.high || callInsights?.risk_breakdown?.critical || 0);
  const proposalViews = Number(analytics?.visitors?.total || 0);
  const recentCallCount = Array.isArray(callInsights?.recent_calls) ? callInsights.recent_calls.length : 0;
  const liveTasks = [
    {
      id: "high-risk-calls",
      title: highRiskCalls ? `Review ${highRiskCalls} high-risk call${highRiskCalls === 1 ? "" : "s"}` : "High-risk call queue is clear",
      detail: highRiskCalls
        ? "Open the call intelligence surface and tighten the next steps for the riskiest conversations."
        : "No call summaries are currently flagged as high risk.",
      href: "/dashboard/voice",
      status: highRiskCalls ? "action" : "clear",
    },
    {
      id: "proposal-engagement",
      title: proposalViews ? `Follow up on ${proposalViews} tracked proposal view${proposalViews === 1 ? "" : "s"}` : "Proposal engagement is quiet",
      detail: proposalViews
        ? "Review proposal engagement and buyer questions to decide which buyers need the next touch."
        : "No recent proposal-view activity is available from the dashboard feed.",
      href: "/dashboard/proposals",
      status: proposalViews ? "monitor" : "clear",
    },
    {
      id: "active-leads",
      title: activeLeadCount ? `Work ${activeLeadCount} active lead${activeLeadCount === 1 ? "" : "s"}` : "Lead queue is empty",
      detail: activeLeadCount
        ? "Open proposal or chat workflows and convert the active lead queue into concrete next steps."
        : "No active leads are currently flagged in analytics.",
      href: "/dashboard/proposals",
      status: activeLeadCount ? "action" : "clear",
    },
    {
      id: "recent-calls",
      title: recentCallCount ? `Turn ${recentCallCount} recent call${recentCallCount === 1 ? "" : "s"} into follow-up` : "No recent call backlog",
      detail: recentCallCount
        ? "Use the call summaries and next-best-action guidance to send the right follow-up while the signal is fresh."
        : "There are no stored recent calls waiting for a follow-up review.",
      href: "/dashboard/voice",
      status: recentCallCount ? "monitor" : "clear",
    },
  ] as const;

  return (
    <div style={{ minHeight: "100vh", paddingBottom: "40px" }}>
      <div style={{ marginBottom: "40px", display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "24px" }}>
        <div>
          <h1 style={{ fontWeight: 900, fontSize: "2.25rem", color: "#1A1A1A", margin: 0, lineHeight: 1.1, letterSpacing: "-0.02em" }}>
            Sales Dashboard
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: "1rem", marginTop: "8px", margin: 0 }}>Real-time AI-powered insights for your sales operations</p>
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <button
            onClick={loadAnalytics}
            style={{
              padding: "12px 20px",
              backgroundColor: "#FFFFFF",
              color: "#1A1A1A",
              border: "2px solid #1A1A1A",
              borderRadius: "12px",
              fontWeight: 700,
              fontSize: "0.9rem",
              cursor: "pointer",
              boxShadow: "3px 3px 0px #1A1A1A",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              transition: "all 0.15s ease-out",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "translate(2px,2px)";
              (e.currentTarget as HTMLElement).style.boxShadow = "1px 1px 0px #1A1A1A";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "translate(0,0)";
              (e.currentTarget as HTMLElement).style.boxShadow = "3px 3px 0px #1A1A1A";
            }}
          >
            <LuRefreshCw size={16} /> Refresh
          </button>
          <button
            onClick={generateProposal}
            style={{
              padding: "12px 24px",
              backgroundColor: "#6366F1",
              color: "#FFFFFF",
              border: "2px solid #1A1A1A",
              borderRadius: "12px",
              fontWeight: 800,
              fontSize: "0.95rem",
              cursor: "pointer",
              boxShadow: "4px 4px 0px #1A1A1A",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              transition: "all 0.15s ease-out",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "translate(2px,2px)";
              (e.currentTarget as HTMLElement).style.boxShadow = "2px 2px 0px #1A1A1A";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "translate(0,0)";
              (e.currentTarget as HTMLElement).style.boxShadow = "4px 4px 0px #1A1A1A";
            }}
          >
            <LuFileText size={18} /> Generate Proposal
          </button>
        </div>
      </div>

      {loading && !analytics && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "400px", gap: "20px" }}>
          <div style={{ width: "64px", height: "64px", backgroundColor: "#6366F1", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite" }}>
            <LuZap size={32} color="white" />
          </div>
          <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "#1A1A1A" }}>Loading analytics...</div>
          <div style={{ fontSize: "0.875rem", color: "#9CA3AF" }}>Fetching your real-time data</div>
        </div>
      )}

      {analytics && (
        <div style={{ display: "grid", gap: "32px" }}>
          <div>
            <SectionHeader title="Key Performance Indicators" subtitle="Your sales metrics at a glance" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <KPICard label="Total Proposals" value={analytics?.averagePos?.avgCount ?? 0} color="#6366F1" icon={LuFileText} />
              <KPICard label="Proposal Views" value={analytics?.visitors?.total ?? 0} color="#FF6B9D" icon={LuTarget} />
              <KPICard label="Conversion Rate" value={analytics?.sales?.rate ?? 0} color="#22C55E" icon={LuTrendingUp} />
              <KPICard label="Active Leads" value={activeLeadCount} color="#FF6633" icon={LuUsers} />
            </div>
          </div>

          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 lg:col-span-6">
              <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px", height: "100%" }}>
                <SectionHeader title="Next Best Action" subtitle="AI-powered recommendations" />
                <NextBestActionPanel />
              </div>
            </div>
            <div className="col-span-12 lg:col-span-6">
              <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px", height: "100%" }}>
                <SectionHeader title="Daily Brief" subtitle="Today's highlights" />
                <DailyBriefPanel />
              </div>
            </div>
          </div>

          <div>
            <SectionHeader title="Call Intelligence" subtitle="Recent call summaries and recurring call signals" />
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-4">
                <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px", height: "100%" }}>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                    <div className="rounded-2xl border-2 border-black bg-[#FFF7ED] p-4 shadow-[3px_3px_0_#000]">
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Recent calls</p>
                      <p className="mt-2 text-2xl font-black">{callInsights?.total_calls ?? 0}</p>
                    </div>
                    <div className="rounded-2xl border-2 border-black bg-[#DCFCE7] p-4 shadow-[3px_3px_0_#000]">
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Avg duration</p>
                      <p className="mt-2 text-2xl font-black">{callInsights?.average_duration_seconds ? `${callInsights.average_duration_seconds}s` : "0s"}</p>
                    </div>
                    <div className="rounded-2xl border-2 border-black bg-[#FEE2E2] p-4 shadow-[3px_3px_0_#000]">
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">High risk</p>
                      <p className="mt-2 text-2xl font-black">{callInsights?.risk_breakdown?.high || callInsights?.risk_breakdown?.critical || 0}</p>
                    </div>
                    <div className="rounded-2xl border-2 border-black bg-[#E0F2FE] p-4 shadow-[3px_3px_0_#000]">
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Signals</p>
                      <p className="mt-2 text-2xl font-black">{callInsights?.top_buying_signals?.length || 0}</p>
                    </div>
                  </div>

                  <div className="mt-5 space-y-3">
                    <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Top objections</div>
                    {callInsights?.top_objections?.length ? (
                      callInsights.top_objections.slice(0, 4).map((item: { label?: string; count?: number }) => (
                        <div key={item.label} className="rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-medium shadow-[3px_3px_0_#000]">
                          <div className="font-black text-slate-950">{item.label || "Unknown"}</div>
                          <div className="text-xs text-slate-500">{item.count || 0} mentions</div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl border-2 border-dashed border-black bg-white px-3 py-3 text-sm font-medium text-slate-500">
                        No call objections recorded yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="col-span-12 lg:col-span-8">
                <div style={{ backgroundColor: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "16px", boxShadow: "4px 4px 0px #1A1A1A", padding: "24px", height: "100%" }}>
                  <div className="flex items-center justify-between gap-4">
                    <SectionHeader title="Recent Calls" subtitle="Summaries pulled from stored call records" />
                    <div className="rounded-full border-2 border-black bg-[#DBEAFE] px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-sky-900">
                      {callInsights?.recent_calls?.length || 0} stored
                    </div>
                  </div>
                  <div className="space-y-3">
                    {callInsights?.recent_calls?.length ? (
                      callInsights.recent_calls.slice(0, 4).map((call: any) => (
                        <div key={call.call_id || call.phone_number} className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <div className="text-sm font-black">{call.phone_number || call.call_id || "Unknown call"}</div>
                              <div className="mt-1 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
                                {call.created_at ? new Date(call.created_at).toLocaleString() : "No timestamp"}
                              </div>
                            </div>
                            <span className="rounded-full border-2 border-black bg-white px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em]">
                              {call.risk_level || call.objection_summary?.risk_level || "unknown"}
                            </span>
                          </div>
                          <p className="mt-3 text-sm font-medium leading-6 text-slate-700">{call.summary || "No summary available."}</p>
                          {!!call.key_points?.length && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {call.key_points.slice(0, 3).map((point: string) => (
                                <span key={point} className="rounded-full border-2 border-black bg-white px-3 py-1 text-xs font-black">
                                  {point}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-5 text-sm font-medium text-slate-500">
                        No recent call summaries have been stored yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <SectionHeader title="Performance Analytics" subtitle="Detailed trends and insights" />
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8">
                <Analytics analytics={analytics.analytics} className="" />
              </div>
              <div className="col-span-12 lg:col-span-4">
                <AveragePositions analytics={analytics.averagePos} className="" />
              </div>
            </div>
          </div>

          <div>
            <SectionHeader title="Traffic & Engagement" subtitle="How your audience interacts with proposals" />
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8">
                <Visitor analytics={analytics.visitors} className="" />
              </div>
              <div className="col-span-12 lg:col-span-4">
                <SessionBrowser analytics={analytics.sessionBrowser} className="" />
              </div>
            </div>
          </div>

          <div>
            <SectionHeader title="Sales Performance" subtitle="Geographic and completion metrics" />
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8">
                <SalesCountry analytics={analytics.sales} className="" />
              </div>
              <div className="col-span-12 lg:col-span-4" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <CompletedGoals analytics={analytics.sales} className="" />
                <CompletedRates analytics={analytics.sales} className="" />
              </div>
            </div>
          </div>

          <div>
            <SectionHeader title="Recent Leads & Actions" subtitle="Latest prospect activity and tasks" />
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8">
                <RecentLeads analytics={analytics.users} className="" />
              </div>
              <div className="col-span-12 lg:col-span-4" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <ProposalEngagement analytics={analytics.proposalEngagement} />
                <ToDoList tasks={[...liveTasks]} />
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default Page;
