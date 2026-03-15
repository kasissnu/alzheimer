"use client";

import { useRef, useEffect } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Mic, Square, Loader2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface ChatAreaProps {
  currentUser: any;
  messages: Message[];
  historySummary: string;
  isRecording: boolean;
  isProcessing: boolean;
  onStartRecord: () => void;
  onStopRecord: () => void;
}

export function ChatArea({
  currentUser,
  messages,
  historySummary,
  isRecording,
  isProcessing,
  onStartRecord,
  onStopRecord
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isProcessing]);

  if (!currentUser) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
        <div className="h-16 w-16 mb-4 rounded-full bg-secondary flex items-center justify-center">
          <Mic className="h-8 w-8 opacity-50" />
        </div>
        <h2 className="text-xl font-medium text-foreground mb-2">Welcome to MEMORA</h2>
        <p className="max-w-md">Identify yourself using the camera or select a user from the sidebar to access memories and start logging new context.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-screen relative bg-background">
      <div className="absolute top-0 w-full h-8 bg-gradient-to-b from-background to-transparent z-10 pointer-events-none" />
      
      <ScrollArea className="flex-1 p-4 md:p-8" viewportRef={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-8 pb-32">
          
          {historySummary && (
            <div className="p-4 rounded-xl bg-secondary/50 text-sm border shadow-sm">
              <span className="font-medium text-foreground mr-2">Context:</span>
              <span className="text-muted-foreground leading-relaxed">{historySummary}</span>
            </div>
          )}

          {messages.length === 0 && !historySummary && (
            <div className="text-center text-muted-foreground mt-24">
              <p>No prior memories found for {currentUser.name}.</p>
              <p className="text-sm mt-2 opacity-50">Speak to start creating new ones.</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              
              {msg.role === 'assistant' && (
                <Avatar className="h-8 w-8 border bg-primary text-primary-foreground hidden sm:flex">
                  <AvatarFallback className="bg-transparent text-xs">AI</AvatarFallback>
                </Avatar>
              )}

              <div className={`px-4 py-3 rounded-2xl max-w-[85%] sm:max-w-[75%] ${
                msg.role === 'user' 
                  ? 'bg-primary text-primary-foreground rounded-tr-sm' 
                  : 'bg-muted rounded-tl-sm text-foreground'
              }`}>
                {msg.content ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                ) : (
                  <span className="flex gap-1 items-center h-6">
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{animationDelay: "0ms"}} />
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{animationDelay: "150ms"}} />
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{animationDelay: "300ms"}} />
                  </span>
                )}
              </div>

            </div>
          ))}
          
          {isProcessing && !isRecording && (
            <div className="flex justify-center py-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground bg-secondary/50 px-4 py-2 rounded-full shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Working on it...
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="absolute bottom-0 w-full p-4 md:p-8 bg-gradient-to-t from-background via-background to-transparent pointer-events-none">
        <div className="max-w-3xl mx-auto flex justify-center pointer-events-auto relative">
          
          {isRecording ? (
            <Button
              size="lg"
              variant="destructive"
              className="rounded-full h-16 px-8 shadow-xl hover:shadow-destructive/25 transition-all outline outline-4 outline-destructive/20 animate-pulse"
              onClick={onStopRecord}
            >
              <Square className="mr-2 h-5 w-5 fill-current" />
              Stop Recording
            </Button>
          ) : (
            <Button
              size="lg"
              className="rounded-full h-16 px-8 shadow-xl transition-all outline outline-4 outline-primary/10 hover:outline-primary/20"
              onClick={onStartRecord}
            >
              <Mic className="mr-2 h-5 w-5" />
              Speak to Memora
            </Button>
          )}

        </div>
      </div>
    </div>
  );
}
