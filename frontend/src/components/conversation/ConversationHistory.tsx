import React, { useEffect } from 'react';
import { List, Input, Button, Empty, Popconfirm, Tag, Space } from 'antd';
import { 
    MessageOutlined, 
    DeleteOutlined, 
    SearchOutlined,
    PlusOutlined,
    ClockCircleOutlined
} from '@ant-design/icons';
import { useConversationStore } from '../../store/conversationStore';
import type { ConversationListItem } from '../../types/conversation';

const { Search } = Input;

export const ConversationHistory: React.FC = () => {
    const {
        conversations,
        filters,
        isLoading,
        loadConversations,
        setFilters,
        deleteConversation,
        createNewConversation,
    } = useConversationStore();

    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    const handleSearch = (value: string) => {
        setFilters({ ...filters, search: value });
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await deleteConversation(id);
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    };

    const handleCreateNew = async () => {
        try {
            await createNewConversation();
        } catch (error) {
            console.error('Failed to create new conversation:', error);
        }
    };

    const formatDate = (date: Date) => {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days === 0) return '今天';
        if (days === 1) return '昨天';
        if (days < 7) return `${days}天前`;
        if (days < 30) return `${Math.floor(days / 7)}周前`;
        return date.toLocaleDateString('zh-CN');
    };

    const renderListItem = (item: ConversationListItem) => (
        <List.Item
            key={item.id}
            style={{
                cursor: 'pointer',
                borderRadius: 8,
                marginBottom: 8,
                padding: 12,
                border: '1px solid #f0f0f0',
                transition: 'all 0.3s',
            }}
            onClick={() => window.location.href = `/chat?conversationId=${item.id}`}
            actions={[
                <Popconfirm
                    title="确定要删除这个对话吗？"
                    onConfirm={(e) => handleDelete(item.id, e as any)}
                    okText="确定"
                    cancelText="取消"
                >
                    <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        size="small"
                        onClick={(e) => e.stopPropagation()}
                    />
                </Popconfirm>,
            ]}
        >
            <List.Item.Meta
                avatar={<MessageOutlined style={{ fontSize: 24, color: '#1677ff' }} />}
                title={
                    <Space>
                        <span style={{ fontWeight: 600 }}>{item.title}</span>
                        <Tag color="blue">{item.messageCount} 条消息</Tag>
                    </Space>
                }
                description={
                    <div>
                        <div style={{ marginBottom: 4, color: '#666' }}>
                            {item.preview}
                        </div>
                        <Space size="small">
                            <span style={{ fontSize: 12, color: '#999' }}>
                                <ClockCircleOutlined /> {formatDate(item.updatedAt)}
                            </span>
                        </Space>
                    </div>
                }
            />
        </List.Item>
    );

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={handleCreateNew}
                        block
                    >
                        新建对话
                    </Button>
                    <Search
                        placeholder="搜索对话..."
                        allowClear
                        onSearch={handleSearch}
                        onChange={(e) => handleSearch(e.target.value)}
                        style={{ width: '100%' }}
                        prefix={<SearchOutlined />}
                    />
                </Space>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
                {isLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                        <div>加载中...</div>
                    </div>
                ) : conversations.length === 0 ? (
                    <Empty
                        description="暂无对话历史"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                ) : (
                    <List
                        dataSource={conversations}
                        renderItem={renderListItem}
                        style={{ background: '#fff' }}
                    />
                )}
            </div>
        </div>
    );
};
