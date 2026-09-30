import { useEffect, useState } from "react";
import { LibraryBig, MessageCircleQuestion, ShipWheel } from "lucide-react";

import { cn } from "@/lib/utils";
import Chat from "@/pages/Chat";
import Library from "@/pages/Library";

type Page = "library" | "chat";

function pageFromPath(): Page {
  return window.location.pathname.startsWith("/chat") ? "chat" : "library";
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromPath);

  useEffect(() => {
    const handlePopState = () => setPage(pageFromPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(nextPage: Page) {
    const path = nextPage === "chat" ? "/chat" : "/";
    window.history.pushState({}, "", path);
    setPage(nextPage);
  }

  return (
    <div className="min-h-svh bg-background md:grid md:grid-cols-[15.5rem_1fr]">
      <aside className="hidden border-r bg-sidebar md:flex md:h-svh md:flex-col md:sticky md:top-0">
        <Brand />
        <nav className="space-y-1 px-3 pt-5" aria-label="Primary navigation">
          <NavItem
            active={page === "library"}
            icon={LibraryBig}
            label="Library"
            onClick={() => navigate("library")}
          />
          <NavItem
            active={page === "chat"}
            icon={MessageCircleQuestion}
            label="Ask assistant"
            onClick={() => navigate("chat")}
          />
        </nav>
        <div className="mt-auto border-t px-5 py-4 text-xs leading-5 text-muted-foreground">
          Answers are grounded in your uploaded itinerary documents.
        </div>
      </aside>

      <div className="flex min-h-svh min-w-0 flex-col">
        <header className="sticky top-0 z-20 flex h-15 items-center justify-between border-b bg-background/95 px-4 backdrop-blur md:hidden">
          <Brand compact />
          <nav className="flex items-center gap-1" aria-label="Primary navigation">
            <NavItem
              active={page === "library"}
              icon={LibraryBig}
              label="Library"
              compact
              onClick={() => navigate("library")}
            />
            <NavItem
              active={page === "chat"}
              icon={MessageCircleQuestion}
              label="Chat"
              compact
              onClick={() => navigate("chat")}
            />
          </nav>
        </header>
        <main className="flex min-h-0 flex-1 flex-col">
          {page === "library" ? (
            <Library onOpenChat={() => navigate("chat")} />
          ) : (
            <Chat onOpenLibrary={() => navigate("library")} />
          )}
        </main>
      </div>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("flex items-center gap-3", compact ? "" : "px-5 pt-6")}>
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <ShipWheel className="size-4.5" aria-hidden="true" />
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight">Cruise Assistant</p>
        {!compact && (
          <p className="mt-0.5 text-xs text-muted-foreground">Itinerary workspace</p>
        )}
      </div>
    </div>
  );
}

function NavItem({
  active,
  compact = false,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  compact?: boolean;
  icon: typeof LibraryBig;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center rounded-lg text-sm font-medium transition-colors",
        compact ? "gap-1.5 px-2.5 py-2" : "w-full gap-3 px-3 py-2.5",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground",
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="size-4" aria-hidden="true" />
      {label}
    </button>
  );
}
