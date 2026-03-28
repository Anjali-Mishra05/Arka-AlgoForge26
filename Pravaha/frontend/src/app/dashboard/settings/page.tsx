"use client";

import ZapierCard from "@/components/settings/ZapierCard";
import axios from "axios";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import {
  LuArrowRight,
  LuBot,
  LuPlugZap,
  LuRefreshCw,
  LuShieldCheck,
  LuToggleLeft,
  LuToggleRight,
  LuWorkflow,
} from "react-icons/lu";

type CrmStatus = {
  connected?: boolean;
  portal_id?: string;
  connected_at?: string;
  expires_at?: string;
  token_status?: string;
  refresh_strategy?: string;
  sync_preferences?: Record<string, boolean>;
};

type CrmSyncPreferenceKey = "buyer_engagement" | "proposal_generated" | "call_summary" | "bulk_email";

type SyncLogEntry = {
  event?: string;
  provider?: string;
  entity_id?: string;
  status?: string;
  error?: string;
  timestamp?: string;
  created_at?: string;
};

type AutomationItem = {
  automation_id?: string;
  name?: string;
  type?: string;
  trigger?: string;
  description?: string;
  enabled?: boolean;
  scope?: Record<string, unknown>;
  schedule?: Record<string, unknown>;
  config?: Record<string, unknown>;
  next_run_at?: string;
  next_run?: string;
  runtime_status?: string;
  review_required?: boolean;
  review_required_reason?: string;
  retry_count?: number;
  max_retries?: number;
  dead_lettered?: boolean;
  dead_letter_reason?: string;
  dead_lettered_at?: string;
  last_run_at?: string;
  last_run_status?: string;
  last_error?: string;
  created_at?: string;
  updated_at?: string;
};

type AutomationRun = {
  automation_id?: string;
  automation_name?: string;
  status?: string;
  error?: string;
  output?: Record<string, unknown>;
  retry_count?: number;
  max_retries?: number;
  dead_lettered?: boolean;
  dead_letter_reason?: string;
  review_required?: boolean;
  review_required_reason?: string;
  started_at?: string;
  completed_at?: string;
  finished_at?: string;
  created_at?: string;
};

const crmSyncControls: Array<{
  key: CrmSyncPreferenceKey;
  title: string;
  description: string;
}> = [
  {
    key: "buyer_engagement",
    title: "Buyer engagement",
    description: "Create or update CRM records when a buyer engages from a public proposal.",
  },
  {
    key: "proposal_generated",
    title: "Proposal generation",
    description: "Log proposal-generation activity when a new shareable proposal is created.",
  },
  {
    key: "call_summary",
    title: "Call summary",
    description: "Log call outcomes and CRM-ready notes after the summary pipeline completes.",
  },
  {
    key: "bulk_email",
    title: "Bulk email",
    description: "Track outbound email campaigns and contact notes from the dashboard mailer.",
  },
];

function formatDate(value?: string) {
  if (!value) return "Pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatScheduleSummary(schedule?: Record<string, unknown>) {
  if (!schedule || Object.keys(schedule).length === 0) {
    return "No schedule configured";
  }

  const type = String(schedule.mode || schedule.type || schedule.trigger || schedule.frequency || "manual");
  const intervalMinutes = schedule.interval_minutes ?? schedule.every_minutes;
  const intervalHours = schedule.interval_hours ?? schedule.interval ?? schedule.every_hours;
  const cron = String(schedule.cron || schedule.rrule || "");
  const byDay = schedule.byday || schedule.days || schedule.weekdays;

  if (type === "manual") {
    return "Manual run only";
  }

  const parts = [type.replace(/_/g, " ")];
  if (typeof intervalMinutes === "number" && intervalMinutes > 0) {
    parts.push(intervalMinutes % 60 === 0 ? `every ${intervalMinutes / 60}h` : `every ${intervalMinutes}m`);
  } else if (typeof intervalHours === "number" && intervalHours > 0) {
    parts.push(`every ${intervalHours}h`);
  }
  if (cron) {
    parts.push(cron);
  }
  if (Array.isArray(byDay) && byDay.length) {
    parts.push(byDay.join(", "));
  } else if (typeof byDay === "string" && byDay.trim()) {
    parts.push(byDay);
  }

  return parts.join(" | ");
}

