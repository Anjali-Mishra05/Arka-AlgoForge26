"use client";

import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import DOMPurify from "dompurify";
import { ControlledBoard, moveCard, Card, KanbanBoard, OnDragEndNotification } from "@caldwell619/react-kanban";
import "@caldwell619/react-kanban/dist/styles.css";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { LuCopy, LuExternalLink, LuRefreshCw, LuUpload, LuWand2 } from "react-icons/lu";
import { getAuthHeaders } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type PreviewState = {
  fileName: string;
  html: string;
};

// Use getAuthHeaders from lib/api so the Bearer token is always included
const authHeaders = () => getAuthHeaders();

const sanitizeHtml = (html: string) => DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });

const buildBoard = (allPdfs: string[], selectedPdfs: string[]): KanbanBoard<Card> => ({
  columns: [
    {
      id: 0,
      title: "All Files",
      cards: allPdfs
        .filter((file) => !selectedPdfs.includes(file))
        .map((file, index) => ({
          id: `all-${index}-${file}`,
          title: file,
          description: "Move to Selected PDFs to prepare for proposal generation",
        })),
    },
    {
      id: 1,
      title: "Selected PDFs",
      cards: selectedPdfs.map((file, index) => ({
        id: `selected-${index}-${file}`,
        title: file,
        description: "Included in the next ingest and proposal run",
      })),
    },
    {
      id: 2,
      title: "View Proposals",
      cards: [
        {
          id: "proposal-preview",
          title: "proposal.html",
          description: "Drop an HTML proposal here to preview it below",
        },
      ],
    },
  ],
});

