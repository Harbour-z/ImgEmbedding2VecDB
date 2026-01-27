import type { ChatMessage } from '../api/types';

export interface Conversation {
    id: string;
    title: string;
    messages: ChatMessage[];
    preview?: string;
    createdAt: Date;
    updatedAt: Date;
    serverSessionId?: string;
}

export interface ConversationListItem {
    id: string;
    title: string;
    preview: string;
    messageCount: number;
    createdAt: Date;
    updatedAt: Date;
    serverSessionId?: string;
}

export interface ConversationFilters {
    search?: string;
    sortBy?: 'createdAt' | 'updatedAt';
    sortOrder?: 'asc' | 'desc';
}