function getAutomationScheduleNextRun(automation: AutomationItem) {
  return (
    automation.next_run_at ||
    automation.next_run ||
    (automation.schedule?.next_run_at as string | undefined) ||
    (automation.schedule?.nextRunAt as string | undefined) ||
    (automation.config?.next_run_at as string | undefined) ||
    (automation.config?.nextRunAt as string | undefined) ||
    (automation.config?.next_run as string | undefined)
  );
}

function getRetryState(automation: AutomationItem, run?: AutomationRun | null) {
  const retryCount =
    run?.retry_count ??
    automation.retry_count ??
    (typeof automation.config?.retry_count === "number" ? (automation.config.retry_count as number) : undefined) ??
    (typeof automation.config?.retryCount === "number" ? (automation.config.retryCount as number) : undefined) ??
    (typeof run?.output?.retry_count === "number" ? (run.output.retry_count as number) : undefined) ??
    (typeof run?.output?.retryCount === "number" ? (run.output.retryCount as number) : undefined);
  const maxRetries =
    run?.max_retries ??
    automation.max_retries ??
    (typeof automation.config?.retry_limit === "number" ? (automation.config.retry_limit as number) : undefined) ??
    (typeof automation.config?.max_retries === "number" ? (automation.config.max_retries as number) : undefined) ??
    (typeof automation.config?.maxRetries === "number" ? (automation.config.maxRetries as number) : undefined) ??
    (typeof run?.output?.max_retries === "number" ? (run.output.max_retries as number) : undefined) ??
    (typeof run?.output?.maxRetries === "number" ? (run.output.maxRetries as number) : undefined);
  const deadLettered = Boolean(
    run?.dead_lettered ??
      automation.dead_lettered ??
      (automation.runtime_status === "dead_letter" ? true : undefined) ??
      (automation.dead_lettered_at ? true : undefined) ??
      (typeof automation.config?.dead_lettered === "boolean" ? automation.config.dead_lettered : undefined) ??
      (typeof automation.config?.deadLettered === "boolean" ? automation.config.deadLettered : undefined) ??
      (typeof run?.output?.dead_lettered === "boolean" ? run.output.dead_lettered : undefined) ??
      (typeof run?.output?.deadLettered === "boolean" ? run.output.deadLettered : undefined)
  );
  const deadLetterReason =
    run?.dead_letter_reason ||
    automation.dead_letter_reason ||
    String(
      automation.config?.dead_letter_reason ||
        automation.config?.deadLetterReason ||
        run?.output?.dead_letter_reason ||
        run?.output?.deadLetterReason ||
        ""
    );

  return {
    retryCount,
    maxRetries,
    deadLettered,
    deadLetterReason,
  };
}

function getReviewState(automation: AutomationItem, run?: AutomationRun | null) {
  const reviewRequired = Boolean(
    run?.review_required ??
      automation.review_required ??
      (typeof automation.config?.review_required === "boolean" ? automation.config.review_required : undefined) ??
      (typeof automation.config?.reviewRequired === "boolean" ? automation.config.reviewRequired : undefined) ??
      (typeof run?.output?.review_required === "boolean" ? run.output.review_required : undefined) ??
      (typeof run?.output?.reviewRequired === "boolean" ? run.output.reviewRequired : undefined)
  );
  const reviewRequiredReason =
    run?.review_required_reason ||
    automation.review_required_reason ||
    String(
      automation.config?.review_required_reason ||
        automation.config?.reviewRequiredReason ||
        run?.output?.review_required_reason ||
        run?.output?.reviewRequiredReason ||
        ""
    );

  return {
    reviewRequired,
    reviewRequiredReason,
  };
}

function findLatestRun(runs: AutomationRun[], automationId?: string, automationName?: string) {
  return runs.find((run) => run.automation_id === automationId || run.automation_name === automationName) || null;
}

