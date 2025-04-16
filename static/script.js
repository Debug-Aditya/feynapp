// Import Firebase libraries
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc, getDocs, query, orderBy, limit } from 'firebase/firestore';

// Firebase configuration (keep this the same as in your script)
const firebaseConfig = {
  apiKey: "AIzaSyBbj8GBEruexPfDUjp31XW-uTygCmORd6o",
  authDomain: "feynapp-688f0.firebaseapp.com",
  projectId: "feynapp-688f0",
  storageBucket: "feynapp-688f0.firebasestorage.app",
  messagingSenderId: "329779568218",
  appId: "1:329779568218:web:35733bc063b6ccedab8263",
  measurementId: "G-FQHP92HFZR"
};

// Initialize Firebase and Firestore
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);  // Firestore reference


  let currentChatId = null;

  // Load all chats when page loads
  window.onload = async () => {
      await loadChatList();
      document.getElementById('chat-input').classList.add('hidden');
  };

  async function loadChatList() {
      const res = await fetch('/api/chats');
      const chats = await res.json();

      const chatsContent = document.getElementById('chatsContent');
      chatsContent.innerHTML = '';

      chats.forEach(chat => {
          const chatTile = document.createElement('div');
          chatTile.className = 'chat-tile';
          chatTile.textContent = chat;
          chatTile.onclick = () => {
              currentChatId = chat;
              showTerminalTab();
              loadChatHistory(currentChatId);
          };
          chatsContent.appendChild(chatTile);
      });
  }

  function showChatsTab() {
      document.getElementById('chatsView').classList.remove('hidden');
      document.getElementById('terminalView').classList.add('hidden');
      document.getElementById('chat-input').classList.add('hidden');
      document.getElementById('messages').innerHTML = '';
  }

  function showTerminalTab() {
      if (!currentChatId) return;
      document.getElementById('chatsView').classList.add('hidden');
      document.getElementById('terminalView').classList.remove('hidden');
      document.getElementById('chat-input').classList.remove('hidden');
  }

  async function loadChatHistory(chatId) {
      const chatBox = document.getElementById('messages');
      chatBox.innerHTML = ''; // Clear the current chat

      // Fetch messages from Firestore
      const q = query(collection(db, "chats", chatId, "messages"), orderBy("timestamp"));
      const querySnapshot = await getDocs(q);

      querySnapshot.forEach(doc => {
          const msg = doc.data();
          const msgDiv = document.createElement('div');
          msgDiv.className = 'chat-message ' + (msg.role === 'user' ? 'user-msg' : 'bot-msg');
          const md = window.markdownit();
          msgDiv.innerHTML = md.render(msg.role === 'user' ? "You: " + msg.content : "FEYN: " + msg.content);
          chatBox.appendChild(msgDiv);
      });

      chatBox.scrollTop = chatBox.scrollHeight;
  }


  async function createNewChat() {
      const input = document.getElementById('newChatName');
      const name = input.value.trim();
      if (!name) return;

      const res = await fetch(`/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
      });

      if (res.ok) {
          input.value = '';
          await loadChatList(); // Reload the chat list to display the new tile
      } else {
          const error = await res.json();
          alert(error.error || "Failed to create chat");
      }
  }

  function handleNewChatKeyPress(event) {
      if (event.key === 'Enter') createNewChat();
  }

  function handleKeyPress(event) {
      if (event.key === 'Enter') sendMessage();
  }

 async function sendMessage() {
     const input = document.getElementById('userInput');
     const message = input.value.trim();
     if (!message || !currentChatId) return;

     const chatBox = document.getElementById('messages');

     // Display user message
     const userMsg = document.createElement('div');
     userMsg.className = 'chat-message user-msg';
     userMsg.textContent = "You: " + message;
     chatBox.appendChild(userMsg);

     // Display placeholder for bot response
     const botMsg = document.createElement('div');
     botMsg.className = 'chat-message bot-msg';
     botMsg.textContent = "FEYN: Thinking...";
     chatBox.appendChild(botMsg);

     input.value = '';
     chatBox.scrollTop = chatBox.scrollHeight;

     try {
         const res = await fetch(`/api/chat/${currentChatId}`, {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ message })
         });

         const data = await res.json();
         console.log("Raw API Response:", data.content);

         // Use Markdown-it with the `breaks` option enabled
         const md = window.markdownit({ breaks: true });
         const sanitizedContent = data.content
             .replace(/\n{3,}/g, '\n\n') // Replace 3+ newlines with 2 newlines
             .replace(/\s{2,}/g, ' ')   // Replace multiple spaces with a single space
             .trim();                   // Trim leading and trailing whitespace
         botMsg.innerHTML = "FEYN: " + md.render(sanitizedContent);

         // Save both user and bot messages to Firestore
         await addDoc(collection(db, "chats", currentChatId, "messages"), {
             role: "user",
             content: message,
             timestamp: new Date()
         });

         await addDoc(collection(db, "chats", currentChatId, "messages"), {
             role: "bot",
             content: sanitizedContent,
             timestamp: new Date()
         });

         chatBox.scrollTop = chatBox.scrollHeight;
     } catch (err) {
         console.error("API Error:", err);
         botMsg.textContent = "FEYN: Sorry, I couldn't reach the server.";
     }
 }
