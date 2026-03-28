"use client";

import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import {
  LuCopy,
  LuExternalLink,
  LuEye,
  LuMessageSquare,
  LuRefreshCw,
  LuSparkles,
  LuPenLine,
  LuCheckCircle2,
  LuXCircle,
  LuRotateCcw,
} from "react-icons/lu";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";

type ProposalRecord = {
  proposal_id: string;
  title?: string;
  created_at?: string;
  status?: string;
  views?: number;
  followup_sent?: boolean;
  followup_sent_at?: string;
  last_followup?: {
    sent_at?: string;
    recipients?: string[];
    subject?: string;
    top_topic?: string;
  };
  latest_buyer_activity?: string;
  buyer_sessions?: Array<{
    buyer_name?: string;
    buyer_email?: string;
    last_active?: string;
    started_at?: string;
    messages?: Array<{ role?: string; content?: string }>;
  }>;
  revision_suggestions?: RevisionSuggestion[];
};

type Engagement = {
  proposal_id: string;
  views: number;
  unique_buyers: number;
  latest_buyer_activity?: string;
  last_view_at?: string;
  followup_outcome?: {
    status?: string;
    sent_at?: string;
    first_reengaged_at?: string;
    last_reengaged_at?: string;
    event_count?: number;
    latest_event_type?: string;
  } | null;
  revision_outcomes?: Array<{
    suggestion_id?: string;
    section_name?: string;
    applied_at?: string;
    status?: string;
    event_count?: number;
    first_event_at?: string;
    last_event_at?: string;
    latest_event_type?: string;
  }>;
  question_summary?: Array<{
    question: string;
    count: number;
    session_count?: number;
    buyer_names?: string[];
    buyer_emails?: string[];
    last_asked_at?: string;
  }>;
  engagement_timeline?: Array<{
    event_type?: string;
    occurred_at?: string;
    label?: string;
    content?: string;
    buyer_name?: string;
    buyer_email?: string;
    viewer_session?: string;
    referrer?: string;
  }>;
  buyer_sessions: Array<{
    session_id?: string;
    buyer_name?: string;
    buyer_email?: string;
    questions_asked?: number;
    message_count?: number;
    first_question?: string;
    last_question?: string;
    last_assistant_response?: string;
    last_active?: string;
    messages?: Array<{ role?: string; content?: string; timestamp?: string }>;
  }>;
};

type SectionDwell = {
  section_id: string;
  total_seconds: number;
  unique_viewers: number;
};

type RevisionSuggestion = {
  suggestion_id: string;
  section_name?: string;
  status?: string;
  reason?: string;
  source_questions?: string[];
  suggested_copy?: string;
  created_at?: string;
  applied_at?: string;
  dismissed_at?: string;
};

type FollowupConfig = {
  user_id?: string;
  enabled?: boolean;
  delay_hours?: number;
  updated_at?: string;
};

type StaleProposal = ProposalRecord;

