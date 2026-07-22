// Global Application State
let state = {
    units: [],
    selectedUnit: null,
    reportDate: getTodayDateString(),
    dashDate: getTodayDateString(),
    dashReports: [],
    dashStats: {},
    currentUser: null,
    pendingTabId: null,
    existingReportForSelectedUnit: null,
    isFormUnlockedForEdit: false
};

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupTabNavigation();
    setupDatePickers();
    setupCategoryListeners();
    await checkAuthStatus();
    loadUnitsList();
    loadDashboardData();
}

/**
 * Returns current date in Israel Timezone (GMT+2 / GMT+3 IDT)
 * Format: YYYY-MM-DD
 */
function getTodayDateString() {
    try {
        const israelDate = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Jerusalem' });
        return israelDate;
    } catch (e) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
}

/**
 * Returns current time in Israel Timezone (GMT+2 / GMT+3 IDT)
 * Format: HH:MM
 */
function formatTimeString(isoStr) {
    try {
        let dt;
        if (!isoStr) {
            dt = new Date();
        } else {
            if (typeof isoStr === 'string' && !isoStr.includes('Z') && !isoStr.includes('+')) {
                dt = new Date(isoStr.replace(' ', 'T') + 'Z');
            } else {
                dt = new Date(isoStr);
            }
        }
        
        if (isNaN(dt.getTime())) {
            dt = new Date();
        }

        return dt.toLocaleTimeString('he-IL', {
            timeZone: 'Asia/Jerusalem',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    } catch (e) {
        const now = new Date();
        return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
}

/* -------------------------------------------------------------------
 * Auth & User Session
 * ------------------------------------------------------------------- */
async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth-check');
        const data = await res.json();
        if (data.is_authenticated) {
            state.currentUser = data.user;
        } else {
            state.currentUser = null;
        }
        updateUserUI();
    } catch (err) {
        state.currentUser = null;
        updateUserUI();
    }
}

function updateUserUI() {
    const statusBox = document.getElementById('user-status-box');
    const dashLock = document.getElementById('dash-lock-icon');
    const quotasLock = document.getElementById('quotas-lock-icon');

    if (state.currentUser) {
        statusBox.innerHTML = `
            <div class="user-welcome-badge">
                <i class="fa-solid fa-user-check"></i> שלום, ${state.currentUser.full_name}
            </div>
            <button class="btn btn-outline-white" onclick="executeLogout()">
                <i class="fa-solid fa-right-from-bracket"></i> התנתק
            </button>
        `;
        if (dashLock) dashLock.style.display = 'none';
        if (quotasLock) quotasLock.style.display = 'none';
    } else {
        statusBox.innerHTML = `
            <button class="btn btn-outline-white" id="login-trigger-btn" onclick="openLoginModal()">
                <i class="fa-solid fa-user-lock"></i> התחברות מנהלים
            </button>
        `;
        if (dashLock) dashLock.style.display = 'inline-block';
        if (quotasLock) quotasLock.style.display = 'inline-block';
    }
}

function openLoginModal(targetTabId = null) {
    state.pendingTabId = targetTabId;
    document.getElementById('login-password').value = '';
    document.getElementById('login-error-msg').classList.add('hidden');
    document.getElementById('login-modal').classList.remove('hidden');
    document.getElementById('login-password').focus();
}

function closeLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
    state.pendingTabId = null;
}

async function executeLogin() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error-msg');

    if (!password) {
        errorEl.textContent = 'נא להזין סיסמה';
        errorEl.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (data.success) {
            state.currentUser = data.user;
            closeLoginModal();
            updateUserUI();
            showToast(data.message, 'success');

            if (state.pendingTabId) {
                switchTab(state.pendingTabId);
                state.pendingTabId = null;
            } else {
                loadDashboardData();
                renderQuotasTable();
            }
        } else {
            errorEl.textContent = data.error || 'שם משתמש או סיסמה שגויים';
            errorEl.classList.remove('hidden');
        }
    } catch (err) {
        errorEl.textContent = 'שגיאת תקשורת עם השרת';
        errorEl.classList.remove('hidden');
    }
}

async function executeLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        state.currentUser = null;
        updateUserUI();
        showToast('התנתקת בהצלחה', 'info');

        const activeTab = document.querySelector('.tab-pane.active').id;
        if (activeTab === 'dashboard-tab' || activeTab === 'quotas-tab') {
            switchTab('report-tab');
        }
    } catch (err) {
        showToast('שגיאה בהתנתקות', 'danger');
    }
}

