"use client";

import { useEffect, useState, useRef } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { useMediaRecorder } from "@/hooks/useMediaRecorder";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_BASE = "http://localhost:8000/api";

export default function Home() {
  const [users, setUsers] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any | null>(null);
  
  // Storage arrays for ChatArea
  const [historySummary, setHistorySummary] = useState("");
  const [historyTimeline, setHistoryTimeline] = useState<any[]>([]);
  
  const [isLoading, setIsLoading] = useState(false);

  // Modals state
  const [isIdentifyOpen, setIsIdentifyOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  
  const [registerName, setRegisterName] = useState("");

  const {
    startCamera,
    stopCamera,
    captureImage,
    startAudioRecording,
    stopAudioRecording
  } = useMediaRecorder();

  const videoRef = useRef<HTMLVideoElement>(null);
  const memVideoRef = useRef<HTMLVideoElement>(null);
  
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
    setHistorySummary("");
    setHistoryTimeline([]);

    try {
      const res = await fetch(`${API_BASE}/history/${user.user_id}`);
      if (res.ok) {
        const data = await res.json();
        setHistorySummary(data.summary);
        setHistoryTimeline(data.history);
      }
    } catch (e) {
      console.error(e);
    }
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
        let u = users.find(u => u.user_id === data.identity);
        if (!u) {
          u = { user_id: data.identity, name: data.name, registered_at: new Date().toISOString() };
          await fetchUsers(); // refresh
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
    
    // Capture Face (No voice required for registration in CLI explicitly anymore)
    const faceBlob = await captureImage();
    if (!faceBlob) {
      toast.error("Could not capture face.");
      setIsLoading(false);
      return;
    }
    stopCamera();

    const formData = new FormData();
    formData.append("name", registerName);
    formData.append("face_image", faceBlob, "face.jpg");

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


  // ---- Add Memory Flow (7s Audio) ----
  const openAddMemory = () => {
    if (!currentUser) return;
    setIsMemoryOpen(true);
    setTimeout(() => {
      if (memVideoRef.current) startCamera(memVideoRef.current);
    }, 100);
  };

  const submitAddMemory = async () => {
    if (!currentUser) return;
    setIsLoading(true);
    toast("Starting 7-second recording memory now...");
    
    const micStarted = await startAudioRecording();
    if (!micStarted) {
      toast.error("Failed to start microphone");
      setIsLoading(false);
      return;
    }
    
    // Record for exactly 7 seconds like CLI
    await new Promise((r) => setTimeout(r, 7000));
    const audioBlob = await stopAudioRecording();
    stopCamera();

    if (!audioBlob) {
      toast.error("Recording failed");
      setIsLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append("user_id", currentUser.user_id);
    formData.append("audio_file", audioBlob, "memory.webm");

    toast("Processing speech-to-text...");
    try {
      const res = await fetch(`${API_BASE}/memories/add`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          toast.success("Memory captured successfully!");
          // Refresh user context
          selectUser(currentUser);
          setIsMemoryOpen(false);
        } else {
          toast.error(data.error || "Failed transcription");
        }
      } else {
        toast.error("Transcription API error");
      }
    } catch (e) {
      toast.error("Network error adding memory");
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
          setHistorySummary("");
          setHistoryTimeline([]);
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
        onAddMemoriesClick={openAddMemory}
        onDeleteClick={handleDeleteUser}
      />
      
      <ChatArea 
        currentUser={currentUser}
        historySummary={historySummary}
        history={historyTimeline}
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
            <DialogDescription>Look into the camera to enroll your face.</DialogDescription>
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
              {isLoading ? "Enrolling..." : "Capture Face & Register"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Memory Modal */}
      <Dialog open={isMemoryOpen} onOpenChange={(o) => { if (!o) stopCamera(); setIsMemoryOpen(o); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Memory</DialogTitle>
            <DialogDescription>Speak your memory aloud for exactly 7 seconds.</DialogDescription>
          </DialogHeader>
          <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border">
            <video ref={memVideoRef} autoPlay playsInline muted className="w-full h-full object-cover transform -scale-x-100" />
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-white animate-pulse">
                Recording Memory...
              </div>
            )}
          </div>
          <DialogFooter className="sm:justify-between">
            <Button variant="outline" onClick={() => setIsMemoryOpen(false)} disabled={isLoading}>Cancel</Button>
            <Button onClick={submitAddMemory} disabled={isLoading}>
              {isLoading ? "Recording..." : "Start 7s Recording"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
