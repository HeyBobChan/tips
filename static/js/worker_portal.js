document.addEventListener('DOMContentLoaded', function() {
    const restaurantId = window.location.pathname.split('/')[1];
    let activeShift = false;
    
    // Initialize
    loadWorkers();
    checkCurrentShift();

    // Event Listeners
    document.getElementById('loginBtn')?.addEventListener('click', handleLogin);
    document.getElementById('clockInBtn')?.addEventListener('click', handleClockIn);
    document.getElementById('clockOutBtn')?.addEventListener('click', handleClockOut);
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    document.getElementById('manualHoursForm')?.addEventListener('submit', handleManualHours);

    async function loadWorkers() {
        try {
            const response = await fetch(`/${restaurantId}/api/workers`);
            const workers = await response.json();
            
            const select = document.getElementById('workerSelect');
            workers.forEach(worker => {
                const option = document.createElement('option');
                option.value = worker;
                option.textContent = worker;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading workers:', error);
        }
    }

    async function checkCurrentShift() {
        try {
            const response = await fetch(`/${restaurantId}/api/worker/current-shift`);
            const data = await response.json();
            
            activeShift = data.active_shift;
            updateStatus();
            
            if (data.active_shift) {
                document.getElementById('startTime').textContent = 
                    `Started: ${new Date(data.start_time).toLocaleTimeString()}`;
            }
        } catch (error) {
            console.error('Error checking shift:', error);
        }
    }

    function updateStatus() {
        const statusText = document.getElementById('statusText');
        statusText.textContent = activeShift ? 'Currently Working / במשמרת' : 'Not Working / לא במשמרת';
        statusText.className = activeShift ? 'text-green-600' : 'text-red-600';
        
        document.getElementById('clockInBtn').disabled = activeShift;
        document.getElementById('clockOutBtn').disabled = !activeShift;
    }

    async function handleLogin(e) {
        e.preventDefault();
        const name = document.getElementById('workerSelect').value;
        
        try {
            const response = await fetch(`/${restaurantId}/api/worker/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            
            if (response.ok) {
                document.getElementById('loginForm').classList.add('hidden');
                document.getElementById('timeTracker').classList.remove('hidden');
                document.getElementById('workerName').textContent = name;
            } else {
                alert('Login failed');
            }
        } catch (error) {
            alert('Error during login');
        }
    }

    // ... implement other handlers (clockIn, clockOut, logout, manualHours) ...
}); 