// We define the backend URL here. Since our FastAPI server runs on port 8000, 
// we point our fetch requests to it.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Sends a user question to the FastAPI backend and retrieves the answer.
 * @param {string} question - The user's input.
 * @returns {Promise<Object>} - A promise that resolves to the backend JSON response { answer: string, sources: [] }
 */
export async function sendQuery(question) {
  try {
    // 1. We use the native fetch API to make a POST request to our FastAPI endpoint.
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // 2. We convert our javascript object into a JSON string that matches 
      // the QueryRequest Pydantic model we built in the backend: { "question": str }
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 3. We wait for the backend to send the response, and parse it back from JSON into a JS Object.
    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error("Error communicating with backend:", error);
    // Return a graceful error message so the UI doesn't completely break
    return {
      answer: "Sorry, I encountered an error communicating with the server.",
      sources: []
    };
  }
}
