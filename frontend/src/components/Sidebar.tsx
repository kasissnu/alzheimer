"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { PlusCircle, Camera, User, Trash2 } from "lucide-react";

interface UserItem {
  user_id: string;
  name: string;
  registered_at: string;
}

interface SidebarProps {
  users: UserItem[];
  currentUser: UserItem | null;
  onSelectUser: (user: UserItem) => void;
  onIdentifyClick: () => void;
  onRegisterClick: () => void;
  onDeleteClick: (userId: string) => void;
}

export function Sidebar({
  users,
  currentUser,
  onSelectUser,
  onIdentifyClick,
  onRegisterClick,
  onDeleteClick
}: SidebarProps) {
  return (
    <div className="w-64 border-r bg-sidebar flex flex-col h-screen">
      <div className="p-4 border-b">
        <h1 className="text-xl font-semibold tracking-tight">MEMORA</h1>
        <p className="text-xs text-muted-foreground mt-1">Biometric Memory System</p>
      </div>
      
      <div className="p-3 space-y-2 border-b">
        <Button 
          variant="default" 
          className="w-full justify-start"
          onClick={onIdentifyClick}
        >
          <Camera className="mr-2 h-4 w-4" />
          Identify Self
        </Button>
        <Button 
          variant="outline" 
          className="w-full justify-start"
          onClick={onRegisterClick}
        >
          <PlusCircle className="mr-2 h-4 w-4" />
          Register New User
        </Button>
      </div>

      <div className="flex-1 overflow-hidden">
        <div className="px-4 py-3 text-sm font-medium text-muted-foreground">
          Known Users
        </div>
        <ScrollArea className="h-full px-2">
          {users.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2 py-4">No users registered.</p>
          ) : (
            users.map((u) => (
              <div 
                key={u.user_id} 
                className={`flex items-center justify-between p-2 rounded-md mb-1 cursor-pointer transition-colors ${currentUser?.user_id === u.user_id ? "bg-accent text-accent-foreground" : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"}`}
                onClick={() => onSelectUser(u)}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="text-[10px]">{u.name.substring(0, 2).toUpperCase()}</AvatarFallback>
                  </Avatar>
                  <span className="text-sm truncate">{u.name}</span>
                </div>
                {currentUser?.user_id === u.user_id && (
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-6 w-6 opacity-50 hover:opacity-100 hover:text-destructive"
                    onClick={(e) => { e.stopPropagation(); onDeleteClick(u.user_id); }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))
          )}
        </ScrollArea>
      </div>
      
      {currentUser && (
        <div className="p-4 border-t bg-muted/30">
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback>{currentUser.name.substring(0, 2).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="overflow-hidden">
              <p className="text-sm font-medium truncate">{currentUser.name}</p>
              <p className="text-xs text-muted-foreground truncate">{currentUser.user_id}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
