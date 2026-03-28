"use client";

import Link from "next/link";
import { LuArrowRight, LuCheck, LuPhoneCall, LuBot, LuBadgeDollarSign, LuShieldCheck, LuWorkflow, LuHome } from "react-icons/lu";
import { PravahaLogo } from "@/components/PravahaLogo";

const PLANS = [
  {
    name: "Starter",
    price: "$49",
    accent: "#FDE68A",
    subtitle: "For early sales teams proving AI-assisted outreach.",
    features: [
      "Role-based AI chat",
      "Proposal generation and buyer chat",
      "Bulk email campaigns",
      "Basic analytics dashboard",
      "1 workspace, 10 active proposals",
    ],
  },
  {
    name: "Growth",
    price: "$99",
    accent: "#C4B5FD",
    subtitle: "For teams that want calls, coaching, CRM sync, and automations.",
    featured: true,
    features: [
      "Everything in Starter",
      "AI agent calls + live coaching",
      "HubSpot sync",
      "Proposal engagement intelligence",
      "Next-best-action recommendations",
      "Manager daily brief",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    accent: "#86EFAC",
    subtitle: "For larger orgs needing compliance, support, and customization.",
    features: [
      "Everything in Growth",
      "Custom integrations",
      "White-label proposal portal",
      "Priority support and onboarding",
      "Advanced automation controls",
      "Security and audit workflows",
    ],
  },
];

const COMPARISON_ROWS = [
  ["Role-based AI chat", true, true, true],
  ["Proposal generation and buyer chat", true, true, true],
  ["Bulk email campaigns", true, true, true],
  ["Live sales call coaching", false, true, true],
  ["HubSpot sync", false, true, true],
  ["Next-best-action recommendations", false, true, true],
  ["Manager daily brief", false, true, true],
  ["White-label proposal portal", false, false, true],
  ["Custom integrations", false, false, true],
  ["Advanced automation controls", false, false, true],
];

const FAQ = [
  ["What counts as a call?", "A completed or in-progress agent call session initiated from Pravaha. We do not hide usage behind credits."],
  ["Is HubSpot included?", "Growth includes HubSpot sync. Enterprise covers custom CRM workflows and deeper field mapping."],
  ["Are proposal links public?", "Yes. Buyers can open proposal links without logging in, and every interaction is tracked in the admin dashboard."],
  ["Can automations be reviewed before action?", "Yes. CRM notes, reminders, and proposal suggestions can be reviewed before you apply or send them."],
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[#FAFAF5] bg-[linear-gradient(#E5E5DD_1px,transparent_1px),linear-gradient(90deg,#E5E5DD_1px,transparent_1px)] bg-[size:24px_24px] text-slate-950">
      {/* Navbar */}
      <nav style={{ borderBottom: "2px solid #1A1A1A", backgroundColor: "#FFFFFF", padding: "0 40px", display: "flex", alignItems: "center", justifyContent: "space-between", height: "64px", position: "sticky", top: 0, zIndex: 100 }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", textDecoration: "none", cursor: "pointer" }}>
          <PravahaLogo size="sm" showText={true} />
        </Link>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <Link href="/" style={{ padding: "8px 14px", color: "#1A1A1A", fontWeight: 600, fontSize: "0.875rem", textDecoration: "none", display: "flex", alignItems: "center", gap: "6px" }}>
            <LuHome size={16} /> Home
          </Link>
          <Link href="/sign-in" style={{ padding: "8px 18px", backgroundColor: "#FFFFFF", color: "#1A1A1A", border: "2px solid #1A1A1A", borderRadius: "10px", fontWeight: 700, fontSize: "0.875rem", textDecoration: "none", boxShadow: "3px 3px 0px #1A1A1A", transition: "all 0.1s" }}>
            Sign In
          </Link>
          <Link href="/sign-up" style={{ padding: "8px 18px", backgroundColor: "#6366F1", color: "#FFFFFF", border: "2px solid #1A1A1A", borderRadius: "10px", fontWeight: 700, fontSize: "0.875rem", textDecoration: "none", boxShadow: "3px 3px 0px #1A1A1A", transition: "all 0.1s" }}>
            Get Started
          </Link>
        </div>
      </nav>

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 md:px-8">
        <section className="rounded-[32px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000] md:p-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#FDE68A] px-4 py-2 text-xs font-black uppercase tracking-[0.25em]">
                <LuBadgeDollarSign size={14} />
                No credits. No surprises.
              </div>
              <h1 className="mt-5 text-4xl font-black leading-tight md:text-6xl">
                Transparent pricing for AI sales teams.
              </h1>
              <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-slate-700">
                Pravaha bundles chat, proposals, calls, CRM sync, coaching, and automations into clear plans. No hidden metering.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border-2 border-black bg-[#E0F2FE] p-4 shadow-[4px_4px_0_#000]">
                <div className="text-xs font-black uppercase tracking-[0.2em] text-sky-700">Chat + Proposals</div>
                <div className="mt-2 text-sm font-semibold">Buyer-facing proposal chat built in.</div>
              </div>
              <div className="rounded-2xl border-2 border-black bg-[#FCE7F3] p-4 shadow-[4px_4px_0_#000]">
                <div className="text-xs font-black uppercase tracking-[0.2em] text-pink-700">Calls + Coaching</div>
                <div className="mt-2 text-sm font-semibold">Live objection detection and summaries.</div>
              </div>
              <div className="rounded-2xl border-2 border-black bg-[#DCFCE7] p-4 shadow-[4px_4px_0_#000]">
                <div className="text-xs font-black uppercase tracking-[0.2em] text-emerald-700">CRM + Automation</div>
                <div className="mt-2 text-sm font-semibold">Sync and follow-ups without double entry.</div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[28px] border-2 border-black bg-[#0F172A] p-6 text-white shadow-[10px_10px_0_#000] md:p-8">
            <div className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[#FDE68A] px-4 py-2 text-xs font-black uppercase tracking-[0.22em] text-slate-950">
              <LuBadgeDollarSign size={14} />
              14-day free trial
            </div>
            <h2 className="mt-5 text-3xl font-black leading-tight md:text-4xl">
              Start with the trial, then keep the plan that matches your pipeline.
            </h2>
            <p className="mt-4 max-w-2xl text-sm font-medium leading-7 text-slate-200">
              Try buyer chat, proposal generation, and the dashboard without credits or surprise usage gates. If you outgrow Starter, move to Growth when calls, CRM sync, and automation matter.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 rounded-2xl border-2 border-black bg-[#FDE68A] px-5 py-3 text-sm font-black text-slate-950 shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px]"
              >
                Start free trial
                <LuArrowRight size={16} />
              </Link>
              <Link
                href="/sign-in"
                className="inline-flex items-center gap-2 rounded-2xl border-2 border-white/20 bg-white/10 px-5 py-3 text-sm font-black text-white shadow-[4px_4px_0_rgba(0,0,0,0.35)] transition-transform hover:translate-x-[1px] hover:translate-y-[1px]"
              >
                Sign in
              </Link>
            </div>
          </div>

          <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000] md:p-8">
            <div className="text-xs font-black uppercase tracking-[0.28em] text-slate-500">Trial includes</div>
            <div className="mt-4 grid gap-3">
              {[
                "Buyer-facing proposal links",
                "Role-aware chat and coaching",
                "Dashboard analytics and call insights",
                "CRM sync visibility",
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 shadow-[4px_4px_0_#000]">
                  <LuCheck className="mt-0.5 shrink-0" size={18} />
                  <span className="text-sm font-semibold leading-6">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          {PLANS.map((plan) => (
            <article
              key={plan.name}
              className={`rounded-[28px] border-2 border-black p-6 shadow-[10px_10px_0_#000] ${
                plan.featured ? "bg-[#EEF2FF]" : "bg-white"
              }`}
            >
              <div
                className="inline-flex items-center rounded-full border-2 border-black px-3 py-1 text-xs font-black uppercase tracking-[0.22em]"
                style={{ backgroundColor: plan.accent }}
              >
                {plan.name}
              </div>
              <div className="mt-5 flex items-end gap-2">
                <div className="text-5xl font-black">{plan.price}</div>
                {plan.price !== "Custom" && <div className="pb-1 text-sm font-bold uppercase tracking-[0.18em] text-slate-500">per user / month</div>}
              </div>
              <p className="mt-3 text-sm font-medium leading-6 text-slate-700">{plan.subtitle}</p>

              <div className="mt-6 space-y-3">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-3 rounded-2xl border-2 border-black bg-[#FFFDF7] px-4 py-3 shadow-[4px_4px_0_#000]">
                    <LuCheck className="mt-0.5 shrink-0" size={18} />
                    <span className="text-sm font-semibold leading-6">{feature}</span>
                  </div>
                ))}
              </div>

              <Link
                href="/sign-up"
                className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-black px-5 py-3 text-sm font-black shadow-[4px_4px_0_#000] transition-transform hover:translate-x-[1px] hover:translate-y-[1px] ${
                  plan.featured ? "bg-black text-white" : "bg-white text-black"
                }`}
              >
                Choose {plan.name}
                <LuArrowRight size={16} />
              </Link>
            </article>
          ))}
        </section>

        <section className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000] md:p-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.28em] text-slate-500">Feature comparison</div>
              <h2 className="mt-2 text-3xl font-black">What changes as you move up.</h2>
              <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600">
                Pricing stays simple. The plans differ by how much of the revenue loop you want automated, coached, and synced.
              </p>
            </div>
            <div className="rounded-2xl border-2 border-black bg-[#DCFCE7] px-4 py-3 text-xs font-black uppercase tracking-[0.22em] shadow-[4px_4px_0_#000]">
              No hidden metering
            </div>
          </div>

          <div className="mt-6 overflow-hidden rounded-[24px] border-2 border-black">
            <div className="grid grid-cols-[1.5fr_repeat(3,minmax(0,1fr))] border-b-2 border-black bg-[#FFF7ED] text-[11px] font-black uppercase tracking-[0.22em] text-slate-600">
              <div className="px-4 py-3">Feature</div>
              <div className="px-4 py-3 text-center">Starter</div>
              <div className="px-4 py-3 text-center">Growth</div>
              <div className="px-4 py-3 text-center">Enterprise</div>
            </div>
            <div className="divide-y-2 divide-black">
              {COMPARISON_ROWS.map(([feature, starter, growth, enterprise]) => (
                <div key={String(feature)} className="grid grid-cols-[1.5fr_repeat(3,minmax(0,1fr))] bg-white">
                  <div className="px-4 py-4 text-sm font-bold leading-6">{feature}</div>
                  <div className="flex items-center justify-center px-4 py-4">
                    {starter ? <LuCheck size={18} className="text-emerald-600" /> : <span className="text-sm font-black text-slate-300">-</span>}
                  </div>
                  <div className="flex items-center justify-center px-4 py-4">
                    {growth ? <LuCheck size={18} className="text-emerald-600" /> : <span className="text-sm font-black text-slate-300">-</span>}
                  </div>
                  <div className="flex items-center justify-center px-4 py-4">
                    {enterprise ? <LuCheck size={18} className="text-emerald-600" /> : <span className="text-sm font-black text-slate-300">-</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border-2 border-black bg-[#C4B5FD] p-3 shadow-[4px_4px_0_#000]">
                <LuWorkflow size={24} />
              </div>
              <div>
                <h2 className="text-2xl font-black">What every paid plan includes</h2>
                <p className="text-sm font-medium text-slate-600">The product gets more capable as you go up, but the fundamentals are not artificially withheld.</p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border-2 border-black bg-[#FFF7ED] p-4 shadow-[4px_4px_0_#000]">
                <LuBot size={20} />
                <div className="mt-3 text-sm font-black uppercase tracking-[0.18em] text-slate-500">AI Assistants</div>
                <p className="mt-2 text-sm font-medium leading-6">Role-based AI for buyers, reps, and managers with document-aware responses.</p>
              </div>
              <div className="rounded-2xl border-2 border-black bg-[#ECFCCB] p-4 shadow-[4px_4px_0_#000]">
                <LuPhoneCall size={20} />
                <div className="mt-3 text-sm font-black uppercase tracking-[0.18em] text-slate-500">Sales Workflows</div>
                <p className="mt-2 text-sm font-medium leading-6">Proposal generation, buyer engagement tracking, and outbound workflows stay in one system.</p>
              </div>
              <div className="rounded-2xl border-2 border-black bg-[#FCE7F3] p-4 shadow-[4px_4px_0_#000]">
                <LuShieldCheck size={20} />
                <div className="mt-3 text-sm font-black uppercase tracking-[0.18em] text-slate-500">Auditability</div>
                <p className="mt-2 text-sm font-medium leading-6">Proposal events, CRM syncs, and future agent actions are visible to admins.</p>
              </div>
              <div className="rounded-2xl border-2 border-black bg-[#DBEAFE] p-4 shadow-[4px_4px_0_#000]">
                <LuBadgeDollarSign size={20} />
                <div className="mt-3 text-sm font-black uppercase tracking-[0.18em] text-slate-500">No Hidden Metering</div>
                <p className="mt-2 text-sm font-medium leading-6">Plans are seat-based. Usage guardrails are operational, not surprise billing instruments.</p>
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border-2 border-black bg-white p-6 shadow-[10px_10px_0_#000]">
            <h2 className="text-2xl font-black">FAQ</h2>
            <div className="mt-5 space-y-4">
              {FAQ.map(([question, answer]) => (
                <div key={question} className="rounded-2xl border-2 border-black bg-[#FFFDF7] p-4 shadow-[4px_4px_0_#000]">
                  <div className="text-sm font-black uppercase tracking-[0.18em] text-slate-600">{question}</div>
                  <p className="mt-2 text-sm font-medium leading-6 text-slate-700">{answer}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
