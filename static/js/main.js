// static/js/main.js

// Initialize the app once the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const root = document.getElementById('root');
    renderApp(root);
  });
  
  function renderApp(container) {
    let currentView = 'hours';
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
              ${renderTab('hours', 'Work Hours / שעות עבודה')}
              ${renderTab('tips', 'Tips Entry / הכנסת טיפים')}
              ${renderTab('daily', 'Daily Summary / סיכום יומי')}
              ${renderTab('monthly', 'Monthly Summary / סיכום חודשי')}
            </div>
  
            <!-- Content -->
            <div class="p-6">
              ${currentView === 'hours' ? renderHoursForm() :
                currentView === 'tips' ? renderTipsForm() :
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
  
    function renderHoursForm() {
      return `
        <form id="hoursForm" class="space-y-6">
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
              <button type="submit"
                class="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                Submit Hours / שלח שעות
              </button>
            </div>
          </div>
        </form>
      `;
    }
  
    function renderTipsForm() {
      return `
        <form id="tipsForm" class="space-y-6">
          <div class="grid grid-cols-1 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700">תאריך / Date *</label>
              <input type="date" name="date" required value="${currentDate}"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
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
              Submit Tips / שלח טיפים
            </button>
          </div>
        </form>
      `;
    }
  
    function renderDailyView() {
      return `
        <div class="space-y-6">
          <div class="flex justify-between items-center">
            <div>
              <label class="block text-sm font-medium text-gray-700">בחר תאריך / Select Date</label>
              <input type="date" id="dailyDate" value="${currentDate}"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
            </div>
            <button id="downloadDailyCSV" 
              class="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
              Download CSV / הורד קובץ
            </button>
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
          <div class="flex justify-between items-center">
            <div>
              <label class="block text-sm font-medium text-gray-700">בחר חודש / Select Month</label>
              <input type="month" id="monthSelect" value="${currentMonth}"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
            </div>
            <button id="downloadMonthlyCSV" 
              class="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
              Download CSV / הורד קובץ
            </button>
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
  
      // Hours form submission
      const hoursForm = document.getElementById('hoursForm');
      if (hoursForm) {
        hoursForm.addEventListener('submit', handleHoursSubmit);
      }
  
      // Tips form submission
      const tipsForm = document.getElementById('tipsForm');
      if (tipsForm) {
        tipsForm.addEventListener('submit', handleTipsSubmit);
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
      if (currentView === 'hours') {
        populateWorkerSelect();
      }
  
      // Add download button handlers
      const downloadDailyBtn = document.getElementById('downloadDailyCSV');
      if (downloadDailyBtn) {
        downloadDailyBtn.addEventListener('click', async () => {
          try {
            const response = await fetch(`/api/tips/daily/${currentDate}`);
            if (!response.ok) throw new Error('Failed to load daily data');
            const data = await response.json();
            const csvContent = generateDailyCSV(data);
            downloadCSV(`daily-summary-${currentDate}.csv`, csvContent);
          } catch (error) {
            alert('Error downloading CSV: ' + error.message);
          }
        });
      }
  
      const downloadMonthlyBtn = document.getElementById('downloadMonthlyCSV');
      if (downloadMonthlyBtn) {
        downloadMonthlyBtn.addEventListener('click', async () => {
          try {
            const response = await fetch(`/api/tips/monthly/${currentMonth}`);
            if (!response.ok) throw new Error('Failed to load monthly data');
            const data = await response.json();
            const csvContent = generateMonthlyCSV(data);
            downloadCSV(`monthly-summary-${currentMonth}.csv`, csvContent);
          } catch (error) {
            alert('Error downloading CSV: ' + error.message);
          }
        });
      }
  
      // Add date format handlers
      document.querySelectorAll('input[type="date"]').forEach(dateInput => {
        // On focus, show the date picker format (YYYY-MM-DD)
        dateInput.addEventListener('focus', function() {
          this.type = 'date';
        });
  
        // On blur, show the formatted date (DD/MM/YYYY)
        dateInput.addEventListener('blur', function() {
          if (this.value) {
            const date = new Date(this.value);
            const displayDate = date.toLocaleDateString('en-GB');
            this.setAttribute('data-display-value', displayDate);
          }
        });
  
        // Initial formatting if there's a value
        if (dateInput.value) {
          const date = new Date(dateInput.value);
          const displayDate = date.toLocaleDateString('en-GB');
          dateInput.setAttribute('data-display-value', displayDate);
        }
      });
    }
  
    async function handleHoursSubmit(e) {
      e.preventDefault();
      const formData = new FormData(e.target);
      const data = Object.fromEntries(formData.entries());
  
      try {
        const response = await fetch('/api/tips/AddHours', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });
  
        if (!response.ok) throw new Error('Failed to submit hours');
  
        alert('Hours submitted successfully! / !השעות נשלחו בהצלחה');
        e.target.reset();
      } catch (error) {
        alert('Error submitting hours: ' + error.message);
      }
    }
  
    async function handleTipsSubmit(e) {
      e.preventDefault();
      const formData = new FormData(e.target);
      const data = Object.fromEntries(formData.entries());
  
      try {
        const response = await fetch('/api/tips/AddTips', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });
  
        if (!response.ok) throw new Error('Failed to submit tips');
  
        alert('Tips submitted successfully! / !הטיפים נשלחו בהצלחה');
        e.target.reset();
      } catch (error) {
        alert('Error submitting tips: ' + error.message);
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
        avgWagePerHour: data?.avgWagePerHour || 0,
        compensation: data?.compensation || 0,
        employees: data?.employees || [],
        totalTips: (data?.totalCashTips || 0) + (data?.totalCreditTips || 0)
      };

      return `
        <div class="grid grid-cols-5 gap-4 mb-6">
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
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="font-semibold">Avg Per Hour / ממוצע לשעה</h3>
            <p class="text-2xl">₪${safeData.avgWagePerHour.toFixed(2)}</p>
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
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Employee / עובד
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hours / שעות
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cash Tips / טיפים במזומן
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Credit Tips / טיפים באשראי
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Compensation / השלמה
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Wage/Hour / שכר ממוצע לשעה
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total / סה״כ
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              ${data.employeeTotals.map(emp => `
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${emp.name}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ${emp.hours.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ₪${emp.cashTips.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ₪${emp.creditTips.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ₪${emp.compensation.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ₪${emp.avgWagePerHour.toFixed(2)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    ₪${emp.finalTotal.toFixed(2)}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
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
  
    function generateDailyCSV(data) {
      // Get all unique keys from employees, excluding internal/special fields
      const employeeFields = data.employees.length > 0 
        ? Object.keys(data.employees[0]).filter(key => !key.startsWith('_'))
        : [];

      // Create headers with both English and Hebrew labels
      const headerLabels = {
        name: 'Employee / עובד',
        hours: 'Hours / שעות',
        cashTips: 'Cash Tips / טיפים במזומן',
        creditTips: 'Credit Tips / טיפים באשראי',
        compensation: 'Compensation / השלמה',
        finalTotal: 'Final Total / סה״כ'
      };

      // Create CSV header row
      const headers = employeeFields.map(field => headerLabels[field] || field).join(',') + '\n';

      // Create employee rows
      const rows = data.employees.map(emp => 
        employeeFields.map(field => {
          const value = emp[field];
          // Format numbers to 2 decimal places if numeric
          return typeof value === 'number' ? value.toFixed(2) : value;
        }).join(',')
      ).join('\n');

      // Create totals row if summary fields exist
      const summaryFields = ['totalHours', 'totalCashTips', 'totalCreditTips', 'compensation'];
      const hasSummary = summaryFields.some(field => field in data);
      
      let totals = '';
      if (hasSummary) {
        totals = '\nTotals / סה״כ,' + 
          summaryFields.map(field => 
            (data[field] || 0).toFixed(2)
          ).join(',');
      }

      return headers + rows + totals;
    }

    function generateMonthlyCSV(data) {
      if (!data?.employeeTotals?.length) {
        return 'No data available / אין נתונים זמינים\n';
      }

      // Get all unique keys from employee totals
      const employeeFields = Object.keys(data.employeeTotals[0]).filter(key => !key.startsWith('_'));

      // Create headers with both English and Hebrew labels
      const headerLabels = {
        name: 'Employee / עובד',
        hours: 'Hours / שעות',
        cashTips: 'Cash Tips / טיפים במזומן',
        creditTips: 'Credit Tips / טיפים באשראי',
        compensation: 'Compensation / השלמה',
        finalTotal: 'Final Total / סה״כ'
      };

      // Create CSV header row
      const headers = employeeFields.map(field => headerLabels[field] || field).join(',') + '\n';

      // Create employee rows
      const rows = data.employeeTotals.map(emp => 
        employeeFields.map(field => {
          const value = emp[field];
          // Format numbers to 2 decimal places if numeric
          return typeof value === 'number' ? value.toFixed(2) : value;
        }).join(',')
      ).join('\n');

      return headers + rows;
    }

    function downloadCSV(filename, csvContent) {
      // Add BOM for proper UTF-8 encoding with Hebrew characters
      const BOM = '\uFEFF';
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
      
      try {
        // For modern browsers
        if (window.navigator.msSaveOrOpenBlob) {
          window.navigator.msSaveBlob(blob, filename);
          return;
        }

        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url); // Clean up
      } catch (error) {
        console.error('Error downloading CSV:', error);
        alert('Error downloading CSV. Please try again.');
      }
    }
  }
