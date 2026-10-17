import { type FormEvent, useState } from "react";

import { uploadDocument } from "./api";
import type { IngestResult } from "./types";

interface Props {
  groups: string[];
  demoRolesEnabled: boolean;
  onUploaded: () => void;
  onBusyChange: (busy: boolean) => void;
}

export default function DocumentUpload({ groups, demoRolesEnabled, onUploaded, onBusyChange }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [allowedGroups, setAllowedGroups] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<IngestResult | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setResult(null);
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("The PDF must be 10 MiB or smaller.");
      return;
    }
    if (sourceUrl.trim() && !/^https?:\/\//i.test(sourceUrl.trim())) {
      setError("Use an HTTP or HTTPS source URL.");
      return;
    }
    if (visibility === "restricted" && !allowedGroups.split(",").some((group) => group.trim())) {
      setError("Enter at least one group for a restricted document.");
      return;
    }
    setBusy(true);
    onBusyChange(true);
    try {
      const response = await uploadDocument({
        file, title: title.trim(), sourceUrl: sourceUrl.trim(), visibility,
        allowedGroups: visibility === "restricted" ? allowedGroups : "",
      }, groups);
      setResult(response);
      onUploaded();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The document could not be added.");
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  }

  return (
    <section className="upload-panel" id="document-upload" aria-labelledby="upload-title">
      <h2 id="upload-title">Add a document</h2>
      <p>Upload a text PDF to make it searchable. Scanned or encrypted PDFs are not supported. Maximum size: 10 MiB.</p>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <label htmlFor="document-file">PDF file</label>
          <input id="document-file" type="file" accept=".pdf,application/pdf" required onChange={(event) => {
            const selected = event.target.files?.[0] ?? null;
            setFile(selected);
            if (selected) setTitle(selected.name.replace(/\.pdf$/i, "").replace(/[_-]/g, " "));
            setError("");
            setResult(null);
          }} />
          <label htmlFor="document-title">Document title</label>
          <input id="document-title" value={title} required maxLength={500} onChange={(event) => setTitle(event.target.value)} />
          <label htmlFor="document-url">Source URL (optional)</label>
          <input id="document-url" type="url" value={sourceUrl} maxLength={2000} placeholder="https://university.example/document.pdf" onChange={(event) => setSourceUrl(event.target.value)} />
          <p className="upload-hint">Add the original document link so readers can open it from search results. Keep a copy of your PDF.</p>
          {demoRolesEnabled && <>
            <label htmlFor="document-access">Who can retrieve this document?</label>
            <select id="document-access" value={visibility} onChange={(event) => setVisibility(event.target.value)}>
              <option value="public">Everyone (public)</option>
              <option value="restricted">Selected groups</option>
            </select>
            {visibility === "restricted" && <>
              <label htmlFor="document-groups">Allowed groups</label>
              <input id="document-groups" value={allowedGroups} required placeholder="students, staff" onChange={(event) => setAllowedGroups(event.target.value)} />
              <p className="upload-hint">Separate groups with commas. The simulated role controls access during this local demo.</p>
            </>}
          </>}
          <button className="upload-submit" type="submit" disabled={!file || !title.trim()}>{busy ? "Adding document…" : "Upload PDF"}</button>
        </fieldset>
      </form>
      {busy && <p role="status">Adding your document. This can take a minute on first use.</p>}
      {error && <p className="upload-error" role="alert">{error}</p>}
      {result && <p className="upload-success" role="status">
        {result.duplicate ? "This PDF is already indexed." : "Document added."} {result.chunks_created} searchable {result.chunks_created === 1 ? "passage" : "passages"}. You can search it now.
      </p>}
    </section>
  );
}
