import { useState, useRef, useCallback } from 'react';

export function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const startCamera = useCallback(async (videoElement: HTMLVideoElement) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      videoElement.srcObject = stream;
      videoElement.play();
      streamRef.current = stream;
      videoRef.current = videoElement;
      return true;
    } catch (err) {
      console.error("Camera access denied:", err);
      return false;
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  }, []);

  const captureImage = useCallback(async (): Promise<Blob | null> => {
    if (!videoRef.current) return null;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    
    return new Promise(resolve => {
      canvas.toBlob(blob => resolve(blob), 'image/jpeg', 0.9);
    });
  }, []);

  const startAudioRecording = useCallback(async (onDataAvailable?: (data: Blob) => void) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && onDataAvailable) {
          onDataAvailable(e.data);
        }
      };

      recorder.start(500); // chunk every 500ms
      mediaRecorderRef.current = recorder;
      streamRef.current = stream;
      setIsRecording(true);
      return true;
    } catch (err) {
      console.error("Microphone access denied:", err);
      return false;
    }
  }, []);

  const stopAudioRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current) {
        resolve(null);
        return;
      }
      
      let finalBlob: Blob | null = null;
      const chunks: BlobPart[] = [];
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };
      
      mediaRecorderRef.current.onstop = () => {
        if (chunks.length > 0) {
          finalBlob = new Blob(chunks, { type: 'audio/webm' });
        }
        
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
        setIsRecording(false);
        resolve(finalBlob);
      };
      
      mediaRecorderRef.current.stop();
    });
  }, []);

  return {
    isRecording,
    startCamera,
    stopCamera,
    captureImage,
    startAudioRecording,
    stopAudioRecording
  };
}