/* -------------------------------------------------------------------
 * Tab Navigation
 * ------------------------------------------------------------------- */
function setupTabNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');

            if ((tabId === 'dashboard-tab' || tabId === 'quotas-tab') && !state.currentUser) {
                openLoginModal(tabId);
                return;
            }

            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(b => b.classList.remove('active'));

    const activeBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');

    if (tabId === 'dashboard-tab') {
        loadDashboardData();
    } else if (tabId === 'quotas-tab') {
        renderQuotasTable();
    }
}

function setupDatePickers() {
    const reportDateInput = document.getElementById('report-date-input');
    const dashDatePicker = document.getElementById('dash-date-picker');

    reportDateInput.value = state.reportDate;
    dashDatePicker.value = state.dashDate;

    reportDateInput.addEventListener('change', (e) => {
        state.reportDate = e.target.value;
        if (state.selectedUnit) {
            fetchUnitReportForDate();
        }
    });

    dashDatePicker.addEventListener('change', (e) => {
        state.dashDate = e.target.value;
        loadDashboardData();
    });
}

/* -------------------------------------------------------------------
 * Load & Render Units
 * ------------------------------------------------------------------- */
async function loadUnitsList() {
    try {
        const res = await fetch('/api/units');
        const data = await res.json();
        if (data.success) {
            state.units = data.units;
            populateUnitDropdown();
            renderQuotasTable();
        }
    } catch (err) {
        showToast('שגיאה בטעינת רשימת היחידות', 'danger');
    }
}

function populateUnitDropdown() {
    const select = document.getElementById('unit-select');
    select.innerHTML = '<option value="">-- בחר יחידה מהרשימה --</option>';

    state.units.forEach(u => {
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = `${u.unit_name} (תקן אע"צים: ${u.quota})`;
        select.appendChild(opt);
    });

    select.addEventListener('change', (e) => {
        const unitId = parseInt(e.target.value);
        if (!unitId) {
            state.selectedUnit = null;
            document.getElementById('no-unit-placeholder').classList.remove('hidden');
            document.getElementById('report-inputs-grid').classList.add('hidden');
            document.getElementById('validation-wrapper').classList.add('hidden');
            document.getElementById('unit-quota-val').textContent = '0';
            return;
        }

        state.selectedUnit = state.units.find(u => u.id === unitId);
        state.isFormUnlockedForEdit = false;
        document.getElementById('no-unit-placeholder').classList.add('hidden');
        document.getElementById('report-inputs-grid').classList.remove('hidden');
        document.getElementById('validation-wrapper').classList.remove('hidden');

        document.getElementById('unit-quota-val').textContent = state.selectedUnit.quota;
        fetchUnitReportForDate();
    });
}

/* -------------------------------------------------------------------
 * Daily Report Form & Strict Form Locking
 * ------------------------------------------------------------------- */
function setFormLocked(isLocked) {
    const categoryInputs = document.querySelectorAll('.category-input');
    const stepBtns = document.querySelectorAll('.btn-step');
    const autoFillBtn = document.getElementById('auto-fill-btn');
    const submitBtn = document.getElementById('submit-report-btn');

    categoryInputs.forEach(input => {
        input.disabled = isLocked;
    });

    stepBtns.forEach(btn => {
        btn.disabled = isLocked;
        if (isLocked) {
            btn.style.opacity = '0.4';
            btn.style.cursor = 'not-allowed';
        } else {
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        }
    });

    if (autoFillBtn) autoFillBtn.disabled = isLocked;
    if (submitBtn && isLocked) submitBtn.disabled = true;
}

async function fetchUnitReportForDate() {
    if (!state.selectedUnit) return;

    try {
        const res = await fetch(`/api/reports?date=${state.reportDate}`);
        const data = await res.json();
        if (data.success) {
            const report = data.reports.find(r => r.unit_id === state.selectedUnit.id);
            state.existingReportForSelectedUnit = (report && report.is_submitted) ? report : null;

            if (state.existingReportForSelectedUnit) {
                document.getElementById('present-base').value = report.present_base;
                document.getElementById('reserve').value = report.reserve;
                document.getElementById('work-from-home').value = report.work_from_home;
                document.getElementById('standby-reduction').value = report.standby_reduction;
                document.getElementById('other-absent').value = report.other_absent;

                // STRICT LOCK: Lock form inputs by default until user explicitly confirms unlock in modal!
                setFormLocked(true);
                showDuplicateWarningModal(report);
            } else {
                resetCategoryInputs();
                setFormLocked(false);
            }
            recalculateValidation();
        }
    } catch (err) {
        resetCategoryInputs();
        setFormLocked(false);
        recalculateValidation();
    }
}

