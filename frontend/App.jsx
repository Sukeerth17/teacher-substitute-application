import React, { useState, useEffect, useCallback } from 'react';

// Tailwind CSS is assumed to be available
const API_BASE_URL = 'http://localhost:8000';

// --- AUTH UTILITIES (Simulated JWT Storage) ---

const storageKey = 'adminToken';

const saveToken = (token) => {
  localStorage.setItem(storageKey, token);
};

const loadToken = () => {
  return localStorage.getItem(storageKey);
};

const clearToken = () => {
  localStorage.removeItem(storageKey);
};

// --- DATA FETCHING & API UTILITIES ---

const fetchApi = async (path, options = {}) => {
  const token = loadToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized globally
  if (response.status === 401 || response.status === 403) {
    clearToken();
    window.location.reload(); 
    throw new Error('Unauthorized or Session Expired. Please log in.');
  }

  // Handle 204 No Content
  if (response.status === 204) {
      return { status: 204 };
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP Error: ${response.status}`);
  }
  return data;
};

// --- MAIN APPLICATION COMPONENT ---

const App = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(!!loadToken());
  const [activeTab, setActiveTab] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(''); // Global message state
  const [workloads, setWorkloads] = useState([]);
  const [history, setHistory] = useState([]);
  const [currentTeacher] = useState({ name: 'Admin', email: 'admin@school.edu' }); // Admin User

  // --- Initial Data Load (Workload & History) ---

  const loadDashboardData = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    try {
      const [workloadData, historyData] = await Promise.all([
        fetchApi('/absence/workload'),
        fetchApi('/absence/history'),
      ]);
      setWorkloads(workloadData);
      setHistory(historyData);
    } catch (error) {
      setMessage(`Failed to load data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadDashboardData();
    // Refresh data every minute
    const interval = setInterval(loadDashboardData, 60000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  // --- HANDLERS ---

  const handleLogin = async () => {
    setLoading(true);
    setMessage('Attempting admin login...');
    try {
      // Simulate OAuth Token request (using a known admin email)
      const form = new URLSearchParams();
      form.append('username', currentTeacher.email);
      form.append('password', 'simulated_password');

      const response = await fetch(`${API_BASE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        saveToken(data.access_token);
        setIsLoggedIn(true);
        setMessage('Login Successful! Welcome, Admin.');
      } else {
        setMessage(`Login Failed: ${data.detail || 'Check credentials'}`);
        clearToken();
      }
    } catch (error) {
      // This is often a CORS or network connectivity error
      setMessage(`Network error: Could not connect to backend API.`);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    clearToken();
    setIsLoggedIn(false);
    setMessage('Logged out successfully.');
    setWorkloads([]);
    setHistory([]);
  };

  // --- Component Rendering ---

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <style jsx global>{`
          /* Basic global styles */
          body { font-family: 'Inter', sans-serif; }
        `}</style>
        <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-sm">
          <h2 className="text-3xl font-extrabold text-gray-900 mb-6 text-center">Admin Login</h2>
          <p className="text-sm text-gray-500 mb-6 text-center">Simulated Google Workspace login for {currentTeacher.email}</p>
          
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out disabled:opacity-50"
          >
            {loading ? 'Logging In...' : 'Simulate Google Login'}
          </button>
          {message && <p className="mt-4 text-center text-sm text-red-500">{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
        <style jsx global>{`
          /* Basic global styles */
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
          body { font-family: 'Inter', sans-serif; }
        `}</style>
      <Header onLogout={handleLogout} userName={currentTeacher.name} />

      <div className="max-w-7xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <div className="mt-8 bg-white p-6 rounded-xl shadow-lg">
          {/* CRITICAL FIX: Pass 'message' down to ALL components that need to read/write it */}
          {activeTab === 'upload' && <TimetableUploader message={message} setMessage={setMessage} loadDashboardData={loadDashboardData} />}
          {activeTab === 'absence' && <AbsenceReporter message={message} setMessage={setMessage} workloads={workloads} loadDashboardData={loadDashboardData} />}
          {activeTab === 'dashboard' && <Dashboard workloads={workloads} history={history} loading={loading} />}
        </div>
      </div>
    </div>
  );
};

// --- Sub-Components ---

const Header = ({ onLogout, userName }) => (
  <header className="bg-white shadow">
    <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center">
        <svg className="w-6 h-6 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
        Substitution Manager
      </h1>
      <div className="flex items-center">
        <span className="text-sm font-medium text-gray-700 mr-4">Welcome, {userName}</span>
        <button
          onClick={onLogout}
          className="px-3 py-1 border border-transparent text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-700 transition"
        >
          Logout
        </button>
      </div>
    </div>
  </header>
);

const Tabs = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'upload', name: 'Upload Timetable' },
    { id: 'absence', name: 'Report Absence' },
    { id: 'dashboard', name: 'Dashboard & History' },
  ];

  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-8" aria-label="Tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              ${tab.id === activeTab
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
              whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm transition duration-150 ease-in-out
              rounded-t-lg
            `}
          >
            {tab.name}
          </button>
        ))}
      </nav>
    </div>
  );
};

