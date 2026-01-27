import React, { useEffect, useRef, useState } from 'react';
import {
  Layout,
  Input,
  Button,
  Avatar,
  Card,
  Space,
  Typography,
  Image,
  Tag,
  Spin,
  Tooltip,
  Modal,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  DeleteOutlined,
  PictureOutlined,
  BulbOutlined,
  PlusOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useChatStore } from '../store/chatStore';
import { useConversationStore } from '../store/conversationStore';
import type { ChatMessage } from '../api/types';
import { MarkdownRenderer } from '../components/common/MarkdownRenderer';

const { Content, Footer } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

export const ChatPage: React.FC = () => {
  const { messages, isLoading, sendMessage, clearHistory, setMessages, addMessage } = useChatStore();
  const { 
    currentConversation,
    createNewConversation,
    loadConversation,
    addMessageToCurrent,
  } = useConversationStore();
  const [inputValue, setInputValue] = useState('');
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [pendingAgentMessage, setPendingAgentMessage] = useState<ChatMessage | null>(null);
  const [processedMessageIds, setProcessedMessageIds] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Initialize conversationId from URL params
  const getInitialConversationId = () => {
    const params = new URLSearchParams(window.location.search);
    return params.get('conversationId');
  };
  
  const [conversationId, setConversationId] = useState<string | null>(() => getInitialConversationId());
  
  // Load conversation from URL params
  useEffect(() => {
    const convId = getInitialConversationId();
    
    // Only load if we have a conversationId and haven't loaded it yet
    if (convId && !currentConversation) {
      setIsRestoring(true);
      loadConversation(convId).catch(err => {
        console.error('Failed to load conversation:', err);
        setIsRestoring(false);
      });
    }
  }, [conversationId, currentConversation]);

  // Restore messages when currentConversation is loaded
  useEffect(() => {
    if (currentConversation && conversationId === currentConversation.id) {
      setMessages(currentConversation.messages);
      setIsRestoring(false);
    }
  }, [currentConversation, conversationId, setMessages]);

  // Save agent message to IndexedDB when new agent message appears
  useEffect(() => {
    if (pendingAgentMessage) {
      addMessageToCurrent(pendingAgentMessage).catch(err => {
        console.error('Failed to save agent message to IndexedDB:', err);
      });
      setPendingAgentMessage(null);
    }
  }, [pendingAgentMessage, addMessageToCurrent]);

  // Monitor messages to detect new agent messages
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    
    // Check if we have a pending agent message that matches last message
    if (pendingAgentMessage === null && lastMessage && lastMessage.type === 'agent') {
      // Check if this message has already been processed
      if (!processedMessageIds.has(lastMessage.id)) {
        // Check if this is a new agent message (not from restoring)
        if (!currentConversation || 
            !currentConversation.messages.some(msg => msg.id === lastMessage.id)) {
          setPendingAgentMessage(lastMessage);
          // Mark as processed
          setProcessedMessageIds(prev => new Set([...prev, lastMessage.id]));
        }
      }
    }
  }, [messages, pendingAgentMessage, currentConversation, processedMessageIds]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading || isRestoring) return;
    const query = inputValue.trim();
    setInputValue('');

    // Create new conversation if not exists
    let conversation = currentConversation;
    if (!conversation) {
      conversation = await createNewConversation();
    }

    // Save user message to both stores
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    
    // Add to conversationStore (IndexedDB)
    await addMessageToCurrent(userMessage);
    
    // Send to agent (userMessage will be added to chatStore by sendMessage)
    await sendMessage(query, userMessage);

    // Update URL with conversation ID
    if (conversation?.id && !window.location.search.includes(conversation.id)) {
      window.history.pushState({}, '', `/chat?conversationId=${conversation.id}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = async () => {
    clearHistory();
    await createNewConversation();
    setMessages([]);  // Clear chatStore messages
    window.location.href = '/chat';
  };

  const renderMessage = (msg: ChatMessage) => {
    const isUser = msg.type === 'user';
    const isSystem = msg.type === 'system';
    
    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 24,
        }}
      >
        <Space align="start" size={16} style={{ flexDirection: isUser ? 'row-reverse' : 'row' }}>
          <Avatar
            icon={
              isUser ? <UserOutlined /> : 
              isSystem ? <BulbOutlined /> : 
              <RobotOutlined />
            }
            style={{ 
                backgroundColor: isUser ? '#1677ff' : isSystem ? '#faad14' : '#52c41a',
                flexShrink: 0 
            }}
          />
          <div style={{ maxWidth: 600 }}>
            <Card
              size="small"
              variant="borderless"
              style={{
                backgroundColor: isUser ? '#e6f7ff' : isSystem ? '#fffbe6' : '#f6f6f6',
                borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                border: isSystem ? '1px solid #ffe58f' : undefined
              }}
              styles={{ body: { padding: '12px 16px' } }}
            >
              {isUser ? (
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {msg.content}
                </div>
              ) : (
                <MarkdownRenderer content={msg.content} />
              )}
            </Card>

            {/* Images */}
            {msg.images && msg.images.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Space size="small" style={{ marginBottom: 8 }}>
                    <PictureOutlined />
                    <Text type="secondary" style={{ fontSize: 12 }}>找到 {msg.images.length} 张图片</Text>
                </Space>
                <div style={{ 
                    background: '#f0f0f0', 
                    padding: 8, 
                    borderRadius: 8,
                    overflowX: 'auto',
                    whiteSpace: 'nowrap'
                }}>
                    <Image.PreviewGroup>
                        <Space size={8}>
                            {msg.images.map(img => (
                                <div key={img.id} style={{ width: 100, height: 100, borderRadius: 4, overflow: 'hidden', display: 'inline-block' }}>
                                    <Image
                                        src={img.preview_url || img.metadata?.file_path}
                                        width={100}
                                        height={100}
                                        style={{ objectFit: 'cover' }}
                                    />
                                </div>
                            ))}
                        </Space>
                    </Image.PreviewGroup>
                </div>
              </div>
            )}

            {/* Suggestions */}
            {msg.suggestions && msg.suggestions.length > 0 && (
                <div style={{ marginTop: 12 }}>
                    <Space size={[8, 8]} wrap>
                        {msg.suggestions.map((s, i) => (
                            <Tag 
                                key={i} 
                                icon={<BulbOutlined />} 
                                color="blue" 
                                style={{ cursor: 'pointer', borderRadius: 12 }}
                                onClick={() => sendMessage(s)}
                            >
                                {s}
                            </Tag>
                        ))}
                    </Space>
                </div>
            )}
            
            <div style={{ textAlign: isUser ? 'right' : 'left', marginTop: 4 }}>
                <Text type="secondary" style={{ fontSize: 10 }}>
                    {new Date(msg.timestamp).toLocaleTimeString()}
                </Text>
            </div>
          </div>
        </Space>
      </div>
    );
  };

  return (
    <Layout style={{ height: 'calc(100vh - 100px)', background: 'transparent' }}>
        <div style={{ 
            position: 'absolute', 
            top: -60, 
            right: 0, 
            zIndex: 1 
        }}>
             <Space>
                <Tooltip title="对话历史">
                    <Button 
                        type="text" 
                        icon={<HistoryOutlined />} 
                        onClick={() => setShowHistoryModal(true)}
                    />
                </Tooltip>
                {messages.length > 0 && (
                    <Tooltip title="清空对话">
                        <Button 
                            type="text" 
                            danger 
                            icon={<DeleteOutlined />} 
                            onClick={clearHistory}
                        />
                    </Tooltip>
                )}
            </Space>
        </div>

      <Content style={{ overflowY: 'auto', padding: '0 16px', scrollBehavior: 'smooth' }}>
        {isRestoring ? (
          <div style={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: '#999'
          }}>
             <Spin size="large" />
             <div style={{ marginTop: 16 }}>正在加载对话历史...</div>
          </div>
        ) : messages.length === 0 ? (
          <div style={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: '#999'
          }}>
             <Avatar size={64} icon={<RobotOutlined />} style={{ backgroundColor: '#f0f0f0', color: '#ccc', marginBottom: 24 }} />
             <Typography.Title level={4} style={{ color: '#666' }}>有什么可以帮您？</Typography.Title>
             <Space wrap style={{ maxWidth: 600, justifyItems: 'center', justifyContent: 'center' }}>
                {['查找去年的海边照片', '搜索红色的跑车', '最近上传的文档'].map(text => (
                    <Button key={text} shape="round" onClick={() => sendMessage(text)}>
                        {text}
                    </Button>
                ))}
             </Space>
          </div>
        ) : (
          <div style={{ maxWidth: 800, margin: '0 auto', paddingBottom: 20 }}>
            {messages.map(renderMessage)}
            {isLoading && (
               <div style={{ display: 'flex', marginBottom: 24 }}>
                   <Space align="start" size={16}>
                        <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
                        <Card size="small" variant="borderless" style={{ backgroundColor: '#f6f6f6', borderRadius: '4px 16px 16px 16px' }}>
                             <Space>
                                 <Spin size="small" />
                                 <Text type="secondary">正在思考...</Text>
                             </Space>
                        </Card>
                   </Space>
               </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </Content>
      
      <Footer style={{ background: 'transparent', padding: '16px 0' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <Card 
            styles={{ body: { padding: 8 } }} 
            style={{ 
                borderRadius: 24, 
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                border: '1px solid #eee'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
                <TextArea
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入消息..."
                    autoSize={{ minRows: 1, maxRows: 6 }}
                    variant="borderless"
                    style={{ 
                        resize: 'none', 
                        padding: '8px 12px', 
                        fontSize: 15,
                        lineHeight: 1.6
                    }}
                    disabled={isLoading}
                />
                <Button 
                    type="primary" 
                    shape="circle" 
                    icon={<SendOutlined />} 
                    size="large"
                    onClick={handleSend}
                    disabled={!inputValue.trim() || isLoading}
                    style={{ marginBottom: 4, marginRight: 4 }}
                />
            </div>
          </Card>
          <div style={{ textAlign: 'center', marginTop: 8 }}>
             <Text type="secondary" style={{ fontSize: 12 }}>AI生成内容可能不准确，请核实重要信息</Text>
          </div>
        </div>
      </Footer>

      {/* Conversation History Modal */}
      <Modal
        title="对话历史"
        open={showHistoryModal}
        onCancel={() => setShowHistoryModal(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        <div style={{ maxHeight: 600, overflowY: 'auto' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleNewConversation}
            style={{ marginBottom: 16 }}
            block
          >
            新建对话
          </Button>
          {currentConversation && (
            <div style={{ 
                padding: 12, 
                background: '#e6f7ff', 
                borderRadius: 8, 
                marginBottom: 16,
                border: '1px solid #1677ff'
            }}>
              <Space direction="vertical" size="small">
                <Text strong>当前对话</Text>
                <Text type="secondary">{currentConversation.title}</Text>
                <Text type="secondary">{currentConversation.messages.length} 条消息</Text>
              </Space>
            </div>
          )}
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">点击下方卡片查看对话历史</Text>
          </div>
          <Button
            type="link"
            onClick={() => window.location.href = '/conversations'}
            style={{ marginTop: 8 }}
          >
            查看完整历史
          </Button>
        </div>
      </Modal>
    </Layout>
  );
};
