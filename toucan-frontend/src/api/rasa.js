import axios from "axios";

const RASA_URL = "http://localhost:5005/webhooks/rest/webhook";

/**
 * Send a message to Rasa REST webhook.
 * `message` should be the text to send; it can be:
 *  - plain text (e.g. "hi")
 *  - an intent payload (e.g. '/affirm')
 *  - an intent + entities JSON (e.g. '/inform{"guests":"2"}')
 *
 * Returns array of messages from Rasa.
 */
export async function sendToRasa(message, sender = "user") {
  try {
    const resp = await axios.post(RASA_URL, { sender, message });
    return resp.data; // array of messages
  } catch (err) {
    console.error("Rasa connection error", err);
    return [{ text: "Sorry — cannot reach Rasa server. Is it running?" }];
  }
}