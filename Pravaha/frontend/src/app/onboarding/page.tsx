"use client";

import axios from "axios";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import { LuCheck, LuCircleDot, LuCopy, LuFileUp, LuSparkles } from "react-icons/lu";

type OnboardingState = {
  completed_steps?: string[];
  current_step?: string | null;
  completed_at?: string | null;
  company_name?: string;
  company_description?: string;
  industry?: string;
  website?: string;
  target_personas?: string[];
  uploaded_docs?: string[];
  test_question?: string;
  proposal_id?: string;
  invite_team_emails?: string[] | string;
};

type StepId = "company_info" | "docs_uploaded" | "ai_trained" | "test_chat" | "share_proposal";

const STEPS: Array<{
  id: StepId;
  title: string;
  description: string;
}> = [
  {
    id: "company_info",
    title: "Company Info",
    description: "Set the basics so Pravaha can speak in your brand voice.",
  },
  {
    id: "docs_uploaded",
    title: "Upload Docs",
    description: "Attach product PDFs, playbooks, or proposal source material.",
  },
  {
    id: "ai_trained",
    title: "Train AI",
    description: "Kick off ingestion so the assistant can ground its answers in your docs.",
  },
  {
    id: "test_chat",
    title: "Test Chat",
    description: "Try a sample question and verify the assistant understands your product.",
  },
  {
    id: "share_proposal",
    title: "Share Proposal",
    description: "Generate the first buyer-facing proposal link and copy it out.",
  },
];

const PERSONA_OPTIONS = ["Founders", "Sales leaders", "Sales reps", "RevOps", "Ops / Enablement"];