function showDuplicateWarningModal(report) {
    const unitTitleEl = document.getElementById('already-submitted-unit-title');
    const timeTextEl = document.getElementById('already-submitted-time-text');
    const modal = document.getElementById('already-submitted-modal');

    const formattedTime = formatTimeString(report.updated_at || report.created_at);

    unitTitleEl.textContent = `יחידת ${report.unit_name}`;
    timeTextEl.innerHTML = `יחידה זו כבר הגישה דיווח יומי מלא עבור תאריך <strong>${report.report_date}</strong> בשעה <strong>${formattedTime}</strong>.<br><br><span style="color:#b45309; font-weight:700;">הטופס נחסם למילוי נוסף למניעת דריסה.</span><br>לחצו על "אני רוצה לאשר פתיחה לעדכון" כדי לשחרר את הטופס לעריכה.`;
    
    modal.classList.remove('hidden');
}

function cancelDuplicateModal() {
    document.getElementById('already-submitted-modal').classList.add('hidden');
    // Reset unit dropdown to force user to choose again or leave locked
    document.getElementById('unit-select').value = '';
    document.getElementById('unit-select').dispatchEvent(new Event('change'));
    showToast('בחירת היחידה בוטלה והטופס נשאר נצול למילוי', 'info');
}

function confirmDuplicateUpdate() {
    document.getElementById('already-submitted-modal').classList.add('hidden');
    state.isFormUnlockedForEdit = true;
    setFormLocked(false);
    recalculateValidation();
    showToast('הטופס נפתח כעת לעריכה ולעדכון נתונים!', 'warning');
}

function showSuccessConfirmationModal(unitName, reportDate, quota) {
    document.getElementById('success-unit-name').textContent = `יחידת ${unitName}`;
    document.getElementById('success-date-val').textContent = reportDate;
    document.getElementById('success-quota-val').textContent = quota;
    document.getElementById('success-time-val').textContent = formatTimeString(null);
    document.getElementById('submission-success-modal').classList.remove('hidden');
}

function closeSuccessModal() {
    document.getElementById('submission-success-modal').classList.add('hidden');
}

function resetCategoryInputs() {
    document.getElementById('present-base').value = 0;
    document.getElementById('reserve').value = 0;
    document.getElementById('work-from-home').value = 0;
    document.getElementById('standby-reduction').value = 0;
    document.getElementById('other-absent').value = 0;
}

function setupCategoryListeners() {
    const inputs = document.querySelectorAll('.category-input');
    inputs.forEach(input => {
        input.addEventListener('input', () => {
            if (input.value === '' || parseInt(input.value) < 0) {
                input.value = 0;
            }
            recalculateValidation();
        });
    });
}

function stepVal(inputId, delta) {
    const input = document.getElementById(inputId);
    if (input.disabled) return;
    let val = parseInt(input.value) || 0;
    val = Math.max(0, val + delta);
    input.value = val;
    recalculateValidation();
}

