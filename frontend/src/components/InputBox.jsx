import { useState } from 'react';

/**
 * Renders the input area where users type their questions.
 * @param {Function} onSend - A callback function passed from the parent (App.jsx) to execute when the user submits.
 * @param {boolean} isLoading - Disables the input while waiting for the backend to respond.
 */
export default function InputBox({ onSend, isLoading }) {
  // 1. We use React 'state' to keep track of exactly what the user is typing in real-time.
  const [text, setText] = useState("");

  const handleSubmit = (e) => {
    // 2. Prevent the default browser behavior of refreshing the page on form submit
    e.preventDefault();
    if (text.trim() && !isLoading) {
      // 3. Call the parent function and pass the question string
      onSend(text.trim());
      // 4. Clear the input box after sending
      setText("");
    }
  };

  return (
    <form className="input-container" onSubmit={handleSubmit}>
      <input
        type="text"
        className="text-input"
        placeholder="Type your message..."
        value={text}
        // Update our 'text' state every time the user presses a key
        onChange={(e) => setText(e.target.value)}
        disabled={isLoading}
      />
      <button 
        type="submit" 
        className="send-button"
        disabled={isLoading || !text.trim()}
      >
        {isLoading ? '...' : 'Send'}
      </button>
    </form>
  );
}
