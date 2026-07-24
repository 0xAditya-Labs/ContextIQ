import { useState, useEffect } from 'react';
import ChatWindow from './components/ChatWindow';
import InputBox from './components/InputBox';
import { sendQuery } from './api/client';
import './index.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Wake up Render backend on load
  useEffect(() => {
    const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    fetch(`${API_BASE_URL}/health`).catch(() => console.log("Backend waking up..."));
  }, []);

  const [theme, setTheme] = useState("dark");

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    document.documentElement.setAttribute("data-theme", newTheme);
  };

  const handleSendMessage = async (text) => {
    const userMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    const response = await sendQuery(text);

    const aiMessage = { 
      role: "assistant", 
      content: response.answer,
      sources: response.sources
    };
    
    setMessages(prev => [...prev, aiMessage]);
    setIsLoading(false);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <img src="/Accenture-Logo.png" alt="Accenture" className="logo" />
          <h1>ContextIQ</h1>
          <span className="subtitle">Enterprise IT Assistant</span>
        </div>
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
      </header>
      
      <main className="main-content">
        <ChatWindow messages={messages} />
        <InputBox onSend={handleSendMessage} isLoading={isLoading} />
      </main>
    </div>
  );
}

export default App;
