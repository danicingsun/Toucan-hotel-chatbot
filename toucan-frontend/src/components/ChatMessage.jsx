import React from "react";

export default function ChatMessage({ from = "bot", text }) {
  const isUser = from === "user";
  return (
    <div className={`msg-row ${isUser ? "msg-user" : "msg-bot"}`}>
      <div className={`bubble ${isUser ? "bubble-user" : "bubble-bot"}`}>
        {String(text).split("\n").map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    </div>
  );
}