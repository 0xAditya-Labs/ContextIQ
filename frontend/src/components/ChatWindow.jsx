import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

/**
 * Renders the full list of messages in a scrollable window.
 * @param {Array} messages - The array of message objects to display.
 */
export default function ChatWindow({ messages }) {
  // We use a React 'ref' to get direct access to the very bottom element of the chat list
  const bottomRef = useRef(null);

  // 1. useEffect runs a side-effect every time its dependency array (messages) changes.
  // 2. So, every time a new message is added to the array, this runs and scrolls us to the bottom automatically!
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-window">
      {messages.length === 0 ? (
        <div className="empty-state">
          <h2>Welcome to ContextIQ</h2>
          <p>Ask a question about internal IT support.</p>
        </div>
      ) : (
        messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))
      )}
      
      {/* This invisible div always stays at the bottom so we can scroll down to it */}
      <div ref={bottomRef} />
    </div>
  );
}
