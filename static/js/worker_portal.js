document.addEventListener('DOMContentLoaded', function() {
    const restaurantId = window.location.pathname.split('/')[1];
    let activeShift = false;
    let startTime = null;
    let updateTimer = null;
    let autoLogoutTimer = null;
    
    // Initialize
    loadWorkers();
    checkCurrentShift();

    // Event Listeners
    document.getElementById('loginBtn')?.addEventListener('click', handleLogin);
    document.getElementById('clockInBtn')?.addEventListener('click', handleClockIn);
    document.getElementById('clockOutBtn')?.addEventListener('click', handleClockOut);
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    document.getElementById('manualHoursForm')?.addEventListener('submit', handleManualHours);

    function startAutoLogoutTimer() {
        if (autoLogoutTimer) {
            clearTimeout(autoLogoutTimer);
        }
        // Calculate milliseconds until 12 hours from now
        const twelveHoursMs = 12 * 60 * 60 * 1000;
        autoLogoutTimer = setTimeout(() => {
            handleClockOut().then(() => {
                handleLogout();
            });
        }, twelveHoursMs);
    }

    function clearAutoLogoutTimer() {
        if (autoLogoutTimer) {
            clearTimeout(autoLogoutTimer);
            autoLogoutTimer = null;
        }
    }

    async function loadWorkers() {
        try {
            const response = await fetch(`/${restaurantId}/api/workers`);
            const workers = await response.json();
            
            const select = document.getElementById('workerSelect');
            select.innerHTML = '<option value="">-- Select Name / בחר שם --</option>';
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
            if (data.active_shift && data.start_time) {
                startTime = new Date(data.start_time);
                updateStatus();
                startTimer();
            } else {
                updateStatus();
            }
        } catch (error) {
            console.error('Error checking shift:', error);
        }
    }

    function updateStatus() {
        const statusText = document.getElementById('statusText');
        const startTimeElem = document.getElementById('startTime');
        
        if (activeShift) {
            statusText.textContent = 'Currently Working / במשמרת';
            statusText.className = 'text-green-600 font-bold';
            if (startTime) {
                updateElapsedTime();
            }
        } else {
            statusText.textContent = 'Not Working / לא במשמרת';
            statusText.className = 'text-red-600 font-bold';
            startTimeElem.textContent = '';
        }
        
        document.getElementById('clockInBtn').disabled = activeShift;
        document.getElementById('clockOutBtn').disabled = !activeShift;
        
        // Update button styles
        document.getElementById('clockInBtn').className = activeShift 
            ? 'bg-gray-400 cursor-not-allowed text-white py-3 px-4 rounded-md'
            : 'bg-green-500 text-white py-3 px-4 rounded-md hover:bg-green-600';
            
        document.getElementById('clockOutBtn').className = !activeShift
            ? 'bg-gray-400 cursor-not-allowed text-white py-3 px-4 rounded-md'
            : 'bg-red-500 text-white py-3 px-4 rounded-md hover:bg-red-600';
    }

    function startTimer() {
        if (updateTimer) {
            clearInterval(updateTimer);
        }
        updateTimer = setInterval(updateElapsedTime, 1000);
    }

    function updateElapsedTime() {
        if (!startTime) return;
        
        const now = new Date();
        const elapsed = now - startTime;
        const hours = Math.floor(elapsed / (1000 * 60 * 60));
        const minutes = Math.floor((elapsed % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((elapsed % (1000 * 60)) / 1000);
        
        const startTimeElem = document.getElementById('startTime');
        startTimeElem.textContent = `Started: ${startTime.toLocaleTimeString()} (${hours}h ${minutes}m ${seconds}s)`;
    }

    async function handleLogin(e) {
        e.preventDefault();
        const name = document.getElementById('workerSelect').value;
        
        if (!name) {
            alert('Please select a name / אנא בחר שם');
            return;
        }
        
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
                checkCurrentShift();
            } else {
                const error = await response.json();
                alert(error.message || 'Login failed');
            }
        } catch (error) {
            alert('Error during login');
            console.error('Login error:', error);
        }
    }

    async function handleClockIn() {
        try {
            // Start tracking locally first
            activeShift = true;
            startTime = new Date();
            updateStatus();
            startTimer();
            startAutoLogoutTimer(); // Set the auto-logout timer

            // Then try to record in database (but don't block on failure)
            try {
                await fetch(`/${restaurantId}/api/worker/clock-in`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (error) {
                console.warn('Failed to record clock-in in database, but local tracking is active:', error);
            }
        } catch (error) {
            console.error('Clock in error:', error);
            alert('Warning: Local time tracking only / אזהרה: מעקב זמן מקומי בלבד');
        }
    }

    async function handleClockOut() {
        try {
            clearAutoLogoutTimer(); // Clear the auto-logout timer
            // First check if we have a start time
            if (!startTime) {
                alert('No active shift found / לא נמצאה משמרת פעילה');
                return;
            }

            // Calculate duration
            const now = new Date();
            const duration = (now - startTime) / 1000; // in seconds
            const hours = Math.floor(duration / 3600);
            const minutes = Math.floor((duration % 3600) / 60);
            
            // For very short shifts (less than a minute), just reset the state
            if (duration < 60) {
                // Try to clean up the database record, but don't block on failure
                try {
                    await fetch(`/${restaurantId}/api/worker/clock-out`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                } catch (error) {
                    console.warn('Failed to clean up clock-out in database:', error);
                }

                // Reset local state
                activeShift = false;
                startTime = null;
                if (updateTimer) {
                    clearInterval(updateTimer);
                    updateTimer = null;
                }
                updateStatus();
                return;
            }

            // Prepare the hours data
            const data = {
                name: document.getElementById('workerName').textContent,
                date: now.toISOString().split('T')[0],
                hours: hours,
                minutes: minutes
            };
            
            // Submit hours and try to clean up the shift record
            try {
                // Submit hours first
                const hoursResponse = await fetch(`/${restaurantId}/api/tips/AddHours`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (!hoursResponse.ok) {
                    const error = await hoursResponse.json();
                    throw new Error(error.message || 'Failed to submit hours');
                }

                // Then try to clean up the shift record (but don't block on failure)
                try {
                    await fetch(`/${restaurantId}/api/worker/clock-out`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                } catch (error) {
                    console.warn('Failed to clean up clock-out in database:', error);
                }

                // Reset local state
                activeShift = false;
                startTime = null;
                if (updateTimer) {
                    clearInterval(updateTimer);
                    updateTimer = null;
                }
                updateStatus();
                alert('Hours submitted successfully! / !השעות נשלחו בהצלחה');
            } catch (error) {
                console.error('Submit hours error:', error);
                alert('Error submitting hours / שגיאה בשליחת השעות');
            }
        } catch (error) {
            console.error('Clock out error:', error);
            alert('Error during clock out / שגיאה ביציאה');
        }
    }

    function showManualForm() {
        const manualForm = document.getElementById('manualHoursForm');
        const dateInput = manualForm.querySelector('input[name="date"]');
        const hoursInput = manualForm.querySelector('input[name="hours"]');
        const minutesInput = manualForm.querySelector('input[name="minutes"]');
        
        // Set today's date
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
        
        // If we have a start time, calculate duration
        if (startTime) {
            const duration = (new Date() - startTime) / 1000; // in seconds
            const hours = Math.floor(duration / 3600);
            const minutes = Math.floor((duration % 3600) / 60);
            
            hoursInput.value = hours;
            minutesInput.value = minutes;
        }
        
        // Scroll to the manual form
        manualForm.scrollIntoView({ behavior: 'smooth' });
    }

    async function handleLogout() {
        try {
            const response = await fetch(`/${restaurantId}/api/worker/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                document.getElementById('loginForm').classList.remove('hidden');
                document.getElementById('timeTracker').classList.add('hidden');
                document.getElementById('workerName').textContent = '';
                activeShift = false;
                startTime = null;
                if (updateTimer) {
                    clearInterval(updateTimer);
                    updateTimer = null;
                }
                updateStatus();
            }
        } catch (error) {
            alert('Error during logout');
            console.error('Logout error:', error);
        }
    }

    async function handleManualHours(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: document.getElementById('workerName').textContent,
            date: formData.get('date'),
            hours: formData.get('hours'),
            minutes: formData.get('minutes')
        };
        
        try {
            const response = await fetch(`/${restaurantId}/api/tips/AddHours`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                alert('Hours submitted successfully! / !השעות נשלחו בהצלחה');
                e.target.reset();
            } else {
                const error = await response.json();
                alert(error.message || 'Failed to submit hours');
            }
        } catch (error) {
            alert('Error submitting hours');
            console.error('Submit hours error:', error);
        }
    }
}); 