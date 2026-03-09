import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function RichMarkdown({ content }: { content: string }) {
  return (
    <div className="pqts-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          code: ({ className, children, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code className="pqts-inline-code" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <pre className="pqts-code-block">
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
