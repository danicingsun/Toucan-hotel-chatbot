import React from "react";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  return (
    <div className="app-shell">
      <div className="card">
        <header className="header">
          <img src="/toucan.jpg" alt="Toucan" className="logo" />
          <div>
            <h1>Toucan Booking Assistant</h1>
            <p className="subtitle">Book a room at Hotel Van der Valk — quick & easy</p>
          </div>
        </header>

        <ChatWindow />
      </div>
    </div>
  );
}