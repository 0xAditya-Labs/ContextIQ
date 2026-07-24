/**
 * Renders a single message bubble in the chat.
 * @param {Object} message - The message object { role: "user" | "assistant", content: "..." }
 */
export default function MessageBubble({ message }) {
  // We determine styling based on whether the user or the AI sent the message
  const isUser = message.role === "user";
  
  return (
    <div className={`message-row ${isUser ? 'row-user' : 'row-assistant'}`}>
      <div className={`message-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        <p className="message-content">{message.content}</p>
        
        {/* If there are sources attached to the response, we display them */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="message-sources">
            <span className="source-title">Sources:</span>
            <ul>
              {message.sources.map((src, i) => (
                <li key={i}>{src}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
