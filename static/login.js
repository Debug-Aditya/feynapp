import { initializeApp } from "https://www.gstatic.com/firebasejs/9.0.2/firebase-app.js";
import { getAuth, signInWithPopup, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/9.0.2/firebase-auth.js";

// Your config
const firebaseConfig = {
  apiKey: "AIzaSyBbj8GBEruexPfDUjp31XW-uTygCmORd6o",
  authDomain: "XXX.firebaseapp.com",
  projectId: "feynapp-688f0.web.app",
  ...
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

document.getElementById('loginBtn').addEventListener('click', async () => {
  try {
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();

    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken })
    });

    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('userId', data.user_id);
      window.location.href = "/";
    } else {
      const err = await res.text();
      console.error("Login error:", err);
      alert("Login failed.");
    }
  } catch (err) {
    console.error("Popup error:", err);
    alert("Login popup failed.");
  }
});
