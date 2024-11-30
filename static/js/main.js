// static/js/main.js

// Initialize the app once the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const root = document.getElementById('root');
    renderApp(root);
  });
  
  function renderApp(container) {
    let currentView = 'entry';
    let currentDate = new Date().toISOString().split('T')[0];
    let currentMonth = new Date().toISOString().slice(0, 7);
  
    // Render initial state
    render();
  
    function render() {
      container.innerHTML = `
        <div class="w-full max-w-6xl mx-auto p-4">
          <div class="bg-white shadow-lg rounded-lg">
            <!-- Tabs -->
            <div class="flex border-b">
              ${renderTab('entry', 'New Entry / כניסה חדשה')}
              ${renderTab('daily', 'Daily Summary / סיכום יומי')}
              ${renderTab('monthly', 'Monthly Summary / סיכום חודשי')}
            </div>
  
            <!-- Content -->
            <div class="p-6">
              ${currentView === 'entry' ? renderEntryForm() :
                currentView === 'daily' ? renderDailyView() :
                renderMonthlyView()}
            </div>
          </div>
        </div>
      `;
  
      // Add event listeners after rendering
      addEventListeners();
    }
  
    function renderTab(view, text) {
      return `
        <button 
          class="flex-1 py-4 px-6 text-center ${currentView === view ? 
            'border-b-2 border-blue-500 text-blue-500' : 
            'text-gray-500 hover:text-blue-500'}"
          data-view="${view}">
          ${text}
        </button>
      `;
    }
  
    function renderEntryForm() {
      return `
        <form id="entryForm" class="space-y-6">
          <div class="grid grid-cols-1 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700">שם העובד / Name *</label>
              <div class="mt-1 grid grid-cols-2 gap-4">
                <select id="workerSelect" 
                  class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="">-- Select Worker / בחר עובד --</option>
                  <!-- Workers will be loaded here -->
                </select>
                <div>
                  <input type="text" name="name" id="nameInput" required
                    placeholder="Or type new name / או הכנס שם חדש"
                    class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                </div>
              </div>
            </div>
  
            <div>
              <label class="block text-sm font-medium text-gray-700">תאריך / Date *</label>
              <input type="date" name="date" required value="${currentDate}"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
            </div>
  
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">שעות / Hours *</label>
                <input type="number" name="hours" required min="0" max="24" step="0.5"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">דקות / Minutes</label>
                <input type="number" name="minutes" min="0" max="59"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
              </div>
            </div>
  
            <div>
              <label class="block text-sm font-medium text-gray-700">סה״כ טיפים במזומן / Total Cash Tips</label>
              <input type="number" name="cashTips" min="0" step="0.01"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
            </div>
  
            <div>
              <label class="block text-sm font-medium text-gray-700">סה״כ טיפים באשראי / Total Credit Tips</label>
              <input type="number" name="creditTips" min="0" step="0.01"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
            </div>
          </div>
  
          <div>
            <button type="submit"
              class="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
              Submit Entry / שלח כניסה
            </button>
          </div>
        </form>
      `;
    }
  
    function renderDailyView() {
      return `
        <div class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-gray-700">בחר תאריך / Select Date</label>
            <input type="date" id="dailyDate" value="${currentDate}"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
          </div>
          <div id="dailyData" class="space-y-6">
            <!-- Data will be loaded here -->
            Loading...
          </div>
        </div>
      `;
    }
  
    function renderMonthlyView() {
      return `
        <div class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-gray-700">בחר חודש / Select Month</label>
            <input type="month" id="monthSelect" value="${currentMonth}"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
          </div>
          <div id="monthlyData" class="space-y-6">
            <!-- Data will be loaded here -->
            Loading...
          </div>
        </div>
      `;
    }
  
    function addEventListeners() {
      // Tab switching
      document.querySelectorAll('[data-view]').forEach(tab => {
        tab.addEventListener('click', (e) => {
          currentView = e.target.dataset.view;
          render();
        });
      });
  
      // Form submission
      const form = document.getElementById('entryForm');
      if (form) {
        form.addEventListener('submit', handleSubmit);
      }
  
      // Date selectors
      const dailyDate = document.getElementById('dailyDate');
      if (dailyDate) {
        dailyDate.addEventListener('change', (e) => {
          currentDate = e.target.value;
          loadDailyData(currentDate);
        });
        loadDailyData(currentDate);
      }
  
      const monthSelect = document.getElementById('monthSelect');
      if (monthSelect) {
        monthSelect.addEventListener('change', (e) => {
          currentMonth = e.target.value;
          loadMonthlyData(currentMonth);
        });
        loadMonthlyData(currentMonth);
      }
  
      // Add this: Populate worker select when on entry view
      if (currentView === 'entry') {
        populateWorkerSelect();
      }
    }
  
    async function handleSubmit(e) {
      e.preventDefault();
      const formData = new FormData(e.target);
      const data = Object.fromEntries(formData.entries());
  
      try {
        const response = await fetch('/api/tips/AddEntry', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });
  
        if (!response.ok) throw new Error('Failed to submit entry');
  
        alert('Entry submitted successfully! / !הכניסה נשלח בהצלחה');
        e.target.reset();
      } catch (error) {
        alert('Error submitting entry: ' + error.message);
      }
    }
  
    async function loadDailyData(date) {
      const container = document.getElementById('dailyData');
      try {
        const response = await fetch(`/api/tips/daily/${date}`);
        if (!response.ok) throw new Error('Failed to load daily data');
        
        const data = await response.json();
        container.innerHTML = renderDailyData(data);
      } catch (error) {
        container.innerHTML = `<div class="text-red-500">Error loading data: ${error.message}</div>`;
      }
    }
  
    async function loadMonthlyData(month) {
      const container = document.getElementById('monthlyData');
      try {
        const response = await fetch(`/api/tips/monthly/${month}`);
        if (!response.ok) throw new Error('Failed to load monthly data');
        
        const data = await response.json();
        container.innerHTML = renderMonthlyData(data);
      } catch (error) {
        console.error('Error loading monthly data:', error);
        container.innerHTML = renderMonthlyData(null); // Pass null to show empty state
      }
    }
  
    function renderDailyData(data) {
      // Ensure data exists with default values
      const safeData = {
        totalHours: data?.totalHours || 0,
        totalCashTips: data?.totalCashTips || 0,
        totalCreditTips: data?.totalCreditTips || 0,
        avgTipsPerHour: data?.avgTipsPerHour || 0,
        compensation: data?.compensation || 0,
        employees: data?.employees || []
      };

      return `
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="font-semibold">Total Hours / סה״כ שעות</h3>
            <p class="text-2xl">${safeData.totalHours.toFixed(2)}</p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="font-semibold">Cash Tips / טיפים במזומן</h3>
            <p class="text-2xl">₪${safeData.totalCashTips.toFixed(2)}</p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="font-semibold">Credit Tips / טיפים באשראי</h3>
            <p class="text-2xl">₪${safeData.totalCreditTips.toFixed(2)}</p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="font-semibold">Compensation / השלמה</h3>
            <p class="text-2xl">₪${safeData.compensation.toFixed(2)}</p>
          </div>
        </div>
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Employee / עובד
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Hours / שעות
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cash / מזומן
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Credit / אשראי
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Compensation / השלמה
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Final Total / סה״כ
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            ${safeData.employees.length > 0 ? 
              safeData.employees.map(emp => `
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-right">${emp.name}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-right">${emp.hours.toFixed(2)}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-right">₪${emp.cashTips.toFixed(2)}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-right">₪${emp.creditTips.toFixed(2)}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-right ${emp.compensation > 0 ? 'text-green-600' : ''}">
                    ${emp.compensation > 0 ? '+' : ''}₪${emp.compensation.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right font-medium">₪${emp.finalTotal.toFixed(2)}</td>
                </tr>
              `).join('')
              : `
                <tr>
                  <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-gray-500">
                    No data available for this day / אין נתונים ליום זה
                  </td>
                </tr>
              `
            }
          </tbody>
        </table>
      `;
    }
  
    function renderMonthlyData(data) {
      const safeEmployees = (data?.employeeTotals || []).map(emp => ({
        name: emp?.name || '',
        hours: Number(emp?.hours || 0),
        cashTips: Number(emp?.cashTips || 0),
        creditTips: Number(emp?.creditTips || 0),
        compensation: Number(emp?.compensation || 0),
        finalTotal: Number(emp?.finalTotal || 0)
      }));

      return `
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Employee / עובד
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Hours / שעות
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cash / מזומן
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Credit / אשראי
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Credit+Comp / אשראי+השלמה
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Final Total / סה״כ
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            ${safeEmployees.length > 0 ? 
              safeEmployees.map(emp => {
                const creditAndComp = emp.creditTips + emp.compensation;
                return `
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-right">${emp.name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">${emp.hours.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">₪${emp.cashTips.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">₪${emp.creditTips.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">₪${creditAndComp.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right font-medium">₪${emp.finalTotal.toFixed(2)}</td>
                  </tr>
                `;
              }).join('')
              : `
                <tr>
                  <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-gray-500">
                    No data available for this month / אין נתונים לחודש זה
                  </td>
                </tr>
              `
            }
          </tbody>
        </table>
      `;
    }
  
    // Add this function to populate the workers dropdown
    async function populateWorkerSelect() {
      try {
        const response = await fetch('/api/workers');
        if (!response.ok) throw new Error('Failed to load workers');
        const workers = await response.json();
        
        const select = document.getElementById('workerSelect');
        if (select) {
          select.innerHTML = '<option value="">-- Select Worker / בחר עובד --</option>';
          workers.forEach(worker => {
            const option = document.createElement('option');
            option.value = worker;
            option.textContent = worker;
            select.appendChild(option);
          });

          // Add event listener to sync select with input
          select.addEventListener('change', function() {
            const nameInput = document.getElementById('nameInput');
            if (nameInput) {
              nameInput.value = this.value;
            }
          });

          // Add event listener to clear select when typing in input
          const nameInput = document.getElementById('nameInput');
          if (nameInput) {
            nameInput.addEventListener('input', function() {
              if (this.value !== select.value) {
                select.value = '';
              }
            });
          }
        }
      } catch (error) {
        console.error('Error loading workers:', error);
      }
    }
  }