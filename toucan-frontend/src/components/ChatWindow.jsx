import React, { useEffect, useRef, useState } from "react";
import ChatMessage from "./ChatMessage";
import QuickReplies from "./QuickReplies";

// Create a unique sender ID per browser session 
function getSenderId() { 
  let id = localStorage.getItem("sender_id"); 
  if (!id) { 
    id = crypto.randomUUID(); 
    localStorage.setItem("sender_id", id); 
  } 
  return id; 
}

async function sendToRasaWithSender(message, senderId) { 
  const res = await fetch("https://toucan-hotel-chatbot-llsu.onrender.com/webhooks/rest/webhook", { 
    method: "POST", 
    headers: { "Content-Type": "application/json" }, 
    body: JSON.stringify({ 
      sender: senderId, 
      message 
    }) 
  });  
  return res.json(); 
}


export default function ChatWindow() {

  const senderId = getSenderId();

  const [messages, setMessages] = useState([
    { from: "bot", text: " Toucan: Hello — would you like help booking a room today?" }
  ]);
  const [input, setInput] = useState("");
  const [buttons, setButtons] = useState([]);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, buttons]);

  function appendMessage(msg) {
    setMessages(prev => [...prev, msg]);
  }

  async function sendMessage({ text, payload }) {
    // Case 1: user typed something
    if (text) {
      appendMessage({ from: "user", text });
      // send the text and a senderID to distinguish between users
      const replies = await sendToRasaWithSender(text, senderId);
      handleBotReplies(replies);
      return;
    }

    // Case 2: user clicked a button
    if (payload) {
      // payload is {title, payload}
      appendMessage({ from: "user", text: payload.title }); // show label
      const replies = await sendToRasaWithSender(payload.payload, senderId);    // send payload and senderID to Rasa
      handleBotReplies(replies);
      return;
    }
  }

  function handleBotReplies(replies) {
    let newButtons = [];
    replies.forEach(r => {
      if (r.text) appendMessage({ from: "bot", text: r.text });
      if (r.buttons) {
        // capture buttons sent by Rasa
        newButtons = r.buttons;
      }
      if (r.custom && r.custom.buttons) {
        newButtons = r.custom.buttons;
      }
    });
    setButtons(newButtons || []);
  }

  function handleSendText(e) {
    e?.preventDefault();
    const txt = input.trim();
    if (!txt) return;
    sendMessage({ text: txt });
    setInput("");
    setButtons([]); // clear quick replies after send
  }

  function handleQuickReply(button) {
    // button is {title, payload}
    sendMessage({ payload: button });
    setButtons([]);
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((m, i) => (
          <ChatMessage key={i} from={m.from} text={m.text} />
        ))}
        <div ref={bottomRef} />
      </div>

      <QuickReplies buttons={buttons} onClick={handleQuickReply} />

      <form className="composer" onSubmit={handleSendText}>
        <input
          placeholder='Type a message or click a suggestion (e.g. "yes")'
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit">Send</button>
        <button
          type="button"
          className="start-btn"
          onClick={() =>
            sendMessage({ payload: { title: "Start booking, please", payload: "/book_hotel" } })
          }
          title="Start booking"
        >
          Start booking
        </button>
      </form>
    </div>
  );
}