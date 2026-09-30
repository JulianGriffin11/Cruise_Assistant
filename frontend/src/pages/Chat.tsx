import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  AlertCircle,
  ArrowUp,
  BookOpen,
  Bot,
  FileSearch,
  LibraryBig,
  Sparkles,
} from "lucide-react";

import {
  listCruises,
  streamChat,
  type ChatTurn,
  type Citation,
  type Cruise,
} from "@/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type Message = ChatTurn & {
  id: string;
  citations?: Citation[];
  pending?: boolean;
  error?: boolean;
};

const suggestions = [
  "What are the highlights of this itinerary?",
  "Which days include shore excursions?",
  "Draft a guest email with the trip details.",
];

export default function Chat({
  onOpenLibrary,
}: {
  onOpenLibrary: () => void;
}) {
  const [cruises, setCruises] = useState<Cruise[]>([]);
  const [selectedCruiseId, setSelectedCruiseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const [loadingCruises, setLoadingCruises] = useState(true);
  const [cruiseError, setCruiseError] = useState("");
  const [sending, setSending] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    listCruises()
      .then((result) => {
        if (active) setCruises(result);
      })
      .catch((caught: unknown) => {
        if (active) setCruiseError(getErrorMessage(caught));
      })
      .finally(() => {
        if (active) setLoadingCruises(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector(
      '[data-slot="scroll-area-viewport"]',
    );
    viewport?.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const question = message.trim();
    if (!question || sending) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    const assistantId = crypto.randomUUID();
    const history = messages
      .filter((item) => !item.pending && !item.error)
      .map(({ role, content }) => ({ role, content }));

    setMessage("");
    setSending(true);
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);

    try {
      await streamChat(question, selectedCruiseId, history, {
        onToken: (token) => {
          setMessages((current) =>
            updateMessage(current, assistantId, (item) => ({
              ...item,
              content: item.content + token,
            })),
          );
        },
        onCitations: (citations) => {
          setMessages((current) =>
            updateMessage(current, assistantId, (item) => ({
              ...item,
              citations,
            })),
          );
        },
      });
      setMessages((current) =>
        updateMessage(current, assistantId, (item) => ({
          ...item,
          pending: false,
        })),
      );
    } catch (caught) {
      setMessages((current) =>
        updateMessage(current, assistantId, (item) => ({
          ...item,
          content: getErrorMessage(caught),
          error: true,
          pending: false,
        })),
      );
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-16 items-center justify-between gap-4 border-b px-4 sm:px-6 lg:px-8">
        <div>
          <h1 className="text-sm font-semibold">Ask the assistant</h1>
          <p className="hidden text-xs text-muted-foreground sm:block">
            Answers include page-level sources.
          </p>
        </div>
        {loadingCruises ? (
          <Skeleton className="h-8 w-44" />
        ) : (
          <Select
            value={selectedCruiseId ?? "all"}
            onValueChange={(value) =>
              setSelectedCruiseId(value === "all" ? null : value)
            }
          >
            <SelectTrigger className="h-9 w-44 sm:w-56" aria-label="Search scope">
              <FileSearch className="text-muted-foreground" />
              <SelectValue>
                {selectedCruiseId
                  ? cruiseLabel(cruises, selectedCruiseId)
                  : "Search all cruises"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent align="end">
              <SelectItem value="all">Search all cruises</SelectItem>
              {cruises.map((cruise) => (
                <SelectItem key={cruise.id} value={cruise.id}>
                  {cruise.name} · {cruise.year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {cruiseError && (
        <div className="px-4 pt-4 sm:px-6">
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{cruiseError}</AlertDescription>
          </Alert>
        </div>
      )}

      <ScrollArea ref={scrollAreaRef} className="min-h-0 flex-1">
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 py-7 sm:px-6 sm:py-10">
          {messages.length === 0 ? (
            <Welcome
              hasCruises={cruises.length > 0}
              onOpenLibrary={onOpenLibrary}
              onSuggestion={setMessage}
            />
          ) : (
            <div className="space-y-8">
              {messages.map((item) => (
                <MessageBubble key={item.id} message={item} />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t bg-background px-3 py-3 sm:px-6 sm:py-4">
        <form
          className="mx-auto max-w-3xl"
          onSubmit={(event) => void handleSubmit(event)}
        >
          <div className="rounded-2xl border bg-card p-2 shadow-sm focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/15">
            <Textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about an itinerary, date, port, or excursion…"
              aria-label="Message"
              className="max-h-40 min-h-14 resize-none border-0 bg-transparent px-2 py-2 shadow-none focus-visible:ring-0"
              disabled={sending}
            />
            <div className="flex items-center justify-between gap-3 px-1">
              <p className="text-xs text-muted-foreground">
                Enter to send · Shift + Enter for a new line
              </p>
              <Button
                type="submit"
                size="icon"
                className="rounded-xl"
                disabled={!message.trim() || sending}
                aria-label="Send message"
              >
                <ArrowUp />
              </Button>
            </div>
          </div>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            Verify important dates and details against the cited itinerary page.
          </p>
        </form>
      </div>
    </div>
  );
}

function Welcome({
  hasCruises,
  onOpenLibrary,
  onSuggestion,
}: {
  hasCruises: boolean;
  onOpenLibrary: () => void;
  onSuggestion: (suggestion: string) => void;
}) {
  return (
    <div className="my-auto py-8">
      <span className="flex size-11 items-center justify-center rounded-xl bg-accent text-primary">
        <Sparkles className="size-5" />
      </span>
      <h2 className="mt-5 text-2xl font-semibold tracking-tight">
        What would you like to know?
      </h2>
      <p className="mt-2 max-w-lg text-sm leading-6 text-muted-foreground">
        Ask about schedules, destinations, excursions, dates, or use the
        itinerary details to draft a guest email.
      </p>

      {!hasCruises && (
        <Alert className="mt-6 max-w-lg">
          <LibraryBig />
          <AlertTitle>Your library is empty</AlertTitle>
          <AlertDescription>
            Add a cruise and a PDF before asking itinerary questions.
            <Button
              variant="link"
              className="ml-1 h-auto p-0"
              onClick={onOpenLibrary}
            >
              Open library
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="mt-7 grid gap-2 sm:grid-cols-3">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSuggestion(suggestion)}
            className="rounded-xl border bg-card p-3 text-left text-sm leading-5 transition-colors hover:border-primary/30 hover:bg-accent/50"
          >
            <BookOpen className="mb-3 size-4 text-primary" />
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-foreground px-4 py-3 text-sm leading-6 text-background sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <span
        className={cn(
          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg",
          message.error ? "bg-destructive/10 text-destructive" : "bg-accent text-primary",
        )}
      >
        {message.error ? (
          <AlertCircle className="size-4" />
        ) : (
          <Bot className="size-4" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div
          className={cn(
            "whitespace-pre-wrap text-sm leading-7",
            message.error && "text-destructive",
          )}
        >
          {message.content}
          {message.pending && (
            <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-primary align-middle" />
          )}
        </div>
        {!!message.citations?.length && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">
              Sources
            </span>
            {message.citations.map((citation) => (
              <Badge
                key={`${citation.cruise}-${citation.year}-${citation.page}`}
                variant="outline"
                className="bg-background font-normal"
              >
                {citation.cruise} {citation.year} · p. {citation.page}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function updateMessage(
  messages: Message[],
  id: string,
  update: (message: Message) => Message,
): Message[] {
  return messages.map((message) =>
    message.id === id ? update(message) : message,
  );
}

function cruiseLabel(cruises: Cruise[], id: string): string {
  const cruise = cruises.find((item) => item.id === id);
  return cruise ? `${cruise.name} · ${cruise.year}` : "Selected cruise";
}

function getErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "Something went wrong.";
}
