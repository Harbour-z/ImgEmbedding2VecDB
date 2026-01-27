import { create } from 'zustand';
import type { Conversation, ConversationListItem, ConversationFilters } from '../types/conversation';
import { conversationStorage } from '../services/conversationStorage';

interface ConversationStore {
    currentConversation: Conversation | null;
    conversations: ConversationListItem[];
    filters: ConversationFilters;
    isLoading: boolean;
    error: string | null;

    loadConversations: () => Promise<void>;
    createNewConversation: (title?: string) => Promise<Conversation>;
    loadConversation: (id: string) => Promise<void>;
    updateCurrentConversation: (updates: Partial<Conversation>) => Promise<void>;
    addMessageToCurrent: (message: any) => Promise<void>;
    deleteConversation: (id: string) => Promise<void>;
    setFilters: (filters: ConversationFilters) => void;
    clearCurrentConversation: () => Promise<void>;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
    currentConversation: null,
    conversations: [],
    filters: {
        sortBy: 'updatedAt',
        sortOrder: 'desc',
    },
    isLoading: false,
    error: null,

    loadConversations: async () => {
        set({ isLoading: true, error: null });
        try {
            const conversations = await conversationStorage.listConversations(get().filters);
            set({ conversations, isLoading: false });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load conversations';
            set({ error: errorMessage, isLoading: false });
        }
    },

    createNewConversation: async (title?: string) => {
        set({ isLoading: true, error: null });
        try {
            const newConversation = await conversationStorage.createConversation(title);
            set({
                currentConversation: newConversation,
                isLoading: false,
            });
            await get().loadConversations();
            return newConversation;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create conversation';
            set({ error: errorMessage, isLoading: false });
            throw error;
        }
    },

    loadConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
            const conversation = await conversationStorage.getConversation(id);
            if (!conversation) {
                throw new Error('Conversation not found');
            }
            set({
                currentConversation: conversation,
                isLoading: false,
            });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation';
            set({ error: errorMessage, isLoading: false });
            throw error;
        }
    },

    updateCurrentConversation: async (updates: Partial<Conversation>) => {
        const { currentConversation } = get();
        if (!currentConversation) return;

        set({ isLoading: true, error: null });
        try {
            const updated = await conversationStorage.updateConversation(currentConversation.id, updates);
            set({
                currentConversation: updated,
                isLoading: false,
            });
            await get().loadConversations();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update conversation';
            set({ error: errorMessage, isLoading: false });
            throw error;
        }
    },

    addMessageToCurrent: async (message: any) => {
        const { currentConversation } = get();
        if (!currentConversation) return;

        set({ isLoading: true, error: null });
        try {
            await conversationStorage.addMessage(currentConversation.id, message);
            const updated = await conversationStorage.getConversation(currentConversation.id);
            set({
                currentConversation: updated || null,
                isLoading: false,
            });
            await get().loadConversations();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to add message';
            set({ error: errorMessage, isLoading: false });
            throw error;
        }
    },

    deleteConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
            await conversationStorage.deleteConversation(id);
            const { currentConversation } = get();
            if (currentConversation?.id === id) {
                set({ currentConversation: null });
            }
            await get().loadConversations();
            set({ isLoading: false });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete conversation';
            set({ error: errorMessage, isLoading: false });
            throw error;
        }
    },

    setFilters: (filters: ConversationFilters) => {
        set({ filters });
        get().loadConversations();
    },

    clearCurrentConversation: async () => {
        set({ currentConversation: null });
    },
}));
