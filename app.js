// عناصر DOM
const accountsList = document.getElementById('accountsList');
const addAccountForm = document.getElementById('addAccountForm');
const botSettingsForm = document.getElementById('botSettingsForm');
const logsContainer = document.getElementById('logsContainer');
const refreshLogsBtn = document.getElementById('refreshLogs');
const clearLogsBtn = document.getElementById('clearLogs');
const verificationModal = new bootstrap.Modal(document.getElementById('verificationModal'));
const verifyCodeBtn = document.getElementById('verifyCode');

// متغيرات التطبيق
let currentVerificationId = null;

// تهيئة التطبيق
document.addEventListener('DOMContentLoaded', () => {
    loadAccounts();
    loadSettings();
    loadLogs();

    // أحداث النماذج
    addAccountForm.addEventListener('submit', handleAddAccount);
    botSettingsForm.addEventListener('submit', handleSaveSettings);
    refreshLogsBtn.addEventListener('click', loadLogs);
    clearLogsBtn.addEventListener('click', clearLogs);
    verifyCodeBtn.addEventListener('click', handleVerification);
});

// تحميل الحسابات من localStorage
function loadAccounts() {
    const accounts = JSON.parse(localStorage.getItem('telegramAccounts')) || [];
    accountsList.innerHTML = '';
    
    accounts.forEach((account, index) => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${account.name}</td>
            <td>${account.appId}</td>
            <td>
                <span class="badge ${account.status === 'active' ? 'bg-success' : 'bg-danger'}">
                    ${account.status === 'active' ? 'نشط' : 'غير نشط'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm ${account.status === 'active' ? 'btn-danger' : 'btn-primary'} toggle-btn" 
                        data-id="${index}">
                    ${account.status === 'active' ? 'إيقاف' : 'تشغيل'}
                </button>
                <button class="btn btn-sm btn-danger delete-btn" data-id="${index}">حذف</button>
            </td>
        `;
        
        accountsList.appendChild(row);
    });

    // إضافة أحداث للأزرار
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', toggleAccountStatus);
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', deleteAccount);
    });
}

// إضافة حساب جديد
function handleAddAccount(e) {
    e.preventDefault();
    
    const account = {
        name: document.getElementById('sessionName').value,
        appId: document.getElementById('appId').value,
        apiHash: document.getElementById('apiHash').value,
        phone: document.getElementById('phoneNumber').value,
        status: 'inactive',
        createdAt: new Date().toISOString()
    };

    // حفظ الحساب في localStorage
    const accounts = JSON.parse(localStorage.getItem('telegramAccounts')) || [];
    accounts.push(account);
    localStorage.setItem('telegramAccounts', JSON.stringify(accounts));
    
    alert('تم إضافة الحساب بنجاح!');
    addAccountForm.reset();
    
    // محاكاة إرسال كود التحقق
    currentVerificationId = accounts.length - 1;
    verificationModal.show();
    
    // تحديث القائمة
    loadAccounts();
    addLog(`تم إضافة حساب جديد: ${account.name}`);
}

// التحقق من الكود
function handleVerification() {
    const code = document.getElementById('verificationCode').value;
    
    if (!code) {
        alert('يرجى إدخال كود التحقق');
        return;
    }

    // في الواقع هنا ستتحقق من صحة الكود مع التليجرام
    // لكننا سنحاكي النجاح للتوضيح
    const accounts = JSON.parse(localStorage.getItem('telegramAccounts')) || [];
    
    if (accounts[currentVerificationId]) {
        accounts[currentVerificationId].status = 'active';
        localStorage.setItem('telegramAccounts', JSON.stringify(accounts));
        
        alert('تم التحقق من الحساب بنجاح!');
        verificationModal.hide();
        document.getElementById('verificationCode').value = '';
        currentVerificationId = null;
        
        // تحديث القائمة
        loadAccounts();
        addLog(`تم تفعيل الحساب: ${accounts[currentVerificationId]?.name}`);
    }
}

// تبديل حالة الحساب
function toggleAccountStatus(e) {
    const accountId = parseInt(e.target.dataset.id);
    const accounts = JSON.parse(localStorage.getItem('telegramAccounts')) || [];
    
    if (accounts[accountId]) {
        accounts[accountId].status = accounts[accountId].status === 'active' ? 'inactive' : 'active';
        localStorage.setItem('telegramAccounts', JSON.stringify(accounts));
        
        addLog(`تم ${e.target.textContent === 'تشغيل' ? 'تشغيل' : 'إيقاف'} الحساب ${accounts[accountId].name}`);
        loadAccounts();
    }
}

// حذف الحساب
function deleteAccount(e) {
    if (!confirm('هل أنت متأكد من حذف هذا الحساب؟')) return;
    
    const accountId = parseInt(e.target.dataset.id);
    const accounts = JSON.parse(localStorage.getItem('telegramAccounts')) || [];
    
    if (accounts[accountId]) {
        const accountName = accounts[accountId].name;
        accounts.splice(accountId, 1);
        localStorage.setItem('telegramAccounts', JSON.stringify(accounts));
        
        addLog(`تم حذف الحساب: ${accountName}`);
        loadAccounts();
    }
}

// تحميل الإعدادات
function loadSettings() {
    const settings = JSON.parse(localStorage.getItem('telegramSettings')) || {
        replyTracking: false,
        autoReply: false,
        autoReplyMessage: 'شكراً على رسالتك!',
        mediaSaving: false
    };
    
    document.getElementById('replyTracking').value = settings.replyTracking ? 'true' : 'false';
    document.getElementById('autoReply').value = settings.autoReply ? 'true' : 'false';
    document.getElementById('autoReplyMessage').value = settings.autoReplyMessage;
    document.getElementById('mediaSaving').value = settings.mediaSaving ? 'true' : 'false';
}

// حفظ الإعدادات
function handleSaveSettings(e) {
    e.preventDefault();
    
    const settings = {
        replyTracking: document.getElementById('replyTracking').value === 'true',
        autoReply: document.getElementById('autoReply').value === 'true',
        autoReplyMessage: document.getElementById('autoReplyMessage').value,
        mediaSaving: document.getElementById('mediaSaving').value === 'true',
        updatedAt: new Date().toISOString()
    };

    localStorage.setItem('telegramSettings', JSON.stringify(settings));
    alert('تم حفظ الإعدادات بنجاح!');
    addLog('تم تحديث إعدادات البوت');
}

// تحميل السجلات
function loadLogs() {
    const logs = JSON.parse(localStorage.getItem('telegramLogs')) || [];
    let logsHtml = '';
    
    logs.reverse().forEach(log => {
        logsHtml += `<div class="log-entry">${log.timestamp} - ${log.message}</div>`;
    });
    
    logsContainer.innerHTML = logsHtml || 'لا توجد سجلات متاحة';
}

// مسح السجلات
function clearLogs() {
    if (confirm('هل أنت متأكد من مسح جميع السجلات؟')) {
        localStorage.removeItem('telegramLogs');
        logsContainer.innerHTML = 'تم مسح السجلات';
        addLog('تم مسح سجل التشغيل');
    }
}

// إضافة سجل جديد
function addLog(message) {
    const logs = JSON.parse(localStorage.getItem('telegramLogs')) || [];
    logs.push({
        message: message,
        timestamp: new Date().toLocaleString()
    });
    
    // حفظ فقط آخر 50 سجل
    const recentLogs = logs.slice(-50);
    localStorage.setItem('telegramLogs', JSON.stringify(recentLogs));
    
    // تحديث العرض إذا كان مفتوحاً
    if (logsContainer.innerHTML.includes('جاري تحميل السجلات') || logsContainer.innerHTML.includes('لا توجد سجلات متاحة')) {
        loadLogs();
    }
}