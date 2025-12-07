import React from "react";

export default function QuickReplies({ buttons, onClick }) {
  if (!buttons || buttons.length === 0) return null;

  return (
    <div className="quick-replies">
      {buttons.map((btn, i) => (
        <button key={i} onClick={() => onClick(btn)}>
          {btn.title}
        </button>
      ))}
    </div>
  );
}