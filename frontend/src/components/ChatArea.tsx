"use client";

import { useRef, useEffect } from "react";
import { User } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface MemoryEntry {
  role: string;
  content: string;
  source: string;
  timestamp: string;
}

interface ChatAreaProps {
  currentUser: any;
  historySummary: string;
  history: MemoryEntry[];
}

export function ChatArea({
  currentUser,
  historySummary,
  history
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  if (!currentUser) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground bg-background">
        <div className="h-16 w-16 mb-4 rounded-full bg-secondary flex items-center justify-center">
          <User className="h-8 w-8 opacity-50" />
        </div>
        <h2 className="text-xl font-medium text-foreground mb-2">Welcome to MEMORA</h2>
        <p className="max-w-md">Select a user from the sidebar or use the camera to identify yourself to access memories.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-screen relative bg-background">
      <div className="absolute top-0 w-full h-8 bg-gradient-to-b from-background to-transparent z-10 pointer-events-none" />
      
      <ScrollArea className="flex-1 p-4 md:p-8" viewportRef={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-8 pb-32">
          
          <div className="pb-4 border-b">
            <h2 className="text-2xl font-semibold mb-2">{currentUser.name}&apos;s Memories</h2>
            <p className="text-sm text-muted-foreground">ID: {currentUser.user_id}</p>
          </div>

          <div className="p-5 rounded-xl bg-secondary/30 text-sm border shadow-sm">
            <h3 className="font-medium text-foreground mb-3 text-base">Context Summary:</h3>
            {historySummary ? (
              <p className="text-muted-foreground leading-relaxed">{historySummary}</p>
            ) : (
              <p className="text-muted-foreground opacity-70 italic">No prior memories are stored for this user yet.</p>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="font-medium text-foreground">Memory Timeline:</h3>
            {(!history || history.length === 0) && (
              <p className="text-sm text-muted-foreground mt-2 opacity-50">Speak to start creating new ones.</p>
            )}

            {history && history.map((msg, i) => (
              <div key={i} className="p-4 border rounded-lg bg-card">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-medium text-muted-foreground uppercase">{msg.source}</span>
                  <span className="text-xs text-muted-foreground">{msg.timestamp}</span>
                </div>
                <p className="text-sm leading-relaxed">{msg.content}</p>
              </div>
            ))}
          </div>

        </div>
      </ScrollArea>
    </div>
  );
}
