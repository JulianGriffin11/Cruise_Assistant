import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  FileText,
  Plus,
  RefreshCw,
  Upload,
} from "lucide-react";

import {
  createCruise,
  listCruises,
  listDocuments,
  retryDocument,
  uploadDocument,
  type Cruise,
  type Document,
} from "@/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

type CruiseForm = {
  name: string;
  year: string;
  startDate: string;
  endDate: string;
};

const emptyForm: CruiseForm = {
  name: "",
  year: String(new Date().getFullYear()),
  startDate: "",
  endDate: "",
};

export default function Library({ onOpenChat }: { onOpenChat: () => void }) {
  const [cruises, setCruises] = useState<Cruise[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadCruiseId, setUploadCruiseId] = useState<string | null>(null);
  const [uploadingCruiseId, setUploadingCruiseId] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listCruises(), listDocuments()])
      .then(([nextCruises, nextDocuments]) => {
        if (active) {
          setCruises(nextCruises);
          setDocuments(nextDocuments);
        }
      })
      .catch((caught: unknown) => {
        if (active) setError(getErrorMessage(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!documents.some((document) => document.status === "processing")) return;
    const interval = window.setInterval(() => {
      listDocuments()
        .then(setDocuments)
        .catch((caught: unknown) => setError(getErrorMessage(caught)));
    }, 2500);
    return () => window.clearInterval(interval);
  }, [documents]);

  function chooseFile(cruiseId: string) {
    setUploadCruiseId(cruiseId);
    fileInputRef.current?.click();
  }

  async function handleFile(file: File | undefined) {
    const cruiseId = uploadCruiseId;
    if (!file || !cruiseId) return;
    setError("");
    setUploadingCruiseId(cruiseId);
    try {
      const document = await uploadDocument(cruiseId, file);
      setDocuments((current) => [
        document,
        ...current.filter((item) => item.id !== document.id),
      ]);
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setUploadingCruiseId(null);
      setUploadCruiseId(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleRetry(documentId: string) {
    setError("");
    setRetryingId(documentId);
    try {
      const document = await retryDocument(documentId);
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? document : item)),
      );
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <>
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10 lg:px-10">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              Source library
            </p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Cruise itineraries
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
              Add a cruise and upload its itinerary PDF. Once processing is
              complete, the assistant can answer questions from it.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="lg" onClick={onOpenChat}>
              Ask a question
              <ArrowRight data-icon="inline-end" />
            </Button>
            <Button size="lg" onClick={() => setCreateOpen(true)}>
              <Plus data-icon="inline-start" />
              New cruise
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="mt-6">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />

        <div className="mt-8">
          {loading ? (
            <LibrarySkeleton />
          ) : cruises.length === 0 ? (
            <EmptyLibrary onCreate={() => setCreateOpen(true)} />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {cruises.map((cruise) => (
                <CruiseCard
                  key={cruise.id}
                  cruise={cruise}
                  documents={documents.filter(
                    (document) => document.cruise_id === cruise.id,
                  )}
                  uploading={uploadingCruiseId === cruise.id}
                  retryingId={retryingId}
                  onUpload={() => chooseFile(cruise.id)}
                  onRetry={handleRetry}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <CreateCruiseDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(cruise) => setCruises((current) => [cruise, ...current])}
      />
    </>
  );
}

function CruiseCard({
  cruise,
  documents,
  uploading,
  retryingId,
  onUpload,
  onRetry,
}: {
  cruise: Cruise;
  documents: Document[];
  uploading: boolean;
  retryingId: string | null;
  onUpload: () => void;
  onRetry: (documentId: string) => Promise<void>;
}) {
  return (
    <Card className="min-h-64">
      <CardHeader>
        <CardTitle className="pr-4 text-lg">{cruise.name}</CardTitle>
        <CardDescription className="flex items-center gap-1.5">
          <CalendarDays className="size-3.5" aria-hidden="true" />
          {dateLabel(cruise)}
        </CardDescription>
        <CardAction>
          <Button
            variant="outline"
            size="sm"
            disabled={uploading}
            onClick={onUpload}
          >
            <Upload data-icon="inline-start" />
            {uploading ? "Uploading…" : "Upload PDF"}
          </Button>
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent className="flex flex-1 flex-col">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Documents
        </p>
        {documents.length === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed px-4 py-7 text-center">
            <div>
              <FileText className="mx-auto size-5 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">No itinerary uploaded</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Upload a PDF to make this cruise searchable.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                retrying={retryingId === document.id}
                onRetry={() => void onRetry(document.id)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DocumentRow({
  document,
  retrying,
  onRetry,
}: {
  document: Document;
  retrying: boolean;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-lg border bg-background px-3 py-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
          <FileText className="size-4 text-muted-foreground" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="truncate text-sm font-medium">{document.filename}</p>
            <StatusBadge status={document.status} />
          </div>
          {document.status === "processing" ? (
            <div className="mt-2 space-y-1.5">
              <Skeleton className="h-1.5 w-full" />
              <Skeleton className="h-1.5 w-2/3" />
            </div>
          ) : document.status === "failed" ? (
            <div className="mt-1.5 flex items-end justify-between gap-3">
              <p className="line-clamp-2 text-xs leading-5 text-destructive">
                {document.error_message ?? "Processing failed."}
              </p>
              <Button
                variant="ghost"
                size="xs"
                disabled={retrying}
                onClick={onRetry}
              >
                <RefreshCw className={retrying ? "animate-spin" : ""} />
                Retry
              </Button>
            </div>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">
              {document.page_count
                ? `${document.page_count} pages indexed`
                : "Ready to search"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Document["status"] }) {
  if (status === "processing") {
    return <Badge className="bg-primary/10 text-primary">Processing</Badge>;
  }
  if (status === "failed") {
    return <Badge variant="destructive">Failed</Badge>;
  }
  return <Badge variant="outline">Ready</Badge>;
}

function EmptyLibrary({ onCreate }: { onCreate: () => void }) {
  return (
    <Card className="items-center px-6 py-14 text-center">
      <span className="flex size-11 items-center justify-center rounded-xl bg-accent text-primary">
        <FileText className="size-5" />
      </span>
      <div>
        <h2 className="font-semibold">Build your source library</h2>
        <p className="mx-auto mt-1 max-w-sm text-sm leading-6 text-muted-foreground">
          Create your first cruise, then upload an itinerary PDF to start asking
          grounded questions.
        </p>
      </div>
      <Button onClick={onCreate}>
        <Plus />
        Create a cruise
      </Button>
    </Card>
  );
}

function LibrarySkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-2" aria-label="Loading cruises">
      {[0, 1].map((index) => (
        <Card key={index} className="min-h-64">
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-28" />
          </CardHeader>
          <Separator />
          <CardContent className="space-y-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-16 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function CreateCruiseDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (cruise: Cruise) => void;
}) {
  const [form, setForm] = useState<CruiseForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const cruise = await createCruise({
        name: form.name.trim(),
        year: Number(form.year),
        start_date: form.startDate || null,
        end_date: form.endDate || null,
      });
      onCreated(cruise);
      onOpenChange(false);
      setForm(emptyForm);
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={(event) => void handleSubmit(event)}>
          <DialogHeader>
            <DialogTitle>New cruise</DialogTitle>
            <DialogDescription>
              Add the cruise details first. You can upload its itinerary next.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-5">
            <label className="grid gap-1.5 text-sm font-medium">
              Cruise name
              <Input
                required
                autoFocus
                placeholder="Africa Expedition"
                value={form.name}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
              />
            </label>
            <label className="grid gap-1.5 text-sm font-medium">
              Year
              <Input
                required
                type="number"
                min="2000"
                max="2100"
                value={form.year}
                onChange={(event) =>
                  setForm({ ...form, year: event.target.value })
                }
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-1.5 text-sm font-medium">
                Start date
                <Input
                  type="date"
                  value={form.startDate}
                  onChange={(event) =>
                    setForm({ ...form, startDate: event.target.value })
                  }
                />
              </label>
              <label className="grid gap-1.5 text-sm font-medium">
                End date
                <Input
                  type="date"
                  min={form.startDate || undefined}
                  value={form.endDate}
                  onChange={(event) =>
                    setForm({ ...form, endDate: event.target.value })
                  }
                />
              </label>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !form.name.trim()}>
              {saving ? "Creating…" : "Create cruise"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function dateLabel(cruise: Cruise): string {
  if (!cruise.start_date || !cruise.end_date) return String(cruise.year);
  const formatter = new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  });
  return `${formatter.format(new Date(`${cruise.start_date}T00:00:00`))} – ${formatter.format(new Date(`${cruise.end_date}T00:00:00`))}, ${cruise.year}`;
}

function getErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "Something went wrong.";
}