function recalculateValidation() {
    if (!state.selectedUnit) return;

    const quota = state.selectedUnit.quota;
    const present = parseInt(document.getElementById('present-base').value) || 0;
    const reserve = parseInt(document.getElementById('reserve').value) || 0;
    const wfh = parseInt(document.getElementById('work-from-home').value) || 0;
    const standby = parseInt(document.getElementById('standby-reduction').value) || 0;
    const other = parseInt(document.getElementById('other-absent').value) || 0;

    const total = present + reserve + wfh + standby + other;

    const reportedTotalEl = document.getElementById('reported-total');
    const targetQuotaEl = document.getElementById('target-quota');
    const progressEl = document.getElementById('validation-progress');
    const msgEl = document.getElementById('validation-msg');
    const counterCard = document.getElementById('validation-counter-card');
    const submitBtn = document.getElementById('submit-report-btn');

    reportedTotalEl.textContent = total;
    targetQuotaEl.textContent = quota;

    const percent = quota > 0 ? Math.min(100, Math.round((total / quota) * 100)) : 0;
    progressEl.style.width = `${percent}%`;

    counterCard.classList.remove('is-match', 'is-mismatch');

    if (state.existingReportForSelectedUnit && !state.isFormUnlockedForEdit) {
        counterCard.classList.add('is-mismatch');
        msgEl.innerHTML = '<i class="fa-solid fa-lock"></i> היחידה כבר הגישה דיווח. הטופס נחסם למילוי שוב.';
        submitBtn.disabled = true;
        return;
    }

    if (total === quota) {
        counterCard.classList.add('is-match');
        msgEl.innerHTML = '<i class="fa-solid fa-circle-check"></i> הנתונים תואמים 100% לתקן היחידה. הטופס תקין ומוכן לשליחה!';
        submitBtn.disabled = false;
        submitBtn.classList.remove('disabled');
    } else if (total < quota) {
        counterCard.classList.add('is-mismatch');
        const diff = quota - total;
        msgEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> חסרים עוד <strong>${diff}</strong> עובדים להשלמת המצבה (התקן: ${quota}).`;
        submitBtn.disabled = true;
    } else {
        counterCard.classList.add('is-mismatch');
        const diff = total - quota;
        msgEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> חריגה! דווחו <strong>${diff}</strong> עובדים מעבר לתקן היחידה (${quota}).`;
        submitBtn.disabled = true;
    }
}

function autoFillRemaining() {
    if (!state.selectedUnit) return;
    const quota = state.selectedUnit.quota;

    const present = parseInt(document.getElementById('present-base').value) || 0;
    const reserve = parseInt(document.getElementById('reserve').value) || 0;
    const wfh = parseInt(document.getElementById('work-from-home').value) || 0;
    const standby = parseInt(document.getElementById('standby-reduction').value) || 0;

    const currentSubtotal = present + reserve + wfh + standby;
    const remaining = Math.max(0, quota - currentSubtotal);

    document.getElementById('other-absent').value = remaining;
    recalculateValidation();
    showToast(`יתרה של ${remaining} עובדים הושלמה לקטגוריה "לא נוכח"`, 'info');
}

async function submitDailyReport() {
    if (!state.selectedUnit) return;

    const reportData = {
        unit_id: state.selectedUnit.id,
        report_date: state.reportDate,
        present_base: parseInt(document.getElementById('present-base').value) || 0,
        reserve: parseInt(document.getElementById('reserve').value) || 0,
        work_from_home: parseInt(document.getElementById('work-from-home').value) || 0,
        standby_reduction: parseInt(document.getElementById('standby-reduction').value) || 0,
        other_absent: parseInt(document.getElementById('other-absent').value) || 0,
        submitted_by: 'נציג יחידה'
    };

    try {
        const res = await fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reportData)
        });

        const data = await res.json();
        if (data.success) {
            showSuccessConfirmationModal(state.selectedUnit.unit_name, state.reportDate, state.selectedUnit.quota);
            loadDashboardData();
        } else {
            showToast(data.error || 'שגיאה בשמירת הדיווח', 'danger');
        }
    } catch (err) {
        showToast('שגיאת תקשורת עם השרת', 'danger');
    }
}

/* -------------------------------------------------------------------
 * Admin Dashboard & Table
 * ------------------------------------------------------------------- */
async function loadDashboardData() {
    try {
        const res = await fetch(`/api/reports?date=${state.dashDate}`);
        const data = await res.json();
        if (data.success) {
            state.dashStats = data.stats;
            state.dashReports = data.reports;
            renderDashboardKPIs(data.stats);
            renderDashboardAuditFeed(data.updated_reports);
            renderDashboardTable(data.reports);
        }
    } catch (err) {
        showToast('שגיאה בטעינת נתוני הדשבורד', 'danger');
    }
}

function setDashToday() {
    state.dashDate = getTodayDateString();
    document.getElementById('dash-date-picker').value = state.dashDate;
    loadDashboardData();
}

function renderDashboardKPIs(stats) {
    document.getElementById('kpi-total-quota').textContent = stats.total_quota || 0;
    document.getElementById('kpi-present').textContent = stats.total_present || 0;
    document.getElementById('kpi-remote').textContent = (stats.total_wfh || 0) + (stats.total_reserve || 0);
    document.getElementById('kpi-percent').textContent = `${stats.completion_percent || 0}%`;
    document.getElementById('kpi-units-ratio').textContent = `${stats.submitted_units}/${stats.total_units} יחידות`;
}