export default function PDF() {
  const [newPDFs, setNewPDFs] = useState<File[]>([]);
  const [allPdfs, setAllPdfs] = useState<string[]>([]);
  const [selectedPdfs, setSelectedPdfs] = useState<string[]>([]);
  const [board, setBoard] = useState<KanbanBoard<Card>>(buildBoard([], []));
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [generatedProposalId, setGeneratedProposalId] = useState<string | null>(null);
  const [publicProposalUrl, setPublicProposalUrl] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setNewPDFs((prev) => [...prev, ...Array.from(e.target.files || [])]);
  };

  const refreshDocuments = useCallback(async () => {
    try {
      const [allDocsResponse, selectedDocsResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/admin/get_all_docs`, { headers: authHeaders() }),
        axios.get(`${API_BASE_URL}/admin/get_selected_docs`, { headers: authHeaders() }),
      ]);

      setAllPdfs(Array.isArray(allDocsResponse.data) ? allDocsResponse.data.map((item: any) => item.filename ?? item) : []);
      setSelectedPdfs(Array.isArray(selectedDocsResponse.data) ? selectedDocsResponse.data.map((item: any) => item.filename ?? item) : []);
    } catch (error: any) {
      if (error?.response?.status === 401) {
        toast.error("Session expired. Redirecting to sign in.");
        router.push("/sign-in");
      } else {
        toast.error("Unable to load document lists.");
      }
    }
  }, [router]);

  const loadHtmlPreview = async (fileName: string) => {
    if (!fileName) return;
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/get_html_from_file?file_name=${encodeURIComponent(fileName)}`, {
        headers: authHeaders(),
        responseType: "text",
      });
      const rawHtml = typeof response.data === "string" ? response.data : String(response.data ?? "");
      setPreview({ fileName, html: sanitizeHtml(rawHtml) });
    } catch {
      toast.error(`Could not load ${fileName}`);
    }
  };

  const uploadToCloud = async () => {
    if (!newPDFs.length) {
      toast.error("No PDF files selected.");
      return;
    }

    setBusy(true);
    try {
      for (const pdfFile of newPDFs) {
        const formData = new FormData();
        formData.append("pdf_file", pdfFile, pdfFile.name);
        await axios.post(`${API_BASE_URL}/admin/upload_pdf`, formData, {
          headers: {
            ...authHeaders(),
            "Content-Type": "multipart/form-data",
          },
        });
      }

      toast.success("Uploads completed.");
      setNewPDFs([]);
      await refreshDocuments();
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Upload failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  const updateSelectedOnCloud = async (files: string[]) => {
    try {
      await axios.post(`${API_BASE_URL}/admin/update_selected_docs`, files, {
        headers: {
          ...authHeaders(),
          "Content-Type": "application/json",
        },
      });
    } catch {
      toast.error("Could not sync selected documents.");
    }
  };

  const ingest = async () => {
    setBusy(true);
    try {
      await axios.get(`${API_BASE_URL}/admin/ingest`, { headers: authHeaders() });
      toast.success("Documents ingested.");
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Ingest failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  const generateProposal = async () => {
    setBusy(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/generate_proposal`, { headers: authHeaders() });
      const proposalId = response.data?.proposal_id;
      if (proposalId) {
        setGeneratedProposalId(proposalId);
        setPublicProposalUrl(`${window.location.origin}/proposal/${proposalId}`);
        toast.success("Proposal generated.");
        await loadHtmlPreview("proposal.html");
      } else {
        toast.success("Proposal generated.");
      }
      await refreshDocuments();
    } catch (error: any) {
      if (error?.response?.status === 401) {
        router.push("/sign-in");
      } else {
        toast.error("Proposal generation failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  const copyProposalLink = async () => {
    if (!publicProposalUrl) return;
    await navigator.clipboard.writeText(publicProposalUrl);
    toast.success("Public proposal link copied.");
  };

  const handleCardMove: OnDragEndNotification<Card> = (card, source, destination) => {
    if (!destination || source?.fromColumnId === destination?.toColumnId) return;

    if (destination.toColumnId === 2) {
      if (card.title?.endsWith(".html")) {
        loadHtmlPreview(card.title);
      } else {
        toast.error("Only HTML proposal files can be previewed.");
      }
      return;
    }

    if (!card.title?.endsWith(".pdf")) {
      toast.error(`Only PDF files can be selected. ${card.title} is not a PDF.`);
      return;
    }

    if (destination.toColumnId === 1) {
      const nextSelected = Array.from(new Set([...selectedPdfs, card.title]));
      setSelectedPdfs(nextSelected);
      updateSelectedOnCloud(nextSelected);
      return;
    }

    if (destination.toColumnId === 0) {
      const nextSelected = selectedPdfs.filter((file) => file !== card.title);
      setSelectedPdfs(nextSelected);
      updateSelectedOnCloud(nextSelected);
      return;
    }
  };

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  useEffect(() => {
    setBoard(buildBoard(allPdfs, selectedPdfs));
  }, [allPdfs, selectedPdfs]);

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border-2 border-black bg-white p-6 shadow-[8px_8px_0px_#000]">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Document Pipeline</p>
            <h1 className="mt-2 text-3xl font-black text-slate-950">PDF vault and proposal generator</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium text-slate-600">
              Upload PDFs, select the ones to ingest, preview generated proposal HTML safely, and open the public buyer link for the current proposal.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={refreshDocuments}
              className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-slate-100 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px]"
            >
              <LuRefreshCw size={14} />
              Refresh
            </button>
            <button
              onClick={ingest}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-emerald-300 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <LuWand2 size={14} />
              Ingest
            </button>
            <button
              onClick={generateProposal}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-amber-300 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <LuExternalLink size={14} />
              Generate Proposal
            </button>
            {generatedProposalId && (
              <button
                onClick={copyProposalLink}
                className="inline-flex items-center gap-2 rounded-xl border-2 border-black bg-cyan-200 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px]"
              >
                <LuCopy size={14} />
                Copy Public Link
              </button>
            )}
          </div>
        </div>
        {generatedProposalId && (
          <div className="mt-4 rounded-xl border-2 border-black bg-slate-950 px-4 py-3 text-sm font-medium text-white">
            Public proposal: <span className="font-black">{publicProposalUrl}</span>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border-2 border-black bg-white p-5 shadow-[8px_8px_0px_#000]">
            <Label htmlFor="file-upload" className="block cursor-pointer rounded-2xl border-2 border-dashed border-black bg-slate-950 p-6 text-center text-white">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border-2 border-white bg-white text-black">
                <LuUpload size={20} />
              </div>
              <p className="text-lg font-black">Drag and drop PDFs or click to browse</p>
              <p className="mt-2 text-sm text-slate-300">
                {newPDFs.length ? newPDFs.map((file) => file.name).join(", ") : "Select the documents you want to upload to the local backend."}
              </p>
            </Label>
            <Input id="file-upload" className="hidden" type="file" accept="application/pdf" multiple onChange={handleFileChange} />
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={uploadToCloud}
                disabled={busy}
                className="rounded-xl border-2 border-black bg-black px-4 py-2 text-sm font-black text-white shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Upload to backend
              </button>
              <button
                onClick={() => setNewPDFs([])}
                className="rounded-xl border-2 border-black bg-slate-100 px-4 py-2 text-sm font-black shadow-[4px_4px_0px_#000] transition-transform hover:translate-x-[2px] hover:translate-y-[2px]"
              >
                Clear selection
              </button>
            </div>
          </div>

          <div className="rounded-2xl border-2 border-black bg-white p-5 shadow-[8px_8px_0px_#000]">
            <div className="mb-4">
              <h2 className="text-xl font-black text-slate-950">Document board</h2>
              <p className="text-sm font-medium text-slate-600">Move PDFs into selected, then generate the proposal and preview the HTML here.</p>
            </div>
            <ControlledBoard onCardDragEnd={handleCardMove}>{board}</ControlledBoard>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-2xl border-2 border-black bg-white p-5 shadow-[8px_8px_0px_#000]">
            <h2 className="text-lg font-black text-slate-950">Status</h2>
            <div className="mt-4 space-y-3 text-sm font-medium text-slate-700">
              <p>All files: {allPdfs.length}</p>
              <p>Selected PDFs: {selectedPdfs.length}</p>
              <p>Generated proposal: {generatedProposalId ? "Ready" : "Not generated yet"}</p>
            </div>
          </div>

          <div className="rounded-2xl border-2 border-black bg-white p-5 shadow-[8px_8px_0px_#000]">
            <h2 className="text-lg font-black text-slate-950">Proposal preview</h2>
            <p className="mt-2 text-sm font-medium text-slate-600">
              HTML is sanitized before rendering to keep the local demo safe.
            </p>
            {preview ? (
              <div className="mt-4 overflow-hidden rounded-xl border-2 border-black bg-white">
                <div className="border-b-2 border-black bg-amber-200 px-4 py-2 text-xs font-black uppercase tracking-[0.3em] text-black">
                  {preview.fileName}
                </div>
                <div className="max-h-[520px] overflow-auto p-4 text-sm text-slate-900" dangerouslySetInnerHTML={{ __html: sanitizeHtml(preview.html) }} />
              </div>
            ) : (
              <div className="mt-4 rounded-xl border-2 border-dashed border-black bg-slate-50 p-6 text-sm font-medium text-slate-500">
                Drop `proposal.html` into the preview column or generate a proposal to see the rendered output.
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
