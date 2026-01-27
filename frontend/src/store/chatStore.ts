import { create } from 'zustand';
import { sendChatMessage } from '../api/agent';
import { getImageUrl } from '../api/storage';
import type { ChatMessage, ImageResult } from '../api/types';

interface ChatStore {
    sessionId: string | null;
    messages: ChatMessage[];
    isLoading: boolean;
    error: string | null;
    sendMessage: (query: string, userMessage?: ChatMessage) => Promise<void>;
    clearHistory: () => void;
    setMessages: (messages: ChatMessage[]) => void;
    addMessage: (message: ChatMessage) => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
    sessionId: localStorage.getItem('chat_session_id'),
    messages: [],
    isLoading: false,
    error: null,

    sendMessage: async (query: string, userMessage?: ChatMessage) => {
        const { sessionId, messages } = get();

        // Check if user message already exists (added by ChatPage)
        const lastMessage = messages[messages.length - 1];
        const hasUserMessage = lastMessage && 
                            lastMessage.type === 'user' && 
                            lastMessage.content === query;

        // Use provided userMessage or create new one
        const msg = userMessage || {
            id: crypto.randomUUID(),
            type: 'user' as const,
            content: query,
            timestamp: new Date(),
        };

        // Only add user message if not already present
        if (!hasUserMessage) {
            set({ messages: [...messages, msg], isLoading: true, error: null });
        } else {
            set({ isLoading: true, error: null });
        }

        // Setup AbortController for timeout (120 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await sendChatMessage({
                query,
                session_id: sessionId || undefined,
                top_k: 10,
            }, { signal: controller.signal });

            clearTimeout(timeoutId);

            if (!response || typeof response.session_id !== 'string' || typeof response.answer !== 'string') {
                throw new Error('服务器响应格式异常，请刷新页面后重试。');
            }

            if (response.session_id && response.session_id !== sessionId) {
                localStorage.setItem('chat_session_id', response.session_id);
                set({ sessionId: response.session_id });
            }

            const images: ImageResult[] = response.results?.images?.map(img => ({
                ...img,
                preview_url: getImageUrl(img.id),
            })) || [];

            const agentMessage: ChatMessage = {
                id: crypto.randomUUID(),
                type: 'agent',
                content: response.answer,
                images: images.length > 0 ? images : undefined,
                suggestions: response.suggestions,
                timestamp: new Date(response.timestamp),
            };

            set(state => ({
                messages: [...state.messages, agentMessage],
                isLoading: false,
            }));
        } catch (error: unknown) {
            clearTimeout(timeoutId);
            
            let errorMessage = error instanceof Error ? error.message : '发送失败';
            const errorRecord = typeof error === 'object' && error !== null ? (error as Record<string, unknown>) : null;
            const errorName = typeof errorRecord?.name === 'string' ? errorRecord.name : undefined;
            const errorCode = typeof errorRecord?.code === 'string' ? errorRecord.code : undefined;
            
            // Handle Timeout / Abort
            if (errorName === 'CanceledError' || errorName === 'AbortError' || errorCode === 'ERR_CANCELED') {
                errorMessage = '请求超时：检索可能较慢（首次加载/向量生成），请稍后重试。';
            }

            // Create an error message bubble
            const errorMessageObj: ChatMessage = {
                id: crypto.randomUUID(),
                type: 'agent',
                content: `❌ ${errorMessage}`,
                timestamp: new Date(),
            };

            set(state => ({
                isLoading: false,
                error: errorMessage,
                messages: [...state.messages, errorMessageObj]
            }));
        }
    },

    clearHistory: () => {
        localStorage.removeItem('chat_session_id');
        set({ sessionId: null, messages: [], error: null });
    },

    setMessages: (messages: ChatMessage[]) => {
        set({ messages });
    },

    addMessage: (message: ChatMessage) => {
        set(state => ({ messages: [...state.messages, message] }));
    },
}));
