import client from './client';
import type {
    ChatRequest,
    ChatResponse,
    ImageRecommendation,
    DeleteConfirmationRequest,
    DeleteConfirmationResponse
} from './types';

export async function sendChatMessage(params: ChatRequest, options?: { signal?: AbortSignal }): Promise<ChatResponse> {
    return await client.post<any, ChatResponse>('/agent/chat', params, { signal: options?.signal });
}

export async function createSession(userId?: string): Promise<string> {
    const res = await client.post<any, { status: string; session_id: string; message?: string }>(
        '/agent/session/create',
        userId ?? null
    );
    return res.session_id;
}

export async function deleteImagesByRecommendation(
    request: DeleteConfirmationRequest
): Promise<any> {
    return await client.post<any, any>('/agent/recommendation/delete', request);
}

export async function previewDeleteOperation(imageIds: string[]): Promise<any> {
    return await client.post<any, any>('/agent/recommendation/preview-delete', imageIds);
}