function toCommaList(value: string[] | string | undefined | null) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join(", ");
  }

  if (typeof value === "string") {
    return value;
  }

  return "";
}

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function makeSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [training, setTraining] = useState(false);
  const [sendingChat, setSendingChat] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [activeStep, setActiveStep] = useState<StepId>("company_info");
  const [state, setState] = useState<OnboardingState>({});
  const [companyName, setCompanyName] = useState("");
  const [companyDescription, setCompanyDescription] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [targetPersonas, setTargetPersonas] = useState<string[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [testQuestion, setTestQuestion] = useState("What does my company do?");
  const [chatHistory, setChatHistory] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [shareLink, setShareLink] = useState("");
  const [inviteTeamEmails, setInviteTeamEmails] = useState("");
  const [localSessionId] = useState(() => makeSessionId());

  const completed = state.completed_steps || [];
  const stepIndex = Math.max(0, STEPS.findIndex((item) => item.id === activeStep));
  const isComplete = Boolean(state.completed_at) || completed.length >= STEPS.length;
  const progress = isComplete ? 100 : ((stepIndex + 1) / STEPS.length) * 100;
  const completedCount = completed.length;
  const isReturningUser = completedCount > 0 || Boolean(state.completed_at);
  const canSkip = isReturningUser && activeStep !== "share_proposal";

  const suggestions = useMemo(
    () => [
      "Who is your main buyer?",
      "What problem do you solve?",
      "What makes you different?",
      "How long does implementation take?",
    ],
    []
  );

  useEffect(() => {
    const load = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/admin/onboarding`, { headers: getAuthHeaders() });
        const next = response.data || {};
        setState(next);
        setCompanyName(next.company_name || "");
        setCompanyDescription(next.company_description || "");
        setIndustry(next.industry || "");
        setWebsite(next.website || "");
        setTargetPersonas(next.target_personas || []);
        setSelectedDocs(next.uploaded_docs || []);
        setTestQuestion(next.test_question || "What does my company do?");
        setProposalId(next.proposal_id || null);
        setInviteTeamEmails(toCommaList(next.invite_team_emails));
        if (next.current_step) {
          setActiveStep(next.current_step as StepId);
        }
      } catch (error: any) {
        if (error?.response?.status === 401) {
          router.push("/sign-in");
          return;
        }
        toast.error("Could not load onboarding state.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [router]);

  const persistStep = async (step: StepId, data: Record<string, unknown> = {}) => {
    setSaving(true);
    try {
      await axios.post(
        `${API_BASE_URL}/admin/onboarding/step`,
        { step, data },
        { headers: getAuthHeaders() }
      );
      setState((current) => ({
        ...current,
        current_step: step,
        completed_steps: Array.from(new Set([...(current.completed_steps || []), step])),
        ...data,
      }));
      toast.success("Saved");
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Could not save onboarding step.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDocsSelection = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const results: { name: string; status: string }[] = [];

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append("pdf_file", file);
      try {
        const res = await fetch(`${API_BASE_URL}/admin/upload_pdf`, {
          method: "POST",
          credentials: "include",
          body: formData,
        });
        results.push({ name: file.name, status: res.ok ? "uploaded" : "failed" });
      } catch {
        results.push({ name: file.name, status: "failed" });
      }
    }

    const uploadedNames = results.filter((r) => r.status === "uploaded").map((r) => r.name);
    const failedCount = results.filter((r) => r.status === "failed").length;

    if (uploadedNames.length > 0) {
      await fetch(`${API_BASE_URL}/admin/update_selected_docs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(uploadedNames),
      });
    }

    if (failedCount > 0) toast.error(`${failedCount} file(s) failed to upload`);
    if (uploadedNames.length > 0) toast.success(`${uploadedNames.length} file(s) uploaded`);

    const allNames = results.map((r) => r.name);
    setSelectedDocs(allNames);
    await persistStep("docs_uploaded", { uploaded_docs: uploadedNames });
  };

  const trainAi = async () => {
    setTraining(true);
    try {
      await axios.get(`${API_BASE_URL}/admin/ingest`, { headers: getAuthHeaders() });
      await persistStep("ai_trained");
      setActiveStep("test_chat");
      toast.success("Training started");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Training failed");
    } finally {
      setTraining(false);
    }
  };

  const sendTestChat = async (question: string = testQuestion) => {
    const trimmed = question.trim();
    if (!trimmed) {
      toast.error("Enter a test question");
      return;
    }

    setSendingChat(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/chat/response?query=${encodeURIComponent(trimmed)}`,
        {},
        { headers: getAuthHeaders() }
      );
      const reply = response.data?.response || response.data || "No response returned.";
      setChatHistory((current) => [
        ...current,
        { role: "user", content: trimmed },
        { role: "assistant", content: reply },
      ]);
      await persistStep("test_chat", { test_question: trimmed });
      setActiveStep("share_proposal");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not run test chat");
    } finally {
      setSendingChat(false);
    }
  };

  const shareProposal = async () => {
    setSharing(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/generate_proposal`, { headers: getAuthHeaders() });
      const nextProposalId = response.data?.proposal_id || proposalId;
      if (nextProposalId) {
        setProposalId(nextProposalId);
        const nextLink = `${window.location.origin}/proposal/${nextProposalId}`;
        setShareLink(nextLink);
        await persistStep("share_proposal", {
          proposal_id: nextProposalId,
          invite_team_emails: parseCommaList(inviteTeamEmails),
        });
        toast.success("Proposal link ready");
      } else {
        toast.error("No proposal id returned");
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not generate proposal");
    } finally {
      setSharing(false);
    }
  };

  const copyLink = async () => {
    if (!shareLink) return;
    await navigator.clipboard.writeText(shareLink);
    toast.success("Link copied");
  };

  const togglePersona = (persona: string) => {
    setTargetPersonas((current) =>
      current.includes(persona) ? current.filter((item) => item !== persona) : [...current, persona]
    );
  };

  const skipSetup = () => {
    router.push("/dashboard");
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-[#FAFAF5] bg-[linear-gradient(#E5E5DD_1px,transparent_1px),linear-gradient(90deg,#E5E5DD_1px,transparent_1px)] bg-[size:24px_24px] px-4 py-10">
        <div className="mx-auto max-w-6xl rounded-[32px] border-2 border-black bg-white p-8 shadow-[10px_10px_0_#000]">
          <div className="text-lg font-black">Loading onboarding wizard...</div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#FAFAF5] bg-[linear-gradient(#E5E5DD_1px,transparent_1px),linear-gradient(90deg,#E5E5DD_1px,transparent_1px)] bg-[size:24px_24px] px-4 py-6 text-slate-950 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[32px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000] md:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#FDE68A] px-4 py-2 text-xs font-black uppercase tracking-[0.25em]">
                <LuSparkles size={14} />
                5-step onboarding
              </div>
              <h1 className="mt-4 text-4xl font-black leading-tight md:text-6xl">Get Pravaha ready in one pass.</h1>
              <p className="mt-3 max-w-2xl text-sm font-medium leading-6 text-slate-700">
                Fill the company profile, upload your docs, train the assistant, test a live answer, and publish the first proposal link.
              </p>
              {canSkip && (
                <div className="mt-4 inline-flex flex-wrap items-center gap-3 rounded-[20px] border-2 border-black bg-[#DCFCE7] px-4 py-3 shadow-[6px_6px_0_#000]">
                  <div className="text-sm font-black">Returning setup detected.</div>
                  <button
                    type="button"
                    onClick={skipSetup}
                    className="rounded-2xl border-2 border-black bg-black px-4 py-2 text-xs font-black text-white shadow-[3px_3px_0_#000]"
                  >
                    Skip setup
                  </button>
                </div>
              )}
            </div>
            <div className="w-full max-w-md rounded-[24px] border-2 border-black bg-[#F5F3FF] p-4 shadow-[6px_6px_0_#000]">
              <div className="flex items-center justify-between text-xs font-black uppercase tracking-[0.22em] text-slate-500">
                <span>Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="mt-3 h-4 rounded-full border-2 border-black bg-white p-1">
                <div className="h-full rounded-full bg-black" style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-3 space-y-1 text-sm font-semibold text-slate-700">
                <div>
                  {isComplete ? "Setup complete" : `Step ${stepIndex + 1} of ${STEPS.length}: ${STEPS[stepIndex]?.title || "Company Info"}`}
                </div>
                <div>
                  {isComplete ? "All onboarding steps are complete." : `${completedCount} of ${STEPS.length} steps completed`}
                </div>
              </div>
            </div>
          </div>
        </section>

        {isComplete ? (
          <section className="rounded-[28px] border-2 border-black bg-[#DCFCE7] p-6 shadow-[8px_8px_0_#000] md:p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.22em] text-white">
                  <LuCheck size={14} />
                  Onboarding complete
                </div>
                <h2 className="mt-4 text-3xl font-black md:text-4xl">Pravaha is ready for the next conversation.</h2>
                <p className="mt-3 max-w-2xl text-sm font-medium leading-6 text-slate-700">
                  Your company profile, docs, test chat, and proposal link are in place. Use the dashboard to review engagement, calls, and CRM activity.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                {proposalId ? (
                  <Link
                    href={`/proposal/${proposalId}`}
                    className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-black px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000]"
                  >
                    Open proposal
                  </Link>
                ) : null}
                <button
                  type="button"
                  onClick={skipSetup}
                  className="rounded-2xl border-2 border-black bg-white px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                >
                  Go to dashboard
                </button>
              </div>
            </div>
          </section>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[280px_1fr]">
          <aside className="rounded-[28px] border-2 border-black bg-white p-4 shadow-[8px_8px_0_#000]">
            <div className="space-y-3">
              {STEPS.map((item, index) => {
                const isDone = completed.includes(item.id);
                const isActive = activeStep === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setActiveStep(item.id)}
                    className={`w-full rounded-2xl border-2 border-black px-4 py-3 text-left shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px] ${
                      isActive ? "bg-[#E0F2FE]" : isDone ? "bg-[#DCFCE7]" : "bg-white"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 rounded-full border-2 border-black p-1 ${isDone ? "bg-[#DCFCE7]" : "bg-[#FFF7ED]"}`}>
                        {isDone ? <LuCheck size={14} /> : <LuCircleDot size={14} />}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">
                          Step {index + 1} of {STEPS.length}
                        </div>
                        <div className="mt-1 flex items-center gap-2">
                          <div className="text-sm font-black">{item.title}</div>
                          {isDone ? (
                            <span className="rounded-full border-2 border-black bg-white px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]">
                              Done
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-1 text-xs font-medium leading-5 text-slate-600">{item.description}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          <div className="space-y-6">
            {activeStep === "company_info" && (
              <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[8px_8px_0_#000]">
                <h2 className="text-2xl font-black">Company info</h2>
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Company name</span>
                    <input
                      value={companyName}
                      onChange={(event) => setCompanyName(event.target.value)}
                      className="w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                      placeholder="Acme Sales"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Industry</span>
                    <input
                      value={industry}
                      onChange={(event) => setIndustry(event.target.value)}
                      className="w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                      placeholder="SaaS, medtech, fintech..."
                    />
                  </label>
                  <label className="space-y-2 md:col-span-2">
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Company description</span>
                    <textarea
                      value={companyDescription}
                      onChange={(event) => setCompanyDescription(event.target.value)}
                      rows={5}
                      className="w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                      placeholder="Describe what your company does and who buys from you."
                    />
                  </label>
                  <div className="space-y-2 md:col-span-2">
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Target personas</span>
                    <div className="flex flex-wrap gap-2">
                      {PERSONA_OPTIONS.map((persona) => {
                        const active = targetPersonas.includes(persona);
                        return (
                          <button
                            key={persona}
                            type="button"
                            onClick={() => togglePersona(persona)}
                            className={`rounded-full border-2 border-black px-4 py-2 text-xs font-black shadow-[3px_3px_0_#000] ${
                              active ? "bg-[#A855F7] text-white" : "bg-[#FFFDF7] text-slate-800"
                            }`}
                          >
                            {persona}
                          </button>
                        );
                      })}
                    </div>
                    <p className="text-xs font-medium text-slate-600">
                      Select the personas this setup should speak to. You can change these later.
                    </p>
                  </div>
                  <label className="space-y-2">
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Website</span>
                    <input
                      value={website}
                      onChange={(event) => setWebsite(event.target.value)}
                      className="w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                      placeholder="https://yourcompany.com"
                    />
                  </label>
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      persistStep("company_info", {
                        company_name: companyName,
                        company_description: companyDescription,
                        industry,
                        website,
                        target_personas: targetPersonas,
                      })
                    }
                    disabled={saving}
                    className="rounded-2xl border-2 border-black bg-black px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000] disabled:opacity-70"
                  >
                    {saving ? "Saving..." : "Save company info"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveStep("docs_uploaded")}
                    className="rounded-2xl border-2 border-black bg-[#FDE68A] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                  >
                    Continue
                  </button>
                </div>
              </section>
            )}

            {activeStep === "docs_uploaded" && (
              <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[8px_8px_0_#000]">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h2 className="text-2xl font-black">Upload docs</h2>
                    <p className="mt-1 text-sm font-medium text-slate-600">
                      Upload the PDFs Pravaha should learn from now, then run ingestion in the next step.
                    </p>
                  </div>
                  <div className="rounded-2xl border-2 border-black bg-[#DCFCE7] px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000]">
                    {selectedDocs.length ? `${selectedDocs.length} file(s) uploaded` : "No docs uploaded yet"}
                  </div>
                </div>

                <label className="mt-6 flex cursor-pointer flex-col items-center justify-center rounded-[28px] border-2 border-dashed border-black bg-[#FFFDF7] px-6 py-10 text-center shadow-[6px_6px_0_#000]">
                  <LuFileUp size={34} />
                  <span className="mt-4 text-lg font-black">Click to browse PDF documents</span>
                  <span className="mt-2 text-sm font-medium text-slate-600">Upload decks, pricing sheets, and proposal source material. Uploaded file names are carried into ingestion next.</span>
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    className="hidden"
                    onChange={(event) => handleDocsSelection(event.target.files)}
                  />
                </label>

                {selectedDocs.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {selectedDocs.map((doc) => (
                      <span key={doc} className="rounded-full border-2 border-black bg-[#E0F2FE] px-3 py-2 text-xs font-black shadow-[3px_3px_0_#000]">
                        {doc}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      persistStep("docs_uploaded", {
                        uploaded_docs: selectedDocs,
                      })
                    }
                    className="rounded-2xl border-2 border-black bg-black px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000]"
                  >
                    Save uploaded docs
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveStep("ai_trained")}
                    className="rounded-2xl border-2 border-black bg-[#FDE68A] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                  >
                    Continue
                  </button>
                </div>
              </section>
            )}

            {activeStep === "ai_trained" && (
              <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[8px_8px_0_#000]">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h2 className="text-2xl font-black">Train AI</h2>
                    <p className="mt-1 text-sm font-medium text-slate-600">
                      Trigger ingestion after the docs are staged. The backend will process PDFs and update the document index.
                    </p>
                  </div>
                  <div className="rounded-2xl border-2 border-black bg-[#FCE7F3] px-4 py-3 text-sm font-black shadow-[4px_4px_0_#000]">
                    Training runs once per setup flow
                  </div>
                </div>
                <div className="mt-6 grid gap-4 md:grid-cols-3">
                  {["Load PDFs", "Split text", "Create embeddings"].map((item) => (
                    <div key={item} className="rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-4 text-sm font-black shadow-[4px_4px_0_#000]">
                      {item}
                    </div>
                  ))}
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={trainAi}
                    disabled={training}
                    className="rounded-2xl border-2 border-black bg-[#22C55E] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000] disabled:opacity-70"
                  >
                    {training ? "Training..." : "Start ingestion"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveStep("test_chat")}
                    className="rounded-2xl border-2 border-black bg-[#FDE68A] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                  >
                    Continue
                  </button>
                </div>
              </section>
            )}

            {activeStep === "test_chat" && (
              <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[8px_8px_0_#000]">
                <h2 className="text-2xl font-black">Test chat</h2>
                <p className="mt-1 text-sm font-medium text-slate-600">
                  Ask a sample question and check whether the assistant answers using your company context.
                </p>

                <div className="mt-5 flex flex-wrap gap-2">
                  {suggestions.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setTestQuestion(item)}
                      className="rounded-full border-2 border-black bg-[#E0F2FE] px-3 py-2 text-xs font-black shadow-[3px_3px_0_#000]"
                    >
                      {item}
                    </button>
                  ))}
                </div>

                <textarea
                  value={testQuestion}
                  onChange={(event) => setTestQuestion(event.target.value)}
                  rows={4}
                  className="mt-5 w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                  placeholder="What does my company do?"
                />

                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => sendTestChat()}
                    disabled={sendingChat}
                    className="rounded-2xl border-2 border-black bg-black px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000] disabled:opacity-70"
                  >
                    {sendingChat ? "Thinking..." : "Ask Pravaha"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveStep("share_proposal")}
                    className="rounded-2xl border-2 border-black bg-[#FDE68A] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000]"
                  >
                    Continue
                  </button>
                </div>

                <div className="mt-6 space-y-3">
                  {chatHistory.length ? (
                    chatHistory.map((message, index) => (
                      <div
                        key={`${message.role}-${index}`}
                        className={`max-w-4xl rounded-2xl border-2 border-black px-4 py-3 shadow-[4px_4px_0_#000] ${
                          message.role === "user" ? "ml-auto bg-[#FDE68A]" : "bg-white"
                        }`}
                      >
                        <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">
                          {message.role === "user" ? "You" : "Pravaha"}
                        </div>
                        <div className="mt-1 text-sm font-medium leading-6">{message.content}</div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border-2 border-dashed border-black bg-[#FFFDF7] px-4 py-5 text-sm font-medium text-slate-600">
                      No test conversation yet.
                    </div>
                  )}
                </div>
              </section>
            )}

            {activeStep === "share_proposal" && (
              <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[8px_8px_0_#000]">
                <h2 className="text-2xl font-black">Share proposal</h2>
                <p className="mt-1 text-sm font-medium text-slate-600">
                  Generate the first shareable proposal link and open the buyer-facing experience.
                </p>

                <label className="mt-6 block space-y-2">
                  <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Team share list</span>
                  <textarea
                    value={inviteTeamEmails}
                    onChange={(event) => setInviteTeamEmails(event.target.value)}
                    rows={3}
                    className="w-full rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 text-sm font-medium shadow-[4px_4px_0_#000] outline-none"
                    placeholder="anna@company.com, sam@company.com"
                  />
                  <p className="text-xs font-medium text-slate-600">
                    Optional. Save comma-separated teammate emails with this setup so you have a ready share list after the proposal is created.
                  </p>
                </label>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={shareProposal}
                    disabled={sharing}
                    className="rounded-2xl border-2 border-black bg-[#A855F7] px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000] disabled:opacity-70"
                  >
                    {sharing ? "Generating..." : "Generate proposal link"}
                  </button>
                  <button
                    type="button"
                    onClick={copyLink}
                    disabled={!shareLink}
                    className="rounded-2xl border-2 border-black bg-[#DCFCE7] px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000] disabled:opacity-70"
                  >
                    <LuCopy className="mr-2 inline-block" size={16} />
                    Copy link
                  </button>
                  {proposalId && (
                    <Link
                      href={`/proposal/${proposalId}`}
                      className="rounded-2xl border-2 border-black bg-black px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_#000]"
                    >
                      Open public proposal
                    </Link>
                  )}
                </div>

                {shareLink && (
                  <div className="mt-6 rounded-[24px] border-2 border-black bg-[#FFF7ED] p-5 shadow-[6px_6px_0_#000]">
                    <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Shareable link</div>
                    <div className="mt-2 break-all text-sm font-bold">{shareLink}</div>
                    <div className="mt-4 flex flex-wrap gap-3">
                      {proposalId ? (
                        <Link
                          href={`/proposal/${proposalId}`}
                          className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-black px-4 py-2 text-sm font-black text-white shadow-[4px_4px_0_#000]"
                        >
                          Open public proposal
                        </Link>
                      ) : null}
                      <button
                        type="button"
                        onClick={skipSetup}
                        className="rounded-2xl border-2 border-black bg-white px-4 py-2 text-sm font-black shadow-[4px_4px_0_#000]"
                      >
                        Finish setup
                      </button>
                    </div>
                  </div>
                )}

                <div className="mt-6 grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border-2 border-black bg-[#E0F2FE] p-4 shadow-[4px_4px_0_#000]">
                    <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Lead capture</div>
                    <div className="mt-2 text-sm font-semibold">Buyer enters name and email before chatting.</div>
                  </div>
                  <div className="rounded-2xl border-2 border-black bg-[#FCE7F3] p-4 shadow-[4px_4px_0_#000]">
                    <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Engagement</div>
                    <div className="mt-2 text-sm font-semibold">Views and questions are tracked per proposal.</div>
                  </div>
                  <div className="rounded-2xl border-2 border-black bg-[#DCFCE7] p-4 shadow-[4px_4px_0_#000]">
                    <div className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Next steps</div>
                    <div className="mt-2 text-sm font-semibold">Admins can follow up with CRM notes and automations.</div>
                  </div>
                </div>
              </section>
            )}
          </div>
        </section>

        <div className="flex flex-wrap gap-3 pb-4">
          {STEPS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveStep(item.id)}
              className={`rounded-full border-2 border-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] shadow-[3px_3px_0_#000] ${
                activeStep === item.id ? "bg-black text-white" : "bg-white text-slate-700"
              }`}
            >
              {item.title}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
