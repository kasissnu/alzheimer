"use client";

import { useEffect, useState, useRef } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { useMediaRecorder } from "@/hooks/useMediaRecorder";
import { useWebSocket } from "@/hooks/useWebSocket";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_BASE = "http://localhost:8000/api";

export default function Home() {
  const [users, setUsers] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any | null>(null);
  const [historySummary, setHistorySummary] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Modals state
  const [isIdentifyOpen, setIsIdentifyOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [registerName, setRegisterName] = useState("");

  const {
    isRecording,
    startCamera,
    stopCamera,
    captureImage,
    startAudioRecording,
    stopAudioRecording
  } = useMediaRecorder();

  const {
    isConnected,
    status: wsStatus,
    messages,
    setMessages,
    connect,
    disconnect,
    sendAudioChunk,
    finishAudio
  } = useWebSocket(currentUser?.user_id || null);

  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Fetch users on mount
  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/users`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      toast.error("Failed to fetch users");
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Handle User Selection & History
  const selectUser = async (user: any) => {
    setCurrentUser(user);
    setMessages([]);
    setHistorySummary("");
    disconnect(); // disconnect old ws

    try {
      const res = await fetch(`${API_BASE}/history/${user.user_id}`);
      if (res.ok) {
        const data = await res.json();
        setHistorySummary(data.summary);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Connect WebSocket when user changes
  useEffect(() => {
    if (currentUser) {
      connect();
    }
    return () => disconnect();
  }, [currentUser, connect, disconnect]);


  // ---- Chat Audio Recording Flow ----
  const handleStartChatVoice = async () => {
    if (!currentUser) return;
    const ok = await startAudioRecording((blob) => {
      sendAudioChunk(blob);
    });
    if (!ok) toast.error("Could not access microphone");
  };

  const handleStopChatVoice = async () => {
    await stopAudioRecording();
    finishAudio(); // Tell backend we ended stream
  };


  // ---- Identity Flow ----
  const openIdentify = async () => {
    setIsIdentifyOpen(true);
    setTimeout(() => {
      if (videoRef.current) startCamera(videoRef.current);
    }, 100);
  };

  const submitIdentity = async () => {
    setIsLoading(true);
    const blob = await captureImage();
    if (!blob) {
      toast.error("Failed to capture image");
      setIsLoading(false);
      return;
    }
    stopCamera();
    setIsIdentifyOpen(false);

    const formData = new FormData();
    formData.append("file", blob, "face.jpg");

    try {
      const res = await fetch(`${API_BASE}/auth/identify`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.verified && data.identity) {
        toast.success(`Welcome back, ${data.name}!`);
        // We know the id, fetch full user object from state or just build it
        let u = users.find(u => u.user_id === data.identity);
        if (!u) {
          u = { user_id: data.identity, name: data.name, registered_at: new Date().toISOString() };
          fetchUsers(); // refresh
        }
        selectUser(u);
      } else {
        toast.error("Identity not verified. Please register.");
      }
    } catch (e) {
      toast.error("Identification failed");
    } finally {
      setIsLoading(false);
    }
  };


  // ---- Registration Flow ----
  const openRegister = () => {
    setRegisterName("");
    setIsRegisterOpen(true);
    setTimeout(() => {
      if (videoRef.current) startCamera(videoRef.current);
    }, 100);
  };

  const submitRegister = async () => {
    if (!registerName.trim()) {
      toast.error("Please enter a name.");
      return;
    }
    setIsLoading(true);
    
    // Capture Face
    const faceBlob = await captureImage();
    if (!faceBlob) {
      toast.error("Could not capture face.");
      setIsLoading(false);
      return;
    }
    
    // Attempt to capture 3 seconds of audio using standard recorder (not streaming chunks)
    toast("Recording voice sample... please speak for 3 seconds.");
    const ok = await startAudioRecording();
    let voiceBlob = null;
    if (ok) {
      await new Promise(r => setTimeout(r, 3000));
      voiceBlob = await stopAudioRecording();
    }
    stopCamera();

    const formData = new FormData();
    formData.append("name", registerName);
    formData.append("face_image", faceBlob, "face.jpg");
    if (voiceBlob) {
      formData.append("audio_file", voiceBlob, "voice.webm");
    }

    try {
      const res = await fetch(`${API_BASE}/users/register`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Successfully registered ${data.name}!`);
        fetchUsers();
        setIsRegisterOpen(false);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to register");
      }
    } catch (e) {
      toast.error("Network error during registration");
    } finally {
      setIsLoading(false);
    }
  };


  // ---- Deletion Flow ----
  const handleDeleteUser = async (user_id: string) => {
    if (!confirm(`Are you sure you want to delete user ${user_id}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/users/${user_id}`, { method: "DELETE" });
      if (res.ok) {
        toast.success("User deleted successfully.");
        if (currentUser?.user_id === user_id) {
          setCurrentUser(null);
          setMessages([]);
          setHistorySummary("");
        }
        fetchUsers();
      }
    } catch (e) {
      toast.error("Failed to delete user");
    }
  };


  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      
      <Sidebar 
        users={users} 
        currentUser={currentUser} 
        onSelectUser={selectUser} 
        onIdentifyClick={openIdentify} 
        onRegisterClick={openRegister}
        onDeleteClick={handleDeleteUser}
      />
      
      <ChatArea 
        currentUser={currentUser}
        messages={messages}
        historySummary={historySummary}
        isRecording={isRecording}
        isProcessing={!!wsStatus}
        onStartRecord={handleStartChatVoice}
        onStopRecord={handleStopChatVoice}
      />


      {/* Identify Modal */}
      <Dialog open={isIdentifyOpen} onOpenChange={(o) => { if (!o) stopCamera(); setIsIdentifyOpen(o); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Identify Self</DialogTitle>
            <DialogDescription>Look into the camera to authenticate biometrically.</DialogDescription>
          </DialogHeader>
          <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border">
            <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover transform -scale-x-100" />
          </div>
          <DialogFooter className="sm:justify-between">
            <Button variant="outline" onClick={() => setIsIdentifyOpen(false)}>Cancel</Button>
            <Button onClick={submitIdentity} disabled={isLoading}>{isLoading ? "Scanning..." : "Capture & Identify"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Register Modal */}
      <Dialog open={isRegisterOpen} onOpenChange={(o) => { if (!o) stopCamera(); setIsRegisterOpen(o); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Register New User</DialogTitle>
            <DialogDescription>Look into the camera and speak your name when recording.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input 
              placeholder="What is your name?" 
              value={registerName} 
              onChange={(e) => setRegisterName(e.target.value)} 
            />
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border">
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover transform -scale-x-100" />
            </div>
          </div>
          <DialogFooter className="sm:justify-between">
            <Button variant="outline" onClick={() => setIsRegisterOpen(false)}>Cancel</Button>
            <Button onClick={submitRegister} disabled={isLoading || registerName.trim().length === 0}>
              {isLoading ? "Recording Voice..." : "Start Enrollment (Takes 3s)"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
