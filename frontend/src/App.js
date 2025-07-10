import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('wallet');
  const [transactions, setTransactions] = useState([]);
  const [qrData, setQrData] = useState(null);
  const [nfcSupported, setNfcSupported] = useState(false);
  const [nfcReading, setNfcReading] = useState(false);
  const [scannerActive, setScannerActive] = useState(false);
  const [searchUsers, setSearchUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // Forms
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ name: '', email: '', password: '' });
  const [rechargeAmount, setRechargeAmount] = useState('');
  const [paymentForm, setPaymentForm] = useState({ to_user: '', amount: '', description: '', method: 'transfer' });

  // Check NFC support
  useEffect(() => {
    if ('NDEFReader' in window) {
      setNfcSupported(true);
      console.log('✅ NFC suportado neste dispositivo');
    } else {
      console.log('❌ NFC não suportado neste dispositivo');
    }
  }, []);

  // Load user data
  useEffect(() => {
    if (token) {
      fetchUserData();
    }
  }, [token]);

  const apiCall = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro na requisição');
    }

    return response.json();
  };

  const fetchUserData = async () => {
    try {
      const userData = await apiCall('/api/profile');
      setUser(userData);
      if (activeTab === 'transactions') {
        fetchTransactions();
      }
    } catch (error) {
      console.error('Erro ao buscar dados do usuário:', error);
      setToken(null);
      localStorage.removeItem('token');
    }
  };

  const fetchTransactions = async () => {
    try {
      const transactionsData = await apiCall('/api/transactions');
      setTransactions(transactionsData);
    } catch (error) {
      console.error('Erro ao buscar transações:', error);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/login', {
        method: 'POST',
        body: JSON.stringify(loginForm)
      });
      
      setToken(response.token);
      localStorage.setItem('token', response.token);
      setUser(response.user);
      setLoginForm({ email: '', password: '' });
      setSuccess('Login realizado com sucesso!');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/register', {
        method: 'POST',
        body: JSON.stringify(registerForm)
      });
      
      setToken(response.token);
      localStorage.setItem('token', response.token);
      setUser(response.user);
      setRegisterForm({ name: '', email: '', password: '' });
      setSuccess('Conta criada com sucesso!');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRecharge = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/recharge', {
        method: 'POST',
        body: JSON.stringify({ amount: parseFloat(rechargeAmount) })
      });
      
      setUser(prev => ({ ...prev, balance: response.new_balance }));
      setRechargeAmount('');
      setSuccess(`Recarga de R$ ${rechargeAmount} realizada com sucesso!`);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/pay', {
        method: 'POST',
        body: JSON.stringify({
          ...paymentForm,
          amount: parseFloat(paymentForm.amount)
        })
      });
      
      setUser(prev => ({ ...prev, balance: response.new_balance }));
      setPaymentForm({ to_user: '', amount: '', description: '', method: 'transfer' });
      setSearchUsers([]);
      setSearchQuery('');
      setSuccess(`Pagamento de R$ ${paymentForm.amount} enviado para ${response.recipient}!`);
      if (activeTab === 'transactions') {
        fetchTransactions();
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const generateQR = async () => {
    try {
      const response = await apiCall('/api/generate-qr');
      setQrData(response);
    } catch (error) {
      setError(error.message);
    }
  };

  const startNFCReading = async () => {
    if (!nfcSupported) return;
    
    try {
      setNfcReading(true);
      const ndef = new NDEFReader();
      await ndef.scan();
      
      ndef.addEventListener('reading', ({ message }) => {
        const textRecord = message.records.find(record => record.recordType === 'text');
        if (textRecord) {
          const decoder = new TextDecoder();
          const nfcData = decoder.decode(textRecord.data);
          console.log('NFC Data:', nfcData);
          
          // Process NFC payment
          if (nfcData.startsWith('cashless:')) {
            const [, userId, userName] = nfcData.split(':');
            setPaymentForm(prev => ({ ...prev, to_user: userId, method: 'nfc' }));
            setSuccess(`Usuário ${userName} detectado via NFC!`);
          }
        }
        setNfcReading(false);
      });
    } catch (error) {
      setError('Erro ao ler NFC: ' + error.message);
      setNfcReading(false);
    }
  };

  const registerNFC = async () => {
    if (!nfcSupported) return;
    
    try {
      const ndef = new NDEFReader();
      const nfcId = `nfc_${user.id}_${Date.now()}`;
      
      await ndef.write({
        records: [
          {
            recordType: 'text',
            data: `cashless:${user.id}:${user.name}`
          }
        ]
      });
      
      await apiCall('/api/register-nfc', {
        method: 'POST',
        body: JSON.stringify({ nfc_id: nfcId })
      });
      
      setUser(prev => ({ ...prev, nfc_id: nfcId }));
      setSuccess('NFC registrado com sucesso!');
    } catch (error) {
      setError('Erro ao registrar NFC: ' + error.message);
    }
  };

  const startQRScanner = async () => {
    try {
      setScannerActive(true);
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      
      // QR code detection would go here
      // For now, we'll just show the scanner UI
    } catch (error) {
      setError('Erro ao acessar câmera: ' + error.message);
      setScannerActive(false);
    }
  };

  const stopQRScanner = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
    }
    setScannerActive(false);
  };

  const searchForUsers = async (query) => {
    if (query.length < 2) {
      setSearchUsers([]);
      return;
    }
    
    try {
      const users = await apiCall(`/api/users/search?q=${encodeURIComponent(query)}`);
      setSearchUsers(users);
    } catch (error) {
      console.error('Erro ao buscar usuários:', error);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setActiveTab('wallet');
    setSuccess('Logout realizado com sucesso!');
  };

  // Clear messages
  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError('');
        setSuccess('');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  // Auth screens
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">💳 Cashless</h1>
            <p className="text-gray-600">Sistema de Pagamentos Digitais</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
              <p className="text-green-600 text-sm">{success}</p>
            </div>
          )}

          <div className="flex border-b border-gray-200 mb-6">
            <button
              onClick={() => setActiveTab('login')}
              className={`flex-1 py-2 px-4 text-center ${
                activeTab === 'login' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setActiveTab('register')}
              className={`flex-1 py-2 px-4 text-center ${
                activeTab === 'register' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
              }`}
            >
              Cadastro
            </button>
          </div>

          {activeTab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <input
                type="email"
                placeholder="Email"
                value={loginForm.email}
                onChange={(e) => setLoginForm(prev => ({ ...prev, email: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <input
                type="password"
                placeholder="Senha"
                value={loginForm.password}
                onChange={(e) => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Entrando...' : 'Entrar'}
              </button>
            </form>
          )}

          {activeTab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              <input
                type="text"
                placeholder="Nome completo"
                value={registerForm.name}
                onChange={(e) => setRegisterForm(prev => ({ ...prev, name: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <input
                type="email"
                placeholder="Email"
                value={registerForm.email}
                onChange={(e) => setRegisterForm(prev => ({ ...prev, email: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <input
                type="password"
                placeholder="Senha"
                value={registerForm.password}
                onChange={(e) => setRegisterForm(prev => ({ ...prev, password: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Criando conta...' : 'Criar conta'}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // Main app
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">💳 Cashless</h1>
              {nfcSupported && (
                <span className="ml-2 bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                  NFC Ativo
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Olá, {user?.name}</span>
              <button
                onClick={logout}
                className="text-sm text-red-600 hover:text-red-800"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {success && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-green-600 text-sm">{success}</p>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {['wallet', 'pay', 'qr', 'transactions'].map((tab) => (
              <button
                key={tab}
                onClick={() => {
                  setActiveTab(tab);
                  if (tab === 'transactions') fetchTransactions();
                }}
                className={`py-4 px-2 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'wallet' && '💰 Carteira'}
                {tab === 'pay' && '💸 Pagar'}
                {tab === 'qr' && '📱 QR Code'}
                {tab === 'transactions' && '📊 Histórico'}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Wallet Tab */}
        {activeTab === 'wallet' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">💰 Minha Carteira</h2>
              <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white mb-6">
                <p className="text-sm opacity-90">Saldo disponível</p>
                <p className="text-3xl font-bold">R$ {user?.balance?.toFixed(2) || '0.00'}</p>
              </div>
              
              <form onSubmit={handleRecharge} className="space-y-4">
                <label className="block text-sm font-medium text-gray-700">
                  Recarregar saldo
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Valor para recarga"
                  value={rechargeAmount}
                  onChange={(e) => setRechargeAmount(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? 'Recarregando...' : 'Recarregar'}
                </button>
              </form>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">🏷️ Configurações NFC</h2>
              {nfcSupported ? (
                <div className="space-y-4">
                  {user?.nfc_id ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <p className="text-green-800 font-medium">✅ NFC Configurado</p>
                      <p className="text-sm text-green-600">Seu dispositivo está pronto para pagamentos NFC</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <p className="text-gray-600">Configure seu NFC para pagamentos rápidos</p>
                      <button
                        onClick={registerNFC}
                        className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700"
                      >
                        🏷️ Configurar NFC
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="text-yellow-800 font-medium">⚠️ NFC não disponível</p>
                  <p className="text-sm text-yellow-600">Seu dispositivo não suporta NFC</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Pay Tab */}
        {activeTab === 'pay' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">💸 Fazer Pagamento</h2>
              
              <form onSubmit={handlePayment} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Destinatário
                  </label>
                  <input
                    type="text"
                    placeholder="Buscar usuário..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      searchForUsers(e.target.value);
                    }}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  
                  {searchUsers.length > 0 && (
                    <div className="mt-2 border border-gray-200 rounded-lg max-h-40 overflow-y-auto">
                      {searchUsers.map((user) => (
                        <button
                          key={user.id}
                          type="button"
                          onClick={() => {
                            setPaymentForm(prev => ({ ...prev, to_user: user.id }));
                            setSearchQuery(user.name);
                            setSearchUsers([]);
                          }}
                          className="w-full text-left p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                        >
                          <p className="font-medium">{user.name}</p>
                          <p className="text-sm text-gray-600">{user.email}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <input
                  type="number"
                  step="0.01"
                  placeholder="Valor"
                  value={paymentForm.amount}
                  onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />

                <input
                  type="text"
                  placeholder="Descrição (opcional)"
                  value={paymentForm.description}
                  onChange={(e) => setPaymentForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />

                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setPaymentForm(prev => ({ ...prev, method: 'transfer' }))}
                    className={`p-3 rounded-lg border-2 text-sm font-medium ${
                      paymentForm.method === 'transfer'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700'
                    }`}
                  >
                    💰 Transferência
                  </button>
                  <button
                    type="button"
                    onClick={() => setPaymentForm(prev => ({ ...prev, method: 'qr' }))}
                    className={`p-3 rounded-lg border-2 text-sm font-medium ${
                      paymentForm.method === 'qr'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700'
                    }`}
                  >
                    📱 QR Code
                  </button>
                  <button
                    type="button"
                    onClick={() => setPaymentForm(prev => ({ ...prev, method: 'nfc' }))}
                    className={`p-3 rounded-lg border-2 text-sm font-medium ${
                      paymentForm.method === 'nfc'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700'
                    }`}
                  >
                    🏷️ NFC
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={loading || !paymentForm.to_user || !paymentForm.amount}
                  className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Processando...' : 'Pagar'}
                </button>
              </form>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">🏷️ Pagamento NFC</h2>
              
              {nfcSupported ? (
                <div className="space-y-4">
                  <p className="text-gray-600">Aproxime seu dispositivo de uma tag NFC para receber dados do destinatário</p>
                  
                  <button
                    onClick={startNFCReading}
                    disabled={nfcReading}
                    className="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50"
                  >
                    {nfcReading ? '📡 Aguardando NFC...' : '🏷️ Ler NFC'}
                  </button>

                  {nfcReading && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                      <div className="animate-pulse">
                        <p className="text-blue-800 font-medium">📡 Aguardando tag NFC...</p>
                        <p className="text-sm text-blue-600">Aproxime seu dispositivo da tag</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="text-yellow-800 font-medium">⚠️ NFC não disponível</p>
                  <p className="text-sm text-yellow-600">Use QR Code ou busca manual</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* QR Tab */}
        {activeTab === 'qr' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">📱 Meu QR Code</h2>
              
              <div className="text-center space-y-4">
                <button
                  onClick={generateQR}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700"
                >
                  Gerar QR Code
                </button>

                {qrData && (
                  <div className="space-y-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <img
                        src={`data:image/png;base64,${qrData.qr_image}`}
                        alt="QR Code"
                        className="mx-auto w-48 h-48"
                      />
                    </div>
                    <p className="text-gray-600">
                      Compartilhe este QR Code para receber pagamentos
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">📷 Escanear QR Code</h2>
              
              <div className="space-y-4">
                {!scannerActive ? (
                  <button
                    onClick={startQRScanner}
                    className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
                  >
                    📷 Iniciar Scanner
                  </button>
                ) : (
                  <div className="space-y-4">
                    <div className="relative">
                      <video
                        ref={videoRef}
                        className="w-full h-48 object-cover rounded-lg"
                        autoPlay
                        playsInline
                      />
                      <div className="absolute inset-0 border-2 border-green-500 rounded-lg pointer-events-none">
                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-32 h-32 border-2 border-green-500 rounded-lg"></div>
                      </div>
                    </div>
                    <button
                      onClick={stopQRScanner}
                      className="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700"
                    >
                      ⏹️ Parar Scanner
                    </button>
                  </div>
                )}
                
                <canvas ref={canvasRef} className="hidden"></canvas>
              </div>
            </div>
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">📊 Histórico de Transações</h2>
            </div>
            
            <div className="divide-y divide-gray-200">
              {transactions.length === 0 ? (
                <div className="p-6 text-center text-gray-500">
                  Nenhuma transação encontrada
                </div>
              ) : (
                transactions.map((transaction) => (
                  <div key={transaction.id} className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          {transaction.type === 'recharge' && '💰'}
                          {transaction.type === 'nfc' && '🏷️'}
                          {transaction.type === 'qr' && '📱'}
                          {transaction.type === 'transfer' && '💸'}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {transaction.from_user === user.id
                              ? `Para: ${transaction.to_name}`
                              : `De: ${transaction.from_name}`
                            }
                          </p>
                          <p className="text-sm text-gray-500">
                            {transaction.description || 'Sem descrição'}
                          </p>
                          <p className="text-xs text-gray-400">
                            {new Date(transaction.timestamp).toLocaleString('pt-BR')}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-medium ${
                          transaction.from_user === user.id
                            ? 'text-red-600'
                            : 'text-green-600'
                        }`}>
                          {transaction.from_user === user.id ? '-' : '+'}
                          R$ {transaction.amount.toFixed(2)}
                        </p>
                        <p className="text-xs text-gray-500 capitalize">
                          {transaction.type}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;