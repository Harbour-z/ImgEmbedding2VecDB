import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ 
  content, 
  className = '' 
}) => {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { className, children } = props as any;
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            
            return language ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={language}
                PreTag="div"
                className="code-block"
                customStyle={{
                  margin: '12px 0',
                  borderRadius: '8px',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  maxHeight: '400px',
                  overflow: 'auto'
                }}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code 
                className="inline-code"
                style={{
                  backgroundColor: '#f0f0f0',
                  color: '#e83e8c',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
                  fontSize: '0.9em',
                  display: 'inline',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}
              >
                {children}
              </code>
            );
          },
          
          pre({ children }) {
            return <>{children}</>;
          },

          h1({ children }) {
            return (
              <h1 style={{
                fontSize: '1.8em',
                fontWeight: 700,
                margin: '1.2em 0 0.6em 0',
                color: '#1a1a1a',
                borderBottom: '2px solid #1677ff',
                paddingBottom: '0.3em'
              }}>
                {children}
              </h1>
            );
          },

          h2({ children }) {
            return (
              <h2 style={{
                fontSize: '1.5em',
                fontWeight: 600,
                margin: '1em 0 0.5em 0',
                color: '#1a1a1a',
                borderBottom: '1px solid #d9d9d9',
                paddingBottom: '0.3em'
              }}>
                {children}
              </h2>
            );
          },

          h3({ children }) {
            return (
              <h3 style={{
                fontSize: '1.3em',
                fontWeight: 600,
                margin: '0.8em 0 0.4em 0',
                color: '#262626'
              }}>
                {children}
              </h3>
            );
          },

          h4({ children }) {
            return (
              <h4 style={{
                fontSize: '1.1em',
                fontWeight: 600,
                margin: '0.6em 0 0.3em 0',
                color: '#262626'
              }}>
                {children}
              </h4>
            );
          },

          p({ children }) {
            return (
              <p style={{
                margin: '0.8em 0',
                lineHeight: '1.7',
                color: '#262626'
              }}>
                {children}
              </p>
            );
          },

          ul({ children }) {
            return (
              <ul style={{
                margin: '0.8em 0',
                paddingLeft: '1.5em',
                lineHeight: '1.7'
              }}>
                {children}
              </ul>
            );
          },

          ol({ children }) {
            return (
              <ol style={{
                margin: '0.8em 0',
                paddingLeft: '1.5em',
                lineHeight: '1.7'
              }}>
                {children}
              </ol>
            );
          },

          li({ children }) {
            return (
              <li style={{
                marginBottom: '0.4em',
                marginLeft: '0.5em'
              }}>
                {children}
              </li>
            );
          },

          blockquote({ children }) {
            return (
              <blockquote style={{
                margin: '1em 0',
                padding: '12px 16px',
                backgroundColor: '#f5f5f5',
                borderLeft: '4px solid #1677ff',
                color: '#595959',
                fontStyle: 'italic'
              }}>
                {children}
              </blockquote>
            );
          },

          a({ children, href }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#1677ff',
                  textDecoration: 'none',
                  borderBottom: '1px dashed #1677ff',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e6f7ff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {children}
              </a>
            );
          },

          img({ src, alt }) {
            return (
              <img
                src={src}
                alt={alt}
                style={{
                  maxWidth: '100%',
                  height: 'auto',
                  borderRadius: '8px',
                  margin: '12px 0',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}
                loading="lazy"
              />
            );
          },

          table({ children }) {
            return (
              <div style={{ overflowX: 'auto', margin: '1em 0' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '14px',
                  backgroundColor: '#fff'
                }}>
                  {children}
                </table>
              </div>
            );
          },

          thead({ children }) {
            return (
              <thead style={{
                backgroundColor: '#fafafa',
                borderBottom: '2px solid #d9d9d'
              }}>
                {children}
              </thead>
            );
          },

          tbody({ children }) {
            return <tbody>{children}</tbody>;
          },

          tr({ children }) {
            return (
              <tr style={{
                borderBottom: '1px solid #f0f0f0'
              }}>
                {children}
              </tr>
            );
          },

          th({ children }) {
            return (
              <th style={{
                padding: '12px',
                textAlign: 'left',
                fontWeight: 600,
                color: '#262626'
              }}>
                {children}
              </th>
            );
          },

          td({ children }) {
            return (
              <td style={{
                padding: '12px',
                color: '#595959'
              }}>
                {children}
              </td>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
