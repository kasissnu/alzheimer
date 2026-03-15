import { useState, useRef, useCallback } from 'react';

type WSMessage = 
  | { type: 'status', message: string }
  | { type: 'transcript', text: string }
  | { type: 'stream', chunk: string, done: boolean }
  | { type: 'complete' }
  | { type: 'error', message: string };

export function useWebSocket(userId: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [status, setStatus] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!userId) return;
    
    // Connect to FastAPI WebSocket
    const ws = new WebSocket(`ws://localhost:8000/api/chat/${userId}`);
    
    ws.onopen = () => {
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        if (data.type === 'status') {
          setStatus(data.message);
        } else if (data.type === 'transcript') {
          setMessages(prev => [
            ...prev, 
            { role: 'user', content: data.text },
            { role: 'assistant', content: '' }
          ]);
        } else if (data.type === 'stream') {
          setMessages(prev => {
            const newMsgs = [...prev];
            const activeMsg = newMsgs[newMsgs.length - 1];
            if (activeMsg && activeMsg.role === 'assistant') {
              activeMsg.content += data.chunk;
            }
            return newMsgs;
          });
        } else if (data.type === 'complete') {
          setStatus('');
        } else if (data.type === 'error') {
          console.error("WS Error from server:", data.message);
          setStatus("Error: " + data.message);
        }
      } catch (e) {
        console.error("Failed to parse WS message", e);
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
    };
    
    wsRef.current = ws;
  }, [userId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendAudioChunk = useCallback((blob: Blob) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(blob);
    }
  }, []);

  const finishAudio = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text: "__END_AUDIO__" }));
    }
  }, []);

  return {
    isConnected,
    status,
    messages,
    setMessages, // expose to allow hydrating history
    connect,
    disconnect,
    sendAudioChunk,
    finishAudio
  };
}