function renderDashboardAuditFeed(updatedReports) {
    const feedContainer = document.getElementById('dashboard-alerts-feed');
    const feedList = document.getElementById('audit-feed-list');

    if (!updatedReports || updatedReports.length === 0) {
        feedContainer.classList.add('hidden');
        return;
    }

    feedContainer.classList.remove('hidden');
    feedList.innerHTML = '';

    updatedReports.forEach(r => {
        const item = document.createElement('div');
        item.className = 'audit-feed-item';
        const formattedTime = formatTimeString(r.updated_at);
        item.innerHTML = `<i class="fa-solid fa-pen"></i> יחידת <strong>${r.unit_name}</strong> עדכנה את הדיווח בשעה <strong>${formattedTime}</strong>`;
        feedList.appendChild(item);
    });
}

function renderDashboardTable(reports) {
    const tbody = document.getElementById('dashboard-table-body');
    const tfoot = document.getElementById('dashboard-table-foot');
    tbody.innerHTML = '';
    tfoot.innerHTML = '';

    if (!reports || reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11">לא נמצאו יחידות</td></tr>';
        return;
    }

    reports.forEach(r => {
        const tr = document.createElement('tr');
        const isSub = r.is_submitted;
        const revCount = r.revision_count || 1;
        const formattedTime = formatTimeString(r.updated_at || r.created_at);

        let statusBadge = '<span class="status-badge pending"><i class="fa-solid fa-clock"></i> טרם דיווחה</span>';
        if (isSub) {
            if (revCount > 1) {
                statusBadge = `<span class="status-badge updated" title="שינוי דיווח מס' ${revCount}"><i class="fa-solid fa-pen-to-square"></i> עודכן (${formattedTime})</span>`;
            } else {
                statusBadge = `<span class="status-badge submitted"><i class="fa-solid fa-check"></i> דיווחה (${formattedTime})</span>`;
            }
        }

        tr.innerHTML = `
            <td>${r.sid}</td>
            <td>${r.authority}</td>
            <td><strong>${r.unit_name}</strong></td>
            <td><strong>${r.quota}</strong></td>
            <td>${isSub ? r.present_base : '-'}</td>
            <td>${isSub ? r.reserve : '-'}</td>
            <td>${isSub ? r.work_from_home : '-'}</td>
            <td>${isSub ? r.standby_reduction : '-'}</td>
            <td>${isSub ? r.other_absent : '-'}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-outline" style="padding:0.35rem 0.7rem; font-size:0.84rem;" onclick="quickEditReport(${r.unit_id})">
                    <i class="fa-solid fa-pen-to-square"></i> ערוך
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Summary Foot Row
    const stats = state.dashStats;
    const footTr = document.createElement('tr');
    footTr.innerHTML = `
        <td colspan="3" style="text-align:right;"><strong>סה"כ כולל</strong></td>
        <td><strong>${stats.total_quota || 0}</strong></td>
        <td><strong>${stats.total_present || 0}</strong></td>
        <td><strong>${stats.total_reserve || 0}</strong></td>
        <td><strong>${stats.total_wfh || 0}</strong></td>
        <td><strong>${stats.total_standby || 0}</strong></td>
        <td><strong>${stats.total_other || 0}</strong></td>
        <td colspan="2"><strong>${stats.submitted_units}/${stats.total_units} יחידות</strong></td>
    `;
    tfoot.appendChild(footTr);
}

function filterDashTable() {
    const search = document.getElementById('dash-search').value.toLowerCase().trim();
    const filter = document.getElementById('dash-status-filter').value;

    const filtered = state.dashReports.filter(r => {
        const matchesName = r.unit_name.toLowerCase().includes(search) || r.authority.toLowerCase().includes(search);
        let matchesStatus = true;
        if (filter === 'submitted') matchesStatus = r.is_submitted === 1;
        if (filter === 'pending') matchesStatus = r.is_submitted === 0;
        if (filter === 'updated') matchesStatus = r.is_submitted === 1 && (r.revision_count || 1) > 1;

        return matchesName && matchesStatus;
    });

    renderDashboardTable(filtered);
}

function quickEditReport(unitId) {
    state.reportDate = state.dashDate;
    document.getElementById('report-date-input').value = state.reportDate;

    switchTab('report-tab');

    const select = document.getElementById('unit-select');
    select.value = unitId;
    select.dispatchEvent(new Event('change'));
}

function exportToExcel() {
    if (!state.currentUser) {
        openLoginModal();
        return;
    }
    const url = `/api/export-excel?date=${state.dashDate}`;
    window.location.href = url;
    showToast('קובץ האקסל מורד למחשבך...', 'success');
}

/* -------------------------------------------------------------------
 * Unit Quotas Manager
 * ------------------------------------------------------------------- */
function renderQuotasTable() {
    const tbody = document.getElementById('quotas-table-body');
    tbody.innerHTML = '';

    state.units.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.sid}</td>
            <td>${u.authority}</td>
            <td><strong>${u.unit_name}</strong></td>
            <td><strong style="color:var(--primary); font-size:1.1rem;">${u.quota}</strong></td>
            <td>
                <button class="btn btn-outline" style="padding:0.35rem 0.7rem; font-size:0.85rem;" onclick="openEditUnitModal(${u.id})">
                    <i class="fa-solid fa-pen"></i> ערוך תקן
                </button>
                <button class="btn btn-outline" style="padding:0.35rem 0.7rem; font-size:0.85rem; color:var(--danger);" onclick="deleteUnitClick(${u.id})">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openAddUnitModal() {
    if (!state.currentUser) {
        openLoginModal('quotas-tab');
        return;
    }
    document.getElementById('modal-title').textContent = 'הוספת יחידה חדשה';
    document.getElementById('modal-unit-id').value = '';
    document.getElementById('modal-sid').value = state.units.length + 1;
    document.getElementById('modal-authority').value = 'אכ"א';
    document.getElementById('modal-unit-name').value = '';
    document.getElementById('modal-quota').value = 10;
    document.getElementById('unit-modal').classList.remove('hidden');
}

function openEditUnitModal(unitId) {
    if (!state.currentUser) {
        openLoginModal('quotas-tab');
        return;
    }
    const unit = state.units.find(u => u.id === unitId);
    if (!unit) return;

    document.getElementById('modal-title').textContent = `עריכת יחידה: ${unit.unit_name}`;
    document.getElementById('modal-unit-id').value = unit.id;
    document.getElementById('modal-sid').value = unit.sid;
    document.getElementById('modal-authority').value = unit.authority;
    document.getElementById('modal-unit-name').value = unit.unit_name;
    document.getElementById('modal-quota').value = unit.quota;
    document.getElementById('unit-modal').classList.remove('hidden');
}

function closeUnitModal() {
    document.getElementById('unit-modal').classList.add('hidden');
}

async function saveUnitModal() {
    if (!state.currentUser) {
        openLoginModal('quotas-tab');
        return;
    }
    const unitId = document.getElementById('modal-unit-id').value;
    const sid = parseInt(document.getElementById('modal-sid').value) || 1;
    const authority = document.getElementById('modal-authority').value.trim();
    const unit_name = document.getElementById('modal-unit-name').value.trim();
    const quota = parseInt(document.getElementById('modal-quota').value) || 0;

    if (!unit_name) {
        showToast('נא להזין שם יחידה', 'danger');
        return;
    }

    const payload = { sid, authority, unit_name, quota };

    try {
        let res;
        if (unitId) {
            res = await fetch(`/api/units/${unitId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            res = await fetch('/api/units', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'היחידה עודכנה בהצלחה', 'success');
            closeUnitModal();
            loadUnitsList();
            loadDashboardData();
        } else {
            if (data.auth_required) {
                openLoginModal('quotas-tab');
            }
            showToast(data.error || 'שגיאה בשמירה', 'danger');
        }
    } catch (err) {
        showToast('שגיאה בתקשורת עם השרת', 'danger');
    }
}

async function deleteUnitClick(unitId) {
    if (!state.currentUser) {
        openLoginModal('quotas-tab');
        return;
    }
    if (!confirm('האם אתה בטוח שברצונך להסיר יחידה זו?')) return;

    try {
        const res = await fetch(`/api/units/${unitId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('היחידה הוסרה בהצלחה', 'success');
            loadUnitsList();
            loadDashboardData();
        } else {
            if (data.auth_required) openLoginModal('quotas-tab');
            showToast(data.error || 'שגיאה בהסרה', 'danger');
        }
    } catch (err) {
        showToast('שגיאה בהסרת היחידה', 'danger');
    }
}

/* -------------------------------------------------------------------
 * Notification Toast
 * ------------------------------------------------------------------- */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3500);
}
