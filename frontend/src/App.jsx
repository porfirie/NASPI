import React, { useState } from 'react';
import Login from './Login';
import Dashboard from './Dashboard'; // Importă noua componentă

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  if (!token) {
    return <Login setToken={setToken} />;
  }

  return (
    <div className="bg-slate-950 min-h-screen">
      <Dashboard setToken={setToken} />
    </div>
  );
}

export default App;