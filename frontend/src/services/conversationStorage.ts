import type { Conversation, ConversationListItem, ConversationFilters } from '../types/conversation';

const DB_NAME = 'ChatAppDB';
const DB_VERSION = 1;
const STORE_NAME = 'conversations';

class ConversationStorage {
    private db: IDBDatabase | null = null;
    private initPromise: Promise<void> | null = null;

    private async init(): Promise<void> {
        if (this.initPromise) {
            return this.initPromise;
        }

        this.initPromise = new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => {
                reject(new Error('Failed to open IndexedDB'));
            };

            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
                    objectStore.createIndex('createdAt', 'createdAt', { unique: false });
                    objectStore.createIndex('updatedAt', 'updatedAt', { unique: false });
                }
            };
        });

        return this.initPromise;
    }

    private async ensureInitialized(): Promise<void> {
        if (!this.db) {
            await this.init();
        }
    }

    async createConversation(title: string = '新对话'): Promise<Conversation> {
        await this.ensureInitialized();
        
        const conversation: Conversation = {
            id: crypto.randomUUID(),
            title,
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.add(conversation);

            request.onsuccess = () => resolve(conversation);
            request.onerror = () => reject(new Error('Failed to create conversation'));
        });
    }

    async getConversation(id: string): Promise<Conversation | null> {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(id);

            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(new Error('Failed to get conversation'));
        });
    }

    async updateConversation(id: string, updates: Partial<Conversation>): Promise<Conversation> {
        await this.ensureInitialized();

        const existing = await this.getConversation(id);
        if (!existing) {
            throw new Error('Conversation not found');
        }

        const updated: Conversation = {
            ...existing,
            ...updates,
            updatedAt: new Date(),
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.put(updated);

            request.onsuccess = () => resolve(updated);
            request.onerror = () => reject(new Error('Failed to update conversation'));
        });
    }

    async addMessage(conversationId: string, message: any): Promise<void> {
        await this.ensureInitialized();

        const conversation = await this.getConversation(conversationId);
        if (!conversation) {
            throw new Error('Conversation not found');
        }

        const updatedMessages = [...conversation.messages, message];
        const preview = this.generatePreview(updatedMessages);
        const title = this.generateTitle(conversation.title, updatedMessages);

        await this.updateConversation(conversationId, {
            messages: updatedMessages,
            preview,
            title,
        });
    }

    async deleteConversation(id: string): Promise<void> {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(new Error('Failed to delete conversation'));
        });
    }

    async listConversations(filters?: ConversationFilters): Promise<ConversationListItem[]> {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = () => {
                let conversations: ConversationListItem[] = request.result.map((conv: any) => ({
                    id: conv.id,
                    title: conv.title,
                    preview: conv.preview || '',
                    messageCount: conv.messages?.length || 0,
                    createdAt: new Date(conv.createdAt),
                    updatedAt: new Date(conv.updatedAt),
                    serverSessionId: conv.serverSessionId,
                }));

                if (filters?.search) {
                    const searchTerm = filters.search.toLowerCase();
                    conversations = conversations.filter(conv =>
                        conv.title.toLowerCase().includes(searchTerm) ||
                        conv.preview.toLowerCase().includes(searchTerm)
                    );
                }

                conversations.sort((a, b) => {
                    const field = filters?.sortBy || 'updatedAt';
                    const order = filters?.sortOrder === 'asc' ? 1 : -1;
                    
                    if (field === 'createdAt') {
                        return (a.createdAt.getTime() - b.createdAt.getTime()) * order;
                    } else {
                        return (a.updatedAt.getTime() - b.updatedAt.getTime()) * order;
                    }
                });

                resolve(conversations);
            };

            request.onerror = () => reject(new Error('Failed to list conversations'));
        });
    }

    async clearAll(): Promise<void> {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(new Error('Failed to clear all conversations'));
        });
    }

    private generatePreview(messages: any[]): string {
        if (messages.length === 0) return '';
        
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.type === 'user') {
            return lastMessage.content.slice(0, 100);
        } else {
            return lastMessage.content.slice(0, 100);
        }
    }

    private generateTitle(currentTitle: string, messages: any[]): string {
        if (currentTitle !== '新对话') return currentTitle;
        
        const firstUserMessage = messages.find(msg => msg.type === 'user');
        if (firstUserMessage) {
            return firstUserMessage.content.slice(0, 50) || '新对话';
        }
        
        return '新对话';
    }
}

export const conversationStorage = new ConversationStorage();