const TimetableUploader = ({ message, setMessage, loadDashboardData }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.name.endsWith('.csv')) {
      setFile(selectedFile);
      setMessage(`File selected: ${selectedFile.name}`);
    } else {
      setFile(null);
      setMessage('Please select a valid CSV file.');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setMessage('Error: CSV file is missing.');
      return;
    }

    setUploading(true);
    setMessage(`Uploading and processing ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const token = loadToken();
      if (!token) throw new Error('Authentication token missing.');

      const response = await fetch(`${API_BASE_URL}/timetable/upload-master`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok) {
        setMessage(`✅ Success! ${data.message} Total periods: ${data.total_entries}.`);
        setFile(null);
        loadDashboardData();
      } else {
        setMessage(`❌ Upload Failed: ${data.detail || 'Upload failed.'}`);
      }
    } catch (error) {
      setMessage(`❌ Fatal Error during upload: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <form onSubmit={handleUpload} className="space-y-6">
      <h3 className="text-xl font-semibold text-gray-900">Upload Master CSV</h3>
      <p className="text-sm text-gray-500">
        This will **delete and replace** the current timetable. Use your cleaned, single-sheet CSV file.
      </p>

      <div className="flex items-center space-x-4">
        {/* The File Input Button */}
        <label htmlFor="file-upload" className="cursor-pointer bg-white border border-indigo-300 px-4 py-2 text-sm font-medium text-indigo-700 rounded-lg hover:bg-indigo-50 shadow-sm transition">
          {file ? `Change File (${file.name})` : "Choose CSV File"}
          <input 
            id="file-upload" 
            name="file-upload"
            type="file" 
            accept=".csv" 
            onChange={handleFileChange} 
            className="hidden"
            disabled={uploading}
          />
        </label>

        <button 
          type="submit"
          disabled={!file || uploading}
          className="px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 transition"
        >
          {uploading ? 'Processing...' : 'Upload & Replace Timetable'}
        </button>
      </div>

      {message && (
        <div className={`p-3 rounded-lg text-sm ${message.includes('Success') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message}
        </div>
      )}
    </form>
  );
};

const AbsenceReporter = ({ message, setMessage, workloads, loadDashboardData }) => {
  const [absentTeacher, setAbsentTeacher] = useState('');
  const [absenceDate, setAbsenceDate] = useState('');
  const [status, setStatus] = useState('Absent');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const availableTeachers = workloads.map(t => t.name);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!absentTeacher || !absenceDate) {
      setMessage('Please select a teacher and a date.');
      return;
    }
    if (status === 'Busy' && !reason) {
        setMessage('Reason is required for "Busy" status.');
        return;
    }

    setSubmitting(true);
    setMessage(`Reporting ${absentTeacher} as ${status}...`);
    setResult(null);

    const payload = {
      teacher_name: absentTeacher,
      absence_date: absenceDate,
      status: status,
      reason: status === 'Busy' ? reason : null,
    };

    try {
      const data = await fetchApi('/absence/report-day', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setMessage(data.message);
      setResult(data);
      loadDashboardData(); // Refresh workloads and history
    } catch (error) {
      setMessage(`❌ Absence Report Failed: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <h3 className="text-xl font-semibold text-gray-900">Report Teacher Absence/Duty</h3>
      
      {/* Teacher and Status Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label htmlFor="teacher" className="block text-sm font-medium text-gray-700">Absent Teacher Name</label>
          <select
            id="teacher"
            value={absentTeacher}
            onChange={(e) => setAbsentTeacher(e.target.value)}
            required
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-lg border shadow-sm"
          >
            <option value="">Select a Teacher</option>
            {availableTeachers.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="date" className="block text-sm font-medium text-gray-700">Absence Date</label>
          <input
            id="date"
            type="date"
            value={absenceDate}
            onChange={(e) => setAbsenceDate(e.target.value)}
            required
            // Set max date to today + 1 year for example
            max={new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().split('T')[0]}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-lg border shadow-sm"
          />
        </div>
        
        <div>
          <label htmlFor="status" className="block text-sm font-medium text-gray-700">Status</label>
          <select
            id="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-lg border shadow-sm"
          >
            <option value="Absent">Absent (Unplanned)</option>
            <option value="Busy">Busy (Planned Duty)</option>
          </select>
        </div>
      </div>

      {/* Reason Field for Busy Status */}
      {status === 'Busy' && (
        <div>
          <label htmlFor="reason" className="block text-sm font-medium text-gray-700">Reason for Duty (Required)</label>
          <input
            id="reason"
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required={status === 'Busy'}
            placeholder="e.g., Field Trip Supervision, Admin Meeting"
            className="mt-1 block w-full border border-gray-300 rounded-lg p-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          />
        </div>
      )}

      <button
        type="submit"
        disabled={submitting || !absentTeacher || !absenceDate}
        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {submitting ? 'Assigning...' : 'Assign Substitutes'}
      </button>

      {message && <div className="mt-4 p-3 rounded-lg text-sm bg-blue-100 text-blue-800">{message}</div>}

      {/* Substitution Results Display */}
      {result && result.substitutions && (
        <div className="mt-6 border-t pt-4">
          <h4 className="text-lg font-semibold mb-3">Substitution Assignments</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {['Period', 'Class', 'Subject', 'Substitute Assigned'].map((header) => (
                    <th key={header} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {result.substitutions.map((sub, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{sub.period}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{sub.class}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{sub.subject}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${sub.substitute !== 'Not Found' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {sub.substitute}
                        </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm text-gray-600 italic">Total Periods Processed: {result.substitutions.length}. Email notifications have been attempted.</p>
        </div>
      )}
    </form>
  );
};

const Dashboard = ({ workloads, history, loading }) => {
  if (loading) {
    return <div className="text-center py-10 text-gray-500">Loading data...</div>;
  }

  return (
    <div className="space-y-10">
      <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">Substitution Dashboard</h3>

      {/* Workload Section */}
      <section>
        <h4 className="text-lg font-medium text-gray-700 mb-4 flex items-center">
        <svg className="w-5 h-5 mr-2 text-indigo-500" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 11a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM7 7h6a1 1 0 110 2H7a1 1 0 110-2zM4 15a1 1 0 011-1h6a1 1 0 110 2H5a1 1 0 01-1-1z" clipRule="evenodd" fillRule="evenodd"></path></svg>
          Current Substitute Workload
        </h4>
        <div className="overflow-x-auto rounded-lg border shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Teacher</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sub Periods (Week)</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {workloads.map((t) => (
                        <tr key={t.email}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{t.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.email}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${t.sub_workload > 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>
                                    {t.sub_workload}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.is_admin ? 'Admin' : 'Teacher'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </section>

      {/* History Section */}
      <section>
        <h4 className="text-lg font-medium text-gray-700 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-indigo-500" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 00-2 0v3a1 1 0 002 0V7z" clipRule="evenodd" fillRule="evenodd"></path></svg>
          Substitution History Log ({history.length} Records)
        </h4>
        <div className="overflow-x-auto rounded-lg border shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        {['Date', 'Time', 'Absent Teacher', 'Status', 'Class', 'Subject', 'Substitute Assigned'].map((header) => (
                            <th key={header} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{header}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {history.slice(0, 20).map((record, index) => ( // Show last 20 records
                        <tr key={index} className={record.status === 'Busy' ? 'bg-yellow-50' : ''}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.date}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.time}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-red-600">{record.absent_teacher}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${record.status === 'Busy' ? 'bg-yellow-200 text-yellow-900' : 'bg-red-100 text-red-800'}`}>
                                    {record.status}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{record.class_name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{record.subject}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                    {record.substitute_teacher}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
        <p className="mt-3 text-sm text-gray-600 italic">Showing the 20 most recent substitution records.</p>
      </section>
    </div>
  );
};

export default App;