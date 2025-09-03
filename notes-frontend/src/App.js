import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

const API = "https://notes-app-mma1.onrender.com";

function App() {
  const [notes, setNotes] = useState([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  // Auth
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") || "");

  useEffect(() => {
    if (token) fetchNotes();
  }, [token]);

  const fetchNotes = async () => {
    try {
      const res = await axios.get(`${API}/notes/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotes(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const register = async () => {
    try {
      await axios.post(`${API}/auth/register`, { email, password });
      alert("Registered — now login");
    } catch (e) {
      alert(e.response?.data?.detail || "Register failed");
    }
  };

  const login = async () => {
    try {
      const res = await axios.post(`${API}/auth/login`, { email, password });
      localStorage.setItem("token", res.data.access_token);
      setToken(res.data.access_token);
      alert("Logged in");
    } catch (e) {
      alert(e.response?.data?.detail || "Login failed");
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken("");
    setNotes([]);
  };

  const addNote = async (e) => {
    e.preventDefault();
    if (!title || !content) return alert("Title and content required");
    try {
      await axios.post(
        `${API}/notes/`,
        { title, content },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTitle("");
      setContent("");
      fetchNotes();
    } catch (e) {
      alert(e.response?.data?.detail || "Add note failed");
    }
  };

  const deleteNote = async (id) => {
    if (!window.confirm("Delete this note?")) return;
    try {
      await axios.delete(`${API}/notes/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchNotes();
    } catch (e) {
      alert(e.response?.data?.detail || "Delete failed");
    }
  };

  if (!token) {
    // Show register/login form if not logged in
    return (
      <div className="app-container">
        <h2>Login / Register</h2>
        <input placeholder="Email" value={email} onChange={(e)=>setEmail(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} />
        <div style={{marginTop:10}}>
          <button onClick={login}>Login</button>
          <button onClick={register} style={{marginLeft:8}}>Register</button>
        </div>
        <p style={{marginTop:12, color:"#666"}}>After login you will be able to create and view your notes.</p>
      </div>
    );
  }

  // Logged in view
  return (
    <div className="app-container">
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <h1>Notes App </h1>
        <div>
          <span style={{marginRight:10}}>Logged in as {email}</span>
          <button onClick={logout}>Logout</button>
        </div>
      </div>

      <form onSubmit={addNote} className="note-form">
        <input value={title} onChange={(e)=>setTitle(e.target.value)} placeholder="Title" />
        <textarea value={content} onChange={(e)=>setContent(e.target.value)} placeholder="Content" />
        <button type="submit">Add Note</button>
      </form>

      <div className="notes-list">
        {notes.map(n=>(
          <div key={n.id} className="note-card">
            <h3>{n.title}</h3>
            <p>{n.content}</p>
            <button onClick={()=>deleteNote(n.id)}>Delete</button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
