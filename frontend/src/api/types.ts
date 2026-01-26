export interface ImageResult {
    id: string;
    score: number;
    metadata: {
        filename: string;
        file_path: string;
        file_size?: number;
        width?: number;
        height?: number;
        format?: string;
        created_at: string;
        tags: string[];
        description?: string;
    };
    preview_url?: string;
}

export interface ChatRequest {
    query: string;
    session_id?: string;
    top_k?: number;
    score_threshold?: number;
}

export interface ChatResponse {
    session_id: string;
    answer: string;
    intent: string;
    optimized_query: string;
    results?: {
        total: number;
        images: ImageResult[];
    };
    suggestions: string[];
    recommendation?: ImageRecommendation;
    timestamp: string;
}

export interface ImageRecommendation {
    recommended_image_id?: string;
    alternative_image_ids: string[];
    recommendation_reason: string;
    user_prompt_for_deletion: boolean;
    total_images_analyzed: number;
}

export interface DeleteConfirmationRequest {
    image_ids: string[];
    confirmed: boolean;
    reason?: string;
}

export interface DeleteConfirmationResponse {
    deleted_count: number;
    failed_count: number;
    deleted_image_ids: string[];
    failed_image_ids: string[];
}

export interface UploadResponse {
    status: string;
    message: string;
    data: {
        id: string;
        filename: string;
        file_path: string;
        full_path: string;
        file_size: number;
        width: number;
        height: number;
        format: string;
        created_at: string;
        url: string;
        indexed: boolean | string;
        index_mode: string;
    };
}

export interface ChatMessage {
    id: string;
    type: 'user' | 'agent';
    content: string;
    images?: ImageResult[];
    suggestions?: string[];
    timestamp: Date;
}