const formatDateTime = (value?: string) => (value ? new Date(value).toLocaleString() : "Not available");

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ProposalRecord[]>([]);
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [suggestions, setSuggestions] = useState<RevisionSuggestion[]>([]);
  const [followupConfig, setFollowupConfig] = useState<FollowupConfig | null>(null);
  const [staleProposals, setStaleProposals] = useState<StaleProposal[]>([]);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [followupLoading, setFollowupLoading] = useState(false);
  const [savingFollowupConfig, setSavingFollowupConfig] = useState(false);
  const [triggeringFollowups, setTriggeringFollowups] = useState(false);
  const [followupEnabledDraft, setFollowupEnabledDraft] = useState(false);
  const [followupDelayDraft, setFollowupDelayDraft] = useState("48");
  const [mutatingSuggestionId, setMutatingSuggestionId] = useState<string | null>(null);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);
  const [regeneratingSection, setRegeneratingSection] = useState("");
  const [sectionDwell, setSectionDwell] = useState<SectionDwell[]>([]);
  const router = useRouter();
  const refreshRef = useRef<(() => Promise<void>) | null>(null);

  const headers = () => ({
    ...getAuthHeaders(),
    Accept: "application/json",
  });

  const refreshFollowupState = async () => {
    setFollowupLoading(true);
    try {
      const configResponse = await axios.get(`${API_BASE_URL}/admin/proposals/followup-config`, { headers: headers() });
      const nextConfig: FollowupConfig = configResponse.data || {};
      const nextDelayHours = Number(nextConfig.delay_hours ?? 48);

      setFollowupConfig(nextConfig);
      setFollowupEnabledDraft(Boolean(nextConfig.enabled));
      setFollowupDelayDraft(String(nextDelayHours));

      const staleResponse = await axios.get(`${API_BASE_URL}/admin/proposals/stale`, {
        headers: headers(),
        params: { hours: nextDelayHours },
      });
      setStaleProposals(Array.isArray(staleResponse.data?.stale_proposals) ? staleResponse.data.stale_proposals : []);
    } catch {
      setFollowupConfig(null);
      setStaleProposals([]);
    } finally {
      setFollowupLoading(false);
    }
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/proposals`, { headers: headers() });
      const nextProposals = Array.isArray(response.data) ? response.data : [];
      setProposals(nextProposals);

      const nextSelected = selectedProposalId || nextProposals[0]?.proposal_id || null;
      if (nextSelected) {
        setSelectedProposalId(nextSelected);
        await loadEngagement(nextSelected);
        await loadSuggestions(nextSelected);
      }
      await refreshFollowupState();
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Unable to load proposals.");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadSectionDwell = async (proposalId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/proposals/${proposalId}/section-dwell`, { headers: headers() });
      setSectionDwell(Array.isArray(response.data?.sections) ? response.data.sections : []);
    } catch {
      setSectionDwell([]);
    }
  };

  const loadEngagement = async (proposalId: string) => {
    setSelectedProposalId(proposalId);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/proposals/${proposalId}/engagement`, { headers: headers() });
      setEngagement(response.data);
    } catch {
      setEngagement(null);
      toast.error("Could not load engagement details.");
    }
    await loadSectionDwell(proposalId);
  };

  const loadSuggestions = async (proposalId: string) => {
    setSuggestionsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/proposals/${proposalId}/revision-suggestions`, {
        headers: headers(),
      });
      setSuggestions(Array.isArray(response.data?.revision_suggestions) ? response.data.revision_suggestions : []);
    } catch {
      setSuggestions([]);
    } finally {
      setSuggestionsLoading(false);
    }
  };

  const generateSuggestions = async (proposalId: string, force = false) => {
    setGeneratingSuggestions(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/admin/proposals/${proposalId}/revision-suggestions/generate`,
        { force },
        { headers: headers() }
      );
      const nextSuggestions = Array.isArray(response.data?.revision_suggestions) ? response.data.revision_suggestions : [];
      setSuggestions(nextSuggestions);
      toast.success(response.data?.message || `Generated ${nextSuggestions.length} suggestion(s).`);
      await refreshProposalMetadata(proposalId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to generate suggestions.");
    } finally {
      setGeneratingSuggestions(false);
    }
  };

  const refreshProposalMetadata = async (proposalId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/proposals`, { headers: headers() });
      const nextProposals = Array.isArray(response.data) ? response.data : [];
      setProposals(nextProposals);
      const nextSelected = nextProposals.find((proposal: ProposalRecord) => proposal.proposal_id === proposalId);
      if (nextSelected) {
        setSelectedProposalId(nextSelected.proposal_id);
      }
    } catch {
      // Keep existing local state if metadata refresh fails.
    }
  };
  refreshRef.current = refresh;

  const saveFollowupConfig = async () => {
    const delayHours = Number(followupDelayDraft);
    if (!Number.isFinite(delayHours) || delayHours < 12 || delayHours > 168) {
      toast.error("Follow-up delay must be between 12 and 168 hours.");
      return;
    }

    setSavingFollowupConfig(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/admin/proposals/followup-config`,
        { enabled: followupEnabledDraft, delay_hours: delayHours },
        { headers: headers() }
      );
      const nextConfig: FollowupConfig = response.data || {};
      setFollowupConfig(nextConfig);
      setFollowupEnabledDraft(Boolean(nextConfig.enabled));
      setFollowupDelayDraft(String(nextConfig.delay_hours ?? delayHours));
      toast.success(`Follow-up automation ${nextConfig.enabled ? "enabled" : "disabled"}.`);
      await refreshFollowupState();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not save follow-up settings.");
    } finally {
      setSavingFollowupConfig(false);
    }
  };

  const triggerFollowups = async () => {
    setTriggeringFollowups(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/admin/proposals/trigger-followups`, {}, { headers: headers() });
      const sentCount = Array.isArray(response.data?.sent) ? response.data.sent.length : response.data?.count ?? 0;
      toast.success(response.data?.message || `Processed ${sentCount} follow-up${sentCount === 1 ? "" : "s"}.`);
      await refresh();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not trigger follow-ups.");
    } finally {
      setTriggeringFollowups(false);
    }
  };

  const applySuggestion = async (proposalId: string, suggestionId: string) => {
    setMutatingSuggestionId(suggestionId);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/admin/proposals/${proposalId}/revision-suggestions/${suggestionId}/apply`,
        {},
        { headers: headers() }
      );
      toast.success(response.data?.message || "Suggestion applied.");
      await loadSuggestions(proposalId);
      await refreshProposalMetadata(proposalId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not apply suggestion.");
    } finally {
      setMutatingSuggestionId(null);
    }
  };

  const dismissSuggestion = async (proposalId: string, suggestionId: string) => {
    setMutatingSuggestionId(suggestionId);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/admin/proposals/${proposalId}/revision-suggestions/${suggestionId}/dismiss`,
        {},
        { headers: headers() }
      );
      toast.success(response.data?.message || "Suggestion dismissed.");
      await loadSuggestions(proposalId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not dismiss suggestion.");
    } finally {
      setMutatingSuggestionId(null);
    }
  };

  const regenerateSection = async (proposalId: string, sectionName: string) => {
    if (!sectionName.trim()) {
      toast.error("Enter a section name.");
      return;
    }
    setRegeneratingSection(sectionName);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/admin/proposals/${proposalId}/regenerate-section`,
        { section_name: sectionName },
        { headers: headers() }
      );
      toast.success(`Regenerated ${response.data?.section_name || sectionName}.`);
      await loadSuggestions(proposalId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not regenerate section.");
    } finally {
      setRegeneratingSection("");
    }
  };

  const copyLink = async (proposalId: string) => {
    const url = `${window.location.origin}/proposal/${proposalId}`;
    await navigator.clipboard.writeText(url);
    toast.success("Public link copied.");
  };

  const openPublicProposal = (proposalId: string) => {
    window.open(`/proposal/${proposalId}`, "_blank", "noopener,noreferrer");
  };

  const loadProposal = async (proposalId: string) => {
    await loadEngagement(proposalId);
    await loadSuggestions(proposalId);
  };

  useEffect(() => {
    void refreshRef.current?.();
  }, []);

  const selectedProposal = proposals.find((proposal) => proposal.proposal_id === selectedProposalId) || null;
  const staleProposalIds = new Set(staleProposals.map((proposal) => proposal.proposal_id));

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <section className="rounded-2xl border-2 border-black bg-white p-6 shadow-[8px_8px_0px_#000]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Proposal Ops</p>
            <h1 className="mt-2 text-3xl font-black text-slate-950">Public proposals and buyer engagement</h1>
            <p className="mt-2 text-sm font-medium text-slate-600">
              Track proposal views, open the buyer-facing page, and inspect the chat transcript by proposal.
            </p>
          </div>
          <button
            onClick={refresh}
            className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-slate-100 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px]"
          >
            <LuRefreshCw size={14} />
            Refresh
          </button>
        </div>

        <div className="mt-6 space-y-4">
          {loading && !proposals.length ? (
            <div className="rounded-xl border-2 border-dashed border-black bg-slate-50 p-6 text-sm font-medium text-slate-500">
              Loading proposals...
            </div>
          ) : proposals.length ? (
            proposals.map((proposal) => {
              const active = proposal.proposal_id === selectedProposalId;
              const buyers = proposal.buyer_sessions?.length ?? 0;
              const messages = proposal.buyer_sessions?.reduce((count, session) => count + (session.messages?.length ?? 0), 0) ?? 0;
              const proposalSuggestions = active ? suggestions : [];
              const isFollowupSent = Boolean(proposal.followup_sent);
              const isStale = staleProposalIds.has(proposal.proposal_id);

              return (
                <div
                  key={proposal.proposal_id}
                  onClick={() => loadProposal(proposal.proposal_id)}
                  role="button"
                  tabIndex={0}
                  className={`w-full rounded-2xl border-2 border-black p-4 text-left shadow-[6px_6px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px] ${
                    active ? "bg-amber-200" : "bg-white"
                  }`}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-lg font-black text-slate-950">{proposal.proposal_id}</div>
                      <div className="mt-1 text-xs font-black uppercase tracking-[0.25em] text-slate-500">
                        {proposal.status || "active"} {proposal.created_at ? `- ${new Date(proposal.created_at).toLocaleString()}` : ""}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs font-black">
                      <span className="rounded-full border-2 border-black bg-cyan-200 px-3 py-1">Views: {proposal.views ?? 0}</span>
                      <span className="rounded-full border-2 border-black bg-emerald-200 px-3 py-1">Buyers: {buyers}</span>
                      <span className="rounded-full border-2 border-black bg-rose-200 px-3 py-1">Messages: {messages}</span>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <span className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-slate-100 px-3 py-2 text-sm font-black">
                      <LuMessageSquare size={14} />
                      Buyer chat enabled
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-slate-100 px-3 py-2 text-sm font-black">
                      <LuEye size={14} />
                      Engagement tracking
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-slate-100 px-3 py-2 text-sm font-black">
                      <LuSparkles size={14} />
                      Suggestions: {proposalSuggestions.length || proposal.revision_suggestions?.length || 0}
                    </span>
                    <span
                      className={`inline-flex items-center gap-2 rounded-xl border-2 border-black px-3 py-2 text-sm font-black ${
                        isFollowupSent
                          ? "bg-emerald-200"
                          : isStale
                            ? "bg-amber-200"
                            : "bg-slate-100"
                      }`}
                    >
                      {isFollowupSent ? "Follow-up sent" : isStale ? "Follow-up due" : "Follow-up tracking"}
                    </span>
                  </div>
                  <div className="mt-4 rounded-xl border-2 border-black bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
                    <span className="mr-2 font-black uppercase tracking-[0.2em] text-slate-500">Latest activity</span>
                    {formatDateTime(proposal.latest_buyer_activity || proposal.buyer_sessions?.[0]?.last_active || proposal.created_at)}
                    {proposal.followup_sent_at ? (
                      <>
                        <span className="mx-2 text-slate-400">•</span>
                        <span className="font-black uppercase tracking-[0.2em] text-emerald-700">Sent</span>
                        <span className="ml-2">{formatDateTime(proposal.followup_sent_at)}</span>
                      </>
                    ) : null}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        copyLink(proposal.proposal_id);
                      }}
                      className="rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-black shadow-[4px_4px_0px_#000]"
                    >
                      <LuCopy className="mr-2 inline-block" size={14} />
                      Copy link
                    </button>
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        openPublicProposal(proposal.proposal_id);
                      }}
                      className="rounded-xl border-2 border-black bg-black px-3 py-2 text-sm font-black text-white shadow-[4px_4px_0px_#000]"
                    >
                      <LuExternalLink className="mr-2 inline-block" size={14} />
                      Open public view
                    </button>
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        loadProposal(proposal.proposal_id);
                      }}
                      className="rounded-xl border-2 border-black bg-[#E0F2FE] px-3 py-2 text-sm font-black shadow-[4px_4px_0px_#000]"
                    >
                      <LuSparkles className="mr-2 inline-block" size={14} />
                      View suggestions
                    </button>
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        generateSuggestions(proposal.proposal_id, true);
                      }}
                      className="rounded-xl border-2 border-black bg-[#FDE68A] px-3 py-2 text-sm font-black shadow-[4px_4px_0px_#000]"
                    >
                      <LuRotateCcw className="mr-2 inline-block" size={14} />
                      Generate
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="rounded-xl border-2 border-dashed border-black bg-slate-50 p-6 text-sm font-medium text-slate-500">
              No proposals have been generated yet. Use the PDF page to generate one from selected documents.
            </div>
          )}
        </div>
      </section>

      <aside className="rounded-2xl border-2 border-black bg-white p-6 shadow-[8px_8px_0px_#000]">
        <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Engagement</p>
        <h2 className="mt-2 text-2xl font-black text-slate-950">Buyer activity</h2>

        <div className="mt-6 rounded-2xl border-2 border-black bg-[#F8FAFC] p-4 shadow-[4px_4px_0px_#000]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Follow-up automation</div>
              <div className="mt-1 text-sm font-medium text-slate-600">
                Configure when stale proposals should receive a follow-up email and trigger the queue manually.
              </div>
            </div>
            <span
              className={`rounded-full border-2 border-black px-3 py-1 text-xs font-black uppercase tracking-[0.2em] ${
                followupConfig?.enabled ? "bg-emerald-200" : "bg-rose-200"
              }`}
            >
              {followupConfig?.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>

          <div className="mt-4 grid gap-3">
            <label className="flex items-center gap-3 rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-bold shadow-[3px_3px_0px_#000]">
              <input
                type="checkbox"
                checked={followupEnabledDraft}
                onChange={(event) => setFollowupEnabledDraft(event.target.checked)}
                className="h-4 w-4 accent-black"
              />
              Enable automatic follow-ups
            </label>

            <label className="rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-bold shadow-[3px_3px_0px_#000]">
              <div className="mb-1 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
                Stale threshold (hours)
              </div>
              <input
                type="number"
                min={12}
                max={168}
                value={followupDelayDraft}
                onChange={(event) => setFollowupDelayDraft(event.target.value)}
                className="w-full bg-transparent text-sm font-bold outline-none"
              />
            </label>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={saveFollowupConfig}
              disabled={savingFollowupConfig || followupLoading}
              className="rounded-xl border-2 border-black bg-black px-3 py-2 text-xs font-black text-white shadow-[3px_3px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingFollowupConfig ? "Saving..." : "Save settings"}
            </button>
            <button
              onClick={triggerFollowups}
              disabled={triggeringFollowups || followupLoading || !staleProposals.length}
              className="rounded-xl border-2 border-black bg-[#FDE68A] px-3 py-2 text-xs font-black shadow-[3px_3px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {triggeringFollowups ? "Triggering..." : "Trigger stale follow-ups"}
            </button>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3 text-center text-xs font-black">
            <div className="rounded-xl border-2 border-black bg-cyan-200 p-3">
              <div className="text-lg">{staleProposals.length}</div>
              <div className="uppercase tracking-[0.2em]">Stale</div>
            </div>
            <div className="rounded-xl border-2 border-black bg-emerald-200 p-3">
              <div className="text-lg">{followupConfig?.delay_hours ?? 48}</div>
              <div className="uppercase tracking-[0.2em]">Delay</div>
            </div>
            <div className="rounded-xl border-2 border-black bg-amber-200 p-3">
              <div className="text-lg">{proposals.filter((proposal) => proposal.followup_sent).length}</div>
              <div className="uppercase tracking-[0.2em]">Sent</div>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Queued follow-ups</div>
            {staleProposals.length ? (
              staleProposals.slice(0, 4).map((proposal) => (
                <div key={proposal.proposal_id} className="rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-[3px_3px_0px_#000]">
                  <div className="font-black text-slate-950">{proposal.title || proposal.proposal_id}</div>
                  <div className="text-xs font-semibold text-slate-500">
                    Last activity: {formatDateTime(proposal.latest_buyer_activity || proposal.buyer_sessions?.[0]?.last_active)}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border-2 border-dashed border-black bg-white px-3 py-3 text-sm font-medium text-slate-500">
                No stale proposals are waiting right now.
              </div>
            )}
          </div>
        </div>

        {engagement ? (
          <div className="mt-6 space-y-5">
            <div className="grid grid-cols-3 gap-3 text-center text-sm font-black">
              <div className="rounded-xl border-2 border-black bg-cyan-200 p-3">
                <div className="text-2xl">{engagement.views}</div>
                <div className="text-xs uppercase tracking-[0.2em]">Views</div>
              </div>
              <div className="rounded-xl border-2 border-black bg-emerald-200 p-3">
                <div className="text-2xl">{engagement.unique_buyers}</div>
                <div className="text-xs uppercase tracking-[0.2em]">Buyers</div>
              </div>
              <div className="rounded-xl border-2 border-black bg-amber-200 p-3">
                <div className="text-2xl">{engagement.buyer_sessions.reduce((count, session) => count + (session.questions_asked ?? 0), 0)}</div>
                <div className="text-xs uppercase tracking-[0.2em]">Questions</div>
              </div>
            </div>

            {selectedProposal ? (
              <div className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0px_#000]">
                <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Follow-up state</div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs font-black">
                  <span className={`rounded-full border-2 border-black px-3 py-1 ${selectedProposal.followup_sent ? "bg-emerald-200" : "bg-slate-100"}`}>
                    {selectedProposal.followup_sent ? "Follow-up already sent" : "No follow-up sent yet"}
                  </span>
                  <span className={`rounded-full border-2 border-black px-3 py-1 ${staleProposalIds.has(selectedProposal.proposal_id) ? "bg-amber-200" : "bg-slate-100"}`}>
                    {staleProposalIds.has(selectedProposal.proposal_id) ? "Stale and eligible" : "Within threshold"}
                  </span>
                </div>
                <div className="mt-3 text-sm font-medium text-slate-700">
                  <span className="font-black uppercase tracking-[0.2em] text-slate-500">Last buyer activity</span>
                  <div className="mt-1">{formatDateTime(engagement.latest_buyer_activity || selectedProposal.latest_buyer_activity || selectedProposal.buyer_sessions?.[0]?.last_active || selectedProposal.created_at)}</div>
                </div>
                <div className="mt-3 text-sm font-medium text-slate-700">
                  <span className="font-black uppercase tracking-[0.2em] text-slate-500">Last view</span>
                  <div className="mt-1">{formatDateTime(engagement.last_view_at)}</div>
                </div>
                {selectedProposal.followup_sent_at ? (
                  <div className="mt-3 text-sm font-medium text-slate-700">
                    <span className="font-black uppercase tracking-[0.2em] text-slate-500">Follow-up sent</span>
                    <div className="mt-1">{formatDateTime(selectedProposal.followup_sent_at)}</div>
                  </div>
                ) : null}
                {selectedProposal.last_followup?.subject ? (
                  <div className="mt-3 text-sm font-medium text-slate-700">
                    <span className="font-black uppercase tracking-[0.2em] text-slate-500">Last follow-up subject</span>
                    <div className="mt-1">{selectedProposal.last_followup.subject}</div>
                  </div>
                ) : null}
                {selectedProposal.last_followup?.top_topic ? (
                  <div className="mt-3 text-sm font-medium text-slate-700">
                    <span className="font-black uppercase tracking-[0.2em] text-slate-500">Follow-up focus</span>
                    <div className="mt-1">{selectedProposal.last_followup.top_topic}</div>
                  </div>
                ) : null}
                {engagement.followup_outcome ? (
                  <div className="mt-4 rounded-xl border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_#000]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Follow-up outcome</span>
                      <span
                        className={`rounded-full border-2 border-black px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                          engagement.followup_outcome.status === "buyer_reengaged" ? "bg-emerald-200" : "bg-amber-200"
                        }`}
                      >
                        {engagement.followup_outcome.status === "buyer_reengaged" ? "Buyer re-engaged" : "Waiting"}
                      </span>
                    </div>
                    <div className="mt-2 text-sm font-medium text-slate-700">
                      {engagement.followup_outcome.status === "buyer_reengaged"
                        ? `${engagement.followup_outcome.event_count ?? 0} follow-on event(s) after the follow-up.`
                        : "No tracked buyer activity after the latest follow-up yet."}
                    </div>
                    {engagement.followup_outcome.last_reengaged_at ? (
                      <div className="mt-2 text-xs font-semibold text-slate-500">
                        Latest follow-on activity: {formatDateTime(engagement.followup_outcome.last_reengaged_at)}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-2xl border-2 border-black bg-[#EEF2FF] p-4 shadow-[4px_4px_0px_#000]">
                <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Repeated buyer questions</div>
                <div className="mt-3 space-y-3">
                  {engagement.question_summary?.length ? (
                    engagement.question_summary.slice(0, 5).map((question) => (
                      <div key={`${question.question}-${question.last_asked_at || ""}`} className="rounded-xl border-2 border-black bg-white p-3 shadow-[3px_3px_0px_#000]">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="text-sm font-black text-slate-950">{question.question}</div>
                          <span className="rounded-full border-2 border-black bg-amber-200 px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em]">
                            {question.count}x
                          </span>
                        </div>
                        <div className="mt-2 text-xs font-semibold text-slate-600">
                          Seen across {question.session_count ?? 1} session{(question.session_count ?? 1) === 1 ? "" : "s"} • Last asked {formatDateTime(question.last_asked_at)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl border-2 border-dashed border-black bg-white p-4 text-sm font-medium text-slate-500">
                      No repeated buyer-question themes yet.
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border-2 border-black bg-[#ECFDF5] p-4 shadow-[4px_4px_0px_#000]">
                <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Engagement timeline</div>
                <div className="mt-3 space-y-3">
                  {engagement.engagement_timeline?.length ? (
                    engagement.engagement_timeline.slice(0, 8).map((event, index) => (
                      <div key={`${event.event_type || "event"}-${event.occurred_at || index}-${index}`} className="rounded-xl border-2 border-black bg-white p-3 shadow-[3px_3px_0px_#000]">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="text-sm font-black text-slate-950">{event.label || "Proposal activity"}</div>
                          <span className={`rounded-full border-2 border-black px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                            event.event_type === "view"
                              ? "bg-cyan-200"
                              : event.event_type === "user_message"
                                ? "bg-amber-200"
                                : "bg-emerald-200"
                          }`}>
                            {event.event_type === "view" ? "View" : event.event_type === "user_message" ? "Buyer" : "Pravaha"}
                          </span>
                        </div>
                        <div className="mt-1 text-xs font-semibold text-slate-500">{formatDateTime(event.occurred_at)}</div>
                        {event.content ? (
                          <div className="mt-2 text-sm font-medium text-slate-700">{event.content}</div>
                        ) : (
                          <div className="mt-2 text-xs font-semibold text-slate-600">
                            {event.buyer_name || event.viewer_session || "Anonymous activity"}
                            {event.referrer ? ` • ${event.referrer}` : ""}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl border-2 border-dashed border-black bg-white p-4 text-sm font-medium text-slate-500">
                      No engagement events yet.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── Section Dwell Heatmap ─────────────────── */}
            {sectionDwell.length > 0 && (
              <div className="rounded-2xl border-2 border-black bg-white p-5 shadow-[4px_4px_0px_#000]">
                <div className="text-xs font-black uppercase tracking-[0.35em] text-slate-500">Section Dwell Time</div>
                <h3 className="mt-1 text-lg font-black text-slate-950">Where buyers spend time</h3>
                <div className="mt-4 space-y-2">
                  {(() => {
                    const maxSeconds = Math.max(...sectionDwell.map((s) => s.total_seconds), 1);
                    const fmtTime = (s: number) => {
                      if (s >= 3600) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
                      if (s >= 60) return `${Math.floor(s / 60)}m ${s % 60}s`;
                      return `${s}s`;
                    };
                    const heatColor = (ratio: number) => {
                      if (ratio > 0.66) return { bg: "bg-rose-100", bar: "bg-rose-400", border: "border-rose-300" };
                      if (ratio > 0.33) return { bg: "bg-amber-50", bar: "bg-amber-400", border: "border-amber-300" };
                      return { bg: "bg-slate-50", bar: "bg-slate-400", border: "border-slate-300" };
                    };
                    return sectionDwell.map((section) => {
                      const ratio = section.total_seconds / maxSeconds;
                      const colors = heatColor(ratio);
                      return (
                        <div
                          key={section.section_id}
                          className={`rounded-xl border-2 border-black ${colors.bg} p-3`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-black text-slate-950 capitalize">
                              {section.section_id.replace(/-/g, " ")}
                            </span>
                            <div className="flex gap-2 text-[10px] font-black uppercase tracking-[0.15em]">
                              <span className={`rounded-full border-2 ${colors.border} px-2 py-0.5`}>
                                {fmtTime(section.total_seconds)}
                              </span>
                              <span className="rounded-full border-2 border-black bg-cyan-200 px-2 py-0.5">
                                {section.unique_viewers} viewer{section.unique_viewers !== 1 ? "s" : ""}
                              </span>
                            </div>
                          </div>
                          <div className="mt-2 h-2 w-full rounded-full border border-black bg-white overflow-hidden">
                            <div
                              className={`h-full rounded-full ${colors.bar} transition-all`}
                              style={{ width: `${Math.max(ratio * 100, 2)}%` }}
                            />
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            )}

            <div className="space-y-3">
              {engagement.buyer_sessions.length ? (
                engagement.buyer_sessions.map((session, index) => (
                  <div key={`${session.buyer_email || session.buyer_name || index}`} className="rounded-2xl border-2 border-black bg-slate-50 p-4 shadow-[4px_4px_0px_#000]">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-black text-slate-950">{session.buyer_name || "Anonymous buyer"}</div>
                        <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{session.buyer_email || "No email"}</div>
                      </div>
                      <div className="flex flex-wrap gap-2 text-[10px] font-black uppercase tracking-[0.2em]">
                        <span className="rounded-full border-2 border-black bg-cyan-200 px-2 py-1">{session.questions_asked ?? 0} questions</span>
                        <span className="rounded-full border-2 border-black bg-emerald-200 px-2 py-1">{session.message_count ?? session.messages?.length ?? 0} messages</span>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <div className="rounded-xl border-2 border-black bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                        <div className="font-black uppercase tracking-[0.2em] text-slate-500">First question</div>
                        <div className="mt-1 text-sm font-medium text-slate-800">{session.first_question || "Not available"}</div>
                      </div>
                      <div className="rounded-xl border-2 border-black bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                        <div className="font-black uppercase tracking-[0.2em] text-slate-500">Last question</div>
                        <div className="mt-1 text-sm font-medium text-slate-800">{session.last_question || "Not available"}</div>
                      </div>
                    </div>
                    <div className="mt-3 rounded-xl border-2 border-black bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                      <div className="font-black uppercase tracking-[0.2em] text-slate-500">Latest buyer session activity</div>
                      <div className="mt-1 text-sm font-medium text-slate-800">{formatDateTime(session.last_active)}</div>
                      {session.last_assistant_response ? (
                        <div className="mt-2 text-sm font-medium text-slate-700">
                          <span className="font-black uppercase tracking-[0.2em] text-slate-500">Last Pravaha reply</span>
                          <div className="mt-1">{session.last_assistant_response}</div>
                        </div>
                      ) : null}
                    </div>
                    <div className="mt-3 space-y-2">
                      {session.messages?.slice(-3).map((message, messageIndex) => (
                        <div key={`${messageIndex}-${message.role}`} className="rounded-xl border-2 border-black bg-white px-3 py-2 text-xs font-medium text-slate-700">
                          <span className="mr-2 font-black uppercase tracking-[0.2em] text-slate-500">{message.role}</span>
                          {message.content}
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border-2 border-dashed border-black bg-slate-50 p-4 text-sm font-medium text-slate-500">
                  No buyer chats yet.
                </div>
              )}
            </div>

            <div className="rounded-2xl border-2 border-black bg-[#F8FAFC] p-4 shadow-[4px_4px_0px_#000]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Revision suggestions</div>
                  <div className="mt-1 text-sm font-medium text-slate-600">
                    Generate, review, apply, or dismiss proposal improvements from buyer questions.
                  </div>
                </div>
                <button
                  onClick={() => loadSuggestions(engagement.proposal_id)}
                  className="rounded-xl border-2 border-black bg-white px-3 py-2 text-xs font-black shadow-[3px_3px_0px_#000]"
                >
                  <LuRefreshCw className="mr-2 inline-block" size={13} />
                  Reload
                </button>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => generateSuggestions(engagement.proposal_id, false)}
                  disabled={generatingSuggestions}
                  className="rounded-xl border-2 border-black bg-[#C4B5FD] px-3 py-2 text-xs font-black shadow-[3px_3px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <LuSparkles className="mr-2 inline-block" size={13} />
                  {generatingSuggestions ? "Generating..." : "Generate suggestions"}
                </button>
                <div className="flex-1 rounded-xl border-2 border-black bg-white px-3 py-2 shadow-[3px_3px_0px_#000]">
                  <div className="flex gap-2">
                    <input
                      value={regeneratingSection}
                      onChange={(event) => setRegeneratingSection(event.target.value)}
                      placeholder="pricing, timeline, integration..."
                      className="min-w-0 flex-1 bg-transparent text-xs font-semibold outline-none"
                    />
                    <button
                      onClick={() => regenerateSection(engagement.proposal_id, regeneratingSection)}
                      disabled={!regeneratingSection.trim()}
                      className="rounded-lg border-2 border-black bg-[#DBEAFE] px-3 py-1 text-xs font-black shadow-[2px_2px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <LuPenLine className="mr-1 inline-block" size={12} />
                      Regenerate
                    </button>
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {engagement.revision_outcomes?.length ? (
                  <div className="rounded-2xl border-2 border-black bg-[#EEF2FF] p-4 shadow-[4px_4px_0px_#000]">
                    <div className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Revision impact</div>
                    <div className="mt-3 space-y-3">
                      {engagement.revision_outcomes.map((outcome) => (
                        <div
                          key={`${outcome.suggestion_id || outcome.section_name || "outcome"}`}
                          className="rounded-xl border-2 border-black bg-white p-3 shadow-[3px_3px_0px_#000]"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-sm font-black text-slate-950">
                              {outcome.section_name || "general"}
                            </div>
                            <span
                              className={`rounded-full border-2 border-black px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                                outcome.status === "engagement_after_revision" ? "bg-emerald-200" : "bg-amber-200"
                              }`}
                            >
                              {outcome.status === "engagement_after_revision" ? "Buyer activity after apply" : "No follow-on activity yet"}
                            </span>
                          </div>
                          <div className="mt-2 text-xs font-semibold text-slate-500">
                            Applied: {formatDateTime(outcome.applied_at)}
                          </div>
                          <div className="mt-2 text-sm font-medium text-slate-700">
                            {outcome.event_count ?? 0} tracked engagement event(s) after this revision.
                          </div>
                          {outcome.last_event_at ? (
                            <div className="mt-2 text-xs font-semibold text-slate-500">
                              Latest event: {formatDateTime(outcome.last_event_at)}{outcome.latest_event_type ? ` • ${outcome.latest_event_type}` : ""}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {suggestionsLoading && !suggestions.length ? (
                  <div className="rounded-xl border-2 border-dashed border-black bg-white p-4 text-sm font-medium text-slate-500">
                    Loading suggestions...
                  </div>
                ) : suggestions.length ? (
                  suggestions.map((suggestion) => (
                    <div key={suggestion.suggestion_id} className="rounded-2xl border-2 border-black bg-white p-4 shadow-[4px_4px_0px_#000]">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-sm font-black text-slate-950">
                          {suggestion.section_name || "general"}
                        </div>
                        <span className={`rounded-full border-2 border-black px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                          suggestion.status === "applied"
                            ? "bg-emerald-200"
                            : suggestion.status === "dismissed"
                              ? "bg-rose-200"
                              : "bg-amber-200"
                        }`}>
                          {suggestion.status || "open"}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-medium leading-6 text-slate-700">{suggestion.reason}</p>
                      {!!suggestion.source_questions?.length && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {suggestion.source_questions.slice(0, 3).map((question) => (
                            <span key={question} className="rounded-full border-2 border-black bg-slate-100 px-2 py-1 text-[11px] font-semibold">
                              {question}
                            </span>
                          ))}
                        </div>
                      )}
                      {suggestion.suggested_copy && (
                        <div className="mt-3 rounded-xl border-2 border-black bg-[#FFFDF7] p-3 text-sm font-medium leading-6 text-slate-800">
                          {suggestion.suggested_copy}
                        </div>
                      )}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          onClick={() => applySuggestion(engagement.proposal_id, suggestion.suggestion_id)}
                          disabled={mutatingSuggestionId === suggestion.suggestion_id || suggestion.status === "applied"}
                          className="rounded-xl border-2 border-black bg-emerald-200 px-3 py-2 text-xs font-black shadow-[3px_3px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <LuCheckCircle2 className="mr-2 inline-block" size={13} />
                          {mutatingSuggestionId === suggestion.suggestion_id ? "Applying..." : "Apply"}
                        </button>
                        <button
                          onClick={() => dismissSuggestion(engagement.proposal_id, suggestion.suggestion_id)}
                          disabled={mutatingSuggestionId === suggestion.suggestion_id || suggestion.status === "dismissed"}
                          className="rounded-xl border-2 border-black bg-rose-200 px-3 py-2 text-xs font-black shadow-[3px_3px_0px_#000] disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <LuXCircle className="mr-2 inline-block" size={13} />
                          {mutatingSuggestionId === suggestion.suggestion_id ? "Saving..." : "Dismiss"}
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl border-2 border-dashed border-black bg-white p-4 text-sm font-medium text-slate-500">
                    No suggestions yet. Generate them from buyer questions or reload if they already exist.
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-xl border-2 border-dashed border-black bg-slate-50 p-4 text-sm font-medium text-slate-500">
            Select a proposal to inspect buyer engagement.
          </div>
        )}
      </aside>
    </div>
  );
}