export default function SettingsPage() {
  const router = useRouter();
  const [crmStatus, setCrmStatus] = useState<CrmStatus | null>(null);
  const [syncLog, setSyncLog] = useState<SyncLogEntry[]>([]);
  const [automations, setAutomations] = useState<AutomationItem[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const [crmResponse, logResponse, automationResponse, runsResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/admin/crm/status`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/crm/sync_log`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/automations`, { headers: getAuthHeaders() }),
        axios.get(`${API_BASE_URL}/admin/automations/runs`, {
          params: { limit: 10 },
          headers: getAuthHeaders(),
        }),
      ]);

      setCrmStatus(crmResponse.data);
      setSyncLog(Array.isArray(logResponse.data) ? logResponse.data : []);
      setAutomations(Array.isArray(automationResponse.data) ? automationResponse.data : []);
      setRuns(Array.isArray(runsResponse.data) ? runsResponse.data : []);
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
        return;
      }
      toast.error("Unable to load settings.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const connectHubSpot = async () => {
    setBusyAction("connect");
    try {
      window.location.assign(`${API_BASE_URL}/admin/crm/connect`);
    } catch (error: any) {
      const message = error?.response?.data?.detail || "Could not start HubSpot connection.";
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  const disconnectHubSpot = async () => {
    setBusyAction("disconnect");
    try {
      await axios.delete(`${API_BASE_URL}/admin/crm/disconnect`, { headers: getAuthHeaders() });
      toast.success("HubSpot disconnected.");
      await loadSettings();
    } catch (error: any) {
      const message = error?.response?.data?.detail || "Could not disconnect HubSpot.";
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  const updateCrmPreference = async (event: CrmSyncPreferenceKey, enabled: boolean) => {
    setBusyAction(`crm-pref-${event}`);
    try {
      const response = await axios.put(
        `${API_BASE_URL}/admin/crm/preferences`,
        { event, enabled },
        { headers: getAuthHeaders() }
      );
      setCrmStatus((current) => ({
        ...(current || {}),
        sync_preferences: response.data?.sync_preferences || {},
      }));
      toast.success(enabled ? "CRM sync enabled." : "CRM sync paused.");
    } catch (error: any) {
      const message = error?.response?.data?.detail || "Could not update CRM sync preference.";
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  const toggleAutomation = async (automationId: string, enabled: boolean) => {
    setBusyAction(`toggle-${automationId}`);
    try {
      await axios.post(
        `${API_BASE_URL}/admin/automations/${automationId}/toggle`,
        { enabled },
        { headers: getAuthHeaders() }
      );
      toast.success(enabled ? "Automation enabled." : "Automation disabled.");
      await loadSettings();
    } catch (error: any) {
      const message = error?.response?.data?.detail || "Could not update automation.";
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  const runAutomation = async (automationId: string) => {
    setBusyAction(`run-${automationId}`);
    try {
      await axios.post(
        `${API_BASE_URL}/admin/automations/${automationId}/run`,
        { input: {} },
        { headers: getAuthHeaders() }
      );
      toast.success("Automation run queued.");
      await loadSettings();
    } catch (error: any) {
      const message = error?.response?.data?.detail || "Could not run automation.";
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 text-slate-950">
      <section className="rounded-[32px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000] md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#DBEAFE] px-4 py-2 text-xs font-black uppercase tracking-[0.25em]">
              <LuWorkflow size={14} />
              CRM and automation control center
            </div>
            <h1 className="mt-5 text-4xl font-black leading-tight md:text-6xl">Integrations, sync logs, and agent automation.</h1>
            <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-slate-700">
              This page keeps the operational layer visible: HubSpot status, recent sync events, automation toggles, and
              the internal agent workflows that keep Pravaha moving after the tab is closed.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadSettings()}
            className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-[#FFF7ED] px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px]"
          >
            <LuRefreshCw size={14} />
            Refresh all
          </button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">HubSpot</p>
              <h2 className="mt-2 text-2xl font-black">CRM connection</h2>
            </div>
            <span
              className={`inline-flex items-center gap-2 rounded-full border-2 border-black px-3 py-1 text-xs font-black uppercase tracking-[0.2em] ${
                crmStatus?.connected ? "bg-[#DCFCE7] text-emerald-900" : "bg-[#FEE2E2] text-rose-900"
              }`}
            >
              <LuShieldCheck size={14} />
              {crmStatus?.connected ? "Connected" : "Disconnected"}
            </span>
          </div>

          <div className="mt-5 grid gap-3">
            <div className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
              <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Portal ID</div>
              <div className="mt-2 text-sm font-semibold">{crmStatus?.portal_id || "Not connected"}</div>
            </div>
            <div className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
              <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Connected at</div>
              <div className="mt-2 text-sm font-semibold">{formatDate(crmStatus?.connected_at)}</div>
            </div>
            <div className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
              <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Token status</div>
              <div className="mt-2 text-sm font-semibold capitalize">{crmStatus?.token_status || "disconnected"}</div>
            </div>
            <div className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
              <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Access token expires</div>
              <div className="mt-2 text-sm font-semibold">{formatDate(crmStatus?.expires_at)}</div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={connectHubSpot}
              disabled={busyAction === "connect"}
              className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-[#C4B5FD] px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px] disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LuPlugZap size={14} />
              {busyAction === "connect" ? "Connecting..." : "Connect HubSpot"}
            </button>
            <button
              type="button"
              onClick={disconnectHubSpot}
              disabled={busyAction === "disconnect" || !crmStatus?.connected}
              className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-white px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px] disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LuPlugZap size={14} />
              {busyAction === "disconnect" ? "Disconnecting..." : "Disconnect"}
            </button>
          </div>

          <div className="mt-6 rounded-2xl border-2 border-black bg-[#E0F2FE] p-4 shadow-[4px_4px_0_#000]">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-sky-800">CRM sync controls</p>
            <p className="mt-3 text-sm font-medium leading-6 text-slate-700">
              Pravaha refreshes HubSpot access tokens automatically on the next live sync path. Toggle each sync source
              independently to control what reaches the connected workspace.
            </p>
            <div className="mt-3 grid gap-3">
              {crmSyncControls.map((action) => {
                const enabled = Boolean(crmStatus?.sync_preferences?.[action.key]);
                return (
                <div key={action.key} className="rounded-xl border-2 border-black bg-white px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-black">{action.title}</div>
                      <div className="mt-1 text-sm font-medium text-slate-600">{action.description}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => updateCrmPreference(action.key, !enabled)}
                      disabled={busyAction === `crm-pref-${action.key}`}
                      className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-[#FFF7ED] px-3 py-2 text-xs font-black uppercase tracking-[0.18em] shadow-[3px_3px_0_#000] disabled:cursor-not-allowed disabled:opacity-70"
                    >
                      {enabled ? <LuToggleRight size={16} /> : <LuToggleLeft size={16} />}
                      {enabled ? "Enabled" : "Paused"}
                    </button>
                  </div>
                  <div className="mt-3 inline-flex rounded-full border-2 border-black bg-white px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em] text-slate-600">
                    {crmStatus?.connected ? "Effective on next sync" : "Saved until HubSpot is connected"}
                  </div>
                </div>
              );})}
            </div>
          </div>
        </div>

        {/* Zapier + MCP Integration */}
        <ZapierCard />

        <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Automation overview</p>
              <h2 className="mt-2 text-2xl font-black">Agent workflows</h2>
            </div>
            <div className="rounded-full border-2 border-black bg-[#DCFCE7] px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-emerald-900">
              {automations.length} definitions
            </div>
          </div>

          <div className="mt-5 space-y-4">
            {automations.length ? (
              automations.map((automation) => {
                const automationId = automation.automation_id || automation.name || "automation";
                const enabled = Boolean(automation.enabled);
                const latestRun = findLatestRun(runs, automation.automation_id, automation.name);
                const retryState = getRetryState(automation, latestRun);
                const reviewState = getReviewState(automation, latestRun);
                const nextRunAt = getAutomationScheduleNextRun(automation);

                return (
                  <div key={automationId} className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <LuBot size={16} className="text-slate-700" />
                          <h3 className="text-lg font-black">{automation.name || "Untitled automation"}</h3>
                        </div>
                        <p className="mt-2 text-sm font-medium leading-6 text-slate-700">
                          {automation.description || "No description provided."}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-black uppercase tracking-[0.18em] text-slate-600">
                          <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                            {automation.type || "custom"}
                          </span>
                          <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                            {enabled ? "Enabled" : "Disabled"}
                          </span>
                          <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                            Updated {formatDate(automation.updated_at)}
                          </span>
                          <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                            {automation.schedule || automation.config?.schedule
                              ? formatScheduleSummary((automation.schedule ||
                                  automation.config?.schedule) as Record<string, unknown>)
                              : "Manual run only"}
                          </span>
                          {nextRunAt ? (
                            <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                              Next run {formatDate(nextRunAt)}
                            </span>
                          ) : null}
                          {reviewState.reviewRequired ? (
                            <span className="rounded-full border-2 border-black bg-amber-200 px-3 py-1 text-amber-950">
                              Review required
                            </span>
                          ) : null}
                          {retryState.retryCount !== undefined || retryState.maxRetries !== undefined ? (
                            <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                              Retry {retryState.retryCount ?? 0}
                              {retryState.maxRetries !== undefined ? `/${retryState.maxRetries}` : ""}
                            </span>
                          ) : null}
                          {retryState.deadLettered ? (
                            <span className="rounded-full border-2 border-black bg-rose-200 px-3 py-1 text-rose-950">
                              Dead-lettered
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                          <div className="rounded-2xl border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0_#000]">
                            <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Last run</div>
                            <div className="mt-1 text-sm font-black">{automation.last_run_status || latestRun?.status || "Pending"}</div>
                            <div className="mt-1 text-xs font-medium text-slate-600">
                              {formatDate(
                                automation.last_run_at || latestRun?.completed_at || latestRun?.finished_at || latestRun?.created_at
                              )}
                            </div>
                            {(automation.last_error || latestRun?.error) ? (
                              <div className="mt-2 rounded-xl border-2 border-black bg-[#FEE2E2] px-3 py-2 text-xs font-medium text-rose-900">
                                {automation.last_error || latestRun?.error}
                              </div>
                            ) : null}
                          </div>
                          <div className="rounded-2xl border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0_#000]">
                            <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Runtime state</div>
                            <div className="mt-1 text-sm font-black">{automation.runtime_status || (enabled ? "idle" : "paused")}</div>
                            <div className="mt-1 text-xs font-medium text-slate-600">
                              {automation.runtime_status === "unsupported_schedule"
                                ? "Only manual and interval schedules are currently executable."
                                : reviewState.reviewRequired
                                ? reviewState.reviewRequiredReason || "Needs review before next action"
                                : retryState.deadLettered
                                  ? retryState.deadLetterReason || "In dead-letter state"
                                  : enabled
                                    ? "Enabled and ready for the next run"
                                    : "Disabled until manually enabled"}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => toggleAutomation(automationId, !enabled)}
                          disabled={busyAction === `toggle-${automationId}`}
                          className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-white px-3 py-2 text-sm font-black shadow-[4px_4px_0_#000] disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          {enabled ? <LuToggleRight size={16} /> : <LuToggleLeft size={16} />}
                          {enabled ? "Disable" : "Enable"}
                        </button>
                        <button
                          type="button"
                          onClick={() => runAutomation(automationId)}
                          disabled={busyAction === `run-${automationId}`}
                          className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-[#C4B5FD] px-3 py-2 text-sm font-black shadow-[4px_4px_0_#000] disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          <LuArrowRight size={14} />
                          Run now
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-5 text-sm font-medium text-slate-500">
                No automations found. Create one from the admin automation API to see it here.
              </div>
            )}
          </div>

          <div className="mt-6 rounded-2xl border-2 border-black bg-[#FDE2FF] p-4 shadow-[4px_4px_0_#000]">
            <div className="flex items-center gap-2">
              <LuBot size={16} />
              <p className="text-xs font-black uppercase tracking-[0.2em] text-fuchsia-900">Agent automation overview</p>
            </div>
            <p className="mt-3 text-sm font-medium leading-6 text-slate-700">
              The internal agent layer is for revenue ops only. It should summarize transcripts, draft CRM notes, suggest
              proposal revisions, recommend the next best action, and prepare manager briefs. Every action should stay
              auditable and reviewable.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">CRM sync log</p>
              <h2 className="mt-2 text-2xl font-black">Recent events</h2>
            </div>
            <div className="rounded-full border-2 border-black bg-[#DBEAFE] px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-sky-900">
              {syncLog.length} entries
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border-2 border-black">
            <div className="hidden grid-cols-5 border-b-2 border-black bg-[#FFF7ED] px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-600 md:grid">
              <span>Event</span>
              <span>Provider</span>
              <span>Entity</span>
              <span>Status</span>
              <span>Time</span>
            </div>
            <div className="divide-y-2 divide-black">
              {syncLog.length ? (
                syncLog.map((entry, index) => (
                  <div key={`${entry.event || "event"}-${index}`} className="bg-white px-4 py-3 text-sm">
                    <div className="grid gap-2 md:grid-cols-5">
                      <span className="font-black">{entry.event || "unknown"}</span>
                      <span className="font-semibold capitalize">{entry.provider || "hubspot"}</span>
                      <span className="font-semibold break-all">{entry.entity_id || "n/a"}</span>
                      <span className="font-black uppercase tracking-[0.18em] text-slate-700">{entry.status || "unknown"}</span>
                      <span className="font-medium text-slate-600">{formatDate(entry.timestamp || entry.created_at)}</span>
                    </div>
                    <div className="mt-3 grid gap-2 md:hidden">
                      <div className="rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2">
                        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Provider</div>
                        <div className="mt-1 text-sm font-semibold capitalize">{entry.provider || "hubspot"}</div>
                      </div>
                      <div className="rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2">
                        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Entity</div>
                        <div className="mt-1 break-all text-sm font-semibold">{entry.entity_id || "n/a"}</div>
                      </div>
                      <div className="rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2">
                        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Status</div>
                        <div className="mt-1 text-sm font-black uppercase tracking-[0.16em] text-slate-700">{entry.status || "unknown"}</div>
                      </div>
                      <div className="rounded-xl border-2 border-black bg-[#FFFDF7] px-3 py-2">
                        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Time</div>
                        <div className="mt-1 text-sm font-medium text-slate-600">{formatDate(entry.timestamp || entry.created_at)}</div>
                      </div>
                    </div>
                    {entry.error ? (
                      <div className="mt-3 rounded-xl border-2 border-black bg-[#FEE2E2] px-3 py-2 text-xs font-medium text-rose-900">
                        {entry.error}
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="bg-slate-50 px-4 py-6 text-sm font-medium text-slate-500">No sync events yet.</div>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Recent runs</p>
              <h2 className="mt-2 text-2xl font-black">Automation history</h2>
            </div>
            <div className="rounded-full border-2 border-black bg-[#DCFCE7] px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-emerald-900">
              {runs.length} runs
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {runs.length ? (
              runs.map((run, index) => (
                <div key={`${run.automation_id || "run"}-${index}`} className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-black">{run.automation_name || run.automation_id || "Automation run"}</div>
                      <div className="mt-1 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
                        {formatDate(run.started_at || run.created_at)}
                      </div>
                    </div>
                    <span className="rounded-full border-2 border-black bg-white px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em]">
                      {run.status || "unknown"}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-black uppercase tracking-[0.18em] text-slate-600">
                    {run.review_required ? (
                      <span className="rounded-full border-2 border-black bg-amber-200 px-3 py-1 text-amber-950">
                        Review required
                      </span>
                    ) : null}
                    {run.retry_count !== undefined || run.max_retries !== undefined ? (
                      <span className="rounded-full border-2 border-black bg-white px-3 py-1">
                        Retry {run.retry_count ?? 0}
                        {run.max_retries !== undefined ? `/${run.max_retries}` : ""}
                      </span>
                    ) : null}
                    {run.dead_lettered ? (
                      <span className="rounded-full border-2 border-black bg-rose-200 px-3 py-1 text-rose-950">
                        Dead-lettered
                      </span>
                    ) : null}
                  </div>
                  {run.review_required && run.review_required_reason ? (
                    <div className="mt-3 rounded-xl border-2 border-black bg-[#FFF7ED] px-3 py-2 text-xs font-medium text-amber-950">
                      {run.review_required_reason}
                    </div>
                  ) : null}
                  {run.error ? (
                    <div className="mt-3 rounded-xl border-2 border-black bg-[#FEE2E2] px-3 py-2 text-xs font-medium text-rose-900">
                      {run.error}
                    </div>
                  ) : null}
                  {run.dead_letter_reason ? (
                    <div className="mt-3 rounded-xl border-2 border-black bg-[#FEE2E2] px-3 py-2 text-xs font-medium text-rose-900">
                      {run.dead_letter_reason}
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border-2 border-dashed border-black bg-slate-50 p-5 text-sm font-medium text-slate-500">
                No recent automation runs.
              </div>
            )}
          </div>
        </div>
      </section>

      {loading ? (
        <div className="rounded-[24px] border-2 border-black bg-[#FFF7ED] p-4 text-sm font-black shadow-[6px_6px_0_#000]">
          Loading settings...
        </div>
      ) : null}
    </main>
  );
}

